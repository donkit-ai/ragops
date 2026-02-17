"""RAG pipeline orchestrator.

Executes the full RAG build pipeline in a single call:
process documents -> chunk -> init compose -> start vectorstore ->
load vectors -> start rag-service.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
from donkit.chunker import ChunkerConfig
from loguru import logger

from donkit_ragops.credential_checker import get_recommended_config
from donkit_ragops.db import close, kv_get, kv_set, open_db
from donkit_ragops.rag_builder.chunking.service import ChunkingService
from donkit_ragops.rag_builder.config.validator import validate_rag_config
from donkit_ragops.rag_builder.deployment.compose_manager import ComposeManager
from donkit_ragops.rag_builder.document_processing.processor import DocumentProcessor
from donkit_ragops.rag_builder.vectorstore.service import VectorstoreService
from donkit_ragops.schemas.config_schemas import (
    ChunkingConfig,
    Embedder,
    EmbedderType,
    GenerationModelType,
    RagConfig,
    RetrieverOptions,
)

# Async progress callback: (step_number, total_steps, message) -> None
ProgressCallback = Callable[[int, int, str], object]

# Docker-internal URIs for database_uri in RagConfig
DOCKER_INTERNAL_URIS: dict[str, str] = {
    "qdrant": "http://qdrant:6333",
    "chroma": "http://chroma:8000",
    "milvus": "http://milvus:19530",
}

# Localhost URIs for vectorstore loading (outside Docker)
LOCALHOST_URIS: dict[str, str] = {
    "qdrant": "http://localhost:6333",
    "chroma": "http://localhost:8015",
    "milvus": "http://localhost:19530",
}

# Health check endpoint paths (appended to the service URL from start_service result)
_HEALTH_PATHS: dict[str, str] = {
    "qdrant": "/healthz",
    "rag-service": "/health",
}

# Kept for backward compatibility in tests and external usage
HEALTH_ENDPOINTS: dict[str, str] = {
    "qdrant": "http://localhost:6333/healthz",
    "rag-service": "http://localhost:8000/health",
}

TOTAL_STEPS = 8


@dataclass
class PipelineBuildResult:
    """Result of a complete RAG pipeline build."""

    project_id: str
    rag_service_url: str = "http://localhost:8000"
    vectorstore_url: str = "http://localhost:6333"
    documents_processed: int = 0
    chunks_created: int = 0
    chunks_loaded: int = 0
    errors: list[str] = field(default_factory=list)

    def to_agent_response(self) -> str:
        """Format result for the LLM agent."""
        lines = [
            f"RAG pipeline built successfully for project '{self.project_id}'.",
            "",
            f"Documents processed: {self.documents_processed}",
            f"Chunks created: {self.chunks_created}",
            f"Chunks loaded to vectorstore: {self.chunks_loaded}",
            "",
            f"RAG Service: {self.rag_service_url}",
            f"Vectorstore: {self.vectorstore_url}",
            "",
            "API Endpoints:",
            f"  POST {self.rag_service_url}/api/query/stream - streaming response",
            f"  POST {self.rag_service_url}/api/query/search - document search",
            f"  POST {self.rag_service_url}/api/query/evaluation - evaluation response",
            "",
            'Request body: {"query": "your question"}',
        ]
        if self.errors:
            lines.append("")
            lines.append(f"Warnings ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  - {err}")
        return "\n".join(lines)


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
    source_path: str,
    db_type: str = "qdrant",
) -> RagConfig:
    """Build a RagConfig with quick-start defaults and auto-detected providers.

    Args:
        project_id: Project identifier.
        source_path: Path to source documents (used to construct files_path).
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

    database_uri = DOCKER_INTERNAL_URIS.get(db_type, DOCKER_INTERNAL_URIS["qdrant"])

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
            split_type="character",
            chunk_size=500,
            chunk_overlap=0,
        ),
        retriever_options=RetrieverOptions(
            collection_name=project_id,
            partial_search=True,
            query_rewrite=True,
        ),
        ranker=False,
        reading_format="json",
    )

    return validate_rag_config(config, project_id=project_id)


