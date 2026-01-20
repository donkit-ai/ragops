from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from enum import StrEnum, auto

from donkit.llm import (
    GenerateRequest,
    LLMModelAbstract,
    Message,
    ModelCapability,
    Tool,
)
from loguru import logger

from donkit_ragops.db import close, kv_get, kv_set, open_db
from donkit_ragops.config import load_settings
from donkit_ragops.agent.local_tools.checklist_tools import (
    tool_create_checklist,
    tool_get_checklist,
    tool_update_checklist_item,
)
from donkit_ragops.agent.local_tools.project_tools import (
    tool_add_loaded_files,
    tool_create_project,
    tool_delete_project,
    tool_get_project,
    tool_get_rag_config,
    tool_list_loaded_files,
    tool_list_projects,
    tool_save_rag_config,
)
from donkit_ragops.agent.local_tools.tools import (
    AgentTool,
    tool_db_get,
    tool_grep,
    tool_interactive_user_choice,
    tool_interactive_user_confirm,
    tool_list_directory,
    tool_quick_start_rag_config,
    tool_read_file,
    tool_time_now,
    tool_update_rag_config_field,
)
from donkit_ragops.mcp.protocol import MCPClientProtocol


class EventType(StrEnum):
    CONTENT = auto()
    TOOL_CALL_START = auto()
    TOOL_CALL_END = auto()
    TOOL_CALL_ERROR = auto()


@dataclass
class StreamEvent:
    """Event yielded during streaming response."""

    type: EventType
    content: str | None = None
    tool_name: str | None = None
    tool_args: dict | None = None
    error: str | None = None


def default_tools() -> list[AgentTool]:
    return [
        tool_time_now(),
        tool_db_get(),
        tool_list_directory(),
        tool_read_file(),
        tool_grep(),
        tool_interactive_user_choice(),
        tool_interactive_user_confirm(),
        tool_quick_start_rag_config(),
        tool_update_rag_config_field(),
        tool_create_project(),
        tool_get_project(),
        tool_list_projects(),
        tool_delete_project(),
        tool_save_rag_config(),
        tool_get_rag_config(),
        tool_add_loaded_files(),
        tool_list_loaded_files(),
        # Checklist management tools
        tool_create_checklist(),
        tool_get_checklist(),
        tool_update_checklist_item(),
    ]


