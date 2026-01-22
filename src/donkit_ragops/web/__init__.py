"""Web interface module for RAGOps CLI.

Provides FastAPI-based web backend with the same functionality as CLI,
for users who prefer GUI over terminal.
"""

from donkit_ragops.web.app import create_app, main

__all__ = ["create_app", "main"]
