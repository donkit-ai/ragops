"""Health check endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

if TYPE_CHECKING:
    from donkit_ragops.web.session.manager import SessionManager

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe - service is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(request: Request) -> dict:
    """Readiness probe - service is ready to accept requests.

    Returns ready status and information about active sessions.
    """
    session_manager: SessionManager = request.app.state.session_manager
    sessions = await session_manager.list_sessions()

    return {
        "status": "ready",
        "sessions": {
            "active": len(sessions),
            "with_mcp": sum(1 for s in sessions if s.mcp_initialized),
        },
    }
