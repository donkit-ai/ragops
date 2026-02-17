"""RAG query client.

HTTP client for querying the RAG service (search and prompt endpoints).
"""

from __future__ import annotations

import httpx


class RagQueryClient:
    """Client for the RAG query service."""

    @staticmethod
    async def search_documents(
        query: str,
        rag_service_url: str = "http://localhost:8000",
        k: int = 10,
    ) -> dict:
        """Search for relevant documents in the RAG vector database.

        Args:
            query: Search query text.
            rag_service_url: RAG service base URL.
            k: Number of top results to return.

        Returns:
            Dict with query, total_results, and documents list.
        """
        url = f"{rag_service_url.rstrip('/')}/api/query/search"
        payload = {"query": query}
        params = {"k": k}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, params=params)
                response.raise_for_status()

                result = response.json()

                formatted_results: dict = {
                    "query": query,
                    "total_results": len(result) if isinstance(result, list) else 0,
                    "documents": [],
                }

                documents = result if isinstance(result, list) else []
                for doc in documents:
                    formatted_results["documents"].append(
                        {
                            "content": doc.get("page_content", "").strip(),
                            "metadata": doc.get("metadata", {}),
                        }
                    )

                return formatted_results

        except httpx.HTTPStatusError as e:
            return {
                "error": "HTTP request failed",
                "detail": f"HTTP {e.response.status_code}: {e.response.text}",
                "url": url,
            }
        except httpx.RequestError as e:
            return {
                "error": "Request error",
                "detail": str(e),
                "url": url,
                "hint": "Make sure RAG service is running and accessible",
            }
        except Exception as e:
            return {"error": "Unexpected error", "detail": str(e)}

    @staticmethod
    async def get_rag_prompt(
        query: str,
        rag_service_url: str = "http://localhost:8000",
    ) -> str | dict:
        """Get a formatted RAG prompt with retrieved context.

        Args:
            query: Query text.
            rag_service_url: RAG service base URL.

        Returns:
            Prompt string on success, or error dict on failure.
        """
        url = f"{rag_service_url.rstrip('/')}/api/query/prompt"
        payload = {"query": query}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.text

        except httpx.HTTPStatusError as e:
            return {
                "error": "HTTP request failed",
                "detail": f"HTTP {e.response.status_code}: {e.response.text}",
                "url": url,
            }
        except httpx.RequestError as e:
            return {
                "error": "Request error",
                "detail": str(e),
                "url": url,
                "hint": "Make sure RAG service is running and accessible",
            }
        except Exception as e:
            return {"error": "Unexpected error", "detail": str(e)}
