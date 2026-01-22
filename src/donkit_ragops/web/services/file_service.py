"""File service for handling file uploads."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import aiofiles
from loguru import logger

if TYPE_CHECKING:
    from fastapi import UploadFile

    from donkit_ragops.web.session.models import WebSession


class FileService:
    """Service for handling file uploads and management."""

    def __init__(self, max_size_mb: int = 100) -> None:
        self._max_size_bytes = max_size_mb * 1024 * 1024

    async def upload_file(
        self,
        session: WebSession,
        file: UploadFile,
    ) -> dict:
        """Upload a file for a session.

        Args:
            session: The web session
            file: The uploaded file

        Returns:
            Dict with file info (path, name, size)

        Raises:
            ValueError: If file is too large or session has no files dir
        """
        if not session.files_dir:
            raise ValueError("Session has no files directory")

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Check file size
        if file_size > self._max_size_bytes:
            raise ValueError(
                f"File too large: {file_size / 1024 / 1024:.1f}MB "
                f"(max {self._max_size_bytes / 1024 / 1024:.0f}MB)"
            )

        # Generate unique filename to avoid collisions
        original_name = file.filename or "unnamed_file"
        unique_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
        file_path = session.files_dir / unique_name

        # Write file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        logger.info(f"Uploaded file {original_name} ({file_size} bytes) to {file_path}")

        return {
            "name": original_name,
            "path": str(file_path),
            "size": file_size,
            "content_type": file.content_type,
        }

    async def upload_files(
        self,
        session: WebSession,
        files: list[UploadFile],
    ) -> list[dict]:
        """Upload multiple files for a session.

        Args:
            session: The web session
            files: List of uploaded files

        Returns:
            List of dicts with file info
        """
        results = []
        errors = []

        for file in files:
            try:
                result = await self.upload_file(session, file)
                results.append(result)
            except Exception as e:
                errors.append(
                    {
                        "name": file.filename,
                        "error": str(e),
                    }
                )

        if errors:
            logger.warning(f"Some files failed to upload: {errors}")

        return results

    async def list_files(self, session: WebSession) -> list[dict]:
        """List files in the session's upload directory.

        Args:
            session: The web session

        Returns:
            List of dicts with file info
        """
        if not session.files_dir or not session.files_dir.exists():
            return []

        files = []
        for file_path in session.files_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append(
                    {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": stat.st_size,
                    }
                )

        return files