def _save_project_to_db(project_id: str, rag_config: RagConfig) -> None:
    """Create or update project in SQLite DB."""
    db = open_db()
    try:
        key = f"project_{project_id}"
        existing = kv_get(db, key)
        if existing:
            state = json.loads(existing)
            state["configuration"] = json.loads(rag_config.model_dump_json())
            state["status"] = "building"
        else:
            state = {
                "project_id": project_id,
                "checklist": [
                    "Process documents",
                    "Chunk documents",
                    "Init Docker Compose",
                    "Start vectorstore",
                    "Load to vectorstore",
                    "Start RAG service",
                ],
                "status": "building",
                "configuration": json.loads(rag_config.model_dump_json()),
                "chunks_path": None,
                "collection_name": project_id,
                "loaded_files": [],
            }
        kv_set(db, key, json.dumps(state))
    finally:
        close(db)


def _update_project_status(project_id: str, status: str) -> None:
    """Update project status in DB."""
    db = open_db()
    try:
        key = f"project_{project_id}"
        raw = kv_get(db, key)
        if raw:
            state = json.loads(raw)
            state["status"] = status
            kv_set(db, key, json.dumps(state))
    finally:
        close(db)


async def _wait_for_service(url: str, timeout: int = 60) -> bool:
    """Poll health endpoint until ready or timeout.

    Args:
        url: Health endpoint URL.
        timeout: Maximum wait time in seconds.

    Returns:
        True if service became healthy, False on timeout.
    """
    async with httpx.AsyncClient() as client:
        for attempt in range(timeout):
            try:
                resp = await client.get(url, timeout=5)
                if resp.status_code < 500:
                    logger.debug(f"Service {url} healthy (status={resp.status_code})")
                    return True
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1)
    logger.warning(f"Service {url} not healthy after {timeout}s")
    return False


