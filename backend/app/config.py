"""InvoicePilot AI — Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "sqlite:///./invoicepilot.db"
    cors_origins: str = "http://localhost:5173"

    # File Upload
    max_file_size_mb: int = 20
    upload_dir: str = "./uploads"
    allowed_extensions: str = "pdf,png,jpg,jpeg"

    # Ollama / AI
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma:2b"
    ollama_timeout: int = 30  # Seconds; fall back to heuristics if exceeded
    ollama_context_length: int = 2048  # Smaller ctx = faster on 2b models
    ollama_num_predict: int = 512  # Max tokens in response
    demo_mode: bool = False

    # Processing
    arithmetic_tolerance: float = 0.02
    max_retries: int = 1  # 1 AI attempt, then heuristic fallback

    # Security
    log_level: str = "info"

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
