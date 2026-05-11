"""Configuration settings for the data-agent."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings for the data agent."""

    # Execution settings
    execution_timeout_seconds: int = 60
    visualization_timeout_seconds: int = 30
    kernel_memory_limit_mb: int = 512

    # LLM settings
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Docker settings
    kernel_container_name: str = "data-agent-kernel"
    docker_network: str = "data-agent-net"

    # Dataset settings
    dataset_mount_path: str = "/data"
    dataset_max_rows: int = 1000

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Security settings
    security_enabled: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()