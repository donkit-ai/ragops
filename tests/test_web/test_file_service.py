"""Tests for file service."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from donkit_ragops.web.services.file_service import FileService
from donkit_ragops.web.session.models import WebSession


@pytest.fixture
def file_service():
    """Create a file service instance."""
    return FileService(max_size_mb=10)


@pytest.fixture
def temp_session():
    """Create a session with temp directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session = WebSession(
            id="test-session",
            provider_name="openai",
            files_dir=Path(tmpdir),
        )
        yield session


class TestFileService:
    """Tests for FileService."""

    def test_file_service_creation(self):
        """Test FileService can be created."""
        service = FileService(max_size_mb=50)
        assert service._max_size_bytes == 50 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_list_files_empty(self, file_service, temp_session):
        """Test listing files in empty directory."""
        files = await file_service.list_files(temp_session)
        assert files == []

    @pytest.mark.asyncio
    async def test_list_files_with_files(self, file_service, temp_session):
        """Test listing files returns correct info."""
        # Create a test file
        test_file = temp_session.files_dir / "test.txt"
        test_file.write_text("hello world")

        files = await file_service.list_files(temp_session)

        assert len(files) == 1
        assert files[0]["name"] == "test.txt"
        assert files[0]["size"] == 11  # "hello world" is 11 bytes

    @pytest.mark.asyncio
    async def test_delete_file_success(self, file_service, temp_session):
        """Test deleting a file succeeds."""
        # Create a test file
        test_file = temp_session.files_dir / "test.txt"
        test_file.write_text("hello")

        result = await file_service.delete_file(temp_session, "test.txt")

        assert result is True
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, file_service, temp_session):
        """Test deleting non-existent file returns False."""
        result = await file_service.delete_file(temp_session, "nonexistent.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_file_path_traversal_blocked(self, file_service, temp_session):
        """Test path traversal attempts are blocked."""
        result = await file_service.delete_file(temp_session, "../../../etc/passwd")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_files_no_directory(self, file_service):
        """Test listing files with no directory returns empty list."""
        session = WebSession(id="test", provider_name="openai", files_dir=None)
        files = await file_service.list_files(session)
        assert files == []
