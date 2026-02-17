"""Web-specific tools for RAGOps Agent."""

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
    tool_list_directory,
    tool_quick_rag_build,
    tool_read_file,
    tool_time_now,
)
from donkit_ragops.web.tools.interactive import (
    create_web_progress_callback,
    current_web_session,
    web_tool_get_recommended_defaults,
    web_tool_interactive_user_choice,
    web_tool_interactive_user_confirm,
)


def web_default_tools() -> list[AgentTool]:
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
        tool_quick_rag_build(progress_callback=create_web_progress_callback()),
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


__all__ = [
    "current_web_session",
    "web_default_tools",
    "web_tool_interactive_user_choice",
    "web_tool_interactive_user_confirm",
    "web_tool_get_recommended_defaults",
]
