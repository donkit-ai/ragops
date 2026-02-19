"""Shared Pydantic models for tool arguments.

Used by both local AgentTools and MCP servers to ensure consistent schemas.
"""

from __future__ import annotations

from typing import Literal, Self

from donkit.chunker import ChunkerConfig
from pydantic import BaseModel, Field, model_validator

from donkit_ragops.rag_builder.config import RagConfigValidator
from donkit_ragops.schemas.config_schemas import RagConfig, ReadingFormat

# ============================================================================
# Reader (process_documents)
# ============================================================================


class ProcessDocumentsArgs(BaseModel):
    source_path: str = Field(
        description=(
            "Path to source: directory, single file, or comma-separated list of files. "
            "Examples: '/path/to/folder', '/path/to/file.pdf', "
            "'/path/file1.pdf,/path/file2.docx'"
        )
    )
    project_id: str = Field(
        description="Project ID to store processed documents in projects/<project_id>/processed/"
    )
    reading_format: ReadingFormat = Field(
        default=ReadingFormat.JSON,
        description="Format in which documents will be read by LLM",
    )
    use_llm: bool = Field(
        default=True,
        description="Use LLM to process pdf, pptx, docx documents with tables, images, etc.",
    )


# ============================================================================
# Chunker (chunk_documents)
# ============================================================================


class ChunkDocumentsArgs(BaseModel):
    source_path: str = Field(description="Path to the source directory with processed documents")
    project_id: str = Field(
        description="Project ID to store chunked documents "
        "in projects/<project_id>/processed/chunked/"
    )
    params: ChunkerConfig
    incremental: bool = Field(
        default=True,
        description="If True, only process new/modified files. If False, reprocess all files.",
    )


# ============================================================================
# Vectorstore (vectorstore_load, delete_from_vectorstore)
# ============================================================================


class VectorstoreParams(BaseModel):
    backend: Literal["qdrant", "chroma", "milvus"] = Field(default="qdrant")
    embedder_type: str = Field(
        description="Embedder provider (openai, vertex, azure_openai, ollama)"
    )
    collection_name: str = Field(description="Use collection name from rag config")
    database_uri: str = Field(
        default="http://localhost:6333", description="local vectorstore database URI outside docker"
    )


class VectorstoreLoadArgs(BaseModel):
    chunks_path: str = Field(
        description=(
            "Path to chunked files: directory, single JSON file, or comma-separated list. "
            "Examples: '/path/to/chunked/', '/path/file.json', "
            "'/path/file1.json,/path/file2.json'"
        )
    )
    params: VectorstoreParams


class VectorstoreDeleteArgs(BaseModel):
    filename: str | None = Field(
        default=None, description="Filename to delete from vectorstore (e.g., 'document.pdf')"
    )
    document_id: str | None = Field(
        default=None, description="Document ID to delete from vectorstore (alternative to filename)"
    )
    params: VectorstoreParams


# ============================================================================
# Compose Manager
# ============================================================================


class InitProjectComposeArgs(BaseModel):
    project_id: str = Field(description="Project ID")
    rag_config: RagConfig = Field(description="RAG service configuration")

    @model_validator(mode="after")
    def _set_default_collection_name(self) -> Self:
        RagConfigValidator.validate_and_fix(self.rag_config, self.project_id)
        return self


class StopContainerArgs(BaseModel):
    container_id: str = Field(description="Container ID or name")


class ServicePort(BaseModel):
    service: Literal["qdrant", "chroma", "milvus", "rag-service"] = Field(
        description="Service name"
    )
    port: str = Field(
        description="Host port mapping in format 'host_port:container_port' (e.g., '6335:6333') "
        "or just host port (e.g., '6335')"
    )


class StartServiceArgs(BaseModel):
    service: Literal["qdrant", "chroma", "milvus", "rag-service"] = Field(
        description="Service name (qdrant, chroma, milvus, rag-service)"
    )
    project_id: str = Field(description="Project ID")
    detach: bool = Field(True, description="Run in detached mode")
    build: bool = Field(False, description="Build images before starting")
    custom_ports: list[ServicePort] | None = Field(
        None,
        description=(
            "Custom port mappings for services. "
            "Example: [{'service': 'qdrant', 'port': '6335:6333'}, "
            "{'service': 'rag-service', 'port': '8001:8000'}]"
        ),
    )


class StopServiceArgs(BaseModel):
    service: str = Field(description="Service name")
    project_id: str = Field(description="Project ID")
    remove_volumes: bool = Field(False, description="Remove volumes")


class ServiceStatusArgs(BaseModel):
    service: str | None = Field(None, description="Service name (optional, default: all)")
    project_id: str = Field(description="Project ID")


class GetLogsArgs(BaseModel):
    service: str = Field(description="Service name")
    tail: int = Field(100, description="Number of lines to show")
    project_id: str = Field(description="Project ID")


# ============================================================================
# Planner (rag_config_plan)
# ============================================================================


class RagConfigPlanArgs(BaseModel):
    project_id: str
    rag_config: RagConfig = Field(default_factory=RagConfig)

    @model_validator(mode="after")
    def _set_default_collection_name(self) -> Self:
        RagConfigValidator.validate_and_fix(self.rag_config, self.project_id)
        return self


# ============================================================================
# RAG Query (search_documents, get_rag_prompt)
# ============================================================================


class SearchQueryArgs(BaseModel):
    query: str = Field(description="Search query text")
    k: int = Field(default=10, description="Number of top results to return")
    rag_service_url: str = Field(
        default="http://localhost:8000",
        description="RAG service base URL (e.g., http://localhost:8000)",
    )


# ============================================================================
# RAG Evaluation (evaluate_batch)
# ============================================================================


class BatchEvaluationArgs(BaseModel):
    input_path: str = Field(
        description=(
            "Path to input file (CSV or JSON) with fields: "
            "question, answer, relevant_passage/document"
        )
    )
    project_id: str = Field(description="Project ID for organizing results")
    output_csv_path: str | None = Field(
        default=None,
        description=(
            "Path to save results CSV. Defaults to projects/<project_id>/evaluation/results.csv"
        ),
    )
    rag_service_url: str = Field(
        default="http://localhost:8000",
        description="RAG service base URL (e.g., http://localhost:8000)",
    )
    evaluation_service_url: str | None = Field(
        default=None,
        description="Optional URL for external evaluation service (for generation metrics)",
    )
    max_concurrent: int = Field(default=5, description="Max concurrent requests to RAG service")
    max_questions: int | None = Field(
        default=None, description="Limit number of questions to process (for debugging)"
    )
