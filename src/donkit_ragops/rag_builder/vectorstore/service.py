"""High-level vectorstore service.

Orchestrates embedder creation, URI validation, and vectorstore operations.
"""

from __future__ import annotations

from donkit_ragops.rag_builder.embeddings import create_embedder
from donkit_ragops.rag_builder.vectorstore.loader import (
    ProgressCallback,
    VectorstoreLoader,
)


def _validate_localhost_uri(database_uri: str) -> str | None:
    """Validate that database URI points to localhost.

    Returns error message string if invalid, None if valid.
    """
    if "localhost" not in database_uri:
        return (
            "Error: database URI arg must be outside "
            "docker like 'localhost' or '127.0.0.1' or '0.0.0.0'"
            "don`t update it in rag config, use `localhost` only in args."
        )
    return None


class VectorstoreService:
    """High-level service for vectorstore load/delete operations.

    Handles embedder creation, URI validation, and delegates to VectorstoreLoader.
    """

    @staticmethod
    async def load(
        *,
        chunks_path: str,
        embedder_type: str,
        backend: str = "qdrant",
        collection_name: str,
        database_uri: str = "http://localhost:6333",
        progress_callback: ProgressCallback | None = None,
    ) -> str:
        """Load chunks into vectorstore.

        Args:
            chunks_path: Path to chunked files (directory, file, or comma-separated).
            embedder_type: Embedder provider (openai, vertex, azure_openai, ollama, donkit).
            backend: Vectorstore backend (qdrant, chroma, milvus).
            collection_name: Collection name in vectorstore.
            database_uri: Database URI (must be localhost for local usage).
            progress_callback: Optional async callback for progress reporting.

        Returns:
            Summary string with load results.

        Raises:
            ValueError: If URI is invalid or embedder creation fails.
        """
        error = _validate_localhost_uri(database_uri)
        if error:
            return error

        try:
            embeddings = create_embedder(embedder_type)
        except ValueError as e:
            raise ValueError(f"Error initializing vectorstore: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error during initialization: {e}")

        loader = VectorstoreLoader(
            backend=backend,
            embeddings=embeddings,
            collection_name=collection_name,
            database_uri=database_uri,
        )

        result = await loader.load_from_path(chunks_path, progress_callback=progress_callback)
        return result.to_summary(collection_name, backend)

    @staticmethod
    def delete(
        *,
        embedder_type: str,
        backend: str = "qdrant",
        collection_name: str,
        database_uri: str = "http://localhost:6333",
        filename: str | None = None,
        document_id: str | None = None,
    ) -> str:
        """Delete a document from vectorstore.

        Args:
            embedder_type: Embedder provider.
            backend: Vectorstore backend.
            collection_name: Collection name.
            database_uri: Database URI (must be localhost).
            filename: Filename to delete.
            document_id: Document ID to delete.

        Returns:
            Status message string.
        """
        if not filename and not document_id:
            return "Error: must provide either 'filename' or 'document_id'"

        if filename and document_id:
            return "Error: provide only one of 'filename' or 'document_id', not both"

        error = _validate_localhost_uri(database_uri)
        if error:
            return error

        try:
            embeddings = create_embedder(embedder_type)
            loader = VectorstoreLoader(
                backend=backend,
                embeddings=embeddings,
                collection_name=collection_name,
                database_uri=database_uri,
            )
        except ValueError as e:
            return f"Error initializing vectorstore: {e}"
        except Exception as e:
            return f"Unexpected error during initialization: {e}"

        try:
            success = loader.delete_document(document_id=document_id, filename=filename)
            identifier = filename if filename else document_id

            if success:
                return (
                    f"Successfully deleted document from collection "
                    f"'{collection_name}' ({backend}):\n"
                    f"  Identifier: {identifier}"
                )
            else:
                return (
                    f"Failed to delete document from collection "
                    f"'{collection_name}' ({backend}):\n"
                    f"  Identifier: {identifier}\n"
                    f"  Document might not exist in the collection"
                )
        except Exception as e:
            return f"Error deleting document: {str(e)}"
