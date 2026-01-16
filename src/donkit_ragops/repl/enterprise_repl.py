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

                # Create project
                project = await self.api_client.create_project()
                self.project_id = str(project.id)
                self.context.system_prompt += f"\nProject ID: {self.project_id}"
                ui.print(f"Project: {self.project_id}", StyleName.SUCCESS)
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
        if self.message_persister:
            await self.message_persister.persist_message(role="user", content=event.message)

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
        # Check for commands
        if self._command_registry.is_command(user_input) or user_input in {"quit", "exit"}:
            return await self._handle_command(user_input)

        # Check for file path - handle file upload
        # Skip if input is too long to be a valid file path (max 255 chars per component)
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
        cmd = self._command_registry.get_command(user_input)
        if cmd is None:
            self.context.ui.print(f"Unknown command: {user_input}", StyleName.WARNING)
            return True

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

        # Add S3 paths context
        upload_message += f"\n\nFile locations: {s3_paths}"

        ui.newline()
        # ui.print(f"You: {upload_message[:100]}...", StyleName.INFO)
        ui.newline()

        # Handle this as a regular message to agent
        await self.handle_message(upload_message)
        return True

    async def handle_message(self, message: str) -> None:
        """Handle a chat message.

        Args:
            message: User's chat message
        """
        if self.context.render_helper:
            self.context.render_helper.append_user_line(message)

        # Add to history
        self.context.history.append(Message(role="user", content=message))

        # Persist user message (if persistence is enabled)
        if self.message_persister:
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
