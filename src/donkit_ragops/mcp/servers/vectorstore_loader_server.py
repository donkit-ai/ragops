"""
MCP Server for vectorstore loading/deletion.

Thin wrapper over VectorstoreService from rag_builder.vectorstore.
"""

import warnings

# Suppress all warnings immediately, before any other imports
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="importlib._bootstrap")
warnings.simplefilter("ignore", DeprecationWarning)
import os
from typing import Literal

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from donkit_ragops.rag_builder.vectorstore import VectorstoreService


class VectorstoreParams(BaseModel):
    backend: Literal["qdrant", "chroma", "milvus"] = Field(default="qdrant")
    embedder_type: str = Field(
        description="Embedder provider (openai, vertex, azure_openai, ollama)"
    )
    collection_name: str = Field(description="Use collection name from rag config")
    database_uri: str = Field(
        default="http://localhost:6333", description="local vectorstore database URI outside docker"
    )


class VectorstoreLoadArgs(BaseModel):
    chunks_path: str = Field(
        description=(
            "Path to chunked files: directory, single JSON file, or comma-separated list. "
            "Examples: '/path/to/chunked/', '/path/file.json', "
            "'/path/file1.json,/path/file2.json'"
        )
    )
    params: VectorstoreParams


class VectorstoreDeleteArgs(BaseModel):
    filename: str | None = Field(
        default=None, description="Filename to delete from vectorstore (e.g., 'document.pdf')"
    )
    document_id: str | None = Field(
        default=None, description="Document ID to delete from vectorstore (alternative to filename)"
    )
    params: VectorstoreParams


server = FastMCP(
    "rag-vectorstore-loader",
)


@server.tool(
    name="vectorstore_load",
    description=(
        "Loads document chunks from JSON files into a specified vectorstore collection. "
        "Supports: directory (all JSON files), single file, or comma-separated file list. "
        "For INCREMENTAL loading (adding new files to existing RAG): pass specific file path(s) "
        "like '/path/new_file.json' or '/path/file1.json,/path/file2.json', NOT directory path. "
        "Use list_directory on chunked folder to find which files to load."
    ),
)
async def vectorstore_load(args: VectorstoreLoadArgs, ctx: Context) -> str:
    async def progress_callback(current: int, total: int, message: str) -> None:
        await ctx.report_progress(progress=current, total=total, message=message)

    return await VectorstoreService.load(
        chunks_path=args.chunks_path,
        embedder_type=args.params.embedder_type,
        backend=args.params.backend,
        collection_name=args.params.collection_name,
        database_uri=args.params.database_uri,
        progress_callback=progress_callback,
    )


@server.tool(
    name="delete_from_vectorstore",
    description=(
        "Delete documents from vectorstore by filename or document_id. "
        "Provide either 'filename' (e.g., 'document.pdf') OR 'document_id', not both. "
        "Returns success status and number of deleted documents."
    ),
)
async def delete_from_vectorstore(args: VectorstoreDeleteArgs, ctx: Context) -> str:
    return VectorstoreService.delete(
        embedder_type=args.params.embedder_type,
        backend=args.params.backend,
        collection_name=args.params.collection_name,
        database_uri=args.params.database_uri,
        filename=args.filename,
        document_id=args.document_id,
    )


def main() -> None:
    server.run(
        transport="stdio",
        log_level=os.getenv("RAGOPS_LOG_LEVEL", "CRITICAL"),
        show_banner=False,
    )


if __name__ == "__main__":
    main()
