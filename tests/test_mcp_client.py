"""Unit tests for MCP Client — focusing on real functionality, not just passing tests.

These tests verify that the MCP client:
1. Properly initializes and connects to MCP servers
2. Correctly discovers and parses tool schemas
3. Properly calls tools with correct argument wrapping
4. Handles errors gracefully (server crashes, timeouts, invalid args)
5. Cleans up resources properly
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from donkit_ragops.mcp.client import MCPClient

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mcp_client() -> MCPClient:
    """Create a basic MCP client for testing."""
    return MCPClient(command="python", args=["dummy_server.py"])


@pytest.fixture
def mcp_client_with_callback() -> MCPClient:
    """Create an MCP client with progress callback."""
    callback = Mock()
    return MCPClient(command="python", args=["dummy_server.py"], progress_callback=callback)


# ============================================================================
# Tests: Initialization
# ============================================================================


def test_mcp_client_initialization() -> None:
    """Test that MCPClient initializes with correct parameters."""
    client = MCPClient(command="python", args=["server.py"], timeout=30.0)

    assert client.command == "python"
    assert client.args == ["server.py"]
    assert client.timeout == 30.0


def test_mcp_client_initialization_with_callback() -> None:
    """Test that MCPClient stores progress callback."""
    callback = Mock()
    client = MCPClient(command="python", args=["server.py"], progress_callback=callback)

    assert client.progress_callback is callback


def test_mcp_client_loads_environment() -> None:
    """Test that MCPClient loads environment variables."""
    client = MCPClient(command="python", args=["server.py"])

    # Should have loaded environment (at least os.environ)
    assert isinstance(client._env, dict)
    assert len(client._env) > 0


# ============================================================================
# Tests: Tool Discovery (Async)
# ============================================================================


@pytest.mark.asyncio
async def test_alist_tools_success(mocked_mcp_client) -> None:
    """Test successful tool discovery from MCP server."""
    client = MCPClient(command="python", args=["server.py"])

    # Mock the FastMCP Client
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool"
    mock_tool.inputSchema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"},
        },
        "required": ["param1"],
    }

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.list_tools = AsyncMock(return_value=[mock_tool])
        tools = await client.alist_tools()

    assert len(tools) == 1
    assert tools[0]["name"] == "test_tool"
    assert tools[0]["description"] == "A test tool"
    assert "properties" in tools[0]["parameters"]


@pytest.mark.asyncio
async def test_alist_tools_with_wrapped_schema(mocked_mcp_client) -> None:
    """Test tool discovery with FastMCP wrapped schema (args wrapper)."""
    client = MCPClient(command="python", args=["server.py"])

    # Mock tool with wrapped schema (FastMCP wraps in {"args": <model>})
    mock_tool = MagicMock()
    mock_tool.name = "wrapped_tool"
    mock_tool.description = "Tool with wrapped schema"
    mock_tool.inputSchema = {
        "type": "object",
        "properties": {
            "args": {"$ref": "#/$defs/ArgsModel"},
        },
        "$defs": {
            "ArgsModel": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "count": {"type": "integer"},
                },
                "required": ["file_path"],
            }
        },
    }

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.list_tools = AsyncMock(return_value=[mock_tool])
        tools = await client.alist_tools()

    assert len(tools) == 1
    # Should unwrap the schema
    assert "file_path" in tools[0]["parameters"]["properties"]
    assert "args" not in tools[0]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_alist_tools_connection_error(mocked_mcp_client) -> None:
    """Test tool discovery when connection fails."""
    client = MCPClient(command="nonexistent_command", args=["server.py"])

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.__aenter__ = AsyncMock(side_effect=ConnectionError("Failed to connect"))
        with pytest.raises(ConnectionError):
            await client.alist_tools()


@pytest.mark.asyncio
async def test_alist_tools_cancellation(mocked_mcp_client) -> None:
    """Test tool discovery handles cancellation properly."""
    client = MCPClient(command="python", args=["server.py"])

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.__aenter__ = AsyncMock(side_effect=asyncio.CancelledError("Cancelled"))
        with pytest.raises(asyncio.CancelledError):
            await client.alist_tools()


# ============================================================================
# Tests: Tool Discovery (Sync)
# ============================================================================


def test_list_tools_success(mcp_client: MCPClient) -> None:
    """Test synchronous tool listing."""
    mock_tool = MagicMock()
    mock_tool.name = "sync_tool"
    mock_tool.description = "Synchronous tool"
    mock_tool.inputSchema = {"type": "object", "properties": {}}

    with patch.object(mcp_client, "alist_tools", new_callable=AsyncMock) as mock_alist:
        mock_alist.return_value = [
            {
                "name": "sync_tool",
                "description": "Synchronous tool",
                "parameters": {"type": "object", "properties": {}},
            }
        ]

        tools = mcp_client.list_tools()

    assert len(tools) == 1
    assert tools[0]["name"] == "sync_tool"


def test_list_tools_keyboard_interrupt(mcp_client: MCPClient) -> None:
    """Test that KeyboardInterrupt returns empty list."""
    with patch.object(mcp_client, "alist_tools", new_callable=AsyncMock) as mock_alist:
        mock_alist.side_effect = KeyboardInterrupt()

        tools = mcp_client.list_tools()

    assert tools == []


# ============================================================================
# Tests: Tool Calling (Async)
# ============================================================================


@pytest.mark.asyncio
async def test_acall_tool_success(mocked_mcp_client) -> None:
    """Test successful tool call with proper argument wrapping."""
    client = MCPClient(command="python", args=["server.py"])

    # Mock tool result
    mock_content = MagicMock()
    mock_content.text = "Tool executed successfully"
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.call_tool = AsyncMock(return_value=mock_result)
        result = await client.acall_tool("test_tool", {"param": "value"})

    assert result == "Tool executed successfully"
    # Verify that arguments were wrapped
    mock_instance.call_tool.assert_called_once()
    call_args = mock_instance.call_tool.call_args
    assert call_args[0][0] == "test_tool"
    assert call_args[0][1] == {"args": {"param": "value"}}


@pytest.mark.asyncio
async def test_acall_tool_with_data_result(mocked_mcp_client) -> None:
    """Test tool call when result has data instead of content."""
    client = MCPClient(command="python", args=["server.py"])

    mock_result = MagicMock()
    mock_result.content = None
    mock_result.data = {"key": "value"}

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.call_tool = AsyncMock(return_value=mock_result)
        result = await client.acall_tool("test_tool", {})

    # Should serialize data to JSON
    assert isinstance(result, str)
    assert json.loads(result) == {"key": "value"}


@pytest.mark.asyncio
async def test_acall_tool_empty_arguments(mocked_mcp_client) -> None:
    """Test tool call with empty arguments."""
    client = MCPClient(command="python", args=["server.py"])

    mock_content = MagicMock()
    mock_content.text = "Success"
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.call_tool = AsyncMock(return_value=mock_result)
        result = await client.acall_tool("test_tool", {})

    assert result == "Success"


@pytest.mark.asyncio
async def test_acall_tool_cancellation(mocked_mcp_client) -> None:
    """Test tool call handles cancellation."""
    client = MCPClient(command="python", args=["server.py"])

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.__aenter__ = AsyncMock(side_effect=asyncio.CancelledError("Cancelled"))
        with pytest.raises(asyncio.CancelledError):
            await client.acall_tool("test_tool", {})


@pytest.mark.asyncio
async def test_acall_tool_keyboard_interrupt(mocked_mcp_client) -> None:
    """Test tool call propagates KeyboardInterrupt."""
    client = MCPClient(command="python", args=["server.py"])

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.__aenter__ = AsyncMock(side_effect=KeyboardInterrupt("User interrupted"))
        with pytest.raises(KeyboardInterrupt):
            await client.acall_tool("test_tool", {})


# ============================================================================
# Tests: Tool Calling (Sync)
# ============================================================================


def test_call_tool_success() -> None:
    """Test synchronous tool call."""
    client = MCPClient(command="python", args=["server.py"])

    with patch.object(client, "acall_tool", new_callable=AsyncMock) as mock_acall:
        mock_acall.return_value = "Tool result"

        result = client.call_tool("test_tool", {"param": "value"})

    assert result == "Tool result"


def test_call_tool_keyboard_interrupt() -> None:
    """Test that KeyboardInterrupt is propagated."""
    client = MCPClient(command="python", args=["server.py"])

    with patch.object(client, "acall_tool", new_callable=AsyncMock) as mock_acall:
        mock_acall.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            client.call_tool("test_tool", {})


# ============================================================================
# Tests: Progress Callback
# ============================================================================


@pytest.mark.asyncio
async def test_progress_handler_with_callback(mcp_client_with_callback: MCPClient) -> None:
    """Test that progress callback is called."""
    # Call the progress handler
    await mcp_client_with_callback._MCPClient__progress_handler(50, 100, "Processing...")

    # Verify callback was called
    mcp_client_with_callback.progress_callback.assert_called_once_with(50, 100, "Processing...")


@pytest.mark.asyncio
async def test_progress_handler_without_callback() -> None:
    """Test progress handler works without callback."""
    client = MCPClient(command="python", args=["server.py"])

    # Should not raise
    await client._MCPClient__progress_handler(50, 100, "Processing...")


# ============================================================================
# Tests: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_acall_tool_with_invalid_schema(mocked_mcp_client) -> None:
    """Test tool call handles invalid schema gracefully."""
    client = MCPClient(command="python", args=["server.py"])

    # Tool with invalid schema should still work if call succeeds
    mock_content = MagicMock()
    mock_content.text = "Success despite invalid schema"
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.call_tool = AsyncMock(return_value=mock_result)
        result = await client.acall_tool("test_tool", {"invalid": "args"})

    assert result == "Success despite invalid schema"


def test_mcp_client_timeout_configuration() -> None:
    """Test that timeout is properly configured."""
    client = MCPClient(command="python", args=["server.py"], timeout=5.0)

    assert client.timeout == 5.0


# ============================================================================
# Tests: Persistent Connection Lifecycle
# ============================================================================


@pytest.mark.asyncio
async def test_connect_opens_persistent_connection(mocked_mcp_client) -> None:
    """Test that connect() opens and stores a persistent connection."""
    client = MCPClient(command="python", args=["server.py"])

    assert client._client is None
    assert client._transport is None

    with mocked_mcp_client() as (mock_class, mock_instance):
        await client.connect()

    assert client._client is not None
    assert client._transport is not None


@pytest.mark.asyncio
async def test_connect_is_idempotent(mocked_mcp_client) -> None:
    """Test that calling connect() twice does not create a second connection."""
    client = MCPClient(command="python", args=["server.py"])

    with mocked_mcp_client() as (mock_class, mock_instance):
        await client.connect()
        first_client = client._client

        # Second call should be a no-op
        await client.connect()
        assert client._client is first_client


@pytest.mark.asyncio
async def test_disconnect_clears_state(mocked_mcp_client) -> None:
    """Test that disconnect() clears transport and client state."""
    client = MCPClient(command="python", args=["server.py"])

    with mocked_mcp_client() as (mock_class, mock_instance):
        await client.connect()
        assert client._client is not None

        await client.disconnect()

    assert client._client is None
    assert client._transport is None


@pytest.mark.asyncio
async def test_disconnect_without_connect() -> None:
    """Test that disconnect() is safe to call without connect()."""
    client = MCPClient(command="python", args=["server.py"])

    # Should not raise
    await client.disconnect()
    assert client._client is None


@pytest.mark.asyncio
async def test_persistent_alist_tools(mocked_mcp_client) -> None:
    """Test that alist_tools() reuses persistent connection when connected."""
    client = MCPClient(command="python", args=["server.py"])

    mock_tool = MagicMock()
    mock_tool.name = "persistent_tool"
    mock_tool.description = "A tool"
    mock_tool.inputSchema = {"type": "object", "properties": {}}

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.list_tools = AsyncMock(return_value=[mock_tool])
        await client.connect()

        # alist_tools should use the persistent client (no new Client created)
        initial_call_count = mock_class.call_count
        tools = await client.alist_tools()
        assert mock_class.call_count == initial_call_count  # no new Client

    assert len(tools) == 1
    assert tools[0]["name"] == "persistent_tool"


@pytest.mark.asyncio
async def test_persistent_acall_tool(mocked_mcp_client) -> None:
    """Test that acall_tool() reuses persistent connection when connected."""
    client = MCPClient(command="python", args=["server.py"])

    mock_content = MagicMock()
    mock_content.text = "Persistent result"
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.call_tool = AsyncMock(return_value=mock_result)
        await client.connect()

        initial_call_count = mock_class.call_count
        result = await client.acall_tool("test_tool", {"key": "val"})
        assert mock_class.call_count == initial_call_count  # no new Client

    assert result == "Persistent result"


@pytest.mark.asyncio
async def test_persistent_alist_tools_recovers_on_failure(mocked_mcp_client) -> None:
    """Test that alist_tools() falls back to temp connection when persistent client dies."""
    client = MCPClient(command="python", args=["server.py"])

    mock_tool = MagicMock()
    mock_tool.name = "recovered_tool"
    mock_tool.description = "A tool"
    mock_tool.inputSchema = {"type": "object", "properties": {}}

    with mocked_mcp_client() as (mock_class, mock_instance):
        # First: connect successfully
        await client.connect()
        assert client._client is not None

        # Simulate subprocess death: list_tools raises on persistent client
        call_count = 0

        async def list_tools_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("subprocess died")
            return [mock_tool]

        mock_instance.list_tools = list_tools_side_effect

        # Should recover via temp connection fallback
        tools = await client.alist_tools()

    # Persistent connection should have been torn down
    assert client._client is None
    assert len(tools) == 1
    assert tools[0]["name"] == "recovered_tool"


@pytest.mark.asyncio
async def test_persistent_acall_tool_recovers_on_failure(mocked_mcp_client) -> None:
    """Test that acall_tool() falls back to temp connection when persistent client dies."""
    client = MCPClient(command="python", args=["server.py"])

    mock_content = MagicMock()
    mock_content.text = "Recovered result"
    mock_result = MagicMock()
    mock_result.content = [mock_content]

    with mocked_mcp_client() as (mock_class, mock_instance):
        await client.connect()
        assert client._client is not None

        call_count = 0

        async def call_tool_side_effect(name, args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("subprocess died")
            return mock_result

        mock_instance.call_tool = call_tool_side_effect

        result = await client.acall_tool("test_tool", {"key": "val"})

    assert client._client is None
    assert result == "Recovered result"


@pytest.mark.asyncio
async def test_persistent_acall_tool_propagates_non_transport_error(mocked_mcp_client) -> None:
    """Test that non-transport errors on persistent path propagate without retry."""
    client = MCPClient(command="python", args=["server.py"])

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.call_tool = AsyncMock(side_effect=ValueError("bad tool argument"))
        await client.connect()
        assert client._client is not None

        with pytest.raises(ValueError, match="bad tool argument"):
            await client.acall_tool("test_tool", {"key": "val"})

        # Persistent connection should still be intact (not torn down)
        assert client._client is not None


@pytest.mark.asyncio
async def test_persistent_alist_tools_propagates_non_transport_error(mocked_mcp_client) -> None:
    """Test that non-transport errors on persistent path propagate without retry."""
    client = MCPClient(command="python", args=["server.py"])

    with mocked_mcp_client() as (mock_class, mock_instance):
        mock_instance.list_tools = AsyncMock(side_effect=ValueError("bad schema"))
        await client.connect()
        assert client._client is not None

        with pytest.raises(ValueError, match="bad schema"):
            await client.alist_tools()

        # Persistent connection should still be intact (not torn down)
        assert client._client is not None
