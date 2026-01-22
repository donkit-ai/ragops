"""Agent service for handling LLM interactions."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from donkit.llm import Message
from loguru import logger

from donkit_ragops.agent.agent import EventType
from donkit_ragops.checklist_manager import (
    ChecklistStatusProvider,
    get_active_checklist_text,
)
from donkit_ragops.history_manager import compress_history_if_needed
from donkit_ragops.web.session.models import WebSession
from donkit_ragops.web.tools.interactive import current_web_session


class AgentService:
    """Service for managing agent interactions and streaming responses."""

    def __init__(self) -> None:
        self._checklist_provider = ChecklistStatusProvider()

    async def stream_response(
        self,
        session: WebSession,
        message: str,
        silent: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream agent response for a message.

        Yields WebSocket-formatted events for:
        - Content chunks
        - Tool call start/end/error
        - Checklist updates
        - Stream start/end

        Args:
            session: The web session
            message: User message to process
            silent: If True, don't persist message to DB (for internal messages like file uploads)

        Yields:
            Dict events for WebSocket transmission
        """
        logger.info(f"AgentService.stream_response called with message: {message[:100]}...")

        if not session.agent:
            logger.error("Agent not initialized for session")
            yield {
                "type": "error",
                "error": "Agent not initialized",
                "code": "agent_not_ready",
                "timestamp": time.time(),
            }
            return

        # Add user message to history
        session.history.append(Message(role="user", content=message))
        session.touch()
        logger.info(f"History now has {len(session.history)} messages")

        # Persist user message for enterprise mode (unless silent)
        if session.enterprise_mode and session.message_persister and not silent:
            try:
                await session.message_persister.persist_user_message(message)
            except Exception as e:
                logger.warning(f"Failed to persist user message: {e}")

        # Stream start
        yield {
            "type": "stream_start",
            "timestamp": time.time(),
        }

        reply = ""
        error_occurred = False

        # Set current session context for web tools
        token = current_web_session.set(session)

        try:
            logger.info("Starting agent.arespond_stream...")
            async for event in session.agent.arespond_stream(session.history):
                if event.type == EventType.CONTENT:
                    if event.content:
                        reply += event.content
                        yield {
                            "type": "content",
                            "content": event.content,
                            "timestamp": time.time(),
                        }

                elif event.type == EventType.TOOL_CALL_START:
                    yield {
                        "type": "tool_call_start",
                        "tool_name": event.tool_name,
                        "tool_args": event.tool_args,
                        "timestamp": time.time(),
                    }

                    # Check for checklist-related tool calls
                    if event.tool_name in (
                        "create_checklist",
                        "get_checklist",
                        "update_checklist_item",
                    ):
                        # Will send checklist update after tool completes
                        pass

                elif event.type == EventType.TOOL_CALL_END:
                    # Get result preview from history
                    result_preview = None
                    if session.history and session.history[-1].role == "tool":
                        result_content = session.history[-1].content
                        if result_content:
                            # Truncate long results
                            result_preview = (
                                result_content[:200] + "..."
                                if len(result_content) > 200
                                else result_content
                            )

                    yield {
                        "type": "tool_call_end",
                        "tool_name": event.tool_name,
                        "result_preview": result_preview,
                        "timestamp": time.time(),
                    }

                    # Send checklist update if it was a checklist tool
                    if event.tool_name in (
                        "create_checklist",
                        "get_checklist",
                        "update_checklist_item",
                    ):
                        checklist_update = await self._get_checklist_update(session)
                        if checklist_update:
                            yield checklist_update

                elif event.type == EventType.TOOL_CALL_ERROR:
                    yield {
                        "type": "tool_call_error",
                        "tool_name": event.tool_name,
                        "error": event.error,
                        "timestamp": time.time(),
                    }

        except asyncio.CancelledError:
            logger.info("Agent stream cancelled")
            yield {
                "type": "stream_cancelled",
                "timestamp": time.time(),
            }
            raise

        except Exception as e:
            logger.error(f"Error in agent stream: {e}", exc_info=True)
            error_occurred = True
            yield {
                "type": "error",
                "error": str(e),
                "code": "agent_error",
                "timestamp": time.time(),
            }

        finally:
            # Reset session context
            current_web_session.reset(token)

        # Add assistant reply to history if we got one
        if reply and not error_occurred:
            session.history.append(Message(role="assistant", content=reply))

            # Persist assistant message for enterprise mode
            if session.enterprise_mode and session.message_persister:
                try:
                    await session.message_persister.persist_assistant_message(content=reply)
                except Exception as e:
                    logger.warning(f"Failed to persist assistant message: {e}")

        # Compress history if needed
        if session.agent and session.agent.provider:
            try:
                session.history[:] = await compress_history_if_needed(
                    session.history, session.agent.provider
                )
            except Exception as e:
                logger.warning(f"Failed to compress history: {e}")

        # Stream end
        yield {
            "type": "stream_end",
            "timestamp": time.time(),
        }

    async def _get_checklist_update(self, session: WebSession) -> dict[str, Any] | None:
        """Get checklist update event if there's an active checklist."""
        try:
            checklist_text = get_active_checklist_text(session.created_at)
            if checklist_text:
                return {
                    "type": "checklist_update",
                    "content": checklist_text,
                    "timestamp": time.time(),
                }
        except Exception as e:
            logger.warning(f"Failed to get checklist: {e}")
        return None

    async def get_checklist(self, session: WebSession) -> dict[str, Any]:
        """Get current checklist state for the session."""
        try:
            checklist_text = get_active_checklist_text(session.created_at)
            return {
                "has_checklist": checklist_text is not None,
                "content": checklist_text,
            }
        except Exception as e:
            logger.warning(f"Failed to get checklist: {e}")
            return {
                "has_checklist": False,
                "content": None,
                "error": str(e),
            }

    async def get_history(self, session: WebSession) -> list[dict[str, Any]]:
        """Get conversation history for the session.

        Returns messages formatted for the frontend.
        """
        messages = []
        for msg in session.history:
            # Skip system messages
            if msg.role == "system":
                continue

            # Skip tool messages (internal)
            if msg.role == "tool":
                continue

            # Skip backend events (temporary runtime notifications)
            if (
                msg.role == "user"
                and msg.content
                and (
                    msg.content.startswith("[SYSTEM INSTRUCTION:")
                    or msg.content.startswith("[PIPELINE:")
                    or msg.content.startswith("[BACKEND_EVENT:")
                    or msg.content.startswith("[EXPERIMENT_ITERATION_COMPLETED]")
                )
            ):
                continue

            messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                }
            )
        return messages
