"""Settings API endpoints for web setup wizard."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values
from fastapi import APIRouter, HTTPException, status
from loguru import logger

from donkit_ragops.credential_checker import check_provider_credentials
from donkit_ragops.web.models.settings import (
    CurrentSettingsResponse,
    ProvidersListResponse,
    ProvidersSaveRequest,
    ProvidersSaveResponse,
    ProviderTestRequest,
    ProviderTestResponse,
)
from donkit_ragops.web.utils.provider_schemas import get_all_providers, get_provider_schema

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def mask_sensitive_value(key: str, value: str) -> str:
    """Mask sensitive values for display."""
    if "KEY" in key.upper() or "TOKEN" in key.upper():
        if len(value) > 12:
            return value[:8] + "..." + value[-4:]
        return "***"
    return value


def get_env_path() -> Path:
    """Get path to .env file (project root or current directory)."""
    # Try project root first
    project_root = Path.cwd()
    env_path = project_root / ".env"
    if env_path.exists():
        return env_path

    # Try current working directory
    env_path = Path.cwd() / ".env"
    return env_path


@router.get("/providers", response_model=ProvidersListResponse)
async def list_providers() -> ProvidersListResponse:
    """
    Get list of all available LLM providers with their configuration schemas.

    Returns provider information including required fields, documentation links,
    and whether each provider is currently configured.
    """
    env_path = get_env_path()
    providers = get_all_providers()

    # Check which providers are configured
    for provider_info in providers:
        provider_info.is_configured = check_provider_credentials(provider_info.name, env_path)

    return ProvidersListResponse(providers=providers)


@router.get("/current", response_model=CurrentSettingsResponse)
async def get_current_settings() -> CurrentSettingsResponse:
    """
    Get current provider settings with sensitive values masked.

    Returns the currently configured provider and its settings (API keys masked).
    """
    env_path = get_env_path()

    if not env_path.exists():
        return CurrentSettingsResponse(current_provider=None, settings={})

    try:
        config = dict(dotenv_values(env_path))
    except Exception as e:
        logger.error(f"Failed to load .env: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load configuration: {e}",
        ) from e

    # Get current provider
    current_provider = config.get("RAGOPS_LLM_PROVIDER")

    # Mask sensitive values
    masked_settings = {k: mask_sensitive_value(k, v) for k, v in config.items() if v}

    return CurrentSettingsResponse(current_provider=current_provider, settings=masked_settings)


@router.post("/test", response_model=ProviderTestResponse)
async def test_provider(request: ProviderTestRequest) -> ProviderTestResponse:
    """
    Test provider credentials without saving them.

    Validates that the provided credentials are correct by checking:
    - Required fields are present
    - File paths exist (for file-based credentials)
    - API key format is valid (basic validation)

    Note: This does NOT make actual API calls to the provider.
    Full validation happens when creating a session.
    """
    provider_schema = get_provider_schema(request.provider)
    if not provider_schema:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {request.provider}",
        )

    # Validate required fields are present
    for field in provider_schema.fields:
        if field.required and field.name not in request.config:
            return ProviderTestResponse(
                success=False, message=f"Missing required field: {field.label}"
            )

    # Validate field values
    for field in provider_schema.fields:
        value = request.config.get(field.name)
        if not value:
            continue

        # File path validation
        if field.type == "file":
            expanded_path = os.path.expanduser(value)
            if not Path(expanded_path).exists():
                return ProviderTestResponse(
                    success=False,
                    message=f"File not found: {value}",
                    details={"field": field.name},
                )

        # Pattern validation
        if field.validation_pattern and value:
            import re

            if not re.match(field.validation_pattern, value):
                return ProviderTestResponse(
                    success=False,
                    message=f"Invalid format for {field.label}",
                    details={"field": field.name, "expected": field.validation_pattern},
                )

    # Additional provider-specific validation
    if request.provider == "vertex":
        creds_path = request.config.get("RAGOPS_VERTEX_CREDENTIALS")
        if creds_path:
            expanded_path = os.path.expanduser(creds_path)
            if not Path(expanded_path).exists():
                return ProviderTestResponse(
                    success=False, message=f"Credentials file not found: {creds_path}"
                )

    elif request.provider == "openai":
        api_key = request.config.get("RAGOPS_OPENAI_API_KEY", "")
        if api_key and not api_key.startswith("sk-"):
            return ProviderTestResponse(
                success=False,
                message="Warning: OpenAI API keys usually start with 'sk-'",
                details={"warning": True},
            )

    elif request.provider == "anthropic":
        api_key = request.config.get("RAGOPS_ANTHROPIC_API_KEY", "")
        if api_key and not api_key.startswith("sk-ant-"):
            return ProviderTestResponse(
                success=False,
                message="Warning: Anthropic API keys usually start with 'sk-ant-'",
                details={"warning": True},
            )

    elif request.provider == "azure_openai":
        endpoint = request.config.get("RAGOPS_AZURE_OPENAI_ENDPOINT", "")
        if endpoint and not endpoint.startswith("https://"):
            return ProviderTestResponse(
                success=False, message="Azure endpoint should start with 'https://'"
            )

    return ProviderTestResponse(success=True, message="Credentials appear valid")


@router.post("/save", response_model=ProvidersSaveResponse)
async def save_provider_config(request: ProvidersSaveRequest) -> ProvidersSaveResponse:
    """
    Save provider configuration to .env file.

    Creates or updates the .env file with the provided configuration.
    If .env exists, it updates only the changed values.
    Always sets RAGOPS_LLM_PROVIDER and RAGOPS_LOG_LEVEL.
    """
    provider_schema = get_provider_schema(request.provider)
    if not provider_schema:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {request.provider}",
        )

    env_path = get_env_path()

    # Validate required fields
    for field in provider_schema.fields:
        if field.required and field.name not in request.config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field.label}",
            )

    # Add provider and log level to config
    config_to_save = dict(request.config)
    config_to_save["RAGOPS_LLM_PROVIDER"] = request.provider
    if "RAGOPS_LOG_LEVEL" not in config_to_save:
        config_to_save["RAGOPS_LOG_LEVEL"] = "ERROR"

    # For OpenRouter, set base URL
    if request.provider == "openrouter":
        config_to_save["RAGOPS_OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"

    # For Donkit, set base URL
    if request.provider == "donkit":
        config_to_save["RAGOPS_DONKIT_BASE_URL"] = "https://api.donkit.ai"

    try:
        # Check write permissions
        target_dir = env_path.parent
        if not os.access(target_dir, os.W_OK):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No write permission in: {target_dir}",
            )

        # Read existing .env if it exists
        existing_config = {}
        if env_path.exists():
            try:
                existing_config = dict(dotenv_values(env_path))
            except Exception as e:
                logger.warning(f"Could not read existing .env: {e}")

        # Create or update .env
        if not existing_config:
            # New file: create with header
            lines = [
                "# RAGOps Agent CE Configuration",
                "# Generated by web setup wizard",
                "",
            ]
            for key, value in config_to_save.items():
                lines.append(f"{key}={value}")
            lines.append("")

            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.write_text("\n".join(lines), encoding="utf-8")
        else:
            # Existing file: update only changed values
            existing_text = env_path.read_text(encoding="utf-8")
            existing_lines = existing_text.splitlines()

            remaining_updates = dict(config_to_save)
            updated_lines: list[str] = []

            for line in existing_lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in line:
                    updated_lines.append(line)
                    continue

                key = stripped.split("=", 1)[0].strip()
                if key in remaining_updates:
                    updated_lines.append(f"{key}={remaining_updates.pop(key)}")
                else:
                    updated_lines.append(line)

            # Add new keys
            if remaining_updates:
                if updated_lines and updated_lines[-1].strip():
                    updated_lines.append("")
                for key, value in remaining_updates.items():
                    updated_lines.append(f"{key}={value}")

            updated_content = "\n".join(updated_lines)
            if not updated_content.endswith("\n"):
                updated_content += "\n"

            env_path.write_text(updated_content, encoding="utf-8")

        return ProvidersSaveResponse(
            success=True,
            message=f"Configuration saved successfully for {provider_schema.display_name}",
            env_path=str(env_path),
        )

    except PermissionError as e:
        logger.error(f"Permission denied writing to {env_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: Cannot write to {env_path}",
        ) from e
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {e}",
        ) from e
