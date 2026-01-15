"""MCP Client Protocol - abstract interface for MCP clients.

Defines a common interface for both local (stdio) and HTTP MCP clients.
This allows the LLMAgent to work with any transport without knowing the implementation details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

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
