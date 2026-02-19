"""Local tools for RAG query execution."""

from __future__ import annotations

import json
from typing import Any

from donkit_ragops.agent.local_tools.tools import AgentTool
from donkit_ragops.schemas.tool_schemas import SearchQueryArgs


def tool_search_documents() -> AgentTool:
    """Tool for searching documents in the RAG vector database."""

    async def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.query import RagQueryClient

        parsed = SearchQueryArgs(**args)
        result = await RagQueryClient.search_documents(
            query=parsed.query,
            rag_service_url=parsed.rag_service_url,
            k=parsed.k,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    schema = SearchQueryArgs.model_json_schema()

    return AgentTool(
        name="search_documents",
        description=(
            "Search for relevant documents in the RAG vector database. "
            "Returns the most relevant document chunks based on the query. "
            "This tool just use retriever without any options. Result may be inaccurate. "
            "Use this tool only for testing purposes. Not for answering questions."
        ),
        parameters=schema,
        handler=_handler,
        is_async=True,
    )


def tool_get_rag_prompt() -> AgentTool:
    """Tool for getting a formatted RAG prompt with retrieved context."""

    async def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.query import RagQueryClient

        parsed = SearchQueryArgs(**args)
        result = await RagQueryClient.get_rag_prompt(
            query=parsed.query,
            rag_service_url=parsed.rag_service_url,
        )
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)
        return result

    schema = SearchQueryArgs.model_json_schema()

    return AgentTool(
        name="get_rag_prompt",
        description=(
            "Get a formatted RAG prompt with retrieved context for a query. "
            "Returns ready-to-use prompt string with relevant document chunks embedded. "
            "Use full rag-config for prompt generation. "
            "Use this tool for answering."
        ),
        parameters=schema,
        handler=_handler,
        is_async=True,
    )
