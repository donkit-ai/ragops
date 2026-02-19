"""
MCP Server for RAG query execution.

Thin wrapper over RagQueryClient from rag_builder.query.
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

from donkit_ragops.rag_builder.query import RagQueryClient
from donkit_ragops.schemas.tool_schemas import SearchQueryArgs

server = FastMCP(
    "rag-query",
)


@server.tool(
    name="search_documents",
    description=(
        "Search for relevant documents in the RAG vector database. "
        "Returns the most relevant document chunks based on the query."
        "This tool just use retriever without any options. Result may be inaccurate."
        "Use this tool only for testing purposes. Not for answering questions."
    ).strip(),
)
async def search_documents(args: SearchQueryArgs) -> str:
    result = await RagQueryClient.search_documents(
        query=args.query,
        rag_service_url=args.rag_service_url,
        k=args.k,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@server.tool(
    name="get_rag_prompt",
    description=(
        "Get a formatted RAG prompt with retrieved context for a query. "
        "Returns ready-to-use prompt string with relevant document chunks embedded."
        "Use full rag-config for prompt generation."
        "Use this tool for answering."
    ).strip(),
)
async def get_rag_prompt(args: SearchQueryArgs) -> str:
    result = await RagQueryClient.get_rag_prompt(
        query=args.query,
        rag_service_url=args.rag_service_url,
    )
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, indent=2)
    return result


def main() -> None:
    server.run(
        transport="stdio",
        log_level=os.getenv("RAGOPS_LOG_LEVEL", "CRITICAL"),
        show_banner=False,
    )


if __name__ == "__main__":
    main()
