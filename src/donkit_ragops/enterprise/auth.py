"""Token management for enterprise mode.

Uses keyring for secure token storage, with fallback to .env file.
Tokens are NEVER:
- Logged to console/files
- Passed to LLM prompts
"""

from __future__ import annotations

from pathlib import Path

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


def _save_token_to_env(token: str) -> None:
    """Save token to .env file as RAGOPS_DONKIT_API_KEY."""
    env_path = Path.cwd() / ".env"

    try:
        # Read existing .env or create new one
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
        else:
            lines = []

        updated_lines = []
        token_key_found = False

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                updated_lines.append(line)
            else:
                key = stripped.split("=", 1)[0].strip()
                if key == "RAGOPS_DONKIT_API_KEY":
                    # Replace existing token
                    updated_lines.append(f"RAGOPS_DONKIT_API_KEY={token}")
                    token_key_found = True
                else:
                    updated_lines.append(line)

        # Add token if not found
        if not token_key_found:
            if updated_lines and updated_lines[-1].strip():
                updated_lines.append("")
            updated_lines.append(f"RAGOPS_DONKIT_API_KEY={token}")

        content = "\n".join(updated_lines)
        if not content.endswith("\n"):
            content += "\n"

        env_path.write_text(content, encoding="utf-8")
    except Exception:
        # Silently ignore errors (file might be read-only, etc.)
        pass


def _delete_token_from_env() -> None:
    """Delete token from .env file (RAGOPS_DONKIT_API_KEY and related keys)."""
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
        updated_lines = []

        # Remove all Donkit-related token keys
        token_keys = {
            "RAGOPS_DONKIT_API_KEY",
            "DONKIT_API_KEY",
        }

        for line in lines:
            stripped = line.strip()
            # Keep lines that are not token-related
            if not stripped or stripped.startswith("#") or "=" not in line:
                updated_lines.append(line)
            else:
                key = stripped.split("=", 1)[0].strip()
                if key not in token_keys:
                    updated_lines.append(line)

        content = "\n".join(updated_lines)
        if not content.endswith("\n"):
            content += "\n"

        env_path.write_text(content, encoding="utf-8")
    except Exception:
        # Silently ignore errors (file might be read-only, etc.)
        pass


class TokenService:
    """Service for managing enterprise API tokens using keyring."""

    def __init__(self, service_name: str = SERVICE_NAME):
        self.service_name = service_name

    def save_token(self, token: str) -> None:
        """Save token to keyring and .env file.

        Args:
            token: The API token to save
        """
        keyring.set_password(self.service_name, TOKEN_KEY, token)
        # Also save to .env file
        _save_token_to_env(token)

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
        """Delete token from keyring and .env file."""
        try:
            keyring.delete_password(self.service_name, TOKEN_KEY)
        except keyring.errors.PasswordDeleteError:
            pass

        # Also delete from .env file
        _delete_token_from_env()

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
