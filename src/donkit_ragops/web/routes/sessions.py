"""Session management endpoints."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    from donkit_ragops.web.session.manager import SessionManager

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _is_dev_mode() -> bool:
    """Check if running in dev mode."""
    return os.environ.get("RAGOPS_WEB_DEV_MODE", "").lower() in ("1", "true", "yes")


class CreateSessionRequest(BaseModel):
    """Request body for creating a session."""

    provider: str | None = None
    model: str | None = None
    enterprise_mode: bool = False
    api_token: str | None = None  # Optional, uses config or keyring if not provided
    existing_project_id: str | None = None  # Optional, for connecting to existing project


class CreateSessionResponse(BaseModel):
    """Response for session creation."""

    session_id: str
    provider: str
    model: str | None
    enterprise_mode: bool = False
    project_id: str | None = None


class SessionResponse(BaseModel):
    """Response with session information."""

    id: str
    provider: str
    model: str | None
    created_at: float
    last_activity: float
    is_connected: bool
    message_count: int
    mcp_initialized: bool
    enterprise_mode: bool = False
    project_id: str | None = None


class ChecklistResponse(BaseModel):
    """Response with checklist information."""

    has_checklist: bool
    content: str | None = None


class HistoryMessage(BaseModel):
    """A message in the conversation history."""

    role: str
    content: str | None


class HistoryResponse(BaseModel):
    """Response with conversation history."""

    messages: list[HistoryMessage]


class NewProjectResponse(BaseModel):
    """Response for new project creation."""

    project_id: str
    session_id: str


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    request: Request,
    body: CreateSessionRequest | None = None,
) -> CreateSessionResponse:
    """Create a new session.

    Supports both local and enterprise modes:
    - Local mode (default): Uses local LLM provider and MCP subprocess
    - Enterprise mode: Connects to Donkit cloud via API Gateway

    Args:
        body: Optional request body with provider, model, and mode preferences

    Returns:
        Created session information
    """
    session_manager: SessionManager = request.app.state.session_manager

    provider = body.provider if body else None
    model = body.model if body else None
    enterprise_mode = body.enterprise_mode if body else False
    api_token = body.api_token if body else None
    existing_project_id = body.existing_project_id if body else None

    try:
        if enterprise_mode:
            # Create enterprise session
            session = await session_manager.create_enterprise_session(
                api_token=api_token,
                existing_project_id=existing_project_id,
            )
        else:
            # Create local session
            session = await session_manager.create_session(
                provider=provider,
                model=model,
            )
    except ValueError as e:
        # Missing API token or other validation error
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        if _is_dev_mode():
            raise  # Re-raise original exception with full traceback in dev mode
        raise HTTPException(status_code=500, detail=str(e)) from e

    return CreateSessionResponse(
        session_id=session.id,
        provider=session.provider_name,
        model=session.model if session.provider_name != "donkit" else None,
        enterprise_mode=session.enterprise_mode,
        project_id=session.project_id,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    request: Request,
    session_id: str,
) -> SessionResponse:
    """Get session information.

    Args:
        session_id: The session ID

    Returns:
        Session information
    """
    session_manager: SessionManager = request.app.state.session_manager
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        id=session.id,
        provider=session.provider_name,
        model=session.model if session.provider_name != "donkit" else None,
        created_at=session.created_at,
        last_activity=session.last_activity,
        is_connected=session.is_connected,
        message_count=len(session.history),
        mcp_initialized=session.mcp_initialized,
        enterprise_mode=session.enterprise_mode,
        project_id=session.project_id,
    )


@router.delete("/{session_id}")
async def delete_session(
    request: Request,
    session_id: str,
) -> dict:
    """Delete a session.

    Args:
        session_id: The session ID

    Returns:
        Success status
    """
    session_manager: SessionManager = request.app.state.session_manager
    deleted = await session_manager.delete_session(session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/checklist", response_model=ChecklistResponse)
async def get_checklist(
    request: Request,
    session_id: str,
) -> ChecklistResponse:
    """Get current checklist state for a session.

    Args:
        session_id: The session ID

    Returns:
        Checklist information
    """
    from donkit_ragops.web.services.agent_service import AgentService

    session_manager: SessionManager = request.app.state.session_manager
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    agent_service = AgentService()
    checklist = await agent_service.get_checklist(session)

    return ChecklistResponse(
        has_checklist=checklist.get("has_checklist", False),
        content=checklist.get("content"),
    )


@router.get("/{session_id}/history", response_model=HistoryResponse)
async def get_history(
    request: Request,
    session_id: str,
) -> HistoryResponse:
    """Get conversation history for a session.

    Args:
        session_id: The session ID

    Returns:
        Conversation history
    """
    from donkit_ragops.web.services.agent_service import AgentService

    session_manager: SessionManager = request.app.state.session_manager
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    agent_service = AgentService()
    messages = await agent_service.get_history(session)

    return HistoryResponse(
        messages=[HistoryMessage(role=m["role"], content=m["content"]) for m in messages]
    )


@router.post("/{session_id}/new-project", response_model=NewProjectResponse)
async def create_new_project(
    request: Request,
    session_id: str,
) -> NewProjectResponse:
    """Create a new project for an existing enterprise session.

    This endpoint creates a new project and switches the session to use it.
    The conversation history will be cleared (except system prompt).

    Only available in enterprise mode.

    Args:
        session_id: The session ID

    Returns:
        New project information

    Raises:
        HTTPException: If session not found or not in enterprise mode
    """
    session_manager: SessionManager = request.app.state.session_manager

    try:
        new_project_id = await session_manager.create_new_project(session_id)
        return NewProjectResponse(
            project_id=new_project_id,
            session_id=session_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        if _is_dev_mode():
            raise
        raise HTTPException(status_code=500, detail=str(e)) from e
