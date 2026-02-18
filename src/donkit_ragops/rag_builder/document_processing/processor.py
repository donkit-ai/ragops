"""Document processing engine.

Resolves source paths, processes documents through DonkitReader,
and manages output directories.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from donkit.read_engine.read_engine import DonkitReader
from loguru import logger

from donkit_ragops.rag_builder.document_processing.path_utils import PathNormalizer

# Sync callback: (current, total, message) -> None
SyncProgressCallback = Callable[[int, int, str | None], None]

# Async callback: (current, total, message) -> coroutine
AsyncProgressCallback = Callable[[int, int, str], object]


class DocumentProcessResult:
    """Result of a document processing operation."""

    def __init__(self) -> None:
        self.processed_files: list[str] = []
        self.failed_files: list[dict[str, str]] = []

    @property
    def processed_count(self) -> int:
        return len(self.processed_files)

    @property
    def failed_count(self) -> int:
        return len(self.failed_files)

    @property
    def status(self) -> str:
        if self.processed_files and not self.failed_files:
            return "success"
        elif self.processed_files and self.failed_files:
            return "partial_success"
        return "error"

    def to_dict(self, output_dir: str) -> dict:
        """Convert to result dict for serialization."""
        return {
            "status": self.status,
            "output_directory": output_dir,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "processed_files": self.processed_files[:10],
            "failed_files": self.failed_files[:10] if self.failed_files else [],
            "message": (
                f"Processed {self.processed_count} files successfully. "
                + (f"Failed: {self.failed_count} files. " if self.failed_files else "")
                + f"Output saved to: {output_dir}"
            ),
        }


def resolve_source_files(
    source_path_raw: str,
    supported_extensions: set[str],
) -> list[Path] | dict:
    """Resolve source path(s) into a list of files to process.

    Supports: single file, directory (recursive), comma-separated list.
    Falls back to fuzzy matching if the exact path is not found.

    Args:
        source_path_raw: Raw source path string from user.
        supported_extensions: Set of supported file extensions (e.g. {".pdf", ".docx"}).

    Returns:
        List of resolved Path objects, or a dict with "status": "error" on failure.
    """
    source_path_str = source_path_raw.strip()
    source_path_str = PathNormalizer.normalize_unicode(source_path_str)
    source_path = Path(source_path_str)

    files_to_process: list[Path] = []

    # Single file
    if source_path.is_file():
        if source_path.suffix.lower() in supported_extensions:
            return [source_path]
        return {
            "status": "error",
            "message": (
                f"File format not supported: {source_path.suffix}. "
                f"Supported: {sorted(supported_extensions)}"
            ),
        }

    # Directory
    if source_path.is_dir():
        return [
            f
            for f in source_path.rglob("*")
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

    # Comma-separated list
    if "," in source_path_raw:
        for raw in source_path_raw.split(","):
            fp_str = PathNormalizer.normalize_unicode(raw.strip())
            fp = Path(fp_str)
            if not fp.exists():
                logger.warning(f"File not found: {fp}")
                continue
            if fp.is_file() and fp.suffix.lower() in supported_extensions:
                files_to_process.append(fp)
            else:
                logger.warning(f"File not supported or not found: {fp}")
        return files_to_process

    # Fuzzy match
    if source_path.parent.exists():
        similar = PathNormalizer.find_similar_files(source_path)
        if similar:
            return {
                "status": "error",
                "message": (
                    f"File not found: {source_path.name}\n\n"
                    f"Found similar file(s):\n"
                    + "\n".join(f"- {f}" for f in similar)
                    + "\n\nPlease provide the exact file path from the list above."
                ),
                "similar_files": [str(f) for f in similar],
            }

    # Nothing found
    return {
        "status": "error",
        "message": (
            f"No supported files found in {source_path}. Supported: {sorted(supported_extensions)}"
        ),
    }


class DocumentProcessor:
    """Processes documents from various formats into text/json/markdown."""

    @staticmethod
    def get_supported_extensions(reading_format: str, use_llm: bool = True) -> set[str]:
        """Get supported file extensions for a given reading format.

        Args:
            reading_format: Output format (json, md, text).
            use_llm: Whether to use LLM for processing.

        Returns:
            Set of supported extensions.
        """
        reader = DonkitReader(output_format=reading_format, use_llm=use_llm)
        extensions = set(reader.readers.keys())
        extensions.add(".pdf")
        extensions.add(".pptx")
        extensions.add(".docx")
        return extensions

    @staticmethod
    async def process_documents(
        source_path: str,
        project_id: str,
        reading_format: str = "json",
        use_llm: bool = True,
        reader_progress_callback: SyncProgressCallback | None = None,
        file_progress_callback: AsyncProgressCallback | None = None,
    ) -> dict:
        """Process documents and save to project directory.

        Args:
            source_path: Path to source (directory, file, or comma-separated list).
            project_id: Project ID for organizing output.
            reading_format: Output format (json, md, text).
            use_llm: Use LLM for document processing.
            reader_progress_callback: Sync callback for DonkitReader page progress.
            file_progress_callback: Async callback for file-level progress.

        Returns:
            Dict with status, output_directory, processed/failed counts.
        """
        reader = DonkitReader(
            output_format=reading_format,
            use_llm=use_llm,
            progress_callback=reader_progress_callback,
        )
        supported_extensions = set(reader.readers.keys())
        supported_extensions.add(".pdf")
        supported_extensions.add(".pptx")
        supported_extensions.add(".docx")

        # Resolve files
        resolved = resolve_source_files(source_path, supported_extensions)
        if isinstance(resolved, dict):
            return resolved
        files_to_process = resolved

        if not files_to_process:
            return {
                "status": "error",
                "message": f"No supported files found. Supported: {sorted(supported_extensions)}",
            }

        # Create output directory
        project_output_dir = Path(f"projects/{project_id}/processed").resolve()
        project_output_dir.mkdir(parents=True, exist_ok=True)

        result = DocumentProcessResult()
        total_files = len(files_to_process)

        for idx, file_path in enumerate(files_to_process):
            try:
                if file_progress_callback:
                    await file_progress_callback(
                        idx,
                        total_files,
                        f"Processing file {file_path.name} - {idx}/{total_files}",
                    )

                output_path = await reader.aread_document(
                    str(file_path),
                    output_dir=str(project_output_dir),
                )
                result.processed_files.append(output_path)
                logger.debug(f"Processed: {file_path.name} -> {output_path}")
            except Exception as e:
                result.failed_files.append({"file": str(file_path), "error": str(e)})
                logger.error(f"Failed to process {file_path.name}: {e}", exc_info=True)

        # Clean up empty temp directories
        for file_path in files_to_process:
            temp_dir = file_path.parent / "processed"
            try:
                if temp_dir.exists() and temp_dir.is_dir() and not list(temp_dir.iterdir()):
                    temp_dir.rmdir()
            except Exception as e:
                logger.warning(f"Could not clean up temp directory {temp_dir}: {e}")

        return result.to_dict(str(project_output_dir))
