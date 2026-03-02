"""
Shared configuration schemas for RAGOps MCP servers.

This module re-exports all models from donkit.rag_toolkit.schemas.config
for backward compatibility. All models are defined in the standalone
donkit-rag-toolkit package.

Shared Models:
    - EmbedderType: Enum of supported embedding providers
    - GenerationModelType: Enum of supported generation model providers
    - SplitType: Enum of text splitting methods for chunking
    - RetrieverType: Enum of supported vector database types
    - Embedder: Embedder configuration
    - ChunkingConfig: Document chunking configuration
    - RetrieverOptions: Retriever configuration options
    - RagConfig: Unified RAG configuration (base schema)
"""

from donkit.rag_toolkit.schemas.config import (
    DEFAULT_PROMPT,
    EMBEDDER_TYPE_DESCRIPTION,
    GENERATION_MODEL_TYPE_DESCRIPTION,
    MODEL_ENV_MAPPING,
    SPLITTER_DESCRIPTION,
    ChunkingConfig,
    Embedder,
    EmbedderType,
    GenerationModelType,
    ReadingFormat,
    ReadingPipeline,
    RetrieverOptions,
    RetrieverType,
    SplitType,
)
from donkit.rag_toolkit.schemas.config import (
    RagConfig as DefaultRagConfig,
)
from pydantic import model_validator

__all__ = [
    "DEFAULT_PROMPT",
    "EMBEDDER_TYPE_DESCRIPTION",
    "GENERATION_MODEL_TYPE_DESCRIPTION",
    "MODEL_ENV_MAPPING",
    "SPLITTER_DESCRIPTION",
    "ChunkingConfig",
    "Embedder",
    "EmbedderType",
    "GenerationModelType",
    "RagConfig",
    "ReadingFormat",
    "ReadingPipeline",
    "RetrieverOptions",
    "RetrieverType",
    "SplitType",
]


class RagConfig(DefaultRagConfig):
    @model_validator(mode="after")
    def validate_and_set_database_uri(self) -> "RagConfig":
        # Auto-generate database_uri from db_type if not provided
        docker_internal_uris = {
            "qdrant": "http://qdrant:6333",
            "chroma": "http://chroma:8000",
            "milvus": "http://milvus:19530",
        }

        if not self.database_uri:
            self.database_uri = docker_internal_uris.get(
                self.db_type, docker_internal_uris["qdrant"]
            )
        elif "localhost" in self.database_uri:
            raise ValueError("Database URI must be inside DOCKER")

        return self
