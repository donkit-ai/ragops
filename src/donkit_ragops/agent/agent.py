from __future__ import annotations

from donkit.llm import LLMModelAbstract
from donkit.llm_agent import AgentTool, EventType, LLMAgent, MCPClientProtocol, StreamEvent

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
from donkit_ragops.agent.local_tools.retriever_tools import tool_local_search_documents
from donkit_ragops.agent.local_tools.tools import (
    tool_db_get,
    tool_get_recommended_defaults,
    tool_grep,
    tool_interactive_user_choice,
    tool_interactive_user_confirm,
    tool_list_directory,
    tool_quick_rag_build,
    tool_read_file,
    tool_time_now,
)
from donkit_ragops.agent.local_tools.vectorstore_tools import (
    tool_delete_from_vectorstore,
    tool_vectorstore_load,
)

# Re-export for backward compatibility
__all__ = [
    "AgentTool",
    "EventType",
    "LLMAgent",
    "MCPClientProtocol",
    "StreamEvent",
    "default_tools",
]


def default_tools(llm_model: LLMModelAbstract | None = None) -> list[AgentTool]:
    return [
        tool_time_now(),
        tool_db_get(),
        tool_list_directory(),
        tool_read_file(),
        tool_grep(),
        tool_interactive_user_choice(),
        tool_interactive_user_confirm(),
        tool_get_recommended_defaults(),
        tool_quick_rag_build(llm_model=llm_model),
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
        tool_process_documents(llm_model=llm_model),
        tool_chunk_documents(),
        tool_vectorstore_load(),
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
        tool_local_search_documents(),
        tool_evaluate_batch(),
    ]
