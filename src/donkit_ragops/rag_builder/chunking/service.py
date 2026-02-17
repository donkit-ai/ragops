"""Document chunking service.

Splits processed documents into smaller text chunks with
incremental processing support.
"""

from __future__ import annotations

import json
from pathlib import Path

from donkit.chunker import ChunkerConfig, DonkitChunker
from loguru import logger


class ChunkingService:
    """Service for splitting documents into chunks."""

    @staticmethod
    def chunk_documents(
        source_path: str,
        project_id: str,
        params: ChunkerConfig,
        incremental: bool = True,
    ) -> dict:
        """Chunk documents from source directory.

        Reads documents from source_path, splits them into smaller text chunks,
        and saves to projects/<project_id>/processed/chunked/.

        Args:
            source_path: Path to the source directory with processed documents.
            project_id: Project ID for organizing output.
            params: Chunker configuration (split_type, chunk_size, chunk_overlap).
            incremental: If True, only process new/modified files.

        Returns:
            Dict with status, output_path, successful/failed/skipped lists.
        """
        chunker = DonkitChunker(params)
        source_dir = Path(source_path)

        if not source_dir.exists() or not source_dir.is_dir():
            logger.error(f"Source path not found: {source_dir}")
            return {"status": "error", "message": f"Source path not found: {source_dir}"}

        output_path = Path(f"projects/{project_id}/processed/chunked").resolve()
        output_path.mkdir(parents=True, exist_ok=True)

        results: dict = {
            "status": "success",
            "output_path": str(output_path),
            "successful": [],
            "failed": [],
            "skipped": [],
            "incremental": incremental,
        }

        files_to_process = [f for f in source_dir.iterdir() if f.is_file()]

        for file in files_to_process:
            output_file = output_path / f"{file.stem}.json"

            # Incremental: skip unmodified files
            if incremental and output_file.exists():
                if file.stat().st_mtime <= output_file.stat().st_mtime:
                    results["skipped"].append(
                        {
                            "file": str(file),
                            "reason": "File not modified since last chunking",
                        }
                    )
                    continue

            try:
                chunked_documents = chunker.chunk_file(file_path=str(file))

                payload = [
                    {"page_content": chunk.page_content, "metadata": chunk.metadata}
                    for chunk in chunked_documents
                ]

                output_file.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                results["successful"].append(
                    {
                        "file": str(file),
                        "output": str(output_file),
                        "chunks_count": len(chunked_documents),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to process {file.name}: {e}")
                results["failed"].append({"file": str(file), "error": str(e)})

        results["message"] = (
            f"Processed: {len(results['successful'])}, "
            f"Skipped: {len(results['skipped'])}, "
            f"Failed: {len(results['failed'])}"
        )

        return results
