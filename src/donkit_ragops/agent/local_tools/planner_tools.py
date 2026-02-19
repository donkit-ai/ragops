"""Local tools for RAG config planning."""

from __future__ import annotations

from typing import Any

from donkit_ragops.agent.local_tools.tools import AgentTool
from donkit_ragops.schemas.tool_schemas import RagConfigPlanArgs


def tool_rag_config_plan() -> AgentTool:
    """Tool for RAG configuration planning/validation."""

    def _handler(args: dict[str, Any]) -> str:
        parsed = RagConfigPlanArgs(**args)
        return parsed.rag_config.model_dump_json()

    schema = RagConfigPlanArgs.model_json_schema()

    return AgentTool(
        name="rag_config_plan",
        description=(
            "Suggest a RAG configuration (vectorstore/chunking/retriever/ranker) "
            "for the given project and sources. "
            "IMPORTANT: When passing rag_config parameter, ensure embedder.embedder_type "
            "is explicitly set to match user's choice (openai, vertex, or azure_openai). "
            "Do not rely on defaults."
        ),
        parameters=schema,
        handler=_handler,
    )
