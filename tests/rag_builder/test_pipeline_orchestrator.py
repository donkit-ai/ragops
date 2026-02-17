"""Tests for rag_builder.pipeline.orchestrator."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from donkit_ragops.rag_builder.pipeline.orchestrator import (
    DOCKER_INTERNAL_URIS,
    HEALTH_ENDPOINTS,
    LOCALHOST_URIS,
    TOTAL_STEPS,
    PipelineBuildResult,
    RagPipelineOrchestrator,
    _map_provider_to_embedder_type,
    _map_provider_to_generation_type,
    _save_project_to_db,
    _update_project_status,
    _wait_for_service,
    build_quick_rag_config,
)
from donkit_ragops.schemas.config_schemas import EmbedderType, GenerationModelType


class TestPipelineBuildResult:
    def test_default_values(self):
        result = PipelineBuildResult(project_id="test-123")
        assert result.project_id == "test-123"
        assert result.rag_service_url == "http://localhost:8000"
        assert result.vectorstore_url == "http://localhost:6333"
        assert result.documents_processed == 0
        assert result.chunks_created == 0
        assert result.chunks_loaded == 0
        assert result.errors == []

    def test_to_agent_response_basic(self):
        result = PipelineBuildResult(
            project_id="my-proj",
            documents_processed=5,
            chunks_created=42,
            chunks_loaded=42,
        )
        response = result.to_agent_response()
        assert "my-proj" in response
        assert "Documents processed: 5" in response
        assert "Chunks created: 42" in response
        assert "Chunks loaded to vectorstore: 42" in response
        assert "/api/query/stream" in response
        assert "/api/query/search" in response
        assert "/api/query/evaluation" in response

    def test_to_agent_response_with_errors(self):
        result = PipelineBuildResult(
            project_id="p1",
            errors=["health check timed out", "another warning"],
        )
        response = result.to_agent_response()
        assert "Warnings (2)" in response
        assert "health check timed out" in response
        assert "another warning" in response

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
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.get_recommended_config")
    def test_builds_valid_config(self, mock_recommended):
        mock_recommended.return_value = {
            "embedder_provider": "openai",
            "embedder_model": "text-embedding-3-small",
            "generation_provider": "openai",
            "generation_model": "gpt-4.1-mini",
        }
        config = build_quick_rag_config("test-proj", "/some/path")
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

    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.get_recommended_config")
    def test_chroma_db_type(self, mock_recommended):
        mock_recommended.return_value = {
            "embedder_provider": "openai",
            "embedder_model": "text-embedding-3-small",
            "generation_provider": "openai",
            "generation_model": "gpt-4.1-mini",
        }
        config = build_quick_rag_config("proj", "/path", db_type="chroma")
        assert config.db_type == "chroma"
        assert config.database_uri == "http://chroma:8000"

    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.get_recommended_config")
    def test_milvus_db_type(self, mock_recommended):
        mock_recommended.return_value = {
            "embedder_provider": "openai",
            "embedder_model": "text-embedding-3-small",
            "generation_provider": "openai",
            "generation_model": "gpt-4.1-mini",
        }
        config = build_quick_rag_config("proj", "/path", db_type="milvus")
        assert config.db_type == "milvus"
        assert config.database_uri == "http://milvus:19530"

    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.get_recommended_config")
    def test_vertex_provider(self, mock_recommended):
        mock_recommended.return_value = {
            "embedder_provider": "vertex",
            "embedder_model": "text-multilingual-embedding-002",
            "generation_provider": "vertex",
            "generation_model": "gemini-2.5-flash",
        }
        config = build_quick_rag_config("proj", "/path")
        assert config.embedder.embedder_type == EmbedderType.VERTEX
        assert config.generation_model_type == GenerationModelType.VERTEX


class TestSaveProjectToDb:
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.close")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.kv_set")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.kv_get")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.open_db")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.get_recommended_config")
    def test_creates_new_project(self, mock_recommended, mock_open, mock_get, mock_set, mock_close):
        mock_recommended.return_value = {
            "embedder_provider": "openai",
            "embedder_model": "text-embedding-3-small",
            "generation_provider": "openai",
            "generation_model": "gpt-4.1-mini",
        }
        mock_open.return_value = MagicMock()
        mock_get.return_value = None

        config = build_quick_rag_config("test-proj", "/some/path")
        _save_project_to_db("test-proj", config)

        mock_set.assert_called_once()
        call_args = mock_set.call_args
        saved_data = json.loads(call_args[0][2])
        assert saved_data["project_id"] == "test-proj"
        assert saved_data["status"] == "building"
        assert saved_data["configuration"] is not None

    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.close")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.kv_set")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.kv_get")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.open_db")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.get_recommended_config")
    def test_updates_existing_project(
        self, mock_recommended, mock_open, mock_get, mock_set, mock_close
    ):
        mock_recommended.return_value = {
            "embedder_provider": "openai",
            "embedder_model": "text-embedding-3-small",
            "generation_provider": "openai",
            "generation_model": "gpt-4.1-mini",
        }
        mock_open.return_value = MagicMock()
        existing_state = json.dumps(
            {
                "project_id": "test-proj",
                "status": "new",
                "configuration": None,
            }
        )
        mock_get.return_value = existing_state

        config = build_quick_rag_config("test-proj", "/some/path")
        _save_project_to_db("test-proj", config)

        mock_set.assert_called_once()
        call_args = mock_set.call_args
        saved_data = json.loads(call_args[0][2])
        assert saved_data["status"] == "building"
        assert saved_data["configuration"] is not None


class TestUpdateProjectStatus:
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.close")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.kv_set")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.kv_get")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.open_db")
    def test_updates_status(self, mock_open, mock_get, mock_set, mock_close):
        mock_open.return_value = MagicMock()
        mock_get.return_value = json.dumps({"project_id": "p1", "status": "building"})

        _update_project_status("p1", "ready")

        call_args = mock_set.call_args
        saved_data = json.loads(call_args[0][2])
        assert saved_data["status"] == "ready"

    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.close")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.kv_set")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.kv_get")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.open_db")
    def test_no_op_if_project_not_found(self, mock_open, mock_get, mock_set, mock_close):
        mock_open.return_value = MagicMock()
        mock_get.return_value = None

        _update_project_status("nonexistent", "ready")
        mock_set.assert_not_called()


class TestWaitForService:
    @pytest.mark.asyncio
    async def test_returns_true_on_healthy(self):
        with patch("donkit_ragops.rag_builder.pipeline.orchestrator.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await _wait_for_service("http://localhost:6333/healthz", timeout=5)
            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self):
        import httpx as _httpx

        with patch("donkit_ragops.rag_builder.pipeline.orchestrator.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_client.get = AsyncMock(side_effect=_httpx.ConnectError("refused"))

            result = await _wait_for_service("http://localhost:6333/healthz", timeout=2)
            assert result is False


class TestConstants:
    def test_docker_internal_uris(self):
        assert DOCKER_INTERNAL_URIS["qdrant"] == "http://qdrant:6333"
        assert DOCKER_INTERNAL_URIS["chroma"] == "http://chroma:8000"
        assert DOCKER_INTERNAL_URIS["milvus"] == "http://milvus:19530"

    def test_localhost_uris(self):
        assert LOCALHOST_URIS["qdrant"] == "http://localhost:6333"
        assert LOCALHOST_URIS["chroma"] == "http://localhost:8015"
        assert LOCALHOST_URIS["milvus"] == "http://localhost:19530"

    def test_health_endpoints(self):
        assert "qdrant" in HEALTH_ENDPOINTS
        assert "rag-service" in HEALTH_ENDPOINTS

    def test_total_steps(self):
        assert TOTAL_STEPS == 8


class TestRagPipelineOrchestratorBuild:
    @pytest.mark.asyncio
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._update_project_status")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._save_project_to_db")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._wait_for_service")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.ComposeManager")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.VectorstoreService")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.ChunkingService")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.DocumentProcessor")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.build_quick_rag_config")
    async def test_successful_build(
        self,
        mock_config,
        mock_doc_proc,
        mock_chunking,
        mock_vs_service,
        mock_compose,
        mock_wait,
        mock_save,
        mock_update_status,
    ):
        # Setup mocks
        mock_rag_config = MagicMock()
        mock_rag_config.reading_format = "json"
        mock_rag_config.chunking_options.split_type = "character"
        mock_rag_config.chunking_options.chunk_size = 500
        mock_rag_config.chunking_options.chunk_overlap = 0
        mock_rag_config.embedder.embedder_type.value = "openai"
        mock_rag_config.retriever_options.collection_name = "test-proj"
        mock_config.return_value = mock_rag_config

        mock_doc_proc.process_documents = AsyncMock(
            return_value={
                "status": "success",
                "processed_count": 3,
                "output_directory": "/tmp/processed",
            }
        )

        mock_chunking.chunk_documents.return_value = {
            "status": "success",
            "output_path": "/tmp/chunked",
            "successful": [
                {"file": "a.json", "chunks_count": 10},
                {"file": "b.json", "chunks_count": 15},
            ],
            "failed": [],
        }

        mock_compose.init_project.return_value = {"status": "success"}
        mock_compose.start_service.return_value = {
            "status": "success",
            "url": "http://localhost:8000",
        }

        mock_vs_service.load = AsyncMock(return_value="Loaded 25 chunks")
        mock_wait.return_value = True

        result = await RagPipelineOrchestrator.build(
            source_path="/some/docs",
            project_id="test-proj",
        )

        assert result.project_id == "test-proj"
        assert result.documents_processed == 3
        assert result.chunks_created == 25
        assert result.chunks_loaded == 25
        assert result.errors == []
        mock_save.assert_called_once()
        mock_update_status.assert_called_with("test-proj", "ready")

    @pytest.mark.asyncio
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._update_project_status")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._save_project_to_db")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.DocumentProcessor")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.build_quick_rag_config")
    async def test_doc_processing_failure_raises(
        self, mock_config, mock_doc_proc, mock_save, mock_update_status
    ):
        mock_rag_config = MagicMock()
        mock_rag_config.reading_format = "json"
        mock_config.return_value = mock_rag_config

        mock_doc_proc.process_documents = AsyncMock(
            return_value={
                "status": "error",
                "message": "No supported files found",
            }
        )

        with pytest.raises(RuntimeError, match="Document processing failed"):
            await RagPipelineOrchestrator.build(
                source_path="/empty/dir",
                project_id="fail-proj",
            )

        mock_update_status.assert_called_with("fail-proj", "failed")

    @pytest.mark.asyncio
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._update_project_status")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._save_project_to_db")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.build_quick_rag_config")
    async def test_auto_generates_project_id(self, mock_config, mock_save, mock_update_status):
        mock_rag_config = MagicMock()
        mock_rag_config.reading_format = "json"
        mock_config.return_value = mock_rag_config

        with patch(
            "donkit_ragops.rag_builder.pipeline.orchestrator.DocumentProcessor"
        ) as mock_doc_proc:
            mock_doc_proc.process_documents = AsyncMock(
                return_value={
                    "status": "error",
                    "message": "fail",
                }
            )

            with pytest.raises(RuntimeError):
                await RagPipelineOrchestrator.build(source_path="/docs")

        # Verify a project_id was generated (from the save call)
        call_args = mock_save.call_args[0]
        generated_id = call_args[0]
        assert len(generated_id) == 12  # uuid4().hex[:12]

    @pytest.mark.asyncio
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._update_project_status")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._save_project_to_db")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._wait_for_service")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.ComposeManager")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.VectorstoreService")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.ChunkingService")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.DocumentProcessor")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.build_quick_rag_config")
    async def test_health_check_timeout_adds_warning(
        self,
        mock_config,
        mock_doc_proc,
        mock_chunking,
        mock_vs_service,
        mock_compose,
        mock_wait,
        mock_save,
        mock_update_status,
    ):
        mock_rag_config = MagicMock()
        mock_rag_config.reading_format = "json"
        mock_rag_config.chunking_options.split_type = "character"
        mock_rag_config.chunking_options.chunk_size = 500
        mock_rag_config.chunking_options.chunk_overlap = 0
        mock_rag_config.embedder.embedder_type.value = "openai"
        mock_rag_config.retriever_options.collection_name = "proj"
        mock_config.return_value = mock_rag_config

        mock_doc_proc.process_documents = AsyncMock(
            return_value={
                "status": "success",
                "processed_count": 1,
                "output_directory": "/tmp/out",
            }
        )

        mock_chunking.chunk_documents.return_value = {
            "status": "success",
            "output_path": "/tmp/chunked",
            "successful": [{"file": "a.json", "chunks_count": 5}],
            "failed": [],
        }

        mock_compose.init_project.return_value = {"status": "success"}
        mock_compose.start_service.return_value = {
            "status": "success",
            "url": "http://localhost:8000",
        }

        mock_vs_service.load = AsyncMock(return_value="Loaded")
        # First call (vectorstore) returns False, second (rag-service) returns True
        mock_wait.side_effect = [False, True]

        result = await RagPipelineOrchestrator.build(
            source_path="/docs",
            project_id="proj",
        )

        assert len(result.errors) == 1
        assert "health check timed out" in result.errors[0]

    @pytest.mark.asyncio
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._update_project_status")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._save_project_to_db")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator._wait_for_service")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.ComposeManager")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.VectorstoreService")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.ChunkingService")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.DocumentProcessor")
    @patch("donkit_ragops.rag_builder.pipeline.orchestrator.build_quick_rag_config")
    async def test_progress_callback_called(
        self,
        mock_config,
        mock_doc_proc,
        mock_chunking,
        mock_vs_service,
        mock_compose,
        mock_wait,
        mock_save,
        mock_update_status,
    ):
        mock_rag_config = MagicMock()
        mock_rag_config.reading_format = "json"
        mock_rag_config.chunking_options.split_type = "character"
        mock_rag_config.chunking_options.chunk_size = 500
        mock_rag_config.chunking_options.chunk_overlap = 0
        mock_rag_config.embedder.embedder_type.value = "openai"
        mock_rag_config.retriever_options.collection_name = "proj"
        mock_config.return_value = mock_rag_config

        mock_doc_proc.process_documents = AsyncMock(
            return_value={
                "status": "success",
                "processed_count": 1,
                "output_directory": "/tmp/out",
            }
        )

        mock_chunking.chunk_documents.return_value = {
            "status": "success",
            "output_path": "/tmp/chunked",
            "successful": [{"file": "a.json", "chunks_count": 5}],
            "failed": [],
        }

        mock_compose.init_project.return_value = {"status": "success"}
        mock_compose.start_service.return_value = {
            "status": "success",
            "url": "http://localhost:8000",
        }

        mock_vs_service.load = AsyncMock(return_value="Loaded")
        mock_wait.return_value = True

        callback = MagicMock()
        await RagPipelineOrchestrator.build(
            source_path="/docs",
            project_id="proj",
            progress_callback=callback,
        )

        assert callback.call_count == TOTAL_STEPS
        # Check that step numbers are 1..TOTAL_STEPS
        step_numbers = [call.args[0] for call in callback.call_args_list]
        assert step_numbers == list(range(1, TOTAL_STEPS + 1))
