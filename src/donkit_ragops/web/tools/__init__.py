"""Web-specific tools for RAGOps Agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from donkit.llm import LLMModelAbstract

from donkit_ragops.agent.local_tools.checklist_tools import (
    tool_create_checklist,
    tool_get_checklist,
    tool_update_checklist_item,
)
from donkit_ragops.agent.local_tools.chunker_tools import tool_chunk_documents
from donkit_ragops.agent.local_tools.compose_tools import (
    tool_get_logs,
    tool_init_project_compose,
    tool_list_available_services,
    tool_list_containers,
    tool_service_status,
    tool_start_service,
    tool_stop_container,
    tool_stop_service,
)
from donkit_ragops.agent.local_tools.evaluation_tools import tool_evaluate_batch
from donkit_ragops.agent.local_tools.planner_tools import tool_rag_config_plan
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
from donkit_ragops.agent.local_tools.query_tools import tool_get_rag_prompt, tool_search_documents
from donkit_ragops.agent.local_tools.reader_tools import tool_process_documents
from donkit_ragops.agent.local_tools.tools import (
    AgentTool,
    tool_db_get,
    tool_grep,
    tool_list_directory,
    tool_quick_rag_build,
    tool_read_file,
    tool_time_now,
)
from donkit_ragops.agent.local_tools.vectorstore_tools import (
    tool_delete_from_vectorstore,
    tool_vectorstore_load,
)
from donkit_ragops.web.tools.interactive import (
    create_web_progress_callback,
    current_web_session,
    web_tool_get_recommended_defaults,
    web_tool_interactive_user_choice,
    web_tool_interactive_user_confirm,
)


def web_default_tools(llm_model: LLMModelAbstract | None = None) -> list[AgentTool]:
    """Default tools for web agent with WebSocket-based interactive dialogs."""
    return [
        tool_time_now(),
        tool_db_get(),
        tool_list_directory(),
        tool_read_file(),
        tool_grep(),
        # Web-specific interactive tools (use WebSocket dialogs)
        web_tool_interactive_user_choice(),
        web_tool_interactive_user_confirm(),
        web_tool_get_recommended_defaults(),
        tool_quick_rag_build(progress_callback=create_web_progress_callback(), llm_model=llm_model),
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
        # Pipeline tools (local, replaces MCP servers)
        tool_process_documents(
            llm_model=llm_model, progress_callback=create_web_progress_callback()
        ),
        tool_chunk_documents(),
        tool_vectorstore_load(progress_callback=create_web_progress_callback()),
        tool_delete_from_vectorstore(),
        tool_init_project_compose(),
        tool_start_service(),
        tool_stop_service(),
        tool_service_status(),
        tool_get_logs(),
        tool_list_containers(),
        tool_list_available_services(),
        tool_stop_container(),
        tool_rag_config_plan(),
        tool_search_documents(),
        tool_get_rag_prompt(),
        tool_evaluate_batch(),
    ]


__all__ = [
    "current_web_session",
    "web_default_tools",
    "web_tool_interactive_user_choice",
    "web_tool_interactive_user_confirm",
    "web_tool_get_recommended_defaults",
]
