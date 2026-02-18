"""Embedder factory for creating embedding providers.

Supports 6 providers: openai, vertex, azure_openai, ollama, donkit.
Can be used independently of MCP servers.
"""

from __future__ import annotations

import json
import os

from langchain_core.embeddings import Embeddings
from loguru import logger


class EmbedderFactory:
    """Factory for creating embedders with support for multiple providers."""

    @staticmethod
    def create(embedder_type: str, **overrides) -> Embeddings:
        """Create an embedder with automatic credential reading from env.

        Args:
            embedder_type: openai | vertex | azure_openai | ollama | donkit
            **overrides: Override env variables (useful for testing).
                For openai: api_key, base_url, model
                For vertex: credentials_path, credentials_data
                For azure_openai: api_key, endpoint, api_version, deployment
                For ollama: api_key, base_url, model
                For donkit: api_key, base_url

        Returns:
            Configured Embeddings instance.

        Raises:
            ValueError: If required credentials are missing or embedder_type is unknown.
        """
        if embedder_type == "openai":
            return EmbedderFactory._create_openai(**overrides)
        elif embedder_type == "vertex":
            return EmbedderFactory._create_vertex(**overrides)
        elif embedder_type == "azure_openai":
            return EmbedderFactory._create_azure_openai(**overrides)
        elif embedder_type == "ollama":
            return EmbedderFactory._create_ollama(**overrides)
        elif embedder_type == "donkit":
            return EmbedderFactory._create_donkit(**overrides)
        else:
            raise ValueError(f"Unknown embedder type: {embedder_type}")

    @staticmethod
    def _create_openai(**overrides) -> Embeddings:
        from langchain_openai import OpenAIEmbeddings

        api_key = overrides.get(
            "api_key", os.getenv("OPENAI_API_KEY", os.getenv("RAGOPS_OPENAI_API_KEY"))
        )
        if not api_key:
            raise ValueError("env variable 'OPENAI_API_KEY' or 'RAGOPS_OPENAI_API_KEY' is not set")
        base_url = overrides.get(
            "base_url", os.getenv("OPENAI_BASE_URL", os.getenv("RAGOPS_OPENAI_BASE_URL"))
        )
        model = overrides.get(
            "model",
            os.getenv("OPENAI_EMBEDDINGS_MODEL", os.getenv("RAGOPS_OPENAI_EMBEDDINGS_MODEL")),
        )
        return OpenAIEmbeddings(
            api_key=api_key,
            openai_api_base=base_url,
            model=model or "text-embedding-3-small",
        )

    @staticmethod
    def _create_vertex(**overrides) -> Embeddings:
        from donkit.embeddings import get_vertexai_embeddings

        credentials_data = overrides.get("credentials_data")
        if not credentials_data:
            creds_path = overrides.get("credentials_path", os.getenv("RAGOPS_VERTEX_CREDENTIALS"))
            if not creds_path:
                raise ValueError("env variable 'RAGOPS_VERTEX_CREDENTIALS' is not set")
            with open(creds_path) as f:
                credentials_data = json.load(f)
        return get_vertexai_embeddings(credentials_data=credentials_data)

    @staticmethod
    def _create_azure_openai(**overrides) -> Embeddings:
        from langchain_openai import AzureOpenAIEmbeddings

        api_key = overrides.get(
            "api_key",
            os.getenv("AZURE_OPENAI_API_KEY", os.getenv("RAGOPS_AZURE_OPENAI_API_KEY")),
        )
        endpoint = overrides.get(
            "endpoint",
            os.getenv("AZURE_OPENAI_ENDPOINT", os.getenv("RAGOPS_AZURE_OPENAI_ENDPOINT")),
        )
        api_version = overrides.get(
            "api_version",
            os.getenv("AZURE_OPENAI_API_VERSION", os.getenv("RAGOPS_AZURE_OPENAI_API_VERSION")),
        )
        deployment = overrides.get(
            "deployment",
            os.getenv(
                "RAGOPS_AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT",
                os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"),
            ),
        )
        if not api_key or not endpoint or not api_version:
            raise ValueError(
                "env variables 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT' "
                "and 'AZURE_OPENAI_API_VERSION' must be set"
            )
        return AzureOpenAIEmbeddings(
            openai_api_key=api_key,
            azure_endpoint=endpoint,
            openai_api_version=api_version,
            deployment=deployment
            if deployment and "embed" in deployment
            else "text-embedding-ada-002",
        )

    @staticmethod
    def _create_ollama(**overrides) -> Embeddings:
        from donkit.embeddings import get_ollama_embeddings

        api_key = overrides.get("api_key", os.getenv("RAGOPS_OLLAMA_API_KEY", "ollama"))
        base_url = overrides.get(
            "base_url",
            os.getenv("RAGOPS_OLLAMA_BASE_URL", "http://localhost:11434").replace("/v1", ""),
        )
        model = overrides.get(
            "model", os.getenv("RAGOPS_OLLAMA_EMBEDDINGS_MODEL", "embeddinggemma")
        )
        logger.debug(f"Using Ollama API key: {api_key}, with base URL: {base_url}, model: {model}")
        return get_ollama_embeddings(host=base_url, model=model)

    @staticmethod
    def _create_donkit(**overrides) -> Embeddings:
        from donkit.embeddings import get_donkit_embeddings

        api_key = overrides.get("api_key", os.getenv("RAGOPS_DONKIT_API_KEY", "qwerty"))
        base_url = overrides.get(
            "base_url", os.getenv("RAGOPS_DONKIT_BASE_URL", "https://api.dev.donkit.ai")
        )
        logger.debug(f"Using Donkit API key: {api_key}, with base URL: {base_url}")
        return get_donkit_embeddings(
            base_url=base_url,
            api_token=api_key,
            provider="default",
        )


def create_embedder(embedder_type: str, **overrides) -> Embeddings:
    """Convenience function for creating embedders.

    Args:
        embedder_type: openai | vertex | azure_openai | ollama | donkit
        **overrides: Override env variables (useful for testing).

    Returns:
        Configured Embeddings instance.
    """
    return EmbedderFactory.create(embedder_type, **overrides)
