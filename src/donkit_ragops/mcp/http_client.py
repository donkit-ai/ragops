"""HTTP MCP client for connecting to API Gateway via Streamable HTTP.

Uses FastMCP Client with StreamableHttpTransport to connect to cloud MCP server.
Implements MCPClientProtocol for compatibility with the agent's MCP abstraction.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from donkit_ragops.mcp.protocol import MCPClientProtocol, ProgressCallback
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from loguru import logger


class MCPHttpClient(MCPClientProtocol):
    """MCP client for connecting to API Gateway via HTTP.

    Uses FastMCP Client with StreamableHttpTransport.
    Implements MCPClientProtocol for compatibility with the agent's MCP abstraction.
    """

    def __init__(
        self,
        url: str,
        token: str,
        timeout: float = 60.0,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Initialize MCP HTTP client.

        Args:
            url: MCP endpoint URL (e.g., https://api.donkit.ai/mcp)
            token: API token for authentication
            timeout: Timeout for operations in seconds
            progress_callback: Optional callback for progress updates from MCP tools
        """
        self._url = url
        self._token = token
        self._timeout = timeout
        self._progress_callback = progress_callback
        self.client = Client(self._create_transport())

    @property
    def identifier(self) -> str:
        """Return the URL as identifier for logging."""
        return self._url

    @property
    def url(self) -> str:
        """Return the endpoint URL."""
        return self._url

    @property
    def token(self) -> str:
        """Return the API token."""
        return self._token

    @property
    def timeout(self) -> float:
        """Return the timeout in seconds."""
        return self._timeout

    @property
    def progress_callback(self) -> ProgressCallback | None:
        """Return the progress callback if set."""
        return self._progress_callback

    def _create_transport(self) -> StreamableHttpTransport:
        """Create transport with authentication headers."""
        return StreamableHttpTransport(
            url=self._url,
            auth=self._token,
        )

    async def __progress_handler(
        self,
        progress: float,
        total: float | None,
        message: str | None,
    ) -> None:
        """Handle progress updates from MCP server."""
        if self._progress_callback:
            self._progress_callback(progress, total, message)
        else:
            if total is not None:
                percentage = (progress / total) * 100
                logger.debug(f"Progress: {percentage:.1f}% - {message or ''}")
            else:
                logger.debug(f"Progress: {progress} - {message or ''}")

    async def alist_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server."""
        try:
            async with self.client as client:
                logger.debug(f"[MCP HTTP] Listing tools from {self._url}")
                tools_resp = await client.list_tools()
                logger.debug(f"[MCP HTTP] Got {len(tools_resp)} tools from server")
                tools = []
                for t in tools_resp:
                    # FastMCP returns Tool objects with name, description, and inputSchema
                    # Default schema matches stdio MCPClient behavior
                    schema: dict[str, Any] = {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True,  # Match stdio client default
                    }
                    raw_schema = getattr(t, "inputSchema", None) or getattr(t, "input_schema", None)
                    if raw_schema and isinstance(raw_schema, dict):
                        try:
                            # Handle FastMCP schema wrapping - match stdio client behavior
                            if "properties" in raw_schema:
                                if "args" in raw_schema["properties"] and "$defs" in raw_schema:
                                    args_ref = raw_schema["properties"]["args"].get("$ref")
                                    if args_ref and args_ref.startswith("#/$defs/"):
                                        def_name = args_ref.split("/")[-1]
                                        if def_name in raw_schema["$defs"]:
                                            # Use the unwrapped model schema
                                            schema = raw_schema["$defs"][def_name].copy()
                                            # Preserve $defs for nested refs (like stdio client)
                                            if "$defs" in raw_schema:
                                                schema["$defs"] = raw_schema["$defs"]
                                else:
                                    # No args wrapper, use as is
                                    schema = raw_schema.copy()
                        except Exception as e:
                            logger.warning(f"Failed to parse schema for tool {t.name}: {e}")
                    tool_dict = {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": schema,
                    }
                    tools.append(tool_dict)
                # Log total size of tools for debugging
                try:
                    tools_json = json.dumps(tools, ensure_ascii=True)
                    logger.debug(
                        f"[MCP HTTP] Tools loaded: count={len(tools)}, "
                        f"total_size_bytes={len(tools_json)}"
                    )
                    # Log first tool's full schema for debugging
                    if tools:
                        logger.debug(
                            f"[MCP HTTP] Sample tool schema: {json.dumps(tools[0], indent=2)}"
                        )
                except Exception as e:
                    logger.warning(f"[MCP HTTP] Failed to serialize tools for size check: {e}")
                return tools
        except asyncio.CancelledError:
            logger.warning("Tool listing was cancelled")
            raise
        except Exception as e:
            logger.error(f"Failed to list tools from MCP server: {e}", exc_info=True)
            raise

    def list_tools(self) -> list[dict[str, Any]]:
        """Synchronously list available tools."""
        try:
            return asyncio.run(asyncio.wait_for(self.alist_tools(), timeout=self._timeout))
        except KeyboardInterrupt:
            logger.warning("Tool listing interrupted by user")
            return []
        except asyncio.TimeoutError:
            logger.warning("Tool listing timed out")
            return []
        except Exception as e:
            logger.error(f"Failed to list tools: {e}", exc_info=True)
            return []

    async def acall_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the MCP server."""
        logger.debug(f"Calling HTTP MCP tool {name} with arguments {arguments}")
        try:
            async with self.client as client:
                # HTTP transport doesn't need args wrapping - pass arguments directly
                logger.debug(f"Arguments for {name}: {arguments}")
                result = await client.call_tool(name, arguments if arguments else None)
                # Extract text content from result
                if hasattr(result, "content") and result.content:
                    texts: list[str] = []
                    for content_item in result.content:
                        if hasattr(content_item, "text"):
                            texts.append(content_item.text)
                    if texts:
                        return "\n".join(texts)
                # Fall back to structured data
                if hasattr(result, "data") and result.data is not None:
                    if isinstance(result.data, str):
                        return result.data
                    return json.dumps(result.data)
                return str(result)
        except asyncio.CancelledError:
            logger.warning(f"Tool {name} execution was cancelled")
            raise
        except KeyboardInterrupt:
            logger.warning(f"Tool {name} execution interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Failed to call tool {name}: {e}", exc_info=True)
            raise

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Synchronously call a tool."""
        try:
            result = asyncio.run(
                asyncio.wait_for(self.acall_tool(name, arguments), timeout=self._timeout)
            )
            if not isinstance(result, str):
                return json.dumps(result)
            return result
        except KeyboardInterrupt:
            logger.warning(f"Tool {name} execution interrupted by user")
            raise
        except asyncio.TimeoutError:
            logger.warning(f"Tool {name} execution timed out")
            return f"Error: Tool {name} execution timed out"
        except Exception as e:
            logger.error(f"Failed to call tool {name}: {e}", exc_info=True)
            return f"Error: {e}"
