"""WebSocket event listener for enterprise mode.

Listens for backend events (experiments, corpus, indexing) and injects them into agent.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
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
    # Pipeline stages
    READING_COMPLETED = auto()
    CHUNKING_COMPLETED = auto()
    EMBEDDING_COMPLETED = auto()
    CATEGORY_EMBEDDING_COMPLETED = auto()
    INDEXING_COMPLETED = auto()
    RAG_COMPLETED = auto()
    EXPERIMENT_ITERATION_COMPLETED = auto()
    # Airbyte events
    AIRBYTE_DOCUMENT_ADDED = auto()
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

        # Handle pipeline_status events (nested stage field)
        if event_type_str == "pipeline_status":
            stage = data.get("stage", "")
            stage_map = {
                "reading_completed": EventType.READING_COMPLETED,
                "chunking_completed": EventType.CHUNKING_COMPLETED,
                "embedding_completed": EventType.EMBEDDING_COMPLETED,
                "category_embedding_completed": EventType.CATEGORY_EMBEDDING_COMPLETED,
                "indexing_completed": EventType.INDEXING_COMPLETED,
                "rag_completed": EventType.RAG_COMPLETED,
                "experiment_iteration_completed": EventType.EXPERIMENT_ITERATION_COMPLETED,
            }
            event_type = stage_map.get(stage, EventType.UNKNOWN)
        else:
            # Map event types
            event_type_map = {
                "experiment_completed": EventType.EXPERIMENT_COMPLETED,
                "experiment_failed": EventType.EXPERIMENT_FAILED,
                "corpus_ready": EventType.CORPUS_READY,
                "indexing_done": EventType.INDEXING_DONE,
                "processing_progress": EventType.PROCESSING_PROGRESS,
                "airbyte_document_added": EventType.AIRBYTE_DOCUMENT_ADDED,
            }
            event_type = event_type_map.get(event_type_str, EventType.UNKNOWN)

        # Generate human-readable message
        message = cls._generate_message(event_type, data)

        return cls(type=event_type, data=data, message=message)

    @staticmethod
    def _generate_message(event_type: EventType, data: dict) -> str:
        """Generate message for LLM to process and communicate to user.

        The message should provide enough context for the LLM to generate
        a helpful, informative response to the user.

        Messages are formatted as user messages with system instructions embedded.
        """
        # System instruction prefix for all backend events
        system_instruction = (
            "[SYSTEM INSTRUCTION: This is a backend notification about experiment progress. "
            "You MUST acknowledge this event to the user in a friendly way and explain what "
            "happened. Do NOT treat this as a user question - it's an automatic status update.]\n\n"
        )

        if event_type == EventType.EXPERIMENT_COMPLETED:
            exp_name = data.get("name", data.get("experiment_id", "Unknown"))
            exp_id = data.get("experiment_id", "")
            metrics = data.get("metrics", {})
            metrics_str = ""
            if metrics:
                metrics_str = f" Metrics: {metrics}"
            return (
                f"{system_instruction}"
                f"[BACKEND_EVENT: EXPERIMENT_COMPLETED] "
                f"Experiment '{exp_name}' (ID: {exp_id}) has completed successfully.{metrics_str} "
                f"Please inform the user about this completion and ask if they want to see "
                f"detailed results or proceed with the next steps."
            )

        if event_type == EventType.EXPERIMENT_FAILED:
            exp_name = data.get("name", data.get("experiment_id", "Unknown"))
            exp_id = data.get("experiment_id", "")
            error = data.get("error", "Unknown error")
            return (
                f"{system_instruction}"
                f"[BACKEND_EVENT: EXPERIMENT_FAILED] "
                f"Experiment '{exp_name}' (ID: {exp_id}) has failed. Error: {error}. "
                f"Please inform the user about this failure and suggest possible next steps "
                f"(retry, adjust parameters, or skip this experiment)."
            )

        if event_type == EventType.CORPUS_READY:
            corpus_name = data.get("name", data.get("corpus_id", "Unknown"))
            corpus_id = data.get("corpus_id", "")
            doc_count = data.get("document_count", "")
            return (
                f"{system_instruction}"
                f"[BACKEND_EVENT: CORPUS_READY] "
                f"Corpus '{corpus_name}' (ID: {corpus_id}) is now ready. "
                f"Documents processed: {doc_count}. "
                f"Please inform the user and suggest proceeding to the next workflow step "
                f"(creating evaluation dataset or planning experiments)."
            )

        if event_type == EventType.INDEXING_DONE:
            doc_count = data.get("document_count", "unknown number of")
            index_id = data.get("index_id", "")
            return (
                f"{system_instruction}"
                f"[BACKEND_EVENT: INDEXING_DONE] "
                f"Indexing completed successfully. {doc_count} documents indexed. "
                f"Index ID: {index_id}. "
                f"Please inform the user that indexing is complete and they can now "
                f"run experiments on this data."
            )

        if event_type == EventType.PROCESSING_PROGRESS:
            progress = data.get("progress", 0)
            total = data.get("total", 100)
            message = data.get("message", "Processing...")
            pct = int((progress / total) * 100) if total else 0
            return (
                f"{system_instruction}"
                f"[BACKEND_EVENT: PROCESSING_PROGRESS] "
                f"Progress update: {progress}/{total} ({pct}%) - {message}"
            )

        # Pipeline stage events
        if event_type == EventType.READING_COMPLETED:
            exp_iter_id = data.get("experiment_iteration_id", "")
            details = data.get("details", {})
            reading_strategy = details.get("reading_strategy", "unknown")
            return (
                f"{system_instruction}"
                f"[PIPELINE: READING_COMPLETED] "
                f"Document reading completed for experiment iteration {exp_iter_id}. "
                f"Reading strategy: {reading_strategy}. "
                f"Please inform the user that documents have been read and chunking is next."
            )

        if event_type == EventType.CHUNKING_COMPLETED:
            exp_iter_id = data.get("experiment_iteration_id", "")
            details = data.get("details", {})
            chunking_strategy = details.get("chunking_strategy", "unknown")
            return (
                f"{system_instruction}"
                f"[PIPELINE: CHUNKING_COMPLETED] "
                f"Document chunking completed for experiment iteration {exp_iter_id}. "
                f"Chunking strategy: {chunking_strategy}. "
                f"Please inform the user that documents have been chunked and embedding is next."
            )

        if event_type == EventType.EMBEDDING_COMPLETED:
            exp_iter_id = data.get("experiment_iteration_id", "")
            details = data.get("details", {})
            embedder = details.get("embedder", "unknown")
            return (
                f"{system_instruction}"
                f"[PIPELINE: EMBEDDING_COMPLETED] "
                f"Chunk embedding completed for experiment iteration {exp_iter_id}. "
                f"Embedder: {embedder}. "
                f"Please inform the user that embeddings are ready and indexing is next."
            )

        if event_type == EventType.CATEGORY_EMBEDDING_COMPLETED:
            exp_iter_id = data.get("experiment_iteration_id", "")
            details = data.get("details", {})
            categories_count = details.get("categories_count", 0)
            return (
                f"{system_instruction}"
                f"[PIPELINE: CATEGORY_EMBEDDING_COMPLETED] "
                f"Category embedding completed for experiment iteration {exp_iter_id}. "
                f"Categories processed: {categories_count}. "
                f"Please inform the user that category embeddings are ready."
            )

        if event_type == EventType.INDEXING_COMPLETED:
            exp_iter_id = data.get("experiment_iteration_id", "")
            details = data.get("details", {})
            vector_storage = details.get("vector_storage", "unknown")
            return (
                f"{system_instruction}"
                f"[PIPELINE: INDEXING_COMPLETED] "
                f"Vector indexing completed for experiment iteration {exp_iter_id}. "
                f"Vector storage: {vector_storage}. "
                f"Please inform the user that indexing is complete and RAG evaluation is next."
            )

        if event_type == EventType.RAG_COMPLETED:
            exp_iter_id = data.get("experiment_iteration_id", "")
            details = data.get("details", {})
            metrics = details.get("metrics", {})
            generation_method = details.get("generation_method", "unknown")

            # Extract question and answer if available
            question = details.get("question", "")
            answer = details.get("answer", "")
            ground_truth = details.get("ground_truth", "")

            # Build message with Q&A context
            message = (
                f"{system_instruction}"
                f"[PIPELINE: RAG_COMPLETED] "
                f"RAG pipeline completed for experiment iteration {exp_iter_id}. "
                f"Generation method: {generation_method}. "
                f"Metrics: {metrics}."
            )

            # Add Q&A details if available
            if question and answer:
                message += "\n\nExample from this run:\n"
                message += f"Question: {question}\n"
                message += f"Generated Answer: {answer}"
                if ground_truth:
                    message += f"\nGround Truth: {ground_truth}"

            message += (
                "\n\nPlease inform the user that the RAG pipeline has completed successfully, "
                "show the metrics, and if available, show the example question and answer."
            )

            return message

        if event_type == EventType.EXPERIMENT_ITERATION_COMPLETED:
            exp_iter_id = data.get("experiment_iteration_id", "")
            details = data.get("details", {})
            all_metrics = details.get("all_rag_metrics", [])
            num_configs = len(all_metrics)

            # Summarize metrics
            metrics_summary = ""
            if all_metrics:
                # Show first few configs as preview
                preview_count = min(3, num_configs)
                metrics_summary = (
                    f"\n\nPreview of results (showing {preview_count}/{num_configs} "
                    f"configurations):\n"
                )
                for i, metric in enumerate(all_metrics[:preview_count]):
                    metrics_summary += (
                        f"{i + 1}. {metric.get('reading_strategy', 'N/A')} / "
                        f"{metric.get('chunking_strategy', 'N/A')} / "
                        f"{metric.get('embedder', 'N/A')} / "
                        f"{metric.get('vector_storage', 'N/A')} / "
                        f"{metric.get('generation_method', 'N/A')}\n"
                        f"   Metrics: {metric.get('metrics', {})}\n"
                    )

            return (
                f"{system_instruction}"
                f"[EXPERIMENT_ITERATION_COMPLETED] "
                f"Experiment iteration {exp_iter_id} has fully completed! "
                f"All {num_configs} RAG pipeline configurations have been evaluated."
                f"{metrics_summary}\n"
                f"Please inform the user that the experiment iteration is complete and ask if "
                f"they want to:\n"
                f"1. View detailed results for all configurations\n"
                f"2. Compare metrics across configurations\n"
                f"3. Run another experiment iteration with different parameters"
            )

        if event_type == EventType.AIRBYTE_DOCUMENT_ADDED:
            sink_name = data.get("sink_name", "Unknown")
            stream = data.get("stream", "unknown")
            document_id = data.get("document_id", "")
            return (
                f"{system_instruction}"
                f"[AIRBYTE_DOCUMENT_ADDED] "
                f"New document added from Airbyte sink '{sink_name}' (stream: {stream}). "
                f"Document ID: {document_id}. "
                f"Briefly inform the user that a new document has been received from Airbyte."
            )

        return f"{system_instruction}[BACKEND_EVENT: UNKNOWN] Received event with data: {data}"


# Type for event callback (sync or async)
EventCallback = Callable[[BackendEvent], None | Awaitable[None]]
ProgressCallback = Callable[[float, float | None, str | None], None | Awaitable[None]]


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
        logger.debug(f"Started event listener for project {self.project_id}")

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

        logger.debug("Event listener stopped")

    async def _listen_loop(self) -> None:
        """Main listening loop with reconnection."""
        from websockets.asyncio.client import connect

        while self._running:
            try:
                headers = {"X-API-Token": self.token}
                async with connect(
                    self.ws_url,
                    additional_headers=headers,
                    ping_interval=20,  # Send keepalive ping every 20 seconds
                    ping_timeout=10,  # Wait 10 seconds for pong response
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

        # Skip heartbeat events (keepalive pings from server)
        # Heartbeat is logged at TRACE level to avoid cluttering output
        if event_type == "heartbeat":
            logger.debug(f"[WS EVENT] Heartbeat received: {raw.get('data', {})}")
            return

        # Parse as backend event
        event = BackendEvent.from_ws_message(raw)

        # Handle progress events separately (future: progress bar)
        if event.type == EventType.PROCESSING_PROGRESS and self.on_progress:
            progress = event.data.get("progress", 0)
            total = event.data.get("total")
            msg = event.data.get("message")
            result = self.on_progress(progress, total, msg)
            if asyncio.iscoroutine(result):
                await result
            return

        # Invoke event callback (supports both sync and async)
        if self.on_event and event.type != EventType.UNKNOWN:
            try:
                result = self.on_event(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in event callback: {e}", exc_info=True)

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._ws is not None and self._running
