"""Provider configuration schemas for web setup wizard."""

from __future__ import annotations

from donkit_ragops.web.models.settings import ProviderField, ProviderInfo

# Define configuration fields for each provider
PROVIDER_SCHEMAS: dict[str, ProviderInfo] = {
    "vertex": ProviderInfo(
        name="vertex",
        display_name="Vertex AI (Google Cloud)",
        description="Google's Gemini models via Vertex AI",
        has_embeddings="default",
        fields=[
            ProviderField(
                name="RAGOPS_VERTEX_CREDENTIALS",
                label="Service Account Key File",
                type="file",
                required=True,
                help_text="Path to Google Cloud service account JSON file",
                placeholder="/path/to/service-account.json",
            ),
        ],
        documentation_url="https://console.cloud.google.com/iam-admin/serviceaccounts",
    ),
    "openai": ProviderInfo(
        name="openai",
        display_name="OpenAI",
        description="ChatGPT API and compatible providers",
        has_embeddings="default",
        fields=[
            ProviderField(
                name="RAGOPS_OPENAI_API_KEY",
                label="API Key",
                type="password",
                required=True,
                help_text="OpenAI API key (usually starts with 'sk-')",
                placeholder="sk-...",
                validation_pattern=r"^sk-",
            ),
            ProviderField(
                name="RAGOPS_LLM_MODEL",
                label="Chat Model (Optional)",
                type="text",
                required=False,
                default="gpt-5",
                placeholder="gpt-5",
                help_text="LLM model to use for chat",
            ),
            ProviderField(
                name="RAGOPS_OPENAI_EMBEDDINGS_MODEL",
                label="Embeddings Model (Optional)",
                type="text",
                required=False,
                default="text-embedding-3-small",
                placeholder="text-embedding-3-small",
                help_text="Model for generating embeddings",
            ),
            ProviderField(
                name="RAGOPS_OPENAI_BASE_URL",
                label="Custom Base URL (Optional)",
                type="text",
                required=False,
                default="https://api.openai.com/v1",
                placeholder="https://api.openai.com/v1",
                help_text="For OpenAI-compatible providers",
                validation_pattern=r"^https?://",
            ),
        ],
        documentation_url="https://platform.openai.com/api-keys",
    ),
    "azure_openai": ProviderInfo(
        name="azure_openai",
        display_name="Azure OpenAI",
        description="OpenAI models via Azure",
        has_embeddings="custom",
        fields=[
            ProviderField(
                name="RAGOPS_AZURE_OPENAI_API_KEY",
                label="API Key",
                type="password",
                required=True,
                help_text="Azure OpenAI API key",
                placeholder="your-azure-api-key",
            ),
            ProviderField(
                name="RAGOPS_AZURE_OPENAI_ENDPOINT",
                label="Endpoint",
                type="text",
                required=True,
                help_text="Azure OpenAI endpoint URL",
                placeholder="https://your-resource.openai.azure.com",
                validation_pattern=r"^https://",
            ),
            ProviderField(
                name="RAGOPS_AZURE_OPENAI_API_VERSION",
                label="API Version",
                type="text",
                required=True,
                default="2024-02-15-preview",
                placeholder="2024-02-15-preview",
                help_text="Azure OpenAI API version",
            ),
            ProviderField(
                name="RAGOPS_AZURE_OPENAI_DEPLOYMENT",
                label="Chat Deployment Name",
                type="text",
                required=True,
                placeholder="gpt-5",
                help_text="Deployment name for chat completion",
            ),
            ProviderField(
                name="RAGOPS_AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT",
                label="Embeddings Deployment Name",
                type="text",
                required=True,
                default="text-embedding-ada-002",
                placeholder="text-embedding-ada-002",
                help_text="Deployment name for embeddings",
            ),
        ],
        documentation_url="https://portal.azure.com",
    ),
    "anthropic": ProviderInfo(
        name="anthropic",
        display_name="Anthropic",
        description="Claude models (requires separate embeddings provider)",
        has_embeddings=False,
        fields=[
            ProviderField(
                name="RAGOPS_ANTHROPIC_API_KEY",
                label="API Key",
                type="password",
                required=True,
                help_text="Anthropic API key (starts with 'sk-ant-')",
                placeholder="sk-ant-...",
                validation_pattern=r"^sk-ant-",
            ),
        ],
        documentation_url="https://console.anthropic.com/",
    ),
    "ollama": ProviderInfo(
        name="ollama",
        display_name="Ollama (Local)",
        description="Local LLM server (OpenAI-compatible)",
        has_embeddings=True,
        fields=[
            ProviderField(
                name="RAGOPS_OLLAMA_BASE_URL",
                label="Base URL",
                type="text",
                required=True,
                default="http://localhost:11434/v1",
                placeholder="http://localhost:11434/v1",
                help_text="Ollama server URL",
                validation_pattern=r"^https?://",
            ),
            ProviderField(
                name="RAGOPS_LLM_MODEL",
                label="Chat Model",
                type="text",
                required=True,
                default="gpt-oss:20b",
                placeholder="gpt-oss:20b",
                help_text="Model for chat completion",
            ),
            ProviderField(
                name="RAGOPS_OLLAMA_CHAT_MODEL",
                label="Chat Model (Alias)",
                type="text",
                required=False,
                help_text="Alternative chat model name",
            ),
            ProviderField(
                name="RAGOPS_OLLAMA_VISION_MODEL",
                label="Vision Model",
                type="text",
                required=False,
                placeholder="gpt-oss:20b",
                help_text="Model for image analysis (defaults to chat model)",
            ),
            ProviderField(
                name="RAGOPS_OLLAMA_EMBEDDINGS_MODEL",
                label="Embeddings Model",
                type="text",
                required=True,
                default="embeddinggemma",
                placeholder="embeddinggemma",
                help_text="Model for generating embeddings",
            ),
        ],
        documentation_url="https://ollama.ai",
    ),
    "donkit": ProviderInfo(
        name="donkit",
        display_name="Donkit",
        description="Donkit default models via Donkit API",
        has_embeddings="default",
        fields=[
            ProviderField(
                name="RAGOPS_DONKIT_API_KEY",
                label="API Key",
                type="password",
                required=True,
                help_text="Donkit API key",
                placeholder="your-donkit-api-key",
            ),
        ],
        documentation_url="https://donkit.ai/api",
    ),
    "openrouter": ProviderInfo(
        name="openrouter",
        display_name="OpenRouter",
        description="Access 100+ models via OpenRouter API (requires separate embeddings provider)",
        has_embeddings=False,
        fields=[
            ProviderField(
                name="RAGOPS_OPENAI_API_KEY",
                label="API Key",
                type="password",
                required=True,
                help_text="OpenRouter API key",
                placeholder="your-openrouter-api-key",
            ),
            ProviderField(
                name="RAGOPS_LLM_MODEL",
                label="Chat Model",
                type="text",
                required=True,
                default="openai/gpt-4o-mini",
                placeholder="openai/gpt-4o-mini",
                help_text="Chat model to use",
            ),
        ],
        documentation_url="https://openrouter.ai/keys",
    ),
}


def get_provider_schema(provider: str) -> ProviderInfo | None:
    """Get configuration schema for a provider."""
    return PROVIDER_SCHEMAS.get(provider)


def get_all_providers() -> list[ProviderInfo]:
    """Get all available provider schemas."""
    return list(PROVIDER_SCHEMAS.values())
