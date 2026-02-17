"""Tests for rag_builder.evaluation.metrics."""

from donkit_ragops.rag_builder.evaluation import DocumentNormalizer, RAGMetrics


class TestDocumentNormalizer:
    def test_normalize_doc_id_basic(self):
        assert DocumentNormalizer.normalize_doc_id("document.pdf") == "document"
        assert DocumentNormalizer.normalize_doc_id("file.docx") == "file"
        assert DocumentNormalizer.normalize_doc_id("data.json") == "data"

    def test_normalize_doc_id_strips_whitespace(self):
        assert DocumentNormalizer.normalize_doc_id("  file.pdf  ") == "file"

    def test_normalize_doc_id_none_returns_empty(self):
        assert DocumentNormalizer.normalize_doc_id(None) == ""

    def test_normalize_doc_id_unicode(self):
        # Non-breaking space replacement
        result = DocumentNormalizer.normalize_doc_id("doc\u00a0name.pdf")
        assert result == "doc name"

    def test_normalize_doc_id_multiple_spaces(self):
        result = DocumentNormalizer.normalize_doc_id("doc   name.pdf")
        assert result == "doc name"

    def test_normalize_doc_id_zero_width_chars(self):
        result = DocumentNormalizer.normalize_doc_id("doc\u200Bname.pdf")
        assert result == "docname"

    def test_normalize_doc_id_no_extension(self):
        assert DocumentNormalizer.normalize_doc_id("nodoc") == "nodoc"

    def test_normalize_doc_id_supported_extensions(self):
        for ext in DocumentNormalizer.SUPPORTED_EXTENSIONS:
            result = DocumentNormalizer.normalize_doc_id(f"file{ext}")
            assert result == "file", f"Failed for extension {ext}"

    def test_extract_documents_string(self):
        result = DocumentNormalizer.extract_documents("doc1.pdf, doc2.pdf")
        assert set(result) == {"doc1.pdf", "doc2.pdf"}

    def test_extract_documents_list(self):
        result = DocumentNormalizer.extract_documents(["doc1.pdf", "doc2.pdf"])
        assert set(result) == {"doc1.pdf", "doc2.pdf"}

    def test_extract_documents_json_string(self):
        result = DocumentNormalizer.extract_documents('["doc1.pdf", "doc2.pdf"]')
        assert set(result) == {"doc1.pdf", "doc2.pdf"}

    def test_extract_documents_non_string(self):
        assert DocumentNormalizer.extract_documents(123) == []
        assert DocumentNormalizer.extract_documents(None) == []

    def test_extract_documents_empty(self):
        assert DocumentNormalizer.extract_documents("") == []
        assert DocumentNormalizer.extract_documents([]) == []


class TestRAGMetrics:
    def test_perfect_retrieval(self):
        retrieved = ["doc1.pdf", "doc2.pdf"]
        relevant = ["doc1.pdf", "doc2.pdf"]
        metrics = RAGMetrics.compute_retrieval_metrics(retrieved, relevant)
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["accuracy"] == 1.0

    def test_partial_retrieval(self):
        retrieved = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
        relevant = ["doc1.pdf", "doc2.pdf"]
        metrics = RAGMetrics.compute_retrieval_metrics(retrieved, relevant)
        assert abs(metrics["precision"] - 2 / 3) < 1e-9
        assert metrics["recall"] == 1.0
        assert metrics["accuracy"] == 0.0

    def test_no_overlap(self):
        retrieved = ["doc1.pdf"]
        relevant = ["doc2.pdf"]
        metrics = RAGMetrics.compute_retrieval_metrics(retrieved, relevant)
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["accuracy"] == 0.0

    def test_empty_retrieved(self):
        retrieved = []
        relevant = ["doc1.pdf"]
        metrics = RAGMetrics.compute_retrieval_metrics(retrieved, relevant)
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["accuracy"] == 0.0

    def test_empty_relevant(self):
        retrieved = ["doc1.pdf"]
        relevant = []
        metrics = RAGMetrics.compute_retrieval_metrics(retrieved, relevant)
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["accuracy"] == 0.0

    def test_both_empty(self):
        metrics = RAGMetrics.compute_retrieval_metrics([], [])
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        # Both empty sets are equal
        assert metrics["accuracy"] == 1.0

    def test_normalizes_doc_ids(self):
        retrieved = ["doc1.json", "doc2.json"]
        relevant = ["doc1.pdf", "doc2.pdf"]
        metrics = RAGMetrics.compute_retrieval_metrics(retrieved, relevant)
        # After normalization, "doc1" and "doc2" match
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
