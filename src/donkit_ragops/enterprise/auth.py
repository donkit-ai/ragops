"""Token management for enterprise mode.

Uses keyring for secure token storage, with fallback to .env file.
Tokens are NEVER:
- Logged to console/files
- Passed to LLM prompts
"""

from __future__ import annotations

import keyring
import keyring.errors

SERVICE_NAME = "donkit-ragops"
TOKEN_KEY = "api_token"


def _get_token_from_env() -> str | None:
    """Get token from .env file (RAGOPS_DONKIT_API_KEY)."""
    try:
        from donkit_ragops.config import load_settings

        settings = load_settings()
        return settings.donkit_api_key
    except Exception:
        return None


class TokenService:
    """Service for managing enterprise API tokens using keyring."""

    def __init__(self, service_name: str = SERVICE_NAME):
        self.service_name = service_name

    def save_token(self, token: str) -> None:
        """Save token to keyring.

        Args:
            token: The API token to save
        """
        keyring.set_password(self.service_name, TOKEN_KEY, token)

    def get_token(self) -> str | None:
        """Get token from keyring or .env file.

        Checks keyring first, then falls back to .env (RAGOPS_DONKIT_API_KEY).

        Returns:
            The stored token, or None if not found/access denied
        """
        # Try keyring first
        try:
            token = keyring.get_password(self.service_name, TOKEN_KEY)
            if token:
                return token
        except (keyring.errors.KeyringError, Exception):
            pass

        # Fallback to .env file
        return _get_token_from_env()

    def delete_token(self) -> None:
        """Delete token from keyring."""
        try:
            keyring.delete_password(self.service_name, TOKEN_KEY)
        except keyring.errors.PasswordDeleteError:
            pass

    def has_token(self) -> bool:
        """Check if a token exists.

        Returns:
            True if token exists, False otherwise
        """
        return self.get_token() is not None


# Module-level convenience functions using default service
_default_service = TokenService()


def save_token(token: str) -> None:
    """Save token to keyring."""
    _default_service.save_token(token)


def get_token() -> str | None:
    """Get token from keyring or .env file."""
    return _default_service.get_token()


def delete_token() -> None:
    """Delete token from keyring."""
    _default_service.delete_token()


def has_token() -> bool:
    """Check if a token exists."""
    return _default_service.has_token()
