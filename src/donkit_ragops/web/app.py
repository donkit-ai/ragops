"""FastAPI application factory and entry point."""

from __future__ import annotations

import shutil
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from donkit_ragops.logging_config import setup_logging
from donkit_ragops.web.config import WebConfig, get_web_config
from donkit_ragops.web.routes import (
    files_router,
    health_router,
    projects_router,
    sessions_router,
    settings_router,
    websocket_router,
)
from donkit_ragops.web.session.manager import SessionManager

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager.

    Handles startup and shutdown of the application.
    """
    # Startup
    logger.debug("Starting RAGOps Web Server...")

    config: WebConfig = app.state.config
    session_manager = SessionManager(config)
    await session_manager.start()
    app.state.session_manager = session_manager

    # Create upload directory if it doesn't exist
    upload_dir = Path(config.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Server ready on http://{config.host}:{config.port}")

    yield

    # Shutdown
    logger.debug("Shutting down RAGOps Web Server...")
    await session_manager.stop()
    logger.debug("Server stopped")


def create_app(config: WebConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Optional WebConfig instance. If not provided, loads from environment.

    Returns:
        Configured FastAPI application
    """
    if config is None:
        config = get_web_config()

    app = FastAPI(
        title="RAGOps Web API",
        description="Web interface for RAGOps CLI - build RAG pipelines with AI assistance",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Store config in app state
    app.state.config = config

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(files_router)
    app.include_router(projects_router)
    app.include_router(settings_router)
    app.include_router(websocket_router)

    # Serve static files (frontend) if the directory exists
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")
        logger.debug(f"Serving frontend from {static_dir}")

    return app


def _get_static_dir() -> Path:
    """Get the static files directory path (built frontend)."""
    return Path(__file__).parent / "static"


def _get_frontend_source_dir() -> Path | None:
    """Get the frontend source directory for dev mode.

    Searches for frontend/ in current directory and parent directories.
    Returns None if not found.
    """
    # Try current working directory first
    cwd = Path.cwd()
    if (cwd / "frontend" / "package.json").exists():
        return cwd / "frontend"

    # Try parent directories (up to 5 levels)
    current = cwd
    for _ in range(5):
        current = current.parent
        if (current / "frontend" / "package.json").exists():
            return current / "frontend"

    return None


def _check_npm() -> bool:
    """Check if npm is available."""
    return shutil.which("npm") is not None


def _check_static_available() -> bool:
    """Check if static frontend files are available."""
    static_dir = _get_static_dir()
    return static_dir.exists() and (static_dir / "index.html").exists()


def _run_dev_mode(config: WebConfig) -> None:
    """Run in development mode with both Vite and FastAPI."""
    import os

    os.environ["RAGOPS_WEB_DEV_MODE"] = "1"
    frontend_dir = _get_frontend_source_dir()

    if frontend_dir is None:
        logger.error("Frontend source not found (looking for frontend/package.json)")
        logger.error("Dev mode requires frontend/ directory in project root")
        sys.exit(1)

    if not _check_npm():
        logger.error("npm not found - required for dev mode")
        sys.exit(1)

    # Install dependencies if needed
    if not (frontend_dir / "node_modules").exists():
        logger.debug("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)

    logger.debug("Starting dev servers...")
    print(f"\n  Backend:  http://{config.host}:{config.port}")
    print("  Frontend: http://localhost:5173")
    print("\n  Press Ctrl+C to stop\n")

    # Start both servers using subprocess
    vite_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        import uvicorn

        uvicorn.run(
            "donkit_ragops.web.app:create_app",
            host=config.host,
            port=config.port,
            reload=True,
            factory=True,
            log_level="info",
        )
    finally:
        vite_process.terminate()
        vite_process.wait()


def main(dev: bool = False) -> None:
    """Entry point for the web server.

    Args:
        dev: Run in development mode with hot reload for both frontend and backend.
    """
    import uvicorn

    # Parse CLI args
    if "--dev" in sys.argv or "-d" in sys.argv:
        dev = True

    # Configure logging
    setup_logging()

    # Load config
    config = get_web_config()

    # Print startup banner
    print(
        """
    ____  ___   ______                     _       __     __
   / __ \\/   | / ____/___  ____  _____   | |     / /__  / /_
  / /_/ / /| |/ / __/ __ \\/ __ \\/ ___/   | | /| / / _ \\/ __ \\
 / _, _/ ___ / /_/ / /_/ / /_/ (__  )    | |/ |/ /  __/ /_/ /
/_/ |_/_/  |_\\____/\\____/ .___/____/     |__/|__/\\___/_.___/
                       /_/
"""
    )

    if dev:
        _run_dev_mode(config)
        return

    # Production mode - check frontend is available
    if not _check_static_available():
        logger.warning("Frontend not available - API will run without UI")
        print("  Note: Web UI not available (static files not found)")
        print("  API endpoints will still work at /api/*\n")

    # Create app
    app = create_app(config)

    print(f"Starting server on http://{config.host}:{config.port}")
    print("Press Ctrl+C to stop\n")

    # Run server
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
