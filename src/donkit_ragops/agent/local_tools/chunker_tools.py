"""Local tools for document chunking."""

from __future__ import annotations

import json
from typing import Any

from donkit_ragops.agent.local_tools.tools import AgentTool
from donkit_ragops.schemas.tool_schemas import ChunkDocumentsArgs


def tool_chunk_documents() -> AgentTool:
    """Tool for chunking processed documents."""

    def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.chunking import ChunkingService

        parsed = ChunkDocumentsArgs(**args)
        result = ChunkingService.chunk_documents(
            source_path=parsed.source_path,
            project_id=parsed.project_id,
            params=parsed.params,
            incremental=parsed.incremental,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    schema = ChunkDocumentsArgs.model_json_schema()

    return AgentTool(
        name="chunk_documents",
        description=(
            "Reads documents from given paths, "
            "splits them into smaller text chunks, "
            "and saves to projects/<project_id>/processed/chunked/. "
            "Supports incremental processing - only new/modified files. "
            "Support only .json"
        ),
        parameters=schema,
        handler=_handler,
    )
