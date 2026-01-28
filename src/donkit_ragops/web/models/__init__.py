"""Web API models."""

from __future__ import annotations

from donkit_ragops.web.models.settings import (
    CurrentSettingsResponse,
    ProviderConfig,
    ProviderField,
    ProviderInfo,
    ProvidersListResponse,
    ProvidersSaveRequest,
    ProvidersSaveResponse,
    ProviderTestRequest,
    ProviderTestResponse,
)

__all__ = [
    "ProviderConfig",
    "ProviderField",
    "ProviderInfo",
    "ProviderTestRequest",
    "ProviderTestResponse",
    "ProvidersSaveRequest",
    "ProvidersSaveResponse",
    "ProvidersListResponse",
    "CurrentSettingsResponse",
]