class RagPipelineOrchestrator:
    """Orchestrates the full RAG build pipeline."""

    @staticmethod
    async def build(
        source_path: str,
        project_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
        db_type: str = "qdrant",
        health_check_timeout: int = 60,
        rag_config: RagConfig | None = None,
    ) -> PipelineBuildResult:
        """Build a complete RAG pipeline from source documents.

        Steps:
        1. Auto-detect config from .env credentials (or use provided config)
        2. Create project and build RagConfig
        3. Process documents
        4. Chunk documents
        5. Init Docker Compose
        6. Start vectorstore + wait for health
        7. Load chunks to vectorstore
        8. Start RAG service + wait for health

        Args:
            source_path: Path to source files or directory.
            project_id: Optional project ID. Auto-generated if None.
            progress_callback: Optional callback for progress reporting.
            db_type: Vector database type (qdrant, chroma, milvus).
                Ignored when *rag_config* is provided (taken from config).
            health_check_timeout: Seconds to wait for services to become healthy.
            rag_config: Optional pre-built RagConfig. When provided, skips
                auto-detection and uses this config directly.

        Returns:
            PipelineBuildResult with URLs and statistics.

        Raises:
            RuntimeError: If a critical pipeline step fails.
        """
        if not project_id:
            project_id = uuid.uuid4().hex[:12]

        result = PipelineBuildResult(project_id=project_id)

        async def _progress(step: int, msg: str) -> None:
            logger.info(f"[Pipeline {project_id}] Step {step}/{TOTAL_STEPS}: {msg}")
            if progress_callback:
                cb_result = progress_callback(step, TOTAL_STEPS, msg)
                if asyncio.iscoroutine(cb_result):
                    await cb_result

        # Step 1: Build config or use provided one
        if rag_config is not None:
            await _progress(1, "Using provided RAG config")
            rag_config = validate_rag_config(rag_config, project_id=project_id)
            db_type = rag_config.db_type
        else:
            await _progress(1, "Auto-detecting provider config from .env")
            rag_config = build_quick_rag_config(project_id, source_path, db_type)

        # Step 2: Save project to DB
        await _progress(2, "Creating project")
        _save_project_to_db(project_id, rag_config)

        try:
            # Step 3: Process documents
            await _progress(3, "Processing documents")
            doc_result = await DocumentProcessor.process_documents(
                source_path=source_path,
                project_id=project_id,
                reading_format=rag_config.reading_format,
                use_llm=True,
            )

            if isinstance(doc_result, dict) and doc_result.get("status") == "error":
                raise RuntimeError(f"Document processing failed: {doc_result.get('message')}")

            result.documents_processed = doc_result.get("processed_count", 0)
            output_dir = doc_result.get("output_directory", f"projects/{project_id}/processed")

            # Step 4: Chunk documents
            await _progress(4, "Chunking documents")
            chunker_config = ChunkerConfig(
                split_type=rag_config.chunking_options.split_type,
                chunk_size=rag_config.chunking_options.chunk_size,
                chunk_overlap=rag_config.chunking_options.chunk_overlap,
            )
            chunk_result = ChunkingService.chunk_documents(
                source_path=output_dir,
                project_id=project_id,
                params=chunker_config,
                incremental=False,
            )

            if chunk_result.get("status") == "error":
                raise RuntimeError(f"Chunking failed: {chunk_result.get('message')}")

            chunks_created = sum(
                item.get("chunks_count", 0) for item in chunk_result.get("successful", [])
            )
            result.chunks_created = chunks_created
            chunks_path = chunk_result.get("output_path", "")

            # Step 5: Init Docker Compose
            await _progress(5, "Initializing Docker Compose")
            init_result = ComposeManager.init_project(
                project_id=project_id,
                rag_config=rag_config,
            )

            if init_result.get("status") == "error":
                raise RuntimeError(f"Docker Compose init failed: {init_result.get('message')}")

            # Step 6: Start vectorstore
            await _progress(6, f"Starting {db_type} vectorstore")
            start_vs_result = ComposeManager.start_service(
                service=db_type,
                project_id=project_id,
            )
            logger.debug(f"[Pipeline {project_id}] start_service({db_type}): {start_vs_result}")

            if start_vs_result.get("status") == "error":
                error_detail = start_vs_result.get("message", "") or start_vs_result.get(
                    "error", ""
                )
                raise RuntimeError(f"Vectorstore start failed: {error_detail}")

            vs_url = start_vs_result.get(
                "url", LOCALHOST_URIS.get(db_type, LOCALHOST_URIS["qdrant"])
            )
            result.vectorstore_url = vs_url

            # Wait for vectorstore health (build URL from start_service result)
            vs_health_path = _HEALTH_PATHS.get(db_type)
            if vs_health_path:
                vs_health_url = f"{vs_url}{vs_health_path}"
                healthy = await _wait_for_service(vs_health_url, timeout=health_check_timeout)
                if not healthy:
                    result.errors.append(
                        f"{db_type} health check timed out after {health_check_timeout}s"
                    )

            # Step 7: Load to vectorstore
            await _progress(7, "Loading chunks to vectorstore")
            embedder_type = rag_config.embedder.embedder_type.value
            collection_name = rag_config.retriever_options.collection_name or project_id

            load_summary = await VectorstoreService.load(
                chunks_path=chunks_path,
                embedder_type=embedder_type,
                backend=db_type,
                collection_name=collection_name,
                database_uri=vs_url,
            )

            # Parse chunks loaded count from summary
            result.chunks_loaded = result.chunks_created
            logger.debug(f"Vectorstore load summary: {load_summary}")

            # Step 8: Start RAG service
            await _progress(8, "Starting RAG service")
            start_rag_result = ComposeManager.start_service(
                service="rag-service",
                project_id=project_id,
            )

            logger.debug(f"[Pipeline {project_id}] start_service(rag-service): {start_rag_result}")

            if start_rag_result.get("status") == "error":
                error_detail = start_rag_result.get("message", "") or start_rag_result.get(
                    "error", ""
                )
                raise RuntimeError(f"RAG service start failed: {error_detail}")

            rag_url = start_rag_result.get("url", "http://localhost:8000")
            rag_health_path = _HEALTH_PATHS.get("rag-service")
            if rag_health_path:
                rag_health_url = f"{rag_url}{rag_health_path}"
                healthy = await _wait_for_service(rag_health_url, timeout=health_check_timeout)
                if not healthy:
                    result.errors.append(
                        f"RAG service health check timed out after {health_check_timeout}s"
                    )

            result.rag_service_url = rag_url

            _update_project_status(project_id, "ready")

        except Exception as exc:
            logger.error(
                f"[Pipeline {project_id}] Failed: {type(exc).__name__}: {exc}",
                exc_info=True,
            )
            _update_project_status(project_id, "failed")
            raise

        return result
