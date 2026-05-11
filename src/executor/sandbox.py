"""Docker sandbox lifecycle manager.

Manages the Docker container lifecycle for secure code execution.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import subprocess

from src.config import settings


class SandboxStatus(Enum):
    """Status of the sandbox container."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    UNHEALTHY = "unhealthy"
    ERROR = "error"


@dataclass
class SandboxConfig:
    """Configuration for the sandbox container."""

    image: str = "data-agent-kernel:latest"
    container_name: str = "data-agent-kernel"
    network: str = "data-agent-net"
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    read_only: bool = True
    no_network: bool = True
    health_check_interval: int = 30
    health_check_timeout: int = 5


class SandboxError(Exception):
    """Sandbox-related errors."""
    pass


class SandboxManager:
    """Manages Docker container lifecycle for the execution sandbox."""

    def __init__(self, config: Optional[SandboxConfig] = None):
        """Initialize the sandbox manager.

        Args:
            config: Sandbox configuration
        """
        self.config = config or SandboxConfig(
            image="data-agent-kernel:latest",
            container_name=settings.kernel_container_name,
            network=settings.docker_network,
            memory_limit=f"{settings.kernel_memory_limit_mb}m",
        )
        self._status: SandboxStatus = SandboxStatus.STOPPED
        self._health_check_task: Optional[asyncio.Task] = None

    @property
    def status(self) -> SandboxStatus:
        """Get the current sandbox status."""
        return self._status

    def _run_docker_command(self, *args: str, timeout: int = 30) -> tuple[int, str, str]:
        """Run a docker command.

        Args:
            *args: Docker command arguments
            timeout: Timeout in seconds

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = ["docker"] + list(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except FileNotFoundError:
            raise SandboxError("Docker not found. Is Docker installed?")

    async def start(self) -> None:
        """Start the sandbox container.

        Raises:
            SandboxError: If container fails to start
        """
        self._status = SandboxStatus.STARTING

        # Check if container already exists
        rc, stdout, _ = self._run_docker_command(
            "ps", "-a", "--filter", f"name={self.config.container_name}", "--format", "{{.Names}}"
        )

        container_exists = self.config.container_name in stdout

        if container_exists:
            # Check if running
            rc, stdout, _ = self._run_docker_command(
                "ps", "--filter", f"name={self.config.container_name}", "--format", "{{.Names}}"
            )

            if self.config.container_name in stdout:
                # Already running
                self._status = SandboxStatus.RUNNING
                return

            # Start existing container
            rc, _, stderr = self._run_docker_command("start", self.config.container_name)
        else:
            # Create and start new container
            create_cmd = [
                "create",
                "--name", self.config.container_name,
                "--network", self.config.network,
                "--memory", self.config.memory_limit,
                "--cpus", str(self.config.cpu_limit),
            ]

            if self.config.read_only:
                create_cmd.append("--read-only")

            if self.config.no_network:
                create_cmd.append("--network:none")

            # Volume mount for datasets
            create_cmd.extend(["-v", f"{settings.dataset_mount_path}:/data:ro"])

            create_cmd.append(self.config.image)

            rc, _, stderr = self._run_docker_command(*create_cmd)

            if rc != 0:
                self._status = SandboxStatus.ERROR
                raise SandboxError(f"Failed to create container: {stderr}")

            rc, _, stderr = self._run_docker_command("start", self.config.container_name)

        if rc != 0:
            self._status = SandboxStatus.ERROR
            raise SandboxError(f"Failed to start container: {stderr}")

        # Wait for container to be ready
        await self._wait_for_ready()
        self._status = SandboxStatus.RUNNING

        # Start health check loop
        self._start_health_check()

    async def stop(self) -> None:
        """Stop the sandbox container."""
        self._stop_health_check()

        rc, _, stderr = self._run_docker_command("stop", self.config.container_name, timeout=10)

        if rc != 0 and "No such container" not in stderr:
            raise SandboxError(f"Failed to stop container: {stderr}")

        self._status = SandboxStatus.STOPPED

    async def restart(self) -> None:
        """Restart the sandbox container."""
        await self.stop()
        await asyncio.sleep(2)
        await self.start()

    async def _wait_for_ready(self, timeout: int = 60) -> None:
        """Wait for the container to be ready (Jupyter server up).

        Args:
            timeout: Maximum wait time in seconds

        Raises:
            SandboxError: If container doesn't become ready in time
        """
        import httpx

        jupyter_ready = False
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            rc, stdout, _ = self._run_docker_command(
                "logs", "--tail", "50", self.config.container_name
            )

            if "Jupyter Server" in stdout or "The Jupyter Notebook" in stdout:
                jupyter_ready = True
                break

            await asyncio.sleep(2)

        if not jupyter_ready:
            raise SandboxError(f"Container did not become ready within {timeout}s")

    async def health_check(self) -> bool:
        """Perform a health check on the sandbox.

        Returns:
            True if sandbox is healthy, False otherwise
        """
        # Check container is running
        rc, stdout, _ = self._run_docker_command(
            "ps", "--filter", f"name={self.config.container_name}", "--format", "{{.Status}}"
        )

        if rc != 0 or not stdout.strip():
            self._status = SandboxStatus.STOPPED
            return False

        # Check Jupyter server is responsive
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get("http://localhost:8888/api/status")
                if response.status_code == 200:
                    self._status = SandboxStatus.RUNNING
                    return True

        except (httpx.HTTPError, httpx.TimeoutException):
            pass

        self._status = SandboxStatus.UNHEALTHY
        return False

    def _start_health_check(self) -> None:
        """Start the periodic health check loop."""
        if self._health_check_task is not None:
            return

        async def health_check_loop():
            while True:
                await asyncio.sleep(self.config.health_check_interval)
                healthy = await self.health_check()
                if not healthy:
                    # Attempt restart
                    try:
                        await self.restart()
                    except Exception:
                        self._status = SandboxStatus.ERROR

        self._health_check_task = asyncio.create_task(health_check_loop())

    def _stop_health_check(self) -> None:
        """Stop the health check loop."""
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            self._health_check_task = None

    async def get_logs(self, tail: int = 100) -> str:
        """Get container logs.

        Args:
            tail: Number of lines to retrieve

        Returns:
            Container logs
        """
        rc, stdout, stderr = self._run_docker_command(
            "logs", "--tail", str(tail), self.config.container_name
        )

        if rc != 0:
            raise SandboxError(f"Failed to get logs: {stderr}")

        return stdout

    def get_container_info(self) -> dict:
        """Get container information.

        Returns:
            Dict with container status and config
        """
        rc, stdout, _ = self._run_docker_command(
            "inspect", self.config.container_name
        )

        if rc != 0:
            return {
                "exists": False,
                "status": "unknown",
            }

        import json
        info = json.loads(stdout)[0]

        return {
            "exists": True,
            "status": info.get("State", {}).get("Status", "unknown"),
            "image": info.get("Config", {}).get("Image", ""),
            "created": info.get("Created", ""),
        }
