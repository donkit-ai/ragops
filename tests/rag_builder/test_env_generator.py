"""Tests for rag_builder.deployment.env_generator."""

import base64

import pytest

from donkit_ragops.rag_builder.deployment import EnvFileGenerator, LLMProviderCredentials
from donkit_ragops.schemas.config_schemas import RagConfig


def _make_rag_config(**kwargs) -> RagConfig:
    defaults = {
        "files_path": "projects/test/processed/",
        "generation_model_type": "openai",
        "database_uri": "http://qdrant:6333",
        "embedder": {"embedder_type": "openai"},
    }
    defaults.update(kwargs)
    return RagConfig(**defaults)


class TestLLMProviderCredentials:
    def test_default_values(self):
        creds = LLMProviderCredentials()
        assert creds.llm_provider is None
        assert creds.openai_api_key is None

    def test_from_env_reads_env(self, monkeypatch):
        monkeypatch.setenv("RAGOPS_LLM_PROVIDER", "openai")
        monkeypatch.setenv("RAGOPS_OPENAI_API_KEY", "test-key")
        creds = LLMProviderCredentials.from_env()
        assert creds.llm_provider == "openai"
        assert creds.openai_api_key == "test-key"


class TestEnvFileGenerator:
    def test_generate_basic(self):
        config = _make_rag_config()
        credentials = LLMProviderCredentials(
            llm_provider="openai",
            openai_api_key="test-key",
        )
        env_content = EnvFileGenerator.generate(
            project_id="test-123",
            rag_config=config,
            credentials=credentials,
        )
        assert "PROJECT_ID=test-123" in env_content
        assert "OPENAI_API_KEY=test-key" in env_content
        assert "CONFIG=" in env_content
        assert "LLM_PROVIDER=openai" in env_content

    def test_generate_container_names(self):
        config = _make_rag_config()
        env_content = EnvFileGenerator.generate(
            project_id="my-project",
            rag_config=config,
        )
        assert "QDRANT_CONTAINER_NAME=my-project_qdrant" in env_content
        assert "RAG_SERVICE_CONTAINER_NAME=my-project_rag_service" in env_content

    def test_generate_base64_config(self):
        config = _make_rag_config()
        env_content = EnvFileGenerator.generate(
            project_id="test",
            rag_config=config,
        )
        # Find CONFIG= line and verify it's base64 encoded
        for line in env_content.split("\n"):
            if line.startswith("CONFIG="):
                b64_value = line.split("=", 1)[1]
                decoded = base64.b64decode(b64_value).decode("utf-8")
                assert "files_path" in decoded
                break
        else:
            pytest.fail("CONFIG= line not found")

    def test_generate_vertex_credentials_base64(self):
        config = _make_rag_config()
        credentials = LLMProviderCredentials(
            vertex_credentials_json='{"type":"service_account"}',
        )
        env_content = EnvFileGenerator.generate(
            project_id="test",
            rag_config=config,
            credentials=credentials,
        )
        for line in env_content.split("\n"):
            if line.startswith("RAGOPS_VERTEX_CREDENTIALS_JSON="):
                b64_value = line.split("=", 1)[1]
                decoded = base64.b64decode(b64_value).decode("utf-8")
                assert "service_account" in decoded
                break
        else:
            pytest.fail("RAGOPS_VERTEX_CREDENTIALS_JSON= line not found")

    def test_generate_ollama_localhost_to_docker(self):
        config = _make_rag_config()
        credentials = LLMProviderCredentials(
            ollama_base_url="http://localhost:11434/v1",
        )
        env_content = EnvFileGenerator.generate(
            project_id="test",
            rag_config=config,
            credentials=credentials,
        )
        assert "OLLAMA_BASE_URL=http://host.docker.internal:11434/v1" in env_content

    def test_generate_raises_on_no_config(self):
        with pytest.raises(ValueError, match="Rag_config must be provided"):
            EnvFileGenerator.generate(
                project_id="test",
                rag_config=None,
            )

    def test_encode_rag_config(self):
        config = _make_rag_config()
        encoded = EnvFileGenerator.encode_rag_config(config)
        decoded = base64.b64decode(encoded).decode("utf-8")
        assert "files_path" in decoded

    def test_encode_vertex_credentials(self):
        encoded = EnvFileGenerator.encode_vertex_credentials('{"key":"value"}')
        decoded = base64.b64decode(encoded).decode("utf-8")
        assert decoded == '{"key":"value"}'

    def test_generate_default_log_level(self):
        config = _make_rag_config()
        env_content = EnvFileGenerator.generate(
            project_id="test",
            rag_config=config,
        )
        assert "LOG_LEVEL=INFO" in env_content

    def test_generate_custom_log_level(self):
        config = _make_rag_config()
        env_content = EnvFileGenerator.generate(
            project_id="test",
            rag_config=config,
            log_level="DEBUG",
        )
        assert "LOG_LEVEL=DEBUG" in env_content
