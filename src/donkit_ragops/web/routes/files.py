"""File upload endpoints."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from loguru import logger
from pydantic import BaseModel

if TYPE_CHECKING:
    from donkit_ragops.web.session.manager import SessionManager

router = APIRouter(prefix="/api/v1/sessions", tags=["files"])


class FileInfo(BaseModel):
    """Information about an uploaded file."""

    name: str
    path: str
    size: int
    content_type: str | None = None
    s3_path: str | None = None  # Cloud path for enterprise mode


class FilesResponse(BaseModel):
    """Response with list of files."""

    files: list[FileInfo]


class UploadResponse(BaseModel):
    """Response for file upload."""

    uploaded: list[FileInfo]
    errors: list[dict] | None = None
    enterprise_mode: bool = False


@router.post("/{session_id}/files", response_model=UploadResponse)
async def upload_files(
    request: Request,
    session_id: str,
    files: list[UploadFile] = File(...),
) -> UploadResponse:
    """Upload files for a session.

    In local mode, files are saved to the session's upload directory.
    In enterprise mode, files are uploaded to cloud storage via API Gateway.

    Args:
        session_id: The session ID
        files: Files to upload (multipart form data)

    Returns:
        Information about uploaded files
    """
    from donkit_ragops.web.services.file_service import FileService

    session_manager: SessionManager = request.app.state.session_manager
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Enterprise mode: upload to cloud storage
    if session.enterprise_mode:
        return await _upload_files_enterprise(session, files)

    # Local mode: save to local directory
    file_service = FileService(max_size_mb=request.app.state.config.max_upload_size_mb)

    try:
        results = await file_service.upload_files(session, files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    uploaded = []
    errors = []

    for result in results:
        if "error" in result:
            errors.append(result)
        else:
            uploaded.append(
                FileInfo(
                    name=result["name"],
                    path=result["path"],
                    size=result["size"],
                    content_type=result.get("content_type"),
                )
            )

    return UploadResponse(
        uploaded=uploaded,
        errors=errors if errors else None,
        enterprise_mode=False,
    )


async def _upload_files_enterprise(
    session,
    files: list[UploadFile],
) -> UploadResponse:
    """Upload files to cloud storage for enterprise mode.

    Args:
        session: WebSession in enterprise mode
        files: Files to upload

    Returns:
        UploadResponse with cloud paths
    """
    from donkit_ragops.enterprise.upload import FileUploader

    if not session.api_client or not session.project_id:
        raise HTTPException(
            status_code=400,
            detail="Enterprise session not properly initialized",
        )

    uploaded = []
    errors = []

    # Create FileUploader
    file_uploader = FileUploader(session.api_client)

    # Save files to temp directory and upload
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_paths = []

        for upload_file in files:
            try:
                # Save to temp file
                temp_path = Path(temp_dir) / upload_file.filename
                content = await upload_file.read()
                temp_path.write_bytes(content)
                temp_paths.append(str(temp_path))
            except Exception as e:
                errors.append(
                    {
                        "name": upload_file.filename,
                        "error": str(e),
                    }
                )
                continue

        # Upload all files to cloud
        for temp_path_str in temp_paths:
            temp_path = Path(temp_path_str)
            try:
                s3_path = await file_uploader.upload_single_file(
                    temp_path_str,
                    session.project_id,
                )

                if s3_path:
                    uploaded.append(
                        FileInfo(
                            name=temp_path.name,
                            path=temp_path_str,
                            size=temp_path.stat().st_size,
                            s3_path=s3_path,
                        )
                    )
                    logger.info(f"Uploaded {temp_path.name} to {s3_path}")
                else:
                    errors.append(
                        {
                            "name": temp_path.name,
                            "error": "Upload failed",
                        }
                    )
            except Exception as e:
                errors.append(
                    {
                        "name": temp_path.name,
                        "error": str(e),
                    }
                )

    file_uploader.reset()

    return UploadResponse(
        uploaded=uploaded,
        errors=errors if errors else None,
        enterprise_mode=True,
    )


@router.get("/{session_id}/files", response_model=FilesResponse)
async def list_files(
    request: Request,
    session_id: str,
) -> FilesResponse:
    """List files for a session.

    Args:
        session_id: The session ID

    Returns:
        List of files in the session's upload directory
    """
    from donkit_ragops.web.services.file_service import FileService

    session_manager: SessionManager = request.app.state.session_manager
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    file_service = FileService()
    files = await file_service.list_files(session)

    return FilesResponse(
        files=[
            FileInfo(
                name=f["name"],
                path=f["path"],
                size=f["size"],
            )
            for f in files
        ]
    )
