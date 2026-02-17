"""Tests for rag_builder.vectorstore.service."""

from donkit_ragops.rag_builder.vectorstore.service import VectorstoreService, _validate_localhost_uri


class TestValidateLocalhostUri:
    def test_valid_localhost(self):
        assert _validate_localhost_uri("http://localhost:6333") is None

    def test_invalid_remote(self):
        result = _validate_localhost_uri("http://qdrant:6333")
        assert result is not None
        assert "localhost" in result


class TestVectorstoreServiceDelete:
    def test_no_identifier(self):
        result = VectorstoreService.delete(
            embedder_type="openai",
            collection_name="test",
        )
        assert "must provide" in result

    def test_both_identifiers(self):
        result = VectorstoreService.delete(
            embedder_type="openai",
            collection_name="test",
            filename="doc.pdf",
            document_id="123",
        )
        assert "only one" in result

    def test_invalid_uri(self):
        result = VectorstoreService.delete(
            embedder_type="openai",
            collection_name="test",
            database_uri="http://remote:6333",
            filename="doc.pdf",
        )
        assert "localhost" in result
