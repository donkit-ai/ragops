"""Local tools for vectorstore loading/deletion."""

from __future__ import annotations

from typing import Any

from donkit_ragops.agent.local_tools.tools import AgentTool
from donkit_ragops.schemas.tool_schemas import VectorstoreDeleteArgs, VectorstoreLoadArgs


def tool_vectorstore_load(progress_callback: Any | None = None) -> AgentTool:
    """Tool for loading chunks into a vectorstore."""

    async def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.vectorstore import VectorstoreService

        async def async_progress(current: int, total: int, message: str) -> None:
            if progress_callback:
                progress_callback(current, total, message)

        parsed = VectorstoreLoadArgs(**args)
        return await VectorstoreService.load(
            chunks_path=parsed.chunks_path,
            embedder_type=parsed.params.embedder_type,
            backend=parsed.params.backend,
            collection_name=parsed.params.collection_name,
            database_uri=parsed.params.database_uri,
            progress_callback=async_progress if progress_callback else None,
        )

    schema = VectorstoreLoadArgs.model_json_schema()

    return AgentTool(
        name="vectorstore_load",
        description=(
            "Loads document chunks from JSON files into a specified vectorstore collection. "
            "Supports: directory (all JSON files), single file, or comma-separated file list. "
            "For INCREMENTAL loading (adding new files to existing RAG): pass specific file path(s) "
            "like '/path/new_file.json' or '/path/file1.json,/path/file2.json', NOT directory path. "
            "Use list_directory on chunked folder to find which files to load."
        ),
        parameters=schema,
        handler=_handler,
        is_async=True,
    )


def tool_delete_from_vectorstore() -> AgentTool:
    """Tool for deleting documents from a vectorstore."""

    def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.vectorstore import VectorstoreService

        parsed = VectorstoreDeleteArgs(**args)
        return VectorstoreService.delete(
            embedder_type=parsed.params.embedder_type,
            backend=parsed.params.backend,
            collection_name=parsed.params.collection_name,
            database_uri=parsed.params.database_uri,
            filename=parsed.filename,
            document_id=parsed.document_id,
        )

    schema = VectorstoreDeleteArgs.model_json_schema()

    return AgentTool(
        name="delete_from_vectorstore",
        description=(
            "Delete documents from vectorstore by filename or document_id. "
            "Provide either 'filename' (e.g., 'document.pdf') OR 'document_id', not both. "
            "Returns success status and number of deleted documents."
        ),
        parameters=schema,
        handler=_handler,
    )
