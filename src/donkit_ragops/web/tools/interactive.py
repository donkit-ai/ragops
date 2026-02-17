"""Web-specific interactive tools that use WebSocket for user interaction."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from loguru import logger

from donkit_ragops.agent.local_tools.tools import AgentTool

if TYPE_CHECKING:
    from donkit_ragops.web.session.models import WebSession

# Context variable for current web session
current_web_session: ContextVar[WebSession | None] = ContextVar("current_web_session", default=None)


def create_web_progress_callback():
    """Create a progress callback that sends updates via WebSocket.

    Returns:
        Callback function (progress, total, message) -> None
        that sends progress events to the current web session.
    """

    def progress_callback(progress: float, total: float | None, message: str | None = None) -> None:
        """Send progress update via WebSocket.

        Args:
            progress: Current progress value
            total: Total value (None for indeterminate progress)
            message: Progress message
        """
        session = current_web_session.get()
        if not session or not session.websocket:
            # Fallback to logging if no web session
            if total is not None:
                percentage = (progress / total) * 100
                logger.debug(f"Progress: {percentage:.1f}% - {message or ''}")
            else:
                logger.debug(f"Progress: {progress} - {message or ''}")
            return

        # Send progress event via WebSocket
        try:
            event = {
                "type": "progress_update",
                "progress": progress,
                "total": total,
                "message": message,
                "timestamp": time.time(),
            }
            # Use asyncio to send from sync context
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                session.websocket.send_json(event),
                loop,
            )
        except Exception as e:
            logger.warning(f"Failed to send progress update via WebSocket: {e}")

    return progress_callback


async def _send_and_wait_response(
    session: WebSession,
    message: dict[str, Any],
    timeout: float = 300.0,
) -> dict[str, Any] | None:
    """Send a WebSocket message and wait for user response.

    Args:
        session: The web session
        message: Message to send (must include request_id)
        timeout: Timeout in seconds

    Returns:
        Response data or None if timeout/cancelled
    """
    request_id = message.get("request_id")
    if not request_id:
        raise ValueError("Message must include request_id")

    if not session.websocket:
        logger.warning("No WebSocket connection for interactive request")
        return None

    # Create future for response
    future: asyncio.Future = asyncio.Future()
    session.pending_responses[request_id] = future

    try:
        # Send the request
        logger.debug(f"Sending interactive request: {message}")
        await session.websocket.send_json(message)
        logger.debug(f"Sent interactive request: {message['type']}, request_id: {request_id}")

        # Wait for response with timeout
        logger.debug(f"Waiting for response to request_id: {request_id}")
        response = await asyncio.wait_for(future, timeout=timeout)
        logger.debug(f"Received response for request_id: {request_id}, response: {response}")
        return response

    except asyncio.TimeoutError:
        logger.warning(f"Interactive request timed out: {request_id}")
        return None
    except asyncio.CancelledError:
        logger.debug(f"Interactive request cancelled: {request_id}")
        raise
    finally:
        # Clean up
        session.pending_responses.pop(request_id, None)


def web_tool_interactive_user_confirm() -> AgentTool:
    """Web tool for interactive yes/no confirmation via WebSocket dialog."""

    async def handler(args: dict[str, Any]) -> str:
        question = args.get("question", "")
        default = args.get("default", True)

        session = current_web_session.get()
        if not session:
            # Fallback: return default
            logger.warning("No web session context, using default for confirm")
            return json.dumps({"cancelled": False, "confirmed": default})

        request_id = str(uuid.uuid4())
        message = {
            "type": "confirm_request",
            "request_id": request_id,
            "question": question,
            "default": default,
            "timestamp": time.time(),
        }

        response = await _send_and_wait_response(session, message)

        if response is None:
            return json.dumps({"cancelled": True, "confirmed": None})

        confirmed = response.get("confirmed", default)
        return json.dumps({"cancelled": False, "confirmed": confirmed})

    return AgentTool(
        name="interactive_user_confirm",
        description=(
            "Present an interactive yes/no confirmation dialog to the user. "
            "Use this when you need confirmation (e.g., 'Continue?', 'Proceed?'). "
            "User will see buttons to click Yes or No. "
            "IMPORTANT: If confirmed=false or cancelled, STOP and wait for user's next message. "
            "If confirmed=true, continue with the planned action."
        ),
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The yes/no question to ask",
                },
                "default": {
                    "type": "boolean",
                    "description": "Default value (true for Yes)",
                    "default": True,
                },
            },
            "required": ["question"],
        },
        handler=handler,
        is_async=True,
    )


def web_tool_interactive_user_choice() -> AgentTool:
    """Web tool for interactive choice selection via WebSocket dialog."""

    async def handler(args: dict[str, Any]) -> str:
        choices = args.get("choices", [])
        title = args.get("title", "Select an option")

        session = current_web_session.get()
        if not session:
            # Fallback: return first choice
            logger.warning("No web session context, using first choice")
            if choices:
                return json.dumps({"cancelled": False, "choice": choices[0]})
            return json.dumps({"cancelled": True, "choice": None})

        request_id = str(uuid.uuid4())
        message = {
            "type": "choice_request",
            "request_id": request_id,
            "choices": choices,
            "title": title,
            "timestamp": time.time(),
        }

        response = await _send_and_wait_response(session, message)

        if response is None:
            return json.dumps({"cancelled": True, "choice": None})

        choice = response.get("choice")
        return json.dumps({"cancelled": False, "choice": choice})

    return AgentTool(
        name="interactive_user_choice",
        description=(
            "Present an interactive selection menu to the user. "
            "The user will see clickable options to choose from. "
            "Use this when you need the user to select from multiple options."
        ),
        parameters={
            "type": "object",
            "properties": {
                "choices": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of options to choose from",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the selection menu",
                    "default": "Select an option",
                },
            },
            "required": ["choices"],
        },
        handler=handler,
        is_async=True,
    )


def web_tool_get_recommended_defaults() -> AgentTool:
    """Web tool that returns available providers and recommended RAG defaults."""

    async def handler(args: dict[str, Any]) -> str:  # noqa: ARG001
        from donkit_ragops.credential_checker import (
            get_available_providers,
            get_recommended_config,
        )

        available_providers = get_available_providers()
        recommended = get_recommended_config()

        return json.dumps(
            {
                "available_providers": available_providers,
                "recommended_config": {
                    "embedder_provider": recommended["embedder_provider"],
                    "embedder_model": recommended["embedder_model"],
                    "generation_provider": recommended["generation_provider"],
                    "generation_model": recommended["generation_model"],
                    "vector_db": "qdrant",
                    "read_format": "json",
                    "split_type": "character",
                    "chunk_size": 500,
                    "chunk_overlap": 0,
                    "ranker": False,
                    "partial_search": True,
                    "query_rewrite": True,
                },
            },
            ensure_ascii=False,
        )

    return AgentTool(
        name="get_recommended_defaults",
        description=(
            "Returns available providers and recommended RAG configuration defaults. "
            "Call this before custom configuration to know which providers "
            "are available and what settings to recommend. "
            "Does NOT ask the user anything — just returns data."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        handler=handler,
        is_async=True,
    )
