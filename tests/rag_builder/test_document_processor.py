"""Tests for rag_builder.document_processing.processor."""

from pathlib import Path

from donkit.read_engine.read_engine import ReadDocumentResult

from donkit.rag_toolkit.document_processing.processor import (
    DocumentProcessResult,
    ResolvedFiles,
    resolve_source_files,
)


def _make_read_result(output_path: str = "a.json", **kwargs) -> ReadDocumentResult:
    return ReadDocumentResult(output_path=output_path, **kwargs)


class TestDocumentProcessResult:
    def test_status_success(self):
        r = DocumentProcessResult()
        r.read_results = [_make_read_result()]
        assert r.status == "success"

    def test_status_partial_success(self):
        r = DocumentProcessResult()
        r.read_results = [_make_read_result()]
        r.failed_files = [{"file": "b.pdf", "error": "fail"}]
        assert r.status == "partial_success"

    def test_status_error(self):
        r = DocumentProcessResult()
        assert r.status == "error"

    def test_counts(self):
        r = DocumentProcessResult()
        r.read_results = [_make_read_result("a"), _make_read_result("b"), _make_read_result("c")]
        r.failed_files = [{"file": "d", "error": "x"}]
        assert r.processed_count == 3
        assert r.failed_count == 1

    def test_to_dict(self):
        r = DocumentProcessResult()
        r.read_results = [_make_read_result("a.json", page_count=5, total_llm_requests=3, total_prompt_tokens=100, total_completion_tokens=200)]
        d = r.to_dict("/out")
        assert d["status"] == "success"
        assert d["output_directory"] == "/out"
        assert d["processed_count"] == 1
        assert d["failed_count"] == 0
        assert d["total_pages"] == 5
        assert d["total_llm_requests"] == 3
        assert d["total_prompt_tokens"] == 100
        assert d["total_completion_tokens"] == 200
        assert "Output saved to: /out" in d["message"]
        assert d["processed_files"][0]["output_path"] == "a.json"

    def test_to_dict_truncates_at_10(self):
        r = DocumentProcessResult()
        r.read_results = [_make_read_result(f"f{i}.json") for i in range(20)]
        d = r.to_dict("/out")
        assert len(d["processed_files"]) == 10

    def test_to_dict_with_skipped(self):
        r = DocumentProcessResult()
        r.read_results = [_make_read_result()]
        r.skipped_files = [{"file": "b.epub", "reason": "Unsupported format: .epub"}]
        d = r.to_dict("/out")
        assert d["skipped_count"] == 1
        assert d["skipped_files"] == [{"file": "b.epub", "reason": "Unsupported format: .epub"}]
        assert "Skipped: 1 files" in d["message"]

    def test_to_dict_aggregates_totals(self):
        r = DocumentProcessResult()
        r.read_results = [
            _make_read_result("a.json", page_count=10, total_llm_requests=5, total_prompt_tokens=500, total_completion_tokens=1000),
            _make_read_result("b.json", page_count=20, total_llm_requests=10, total_prompt_tokens=1500, total_completion_tokens=3000),
        ]
        d = r.to_dict("/out")
        assert d["total_pages"] == 30
        assert d["total_llm_requests"] == 15
        assert d["total_prompt_tokens"] == 2000
        assert d["total_completion_tokens"] == 4000


class TestResolveSourceFiles:
    def test_single_supported_file(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.touch()
        result = resolve_source_files(str(f), {".pdf"})
        assert isinstance(result, ResolvedFiles)
        assert len(result.supported) == 1
        assert result.supported[0].name == "doc.pdf"
        assert len(result.skipped) == 0

    def test_single_unsupported_file(self, tmp_path):
        f = tmp_path / "doc.xyz"
        f.touch()
        result = resolve_source_files(str(f), {".pdf"})
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert ".xyz" in result["message"]

    def test_directory(self, tmp_path):
        (tmp_path / "a.pdf").touch()
        (tmp_path / "b.pdf").touch()
        (tmp_path / "c.txt").touch()
        result = resolve_source_files(str(tmp_path), {".pdf"})
        assert isinstance(result, ResolvedFiles)
        assert len(result.supported) == 2
        assert len(result.skipped) == 1
        assert result.skipped[0].name == "c.txt"

    def test_comma_separated(self, tmp_path):
        f1 = tmp_path / "a.pdf"
        f2 = tmp_path / "b.pdf"
        f1.touch()
        f2.touch()
        result = resolve_source_files(f"{f1},{f2}", {".pdf"})
        assert isinstance(result, ResolvedFiles)
        assert len(result.supported) == 2

    def test_comma_separated_with_missing(self, tmp_path):
        f1 = tmp_path / "a.pdf"
        f1.touch()
        result = resolve_source_files(f"{f1},{tmp_path / 'missing.pdf'}", {".pdf"})
        assert isinstance(result, ResolvedFiles)
        assert len(result.supported) == 1

    def test_comma_separated_with_unsupported(self, tmp_path):
        f1 = tmp_path / "a.pdf"
        f2 = tmp_path / "b.epub"
        f1.touch()
        f2.touch()
        result = resolve_source_files(f"{f1},{f2}", {".pdf"})
        assert isinstance(result, ResolvedFiles)
        assert len(result.supported) == 1
        assert len(result.skipped) == 1
        assert result.skipped[0].name == "b.epub"

    def test_nonexistent_path(self):
        result = resolve_source_files("/nonexistent/path/file.pdf", {".pdf"})
        assert isinstance(result, dict)
        assert result["status"] == "error"

    def test_fuzzy_match(self, tmp_path):
        (tmp_path / "document  v2.pdf").touch()
        result = resolve_source_files(str(tmp_path / "document v2.pdf"), {".pdf"})
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "similar_files" in result

    def test_empty_directory(self, tmp_path):
        result = resolve_source_files(str(tmp_path), {".pdf"})
        assert isinstance(result, ResolvedFiles)
        assert len(result.supported) == 0
        assert len(result.skipped) == 0
