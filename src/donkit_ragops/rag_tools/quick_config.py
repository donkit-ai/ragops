"""Quick RAG config builder.

Builds a RagConfig with quick-start defaults and auto-detected providers.
This module stays in donkit_ragops because it depends on credential_checker.
"""

from __future__ import annotations

from donkit.rag_toolkit.config.validator import validate_rag_config
from donkit.rag_toolkit.schemas.config import (
    ChunkingConfig,
    Embedder,
    EmbedderType,
    GenerationModelType,
    RagConfig,
    ReadingFormat,
    RetrieverOptions,
    SplitType,
)

from donkit_ragops.credential_checker import get_recommended_config


def _map_provider_to_embedder_type(provider: str) -> EmbedderType:
    """Map credential checker provider name to EmbedderType enum."""
    mapping: dict[str, EmbedderType] = {
        "openai": EmbedderType.OPENAI,
        "vertex": EmbedderType.VERTEX,
        "azure_openai": EmbedderType.AZURE_OPENAI,
        "ollama": EmbedderType.OLLAMA,
        "donkit": EmbedderType.DONKIT,
    }
    return mapping.get(provider, EmbedderType.OPENAI)


def _map_provider_to_generation_type(provider: str) -> GenerationModelType:
    """Map credential checker provider name to GenerationModelType enum."""
    mapping: dict[str, GenerationModelType] = {
        "openai": GenerationModelType.OPENAI,
        "vertex": GenerationModelType.VERTEX,
        "azure_openai": GenerationModelType.AZURE_OPENAI,
        "donkit": GenerationModelType.DONKIT,
        # openrouter uses openai-compatible API
        "openrouter": GenerationModelType.OPENAI,
        "ollama": GenerationModelType.OPENAI,
    }
    return mapping.get(provider, GenerationModelType.OPENAI)


def build_quick_rag_config(
    project_id: str,
    db_type: str = "qdrant",
) -> RagConfig:
    """Build a RagConfig with quick-start defaults and auto-detected providers.

    Args:
        project_id: Project identifier.
        db_type: Vector database type.

    Returns:
        Fully populated RagConfig.
    """
    recommended = get_recommended_config()

    embedder_provider = recommended["embedder_provider"]
    embedder_model = recommended["embedder_model"]
    generation_provider = recommended["generation_provider"]
    generation_model = recommended["generation_model"]

    embedder_type = _map_provider_to_embedder_type(embedder_provider)
    generation_model_type = _map_provider_to_generation_type(generation_provider)

    files_path = f"projects/{project_id}/processed"

    docker_internal_uris = {
        "qdrant": "http://qdrant:6333",
        "chroma": "http://chroma:8000",
        "milvus": "http://milvus:19530",
    }
    database_uri = docker_internal_uris.get(db_type, docker_internal_uris["qdrant"])

    config = RagConfig(
        files_path=files_path,
        embedder=Embedder(
            embedder_type=embedder_type,
            model_name=embedder_model,
        ),
        db_type=db_type,
        database_uri=database_uri,
        generation_model_type=generation_model_type,
        generation_model_name=generation_model,
        chunking_options=ChunkingConfig(
            split_type=SplitType.CHARACTER,
            chunk_size=500,
            chunk_overlap=0,
        ),
        retriever_options=RetrieverOptions(
            collection_name=project_id,
            partial_search=True,
            query_rewrite=True,
        ),
        ranker=False,
        reading_format=ReadingFormat.JSON,
    )

    return validate_rag_config(config, project_id=project_id)
