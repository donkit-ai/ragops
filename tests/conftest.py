import json

import pytest
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

# Ensure src/ is on sys.path for tests without installation
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

os.environ.setdefault("RAGOPS_API_URL", "http://localhost:8080")


@pytest.fixture(autouse=True, scope="function")
def clear_enterprise_env_vars():
    """Clear enterprise env vars before each test to ensure clean state."""
    # Save original values
    saved_vars = {}
    enterprise_vars = [
        "RAGOPS_DONKIT_BASE_URL",
        "RAGOPS_DONKIT_PERSIST_MESSAGES",
        "RAGOPS_DONKIT_TIMEOUT",
    ]

    for var in enterprise_vars:
        if var in os.environ:
            saved_vars[var] = os.environ[var]
            del os.environ[var]

    yield

    # Restore original values
    for var, value in saved_vars.items():
        os.environ[var] = value


@pytest.fixture(autouse=True)
def disable_loguru():
    """Disable loguru logging during tests to prevent pytest capture issues."""
    import loguru

    # Remove all handlers and disable logging
    loguru.logger.remove()
    # Add a null handler to prevent any logging
    loguru.logger.add(lambda x: None, level="CRITICAL", enqueue=False)
    yield
    # Clean up after test
    loguru.logger.remove()


@pytest.fixture(autouse=True)
def use_plain_ui():
    """Force PlainUI for all tests to avoid prompt_toolkit file handle issues."""
    from donkit_ragops.ui import reset_ui, set_ui_adapter, UIAdapter

    reset_ui()
    set_ui_adapter(UIAdapter.PLAIN)
    yield
    reset_ui()


# ============================================================================
# Reusable Mock Classes (from shared library)
# ============================================================================

from donkit.llm_agent.testing import BaseMockMCPClient, BaseMockProvider  # noqa: F401


# ============================================================================
# Reusable Fixtures
# ============================================================================


@pytest.fixture
def mocked_mcp_client():
    """Pre-configured MCP client mock with common setup.

    Yields a context manager that provides mock_client_class and mock_client_instance.

    Usage:
        with mocked_mcp_client() as (mock_class, mock_instance):
            # Configure mock_instance.list_tools, etc.
            # Your test code here
    """

    @contextmanager
    def _create_mock():
        with patch("donkit_ragops.mcp.client.Client") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client_instance

            with patch("donkit_ragops.mcp.client.StdioTransport"):
                yield mock_client_class, mock_client_instance

    return _create_mock


@pytest.fixture
def mock_mcp_http_client():
    """Create a mocked MCPHttpClient that doesn't make real connections.

    Usage:
        with mock_mcp_http_client() as (client, mock_client):
            # client is MCPHttpClient instance
            # mock_client is the mocked Client for further patching
    """
    from contextlib import contextmanager

    @contextmanager
    def _create_mock():
        with patch("donkit_ragops.mcp.http_client.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            from donkit_ragops.mcp.http_client import MCPHttpClient
            client = MCPHttpClient(url="https://api.example.com/mcp", token="token")

            yield client, mock_client

    return _create_mock


@pytest.fixture
def cli_mocks():
    """Pre-patched CLI dependencies for testing.

    Returns:
        Tuple of (mock_setup, mock_select, mock_repl_handler)
    """
    with (
        patch("donkit_ragops.cli.run_setup_if_needed") as mock_setup,
        patch("donkit_ragops.cli.select_model_at_startup") as mock_select,
        patch("donkit_ragops.cli._run_repl_with_interrupt_handling") as mock_repl_handler,
    ):
        # Default return values
        mock_setup.return_value = True
        mock_select.return_value = ("openai", "gpt-4")
        mock_repl_handler.return_value = None

        yield mock_setup, mock_select, mock_repl_handler


# ============================================================================
# Helper Functions
# ============================================================================


def create_mock_tool(
    name: str,
    handler: Any,
    description: str = "",
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Factory for creating mock tool configurations.

    Args:
        name: Tool name
        handler: Callable that handles tool execution
        description: Tool description
        parameters: Tool parameters schema

    Returns:
        Tool configuration dict
    """
    return {
        "name": name,
        "description": description or f"Mock tool: {name}",
        "parameters": parameters
        or {
            "type": "object",
            "properties": {},
        },
        "handler": handler,
    }


def assert_tool_has_valid_metadata(tool: dict[str, Any]) -> None:
    """Assert that tool has all required metadata fields.

    Args:
        tool: Tool dict to validate
    """
    assert "name" in tool, "Tool missing 'name'"
    assert "description" in tool, "Tool missing 'description'"
    assert "parameters" in tool, "Tool missing 'parameters'"
    assert isinstance(tool["name"], str), "Tool name must be string"
    assert isinstance(tool["description"], str), "Tool description must be string"
    assert isinstance(tool["parameters"], dict), "Tool parameters must be dict"


def assert_tool_schema_is_valid(schema: dict[str, Any]) -> None:
    """Assert that tool schema is valid JSON Schema.

    Args:
        schema: JSON Schema to validate
    """
    assert "type" in schema, "Schema missing 'type'"
    assert schema["type"] == "object", "Schema type must be 'object'"

    if "properties" in schema:
        assert isinstance(schema["properties"], dict), "Schema properties must be dict"

    if "required" in schema:
        assert isinstance(schema["required"], list), "Schema required must be list"
