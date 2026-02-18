from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, find_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from loguru import logger

from donkit_ragops.mcp.protocol import MCPClientProtocol, ProgressCallback


def _load_env_for_mcp() -> dict[str, str | None]:
    """Load environment variables for MCP server.

    Combines:
    1. Current os.environ (so MCP server inherits parent env)
    2. Variables from .env files (with multiple search strategies for Windows compatibility)

    Returns dict with environment variables for the MCP server process.
    """
    # Start with current environment
    env = dict(os.environ)

    # Try to load from .env files in multiple locations
    env_loaded = False
    for fname in (".env.local", ".env"):
        # 1. Current working directory
        cwd_path = Path.cwd() / fname
        if cwd_path.exists():
            env.update(dotenv_values(cwd_path))
            env_loaded = True
            logger.debug(f"Loaded MCP env from {cwd_path}")
        if env_loaded:
            break
        # 2. Parent directories (walk up 3 levels)
        parent = Path.cwd()
        for _ in range(4):
            parent = parent.parent
            parent_env = parent / fname
            if parent_env.exists():
                env.update(dotenv_values(parent_env))
                env_loaded = True
                logger.debug(f"Loaded MCP env from {parent_env}")
                break
        # 3. Fallback to find_dotenv
        if not env_loaded:
            found = find_dotenv(filename=fname, usecwd=True)
            if found:
                env.update(dotenv_values(found))
                env_loaded = True
                logger.debug(f"Loaded MCP env from {found}")

    if not env_loaded:
        logger.debug("No .env file found for MCP server, using current environment only")
    return env


