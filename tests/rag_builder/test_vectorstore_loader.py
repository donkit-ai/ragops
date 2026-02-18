"""Tests for rag_builder.vectorstore.loader."""

import json

import pytest

from donkit_ragops.rag_builder.vectorstore.loader import VectorstoreLoadResult, VectorstoreLoader


class TestVectorstoreLoadResult:
    def test_to_summary_success(self):
        result = VectorstoreLoadResult()
        result.total_chunks = 100
        result.successful_files = [("file1.json", 60), ("file2.json", 40)]

        summary = result.to_summary("my_collection", "qdrant")
        assert "my_collection" in summary
        assert "qdrant" in summary
        assert "100 chunk(s)" in summary
        assert "file1.json: 60 chunks" in summary
        assert "file2.json: 40 chunks" in summary

    def test_to_summary_with_failures(self):
        result = VectorstoreLoadResult()
        result.total_chunks = 50
        result.successful_files = [("file1.json", 50)]
        result.failed_files = [("bad.json", "invalid JSON")]

        summary = result.to_summary("coll", "chroma")
        assert "Failed: 1 file(s)" in summary
        assert "bad.json: invalid JSON" in summary

    def test_to_summary_empty(self):
        result = VectorstoreLoadResult()
        summary = result.to_summary("coll", "qdrant")
        assert "0 file(s)" in summary
        assert "0 chunk(s)" in summary


class TestVectorstoreLoaderParseChunksPath:
    def test_parse_single_json_file(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text("[]")
        result = VectorstoreLoader._parse_chunks_path(str(f))
        assert len(result) == 1
        assert result[0].name == "test.json"

    def test_parse_non_json_file_raises(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        with pytest.raises(ValueError, match="must be JSON"):
            VectorstoreLoader._parse_chunks_path(str(f))

    def test_parse_directory(self, tmp_path):
        (tmp_path / "a.json").write_text("[]")
        (tmp_path / "b.json").write_text("[]")
        (tmp_path / "c.txt").write_text("not json")
        result = VectorstoreLoader._parse_chunks_path(str(tmp_path))
        assert len(result) == 2
        names = {f.name for f in result}
        assert names == {"a.json", "b.json"}

    def test_parse_comma_separated(self, tmp_path):
        f1 = tmp_path / "one.json"
        f2 = tmp_path / "two.json"
        f1.write_text("[]")
        f2.write_text("[]")
        path_str = f"{f1},{f2}"
        result = VectorstoreLoader._parse_chunks_path(path_str)
        assert len(result) == 2

    def test_parse_nonexistent_raises(self):
        with pytest.raises(ValueError, match="Path not found"):
            VectorstoreLoader._parse_chunks_path("/nonexistent/path")

    def test_parse_empty_directory(self, tmp_path):
        result = VectorstoreLoader._parse_chunks_path(str(tmp_path))
        assert result == []
