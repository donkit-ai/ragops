"""Vectorstore loader wrapper.

Provides vectorstore loading logic that was previously embedded
in vectorstore_loader_server.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class ProgressCallback(Protocol):
    """Protocol for progress reporting."""

    async def __call__(self, current: int, total: int, message: str) -> None: ...


class VectorstoreLoadResult:
    """Result of vectorstore loading operation."""

    def __init__(self) -> None:
        self.total_chunks: int = 0
        self.successful_files: list[tuple[str, int]] = []
        self.failed_files: list[tuple[str, str]] = []

    def to_summary(self, collection_name: str, backend: str) -> str:
        """Format a summary string for output.

        Args:
            collection_name: Name of the vectorstore collection.
            backend: Backend type (qdrant, chroma, milvus).

        Returns:
            Formatted summary string.
        """
        lines = [
            f"Vectorstore loading completed for collection '{collection_name}' ({backend}):",
            "",
            f"Successfully loaded: {len(self.successful_files)} file(s),"
            f" {self.total_chunks} chunk(s)",
        ]

        if self.successful_files:
            lines.append("")
            lines.append("Successful files:")
            for filename, count in self.successful_files:
                lines.append(f"  - {filename}: {count} chunks")

        if self.failed_files:
            lines.append("")
            lines.append(f"Failed: {len(self.failed_files)} file(s)")
            lines.append("Failed files:")
            for filename, error in self.failed_files:
                lines.append(f"  - {filename}: {error}")

        return "\n".join(lines)


class VectorstoreLoader:
    """Wrapper for loading documents into vectorstore."""

    def __init__(
        self,
        backend: str,
        embeddings: Embeddings,
        collection_name: str,
        database_uri: str,
    ):
        from donkit.vectorstore_loader import create_vectorstore_loader

        self.backend = backend
        self.collection_name = collection_name
        self.loader = create_vectorstore_loader(
            db_type=backend,
            embeddings=embeddings,
            collection_name=collection_name,
            database_uri=database_uri,
        )

    async def load_from_path(
        self,
        chunks_path: str,
        progress_callback: ProgressCallback | None = None,
        batch_size: int = 500,
    ) -> VectorstoreLoadResult:
        """Load chunks from JSON files into vectorstore.

        Supports:
        - Directory (all JSON files)
        - Single file
        - Comma-separated file list

        Args:
            chunks_path: Path to directory, file, or comma-separated file list.
            progress_callback: Optional async callback for progress reporting.
            batch_size: Number of chunks per batch.

        Returns:
            VectorstoreLoadResult with detailed loading statistics.

        Raises:
            ValueError: If path not found or no JSON files found.
        """
        json_files = self._parse_chunks_path(chunks_path)

        if not json_files:
            raise ValueError(f"No JSON files found in {chunks_path}")

        result = VectorstoreLoadResult()
        total_files = len(json_files)

        for file_idx, file in enumerate(json_files, start=1):
            try:
                chunk_count = await self._load_file(
                    file, batch_size, progress_callback, file_idx, total_files
                )
                result.total_chunks += chunk_count
                result.successful_files.append((file.name, chunk_count))

                if progress_callback:
                    percentage = (file_idx / total_files) * 100
                    msg = (
                        f"{file_idx}/{total_files} files ({percentage:.1f}%) - "
                        f"{file.name}: {chunk_count} chunks loaded"
                    )
                    await progress_callback(file_idx, total_files, msg)

            except FileNotFoundError:
                result.failed_files.append((file.name, "file not found"))
                raise
            except json.JSONDecodeError as e:
                result.failed_files.append((file.name, f"invalid JSON: {str(e)}"))
                raise
            except Exception as e:
                result.failed_files.append((file.name, f"unexpected error: {str(e)}"))
                raise

        return result

    def delete_document(
        self,
        document_id: str | None = None,
        filename: str | None = None,
    ) -> bool:
        """Delete documents from vectorstore by filename or document_id.

        Args:
            document_id: Document ID to delete.
            filename: Filename to delete.

        Returns:
            True if deletion was successful.
        """
        return self.loader.delete_document_from_vectorstore(
            document_id=document_id, filename=filename
        )

    @staticmethod
    def _parse_chunks_path(chunks_path: str) -> list[Path]:
        """Parse chunks_path into a list of JSON files.

        Args:
            chunks_path: Path string (directory, file, or comma-separated list).

        Returns:
            List of Path objects for JSON files.

        Raises:
            ValueError: If path not found.
        """
        json_files: list[Path] = []

        # Comma-separated list
        if "," in chunks_path:
            file_paths = [p.strip() for p in chunks_path.split(",")]
            for file_path_str in file_paths:
                file_path = Path(file_path_str)
                if file_path.exists() and file_path.is_file() and file_path.suffix == ".json":
                    json_files.append(file_path)
        # Single file
        elif Path(chunks_path).is_file():
            file_path = Path(chunks_path)
            if file_path.suffix == ".json":
                json_files.append(file_path)
            else:
                raise ValueError(f"File must be JSON, got {file_path.suffix}")
        # Directory
        elif Path(chunks_path).is_dir():
            dir_path = Path(chunks_path)
            json_files = sorted(
                [f for f in dir_path.iterdir() if f.is_file() and f.suffix == ".json"]
            )
        else:
            raise ValueError(f"Path not found: {chunks_path}")

        return json_files

    async def _load_file(
        self,
        file: Path,
        batch_size: int = 500,
        progress_callback: ProgressCallback | None = None,
        file_idx: int = 1,
        total_files: int = 1,
    ) -> int:
        """Load a single JSON file with batching.

        Args:
            file: Path to JSON file.
            batch_size: Number of chunks per batch.
            progress_callback: Optional async callback for progress reporting.
            file_idx: Current file index (for progress reporting).
            total_files: Total number of files (for progress reporting).

        Returns:
            Number of chunks loaded.
        """
        with file.open("r", encoding="utf-8") as f:
            chunks = json.load(f)

        if not isinstance(chunks, list):
            raise ValueError(f"Expected list in {file.name}, got {type(chunks).__name__}")

        documents: list[Document] = []
        for chunk_data in chunks:
            if not isinstance(chunk_data, dict) or "page_content" not in chunk_data:
                raise ValueError(f"Invalid chunk format in {file.name}")

            doc = Document(
                page_content=chunk_data["page_content"],
                metadata=chunk_data.get("metadata", {}),
            )
            documents.append(doc)

        if not documents:
            raise ValueError(f"No valid chunks found in {file.name}")

        chunk_count = len(documents)
        total_batches = (chunk_count + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, chunk_count)
            batch = documents[start_idx:end_idx]

            task_id = uuid4()
            await self.loader.aload_documents(task_id=task_id, documents=batch)

            if total_batches > 1 and progress_callback:
                if total_files > 1:
                    batch_msg = (
                        f"File {file_idx}/{total_files} - "
                        f"Batch {batch_idx + 1}/{total_batches} ({len(batch)} chunks)"
                    )
                else:
                    batch_msg = f"Batch {batch_idx + 1}/{total_batches} ({len(batch)} chunks)"
                await progress_callback(batch_idx + 1, total_batches, batch_msg)

        return chunk_count
