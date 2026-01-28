"""API routes for the web interface."""

from donkit_ragops.web.routes.files import router as files_router
from donkit_ragops.web.routes.health import router as health_router
from donkit_ragops.web.routes.projects import router as projects_router
from donkit_ragops.web.routes.sessions import router as sessions_router
from donkit_ragops.web.routes.settings import router as settings_router
from donkit_ragops.web.routes.websocket import router as websocket_router

__all__ = [
    "health_router",
    "sessions_router",
    "files_router",
    "projects_router",
    "settings_router",
    "websocket_router",
]
