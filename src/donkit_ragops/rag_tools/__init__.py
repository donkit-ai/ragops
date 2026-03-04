"""
RAG Builder - CLI extensions.

Core RAG pipeline logic lives in donkit-rag-toolkit package (donkit.rag_toolkit).
This module adds CLI-specific components: EmbedderFactory, create_embedder,
build_quick_rag_config, and DB-aware orchestrator helpers.
"""

from .embeddings import EmbedderFactory, create_embedder
from .quick_config import build_quick_rag_config

__all__ = [
    "EmbedderFactory",
    "create_embedder",
    "build_quick_rag_config",
]
