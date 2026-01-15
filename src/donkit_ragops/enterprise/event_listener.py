"""WebSocket event listener for enterprise mode.

Listens for backend events (experiments, corpus, indexing) and injects them into agent.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any

from loguru import logger


class EventType(StrEnum):
    """Types of events from backend."""

    EXPERIMENT_COMPLETED = auto()
    CORPUS_READY = auto()
    INDEXING_DONE = auto()
    EXPERIMENT_FAILED = auto()
    PROCESSING_PROGRESS = auto()
    UNKNOWN = auto()


@dataclass
class BackendEvent:
    """Event from backend WebSocket."""

    type: EventType
    data: dict[str, Any]
    message: str  # Human-readable message for agent

    @classmethod
    def from_ws_message(cls, raw: dict) -> BackendEvent:
        """Create BackendEvent from raw WebSocket message.

        Args:
            raw: Raw WebSocket message dict

        Returns:
            Parsed BackendEvent
        """
        event_type_str = raw.get("type", "unknown")
        data = raw.get("data", {})

        # Map event types
        event_type_map = {
            "experiment_completed": EventType.EXPERIMENT_COMPLETED,
            "experiment_failed": EventType.EXPERIMENT_FAILED,
            "corpus_ready": EventType.CORPUS_READY,
            "indexing_done": EventType.INDEXING_DONE,
            "processing_progress": EventType.PROCESSING_PROGRESS,
        }
        event_type = event_type_map.get(event_type_str, EventType.UNKNOWN)

        # Generate human-readable message
        message = cls._generate_message(event_type, data)

        return cls(type=event_type, data=data, message=message)

    @staticmethod
    def _generate_message(event_type: EventType, data: dict) -> str:
        """Generate human-readable message for event."""
        if event_type == EventType.EXPERIMENT_COMPLETED:
            exp_name = data.get("name", data.get("experiment_id", "Unknown"))
            return f"[System] Experiment '{exp_name}' has completed successfully."

        if event_type == EventType.EXPERIMENT_FAILED:
            exp_name = data.get("name", data.get("experiment_id", "Unknown"))
            error = data.get("error", "Unknown error")
            return f"[System] Experiment '{exp_name}' failed: {error}"

        if event_type == EventType.CORPUS_READY:
            corpus_name = data.get("name", data.get("corpus_id", "Unknown"))
            return f"[System] Corpus '{corpus_name}' is ready for use."

        if event_type == EventType.INDEXING_DONE:
            doc_count = data.get("document_count", "unknown number of")
            return f"[System] Indexing completed. {doc_count} documents indexed."

        if event_type == EventType.PROCESSING_PROGRESS:
            progress = data.get("progress", 0)
            total = data.get("total", 100)
            message = data.get("message", "Processing...")
            return f"[System] Progress: {progress}/{total} - {message}"

        return f"[System] Received event: {data}"


# Type for event callback
EventCallback = Callable[[BackendEvent], None]
ProgressCallback = Callable[[float, float | None, str | None], None]


class EventListener:
    """WebSocket event listener for backend notifications.

    Connects to API Gateway WebSocket and listens for events.
    Events are passed to the agent via callback.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        project_id: str,
        on_event: EventCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        """Initialize event listener.

        Args:
            base_url: API Gateway base URL
            token: API token for authentication
            project_id: Project ID to listen for
            on_event: Callback for backend events
            on_progress: Callback for progress updates (future use)
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.project_id = project_id
        self.on_event = on_event
        self.on_progress = on_progress

        self._ws = None
        self._running = False
        self._task: asyncio.Task | None = None

    @property
    def ws_url(self) -> str:
        """Get WebSocket URL."""
        base = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        return f"{base}/agent/ws?project_id={self.project_id}"

    async def start(self) -> None:
        """Start listening for events in background."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info(f"Started event listener for project {self.project_id}")

    async def stop(self) -> None:
        """Stop listening for events."""
        self._running = False

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Event listener stopped")

    async def _listen_loop(self) -> None:
        """Main listening loop with reconnection."""
        from websockets.asyncio.client import connect

        while self._running:
            try:
                headers = {"X-API-Token": self.token}
                async with connect(
                    self.ws_url,
                    additional_headers=headers,
                    ping_interval=None,
                ) as ws:
                    self._ws = ws
                    logger.debug(f"Connected to event WebSocket at {self.ws_url}")

                    async for message in ws:
                        if not self._running:
                            break

                        await self._handle_message(message)

            except asyncio.CancelledError:
                logger.debug("Event listener cancelled")
                break
            except Exception as e:
                if self._running:
                    logger.warning(f"Event WebSocket disconnected: {e}. Reconnecting...")
                    await asyncio.sleep(2)  # Wait before reconnecting
                else:
                    break

    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message.

        Args:
            message: Raw WebSocket message
        """
        try:
            raw = json.loads(message)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse WebSocket message: {message[:100]}")
            return

        event_type = raw.get("type", "")

        # DEBUG: Log ALL incoming WebSocket events to diagnose streaming issues
        logger.debug(f"[WS EVENT] type={event_type}, keys={list(raw.keys())}")

        # Skip chat messages - these are handled by old enterprise flow
        # We only care about backend events
        if event_type == "chat_message":
            logger.debug(f"[WS EVENT] Skipping chat_message: {str(raw)[:200]}")
            return

        # Skip agent thinking events
        if event_type == "agent_thinking":
            logger.debug(f"[WS EVENT] Skipping agent_thinking: {str(raw)[:200]}")
            return

        # Parse as backend event
        event = BackendEvent.from_ws_message(raw)

        # Handle progress events separately (future: progress bar)
        if event.type == EventType.PROCESSING_PROGRESS and self.on_progress:
            progress = event.data.get("progress", 0)
            total = event.data.get("total")
            msg = event.data.get("message")
            self.on_progress(progress, total, msg)
            return

        # Invoke event callback
        if self.on_event and event.type != EventType.UNKNOWN:
            try:
                self.on_event(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}", exc_info=True)

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._ws is not None and self._running
