"""Unit tests for enterprise mode components.

Tests for:
- MCPHttpClient: HTTP MCP client for API Gateway
- MessagePersister: Message persistence to API Gateway
- EventListener: WebSocket event listener for backend events
- EnterpriseREPL: Enterprise mode REPL
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from donkit_ragops.enterprise.event_listener import (
    BackendEvent,
    EventListener,
    EventType,
)
from donkit_ragops.enterprise.message_persister import MessagePersister
from donkit_ragops.mcp.http_client import MCPHttpClient

# ============================================================================
# MCPHttpClient Tests
# ============================================================================


class TestMCPHttpClientInitialization:
    """Test MCPHttpClient initialization."""

    def test_initialization_with_required_params(self) -> None:
        """Test initialization with required parameters."""
        client = MCPHttpClient(
            url="https://api.example.com/mcp",
            token="test-token",
        )

        assert client.url == "https://api.example.com/mcp"
        assert client.token == "test-token"
        assert client.timeout == 60.0  # default

    def test_initialization_with_custom_timeout(self) -> None:
        """Test initialization with custom timeout."""
        client = MCPHttpClient(
            url="https://api.example.com/mcp",
            token="test-token",
            timeout=30.0,
        )

        assert client.timeout == 30.0

    def test_initialization_with_progress_callback(self) -> None:
        """Test initialization with progress callback."""
        callback = MagicMock()
        client = MCPHttpClient(
            url="https://api.example.com/mcp",
            token="test-token",
            progress_callback=callback,
        )

        assert client.progress_callback is callback

    def test_create_transport_sets_auth(self) -> None:
        """Test that transport is created with correct URL and auth."""
        from fastmcp.client.auth.bearer import BearerAuth

        client = MCPHttpClient(
            url="https://api.example.com/mcp",
            token="my-secret-token",
        )

        transport = client._create_transport()

        # Transport should have the URL and auth configured
        assert transport.url == "https://api.example.com/mcp"
        # FastMCP wraps string tokens in BearerAuth
        assert isinstance(transport.auth, BearerAuth)
        assert transport.auth.token.get_secret_value() == "my-secret-token"


class TestMCPHttpClientToolListing:
    """Test MCPHttpClient tool listing."""

    @pytest.mark.asyncio
    async def test_alist_tools_success(self) -> None:
        """Test successful tool listing."""
        # Mock Client creation to avoid real connection
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            # Mock tool response
            mock_tool = MagicMock()
            mock_tool.name = "test_tool"
            mock_tool.description = "A test tool"
            mock_tool.inputSchema = {
                "type": "object",
                "properties": {"param1": {"type": "string"}},
            }

            with patch.object(mock_client, "__aenter__", new_callable=AsyncMock) as mock_aenter:
                mock_client_instance = AsyncMock()
                mock_client_instance.list_tools = AsyncMock(return_value=[mock_tool])
                mock_aenter.return_value = mock_client_instance

                tools = await client.alist_tools()

            assert len(tools) == 1
            assert tools[0]["name"] == "test_tool"
            assert tools[0]["description"] == "A test tool"
            assert "properties" in tools[0]["parameters"]

    @pytest.mark.asyncio
    async def test_alist_tools_with_wrapped_schema(self) -> None:
        """Test tool listing with FastMCP wrapped schema."""
        # Mock Client creation to avoid real connection
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            # Mock tool with wrapped schema
            mock_tool = MagicMock()
            mock_tool.name = "wrapped_tool"
            mock_tool.description = "Tool with wrapped schema"
            mock_tool.inputSchema = {
                "type": "object",
                "properties": {"args": {"$ref": "#/$defs/ArgsModel"}},
                "$defs": {
                    "ArgsModel": {
                        "type": "object",
                        "properties": {"file_path": {"type": "string"}},
                        "required": ["file_path"],
                    }
                },
            }

            with patch.object(mock_client, "__aenter__", new_callable=AsyncMock) as mock_aenter:
                mock_client_instance = AsyncMock()
                mock_client_instance.list_tools = AsyncMock(return_value=[mock_tool])
                mock_aenter.return_value = mock_client_instance

                tools = await client.alist_tools()

            assert len(tools) == 1
            # Should unwrap the schema
            assert "file_path" in tools[0]["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_alist_tools_connection_error(self) -> None:
        """Test tool listing with connection error."""
        # Mock transport creation to avoid real connection
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            with patch.object(
                client.client, "__aenter__", new_callable=AsyncMock
            ) as mock_aenter:
                mock_aenter.side_effect = ConnectionError("Failed")

                with pytest.raises(ConnectionError):
                    await client.alist_tools()

    @pytest.mark.asyncio
    async def test_alist_tools_cancellation(self) -> None:
        """Test tool listing handles cancellation."""
        # Mock transport creation to avoid real connection
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            with patch.object(
                client.client, "__aenter__", new_callable=AsyncMock
            ) as mock_aenter:
                mock_aenter.side_effect = asyncio.CancelledError()

                with pytest.raises(asyncio.CancelledError):
                    await client.alist_tools()

    def test_list_tools_sync_success(self) -> None:
        """Test synchronous tool listing."""
        client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

        with patch.object(client, "alist_tools", new_callable=AsyncMock) as mock_alist:
            mock_alist.return_value = [{"name": "tool1", "description": "Tool 1", "parameters": {}}]

            tools = client.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "tool1"

    def test_list_tools_keyboard_interrupt(self) -> None:
        """Test that KeyboardInterrupt returns empty list."""
        client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

        with patch.object(client, "alist_tools", new_callable=AsyncMock) as mock_alist:
            mock_alist.side_effect = KeyboardInterrupt()

            tools = client.list_tools()

        assert tools == []


class TestMCPHttpClientToolCalling:
    """Test MCPHttpClient tool calling."""

    @pytest.mark.asyncio
    async def test_acall_tool_success(self) -> None:
        """Test successful tool call."""
        # Mock transport creation to avoid real connection
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            mock_content = MagicMock()
            mock_content.text = "Tool executed successfully"
            mock_result = MagicMock()
            mock_result.content = [mock_content]

            with patch.object(
                client.client, "__aenter__", new_callable=AsyncMock
            ) as mock_aenter:
                mock_client_instance = AsyncMock()
                mock_client_instance.call_tool = AsyncMock(return_value=mock_result)
                mock_aenter.return_value = mock_client_instance

                result = await client.acall_tool("test_tool", {"param": "value"})

            assert result == "Tool executed successfully"
            # Verify arguments were passed directly (no wrapping for HTTP transport)
            mock_client_instance.call_tool.assert_called_once()
            call_args = mock_client_instance.call_tool.call_args
            assert call_args[0][0] == "test_tool"
            assert call_args[0][1] == {"param": "value"}

    @pytest.mark.asyncio
    async def test_acall_tool_with_data_result(self) -> None:
        """Test tool call when result has data instead of content."""
        # Mock transport creation to avoid real connection
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            mock_result = MagicMock()
            mock_result.content = None
            mock_result.data = {"key": "value"}

            with patch.object(
                client.client, "__aenter__", new_callable=AsyncMock
            ) as mock_aenter:
                mock_client_instance = AsyncMock()
                mock_client_instance.call_tool = AsyncMock(return_value=mock_result)
                mock_aenter.return_value = mock_client_instance

                result = await client.acall_tool("test_tool", {})

            assert isinstance(result, str)
            assert json.loads(result) == {"key": "value"}

    @pytest.mark.asyncio
    async def test_acall_tool_empty_arguments(self) -> None:
        """Test tool call with empty arguments."""
        # Mock transport creation to avoid real connection
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            mock_content = MagicMock()
            mock_content.text = "Success"
            mock_result = MagicMock()
            mock_result.content = [mock_content]

            with patch.object(
                client.client, "__aenter__", new_callable=AsyncMock
            ) as mock_aenter:
                mock_client_instance = AsyncMock()
                mock_client_instance.call_tool = AsyncMock(return_value=mock_result)
                mock_aenter.return_value = mock_client_instance

                result = await client.acall_tool("test_tool", {})

            assert result == "Success"

    @pytest.mark.asyncio
    async def test_acall_tool_cancellation(self) -> None:
        """Test tool call handles cancellation."""
        # Mock transport creation to avoid real connection
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            with patch.object(
                client.client, "__aenter__", new_callable=AsyncMock
            ) as mock_aenter:
                mock_aenter.side_effect = asyncio.CancelledError()

                with pytest.raises(asyncio.CancelledError):
                    await client.acall_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_acall_tool_keyboard_interrupt(self) -> None:
        """Test tool call propagates KeyboardInterrupt."""
        # Mock transport creation to avoid real connection
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            with patch.object(
                client.client, "__aenter__", new_callable=AsyncMock
            ) as mock_aenter:
                mock_aenter.side_effect = KeyboardInterrupt()

                with pytest.raises(KeyboardInterrupt):
                    await client.acall_tool("test_tool", {})

    def test_call_tool_sync_success(self) -> None:
        """Test synchronous tool call."""
        client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

        with patch.object(client, "acall_tool", new_callable=AsyncMock) as mock_acall:
            mock_acall.return_value = "Tool result"

            result = client.call_tool("test_tool", {"param": "value"})

        assert result == "Tool result"

    def test_call_tool_keyboard_interrupt(self) -> None:
        """Test that KeyboardInterrupt is propagated."""
        client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

        with patch.object(client, "acall_tool", new_callable=AsyncMock) as mock_acall:
            mock_acall.side_effect = KeyboardInterrupt()

            with pytest.raises(KeyboardInterrupt):
                client.call_tool("test_tool", {})


class TestMCPHttpClientProgress:
    """Test MCPHttpClient progress handling."""

    @pytest.mark.asyncio
    async def test_progress_handler_with_callback(self) -> None:
        """Test that progress callback is called."""
        callback = MagicMock()
        client = MCPHttpClient(
            url="https://api.example.com/mcp",
            token="token",
            progress_callback=callback,
        )

        await client._MCPHttpClient__progress_handler(50, 100, "Processing...")

        callback.assert_called_once_with(50, 100, "Processing...")

    @pytest.mark.asyncio
    async def test_progress_handler_without_callback(self) -> None:
        """Test progress handler works without callback."""
        client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

        # Should not raise
        await client._MCPHttpClient__progress_handler(50, 100, "Processing...")


# ============================================================================
# MessagePersister Tests
# ============================================================================


class TestMessagePersister:
    """Test MessagePersister functionality."""

    @pytest.fixture
    def mock_api_client(self) -> MagicMock:
        """Create mock API client."""
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.add_message = AsyncMock()
        return client

    @pytest.fixture
    def persister(self, mock_api_client: MagicMock) -> MessagePersister:
        """Create MessagePersister with mock client."""
        return MessagePersister(
            api_client=mock_api_client,
            project_id="12345678-1234-5678-1234-567812345678",
        )

    @pytest.mark.asyncio
    async def test_persist_user_message(
        self, persister: MessagePersister, mock_api_client: MagicMock
    ) -> None:
        """Test persisting user message."""
        await persister.persist_user_message("Hello, world!")

        mock_api_client.add_message.assert_called_once()
        request = mock_api_client.add_message.call_args[0][0]
        assert request.message.role == "user"
        assert request.message.content == "Hello, world!"

    @pytest.mark.asyncio
    async def test_persist_user_message_with_files(
        self, persister: MessagePersister, mock_api_client: MagicMock
    ) -> None:
        """Test persisting user message with attached files."""
        await persister.persist_user_message(
            "Check these files",
            attached_files=["/path/to/file.pdf"],
            file_analysis={"file.pdf": {"pages": 10}},
        )

        mock_api_client.add_message.assert_called_once()
        request = mock_api_client.add_message.call_args[0][0]
        assert request.message.role == "user"
        assert request.message.attached_files == ["/path/to/file.pdf"]
        assert request.message.file_analysis == {"file.pdf": {"pages": 10}}

    @pytest.mark.asyncio
    async def test_persist_assistant_message(
        self, persister: MessagePersister, mock_api_client: MagicMock
    ) -> None:
        """Test persisting assistant message."""
        await persister.persist_assistant_message("I'll help you with that.")

        mock_api_client.add_message.assert_called_once()
        request = mock_api_client.add_message.call_args[0][0]
        assert request.message.role == "assistant"
        assert request.message.content == "I'll help you with that."

    @pytest.mark.asyncio
    async def test_persist_assistant_message_with_tool_calls(
        self, persister: MessagePersister, mock_api_client: MagicMock
    ) -> None:
        """Test persisting assistant message with tool calls."""
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "read_file", "arguments": "{}"},
            }
        ]
        await persister.persist_assistant_message(content=None, tool_calls=tool_calls)

        mock_api_client.add_message.assert_called_once()
        request = mock_api_client.add_message.call_args[0][0]
        assert request.message.role == "assistant"
        assert request.message.tool_calls == tool_calls

    @pytest.mark.asyncio
    async def test_persist_tool_result(
        self, persister: MessagePersister, mock_api_client: MagicMock
    ) -> None:
        """Test persisting tool result."""
        await persister.persist_tool_result(
            tool_name="read_file",
            tool_call_id="call_1",
            content="File contents here",
        )

        mock_api_client.add_message.assert_called_once()
        request = mock_api_client.add_message.call_args[0][0]
        assert request.message.role == "tool"
        assert request.message.tool_name == "read_file"
        assert request.message.tool_call_id == "call_1"
        assert request.message.content == "File contents here"

    @pytest.mark.asyncio
    async def test_persist_message_generic(
        self, persister: MessagePersister, mock_api_client: MagicMock
    ) -> None:
        """Test generic persist_message method."""
        await persister.persist_message(role="system", content="System notification")

        mock_api_client.add_message.assert_called_once()
        request = mock_api_client.add_message.call_args[0][0]
        assert request.message.role == "system"
        assert request.message.content == "System notification"

    @pytest.mark.asyncio
    async def test_persist_handles_error_gracefully(
        self, persister: MessagePersister, mock_api_client: MagicMock
    ) -> None:
        """Test that persistence errors are handled gracefully."""
        mock_api_client.add_message.side_effect = Exception("API Error")

        # Should not raise
        await persister.persist_user_message("Test message")


# ============================================================================
# EventListener Tests
# ============================================================================


class TestBackendEvent:
    """Test BackendEvent parsing."""

    def test_parse_experiment_completed(self) -> None:
        """Test parsing experiment completed event."""
        raw = {
            "type": "experiment_completed",
            "data": {"name": "test-experiment", "experiment_id": "exp-123"},
        }

        event = BackendEvent.from_ws_message(raw)

        assert event.type == EventType.EXPERIMENT_COMPLETED
        assert "test-experiment" in event.message
        assert "completed" in event.message.lower()

    def test_parse_experiment_failed(self) -> None:
        """Test parsing experiment failed event."""
        raw = {
            "type": "experiment_failed",
            "data": {"name": "test-experiment", "error": "Out of memory"},
        }

        event = BackendEvent.from_ws_message(raw)

        assert event.type == EventType.EXPERIMENT_FAILED
        assert "test-experiment" in event.message
        assert "failed" in event.message.lower()
        assert "Out of memory" in event.message

    def test_parse_corpus_ready(self) -> None:
        """Test parsing corpus ready event."""
        raw = {
            "type": "corpus_ready",
            "data": {"name": "my-corpus", "corpus_id": "corpus-456"},
        }

        event = BackendEvent.from_ws_message(raw)

        assert event.type == EventType.CORPUS_READY
        assert "my-corpus" in event.message
        assert "ready" in event.message.lower()

    def test_parse_indexing_done(self) -> None:
        """Test parsing indexing done event."""
        raw = {
            "type": "indexing_done",
            "data": {"document_count": 100},
        }

        event = BackendEvent.from_ws_message(raw)

        assert event.type == EventType.INDEXING_DONE
        assert "100" in event.message
        assert "indexed" in event.message.lower()

    def test_parse_processing_progress(self) -> None:
        """Test parsing processing progress event."""
        raw = {
            "type": "processing_progress",
            "data": {"progress": 50, "total": 100, "message": "Processing files..."},
        }

        event = BackendEvent.from_ws_message(raw)

        assert event.type == EventType.PROCESSING_PROGRESS
        assert "50/100" in event.message

    def test_parse_unknown_event(self) -> None:
        """Test parsing unknown event type."""
        raw = {
            "type": "some_unknown_event",
            "data": {"foo": "bar"},
        }

        event = BackendEvent.from_ws_message(raw)

        assert event.type == EventType.UNKNOWN


class TestEventListener:
    """Test EventListener functionality."""

    def test_initialization(self) -> None:
        """Test EventListener initialization."""
        listener = EventListener(
            base_url="https://api.example.com",
            token="test-token",
            project_id="project-123",
        )

        assert listener.base_url == "https://api.example.com"
        assert listener.token == "test-token"
        assert listener.project_id == "project-123"
        assert not listener._running

    def test_ws_url_https(self) -> None:
        """Test WebSocket URL generation from HTTPS."""
        listener = EventListener(
            base_url="https://api.example.com",
            token="token",
            project_id="proj-123",
        )

        assert listener.ws_url == "wss://api.example.com/agent/ws?project_id=proj-123"

    def test_ws_url_http(self) -> None:
        """Test WebSocket URL generation from HTTP."""
        listener = EventListener(
            base_url="http://localhost:8080",
            token="token",
            project_id="proj-123",
        )

        assert listener.ws_url == "ws://localhost:8080/agent/ws?project_id=proj-123"

    def test_ws_url_trailing_slash(self) -> None:
        """Test WebSocket URL generation with trailing slash."""
        listener = EventListener(
            base_url="https://api.example.com/",
            token="token",
            project_id="proj-123",
        )

        assert listener.ws_url == "wss://api.example.com/agent/ws?project_id=proj-123"

    @pytest.mark.asyncio
    async def test_start_and_stop(self) -> None:
        """Test starting and stopping listener."""
        listener = EventListener(
            base_url="https://api.example.com",
            token="token",
            project_id="proj-123",
        )

        # Mock the listen loop to avoid actual WebSocket connection
        with patch.object(listener, "_listen_loop", new_callable=AsyncMock):
            await listener.start()
            assert listener._running
            assert listener._task is not None

            await listener.stop()
            assert not listener._running
            assert listener._task is None

    @pytest.mark.asyncio
    async def test_handle_message_backend_event(self) -> None:
        """Test handling backend event message."""
        callback = MagicMock()
        listener = EventListener(
            base_url="https://api.example.com",
            token="token",
            project_id="proj-123",
            on_event=callback,
        )

        message = json.dumps(
            {
                "type": "experiment_completed",
                "data": {"name": "test-exp"},
            }
        )

        await listener._handle_message(message)

        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert event.type == EventType.EXPERIMENT_COMPLETED

    @pytest.mark.asyncio
    async def test_handle_message_chat_message_ignored(self) -> None:
        """Test that chat messages are ignored."""
        callback = MagicMock()
        listener = EventListener(
            base_url="https://api.example.com",
            token="token",
            project_id="proj-123",
            on_event=callback,
        )

        message = json.dumps({"type": "chat_message", "data": {}})

        await listener._handle_message(message)

        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_agent_thinking_ignored(self) -> None:
        """Test that agent thinking events are ignored."""
        callback = MagicMock()
        listener = EventListener(
            base_url="https://api.example.com",
            token="token",
            project_id="proj-123",
            on_event=callback,
        )

        message = json.dumps({"type": "agent_thinking", "data": {}})

        await listener._handle_message(message)

        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_progress_callback(self) -> None:
        """Test progress callback is called for progress events."""
        progress_callback = MagicMock()
        listener = EventListener(
            base_url="https://api.example.com",
            token="token",
            project_id="proj-123",
            on_progress=progress_callback,
        )

        message = json.dumps(
            {
                "type": "processing_progress",
                "data": {"progress": 50, "total": 100, "message": "Working..."},
            }
        )

        await listener._handle_message(message)

        progress_callback.assert_called_once_with(50, 100, "Working...")

    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self) -> None:
        """Test handling invalid JSON message."""
        listener = EventListener(
            base_url="https://api.example.com",
            token="token",
            project_id="proj-123",
        )

        # Should not raise
        await listener._handle_message("not valid json")

    @pytest.mark.asyncio
    async def test_handle_message_callback_error(self) -> None:
        """Test that callback errors are handled gracefully."""
        callback = MagicMock(side_effect=Exception("Callback error"))
        listener = EventListener(
            base_url="https://api.example.com",
            token="token",
            project_id="proj-123",
            on_event=callback,
        )

        message = json.dumps(
            {
                "type": "experiment_completed",
                "data": {"name": "test"},
            }
        )

        # Should not raise
        await listener._handle_message(message)

    def test_is_connected_false_initially(self) -> None:
        """Test that is_connected is False initially."""
        listener = EventListener(
            base_url="https://api.example.com",
            token="token",
            project_id="proj-123",
        )

        assert not listener.is_connected


# ============================================================================
# EnterpriseREPL Tests
# ============================================================================


class TestEnterpriseREPL:
    """Test EnterpriseREPL functionality."""

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create mock REPL context."""

        context = MagicMock()
        context.history = []
        context.transcript = []
        context.ui = MagicMock()
        context.ui.text_input = MagicMock(return_value="")
        context.ui.print = MagicMock()
        context.ui.print_error = MagicMock()
        context.ui.print_warning = MagicMock()
        context.ui.print_success = MagicMock()
        context.ui.print_styled = MagicMock()
        context.ui.print_markdown = MagicMock()
        context.ui.newline = MagicMock()
        context.ui.create_spinner = MagicMock(return_value=MagicMock())
        context.ui.create_progress = MagicMock(return_value=MagicMock())
        context.provider = None
        context.provider_name = "donkit"
        context.model = None
        context.agent = None
        context.mcp_clients = []
        context.agent_settings = None
        context.system_prompt = "You are a helpful assistant."
        context.session_started_at = 0.0
        context.show_checklist = False
        context.renderer = None
        context.render_helper = None
        context.mcp_handler = None
        return context

    @pytest.fixture
    def mock_api_client(self) -> MagicMock:
        """Create mock API client."""
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        # Mock get_me
        mock_user = MagicMock()
        mock_user.id = "test-user-123"
        mock_user.first_name = "Test User"
        client.get_me = AsyncMock(return_value=mock_user)

        # Mock project creation
        mock_project = MagicMock()
        mock_project.id = "test-project-123"
        client.create_project = AsyncMock(return_value=mock_project)

        return client

    @pytest.fixture
    def mock_persister(self) -> MagicMock:
        """Create mock message persister."""
        persister = MagicMock()
        persister.project_id = ""
        persister.persist_user_message = AsyncMock()
        persister.persist_assistant_message = AsyncMock()
        persister.persist_tool_result = AsyncMock()
        persister.persist_message = AsyncMock()
        return persister

    @pytest.fixture
    def mock_event_listener(self) -> MagicMock:
        """Create mock event listener."""
        listener = MagicMock()
        listener.start = AsyncMock()
        listener.stop = AsyncMock()
        listener.on_event = None
        return listener

    @pytest.mark.asyncio
    async def test_initialization_creates_project(
        self,
        mock_context: MagicMock,
        mock_api_client: MagicMock,
        mock_persister: MagicMock,
        mock_event_listener: MagicMock,
    ) -> None:
        """Test that initialization creates a project."""
        from donkit_ragops.repl.enterprise_repl import EnterpriseREPL

        repl = EnterpriseREPL(
            context=mock_context,
            api_client=mock_api_client,
            message_persister=mock_persister,
            event_listener=mock_event_listener,
        )

        await repl.initialize()

        mock_api_client.create_project.assert_called_once()
        assert repl.project_id == "test-project-123"
        assert mock_persister.project_id == "test-project-123"

    @pytest.mark.asyncio
    async def test_initialization_starts_event_listener(
        self,
        mock_context: MagicMock,
        mock_api_client: MagicMock,
        mock_persister: MagicMock,
        mock_event_listener: MagicMock,
    ) -> None:
        """Test that initialization starts the event listener."""
        from donkit_ragops.repl.enterprise_repl import EnterpriseREPL

        repl = EnterpriseREPL(
            context=mock_context,
            api_client=mock_api_client,
            message_persister=mock_persister,
            event_listener=mock_event_listener,
        )

        await repl.initialize()

        mock_event_listener.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_stops_event_listener(
        self,
        mock_context: MagicMock,
        mock_api_client: MagicMock,
        mock_persister: MagicMock,
        mock_event_listener: MagicMock,
    ) -> None:
        """Test that cleanup stops the event listener."""
        from donkit_ragops.repl.enterprise_repl import EnterpriseREPL

        repl = EnterpriseREPL(
            context=mock_context,
            api_client=mock_api_client,
            message_persister=mock_persister,
            event_listener=mock_event_listener,
        )

        await repl.cleanup()

        mock_event_listener.stop.assert_called_once()



