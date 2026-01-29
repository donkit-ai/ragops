"""Web server configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebConfig(BaseSettings):
    """Configuration for the web server."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8067
    reload: bool = False

    # CORS settings
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Session settings
    session_ttl_seconds: int = 7200  # 2 hours
    cleanup_interval_seconds: int = 300  # 5 minutes

    # File upload settings
    max_upload_size_mb: int = 100
    upload_dir: str = "./uploads"

    # Enterprise settings (optional overrides)
    enterprise_api_url: str = Field(
        default="https://api.dev.donkit.ai",
        description="Enterprise API Gateway URL",
    )
    enterprise_persist_messages: bool = Field(
        default=True,
        description="Persist messages to API Gateway in enterprise mode",
    )

    model_config = SettingsConfigDict(env_prefix="DONKIT_", case_sensitive=False)

    @property
    def enterprise_mcp_url(self) -> str:
        """MCP URL derived from enterprise API URL."""
        base = self.enterprise_api_url.rstrip("/")
        return f"{base}/mcp/"


def get_web_config() -> WebConfig:
    """Load web configuration from environment."""
    return WebConfig()
