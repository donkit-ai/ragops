"""High-level local retriever service — CLI compatibility shim.

Provides a CLI-compatible API that accepts RagConfig and creates
embeddings internally using EmbedderFactory. Searches vectorstore
directly without requiring rag-service.

For the standalone API that accepts Embeddings directly,
use donkit.rag_toolkit.retriever.service.
"""

from __future__ import annotations

from donkit.rag_toolkit.retriever.service import RetrieverService

from donkit_ragops.rag_tools.embeddings import create_embedder
from donkit_ragops.schemas.config_schemas import RagConfig


def _validate_localhost_uri(database_uri: str) -> str | None:
    """Validate that database URI points to localhost.

    Returns error message string if invalid, None if valid.
    """
    if "localhost" not in database_uri:
        return (
            "Error: database URI must use 'localhost' for local retrieval. "
            "Don't use docker-internal URIs like 'qdrant:6333'."
        )
    return None


class LocalRetrieverService:
    """High-level service for local vectorstore search.

    CLI-compatible version that handles embedder creation from RagConfig.
    Does not require rag-service — only a running vector database.
    """

    @staticmethod
    async def search(
        *,
        query: str,
        rag_config: RagConfig,
        database_uri: str = "http://localhost:6333",
        k: int = 5,
    ) -> dict:
        """Search for documents in a vectorstore locally.

        Args:
            query: Search query string.
            rag_config: RAG configuration (embedder, db_type, retriever_options used).
            database_uri: Database URI (must be localhost for local usage).
            k: Maximum number of documents to return.

        Returns:
            Dict with query, total_results, and documents list.
        """
        error = _validate_localhost_uri(database_uri)
        if error:
            return {"error": error}

        embedder_type = str(rag_config.embedder.embedder_type)

        try:
            embeddings = create_embedder(embedder_type)
        except ValueError as e:
            return {"error": f"Failed to create embedder: {e}"}
        except Exception as e:
            return {"error": f"Unexpected error creating embedder: {e}"}

        collection_name = rag_config.retriever_options.collection_name or "default"

        try:
            docs = await RetrieverService.search(
                query=query,
                embeddings=embeddings,
                backend=rag_config.db_type,
                collection_name=collection_name,
                database_uri=database_uri,
                k=k,
                retriever_options=rag_config.retriever_options,
            )
        except Exception as e:
            return {
                "error": f"Search failed: {e}",
                "hint": ("Make sure the vectorstore is running and the collection exists."),
            }

        return {
            "query": query,
            "total_results": len(docs),
            "documents": [
                {
                    "content": doc.page_content.strip(),
                    "metadata": doc.metadata,
                }
                for doc in docs
            ],
        }
