"""Enterprise-specific settings.

Note: API token is NOT stored here - it's managed via keyring in auth.py
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnterpriseSettings(BaseSettings):
    """Enterprise mode configuration."""

    # API Gateway URL (REST API)
    api_url: str = Field(
        default="https://api.donkit.ai",
        description="Donkit API Gateway URL",
    )

    # Connection timeout
    timeout: int = Field(
        default=60,
        description="Connection timeout in seconds",
    )

    # Message persistence
    persist_messages: bool = Field(
        default=True,
        description="Whether to persist messages to API Gateway",
    )

    model_config = SettingsConfigDict(
        env_prefix="DONKIT_ENTERPRISE_",
        case_sensitive=False,
    )

    @property
    def mcp_url(self) -> str:
        """MCP URL is derived from api_url with /mcp path."""
        base = self.api_url.rstrip("/")
        return f"{base}/mcp"


def load_enterprise_settings() -> EnterpriseSettings:
    """Load enterprise settings from environment."""
    return EnterpriseSettings()
