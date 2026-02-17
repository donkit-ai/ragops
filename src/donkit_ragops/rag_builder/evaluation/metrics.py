"""RAG evaluation metrics.

Provides document ID normalization and retrieval metrics computation
that were previously embedded in rag_evaluation_server.py.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from loguru import logger


class DocumentNormalizer:
    """Normalization of document IDs for correct comparison."""

    SUPPORTED_EXTENSIONS = [
        ".json",
        ".pdf",
        ".docx",
        ".doc",
        ".txt",
        ".xlsx",
        ".xls",
        ".pptx",
        ".ppt",
    ]

    @staticmethod
    def normalize_doc_id(doc_id: str) -> str:
        """Normalize document ID for robust comparison.

        Applies:
        - Unicode normalization (NFKC)
        - Removal of invisible characters
        - Replacement of non-breaking spaces
        - Whitespace normalization
        - File extension removal

        Args:
            doc_id: Document ID to normalize.

        Returns:
            Normalized document ID.
        """
        if doc_id is None:
            return ""

        doc = str(doc_id).strip()

        # Unicode normalization
        doc = unicodedata.normalize("NFKC", doc)

        # Remove invisible zero-width characters
        doc = re.sub(r"[\u200B-\u200F\uFEFF]", "", doc)

        # Replace non-breaking spaces with normal
        doc = doc.replace("\u00a0", " ")

        # Normalize whitespace
        doc = re.sub(r"\s+", " ", doc)

        # Remove file extensions
        for ext in DocumentNormalizer.SUPPORTED_EXTENSIONS:
            if doc.lower().endswith(ext):
                doc = doc[: -len(ext)]
                break

        return doc.strip()

    @staticmethod
    def extract_documents(text: str | list[str] | Any) -> list[str]:
        """Extract list of document names from text or list.

        Handles strings, lists, and JSON-encoded lists.

        Args:
            text: Text or list containing document names.

        Returns:
            List of document name strings.
        """
        if isinstance(text, list):
            documents = []
            for item in text:
                documents.extend(DocumentNormalizer.extract_documents(item))
            return list(set(documents))

        if not isinstance(text, str):
            return []

        # Handle JSON string representation of list
        if text.startswith("[") and text.endswith("]"):
            try:
                loaded = json.loads(text)
                if isinstance(loaded, list):
                    return DocumentNormalizer.extract_documents(loaded)
            except json.JSONDecodeError:
                pass

        # Simple split by comma
        return [doc.strip() for doc in text.split(",") if doc.strip()]


class RAGMetrics:
    """Metrics for evaluating RAG system retrieval quality."""

    @staticmethod
    def compute_retrieval_metrics(
        retrieved_docs: list[str],
        relevant_docs: list[str],
    ) -> dict[str, float]:
        """Compute precision, recall, and accuracy for one query.

        Args:
            retrieved_docs: List of retrieved document IDs.
            relevant_docs: List of relevant (ground truth) document IDs.

        Returns:
            Dict with keys: precision, recall, accuracy.
        """
        retrieved_set = {DocumentNormalizer.normalize_doc_id(doc) for doc in retrieved_docs}
        relevant_set = {DocumentNormalizer.normalize_doc_id(doc) for doc in relevant_docs}
        logger.debug(f"Computing metrics: retrieved={retrieved_set}, relevant={relevant_set}")

        # Filter out empty strings
        retrieved_set = {d for d in retrieved_set if d}
        relevant_set = {d for d in relevant_set if d}

        intersection_count = len(retrieved_set.intersection(relevant_set))
        retrieved_count = len(retrieved_set)
        relevant_count = len(relevant_set)

        precision = intersection_count / retrieved_count if retrieved_count > 0 else 0.0
        recall = intersection_count / relevant_count if relevant_count > 0 else 0.0
        accuracy = 1.0 if retrieved_set == relevant_set else 0.0

        return {"precision": precision, "recall": recall, "accuracy": accuracy}
