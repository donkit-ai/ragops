"""Enterprise REPL implementation.

Handles enterprise mode REPL with local LLMAgent + DonkitModel.
MCP tools are accessed via API Gateway. WebSocket for backend events.
All messages are persisted via API Gateway.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from donkit.llm import Message, ModelCapability
from loguru import logger

from donkit_ragops import texts
from donkit_ragops.display import ScreenRenderer
from donkit_ragops.history_manager import compress_history_if_needed
from donkit_ragops.prints import RAGOPS_LOGO_ART, RAGOPS_LOGO_TEXT
from donkit_ragops.repl.base import BaseREPL, ReplContext
from donkit_ragops.repl.commands import CommandRegistry, create_default_registry
from donkit_ragops.repl_helpers import (
    MCPEventHandler,
    build_stream_render_helper,
    format_timestamp,
    render_markdown_to_rich,
)
from donkit_ragops.ui import UIAdapter, get_ui, set_ui_adapter
from donkit_ragops.ui.styles import StyleName

if TYPE_CHECKING:
    from donkit.ragops_api_gateway_client.client import RagopsAPIGatewayClient

    from donkit_ragops.enterprise.event_listener import BackendEvent, EventListener
    from donkit_ragops.enterprise.message_persister import MessagePersister


class EnterpriseREPL(BaseREPL):
    """REPL for enterprise mode with local LLMAgent.

    Uses DonkitModel for LLM, MCPHttpClient for MCP tools via API Gateway.
    File uploads happen without LLM, then message sent to agent.
    All messages persisted via API Gateway.
    """

    def __init__(
        self,
        context: ReplContext,
        api_client: RagopsAPIGatewayClient,
        message_persister: MessagePersister | None = None,
        event_listener: EventListener | None = None,
        enterprise_settings: Any = None,
    ) -> None:
        """Initialize EnterpriseREPL.

        Args:
            context: REPL context with agent, provider, tools, etc.
            api_client: API Gateway client for file operations
            message_persister: For persisting messages to API Gateway (optional, can be disabled)
            event_listener: WebSocket event listener for backend events
            enterprise_settings: Enterprise configuration
        """
        super().__init__(context)
        self.api_client = api_client
        self.message_persister = message_persister
        self.event_listener = event_listener
        self.enterprise_settings = enterprise_settings
        self.project_id: str | None = None
        self._command_registry: CommandRegistry = create_default_registry()
        # Register enterprise-specific commands
        self._command_registry.register_enterprise_commands()
        # Temporary storage for loaded messages (added after system prompt)
        self._loaded_messages: list[Message] = []

        # Set UI adapter
        set_ui_adapter(UIAdapter.RICH)

    async def initialize(self) -> None:
        """Initialize REPL resources."""
        ui = get_ui()

        # Print logo
        ui.print(RAGOPS_LOGO_TEXT)
        ui.print(RAGOPS_LOGO_ART)

        try:
            async with self.api_client:
                # Get user info
                user_info = await self.api_client.get_me()
                user_name = user_info.first_name or "User"
                user_id = user_info.id
                self.context.system_prompt += f"\nUser name: {user_name}\nUser ID: {user_id}"

                # Connect to most recent project, or create first project if none exist
                recent_projects = await self.api_client.get_recent_projects(limit=1)
                if recent_projects:
                    # Use most recent project
                    self.project_id = str(recent_projects[0].get("id"))
                    ui.print(f"Connected to project: {self.project_id}", StyleName.SUCCESS)

                    # Load project messages
                    project_messages = await self._load_project_messages(self.project_id)
                    for msg in project_messages:
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        # Skip system messages (will be added below)
                        if role == "system":
                            continue
                        # Skip backend events
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
                        # Collect user and assistant messages (will be added after system prompt)
                        if role in ("user", "assistant"):
                            self._loaded_messages.append(Message(role=role, content=content))

                    if self._loaded_messages:
                        ui.print(
                            f"Loaded {len(self._loaded_messages)} messages from history",
                            StyleName.DIM,
                        )
                else:
                    # No projects exist - create first one
                    project = await self.api_client.create_project()
                    self.project_id = str(project.id)
                    ui.print(f"Created new project: {self.project_id}", StyleName.SUCCESS)

                # Add project ID to system prompt
                self.context.system_prompt += f"\nProject ID: {self.project_id}"
        except Exception as e:
            ui.print_error(f"Error initializing: {e}")
            self.stop()
            raise

        # Update context, message persister and event listener with project ID
        self.context.project_id = self.project_id
        if self.message_persister:
            self.message_persister.project_id = self.project_id
        if self.event_listener:
            self.event_listener.project_id = self.project_id

        # Set up render helpers
        if self.context.renderer is None:
            self.context.renderer = ScreenRenderer()

        if self.context.render_helper is None and self.context.agent_settings is not None:
            self.context.render_helper = build_stream_render_helper(
                transcript=self.context.transcript,
                renderer=self.context.renderer,
                agent_settings=self.context.agent_settings,
                session_started_at=self.context.session_started_at,
                show_checklist=self.context.show_checklist,
            )

        if self.context.mcp_handler is None and self.context.agent_settings is not None:
            self.context.mcp_handler = MCPEventHandler(
                render_helper=self.context.render_helper,
                agent_settings=self.context.agent_settings,
                session_started_at=self.context.session_started_at,
                show_checklist=self.context.show_checklist,
            )
        # Initialize agent MCP tools
        if self.context.agent is not None:
            await self.context.agent.ainit_mcp_tools()

        # Add system prompt to history
        if self.context.system_prompt:
            self.context.history.append(Message(role="system", content=self.context.system_prompt))

        # Add loaded messages from project history (after system prompt)
        if self._loaded_messages:
            ui.newline()
            ui.print("─" * 80, StyleName.DIM)
            ui.print("Loaded conversation history:", StyleName.INFO)
            ui.print("─" * 80, StyleName.DIM)
            ui.newline()

            for msg in self._loaded_messages:
                # Add to history
                self.context.history.append(msg)

                # Add to visual transcript and print with visual separation
                if msg.role == "user":
                    if self.context.render_helper:
                        self.context.render_helper.append_user_line(msg.content)
                    # Print user message with better styling
                    ts = format_timestamp()
                    ui.print(f"{ts}{texts.USER_PREFIX}", StyleName.USER_PREFIX, end=" ")
                    ui.print(msg.content, StyleName.DIM)
                    ui.newline()
                elif msg.role == "assistant":
                    if self.context.render_helper:
                        rendered = render_markdown_to_rich(msg.content)
                        self.context.render_helper.append_agent_message(rendered)
                    # Print agent message with better styling
                    ts = format_timestamp()
                    ui.print(f"{ts}{texts.AGENT_PREFIX}", StyleName.SUCCESS, end=" ")
                    ui.print(msg.content, StyleName.DIM)
                    ui.newline()

            ui.newline()
            ui.print("─" * 80, StyleName.DIM)
            ui.newline()

            self._loaded_messages.clear()

        # Start event listener with callbacks
        if self.event_listener:
            self.event_listener.on_event = self._on_backend_event
            self.event_listener.on_progress = self._on_backend_progress
            await self.event_listener.start()

    async def _on_backend_event(self, event: BackendEvent) -> None:
        """Handle backend event from WebSocket.

        Sends event to LLM so it can notify the user with a contextual message.

        Args:
            event: Backend event
        """
        from donkit.llm import Message

        # Add event as user message (backend notification with embedded system instruction)
        event_msg = Message(role="user", content=event.message)
        self.context.history.append(event_msg)

        # Persist the event message (if persistence is enabled)
        # if self.message_persister:
        #     await self.message_persister.persist_message(role="user", content=event.message)

        # Let LLM respond to the event
        await self._handle_event_response(event)

    async def _handle_event_response(self, event: BackendEvent) -> None:
        """Generate LLM response for backend event.

        Args:
            event: Backend event to respond to
        """
        from donkit.llm import Message, ModelCapability

        ui = get_ui()

        # Show notification that we're processing an event
        ui.newline()
        ui.print(f"[Event] {event.type.value}", StyleName.INFO)

        try:
            if self.context.provider and self.context.provider.supports_capability(
                ModelCapability.STREAMING
            ):
                # Streaming response
                reply = ""
                if self.context.render_helper:
                    self.context.render_helper.print_agent_prefix()

                async for chunk in self.context.agent.arespond_stream(self.context.history):
                    if chunk.type == chunk.type.CONTENT:
                        ui.print(chunk.content)
                        reply += chunk.content

                if reply:
                    self.context.history.append(Message(role="assistant", content=reply))
                    if self.message_persister:
                        await self.message_persister.persist_assistant_message(content=reply)
                    ui.newline()
            else:
                # Non-streaming response
                reply = await self.context.agent.arespond(self.context.history)
                if reply:
                    self.context.history.append(Message(role="assistant", content=reply))
                    if self.message_persister:
                        await self.message_persister.persist_assistant_message(content=reply)
                    if self.context.render_helper:
                        self.context.render_helper.print_agent_prefix()
                    ui.print_markdown(reply)
                    ui.newline()

        except Exception as e:
            logger.error(f"Error generating event response: {e}", exc_info=True)
            ui.print_error(f"Failed to process event: {e}")

    def _on_backend_progress(
        self, progress: float, total: float | None, message: str | None
    ) -> None:
        """Handle progress event from WebSocket.

        Args:
            progress: Current progress value
            total: Total value (if known)
            message: Progress message
        """
        ui = get_ui()
        if total:
            pct = int((progress / total) * 100)
            msg = message or "Processing..."
            ui.print(f"[Progress] {pct}% - {msg}", StyleName.DIM)
        elif message:
            ui.print(f"[Progress] {message}", StyleName.DIM)

    async def run(self) -> None:
        """Run the REPL main loop."""
        await self.initialize()

        if not self._running:
            return

        self.print_welcome()
        self._print_welcome_message()

        while self._running:
            try:
                # Run text_input in a separate thread to avoid blocking event loop
                user_input = await self.context.ui.text_input()
            except KeyboardInterrupt:
                self.context.ui.print_warning("Input cancelled. Type :quit/exit/:q to exit")
                continue

            if not user_input:
                continue

            try:
                should_continue = await self.handle_input(user_input)
                if not should_continue:
                    break
            except (KeyboardInterrupt, asyncio.CancelledError):
                self.context.ui.print_warning("Operation interrupted.")
                if self.context.mcp_handler:
                    self.context.mcp_handler.clear_progress()
            except Exception as e:
                if self.context.render_helper:
                    self.context.render_helper.append_error(str(e))
                logger.opt(exception=True).error("Error in main loop: {}", repr(e))
                raise

        await self.cleanup()

    async def handle_input(self, user_input: str) -> bool:
        """Handle user input.

        Args:
            user_input: Raw user input

        Returns:
            False to exit, True to continue
        """
        # Check for commands first
        # is_command() now properly distinguishes between slash commands (/help, /exit)
        # and absolute file paths (/Users/..., /home/...) by checking registered commands
        if self._command_registry.is_command(user_input) or user_input in {"quit", "exit"}:
            return await self._handle_command(user_input)

        # Check for file path - handle file upload
        # Skip if input is too long to be a valid file path (max 255 chars per component)
        # This protects against OSError when pasting large JSON or other text
        if not user_input.startswith(":") and len(user_input) < 4096:
            try:
                file_path = Path(user_input.strip())
                if file_path.exists():
                    return await self._handle_file_upload(file_path)
            except OSError:
                # Input is not a valid file path (too long, invalid chars, etc.)
                pass

        # Regular message
        await self.handle_message(user_input)
        return True

    async def _handle_command(self, user_input: str) -> bool:
        """Handle a registered command."""
        from donkit_ragops.repl.commands import (
            NewProjectCommand,
            ProjectsCommand,
        )

        cmd = self._command_registry.get_command(user_input)
        if cmd is None:
            self.context.ui.print(f"Unknown command: {user_input}", StyleName.WARNING)
            return True

        # Handle enterprise-specific commands
        if isinstance(cmd, ProjectsCommand):
            await self._list_projects()
            return True
        elif isinstance(cmd, NewProjectCommand):
            await self._create_new_project()
            return True

        # Handle default commands
        result = await cmd.execute(self.context)

        # Print styled messages using UI abstraction
        for styled_msg in result.styled_messages:
            self.context.ui.print_styled(styled_msg)

        # Legacy: also handle plain messages
        for msg in result.messages:
            self.context.transcript.append(msg)

        if result.should_exit:
            if self.context.render_helper:
                self.context.render_helper.render_current_screen()
            if self.context.renderer:
                self.context.renderer.render_goodbye_screen()
            return False

        return True

    async def _handle_file_upload(self, file_path: Path) -> bool:
        """Handle file upload without LLM involvement.

        After upload, sends message to agent about uploaded files.

        Args:
            file_path: Path to file or directory

        Returns:
            True to continue REPL
        """
        from donkit_ragops.enterprise.analyzer import FileAnalyzer
        from donkit_ragops.enterprise.upload import FileUploader

        ui = get_ui()

        files_to_upload: list[str] = []
        if file_path.is_file():
            files_to_upload.append(str(file_path))
        elif file_path.is_dir():
            files_in_dir = list(file_path.rglob("*"))
            files_to_upload.extend(str(f) for f in files_in_dir if f.is_file())

        if not files_to_upload:
            return True

        file_names = [Path(f).name for f in files_to_upload]
        ui.newline()
        ui.print(f"Uploading: {', '.join(file_names)}", StyleName.INFO)

        file_analyzer = FileAnalyzer()
        file_uploader = FileUploader(self.api_client)

        s3_paths: list[str] = []
        file_analysis: dict = {}

        # Analyze files
        with ui.create_spinner("Analyzing files...") as spinner:
            try:
                file_analysis = await file_analyzer.analyze_files(
                    [Path(f) for f in files_to_upload]
                )
                spinner.update("Analysis complete")
            except Exception as e:
                ui.print_warning(f"Analysis failed: {e}")

        # Upload files
        with ui.create_progress(len(files_to_upload), "Uploading to cloud...") as progress:
            async with self.api_client:
                for i, file_path_str in enumerate(files_to_upload):
                    s3_path = await file_uploader.upload_single_file(file_path_str, self.project_id)
                    if s3_path:
                        s3_paths.append(s3_path)
                    progress.update(i + 1)
            file_uploader.reset()

        if not s3_paths:
            ui.print_error("Upload failed")
            return True

        ui.print_success(f"Uploaded {len(s3_paths)} file(s)")

        # Generate message about uploaded files
        if len(file_names) == 1:
            upload_message = f"I've uploaded the file: {file_names[0]}."
        else:
            upload_message = f"I've uploaded {len(file_names)} files: {', '.join(file_names)}. "

        # Add file analysis context to message
        if file_analysis:
            upload_message += f"\n\nFile analysis: {file_analysis}"

        # Add S3 paths context (one path per line for consistency with web UI)
        upload_message += f"\n\nFile locations:\n{chr(10).join(s3_paths)}"

        ui.newline()

        # Handle this as a silent message to agent (don't show in UI or persist)
        await self.handle_message(upload_message, silent=True)
        return True

    async def handle_message(self, message: str, silent: bool = False) -> None:
        """Handle a chat message.

        Args:
            message: User's chat message
            silent: If True, don't show in UI or persist to history (for internal messages)
        """
        if not silent:
            if self.context.render_helper:
                self.context.render_helper.append_user_line(message)

        # Add to history
        self.context.history.append(Message(role="user", content=message))

        # Persist user message (if persistence is enabled and not silent)
        if self.message_persister and not silent:
            await self.message_persister.persist_user_message(message)

        # Stream or non-stream response
        if self.context.provider and self.context.provider.supports_capability(
            ModelCapability.STREAMING
        ):
            await self._handle_streaming_response()
        else:
            await self._handle_non_streaming_response()

        # Compress history if needed
        if self.context.provider:
            self.context.history[:] = await compress_history_if_needed(
                self.context.history, self.context.provider
            )

    async def _handle_streaming_response(self) -> None:
        """Handle streaming response from agent."""
        reply = ""
        interrupted = False
        first_content = True
        response_index = None

        if self.context.render_helper:
            response_index = self.context.render_helper.start_agent_placeholder()

        spinner = self.context.ui.create_spinner(texts.THINKING_MESSAGE_PLAIN)
        spinner.start()

        try:
            display_content = ""
            temp_executing = ""

            async for event in self.context.agent.arespond_stream(self.context.history):
                # logger.debug(f"Event: {event}")
                # Stop spinner on first event
                if first_content:
                    spinner.stop()
                    first_content = False
                    if event.type == event.type.CONTENT:
                        if self.context.render_helper:
                            self.context.render_helper.print_agent_prefix()

                # Print content directly and accumulate reply
                if event.type == event.type.CONTENT:
                    self.context.ui.print(event.content)
                # Handle tool calls
                if event.type == event.type.TOOL_CALL_START and self.context.mcp_handler:
                    self.context.ui.print(
                        self.context.mcp_handler.tool_executing_message(
                            event.tool_name, event.tool_args
                        )
                    )
                    # Persist tool call (if persistence is enabled)
                    if self.message_persister:
                        tool_call = {
                            "id": f"call_{event.tool_name}",
                            "type": "function",
                            "function": {
                                "name": event.tool_name,
                                "arguments": str(event.tool_args),
                            },
                        }
                        await self.message_persister.persist_assistant_message(
                            tool_calls=[tool_call],
                        )
                elif event.type == event.type.TOOL_CALL_END and self.context.mcp_handler:
                    self.context.ui.print(
                        self.context.mcp_handler.tool_done_message(event.tool_name)
                    )
                elif event.type == event.type.TOOL_CALL_ERROR and self.context.mcp_handler:
                    self.context.ui.print(
                        self.context.mcp_handler.tool_error_message(
                            event.tool_name, event.error or ""
                        )
                    )

                if self.context.mcp_handler:
                    reply, display_content, temp_executing = (
                        self.context.mcp_handler.process_stream_event(
                            event,
                            self.context.history,
                            reply,
                            display_content,
                            temp_executing,
                        )
                    )

                if self.context.render_helper and response_index is not None:
                    self.context.render_helper.set_agent_line(
                        response_index, display_content, temp_executing
                    )

        except (KeyboardInterrupt, asyncio.CancelledError):
            if first_content:
                spinner.stop()
            interrupted = True
            if reply:
                self.context.history.append(Message(role="assistant", content=reply))
                rendered = render_markdown_to_rich(display_content)
                if self.context.render_helper and response_index is not None:
                    self.context.render_helper.set_agent_line(
                        response_index, f"{rendered}\nGeneration interrupted by user", ""
                    )
            elif response_index is not None:
                self.context.transcript[response_index] = (
                    f"{format_timestamp()}[yellow]Generation interrupted by user[/yellow]"
                )
            self.context.ui.print_warning("\nGeneration interrupted")

        except Exception as e:
            if first_content:
                spinner.stop()
            error_msg = f"{format_timestamp()}[bold red]Error:[/bold red] {e}"
            if response_index is not None:
                self.context.transcript[response_index] = error_msg
            else:
                self.context.transcript.append(error_msg)
            logger.error(f"Error during streaming: {e}", exc_info=True)
            self.context.ui.print_error(str(e))
            if self.context.mcp_handler:
                self.context.mcp_handler.clear_progress()

        if first_content:
            spinner.stop()

        # Add to history and persist if we got a response
        if reply and not interrupted:
            self.context.history.append(Message(role="assistant", content=reply))
            # Persist assistant response (if persistence is enabled)
            if self.message_persister:
                await self.message_persister.persist_assistant_message(content=reply)
            rendered = render_markdown_to_rich(display_content)
            if self.context.render_helper and response_index is not None:
                self.context.render_helper.set_agent_line(response_index, rendered, "")
            self.context.ui.newline()
        elif not interrupted and not reply:
            error_msg = f"{format_timestamp()}[bold red]Error:[/bold red] No response from agent"
            if response_index is not None:
                self.context.transcript[response_index] = error_msg
            else:
                self.context.transcript.append(error_msg)
            self.context.ui.print_error("No response from agent")

        if self.context.mcp_handler:
            self.context.mcp_handler.clear_progress()

    async def _handle_non_streaming_response(self) -> None:
        """Handle non-streaming response from agent."""
        response_index = None
        if self.context.render_helper:
            response_index = self.context.render_helper.start_agent_placeholder()

        spinner = self.context.ui.create_spinner(texts.THINKING_MESSAGE_PLAIN)
        spinner.start()

        try:
            reply = await self.context.agent.arespond(self.context.history)
            spinner.stop()

            if reply:
                self.context.history.append(Message(role="assistant", content=reply))
                # Persist assistant response (if persistence is enabled)
                if self.message_persister:
                    await self.message_persister.persist_assistant_message(content=reply)
                rendered = render_markdown_to_rich(reply)
                if self.context.render_helper and response_index is not None:
                    self.context.render_helper.set_agent_line(response_index, rendered, "")
                    self.context.render_helper.print_agent_prefix()
                self.context.ui.print_markdown(reply)
            else:
                if response_index is not None:
                    self.context.transcript[response_index] = (
                        f"{format_timestamp()}[bold red]Error:[/bold red] "
                        "No response from agent. Check logs for details."
                    )
                self.context.ui.print_error("No response from agent.")

        except (KeyboardInterrupt, asyncio.CancelledError):
            spinner.stop()
            self.context.ui.print_warning("Generation interrupted by user")
            if response_index is not None:
                self.context.transcript[response_index] = (
                    f"{format_timestamp()}[yellow]Generation interrupted[/yellow]"
                )

        except Exception as e:
            spinner.stop()
            error_msg = f"{format_timestamp()}[bold red]Error:[/bold red] {e}"
            if response_index is not None:
                self.context.transcript[response_index] = error_msg
            logger.error(f"Error during agent response: {e}", exc_info=True)
            self.context.ui.print_error(str(e))

        if self.context.mcp_handler:
            self.context.mcp_handler.clear_progress()

    async def cleanup(self) -> None:
        """Clean up REPL resources."""
        self._running = False

        # Stop event listener
        if self.event_listener:
            await self.event_listener.stop()

        ui = get_ui()
        ui.print("Disconnected", StyleName.DIM)

    def _print_welcome_message(self) -> None:
        """Print welcome message."""
        rendered = render_markdown_to_rich(texts.WELCOME_MESSAGE)
        if self.context.render_helper:
            self.context.render_helper.append_agent_message(rendered)
        self.context.ui.print(f"{rendered}", style=StyleName.HIGHLIGHTED)
        self.context.ui.newline()

    async def _list_projects(self) -> None:
        """List recent projects and allow interactive selection."""
        ui = get_ui()
        ui.newline()

        try:
            async with self.api_client:
                # Get recent projects
                projects = await self.api_client.get_recent_projects(limit=20)

                if not projects:
                    ui.print("No projects found. Use /new-project to create one.", StyleName.INFO)
                    ui.newline()
                    return

                # Filter out current project and prepare choices
                other_projects = []
                current_project_info = None

                for project in projects:
                    project_id = str(project.get("id", ""))
                    if project_id == self.project_id:
                        current_project_info = project
                    else:
                        other_projects.append(project)

                # Show current project info
                if current_project_info:
                    ui.print("Current Project:", StyleName.HIGHLIGHTED)
                    ui.print("-" * 80, StyleName.DIM)
                    project_id = str(current_project_info.get("id", ""))
                    rag_use_case = current_project_info.get("rag_use_case", "")
                    message_count = current_project_info.get("message_count", 0)
                    updated_at = current_project_info.get("updated_at", "")

                    ui.print(f"  ID: {project_id}", StyleName.SUCCESS)
                    if rag_use_case:
                        ui.print(f"  Use case: {rag_use_case}", StyleName.INFO)
                    ui.print(f"  Messages: {message_count}", StyleName.DIM)
                    if updated_at:
                        ui.print(f"  Updated: {updated_at[:19]}", StyleName.DIM)
                    ui.print("-" * 80, StyleName.DIM)
                    ui.newline()

                # Prepare choices for interactive selection
                if not other_projects:
                    ui.print(
                        "No other projects available. Use /new-project to create one.",
                        StyleName.INFO,
                    )
                    ui.newline()
                    return

                ui.print("Switch to another project:", StyleName.HIGHLIGHTED)
                ui.newline()

                # Create choice labels with project info
                choices = []
                project_map = {}  # choice label -> project_id

                for project in other_projects:
                    project_id = str(project.get("id", ""))
                    rag_use_case = project.get("rag_use_case", "")
                    message_count = project.get("message_count", 0)
                    updated_at = (
                        project.get("updated_at", "")[:19] if project.get("updated_at") else ""
                    )

                    # Create informative choice label
                    pid_short = project_id[:8]
                    if rag_use_case:
                        choice_label = (
                            f"{pid_short}... | {rag_use_case} | {message_count} msgs | {updated_at}"
                        )
                    else:
                        choice_label = f"{pid_short}... | {message_count} msgs | {updated_at}"

                    choices.append(choice_label)
                    project_map[choice_label] = project_id

                # Show interactive selection
                selected_choice = ui.select(
                    choices=choices,
                    title="Select project (↑/↓ to navigate, Enter to select, Esc to cancel)",
                )

                if selected_choice is None:
                    ui.print("Cancelled.", StyleName.DIM)
                    ui.newline()
                    return

                # Get selected project ID
                selected_project_id = project_map.get(selected_choice)
                if not selected_project_id:
                    ui.print_error("Invalid selection.")
                    ui.newline()
                    return

                # Switch to selected project
                await self._switch_to_project(selected_project_id)

        except Exception as e:
            logger.error(f"Failed to list projects: {e}", exc_info=True)
            ui.print_error(f"Failed to list projects: {e}")

        ui.newline()

    async def _create_new_project(self) -> None:
        """Create a new project and switch to it."""
        ui = get_ui()
        ui.newline()

        try:
            async with self.api_client:
                ui.print("Creating new project...", StyleName.INFO)

                # Create new project
                project = await self.api_client.create_project()
                new_project_id = str(project.id)

                ui.print(f"Created project: {new_project_id}", StyleName.SUCCESS)

                # Switch to the new project
                await self._switch_to_project(new_project_id)

        except Exception as e:
            logger.error(f"Failed to create new project: {e}", exc_info=True)
            ui.print_error(f"Failed to create new project: {e}")

        ui.newline()

    async def _switch_to_project(self, project_id: str) -> None:
        """Switch to a specific project with history loading.

        Args:
            project_id: Project ID to switch to
        """
        from donkit.llm import Message

        from donkit_ragops.agent.prompts import get_prompt

        ui = get_ui()

        try:
            async with self.api_client:
                # Verify project exists
                try:
                    await self.api_client.get_project(project_id)
                except Exception as e:
                    ui.print_error(f"Project not found: {project_id}")
                    logger.error(f"Failed to get project {project_id}: {e}")
                    return

                ui.print(f"Switching to project {project_id}...", StyleName.INFO)

                # Update project ID
                self.project_id = project_id
                self.context.project_id = project_id

                # Get user info for updated system prompt
                user_name = "User"
                user_id = ""
                try:
                    user_info = await self.api_client.get_me()
                    user_name = user_info.first_name or "User"
                    user_id = user_info.id
                except Exception as e:
                    logger.warning(f"Failed to get user info: {e}")

                # Generate new system prompt with updated project ID
                new_system_prompt = get_prompt("enterprise", interface="repl")
                new_system_prompt += f"\nUser name: {user_name}\nUser ID: {user_id}"
                new_system_prompt += f"\nProject ID: {project_id}"

                # Update system prompt in context
                self.context.system_prompt = new_system_prompt

                # Clear message history and add updated system prompt
                self.context.history.clear()
                self.context.history.append(Message(role="system", content=new_system_prompt))

                # Load project messages
                project_messages = await self._load_project_messages(project_id)

                # Add messages to history (skip system messages and backend events)
                loaded_count = 0
                for msg in project_messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")

                    # Skip system messages (already added above)
                    if role == "system":
                        continue

                    # Skip backend events (temporary notifications)
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

                    # Add user and assistant messages to history and transcript
                    if role in ("user", "assistant"):
                        self.context.history.append(Message(role=role, content=content))
                        loaded_count += 1

                        # Add to visual transcript
                        if role == "user":
                            if self.context.render_helper:
                                self.context.render_helper.append_user_line(content)
                        elif role == "assistant":
                            if self.context.render_helper:
                                rendered = render_markdown_to_rich(content)
                                self.context.render_helper.append_agent_message(rendered)

                # Update message persister if enabled
                if self.message_persister:
                    self.message_persister.project_id = project_id

                # Update event listener
                if self.event_listener:
                    self.event_listener.project_id = project_id
                    # Restart event listener with new project
                    await self.event_listener.stop()
                    await self.event_listener.start()

                # Clear transcript (visual display)
                self.context.transcript.clear()

                ui.print(
                    f"Switched to project {project_id} ({loaded_count} messages loaded)",
                    StyleName.SUCCESS,
                )

                # Print loaded history if any
                if loaded_count > 0:
                    ui.newline()
                    ui.print("─" * 80, StyleName.DIM)
                    ui.print("Conversation history:", StyleName.INFO)
                    ui.print("─" * 80, StyleName.DIM)
                    ui.newline()

                    # Print all loaded messages from transcript with visual separation
                    for msg in self.context.history[1:]:  # Skip system message
                        if msg.role == "user":
                            ts = format_timestamp()
                            ui.print(f"{ts}{texts.USER_PREFIX}", StyleName.USER_PREFIX, end=" ")
                            ui.print(msg.content, StyleName.DIM)
                            ui.newline()
                        elif msg.role == "assistant":
                            ts = format_timestamp()
                            ui.print(f"{ts}{texts.AGENT_PREFIX}", StyleName.SUCCESS, end=" ")
                            ui.print(msg.content, StyleName.DIM)
                            ui.newline()

                    ui.newline()
                    ui.print("─" * 80, StyleName.DIM)
                    ui.newline()

        except Exception as e:
            logger.error(f"Failed to switch to project {project_id}: {e}", exc_info=True)
            ui.print_error(f"Failed to switch to project: {e}")

    async def _load_project_messages(self, project_id: str) -> list[dict]:
        """Load message history for a project.

        Args:
            project_id: Project ID

        Returns:
            List of message dicts
        """
        try:
            async with self.api_client:
                messages = await self.api_client.get_project_messages(
                    project_id=project_id,
                    limit=1000,
                )
                logger.debug(f"Loaded {len(messages)} messages from project {project_id}")
                return messages
        except Exception as e:
            logger.warning(f"Failed to load project messages: {e}")
            return []
