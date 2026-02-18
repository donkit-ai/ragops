"""Tests for rag_builder.chunking.service."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from donkit_ragops.rag_builder.chunking import ChunkingService


def _make_chunker_config():
    from donkit.chunker import ChunkerConfig

    return ChunkerConfig(split_type="character", chunk_size=100, chunk_overlap=0)


class TestChunkingService:
    def test_source_not_found(self):
        result = ChunkingService.chunk_documents(
            source_path="/nonexistent/path",
            project_id="test",
            params=_make_chunker_config(),
        )
        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_source_is_file_not_dir(self, tmp_path):
        f = tmp_path / "file.json"
        f.write_text("[]")
        result = ChunkingService.chunk_documents(
            source_path=str(f),
            project_id="test",
            params=_make_chunker_config(),
        )
        assert result["status"] == "error"

    def test_empty_directory(self, tmp_path):
        result = ChunkingService.chunk_documents(
            source_path=str(tmp_path),
            project_id="test",
            params=_make_chunker_config(),
        )
        assert result["status"] == "success"
        assert len(result["successful"]) == 0
        assert len(result["failed"]) == 0
        assert "Processed: 0" in result["message"]

    def test_incremental_skip(self, tmp_path):
        # Create source file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        src_file = src_dir / "doc.json"
        src_file.write_text(json.dumps([{"page_content": "text", "metadata": {}}]))

        # Create output that is newer
        out_dir = Path(f"projects/test-incr/processed/chunked").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "doc.json"
        out_file.write_text("[]")

        # Make source older than output
        import os
        import time

        old_time = time.time() - 1000
        os.utime(src_file, (old_time, old_time))

        try:
            result = ChunkingService.chunk_documents(
                source_path=str(src_dir),
                project_id="test-incr",
                params=_make_chunker_config(),
                incremental=True,
            )
            assert len(result["skipped"]) == 1
            assert result["skipped"][0]["reason"] == "File not modified since last chunking"
        finally:
            # Cleanup
            import shutil

            shutil.rmtree("projects/test-incr", ignore_errors=True)

    def test_incremental_false_processes_all(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        src_file = src_dir / "doc.json"
        src_file.write_text(json.dumps([{"page_content": "hello world", "metadata": {}}]))

        mock_chunk = MagicMock()
        mock_chunk.page_content = "hello"
        mock_chunk.metadata = {}

        with patch(
            "donkit_ragops.rag_builder.chunking.service.DonkitChunker"
        ) as MockChunker:
            MockChunker.return_value.chunk_file.return_value = [mock_chunk]

            result = ChunkingService.chunk_documents(
                source_path=str(src_dir),
                project_id="test-no-incr",
                params=_make_chunker_config(),
                incremental=False,
            )

        assert result["status"] == "success"
        assert len(result["successful"]) == 1
        assert result["successful"][0]["chunks_count"] == 1
        assert len(result["skipped"]) == 0

        # Cleanup
        import shutil

        shutil.rmtree("projects/test-no-incr", ignore_errors=True)

    def test_chunking_failure(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "bad.json").write_text("not valid json for chunker")

        with patch(
            "donkit_ragops.rag_builder.chunking.service.DonkitChunker"
        ) as MockChunker:
            MockChunker.return_value.chunk_file.side_effect = Exception("parse error")

            result = ChunkingService.chunk_documents(
                source_path=str(src_dir),
                project_id="test-fail",
                params=_make_chunker_config(),
                incremental=False,
            )

        assert len(result["failed"]) == 1
        assert "parse error" in result["failed"][0]["error"]

        import shutil

        shutil.rmtree("projects/test-fail", ignore_errors=True)