class LLMAgent:
    def __init__(
        self,
        provider: LLMModelAbstract,
        tools: list[AgentTool] | None = None,
        mcp_clients: list[MCPClientProtocol] | None = None,
        max_iterations: int = 500,
        project_id_provider: Callable[[], str | None] | None = None,
    ) -> None:
        self.provider = provider
        self.local_tools = tools or default_tools()
        self.mcp_clients = mcp_clients or []
        self.mcp_tools: dict[str, tuple[dict, MCPClientProtocol]] = {}
        self.max_iterations = max_iterations
        self._project_id_provider = project_id_provider
        self._logged_tool_specs = False
        self.settings = load_settings()

    async def ainit_mcp_tools(self, register_tools: bool = True, max_tools: int = 0) -> None:
        """Initialize MCP tools asynchronously. Call this after creating the agent.

        Args:
            register_tools: If False, tools are fetched but NOT registered (for debugging).
            max_tools: If > 0, only register this many tools (for debugging).
        """
        for client in self.mcp_clients:
            try:
                logger.info(f"[MCP] Loading tools from {client.identifier}...")
                discovered = await client.alist_tools()
                logger.info(f"[MCP] Discovered {len(discovered)} tools from {client.identifier}")
                total_size = 0
                registered_count = 0
                for t in discovered:
                    tool_name = t["name"]
                    if register_tools:
                        # Respect max_tools limit if set
                        if max_tools > 0 and registered_count >= max_tools:
                            logger.debug(
                                f"[MCP] Skipping tool: {tool_name} (max_tools={max_tools})"
                            )
                            continue
                        self.mcp_tools[tool_name] = (t, client)
                        registered_count += 1
                    # Log each tool with its size
                    try:
                        tool_size = len(json.dumps(t, ensure_ascii=True))
                        total_size += tool_size
                        logger.debug(f"[MCP] Registered tool: {tool_name} (size={tool_size} bytes)")
                    except Exception:
                        logger.debug(f"[MCP] Registered tool: {tool_name}")
                logger.info(f"[MCP] Tools from {client.identifier}: total_size={total_size} bytes")
                if not register_tools:
                    logger.warning("[MCP] Tools fetched but NOT registered (debug mode)")
                elif max_tools > 0:
                    logger.warning(
                        f"[MCP] Only {registered_count} tools registered (max_tools={max_tools})"
                    )
            except Exception as ex:
                logger.error(
                    f"Failed to list tools from MCP client {client.identifier}\n {ex}",
                    exc_info=True,
                )
                pass
        logger.info(f"[MCP] Total MCP tools registered: {len(self.mcp_tools)}")

    def _tool_specs(self) -> list[Tool]:
        local_specs = [t.to_tool_spec() for t in self.local_tools]
        mcp_specs = []
        for tool_info, _ in self.mcp_tools.values():
            mcp_specs.append(
                Tool(
                    **{
                        "function": {
                            "name": tool_info["name"],
                            "description": tool_info["description"],
                            "parameters": tool_info["parameters"],
                        }
                    }
                )
            )
        specs = local_specs + mcp_specs
        if not self._logged_tool_specs:
            try:
                local_size = len(
                    json.dumps(
                        [s.model_dump() for s in local_specs],
                        ensure_ascii=True,
                    )
                )
                mcp_size = (
                    len(
                        json.dumps(
                            [s.model_dump() for s in mcp_specs],
                            ensure_ascii=True,
                        )
                    )
                    if mcp_specs
                    else 0
                )
                logger.debug(
                    "[TOOLS] local={} ({}bytes), mcp={} ({}bytes), total={}",
                    len(local_specs),
                    local_size,
                    len(mcp_specs),
                    mcp_size,
                    len(specs),
                )
            except Exception as e:
                logger.warning(f"[TOOLS] Failed to log tool specs: {e}")
            self._logged_tool_specs = True
        return specs

    def _find_tool(
        self, name: str
    ) -> tuple[AgentTool | None, tuple[dict, MCPClientProtocol] | None]:
        for t in self.local_tools:
            if t.name == name:
                return t, None
        if name in self.mcp_tools:
            return None, self.mcp_tools[name]
        return None, None

    def _get_current_project_id(self) -> str | None:
        if self._project_id_provider:
            try:
                project_id = self._project_id_provider()
                if project_id:
                    return project_id
            except Exception:
                pass
        db = open_db()
        try:
            return kv_get(db, "current_project_id")
        finally:
            close(db)

    def _get_current_rag_config(self) -> dict | None:
        project_id = self._get_current_project_id()
        if not project_id:
            return None
        db = open_db()
        try:
            raw = kv_get(db, f"project_{project_id}")
            if not raw:
                return None
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return None
            config = data.get("configuration")
            if isinstance(config, dict):
                env_password = self._get_project_env_password()
                if env_password and config.get("graph_password") != env_password:
                    config["graph_password"] = env_password
                    data["configuration"] = config
                    kv_set(db, f"project_{project_id}", json.dumps(data))
                return config
            return None
        finally:
            close(db)

    def _get_project_state(self, project_id: str) -> dict | None:
        db = open_db()
        try:
            raw = kv_get(db, f"project_{project_id}")
            if not raw:
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        finally:
            close(db)

    def _save_project_state(self, project_id: str, state: dict) -> None:
        db = open_db()
        try:
            kv_set(db, f"project_{project_id}", json.dumps(state))
        finally:
            close(db)

    def _running_in_docker(self) -> bool:
        if os.path.exists("/.dockerenv"):
            return True
        try:
            with open("/proc/1/cgroup", "r", encoding="utf-8") as f:
                data = f.read()
            return "docker" in data or "containerd" in data
        except OSError:
            return False

    async def _ensure_compose_service_running(self, service: str) -> None:
        if not self.settings.auto_start_services:
            return
        if self._running_in_docker():
            return
        project_id = self._get_current_project_id()
        if not project_id:
            return

        status_tool = self.mcp_tools.get("compose_service_status")
        start_tool = self.mcp_tools.get("compose_start_service")
        init_tool = self.mcp_tools.get("compose_init_project_compose")
        if not status_tool or not start_tool:
            return

        compose_file = Path(f"projects/{project_id}/docker-compose.yml")
        if not compose_file.exists() and init_tool:
            config = self._get_current_rag_config()
            if isinstance(config, dict):
                init_meta, init_client = init_tool
                await init_client.acall_tool(
                    init_meta["name"],
                    {"project_id": project_id, "rag_config": config},
                )

        status_meta, status_client = status_tool
        status_result = await status_client.acall_tool(
            status_meta["name"],
            {"project_id": project_id, "service": service},
        )

        is_running = False
        try:
            payload = json.loads(status_result) if isinstance(status_result, str) else status_result
            services = payload.get("services", []) if isinstance(payload, dict) else []
            for entry in services:
                if entry.get("service") == service and entry.get("status") == "running":
                    is_running = True
                    break
        except Exception:
            is_running = False

        if not is_running:
            start_meta, start_client = start_tool
            await start_client.acall_tool(
                start_meta["name"],
                {"project_id": project_id, "service": service, "detach": True},
            )

    async def _ensure_required_services(self, retrieval_mode: str, db_type: str | None) -> None:
        if retrieval_mode in {"graph", "hybrid"}:
            await self._ensure_compose_service_running("neo4j")
        if retrieval_mode in {"vector", "hybrid"}:
            service = db_type or "qdrant"
            await self._ensure_compose_service_running(service)

    def _normalize_graph_uri(self, graph_uri: str) -> str:
        if self._running_in_docker():
            return graph_uri
        if "neo4j" in graph_uri and "localhost" not in graph_uri:
            return "bolt://localhost:7687"
        return graph_uri

    def _chunks_path(self, project_id: str) -> Path:
        return Path(f"projects/{project_id}/processed/chunked")

    def _latest_chunks_mtime(self, chunks_path: Path) -> float:
        if not chunks_path.exists():
            return 0.0
        latest = 0.0
        for file_path in chunks_path.glob("*.json"):
            try:
                latest = max(latest, file_path.stat().st_mtime)
            except OSError:
                continue
        return latest

    async def _ensure_graph_built(self, config: dict) -> None:
        await self._ensure_compose_service_running("neo4j")
        project_id = self._get_current_project_id()
        if not project_id:
            return
        graph_tool_name = "graph-builder_graph_build"
        if graph_tool_name not in self.mcp_tools:
            return
        chunks_path = self._chunks_path(project_id)
        latest_mtime = self._latest_chunks_mtime(chunks_path)
        if latest_mtime == 0.0:
            return
        state = self._get_project_state(project_id) or {}
        graph_built_at = float(state.get("graph_built_at", 0.0))
        graph_built_mtime = float(state.get("graph_built_mtime", 0.0))
        if graph_built_at >= latest_mtime and graph_built_mtime >= latest_mtime:
            return

        graph_args: dict = {
            "chunks_path": str(chunks_path),
            "project_id": project_id,
        }
        for key in ("graph_database_uri", "graph_user", "graph_password"):
            value = config.get(key) if isinstance(config, dict) else None
            if value:
                if key == "graph_database_uri":
                    graph_args[key] = self._normalize_graph_uri(str(value))
                else:
                    graph_args[key] = value
        if "graph_password" not in graph_args:
            env_password = self._get_project_env_password()
            if env_password:
                graph_args["graph_password"] = env_password
        graph_options = config.get("graph_options") if isinstance(config, dict) else None
        if isinstance(graph_options, dict):
            graph_args["graph_options"] = graph_options

        tool_meta, client = self.mcp_tools[graph_tool_name]
        try:
            await client.acall_tool(tool_meta["name"], graph_args)
        except Exception as e:
            error_text = str(e).lower()
            if "unauthorized" in error_text or "authentication failure" in error_text:
                reset_tool = "compose_reset_neo4j"
                if reset_tool in self.mcp_tools:
                    reset_meta, reset_client = self.mcp_tools[reset_tool]
                    await reset_client.acall_tool(reset_meta["name"], {"project_id": project_id})
                    await client.acall_tool(tool_meta["name"], graph_args)
                else:
                    raise
            else:
                raise
        state["graph_built_at"] = time.time()
        state["graph_built_mtime"] = latest_mtime
        self._save_project_state(project_id, state)

    def _get_project_env_password(self) -> str | None:
        project_id = self._get_current_project_id()
        if not project_id:
            return None
        env_path = Path(f"projects/{project_id}/.env")
        if not env_path.exists():
            return None
        for line in env_path.read_text().splitlines():
            if line.strip().startswith("NEO4J_PASSWORD="):
                return line.split("=", 1)[1].strip() or None
        return None

    # --- Internal helpers to keep respond() small and readable ---
    def _should_execute_tools(self, resp) -> bool:
        """Whether the provider response requires tool execution."""
        return bool(
            self.provider.supports_capability(ModelCapability.TOOL_CALLING) and resp.tool_calls
        )

    def _append_synthetic_assistant_turn(self, messages: list[Message], tool_calls) -> None:
        """Append a single assistant message with tool_calls."""
        messages.append(
            Message(
                role="assistant",
                content="",  # OpenAI converter expects a string or iterable; keep empty text.
                tool_calls=tool_calls,
            )
        )

    def _parse_tool_args(self, tc) -> dict:
        """Parse tool arguments into a dict, tolerating stringified JSON or None."""
        try:
            raw = tc.function.arguments
            if isinstance(raw, dict):
                return raw
            return json.loads(raw or "{}")
        except Exception as e:
            logger.error(f"Failed to parse tool arguments: {e}")
            return {}

    async def _aexecute_tool_call(self, tc, args: dict) -> str:
        """Execute either a local or MCP tool and return a serialized string result.

        Raises on execution error, matching previous behavior.
        """
        try:
            if tc.function.name == "vectorstore_vectorstore_load":
                backend = None
                if isinstance(args, dict):
                    params = args.get("params")
                    if isinstance(params, dict):
                        backend = params.get("backend")
                config = self._get_current_rag_config()
                retrieval_mode = "vector"
                if isinstance(config, dict):
                    retrieval_mode = str(config.get("retrieval_mode", "vector")).lower()
                    if not backend:
                        backend = str(config.get("db_type", "qdrant")).lower()
                await self._ensure_required_services(retrieval_mode, backend)

            if tc.function.name == "query_search_documents":
                config = self._get_current_rag_config()
                retrieval_mode = ""
                if isinstance(config, dict):
                    retrieval_mode = str(config.get("retrieval_mode", "")).lower()
                    await self._ensure_required_services(
                        retrieval_mode, str(config.get("db_type", "")).lower()
                    )
                if retrieval_mode in {"graph", "hybrid"}:
                    await self._ensure_graph_built(config)
                    graph_tool_name = "graph-query_graph_search"
                    if graph_tool_name in self.mcp_tools:
                        tool_meta, client = self.mcp_tools[graph_tool_name]
                        graph_args: dict = {
                            "query": args.get("query", ""),
                            "k": args.get("k", 5),
                        }
                        for key in ("graph_database_uri", "graph_user", "graph_password"):
                            value = config.get(key) if isinstance(config, dict) else None
                            if value:
                                if key == "graph_database_uri":
                                    graph_args[key] = self._normalize_graph_uri(str(value))
                                else:
                                    graph_args[key] = value
                        if "graph_password" not in graph_args:
                            env_password = self._get_project_env_password()
                            if env_password:
                                graph_args["graph_password"] = env_password
                        if isinstance(config, dict):
                            graph_options = config.get("graph_options")
                            if isinstance(graph_options, dict):
                                graph_args["graph_options"] = graph_options
                        logger.debug(
                            f"Routing query_search_documents to {graph_tool_name} with args: {graph_args}"
                        )
                        result = await client.acall_tool(tool_meta["name"], graph_args)
                        return self._serialize_tool_result(result)
            if tc.function.name == "query_get_rag_prompt":
                config = self._get_current_rag_config()
                retrieval_mode = ""
                if isinstance(config, dict):
                    retrieval_mode = str(config.get("retrieval_mode", "")).lower()
                    await self._ensure_required_services(
                        retrieval_mode, str(config.get("db_type", "")).lower()
                    )
                if retrieval_mode in {"graph", "hybrid"}:
                    await self._ensure_graph_built(config)
                    graph_tool_name = "graph-query_graph_search"
                    if graph_tool_name in self.mcp_tools:
                        tool_meta, client = self.mcp_tools[graph_tool_name]
                        graph_args: dict = {
                            "query": args.get("query", ""),
                            "k": args.get("k", 5),
                        }
                        for key in ("graph_database_uri", "graph_user", "graph_password"):
                            value = config.get(key) if isinstance(config, dict) else None
                            if value:
                                if key == "graph_database_uri":
                                    graph_args[key] = self._normalize_graph_uri(str(value))
                                else:
                                    graph_args[key] = value
                        if "graph_password" not in graph_args:
                            env_password = self._get_project_env_password()
                            if env_password:
                                graph_args["graph_password"] = env_password
                        if isinstance(config, dict):
                            graph_options = config.get("graph_options")
                            if isinstance(graph_options, dict):
                                graph_args["graph_options"] = graph_options
                        logger.debug(
                            f"Routing query_get_rag_prompt to {graph_tool_name} with args: {graph_args}"
                        )
                        search_result = await client.acall_tool(tool_meta["name"], graph_args)
                        context_text = ""
                        try:
                            parsed = json.loads(search_result) if isinstance(search_result, str) else {}
                            documents = parsed.get("documents", []) if isinstance(parsed, dict) else []
                            context_text = "\n\n".join(
                                str(doc.get("content", "")).strip()
                                for doc in documents
                                if isinstance(doc, dict)
                            ).strip()
                        except Exception:
                            context_text = ""
                        generation_prompt = ""
                        if isinstance(config, dict):
                            generation_prompt = str(config.get("generation_prompt", "")).strip()
                        if generation_prompt:
                            try:
                                prompt = generation_prompt.format(
                                    context=context_text, question=str(args.get("query", ""))
                                )
                            except Exception:
                                prompt = (
                                    f"{generation_prompt}\n\nContext:\n{context_text}\n\nQuestion: "
                                    f"{args.get('query', '')}"
                                )
                        else:
                            prompt = (
                                f"Context:\n{context_text}\n\nQuestion: {args.get('query', '')}"
                            )
                        return self._serialize_tool_result(prompt)

            local_tool, mcp_tool_info = self._find_tool(tc.function.name)
            if not local_tool and not mcp_tool_info:
                logger.warning(f"Tool not found: {tc.function.name}")
                return ""

            if local_tool:
                logger.debug(f"Executing local tool {tc.function.name} with args: {args}")
                result = local_tool.handler(args)
                logger.debug(f"Local tool {tc.function.name} result: {str(result)[:200]}...")
            elif mcp_tool_info:
                logger.debug(f"Executing MCP tool {tc.function.name} with args: {args}")
                tool_meta, client = mcp_tool_info
                result = await client.acall_tool(tool_meta["name"], args)
                logger.debug(f"MCP tool {tc.function.name} result: {str(result)[:200]}...")
            else:
                result = f"Error: Tool '{tc.function.name}' not found or MCP client not configured."
                logger.error(result)

        except KeyboardInterrupt:
            logger.warning(f"Tool {tc.function.name} execution cancelled by user")
            # Don't raise - return cancellation message instead
            return "Tool execution cancelled by user (Ctrl+C)"
        except asyncio.CancelledError:
            logger.warning(f"Tool {tc.function.name} execution cancelled")
            # Don't raise - return cancellation message instead
            return "Tool execution cancelled by user (Ctrl+C)"
        except Exception as e:
            logger.error(f"Tool execution error: {e}", exc_info=True)
            # Return error message as tool result
            return f"Error: {str(e)}"

        return self._serialize_tool_result(result)

    def _serialize_tool_result(self, result) -> str:
        """Ensure the tool result is a JSON string."""
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Failed to serialize tool result to JSON: {e}")
            return str(result)

    async def _ahandle_tool_calls(self, messages: list[Message], tool_calls) -> None:
        """Full tool call handling: synthetic assistant turn, execute, and append tool messages."""
        logger.debug(f"Processing {len(tool_calls)} tool calls")
        # 1) synthetic assistant turns
        self._append_synthetic_assistant_turn(messages, tool_calls)
        # 2) execute and append responses
        for tc in tool_calls:
            args = self._parse_tool_args(tc)
            result_str = await self._aexecute_tool_call(tc, args)
            messages.append(
                Message(
                    role="tool",
                    name=tc.function.name,
                    tool_call_id=tc.id,
                    content=result_str,
                )
            )

    async def achat(
        self, *, prompt: str, system: str | None = None, model: str | None = None
    ) -> str:
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))
        return await self.arespond(messages)

    async def achat_stream(
        self, *, prompt: str, system: str | None = None, model: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Chat with streaming output. Yields text chunks."""
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))
        async for chunk in self.arespond_stream(messages):
            yield chunk

    async def arespond(self, messages: list[Message]) -> str:
        """Perform a single assistant turn given an existing message history.

        This method mutates the provided messages list by appending tool results as needed.
        Returns the assistant content.
        """
        tools = (
            self._tool_specs()
            if self.provider.supports_capability(ModelCapability.TOOL_CALLING)
            else None
        )

        for _ in range(self.max_iterations):
            request = GenerateRequest(messages=messages, tools=tools)
            resp = await self.provider.generate(request)

            # Handle tool calls if requested
            if self._should_execute_tools(resp):
                await self._ahandle_tool_calls(messages, resp.tool_calls)
                # continue loop to give tool results back to the model
                continue

            # Otherwise return the content from the model
            if not resp.content:
                retry_request = GenerateRequest(messages=messages)
                retry_resp = await self.provider.generate(retry_request)
                return retry_resp.content or ""
            return resp.content

        return ""

    async def arespond_stream(self, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        """Perform a single assistant turn with streaming output.

        This method mutates the provided messages list by appending tool results as needed.
        Yields StreamEvent objects for content chunks and tool calls.

        Returns:
            AsyncIterator that yields StreamEvent objects.
        """

        tools = (
            self._tool_specs()
            if self.provider.supports_capability(ModelCapability.TOOL_CALLING)
            else None
        )

        for _ in range(self.max_iterations):
            request = GenerateRequest(messages=messages, tools=tools)
            streamed_content = ""
            saw_finish_reason = False
            saw_tool_calls = False
            chunk_count = 0
            try:
                stream = self.provider.generate_stream(request)
                # Fallback for providers that claim streaming but return None or a bad stream.
                if stream is None:
                    resp = await self.provider.generate(request)
                    if self._should_execute_tools(resp):
                        await self._ahandle_tool_calls(messages, resp.tool_calls)
                        continue
                    if resp.content:
                        yield StreamEvent(type=EventType.CONTENT, content=resp.content)
                    return
                async for chunk in stream:  # noqa
                    chunk_count += 1
                    if chunk.finish_reason is not None:
                        saw_finish_reason = True
                    # Yield text chunks as they arrive
                    if chunk.content:
                        streamed_content += chunk.content
                        yield StreamEvent(type=EventType.CONTENT, content=chunk.content)

                    # Handle tool calls immediately when they arrive
                    if chunk.tool_calls and self.provider.supports_capability(
                        ModelCapability.TOOL_CALLING
                    ):
                        saw_tool_calls = True
                        # Append synthetic assistant turn
                        self._append_synthetic_assistant_turn(messages, chunk.tool_calls)

                        # Execute each tool and yield events
                        for tc in chunk.tool_calls:
                            args = self._parse_tool_args(tc)

                            # Yield tool call start event
                            yield StreamEvent(
                                type=EventType.TOOL_CALL_START,
                                tool_name=tc.function.name,
                                tool_args=args,
                            )

                            try:
                                # Execute tool
                                result_str = await self._aexecute_tool_call(tc, args)
                                # Add the tool result to messages
                                messages.append(
                                    Message(
                                        role="tool",
                                        name=tc.function.name,
                                        tool_call_id=tc.id,
                                        content=result_str,
                                    )
                                )
                                # Yield tool call end event
                                yield StreamEvent(
                                    type=EventType.TOOL_CALL_END, tool_name=tc.function.name
                                )
                            except Exception as e:
                                error_msg = str(e)
                                logger.error(f"Tool {tc.function.name} failed: {error_msg}")
                                # Add an error as the tool result
                                messages.append(
                                    Message(
                                        role="tool",
                                        name=tc.function.name,
                                        tool_call_id=tc.id,
                                        content=f"Error: {error_msg}",
                                    )
                                )
                                # Yield the tool call error event
                                yield StreamEvent(
                                    type=EventType.TOOL_CALL_ERROR,
                                    tool_name=tc.function.name,
                                    error=error_msg,
                                )
            except TypeError as e:
                # Some providers return a non-async-iterable (or None) from generate_stream.
                if "NoneType" in str(e) or "async iterable" in str(e) or "iterable" in str(e):
                    resp = await self.provider.generate(request)
                    if self._should_execute_tools(resp):
                        await self._ahandle_tool_calls(messages, resp.tool_calls)
                        continue
                    if resp.content:
                        yield StreamEvent(type=EventType.CONTENT, content=resp.content)
                    return
                raise
            except StopAsyncIteration:
                logger.debug(
                    "[AGENT STREAM] end: chunks={}, saw_finish_reason={}",
                    chunk_count,
                    saw_finish_reason,
                )
            except StopIteration:
                logger.debug(
                    "[AGENT STREAM] end: chunks={}, saw_finish_reason={}",
                    chunk_count,
                    saw_finish_reason,
                )
            if not saw_tool_calls:
                logger.debug(
                    "[AGENT STREAM] end: chunks={}, saw_finish_reason={}",
                    chunk_count,
                    saw_finish_reason,
                )
                if not saw_finish_reason and streamed_content:
                    logger.warning("[AGENT STREAM] Stream ended without finish_reason;")
                # Stream finished without tool calls - done
                return
            # Continue outer loop - send tool results back to model
        # Max iterations reached
        return
