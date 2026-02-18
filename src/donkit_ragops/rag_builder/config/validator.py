"""RAG config validation and normalization.

Provides validation logic that was previously embedded in MCP servers
(planner_server.py and compose_manager_server.py).
"""

from __future__ import annotations

import re

from donkit_ragops.schemas.config_schemas import RagConfig


class RagConfigValidator:
    """Validator and normalizer for RagConfig."""

    @staticmethod
    def validate_and_fix(
        rag_config: RagConfig,
        project_id: str | None = None,
    ) -> RagConfig:
        """Validate and fix RagConfig.

        Applies:
        - Auto-generation of collection_name from project_id
        - Milvus naming constraints fix

        Args:
            rag_config: The RAG configuration to validate.
            project_id: Optional project ID to use as default collection_name.

        Returns:
            The validated and fixed RagConfig (mutated in place).
        """
        if project_id and not getattr(rag_config.retriever_options, "collection_name", None):
            rag_config.retriever_options.collection_name = project_id

        if rag_config.db_type == "milvus" and rag_config.retriever_options.collection_name:
            rag_config.retriever_options.collection_name = (
                RagConfigValidator.fix_milvus_collection_name(
                    rag_config.retriever_options.collection_name
                )
            )

        return rag_config

    @staticmethod
    def fix_milvus_collection_name(collection_name: str) -> str:
        """Fix collection name for Milvus (must start with [a-zA-Z_]).

        Args:
            collection_name: The collection name to fix.

        Returns:
            Fixed collection name.
        """
        if not re.match(r"^[a-zA-Z_]", collection_name):
            return f"_{collection_name}"
        return collection_name


def validate_rag_config(
    rag_config: RagConfig,
    project_id: str | None = None,
) -> RagConfig:
    """Convenience function for validating RagConfig.

    Args:
        rag_config: The RAG configuration to validate.
        project_id: Optional project ID to use as default collection_name.

    Returns:
        The validated and fixed RagConfig.
    """
    return RagConfigValidator.validate_and_fix(rag_config, project_id)
