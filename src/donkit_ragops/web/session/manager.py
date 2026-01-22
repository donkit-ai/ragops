"""Session manager for web interface."""

from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from donkit.llm import Message
from loguru import logger

from donkit_ragops.agent.agent import LLMAgent
from donkit_ragops.agent.prompts import get_prompt
from donkit_ragops.config import load_settings
from donkit_ragops.llm.provider_factory import get_provider
from donkit_ragops.mcp.client import MCPClient
from donkit_ragops.schemas.agent_schemas import AgentSettings
from donkit_ragops.web.config import WebConfig
from donkit_ragops.web.session.models import SessionInfo, WebSession
from donkit_ragops.web.tools import web_default_tools

if TYPE_CHECKING:
    from donkit_ragops.enterprise.message_persister import MessagePersister


class SessionManager:
    """Manages web sessions with TTL and cleanup."""

    def __init__(self, config: WebConfig) -> None:
        self.config = config
        self._sessions: dict[str, WebSession] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    @property
    def sessions(self) -> dict[str, WebSession]:
        """Get all sessions."""
        return self._sessions

    async def start(self) -> None:
        """Start the session manager and cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started")

    async def stop(self) -> None:
        """Stop the session manager and clean up all sessions."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clean up all sessions
        async with self._lock:
            for session_id in list(self._sessions.keys()):
                await self._cleanup_session(session_id)
            self._sessions.clear()

        logger.info("Session manager stopped")

    async def create_session(
        self,
        provider: str | None = None,
        model: str | None = None,
    ) -> WebSession:
        """Create a new session with LLM agent.

        Args:
            provider: LLM provider name (e.g., "openai", "anthropic")
            model: Model name (optional, uses default if not specified)

        Returns:
            Created WebSession
        """
        session_id = str(uuid.uuid4())

        # Load settings
        settings = load_settings()
        provider_name = provider or settings.llm_provider or "openai"
        model_name = model or settings.llm_model

        # Create provider
        try:
            llm_provider = get_provider(
                settings=settings,
                llm_provider=provider_name,
                model_name=model_name,
            )
        except Exception as e:
            logger.error(f"Failed to create LLM provider: {e}")
            raise

        # Create agent settings
        agent_settings = AgentSettings(
            llm_provider=llm_provider,
            model=model_name,
        )

        # Create MCP clients
        mcp_clients = self._create_mcp_clients()

        # Create agent with project_id provider for tool calls
        def get_project_id() -> str | None:
            session = self._sessions.get(session_id)
            return session.project_id if session else None

        agent = LLMAgent(
            provider=llm_provider,
            tools=web_default_tools(),
            mcp_clients=mcp_clients,
            project_id_provider=get_project_id,
        )

        # Create files directory
        files_dir = Path(self.config.upload_dir) / session_id
        files_dir.mkdir(parents=True, exist_ok=True)

        # Generate system prompt for web interface
        system_prompt = get_prompt(provider_name, interface="web")

        # Create session
        session = WebSession(
            id=session_id,
            provider_name=provider_name,
            model=model_name,
            agent=agent,
            agent_settings=agent_settings,
            mcp_clients=mcp_clients,
            system_prompt=system_prompt,
            files_dir=files_dir,
        )

        # Add system prompt to history
        if system_prompt:
            session.history.append(Message(role="system", content=system_prompt))

        async with self._lock:
            self._sessions[session_id] = session

        logger.info(f"Created session {session_id} with provider {provider_name}")
        return session

    async def create_enterprise_session(
        self,
        api_token: str | None = None,
        existing_project_id: str | None = None,
    ) -> WebSession:
        """Create a new enterprise mode session.

        Enterprise mode uses:
        - DonkitModel provider (LLM via API Gateway)
        - MCPHttpClient for MCP tools via API Gateway
        - EventListener for backend events
        - FileUploader for cloud file storage

        Args:
            api_token: API token (optional, uses keyring if not provided)
            existing_project_id: Existing project ID to connect to (optional,
                creates new if not provided)

        Returns:
            Created WebSession in enterprise mode

        Raises:
            ValueError: If no API token available
        """
        from pydantic_settings import BaseSettings

        from donkit_ragops.agent.local_tools.tools import (
            tool_grep,
            tool_list_directory,
            tool_read_file,
        )
        from donkit_ragops.enterprise.event_listener import EventListener
        from donkit_ragops.enterprise.message_persister import MessagePersister
        from donkit_ragops.mcp.http_client import MCPHttpClient
        from donkit_ragops.web.tools.interactive import (
            web_tool_interactive_user_choice,
            web_tool_interactive_user_confirm,
        )

        session_id = str(uuid.uuid4())

        # Get API token: from parameter, .env file, or keyring
        token = api_token
        token_source = "parameter" if token else None

        if not token:
            # Try to get from .env file (RAGOPS_DONKIT_API_KEY)
            try:
                from donkit_ragops.config import load_settings

                settings = load_settings()
                if settings.donkit_api_key:
                    token = settings.donkit_api_key
                    token_source = ".env"
            except Exception as e:
                logger.debug(f"Could not load token from .env: {e}")

        if not token:
            # Try to get from keyring (if user logged in via CLI)
            try:
                from donkit_ragops.enterprise.auth import get_token

                token = get_token()
                if token:
                    token_source = "keyring"
            except ImportError:
                pass

        if not token:
            raise ValueError(
                "Enterprise mode requires API token. "
                "Please provide token, set RAGOPS_DONKIT_API_KEY in .env, or login via CLI."
            )

        logger.debug(f"Using API token from {token_source}")

        api_url = self.config.enterprise_api_url
        mcp_url = self.config.enterprise_mcp_url

        # Create API client for file operations
        from donkit.ragops_api_gateway_client.client import RagopsAPIGatewayClient

        api_client = RagopsAPIGatewayClient(
            base_url=api_url,
            api_token=token,
        )

        # Create Donkit provider (LLM via API Gateway)
        class DonkitSettings(BaseSettings):
            donkit_api_key: str = token
            donkit_base_url: str = api_url

        try:
            llm_provider = get_provider(DonkitSettings(), llm_provider="donkit")
        except Exception as e:
            logger.error(f"Failed to create Donkit provider: {e}")
            raise

        # Create MCP HTTP client (MCP tools via API Gateway) with progress callback
        from donkit_ragops.web.tools.interactive import create_web_progress_callback

        mcp_client = MCPHttpClient(
            url=mcp_url,
            token=token,
            timeout=600.0,
            progress_callback=create_web_progress_callback(),
        )

        # Create agent settings
        agent_settings = AgentSettings(
            llm_provider=llm_provider,
            model=None,  # Donkit model is server-side
        )

        # Connect to existing project or get most recent project
        project_id: str | None = existing_project_id
        project_messages: list[dict] = []
        user_name: str = "User"
        user_id: str = ""
        try:
            async with api_client:
                # Get user info
                try:
                    user_info = await api_client.get_me()
                    user_name = user_info.first_name or "User"
                    user_id = user_info.id
                    logger.info(f"Retrieved user info: {user_name} (ID: {user_id})")
                except Exception as e:
                    logger.warning(f"Failed to get user info: {e}")

                if existing_project_id:
                    # Connect to specific existing project
                    logger.info(f"Connecting to existing project {existing_project_id}")
                    # Verify project exists
                    project = await api_client.get_project(existing_project_id)
                    project_id = str(project.id)
                    logger.info(f"Connected to enterprise project {project_id}")
                else:
                    # Get most recent project, or create new if none exist
                    logger.info("No project specified, getting most recent project...")
                    recent_projects = await api_client.get_recent_projects(limit=1)
                    if recent_projects:
                        project_id = str(recent_projects[0].get("id"))
                        logger.info(f"Connected to most recent project {project_id}")
                    else:
                        # No projects exist - create first one
                        logger.info("No projects found, creating first project...")
                        project = await api_client.create_project()
                        project_id = str(project.id)
                        logger.info(f"Created first enterprise project {project_id}")

                # Load message history for the project
                if project_id:
                    try:
                        project_messages = await api_client.get_project_messages(
                            project_id=project_id,
                            limit=1000,
                        )
                        logger.info(
                            f"Loaded {len(project_messages)} messages from project {project_id}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load project messages: {e}")
                        project_messages = []

                # Save token to .env and keyring if it was provided via API
                if token_source == "parameter":
                    # Save to .env for web UI detection
                    try:
                        from pathlib import Path

                        env_path = Path.cwd() / ".env"
                        config_to_save = {
                            "RAGOPS_DONKIT_API_KEY": token,
                            "RAGOPS_DONKIT_BASE_URL": "https://api.donkit.ai",
                        }

                        if env_path.exists():
                            existing_text = env_path.read_text(encoding="utf-8")
                            existing_lines = existing_text.splitlines()
                            remaining_updates = dict(config_to_save)
                            updated_lines: list[str] = []

                            for line in existing_lines:
                                stripped = line.strip()
                                if not stripped or stripped.startswith("#") or "=" not in line:
                                    updated_lines.append(line)
                                    continue
                                key = stripped.split("=", 1)[0].strip()
                                if key in remaining_updates:
                                    updated_lines.append(f"{key}={remaining_updates.pop(key)}")
                                else:
                                    updated_lines.append(line)

                            if remaining_updates:
                                if updated_lines and updated_lines[-1].strip():
                                    updated_lines.append("")
                                for key, value in remaining_updates.items():
                                    updated_lines.append(f"{key}={value}")

                            updated_content = "\n".join(updated_lines)
                            if not updated_content.endswith("\n"):
                                updated_content += "\n"
                            env_path.write_text(updated_content, encoding="utf-8")
                        else:
                            lines = [
                                "# RAGOps Agent CE Configuration",
                                "# Generated by web setup",
                                "",
                            ]
                            for key, value in config_to_save.items():
                                lines.append(f"{key}={value}")
                            lines.append("")
                            env_path.write_text("\n".join(lines), encoding="utf-8")

                        logger.info("Saved API token to .env")
                    except Exception as e:
                        logger.warning(f"Failed to save token to .env: {e}")

                    # Also save to keyring as backup
                    try:
                        from donkit_ragops.enterprise.auth import save_token

                        save_token(token)
                        logger.debug("Saved API token to keyring")
                    except Exception as e:
                        logger.debug(f"Failed to save token to keyring: {e}")

        except Exception as e:
            logger.error(f"Failed to create/connect to enterprise project: {e}")
            raise

        # Create enterprise tools (minimal local tools + web interactive tools)
        enterprise_tools = [
            tool_read_file(),
            tool_list_directory(),
            tool_grep(),
            web_tool_interactive_user_confirm(),
            web_tool_interactive_user_choice(),
        ]

        # Create agent with project_id provider
        def get_project_id() -> str | None:
            session = self._sessions.get(session_id)
            return session.project_id if session else None

        agent = LLMAgent(
            provider=llm_provider,
            tools=enterprise_tools,
            mcp_clients=[mcp_client],
            project_id_provider=get_project_id,
        )

        # Create message persister (optional)
        message_persister: MessagePersister | None = None
        if self.config.enterprise_persist_messages:
            message_persister = MessagePersister(
                api_client=api_client,
                project_id=project_id or "",
            )

        # Create event listener for backend events
        event_listener = EventListener(
            base_url=api_url,
            token=token,
            project_id=project_id or "",
        )

        # Generate enterprise system prompt for web interface
        system_prompt = get_prompt("enterprise", interface="web")
        # Add user and project context to prompt
        system_prompt += f"\nUser name: {user_name}\nUser ID: {user_id}"
        if project_id:
            system_prompt += f"\nProject ID: {project_id}"

        # Create files directory (for any local temp files)
        files_dir = Path(self.config.upload_dir) / session_id
        files_dir.mkdir(parents=True, exist_ok=True)

        # Create session
        session = WebSession(
            id=session_id,
            provider_name="donkit",
            model=None,
            agent=agent,
            agent_settings=agent_settings,
            mcp_clients=[mcp_client],
            system_prompt=system_prompt,
            files_dir=files_dir,
            project_id=project_id,
            enterprise_mode=True,
            api_client=api_client,
            event_listener=event_listener,
            message_persister=message_persister,
        )

        # Add system prompt to history
        if system_prompt:
            session.history.append(Message(role="system", content=system_prompt))

        # Load message history for existing project
        if project_messages:
            for msg in project_messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                # Skip system messages (already added above)
                if role == "system":
                    continue
                # Skip backend events (they were mistakenly saved as user messages)
                # These are temporary notifications that should not be in persistent history
                if (
                    role == "user"
                    and content
                    and (
                        content.startswith("[SYSTEM INSTRUCTION:")
                        or content.startswith("[PIPELINE:")
                        or content.startswith("[BACKEND_EVENT:")
                        or content.startswith("[EXPERIMENT_ITERATION_COMPLETED]")
                    )
                ):
                    continue
                # Add user and assistant messages
                if role in ("user", "assistant"):
                    session.history.append(Message(role=role, content=content))
            msg_count = len([m for m in project_messages if m.get("role") in ("user", "assistant")])
            logger.info(f"Added {msg_count} messages to session history")

        async with self._lock:
            self._sessions[session_id] = session

        logger.info(f"Created enterprise session {session_id} with project {project_id}")
        return session

    async def get_session(self, session_id: str) -> WebSession | None:
        """Get a session by ID."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
            return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and clean up resources."""
        async with self._lock:
            if session_id not in self._sessions:
                return False
            await self._cleanup_session(session_id)
            del self._sessions[session_id]
        logger.info(f"Deleted session {session_id}")
        return True

    async def list_sessions(self) -> list[SessionInfo]:
        """List all active sessions."""
        async with self._lock:
            return [SessionInfo.from_session(s) for s in self._sessions.values()]

    async def create_new_project(self, session_id: str) -> str:
        """Create a new project for an existing enterprise session.

        Args:
            session_id: Session ID

        Returns:
            New project ID

        Raises:
            ValueError: If session not found or not in enterprise mode
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        if not session.enterprise_mode or not session.api_client:
            raise ValueError("Project creation is only available in enterprise mode")

        try:
            async with session.api_client:
                # Create new project via API
                project = await session.api_client.create_project()
                new_project_id = str(project.id)
                logger.info(f"Created new project {new_project_id} for session {session_id}")

                # Update session with new project ID
                session.project_id = new_project_id

                # Get user info for updated system prompt
                user_name = "User"
                user_id = ""
                try:
                    user_info = await session.api_client.get_me()
                    user_name = user_info.first_name or "User"
                    user_id = user_info.id
                except Exception as e:
                    logger.warning(f"Failed to get user info for new project: {e}")

                # Generate new system prompt with updated project ID
                new_system_prompt = get_prompt("enterprise", interface="web")
                new_system_prompt += f"\nUser name: {user_name}\nUser ID: {user_id}"
                new_system_prompt += f"\nProject ID: {new_project_id}"

                # Update system prompt in session
                session.system_prompt = new_system_prompt

                # Clear message history and add updated system prompt
                session.history.clear()
                session.history.append(Message(role="system", content=new_system_prompt))

                # Update message persister if enabled
                if session.message_persister:
                    session.message_persister.project_id = new_project_id

                # Update event listener
                if session.event_listener:
                    session.event_listener.project_id = new_project_id
                    # Restart event listener with new project
                    await session.event_listener.stop()
                    await session.event_listener.start()

                return new_project_id

        except Exception as e:
            logger.error(f"Failed to create new project: {e}")
            raise

    async def initialize_mcp(self, session_id: str) -> bool:
        """Initialize MCP tools for a session.

        Returns True if initialization was successful or already done.
        """
        session = await self.get_session(session_id)
        if not session or not session.agent:
            return False

        if session.mcp_initialized:
            return True

        try:
            await session.agent.ainit_mcp_tools()
            session.mcp_initialized = True
            logger.info(f"MCP tools initialized for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MCP tools for session {session_id}: {e}")
            return False

    def _create_mcp_clients(self) -> list[MCPClient]:
        """Create MCP clients for the session with progress callback."""
        from donkit_ragops.web.tools.interactive import create_web_progress_callback

        clients = []

        # Create the unified donkit-ragops-mcp client with progress callback
        try:
            # Use the same approach as CLI
            import sys

            client = MCPClient(
                command=sys.executable,
                args=["-m", "donkit_ragops.mcp.servers.donkit_ragops_mcp"],
                timeout=120.0,
                progress_callback=create_web_progress_callback(),
            )
            clients.append(client)
        except Exception as e:
            logger.warning(f"Failed to create MCP client: {e}")

        return clients

    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up a single session's resources."""
        session = self._sessions.get(session_id)
        if not session:
            return

        # Cancel any running task
        if session.current_task and not session.current_task.done():
            session.current_task.cancel()
            try:
                await session.current_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket if connected
        if session.websocket:
            try:
                await session.websocket.close()
            except Exception:
                pass

        # Clean up enterprise resources
        if session.enterprise_mode:
            # Stop event listener
            if session.event_listener:
                try:
                    await session.event_listener.stop()
                except Exception as e:
                    logger.warning(f"Failed to stop event listener: {e}")

            # Note: api_client is typically used in context manager,
            # no explicit cleanup needed

        # Remove files directory
        if session.files_dir and session.files_dir.exists():
            try:
                shutil.rmtree(session.files_dir)
            except Exception as e:
                logger.warning(f"Failed to remove files directory: {e}")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        async with self._lock:
            expired = [
                sid
                for sid, session in self._sessions.items()
                if session.is_expired(self.config.session_ttl_seconds)
            ]

            for session_id in expired:
                await self._cleanup_session(session_id)
                del self._sessions[session_id]
                logger.info(f"Cleaned up expired session {session_id}")
