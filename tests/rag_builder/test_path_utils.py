"""Tests for rag_builder.document_processing.path_utils."""

import unicodedata
from pathlib import Path

from donkit_ragops.rag_builder.document_processing import PathNormalizer


class TestPathNormalizer:
    def test_normalize_unicode_nfd(self):
        # macOS uses NFD normalization
        original = "caf\u00e9"  # "cafe" + combining accent
        result = PathNormalizer.normalize_unicode(original)
        assert result == unicodedata.normalize("NFD", original)

    def test_normalize_unicode_passthrough(self):
        result = PathNormalizer.normalize_unicode("simple_path.pdf")
        assert result == "simple_path.pdf"

    def test_normalize_whitespace(self):
        assert PathNormalizer.normalize_whitespace("file  name.pdf") == "file name.pdf"
        assert PathNormalizer.normalize_whitespace("a   b   c") == "a b c"
        assert PathNormalizer.normalize_whitespace("no_spaces") == "no_spaces"
        assert PathNormalizer.normalize_whitespace("single space") == "single space"

    def test_find_similar_files(self, tmp_path):
        # Create test files
        (tmp_path / "document  v2.pdf").touch()
        (tmp_path / "other_file.pdf").touch()

        # Search for normalized version
        source = tmp_path / "document v2.pdf"  # single space
        results = PathNormalizer.find_similar_files(source)

        # Should find the file with double spaces
        assert len(results) == 1
        assert results[0].name == "document  v2.pdf"

    def test_find_similar_files_exact_match(self, tmp_path):
        (tmp_path / "exact_match.pdf").touch()
        source = tmp_path / "exact_match.pdf"
        results = PathNormalizer.find_similar_files(source)
        assert len(results) == 1
        assert results[0].name == "exact_match.pdf"

    def test_find_similar_files_no_match(self, tmp_path):
        (tmp_path / "other.pdf").touch()
        source = tmp_path / "nonexistent.pdf"
        results = PathNormalizer.find_similar_files(source)
        assert len(results) == 0

    def test_find_similar_files_parent_not_exists(self):
        source = Path("/nonexistent/directory/file.pdf")
        results = PathNormalizer.find_similar_files(source)
        assert len(results) == 0

    def test_find_similar_files_custom_target(self, tmp_path):
        (tmp_path / "target  file.pdf").touch()
        source = tmp_path / "irrelevant.pdf"
        results = PathNormalizer.find_similar_files(source, target_filename="target file.pdf")
        assert len(results) == 1
