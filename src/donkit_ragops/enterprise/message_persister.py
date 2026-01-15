"""Message persistence for enterprise mode.

Persists all messages (user, assistant, tool calls, tool results) to API Gateway.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from donkit.ragops_api_gateway_client.client import RagopsAPIGatewayClient


class MessagePersister:
    """Persists messages to API Gateway history.

    All messages including tool calls and results are persisted immediately.
    """

    def __init__(self, api_client: RagopsAPIGatewayClient, project_id: str) -> None:
        """Initialize message persister.

        Args:
            api_client: API Gateway client for persistence
            project_id: Project ID for message association
        """
        self.api_client = api_client
        self.project_id = project_id

    async def persist_user_message(
        self,
        content: str,
        attached_files: list[str] | None = None,
        file_analysis: dict | None = None,
    ) -> None:
        """Persist a user message.

        Args:
            content: Message content
            attached_files: Optional list of attached file paths
            file_analysis: Optional file analysis data
        """
        from donkit.ragops_api_gateway_client.client import (
            AddMessageRequest,
            MessagePayload,
        )

        message = MessagePayload(
            role="user",
            content=content,
            attached_files=attached_files,
            file_analysis=file_analysis,
        )
        request = AddMessageRequest(
            project_id=self.project_id,
            message=message,
        )
        await self._persist(request)

    async def persist_assistant_message(
        self,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
    ) -> None:
        """Persist an assistant message.

        Args:
            content: Message content (may be None if only tool calls)
            tool_calls: Optional list of tool calls
        """
        from donkit.ragops_api_gateway_client.client import (
            AddMessageRequest,
            MessagePayload,
        )

        message = MessagePayload(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
        )
        request = AddMessageRequest(
            project_id=self.project_id,
            message=message,
        )
        await self._persist(request)

    async def persist_tool_result(
        self,
        tool_name: str,
        tool_call_id: str,
        content: str,
    ) -> None:
        """Persist a tool result message.

        Args:
            tool_name: Name of the tool
            tool_call_id: ID of the tool call this is responding to
            content: Tool result content
        """
        from donkit.ragops_api_gateway_client.client import (
            AddMessageRequest,
            MessagePayload,
        )

        message = MessagePayload(
            role="tool",
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )
        request = AddMessageRequest(
            project_id=self.project_id,
            message=message,
        )
        await self._persist(request)

    async def persist_message(
        self,
        role: str,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        attached_files: list[str] | None = None,
        file_analysis: dict[str, Any] | None = None,
    ) -> None:
        """Persist any type of message.

        Generic method for persisting any message type.

        Args:
            role: Message role (user, assistant, tool)
            content: Message content
            tool_calls: Tool calls (for assistant messages)
            tool_name: Tool name (for tool results)
            tool_call_id: Tool call ID (for tool results)
            attached_files: Attached files (for user messages)
            file_analysis: File analysis data (for user messages)
        """
        from donkit.ragops_api_gateway_client.client import (
            AddMessageRequest,
            MessagePayload,
        )

        message = MessagePayload(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            attached_files=attached_files,
            file_analysis=file_analysis,
        )
        request = AddMessageRequest(
            project_id=self.project_id,
            message=message,
        )
        await self._persist(request)

    async def _persist(self, request: Any) -> None:
        """Persist a message request to API Gateway.

        Args:
            request: AddMessageRequest to persist
        """
        try:
            async with self.api_client:
                await self.api_client.add_message(request)
            logger.debug("Persisted {} message to history", request.message.role)
        except Exception as e:
            # Log error but don't fail - message persistence is best-effort
            # Use logger.opt(exception=True) to avoid format issues with braces in error message
            logger.opt(exception=True).error("Failed to persist message: {}", str(e))
