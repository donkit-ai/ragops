"""WebSocket endpoint for real-time chat."""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

if TYPE_CHECKING:
    from donkit_ragops.enterprise.event_listener import BackendEvent
    from donkit_ragops.web.session.manager import SessionManager
    from donkit_ragops.web.session.models import WebSession

router = APIRouter(tags=["websocket"])


@router.websocket("/api/v1/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """WebSocket endpoint for chat communication.

    Protocol:

    Client -> Server:
        {"type": "chat", "content": "user message", "silent": false}  # silent: skip persistence
        {"type": "cancel"}
        {"type": "ping"}

    Server -> Client:
        {"type": "stream_start", "timestamp": ...}
        {"type": "content", "content": "...", "timestamp": ...}
        {"type": "tool_call_start", "tool_name": "...", "tool_args": {...}, "timestamp": ...}
        {"type": "tool_call_end", "tool_name": "...", "result_preview": "...", "timestamp": ...}
        {"type": "tool_call_error", "tool_name": "...", "error": "...", "timestamp": ...}
        {"type": "checklist_update", "content": "...", "timestamp": ...}
        {"type": "stream_end", "timestamp": ...}
        {"type": "error", "error": "...", "code": "...", "timestamp": ...}
        {"type": "pong", "timestamp": ...}
    """
    from donkit_ragops.web.services.agent_service import AgentService

    session_manager: SessionManager = websocket.app.state.session_manager

    # Get session
    session = await session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    # Accept WebSocket connection
    await websocket.accept()
    session.websocket = websocket
    logger.debug(f"WebSocket connected for session {session_id}")

    # Track connection state to avoid sending on closed connection
    connected = True

    # Initialize MCP tools if not already done
    if not session.mcp_initialized:
        try:
            await session_manager.initialize_mcp(session_id)
        except Exception as e:
            logger.warning(f"Failed to initialize MCP for session {session_id}: {e}")

    agent_service = AgentService()

    async def send_message(message: dict) -> None:
        """Send a message over WebSocket."""
        if not connected:
            return
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")

    # Start event listener for enterprise mode
    event_listener_started = False
    if session.enterprise_mode and session.event_listener:
        try:
            # Set up event callback to forward backend events to WebSocket
            async def on_backend_event(event: BackendEvent) -> None:
                """Forward backend event to WebSocket and trigger agent response."""
                await _handle_backend_event(session, event, agent_service, send_message)

            def on_backend_progress(
                progress: float, total: float | None, message: str | None
            ) -> None:
                """Forward progress events to WebSocket."""
                asyncio.create_task(
                    send_message(
                        {
                            "type": "backend_progress",
                            "progress": progress,
                            "total": total,
                            "message": message,
                            "timestamp": time.time(),
                        }
                    )
                )

            session.event_listener.on_event = on_backend_event
            session.event_listener.on_progress = on_backend_progress
            await session.event_listener.start()
            event_listener_started = True
            logger.debug(f"Started event listener for enterprise session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to start event listener: {e}")

    try:
        while True:
            try:
                # Receive message from client
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                await send_message(
                    {
                        "type": "error",
                        "error": "Invalid JSON",
                        "code": "invalid_json",
                        "timestamp": time.time(),
                    }
                )
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await send_message(
                    {
                        "type": "pong",
                        "timestamp": time.time(),
                    }
                )

            elif msg_type == "cancel":
                # Cancel current task if running
                if session.current_task and not session.current_task.done():
                    session.current_task.cancel()
                    try:
                        await session.current_task
                    except asyncio.CancelledError:
                        pass
                    session.current_task = None
                    await send_message(
                        {
                            "type": "stream_cancelled",
                            "timestamp": time.time(),
                        }
                    )

            elif msg_type == "interactive_response":
                # Handle response to interactive request (confirm/choice)
                logger.debug(f"Received interactive_response: {data}")
                request_id = data.get("request_id")
                logger.debug(
                    f"Request ID: {request_id}, "
                    f"pending_responses: {list(session.pending_responses.keys())}"
                )
                if request_id and request_id in session.pending_responses:
                    future = session.pending_responses[request_id]
                    logger.debug(
                        f"Future found for request_id: {request_id}, done: {future.done()}"
                    )
                    if not future.done():
                        future.set_result(data)
                        logger.debug(f"Resolved interactive response: {request_id}")
                    else:
                        logger.warning(f"Future already done for request_id: {request_id}")
                else:
                    logger.warning(f"No pending response found for request_id: {request_id}")

            elif msg_type == "chat":
                content = data.get("content", "").strip()
                silent = data.get("silent", False)  # Don't persist to history if True
                logger.debug(f"Received chat message: {content[:100]}... (silent={silent})")
                if not content:
                    await send_message(
                        {
                            "type": "error",
                            "error": "Empty message",
                            "code": "empty_message",
                            "timestamp": time.time(),
                        }
                    )
                    continue

                # Cancel any existing task
                if session.current_task and not session.current_task.done():
                    session.current_task.cancel()
                    try:
                        await session.current_task
                    except asyncio.CancelledError:
                        pass

                # Stream response
                async def stream_response() -> None:
                    try:
                        async for event in agent_service.stream_response(
                            session, content, silent=silent
                        ):
                            await send_message(event)
                    except asyncio.CancelledError:
                        await send_message(
                            {
                                "type": "stream_cancelled",
                                "timestamp": time.time(),
                            }
                        )
                        raise
                    except Exception as e:
                        logger.error(f"Error streaming response: {e}", exc_info=True)
                        await send_message(
                            {
                                "type": "error",
                                "error": str(e),
                                "code": "stream_error",
                                "timestamp": time.time(),
                            }
                        )
                    finally:
                        # Clear current_task when done
                        if session.current_task and session.current_task.done():
                            session.current_task = None

                # Create task but don't await it - let the main loop continue
                # This allows the loop to receive interactive_response messages
                session.current_task = asyncio.create_task(stream_response())

            else:
                await send_message(
                    {
                        "type": "error",
                        "error": f"Unknown message type: {msg_type}",
                        "code": "unknown_type",
                        "timestamp": time.time(),
                    }
                )

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for session {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")

    finally:
        # Mark connection as closed to prevent further sends
        connected = False

        # Stop event listener for enterprise mode
        if event_listener_started and session.event_listener:
            try:
                await session.event_listener.stop()
                logger.debug(f"Stopped event listener for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to stop event listener: {e}")

        # Clean up
        session.websocket = None

        # Cancel any running task
        if session.current_task and not session.current_task.done():
            session.current_task.cancel()
            try:
                await session.current_task
            except asyncio.CancelledError:
                pass
            session.current_task = None


async def _handle_backend_event(
    session: WebSession,
    event: BackendEvent,
    agent_service: Any,
    send_message: Any,
) -> None:
    """Handle a backend event from EventListener.

    Sends the event to the frontend and triggers an agent response.

    Args:
        session: The web session
        event: Backend event from EventListener
        agent_service: AgentService instance
        send_message: Function to send WebSocket messages
    """
    from donkit.llm import Message

    # Send event notification to frontend
    await send_message(
        {
            "type": "backend_event",
            "event_type": event.type.value,
            "data": event.data,
            "timestamp": time.time(),
        }
    )

    # Add event as user message to history (for agent context)
    event_msg = Message(role="user", content=event.message)
    session.history.append(event_msg)

    # NOTE: We do NOT persist backend events to DB
    # They are temporary runtime notifications and should not appear
    # in conversation history when reloading a project

    # Let agent respond to the event
    try:
        async for response_event in agent_service.stream_response(session, event.message):
            await send_message(response_event)
    except Exception as e:
        logger.error(f"Error generating event response: {e}", exc_info=True)
        await send_message(
            {
                "type": "error",
                "error": f"Failed to process backend event: {e}",
                "code": "event_response_error",
                "timestamp": time.time(),
            }
        )
