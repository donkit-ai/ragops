"""Tests for donkit.rag_toolkit.pipeline.orchestrator + CLI quick_config."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.embeddings import Embeddings

from donkit.rag_toolkit.pipeline.orchestrator import (
    TOTAL_STEPS,
    PipelineBuildResult,
    RagPipelineOrchestrator,
)
from donkit.rag_toolkit.schemas.config import EmbedderType, GenerationModelType
from donkit_ragops.rag_tools.quick_config import (
    _map_provider_to_embedder_type,
    _map_provider_to_generation_type,
    build_quick_rag_config,
)


def _mock_embeddings() -> Embeddings:
    return MagicMock(spec=Embeddings)


def _mock_rag_config() -> MagicMock:
    cfg = MagicMock()
    cfg.reading_format = "json"
    cfg.reading_pipeline = "docling_llm"
    cfg.db_type = "qdrant"
    cfg.chunking_options.split_type = "character"
    cfg.chunking_options.chunk_size = 500
    cfg.chunking_options.chunk_overlap = 0
    cfg.embedder.embedder_type.value = "openai"
    cfg.retriever_options.collection_name = "test-proj"
    return cfg


class TestPipelineBuildResult:
    def test_default_values(self):
        result = PipelineBuildResult(project_id="test-123")
        assert result.project_id == "test-123"
        assert result.vectorstore_url == ""
        assert result.documents_processed == 0
        assert result.chunks_created == 0
        assert result.chunks_loaded == 0
        assert result.errors == []

    def test_to_agent_response_basic(self):
        result = PipelineBuildResult(
            project_id="my-proj",
            vectorstore_url="http://localhost:6333",
            documents_processed=5,
            chunks_created=42,
            chunks_loaded=42,
        )
        response = result.to_agent_response()
        assert "my-proj" in response
        assert "Documents processed: 5" in response
        assert "Chunks created: 42" in response
        assert "Chunks loaded to vectorstore: 42" in response
        assert "Vectorstore: http://localhost:6333" in response

    def test_to_agent_response_with_errors(self):
        result = PipelineBuildResult(
            project_id="p1",
            errors=["health check timed out", "another warning"],
        )
        response = result.to_agent_response()
        assert "Warnings (2)" in response
        assert "health check timed out" in response

    def test_to_agent_response_no_errors(self):
        result = PipelineBuildResult(project_id="p2")
        response = result.to_agent_response()
        assert "Warnings" not in response


class TestMapProviderToEmbedderType:
    def test_openai(self):
        assert _map_provider_to_embedder_type("openai") == EmbedderType.OPENAI

    def test_vertex(self):
        assert _map_provider_to_embedder_type("vertex") == EmbedderType.VERTEX

    def test_azure_openai(self):
        assert _map_provider_to_embedder_type("azure_openai") == EmbedderType.AZURE_OPENAI

    def test_ollama(self):
        assert _map_provider_to_embedder_type("ollama") == EmbedderType.OLLAMA

    def test_donkit(self):
        assert _map_provider_to_embedder_type("donkit") == EmbedderType.DONKIT

    def test_unknown_defaults_to_openai(self):
        assert _map_provider_to_embedder_type("unknown") == EmbedderType.OPENAI


class TestMapProviderToGenerationType:
    def test_openai(self):
        assert _map_provider_to_generation_type("openai") == GenerationModelType.OPENAI

    def test_vertex(self):
        assert _map_provider_to_generation_type("vertex") == GenerationModelType.VERTEX

    def test_azure_openai(self):
        assert _map_provider_to_generation_type("azure_openai") == GenerationModelType.AZURE_OPENAI

    def test_donkit(self):
        assert _map_provider_to_generation_type("donkit") == GenerationModelType.DONKIT

    def test_openrouter_maps_to_openai(self):
        assert _map_provider_to_generation_type("openrouter") == GenerationModelType.OPENAI

    def test_ollama_maps_to_openai(self):
        assert _map_provider_to_generation_type("ollama") == GenerationModelType.OPENAI

    def test_unknown_defaults_to_openai(self):
        assert _map_provider_to_generation_type("unknown") == GenerationModelType.OPENAI


class TestBuildQuickRagConfig:
    @patch("donkit_ragops.rag_tools.quick_config.get_recommended_config")
    def test_builds_valid_config(self, mock_recommended):
        mock_recommended.return_value = {
            "embedder_provider": "openai",
            "embedder_model": "text-embedding-3-small",
            "generation_provider": "openai",
            "generation_model": "gpt-4.1-mini",
        }
        config = build_quick_rag_config("test-proj")
        assert config.files_path == "projects/test-proj/processed"
        assert config.db_type == "qdrant"
        assert config.database_uri == "http://qdrant:6333"
        assert config.embedder.embedder_type == EmbedderType.OPENAI
        assert config.embedder.model_name == "text-embedding-3-small"
        assert config.generation_model_type == GenerationModelType.OPENAI
        assert config.generation_model_name == "gpt-4.1-mini"
        assert config.chunking_options.split_type == "character"
        assert config.chunking_options.chunk_size == 500
        assert config.chunking_options.chunk_overlap == 0
        assert config.retriever_options.collection_name == "test-proj"
        assert config.retriever_options.partial_search is True
        assert config.retriever_options.query_rewrite is True
        assert config.ranker is False

    @patch("donkit_ragops.rag_tools.quick_config.get_recommended_config")
    def test_chroma_db_type(self, mock_recommended):
        mock_recommended.return_value = {
            "embedder_provider": "openai",
            "embedder_model": "text-embedding-3-small",
            "generation_provider": "openai",
            "generation_model": "gpt-4.1-mini",
        }
        config = build_quick_rag_config("proj", db_type="chroma")
        assert config.db_type == "chroma"
        assert config.database_uri == "http://chroma:8000"

    @patch("donkit_ragops.rag_tools.quick_config.get_recommended_config")
    def test_milvus_db_type(self, mock_recommended):
        mock_recommended.return_value = {
            "embedder_provider": "openai",
            "embedder_model": "text-embedding-3-small",
            "generation_provider": "openai",
            "generation_model": "gpt-4.1-mini",
        }
        config = build_quick_rag_config("proj", db_type="milvus")
        assert config.db_type == "milvus"
        assert config.database_uri == "http://milvus:19530"

    @patch("donkit_ragops.rag_tools.quick_config.get_recommended_config")
    def test_vertex_provider(self, mock_recommended):
        mock_recommended.return_value = {
            "embedder_provider": "vertex",
            "embedder_model": "text-multilingual-embedding-002",
            "generation_provider": "vertex",
            "generation_model": "gemini-2.5-flash",
        }
        config = build_quick_rag_config("proj")
        assert config.embedder.embedder_type == EmbedderType.VERTEX
        assert config.generation_model_type == GenerationModelType.VERTEX


class TestConstants:
    def test_total_steps(self):
        assert TOTAL_STEPS == 4


class TestRagPipelineOrchestratorBuild:
    @pytest.mark.asyncio
    @patch("donkit.rag_toolkit.pipeline.orchestrator.VectorstoreService")
    @patch("donkit.rag_toolkit.pipeline.orchestrator.ChunkingService")
    @patch("donkit.rag_toolkit.pipeline.orchestrator.DocumentProcessor")
    @patch("donkit.rag_toolkit.pipeline.orchestrator.validate_rag_config")
    async def test_successful_build(
        self, mock_validate, mock_doc_proc, mock_chunking, mock_vs_service,
    ):
        cfg = _mock_rag_config()
        mock_validate.return_value = cfg

        mock_doc_proc.process_documents = AsyncMock(return_value={
            "status": "success", "processed_count": 3,
            "output_directory": "/tmp/processed",
        })
        mock_chunking.chunk_documents.return_value = {
            "status": "success", "output_path": "/tmp/chunked",
            "successful": [
                {"file": "a.json", "chunks_count": 10},
                {"file": "b.json", "chunks_count": 15},
            ],
            "failed": [],
        }
        mock_vs_service.load = AsyncMock(return_value="Loaded 25 chunks")

        result = await RagPipelineOrchestrator.build(
            source_path="/some/docs", rag_config=cfg,
            embeddings=_mock_embeddings(),
            database_uri="http://localhost:6333",
            project_id="test-proj",
        )
        assert result.project_id == "test-proj"
        assert result.documents_processed == 3
        assert result.chunks_created == 25
        assert result.chunks_loaded == 25
        assert result.vectorstore_url == "http://localhost:6333"
        assert result.errors == []

    @pytest.mark.asyncio
    @patch("donkit.rag_toolkit.pipeline.orchestrator.DocumentProcessor")
    @patch("donkit.rag_toolkit.pipeline.orchestrator.validate_rag_config")
    async def test_doc_processing_failure_raises(self, mock_validate, mock_doc_proc):
        cfg = _mock_rag_config()
        mock_validate.return_value = cfg
        mock_doc_proc.process_documents = AsyncMock(return_value={
            "status": "error", "message": "No supported files found",
        })
        with pytest.raises(RuntimeError, match="Document processing failed"):
            await RagPipelineOrchestrator.build(
                source_path="/empty/dir", rag_config=cfg,
                embeddings=_mock_embeddings(),
                database_uri="http://localhost:6333",
                project_id="fail-proj",
            )

    @pytest.mark.asyncio
    @patch("donkit.rag_toolkit.pipeline.orchestrator.VectorstoreService")
    @patch("donkit.rag_toolkit.pipeline.orchestrator.ChunkingService")
    @patch("donkit.rag_toolkit.pipeline.orchestrator.DocumentProcessor")
    @patch("donkit.rag_toolkit.pipeline.orchestrator.validate_rag_config")
    async def test_progress_callback_called(
        self, mock_validate, mock_doc_proc, mock_chunking, mock_vs_service,
    ):
        cfg = _mock_rag_config()
        mock_validate.return_value = cfg

        mock_doc_proc.process_documents = AsyncMock(return_value={
            "status": "success", "processed_count": 1,
            "output_directory": "/tmp/out",
        })
        mock_chunking.chunk_documents.return_value = {
            "status": "success", "output_path": "/tmp/chunked",
            "successful": [{"file": "a.json", "chunks_count": 5}], "failed": [],
        }
        mock_vs_service.load = AsyncMock(return_value="Loaded")

        callback = MagicMock()
        await RagPipelineOrchestrator.build(
            source_path="/docs", rag_config=cfg,
            embeddings=_mock_embeddings(),
            database_uri="http://localhost:6333",
            project_id="proj",
            progress_callback=callback,
        )
        assert callback.call_count == TOTAL_STEPS
        step_numbers = [call.args[0] for call in callback.call_args_list]
        assert step_numbers == list(range(1, TOTAL_STEPS + 1))
