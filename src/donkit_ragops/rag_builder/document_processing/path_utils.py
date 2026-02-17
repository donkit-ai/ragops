"""Path normalization utilities for cross-platform compatibility.

Handles Unicode normalization (macOS NFD), whitespace normalization,
and fuzzy file search.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


class PathNormalizer:
    """Utilities for path normalization (macOS, Windows compatibility)."""

    @staticmethod
    def normalize_unicode(path_str: str) -> str:
        """Unicode normalization (NFD for macOS compatibility).

        Args:
            path_str: Path string to normalize.

        Returns:
            Normalized path string.
        """
        return unicodedata.normalize("NFD", path_str)

    @staticmethod
    def normalize_whitespace(filename: str) -> str:
        """Normalize whitespace in filename (collapse multiple spaces).

        Args:
            filename: Filename to normalize.

        Returns:
            Normalized filename.
        """
        return re.sub(r"\s+", " ", filename)

    @staticmethod
    def find_similar_files(
        source_path: Path,
        target_filename: str | None = None,
    ) -> list[Path]:
        """Fuzzy file search with whitespace and unicode normalization.

        Looks for files in the parent directory of source_path that match
        the filename after normalizing whitespace and unicode.

        Args:
            source_path: Path whose parent directory to search in.
            target_filename: Filename to search for. If None, uses source_path.name.

        Returns:
            List of matching file paths.
        """
        if target_filename is None:
            target_filename = source_path.name

        normalized_name = PathNormalizer.normalize_whitespace(target_filename)

        similar_files = []
        parent = source_path.parent
        if not parent.exists():
            return similar_files

        for file_path in parent.iterdir():
            if not file_path.is_file():
                continue
            actual_normalized = PathNormalizer.normalize_whitespace(file_path.name)
            if actual_normalized == normalized_name:
                similar_files.append(file_path)

        return similar_files
