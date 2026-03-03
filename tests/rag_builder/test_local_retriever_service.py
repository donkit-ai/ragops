"""Tests for rag_builder.retriever.service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from donkit_ragops.rag_tools.retriever.service import (
    LocalRetrieverService,
    _validate_localhost_uri,
)


def _make_rag_config(**overrides):
    """Create a minimal RagConfig for testing."""
    from donkit_ragops.schemas.config_schemas import RagConfig

    defaults = {
        "generation_model_type": "openai",
        "embedder": {"embedder_type": "openai"},
        "db_type": "qdrant",
    }
    defaults.update(overrides)
    return RagConfig(**defaults)


class TestValidateLocalhostUri:
    def test_valid_localhost(self):
        assert _validate_localhost_uri("http://localhost:6333") is None

    def test_invalid_remote(self):
        result = _validate_localhost_uri("http://qdrant:6333")
        assert result is not None
        assert "localhost" in result


class TestLocalRetrieverServiceSearch:
    @pytest.mark.asyncio
    async def test_invalid_uri_returns_error(self):
        config = _make_rag_config()
        result = await LocalRetrieverService.search(
            query="test",
            rag_config=config,
            database_uri="http://qdrant:6333",
        )
        assert "error" in result
        assert "localhost" in result["error"]

    @pytest.mark.asyncio
    async def test_embedder_creation_failure(self):
        config = _make_rag_config()
        with patch(
            "donkit_ragops.rag_tools.retriever.service.create_embedder",
            side_effect=ValueError("Missing API key"),
        ):
            result = await LocalRetrieverService.search(
                query="test",
                rag_config=config,
            )
        assert "error" in result
        assert "Failed to create embedder" in result["error"]

    @pytest.mark.asyncio
    async def test_search_failure_returns_error_with_hint(self):
        config = _make_rag_config()
        with (
            patch(
                "donkit_ragops.rag_tools.retriever.service.create_embedder",
                return_value=MagicMock(),
            ),
            patch(
                "donkit_ragops.rag_tools.retriever.service.RetrieverService.search",
                new_callable=AsyncMock,
                side_effect=Exception("Connection refused"),
            ),
        ):
            result = await LocalRetrieverService.search(
                query="test",
                rag_config=config,
            )
        assert "error" in result
        assert "hint" in result

    @pytest.mark.asyncio
    async def test_happy_path(self):
        config = _make_rag_config()
        mock_docs = [
            Document(page_content="First doc", metadata={"source": "a.pdf"}),
            Document(page_content="Second doc", metadata={"source": "b.pdf"}),
        ]
        with (
            patch(
                "donkit_ragops.rag_tools.retriever.service.create_embedder",
                return_value=MagicMock(),
            ),
            patch(
                "donkit_ragops.rag_tools.retriever.service.RetrieverService.search",
                new_callable=AsyncMock,
                return_value=mock_docs,
            ),
        ):
            result = await LocalRetrieverService.search(
                query="test query",
                rag_config=config,
                k=3,
            )
        assert result["query"] == "test query"
        assert result["total_results"] == 2
        assert result["documents"][0]["content"] == "First doc"
        assert result["documents"][0]["metadata"]["source"] == "a.pdf"
        assert result["documents"][1]["content"] == "Second doc"

    @pytest.mark.asyncio
    async def test_passes_retriever_options_from_config(self):
        config = _make_rag_config()
        config.retriever_options.collection_name = "my_collection"
        config.retriever_options.partial_search = True

        with (
            patch(
                "donkit_ragops.rag_tools.retriever.service.create_embedder",
                return_value=MagicMock(),
            ),
            patch(
                "donkit_ragops.rag_tools.retriever.service.RetrieverService.search",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_search,
        ):
            await LocalRetrieverService.search(
                query="test",
                rag_config=config,
            )
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["collection_name"] == "my_collection"
        assert call_kwargs["retriever_options"].partial_search is True


class TestToolMetadata:
    def test_tool_name_and_async(self):
        from donkit_ragops.agent.local_tools.retriever_tools import (
            tool_local_search_documents,
        )

        tool = tool_local_search_documents()
        assert tool.name == "local_search_documents"
        assert tool.is_async is True

    def test_tool_in_default_tools(self):
        from donkit_ragops.agent.agent import default_tools

        tools = default_tools()
        tool_names = [t.name for t in tools]
        assert "local_search_documents" in tool_names
