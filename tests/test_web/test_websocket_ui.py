"""Tests for WebSocketUI adapter."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from donkit_ragops.web.adapters.websocket_ui import (
    WebLiveContext,
    WebProgressBar,
    WebSocketUI,
    WebSpinner,
)


class TestWebSpinner:
    """Tests for WebSpinner."""

    def test_spinner_creation(self):
        """Test spinner can be created."""
        send_mock = AsyncMock()
        spinner = WebSpinner(send_mock, "Loading...")

        assert spinner._message == "Loading..."
        assert spinner._running is False

    @pytest.mark.asyncio
    async def test_spinner_start_sends_message(self):
        """Test start sends spinner_start message."""
        messages = []

        async def capture(msg):
            messages.append(msg)

        spinner = WebSpinner(capture, "Loading...")
        spinner.start()

        # Allow the async task to run
        await asyncio.sleep(0.01)

        assert len(messages) == 1
        assert messages[0]["type"] == "spinner_start"
        assert messages[0]["message"] == "Loading..."

    @pytest.mark.asyncio
    async def test_spinner_context_manager(self):
        """Test spinner can be used as context manager."""
        messages = []

        async def capture(msg):
            messages.append(msg)

        spinner = WebSpinner(capture, "Loading...")

        with spinner:
            assert spinner._running is True
            # Let the async task run
            await asyncio.sleep(0.01)

        assert spinner._running is False


class TestWebProgressBar:
    """Tests for WebProgressBar."""

    def test_progress_bar_creation(self):
        """Test progress bar can be created."""
        send_mock = AsyncMock()
        progress = WebProgressBar(send_mock, 100, "Processing")

        assert progress._total == 100
        assert progress._description == "Processing"
        assert progress._current == 0

    @pytest.mark.asyncio
    async def test_progress_bar_context_manager(self):
        """Test progress bar can be used as context manager."""
        messages = []

        async def capture(msg):
            messages.append(msg)

        progress = WebProgressBar(capture, 100, "Processing")

        with progress:
            assert progress._running is True
            # Let the async task run
            await asyncio.sleep(0.01)

        assert progress._running is False


class TestWebSocketUI:
    """Tests for WebSocketUI."""

    def test_ui_creation(self):
        """Test WebSocketUI can be created."""
        send_mock = AsyncMock()
        ui = WebSocketUI(send_mock)

        assert ui._send == send_mock

    def test_create_spinner_returns_web_spinner(self):
        """Test create_spinner returns WebSpinner instance."""
        send_mock = AsyncMock()
        ui = WebSocketUI(send_mock)

        spinner = ui.create_spinner("Loading...")

        assert isinstance(spinner, WebSpinner)

    def test_create_progress_returns_web_progress_bar(self):
        """Test create_progress returns WebProgressBar instance."""
        send_mock = AsyncMock()
        ui = WebSocketUI(send_mock)

        progress = ui.create_progress(100, "Processing")

        assert isinstance(progress, WebProgressBar)

    def test_create_live_context_returns_web_live_context(self):
        """Test create_live_context returns WebLiveContext instance."""
        send_mock = AsyncMock()
        ui = WebSocketUI(send_mock)

        live = ui.create_live_context()

        assert isinstance(live, WebLiveContext)

    def test_text_input_raises_not_implemented(self):
        """Test text_input raises NotImplementedError in web context."""
        send_mock = AsyncMock()
        ui = WebSocketUI(send_mock)

        with pytest.raises(NotImplementedError):
            ui.text_input()
