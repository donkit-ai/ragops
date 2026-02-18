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

from donkit.chunker import ChunkerConfig
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from donkit_ragops.rag_builder.chunking import ChunkingService

server = FastMCP(
    "rag-chunker",
)


class ChunkDocumentsArgs(BaseModel):
    source_path: str = Field(description="Path to the source directory with processed documents")
    project_id: str = Field(
        description="Project ID to store chunked documents "
        "in projects/<project_id>/processed/chunked/"
    )
    params: ChunkerConfig
    incremental: bool = Field(
        default=True,
        description="If True, only process new/modified files. If False, reprocess all files.",
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
