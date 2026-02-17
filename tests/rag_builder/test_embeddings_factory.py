"""Tests for rag_builder.embeddings.factory."""

import pytest

from donkit_ragops.rag_builder.embeddings import EmbedderFactory, create_embedder


class TestEmbedderFactory:
    def test_unknown_embedder_type_raises(self):
        with pytest.raises(ValueError, match="Unknown embedder type"):
            EmbedderFactory.create("nonexistent")

    def test_openai_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("RAGOPS_OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            EmbedderFactory.create("openai")

    def test_openai_with_override_api_key(self):
        embedder = EmbedderFactory.create("openai", api_key="test-key-123")
        assert embedder is not None

    def test_azure_missing_credentials_raises(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("RAGOPS_AZURE_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("RAGOPS_AZURE_OPENAI_ENDPOINT", raising=False)
        with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY"):
            EmbedderFactory.create("azure_openai")

    def test_azure_with_overrides(self):
        embedder = EmbedderFactory.create(
            "azure_openai",
            api_key="test-key",
            endpoint="https://test.openai.azure.com",
            api_version="2024-02-15",
            deployment="text-embedding-ada-002",
        )
        assert embedder is not None

    def test_vertex_missing_credentials_raises(self, monkeypatch):
        monkeypatch.delenv("RAGOPS_VERTEX_CREDENTIALS", raising=False)
        with pytest.raises(ValueError, match="RAGOPS_VERTEX_CREDENTIALS"):
            EmbedderFactory.create("vertex")

    def test_create_embedder_convenience_function_raises(self):
        with pytest.raises(ValueError, match="Unknown embedder type"):
            create_embedder("invalid_type")

    def test_create_embedder_openai_with_override(self):
        embedder = create_embedder("openai", api_key="test-key-456")
        assert embedder is not None