class MCPClient(MCPClientProtocol):
    """Client for connecting to an MCP server using FastMCP over stdio.

    Supports two usage modes:
    - Persistent: call connect() once, then reuse the subprocess across
      alist_tools()/acall_tool() calls. Call disconnect() when done.
    - Temporary (fallback): each call spawns its own subprocess.
      Used by sync callers and when connect() was not called.
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        timeout: float = 999.0,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Initialize MCP client.

        Args:
            command: Command to run the MCP server (e.g., "python" or "uv")
            args: Command-line arguments including the script path
            timeout: Timeout for operations in seconds
            progress_callback: Optional callback for progress updates from MCP tools
        """
        self._command = command
        self._args = args or []
        self._timeout = timeout
        self._progress_callback = progress_callback
        # Load environment variables for the server
        self._env = _load_env_for_mcp()
        # Persistent connection state (populated by connect())
        self._transport: StdioTransport | None = None
        self._client: Client | None = None

    @property
    def identifier(self) -> str:
        """Return the command as identifier for logging."""
        return self._command

    @property
    def command(self) -> str:
        """Return the command (for backwards compatibility)."""
        return self._command

    @property
    def args(self) -> list[str]:
        """Return the command arguments."""
        return self._args

    @property
    def timeout(self) -> float:
        """Return the timeout in seconds."""
        return self._timeout

    @property
    def progress_callback(self) -> ProgressCallback | None:
        """Return the progress callback if set."""
        return self._progress_callback

    # -- Persistent connection lifecycle -----------------------------------

    async def connect(self) -> None:
        """Open a persistent stdio connection for reuse across calls."""
        if self._client is not None:
            return  # already connected
        transport = StdioTransport(
            command=self.command,
            args=self.args,
            env=self._env,
        )
        client = Client(transport, progress_handler=self.__progress_handler)
        await client.__aenter__()
        self._transport = transport
        self._client = client
        logger.debug(f"Persistent MCP connection opened: {self.identifier}")

    async def disconnect(self) -> None:
        """Close the persistent connection and terminate the subprocess."""
        client = self._client
        transport = self._transport
        self._client = None
        self._transport = None
        if client is not None:
            try:
                await client.__aexit__(None, None, None)
            except Exception as e:
                logger.debug(f"Error closing MCP client: {e}")
        if transport is not None:
            await self._terminate_transport(transport)
        logger.debug(f"Persistent MCP connection closed: {self.identifier}")

    # -- Progress handling -------------------------------------------------

    async def __progress_handler(
        self,
        progress: float,
        total: float | None,
        message: str | None,
    ) -> None:
        """Handle progress updates from read_engine MCP server."""
        if self.progress_callback:
            self.progress_callback(progress, total, message)
        else:
            # Fallback: overwrite the same line using \r
            import sys

            if total is not None:
                percentage = (progress / total) * 100
                line = f"Progress: {percentage:.1f}% - {message or ''}"
            else:
                line = f"Progress: {progress} - {message or ''}"
            # Clear line and write progress in-place
            sys.stdout.write(f"\r\033[K{line}")
            sys.stdout.flush()
            # Print newline when done (100%)
            if total is not None and progress >= total:
                sys.stdout.write("\n")
                sys.stdout.flush()

    # -- Shared helpers ----------------------------------------------------

    @staticmethod
    async def _list_tools_from(client: Client) -> list[dict[str, Any]]:
        """List tools using the given client and parse their schemas."""
        tools_resp = await client.list_tools()
        tools: list[dict[str, Any]] = []
        for t in tools_resp:
            raw_schema = getattr(t, "inputSchema", None) or getattr(t, "input_schema", None)
            schema = MCPClient._parse_tool_schema(raw_schema, t.name)
            tools.append(
                {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": schema,
                }
            )
        return tools

    @staticmethod
    async def _call_tool_with(client: Client, name: str, arguments: dict[str, Any]) -> str:
        """Call a tool using the given client and extract the result string."""
        # FastMCP wraps Pydantic models in {"args": <model>}, so wrap arguments
        wrapped_args = {"args": arguments} if arguments else None
        logger.debug(f"Wrapped arguments for {name}: {wrapped_args}")
        result = await client.call_tool(name, wrapped_args)
        # Try to extract text content first
        if hasattr(result, "content") and result.content:
            texts: list[str] = []
            for content_item in result.content:
                if hasattr(content_item, "text"):
                    texts.append(content_item.text)
            if texts:
                return "\n".join(texts)
        # Fall back to structured data if available
        if hasattr(result, "data") and result.data is not None:
            if isinstance(result.data, str):
                return result.data
            return json.dumps(result.data)
        # Last resort: stringify the whole result
        return str(result)

    @staticmethod
    async def _terminate_transport(transport: StdioTransport) -> None:
        """Terminate the subprocess owned by a StdioTransport."""
        if hasattr(transport, "_process") and transport._process:
            try:
                transport._process.terminate()
                try:
                    await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    pass
                if transport._process.poll() is None:
                    transport._process.kill()
            except Exception as e:
                logger.debug(f"Error during transport cleanup: {e}")

    # I/O errors that signal a dead transport/subprocess.
    # ConnectionError covers BrokenPipeError, ConnectionResetError, etc.
    # Intentionally excludes TimeoutError (subprocess may still be running)
    # and other OSError subclasses (FileNotFoundError, PermissionError).
    _TRANSPORT_ERRORS = (ConnectionError, EOFError)

    # -- Public async API --------------------------------------------------

    async def alist_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server."""
        # Fast path: reuse persistent connection
        if self._client is not None:
            try:
                return await self._list_tools_from(self._client)
            except self._TRANSPORT_ERRORS as e:
                logger.warning(f"Persistent MCP connection failed, reconnecting: {e}")
                await self.disconnect()

        # Fallback: temporary connection per call
        transport = StdioTransport(
            command=self.command,
            args=self.args,
            env=self._env,
        )
        client = Client(transport)
        try:
            async with client:
                return await self._list_tools_from(client)
        except asyncio.CancelledError:
            logger.warning("Tool listing was cancelled")
            raise
        finally:
            await self._terminate_transport(transport)

    def list_tools(self) -> list[dict[str, Any]]:
        """Synchronously list available tools."""
        try:
            return asyncio.run(asyncio.wait_for(self.alist_tools(), timeout=self.timeout))
        except KeyboardInterrupt:
            logger.warning("Tool listing interrupted by user")
            # Don't re-raise - return empty list to allow agent to continue
            return []
        finally:
            # Ensure any remaining event loop cleanup happens
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.stop()
            except RuntimeError:
                # No event loop available, which is fine
                pass

    async def acall_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the MCP server."""
        logger.debug(f"Calling tool {name} with arguments {arguments}")

        # Fast path: reuse persistent connection
        if self._client is not None:
            try:
                return await self._call_tool_with(self._client, name, arguments)
            except self._TRANSPORT_ERRORS as e:
                logger.warning(f"Persistent MCP connection failed, reconnecting: {e}")
                await self.disconnect()

        # Fallback: temporary connection per call
        transport = StdioTransport(command=self.command, args=self.args, env=self._env)
        client = Client(transport, progress_handler=self.__progress_handler)
        try:
            async with client:
                return await self._call_tool_with(client, name, arguments)
        except asyncio.CancelledError:
            logger.warning(f"Tool {name} execution was cancelled")
            raise
        except KeyboardInterrupt:
            logger.warning(f"Tool {name} execution interrupted by user")
            raise
        finally:
            await self._terminate_transport(transport)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Synchronously call a tool."""
        try:
            result = asyncio.run(
                asyncio.wait_for(self.acall_tool(name, arguments), timeout=self.timeout)
            )
            if not isinstance(result, str):
                return json.dumps(result)
            return result
        except KeyboardInterrupt:
            logger.warning(f"Tool {name} execution interrupted by user")
            raise
        finally:
            # Ensure any remaining event loop cleanup happens
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.stop()
            except RuntimeError:
                # No event loop available, which is fine
                pass
