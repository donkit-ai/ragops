"""
MCP Server for document chunking.

Thin wrapper over ChunkingService from rag_builder.chunking.
"""

from __future__ import annotations

import warnings

# Suppress all warnings immediately, before any other imports
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="importlib._bootstrap")
warnings.simplefilter("ignore", DeprecationWarning)
import json
import os

from fastmcp import FastMCP

from donkit_ragops.rag_builder.chunking import ChunkingService
from donkit_ragops.schemas.tool_schemas import ChunkDocumentsArgs

server = FastMCP(
    "rag-chunker",
)


@server.tool(
    name="chunk_documents",
    description=(
        "Reads documents from given paths, "
        "splits them into smaller text chunks, "
        "and saves to projects/<project_id>/processed/chunked/. "
        "Supports incremental processing - only new/modified files. "
        "Support only .json"
    ).strip(),
)
def chunk_documents(args: ChunkDocumentsArgs) -> str:
    result = ChunkingService.chunk_documents(
        source_path=args.source_path,
        project_id=args.project_id,
        params=args.params,
        incremental=args.incremental,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


def main() -> None:
    server.run(
        transport="stdio",
        log_level=os.getenv("RAGOPS_LOG_LEVEL", "CRITICAL"),
        show_banner=False,
    )


if __name__ == "__main__":
    main()
