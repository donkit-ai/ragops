"""Tests for rag_builder.config.validator."""

from unittest.mock import MagicMock

from donkit_ragops.rag_builder.config import RagConfigValidator, validate_rag_config
from donkit_ragops.schemas.config_schemas import RagConfig


def _make_rag_config(**kwargs) -> RagConfig:
    """Create a RagConfig with sensible defaults for testing."""
    defaults = {
        "files_path": "projects/test/processed/",
        "generation_model_type": "openai",
        "database_uri": "http://qdrant:6333",
        "embedder": {"embedder_type": "openai"},
    }
    defaults.update(kwargs)
    return RagConfig(**defaults)


class TestRagConfigValidator:
    def test_auto_generate_collection_name(self):
        config = _make_rag_config()
        assert config.retriever_options.collection_name is None

        validated = RagConfigValidator.validate_and_fix(config, project_id="test-123")
        assert validated.retriever_options.collection_name == "test-123"

    def test_preserve_existing_collection_name(self):
        config = _make_rag_config()
        config.retriever_options.collection_name = "my-collection"

        validated = RagConfigValidator.validate_and_fix(config, project_id="test-123")
        assert validated.retriever_options.collection_name == "my-collection"

    def test_milvus_collection_name_fix_starts_with_number(self):
        config = _make_rag_config(db_type="milvus")
        config.retriever_options.collection_name = "123-invalid"

        validated = RagConfigValidator.validate_and_fix(config)
        assert validated.retriever_options.collection_name == "_123-invalid"

    def test_milvus_collection_name_ok_starts_with_letter(self):
        config = _make_rag_config(db_type="milvus")
        config.retriever_options.collection_name = "valid_name"

        validated = RagConfigValidator.validate_and_fix(config)
        assert validated.retriever_options.collection_name == "valid_name"

    def test_milvus_collection_name_ok_starts_with_underscore(self):
        config = _make_rag_config(db_type="milvus")
        config.retriever_options.collection_name = "_valid_name"

        validated = RagConfigValidator.validate_and_fix(config)
        assert validated.retriever_options.collection_name == "_valid_name"

    def test_fix_milvus_collection_name_static_method(self):
        assert RagConfigValidator.fix_milvus_collection_name("123") == "_123"
        assert RagConfigValidator.fix_milvus_collection_name("abc") == "abc"
        assert RagConfigValidator.fix_milvus_collection_name("_abc") == "_abc"
        assert RagConfigValidator.fix_milvus_collection_name("-dash") == "_-dash"

    def test_no_project_id_no_collection_name(self):
        config = _make_rag_config()
        validated = RagConfigValidator.validate_and_fix(config)
        assert validated.retriever_options.collection_name is None

    def test_validate_rag_config_convenience_function(self):
        config = _make_rag_config()
        validated = validate_rag_config(config, project_id="convenience-test")
        assert validated.retriever_options.collection_name == "convenience-test"

    def test_qdrant_no_milvus_fix(self):
        config = _make_rag_config(db_type="qdrant")
        config.retriever_options.collection_name = "123-start"

        validated = RagConfigValidator.validate_and_fix(config)
        # Qdrant doesn't need the fix
        assert validated.retriever_options.collection_name == "123-start"
