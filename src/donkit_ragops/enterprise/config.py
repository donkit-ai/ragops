"""Enterprise-specific settings.

Note: API token is NOT stored here - it's managed via keyring in auth.py
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnterpriseSettings(BaseSettings):
    """Enterprise mode configuration.

    Uses RAGOPS_ prefix for consistency with main settings.
    API URL is read from RAGOPS_DONKIT_BASE_URL.
    """

    # API Gateway URL (REST API)
    # Maps to RAGOPS_DONKIT_BASE_URL environment variable
    donkit_base_url: str = Field(
        default="https://api.donkit.ai",
        description="Donkit API Gateway URL",
    )

    # Connection timeout
    donkit_timeout: int = Field(
        default=60,
        description="Connection timeout in seconds",
    )

    # Message persistence (internal, for development)
    donkit_persist_messages: bool = Field(
        default=True,
        description="Whether to persist messages to API Gateway",
    )

    model_config = SettingsConfigDict(
        env_prefix="RAGOPS_",
        case_sensitive=False,
    )

    @property
    def api_url(self) -> str:
        """API URL (alias for donkit_base_url for backward compatibility)."""
        return self.donkit_base_url

    @property
    def timeout(self) -> int:
        """Timeout (alias for donkit_timeout for backward compatibility)."""
        return self.donkit_timeout

    @property
    def persist_messages(self) -> bool:
        """Persist messages (alias for backward compatibility)."""
        return self.donkit_persist_messages

    @property
    def mcp_url(self) -> str:
        """MCP URL is derived from api_url with /mcp path."""
        base = self.donkit_base_url.rstrip("/")
        return f"{base}/mcp/"


def load_enterprise_settings() -> EnterpriseSettings:
    """Load enterprise settings from environment."""
    return EnterpriseSettings()
