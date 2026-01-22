"""WebSocket-based UI adapter.

Implements the UI protocol by sending events over WebSocket to the client.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from donkit_ragops.ui.components import LiveContext, ProgressBar, Spinner
from donkit_ragops.ui.protocol import UI
from donkit_ragops.ui.styles import StyledText, StyleName


class WebSpinner:
    """Spinner implementation that sends events via WebSocket."""

    def __init__(self, send_func: Callable[[dict], Awaitable[None]], message: str) -> None:
        self._send = send_func
        self._message = message
        self._running = False

    def start(self) -> None:
        """Start the spinner."""
        self._running = True
        asyncio.create_task(
            self._send(
                {
                    "type": "spinner_start",
                    "message": self._message,
                    "timestamp": time.time(),
                }
            )
        )

    def stop(self) -> None:
        """Stop the spinner."""
        if self._running:
            self._running = False
            asyncio.create_task(
                self._send(
                    {
                        "type": "spinner_stop",
                        "timestamp": time.time(),
                    }
                )
            )

    def update(self, message: str) -> None:
        """Update spinner message."""
        self._message = message
        if self._running:
            asyncio.create_task(
                self._send(
                    {
                        "type": "spinner_update",
                        "message": message,
                        "timestamp": time.time(),
                    }
                )
            )

    def __enter__(self) -> WebSpinner:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.stop()


class WebProgressBar:
    """Progress bar implementation that sends events via WebSocket."""

    def __init__(
        self,
        send_func: Callable[[dict], Awaitable[None]],
        total: int,
        description: str,
    ) -> None:
        self._send = send_func
        self._total = total
        self._description = description
        self._current = 0
        self._running = False

    def start(self) -> None:
        """Start the progress bar."""
        self._running = True
        asyncio.create_task(
            self._send(
                {
                    "type": "progress_start",
                    "total": self._total,
                    "description": self._description,
                    "timestamp": time.time(),
                }
            )
        )

    def update(self, current: int, message: str = "") -> None:
        """Update progress."""
        self._current = current
        if self._running:
            asyncio.create_task(
                self._send(
                    {
                        "type": "progress_update",
                        "current": current,
                        "total": self._total,
                        "message": message or self._description,
                        "timestamp": time.time(),
                    }
                )
            )

    def advance(self, amount: int = 1) -> None:
        """Advance progress by amount."""
        self._current += amount
        if self._running:
            asyncio.create_task(
                self._send(
                    {
                        "type": "progress_update",
                        "current": self._current,
                        "total": self._total,
                        "timestamp": time.time(),
                    }
                )
            )

    def finish(self) -> None:
        """Mark progress as complete."""
        self._current = self._total
        if self._running:
            asyncio.create_task(
                self._send(
                    {
                        "type": "progress_update",
                        "current": self._total,
                        "total": self._total,
                        "timestamp": time.time(),
                    }
                )
            )

    def stop(self) -> None:
        """Stop the progress bar."""
        if self._running:
            self._running = False
            asyncio.create_task(
                self._send(
                    {
                        "type": "progress_stop",
                        "timestamp": time.time(),
                    }
                )
            )

    def __enter__(self) -> WebProgressBar:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.stop()


class WebLiveContext:
    """Live context implementation that sends events via WebSocket."""

    def __init__(self, send_func: Callable[[dict], Awaitable[None]]) -> None:
        self._send = send_func
        self._content = ""
        self._running = False

    def start(self) -> None:
        """Start live context."""
        self._running = True

    def update(self, content: str) -> None:
        """Update displayed content."""
        self._content = content
        if self._running:
            asyncio.create_task(
                self._send(
                    {
                        "type": "live_update",
                        "content": content,
                        "timestamp": time.time(),
                    }
                )
            )

    def refresh(self) -> None:
        """Force a display refresh."""
        if self._running:
            asyncio.create_task(
                self._send(
                    {
                        "type": "live_refresh",
                        "content": self._content,
                        "timestamp": time.time(),
                    }
                )
            )

    def stop(self) -> None:
        """Stop live context."""
        self._running = False

    def __enter__(self) -> WebLiveContext:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.stop()


class WebSocketUI(UI):
    """UI adapter that sends events via WebSocket to the client.

    This adapter implements the UI protocol by converting all UI operations
    into WebSocket messages that the frontend can render.
    """

    def __init__(self, send_func: Callable[[dict], Awaitable[None]]) -> None:
        """Initialize WebSocket UI.

        Args:
            send_func: Async function to send messages over WebSocket
        """
        self._send = send_func

    async def _async_send(self, message: dict) -> None:
        """Send a message asynchronously."""
        await self._send(message)

    def _fire_and_forget(self, message: dict) -> None:
        """Send a message without waiting (for sync methods)."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_send(message))
        except RuntimeError:
            # No running loop, skip sending
            pass

    # === OUTPUT ===

    def print(self, message: str, style: StyleName | None = None, *, end: str = "\n") -> None:
        """Print a message with optional styling."""
        self._fire_and_forget(
            {
                "type": "content",
                "content": message,
                "style": style.value if style else None,
                "end": end,
                "timestamp": time.time(),
            }
        )

    def print_styled(self, styled_text: StyledText) -> None:
        """Print styled text segments."""
        segments = []
        for style, text in styled_text:
            segments.append(
                {
                    "style": style.value if style else None,
                    "text": text,
                }
            )
        self._fire_and_forget(
            {
                "type": "styled_content",
                "segments": segments,
                "timestamp": time.time(),
            }
        )

    def print_error(self, message: str) -> None:
        """Print an error message."""
        self._fire_and_forget(
            {
                "type": "error_message",
                "content": message,
                "timestamp": time.time(),
            }
        )

    def print_success(self, message: str) -> None:
        """Print a success message."""
        self._fire_and_forget(
            {
                "type": "success_message",
                "content": message,
                "timestamp": time.time(),
            }
        )

    def print_warning(self, message: str) -> None:
        """Print a warning message."""
        self._fire_and_forget(
            {
                "type": "warning_message",
                "content": message,
                "timestamp": time.time(),
            }
        )

    def print_info(self, message: str) -> None:
        """Print an info message."""
        self._fire_and_forget(
            {
                "type": "info_message",
                "content": message,
                "timestamp": time.time(),
            }
        )

    def print_markdown(self, content: str) -> None:
        """Print markdown-formatted content."""
        self._fire_and_forget(
            {
                "type": "markdown",
                "content": content,
                "timestamp": time.time(),
            }
        )

    def print_panel(
        self,
        content: str | list[StyledText],
        title: str = "",
        border_style: StyleName | None = None,
    ) -> None:
        """Print content in a bordered panel."""
        if isinstance(content, str):
            panel_content = content
        else:
            # Convert styled text to serializable format
            lines = []
            for styled_line in content:
                segments = []
                for style, text in styled_line:
                    segments.append(
                        {
                            "style": style.value if style else None,
                            "text": text,
                        }
                    )
                lines.append(segments)
            panel_content = lines

        self._fire_and_forget(
            {
                "type": "panel",
                "content": panel_content,
                "title": title,
                "border_style": border_style.value if border_style else None,
                "timestamp": time.time(),
            }
        )

    def newline(self) -> None:
        """Print a blank line."""
        self._fire_and_forget(
            {
                "type": "newline",
                "timestamp": time.time(),
            }
        )

    def clear(self) -> None:
        """Clear the display."""
        self._fire_and_forget(
            {
                "type": "clear",
                "timestamp": time.time(),
            }
        )

    # === PROGRESS COMPONENTS ===

    def create_spinner(self, message: str = "Loading...") -> Spinner:
        """Create a loading spinner."""
        return WebSpinner(self._send, message)

    def create_progress(self, total: int = 100, description: str = "") -> ProgressBar:
        """Create a progress bar."""
        return WebProgressBar(self._send, total, description)

    # === INTERACTIVE COMPONENTS ===

    def select(
        self,
        choices: list[str],
        title: str = "Select an option",
        default_index: int = 0,
    ) -> str | None:
        """Show interactive selection menu.

        Note: For web UI, this sends a request to the client and waits for response.
        In practice, this would need to be handled differently in an async context.
        For now, returns the default choice.
        """
        self._fire_and_forget(
            {
                "type": "select_request",
                "choices": choices,
                "title": title,
                "default_index": default_index,
                "timestamp": time.time(),
            }
        )
        # In web context, we'd need to wait for client response
        # For now, return the default choice
        if choices and 0 <= default_index < len(choices):
            return choices[default_index]
        return choices[0] if choices else None

    def confirm(self, question: str, default: bool = True) -> bool | None:
        """Show yes/no confirmation dialog.

        Note: For web UI, this sends a request to the client.
        For now, returns the default value.
        """
        self._fire_and_forget(
            {
                "type": "confirm_request",
                "question": question,
                "default": default,
                "timestamp": time.time(),
            }
        )
        # In web context, we'd need to wait for client response
        return default

    def text_input(self, prompt: str = "> ") -> str:
        """Get text input from user.

        Note: For web UI, input comes from WebSocket messages.
        This method is not used in the web context.
        """
        raise NotImplementedError("text_input should not be called in web context")

    # === LIVE UPDATES ===

    def create_live_context(self) -> LiveContext:
        """Create a live-updating display region."""
        return WebLiveContext(self._send)
