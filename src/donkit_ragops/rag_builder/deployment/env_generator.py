"""Environment file generator for Docker Compose deployment.

Generates .env files with LLM provider credentials and RAG configuration
for Docker Compose services.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from pydantic import BaseModel

from donkit_ragops.schemas.config_schemas import RagConfig


class LLMProviderCredentials(BaseModel):
    """Credentials for LLM providers."""

    llm_provider: str | None = None
    llm_model: str | None = None

    # OpenAI
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_embeddings_model: str | None = None

    # Azure OpenAI
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_embeddings_deployment: str | None = None

    # Vertex AI
    vertex_credentials_json: str | None = None

    # Ollama
    ollama_base_url: str | None = None
    ollama_api_key: str | None = None
    ollama_chat_model: str | None = None
    ollama_embedding_model: str | None = None

    # Donkit
    donkit_api_key: str | None = None
    donkit_base_url: str | None = None

    @classmethod
    def from_env(cls) -> LLMProviderCredentials:
        """Read credentials from environment variables."""
        vertex_credentials_json = None
        vertex_creds_path = os.getenv("RAGOPS_VERTEX_CREDENTIALS")
        if vertex_creds_path and Path(vertex_creds_path).exists():
            try:
                creds_data = json.loads(Path(vertex_creds_path).read_text())
                vertex_credentials_json = json.dumps(creds_data, separators=(",", ":"))
            except Exception:
                pass

        return cls(
            llm_provider=os.getenv("RAGOPS_LLM_PROVIDER"),
            llm_model=os.getenv("RAGOPS_LLM_MODEL"),
            openai_api_key=os.getenv("RAGOPS_OPENAI_API_KEY"),
            openai_base_url=os.getenv("RAGOPS_OPENAI_BASE_URL"),
            openai_embeddings_model=os.getenv("RAGOPS_OPENAI_EMBEDDINGS_MODEL"),
            azure_openai_api_key=os.getenv("RAGOPS_AZURE_OPENAI_API_KEY"),
            azure_openai_endpoint=os.getenv("RAGOPS_AZURE_OPENAI_ENDPOINT"),
            azure_openai_deployment=os.getenv("RAGOPS_AZURE_OPENAI_DEPLOYMENT"),
            azure_openai_embeddings_deployment=os.getenv(
                "RAGOPS_AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"
            ),
            azure_openai_api_version=os.getenv("RAGOPS_AZURE_OPENAI_API_VERSION"),
            vertex_credentials_json=vertex_credentials_json,
            ollama_base_url=os.getenv("RAGOPS_OLLAMA_BASE_URL"),
            ollama_api_key=os.getenv("RAGOPS_OLLAMA_API_KEY"),
            ollama_chat_model=os.getenv("RAGOPS_OLLAMA_CHAT_MODEL"),
            ollama_embedding_model=os.getenv("RAGOPS_OLLAMA_EMBEDDINGS_MODEL"),
            donkit_api_key=os.getenv("RAGOPS_DONKIT_API_KEY"),
            donkit_base_url=os.getenv("RAGOPS_DONKIT_BASE_URL"),
        )


class EnvFileGenerator:
    """Generator for .env files for Docker Compose."""

    @staticmethod
    def generate(
        project_id: str,
        rag_config: RagConfig,
        credentials: LLMProviderCredentials | None = None,
        log_level: str = "INFO",
    ) -> str:
        """Generate .env file content for Docker Compose.

        Applies:
        - Base64 encoding for rag_config (avoids special character issues)
        - Base64 encoding for Vertex credentials
        - Mapping of all LLM provider credentials
        - Container naming based on project_id

        Args:
            project_id: Project identifier.
            rag_config: RAG configuration.
            credentials: LLM provider credentials. If None, reads from env.
            log_level: Logging level for services.

        Returns:
            .env file content as string.

        Raises:
            ValueError: If rag_config is not provided.
        """
        if not rag_config:
            raise ValueError("Rag_config must be provided to the env generator")

        if credentials is None:
            credentials = LLMProviderCredentials()

        lines = [
            "# =============================================================================",
            "# RAGOps Agent CE - Docker Compose Environment Variables",
            "# =============================================================================",
            "# Generated automatically by ragops-compose-manager",
            "",
            "# -----------------------------------------------------------------------------",
            "# Project Configuration",
            "# -----------------------------------------------------------------------------",
            "",
            f"PROJECT_ID={project_id}",
            f"QDRANT_CONTAINER_NAME={project_id}_qdrant",
            f"CHROMA_CONTAINER_NAME={project_id}_chroma",
            f"MILVUS_ETCD_CONTAINER_NAME={project_id}_milvus_etcd",
            f"MILVUS_MINIO_CONTAINER_NAME={project_id}_milvus_minio",
            f"MILVUS_STANDALONE_CONTAINER_NAME={project_id}_milvus_standalone",
            f"RAG_SERVICE_CONTAINER_NAME={project_id}_rag_service",
            "",
            "# -----------------------------------------------------------------------------",
            "# LLM Provider Credentials",
            "# -----------------------------------------------------------------------------",
            "",
        ]

        # LLM Provider Selection
        lines.append("# LLM Provider Selection")
        lines.append(f"LLM_PROVIDER={credentials.llm_provider or ''}")
        lines.append(f"LLM_MODEL={credentials.llm_model or ''}")
        lines.append("")

        # OpenAI
        lines.append("# OpenAI")
        lines.append(f"OPENAI_API_KEY={credentials.openai_api_key or ''}")
        lines.append(
            f"OPENAI_BASE_URL={credentials.openai_base_url or 'https://api.openai.com/v1'}"
        )
        lines.append(
            f"OPENAI_EMBEDDINGS_MODEL="
            f"{credentials.openai_embeddings_model or 'text-embedding-3-small'}"
        )
        lines.append("")

        # Azure OpenAI
        lines.append("# Azure OpenAI")
        lines.append(f"AZURE_OPENAI_API_KEY={credentials.azure_openai_api_key or ''}")
        lines.append(f"AZURE_OPENAI_AZURE_ENDPOINT={credentials.azure_openai_endpoint or ''}")
        lines.append("AZURE_OPENAI_API_VERSION=2024-02-15-preview")
        lines.append(f"AZURE_OPENAI_DEPLOYMENT={credentials.azure_openai_deployment or ''}")
        lines.append(f"AZURE_OPENAI_API_VERSION={credentials.azure_openai_api_version or ''}")
        lines.append(
            f"AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT="
            f"{credentials.azure_openai_embeddings_deployment or ''}"
        )
        lines.append("")

        # Donkit
        lines.append("# Donkit")
        lines.append(f"DONKIT_API_KEY={credentials.donkit_api_key or ''}")
        lines.append(
            f"DONKIT_BASE_URL={credentials.donkit_base_url or 'https://api.dev.donkit.ai'}"
        )

        # Vertex AI
        lines.append("# Vertex AI (Google Cloud)")
        lines.append("# Pass credentials as base64-encoded JSON")
        if credentials.vertex_credentials_json:
            encoded = EnvFileGenerator.encode_vertex_credentials(
                credentials.vertex_credentials_json
            )
            lines.append(f"RAGOPS_VERTEX_CREDENTIALS_JSON={encoded}")
        else:
            lines.append("RAGOPS_VERTEX_CREDENTIALS_JSON=")
        lines.append("")

        # Ollama
        lines.append("# Ollama (Local LLM)")
        ollama_uri = (
            credentials.ollama_base_url.replace("localhost", "host.docker.internal")
            if credentials.ollama_base_url
            else "http://host.docker.internal:11434/v1"
        )
        lines.append(f"OLLAMA_BASE_URL={ollama_uri}")
        lines.append(f"OLLAMA_API_KEY={credentials.ollama_api_key or 'ollama'}")
        lines.append(f"OLLAMA_CHAT_MODEL={credentials.ollama_chat_model or 'mistral'}")
        lines.append(
            f"OLLAMA_EMBEDDING_MODEL={credentials.ollama_embedding_model or 'nomic-embed-text'}"
        )
        lines.append("")

        lines.append(
            "# -----------------------------------------------------------------------------"
        )
        lines.append("# RAG Service Configuration")
        lines.append(
            "# -----------------------------------------------------------------------------"
        )
        lines.append("")

        # Encode rag_config to base64
        encoded_config = EnvFileGenerator.encode_rag_config(rag_config)
        lines.append("# RAG Configuration (auto-generated from RagConfig, base64-encoded)")
        lines.append(f"CONFIG={encoded_config}")

        lines.append("")
        lines.append(
            "# -----------------------------------------------------------------------------"
        )
        lines.append("# Server Settings")
        lines.append(
            "# -----------------------------------------------------------------------------"
        )
        lines.append("")

        lines.append(f"LOG_LEVEL={log_level}")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def encode_rag_config(rag_config: RagConfig) -> str:
        """Base64-encode RagConfig for safe use in .env files.

        Args:
            rag_config: RAG configuration to encode.

        Returns:
            Base64-encoded JSON string.
        """
        config_json = rag_config.model_dump_json()
        return base64.b64encode(config_json.encode("utf-8")).decode("utf-8")

    @staticmethod
    def encode_vertex_credentials(credentials_json: str) -> str:
        """Base64-encode Vertex credentials JSON.

        Args:
            credentials_json: Vertex credentials as JSON string.

        Returns:
            Base64-encoded string.
        """
        return base64.b64encode(credentials_json.encode("utf-8")).decode("utf-8")
