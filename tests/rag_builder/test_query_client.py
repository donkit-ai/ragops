"""Tests for rag_builder.query.client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from donkit_ragops.rag_builder.query import RagQueryClient


@pytest.mark.asyncio
async def test_search_documents_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"page_content": "chunk text", "metadata": {"source": "doc.pdf"}},
    ]
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("donkit_ragops.rag_builder.query.client.httpx.AsyncClient", return_value=mock_client):
        result = await RagQueryClient.search_documents("test query")

    assert result["query"] == "test query"
    assert result["total_results"] == 1
    assert result["documents"][0]["content"] == "chunk text"


@pytest.mark.asyncio
async def test_search_documents_connection_error():
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("donkit_ragops.rag_builder.query.client.httpx.AsyncClient", return_value=mock_client):
        result = await RagQueryClient.search_documents("test query")

    assert "error" in result
    assert "hint" in result


@pytest.mark.asyncio
async def test_get_rag_prompt_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Context: ... Question: test"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("donkit_ragops.rag_builder.query.client.httpx.AsyncClient", return_value=mock_client):
        result = await RagQueryClient.get_rag_prompt("test query")

    assert isinstance(result, str)
    assert "Context" in result


@pytest.mark.asyncio
async def test_get_rag_prompt_error():
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("donkit_ragops.rag_builder.query.client.httpx.AsyncClient", return_value=mock_client):
        result = await RagQueryClient.get_rag_prompt("test query")

    assert isinstance(result, dict)
    assert "error" in result
