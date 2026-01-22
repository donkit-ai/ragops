"""Projects API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel

if TYPE_CHECKING:
    from donkit_ragops.web.session.manager import SessionManager

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectInfo(BaseModel):
    """Project information."""

    id: str
    created_at: str | None = None
    updated_at: str | None = None
    message_count: int = 0
    status: str | None = None
    rag_use_case: str | None = None


class ProjectListResponse(BaseModel):
    """Response for project list."""

    projects: list[ProjectInfo]


class MessageHistoryResponse(BaseModel):
    """Response for message history."""

    messages: list[dict[str, Any]]
    project_id: str


@router.get("/recent", response_model=ProjectListResponse)
async def get_recent_projects(
    request: Request,
    session_id: str,
    limit: int = 10,
) -> ProjectListResponse:
    """Get recent projects for the current user.

    Args:
        request: FastAPI request object
        session_id: Session ID (to get API client)
        limit: Maximum number of projects to return

    Returns:
        List of recent projects
    """
    session_manager: SessionManager = request.app.state.session_manager
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.enterprise_mode or not session.api_client:
        raise HTTPException(
            status_code=400, detail="Projects are only available in enterprise mode"
        )

    try:
        async with session.api_client:
            # Use API Gateway client to get recent projects
            projects_data = await session.api_client.get_recent_projects(limit=limit)

            # Convert to ProjectInfo
            projects = []
            for p in projects_data:
                projects.append(
                    ProjectInfo(
                        id=str(p.get("id", "")),
                        created_at=p.get("created_at"),
                        updated_at=p.get("updated_at"),
                        message_count=p.get("message_count", 0),
                        status=p.get("status"),
                        rag_use_case=p.get("rag_use_case"),
                    )
                )

            return ProjectListResponse(projects=projects)

    except Exception as e:
        logger.error(f"Failed to get recent projects: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent projects: {e}")


@router.get("/{project_id}/messages", response_model=MessageHistoryResponse)
async def get_project_messages(
    request: Request,
    session_id: str,
    project_id: str,
    limit: int = 100,
) -> MessageHistoryResponse:
    """Get message history for a project.

    Args:
        request: FastAPI request object
        session_id: Session ID (to get API client)
        project_id: Project ID
        limit: Maximum number of messages to return

    Returns:
        Message history for the project
    """
    session_manager: SessionManager = request.app.state.session_manager
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.enterprise_mode or not session.api_client:
        raise HTTPException(
            status_code=400, detail="Message history is only available in enterprise mode"
        )

    try:
        async with session.api_client:
            # Use API Gateway client to get messages
            messages = await session.api_client.get_project_messages(
                project_id=project_id, limit=limit
            )

            return MessageHistoryResponse(messages=messages, project_id=project_id)

    except Exception as e:
        logger.error(f"Failed to get project messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get project messages: {e}")


@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project(
    request: Request,
    session_id: str,
    project_id: str,
) -> ProjectInfo:
    """Get project details.

    Args:
        request: FastAPI request object
        session_id: Session ID (to get API client)
        project_id: Project ID

    Returns:
        Project information
    """
    session_manager: SessionManager = request.app.state.session_manager
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.enterprise_mode or not session.api_client:
        raise HTTPException(
            status_code=400, detail="Project details are only available in enterprise mode"
        )

    try:
        async with session.api_client:
            # Use API Gateway client to get project
            project_data = await session.api_client.get_project_details(project_id=project_id)

            return ProjectInfo(
                id=str(project_data.get("id", "")),
                created_at=project_data.get("created_at"),
                updated_at=project_data.get("updated_at"),
                message_count=project_data.get("message_count", 0),
                status=project_data.get("status"),
                rag_use_case=project_data.get("rag_use_case"),
            )

    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get project: {e}")
