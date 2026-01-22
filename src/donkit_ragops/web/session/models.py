"""Session models for web interface."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from donkit.llm import Message

if TYPE_CHECKING:
    from fastapi import WebSocket

    from donkit_ragops.agent.agent import LLMAgent
    from donkit_ragops.enterprise.event_listener import EventListener
    from donkit_ragops.enterprise.message_persister import MessagePersister
    from donkit_ragops.mcp.protocol import MCPClientProtocol
    from donkit_ragops.schemas.agent_schemas import AgentSettings


@dataclass
class WebSession:
    """Represents a web client session with its state.

    Contains all the context needed to run the LLM agent for a web client,
    similar to ReplContext but adapted for web use.
    """

    id: str
    provider_name: str
    model: str | None = None

    # Agent and provider (set after initialization)
    agent: LLMAgent | None = None
    agent_settings: AgentSettings | None = None

    # MCP clients
    mcp_clients: list[MCPClientProtocol] = field(default_factory=list)

    # Conversation history
    history: list[Message] = field(default_factory=list)

    # System prompt
    system_prompt: str | None = None

    # WebSocket connection (set when client connects)
    websocket: WebSocket | None = None

    # Currently running task (for cancellation)
    current_task: asyncio.Task | None = None

    # Timestamps
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    # Files directory for uploaded files
    files_dir: Path | None = None

    # Project ID (for enterprise mode integration)
    project_id: str | None = None

    # Track if MCP tools have been initialized
    mcp_initialized: bool = False

    # Pending interactive responses (request_id -> Future)
    pending_responses: dict[str, asyncio.Future] = field(default_factory=dict)

    # Enterprise mode fields
    enterprise_mode: bool = False
    api_client: Any = None  # RagopsAPIGatewayClient (avoid circular import)
    event_listener: EventListener | None = None
    message_persister: MessagePersister | None = None

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if session has expired."""
        return time.time() - self.last_activity > ttl_seconds

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.websocket is not None


@dataclass
class SessionInfo:
    """Session information for API responses."""

    id: str
    provider: str
    model: str | None
    created_at: float
    last_activity: float
    is_connected: bool
    message_count: int
    mcp_initialized: bool
    enterprise_mode: bool = False
    project_id: str | None = None

    @classmethod
    def from_session(cls, session: WebSession) -> SessionInfo:
        """Create SessionInfo from WebSession."""
        return cls(
            id=session.id,
            provider=session.provider_name,
            model=session.model,
            created_at=session.created_at,
            last_activity=session.last_activity,
            is_connected=session.is_connected,
            message_count=len(session.history),
            mcp_initialized=session.mcp_initialized,
            enterprise_mode=session.enterprise_mode,
            project_id=session.project_id,
        )
