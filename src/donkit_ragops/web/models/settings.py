"""Pydantic models for settings API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ProviderField(BaseModel):
    """Defines a configuration field for a provider."""

    name: str = Field(..., description="Environment variable name (e.g., RAGOPS_OPENAI_API_KEY)")
    label: str = Field(..., description="Human-readable label for the field")
    type: Literal["text", "password", "file"] = Field(
        ..., description="Input type (text, password, or file path)"
    )
    required: bool = Field(..., description="Whether this field is required")
    default: str | None = Field(None, description="Default value if any")
    placeholder: str | None = Field(None, description="Placeholder text")
    help_text: str | None = Field(None, description="Help text explaining this field")
    validation_pattern: str | None = Field(None, description="Regex pattern for validation")


class ProviderInfo(BaseModel):
    """Information about a provider and its configuration requirements."""

    name: str = Field(..., description="Provider identifier (e.g., 'openai', 'vertex')")
    display_name: str = Field(..., description="Display name (e.g., 'OpenAI')")
    description: str = Field(..., description="Provider description")
    fields: list[ProviderField] = Field(..., description="Configuration fields required")
    has_embeddings: bool | Literal["default", "custom"] = Field(
        ..., description="Whether provider supports embeddings"
    )
    is_configured: bool = Field(
        False, description="Whether provider has valid credentials configured"
    )
    documentation_url: str | None = Field(None, description="Link to provider documentation")


class ProvidersListResponse(BaseModel):
    """Response listing all available providers."""

    providers: list[ProviderInfo] = Field(..., description="List of available providers")


class ProviderConfig(BaseModel):
    """Configuration values for a specific provider."""

    provider: str = Field(..., description="Provider name (e.g., 'openai')")
    config: dict[str, str] = Field(
        ..., description="Configuration key-value pairs (e.g., {'RAGOPS_OPENAI_API_KEY': 'sk-...'})"
    )


class CurrentSettingsResponse(BaseModel):
    """Response with current provider settings."""

    current_provider: str | None = Field(None, description="Currently configured provider")
    settings: dict[str, str] = Field(..., description="Current settings (masked sensitive values)")


class ProviderTestRequest(BaseModel):
    """Request to test provider credentials."""

    provider: str = Field(..., description="Provider to test (e.g., 'openai')")
    config: dict[str, str] = Field(..., description="Configuration to test")


class ProviderTestResponse(BaseModel):
    """Response from testing provider credentials."""

    success: bool = Field(..., description="Whether credentials are valid")
    message: str = Field(..., description="Success or error message")
    details: dict[str, Any] | None = Field(None, description="Additional details if any")


class ProvidersSaveRequest(BaseModel):
    """Request to save provider configuration."""

    provider: str = Field(..., description="Provider to configure (e.g., 'openai')")
    config: dict[str, str] = Field(..., description="Configuration to save")


class ProvidersSaveResponse(BaseModel):
    """Response from saving provider configuration."""

    success: bool = Field(..., description="Whether save was successful")
    message: str = Field(..., description="Success or error message")
    env_path: str | None = Field(None, description="Path to .env file that was updated")