# ============================================================================
# EnterpriseSettings Tests
# ============================================================================


class TestEnterpriseSettings:
    """Test EnterpriseSettings configuration."""

    def test_default_persist_messages_is_true(self) -> None:
        """Test that persist_messages defaults to True."""
        import os

        from donkit_ragops.enterprise.config import EnterpriseSettings

        # Save and clear env var to test default
        original = os.environ.get("DONKIT_ENTERPRISE_PERSIST_MESSAGES")
        try:
            if "DONKIT_ENTERPRISE_PERSIST_MESSAGES" in os.environ:
                del os.environ["DONKIT_ENTERPRISE_PERSIST_MESSAGES"]

            settings = EnterpriseSettings()
            assert settings.persist_messages is True
        finally:
            # Restore original value
            if original is not None:
                os.environ["DONKIT_ENTERPRISE_PERSIST_MESSAGES"] = original

    def test_persist_messages_from_env(self) -> None:
        """Test that persist_messages can be set via environment."""
        import os

        from donkit_ragops.enterprise.config import EnterpriseSettings

        # Save original value
        original = os.environ.get("DONKIT_ENTERPRISE_PERSIST_MESSAGES")

        try:
            os.environ["DONKIT_ENTERPRISE_PERSIST_MESSAGES"] = "true"
            settings = EnterpriseSettings()
            assert settings.persist_messages is True

            os.environ["DONKIT_ENTERPRISE_PERSIST_MESSAGES"] = "false"
            settings = EnterpriseSettings()
            assert settings.persist_messages is False
        finally:
            # Restore original value
            if original is None:
                os.environ.pop("DONKIT_ENTERPRISE_PERSIST_MESSAGES", None)
            else:
                os.environ["DONKIT_ENTERPRISE_PERSIST_MESSAGES"] = original

    def test_default_api_url(self) -> None:
        """Test default API URL."""
        from donkit_ragops.enterprise.config import EnterpriseSettings

        # Fixture clears env vars automatically
        settings = EnterpriseSettings()
        assert settings.api_url == "https://api.donkit.ai"

    def test_mcp_url_property(self) -> None:
        """Test MCP URL property combines api_url and mcp_path."""
        from donkit_ragops.enterprise.config import EnterpriseSettings

        # Fixture clears env vars automatically
        settings = EnterpriseSettings()
        assert settings.mcp_url == "https://api.donkit.ai/mcp"
