"""Jupyter kernel client for async code execution.

Provides an async interface to a Jupyter kernel running inside the Docker sandbox.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional
import uuid

import httpx

from src.config import settings


@dataclass
class ExecutionResult:
    """Result from executing code in the kernel."""

    result: Any
    stdout: str
    stderr: str
    execution_time_ms: int
    success: bool = True


class KernelError(Exception):
    """Kernel-related errors."""
    pass


class KernelTimeoutError(KernelError):
    """Kernel execution timeout."""
    pass


class KernelClient:
    """Async Jupyter kernel client.

    Manages connection to a Jupyter kernel running inside the sandbox container.
    The kernel is accessed via HTTP (jupyter-server proxy in the container).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8888",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """Initialize the kernel client.

        Args:
            base_url: Base URL of the Jupyter server in the container
            timeout: Default timeout for execution in seconds
            max_retries: Maximum retries for transient failures
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._kernel_id: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._execution_count = 0
        self._busy = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def connect(self, kernel_id: Optional[str] = None) -> str:
        """Connect to a kernel.

        Args:
            kernel_id: Specific kernel ID to connect to, or None for new kernel

        Returns:
            The kernel ID
        """
        client = await self._get_client()

        if kernel_id:
            self._kernel_id = kernel_id
            return kernel_id

        # Get list of available kernels
        try:
            response = await client.get(f"{self.base_url}/api/kernels")
            response.raise_for_status()
            kernels = response.json()

            if kernels:
                self._kernel_id = kernels[0]["id"]
                return self._kernel_id

        except httpx.HTTPError:
            pass

        # Create a new kernel if none available
        try:
            response = await client.post(
                f"{self.base_url}/api/kernels",
                json={"name": "python3"},
            )
            response.raise_for_status()
            kernel_info = response.json()
            self._kernel_id = kernel_info["id"]
            return self._kernel_id

        except httpx.HTTPError as e:
            raise KernelError(f"Failed to connect or create kernel: {e}")

    async def execute(
        self,
        code: str,
        timeout: Optional[int] = None,
        store_history: bool = True,
    ) -> ExecutionResult:
        """Execute code in the kernel.

        Args:
            code: Python code to execute
            timeout: Timeout in seconds (overrides default)
            store_history: Whether to store in kernel history

        Returns:
            ExecutionResult with result, stdout, stderr, and timing

        Raises:
            KernelError: If execution fails
            KernelTimeoutError: If execution times out
        """
        if not self._kernel_id:
            await self.connect()

        client = await self._get_client()
        exec_timeout = timeout or self.timeout
        self._execution_count += 1

        # Create execution request
        msg_id = str(uuid.uuid4())

        # Execute via WebSocket would be ideal, but using HTTP API
        # Poll for execution result
        execute_payload = {
            "code": code,
            "silent": False,
            "store_history": store_history,
            "user_expressions": {},
            "allow_stdin": False,
        }

        try:
            # Start execution
            response = await client.post(
                f"{self.base_url}/api/kernels/{self._kernel_id}/execute",
                json=execute_payload,
            )
            response.raise_for_status()

            # For simplicity, assume synchronous execution completed
            # In production, use WebSocket for real-time output
            result_payload = response.json()

            return ExecutionResult(
                result=result_payload.get("data", {}),
                stdout=result_payload.get("stdout", ""),
                stderr=result_payload.get("stderr", ""),
                execution_time_ms=result_payload.get("execution_time_ms", 0),
                success=result_payload.get("success", True),
            )

        except httpx.TimeoutException:
            raise KernelTimeoutError(f"Kernel execution timed out after {exec_timeout}s")

        except httpx.HTTPError as e:
            raise KernelError(f"Kernel execution failed: {e}")

    async def interrupt(self) -> None:
        """Interrupt the currently executing code.

        Note: This requires the interrupt kernel extension to be installed.
        """
        if not self._kernel_id:
            return

        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.base_url}/api/kernels/{self._kernel_id}/interrupt"
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise KernelError(f"Failed to interrupt kernel: {e}")

    async def restart(self, timeout: int = 30) -> None:
        """Restart the kernel.

        Args:
            timeout: Timeout for restart operation in seconds

        Raises:
            KernelError: If restart fails
        """
        if not self._kernel_id:
            raise KernelError("No kernel connected")

        client = await self._get_client()

        try:
            # Restart the kernel
            response = await client.post(
                f"{self.base_url}/api/kernels/{self._kernel_id}/restart",
                timeout=timeout,
            )
            response.raise_for_status()
            self._execution_count = 0

        except httpx.HTTPError as e:
            raise KernelError(f"Failed to restart kernel: {e}")

    async def is_alive(self) -> bool:
        """Check if the kernel is responsive.

        Returns:
            True if kernel responds to heartbeat, False otherwise
        """
        if not self._kernel_id:
            return False

        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.base_url}/api/kernels/{self._kernel_id}"
            )
            return response.status_code == 200

        except httpx.HTTPError:
            return False

    async def get_kernel_info(self) -> dict:
        """Get kernel information.

        Returns:
            Dict with kernel info (language, version, etc.)
        """
        if not self._kernel_id:
            await self.connect()

        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.base_url}/api/kernels/{self._kernel_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            raise KernelError(f"Failed to get kernel info: {e}")

    async def close(self) -> None:
        """Close the client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def __del__(self):
        """Cleanup on deletion."""
        # Note: Can't use async in __del__, just cleanup hints
        pass
