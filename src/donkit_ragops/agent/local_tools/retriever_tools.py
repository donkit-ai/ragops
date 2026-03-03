"""Local tools for direct vectorstore retrieval (no rag-service needed)."""

from __future__ import annotations

import json
from typing import Any

from donkit_ragops.agent.local_tools.tools import AgentTool
from donkit_ragops.schemas.tool_schemas import LocalSearchArgs


def tool_local_search_documents() -> AgentTool:
    """Tool for searching documents directly in a vectorstore without rag-service."""

    async def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_tools.retriever.service import LocalRetrieverService

        parsed = LocalSearchArgs(**args)
        result = await LocalRetrieverService.search(
            query=parsed.query,
            rag_config=parsed.rag_config,
            database_uri=parsed.database_uri,
            k=parsed.k,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    schema = LocalSearchArgs.model_json_schema()

    return AgentTool(
        name="local_search_documents",
        description=(
            "Search for relevant documents directly in the vectorstore "
            "without requiring rag-service to be running. "
            "Only needs a running vector database (e.g., Qdrant on localhost:6333). "
            "Pass rag_config from the project. Uses embedder, db_type, and retriever_options "
            "from the config. Ignores generation model fields. "
            "Returns document chunks with content and metadata."
        ),
        parameters=schema,
        handler=_handler,
        is_async=True,
    )
