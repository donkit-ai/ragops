"""MCP Client Protocol - abstract interface for MCP clients.

Defines a common interface for both local (stdio) and HTTP MCP clients.
This allows the LLMAgent to work with any transport without knowing the implementation details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from loguru import logger

# Type alias for progress callback
ProgressCallback = Callable[[float, float | None, str | None], None]


class MCPClientProtocol(ABC):
    """Abstract protocol for MCP clients.

    Both local (stdio) and HTTP clients implement this interface,
    allowing the agent to work with any MCP transport transparently.
    """

    @property
    @abstractmethod
    def identifier(self) -> str:
        """Return a string identifying this client (for logging/errors).

        For stdio clients, this is typically the command.
        For HTTP clients, this is typically the URL.
        """
        ...

    @property
    @abstractmethod
    def timeout(self) -> float:
        """Return the timeout in seconds for operations."""
        ...

    @property
    @abstractmethod
    def progress_callback(self) -> ProgressCallback | None:
        """Return the progress callback if set."""
        ...

    @abstractmethod
    def list_tools(self) -> list[dict[str, Any]]:
        """Synchronously list available tools from the MCP server.

        Returns:
            List of tool dictionaries with 'name', 'description', and 'parameters' keys.
        """
        ...

    @abstractmethod
    async def alist_tools(self) -> list[dict[str, Any]]:
        """Asynchronously list available tools from the MCP server.

        Returns:
            List of tool dictionaries with 'name', 'description', and 'parameters' keys.
        """
        ...

    @abstractmethod
    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Synchronously call a tool on the MCP server.

        Args:
            name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            Tool result as a string.
        """
        ...

    @abstractmethod
    async def acall_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Asynchronously call a tool on the MCP server.

        Args:
            name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            Tool result as a string.
        """
        ...

    # -- Shared schema helpers ------------------------------------------------

    @staticmethod
    def _parse_tool_schema(raw_schema: dict[str, Any] | None, tool_name: str) -> dict[str, Any]:
        """Parse and unwrap a FastMCP tool schema.

        FastMCP wraps Pydantic models in {"args": <$ref>}. This method
        follows the $ref to return the actual model schema.
        """
        default: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        }
        if not raw_schema or not isinstance(raw_schema, dict):
            return default
        try:
            if "properties" in raw_schema:
                if "args" in raw_schema["properties"] and "$defs" in raw_schema:
                    args_ref = raw_schema["properties"]["args"].get("$ref")
                    if args_ref and args_ref.startswith("#/$defs/"):
                        def_name = args_ref.split("/")[-1]
                        if def_name in raw_schema["$defs"]:
                            schema = raw_schema["$defs"][def_name].copy()
                            if "$defs" in raw_schema:
                                schema["$defs"] = raw_schema["$defs"]
                            return schema
                else:
                    return raw_schema
        except Exception as e:
            logger.warning(f"Failed to parse schema for tool {tool_name}: {e}")
        return default

    async def connect(self) -> None:
        """Open a persistent connection for reuse across calls.

        No-op by default. Subclasses that benefit from connection reuse
        (e.g. stdio transport) override this to hold the connection open.
        """

    async def disconnect(self) -> None:
        """Close a persistent connection opened by connect().

        No-op by default. Safe to call even if connect() was never called.
        """
