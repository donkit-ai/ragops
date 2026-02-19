"""Local tools for Docker Compose service management."""

from __future__ import annotations

import json
from typing import Any

from donkit_ragops.agent.local_tools.tools import AgentTool
from donkit_ragops.schemas.tool_schemas import (
    GetLogsArgs,
    InitProjectComposeArgs,
    ServiceStatusArgs,
    StartServiceArgs,
    StopContainerArgs,
    StopServiceArgs,
)


def tool_init_project_compose() -> AgentTool:
    """Tool to initialize docker-compose for a project."""

    def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.deployment import ComposeManager

        parsed = InitProjectComposeArgs(**args)
        result = ComposeManager.init_project(
            project_id=parsed.project_id,
            rag_config=parsed.rag_config,
        )
        return json.dumps(result, indent=2)

    schema = InitProjectComposeArgs.model_json_schema()

    return AgentTool(
        name="init_project_compose",
        description="Initialize docker-compose file in the project directory with RAG configuration",
        parameters=schema,
        handler=_handler,
    )


def tool_start_service() -> AgentTool:
    """Tool to start a Docker Compose service."""

    def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.deployment import ComposeManager

        parsed = StartServiceArgs(**args)
        custom_ports = None
        if parsed.custom_ports:
            custom_ports = {sp.service: sp.port for sp in parsed.custom_ports}

        result = ComposeManager.start_service(
            service=parsed.service,
            project_id=parsed.project_id,
            detach=parsed.detach,
            build=parsed.build,
            custom_ports=custom_ports,
        )
        return json.dumps(result, indent=2)

    schema = StartServiceArgs.model_json_schema()

    return AgentTool(
        name="start_service",
        description=(
            "Start a Docker Compose service,"
            "if want to redeploy with another configuration use init_project_compose first"
        ),
        parameters=schema,
        handler=_handler,
    )


def tool_stop_service() -> AgentTool:
    """Tool to stop a Docker Compose service."""

    def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.deployment import ComposeManager

        parsed = StopServiceArgs(**args)
        result = ComposeManager.stop_service(
            service=parsed.service,
            project_id=parsed.project_id,
            remove_volumes=parsed.remove_volumes,
        )
        return json.dumps(result, indent=2)

    schema = StopServiceArgs.model_json_schema()

    return AgentTool(
        name="stop_service",
        description="Stop a Docker Compose service",
        parameters=schema,
        handler=_handler,
    )


def tool_service_status() -> AgentTool:
    """Tool to check status of Docker Compose services."""

    def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.deployment import ComposeManager

        parsed = ServiceStatusArgs(**args)
        result = ComposeManager.service_status(
            project_id=parsed.project_id,
            service=parsed.service,
        )
        return json.dumps(result, indent=2)

    schema = ServiceStatusArgs.model_json_schema()

    return AgentTool(
        name="service_status",
        description="Check status of Docker Compose services",
        parameters=schema,
        handler=_handler,
    )


def tool_get_logs() -> AgentTool:
    """Tool to get logs from a Docker Compose service."""

    def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.deployment import ComposeManager

        parsed = GetLogsArgs(**args)
        result = ComposeManager.get_logs(
            service=parsed.service,
            project_id=parsed.project_id,
            tail=parsed.tail,
        )
        return json.dumps(result, indent=2)

    schema = GetLogsArgs.model_json_schema()

    return AgentTool(
        name="get_logs",
        description="Get logs from a Docker Compose service",
        parameters=schema,
        handler=_handler,
    )


def tool_list_containers() -> AgentTool:
    """Tool to list Docker containers."""

    def _handler(args: dict[str, Any]) -> str:  # noqa: ARG001
        from donkit_ragops.rag_builder.deployment import ComposeManager

        return json.dumps(ComposeManager.list_containers(), indent=2)

    return AgentTool(
        name="list_containers",
        description=(
            "List Docker containers,"
            "if want to analyze whether container from another project occupies the same port"
        ),
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        handler=_handler,
    )


def tool_list_available_services() -> AgentTool:
    """Tool to list available Docker Compose services."""

    def _handler(args: dict[str, Any]) -> str:  # noqa: ARG001
        from donkit_ragops.rag_builder.deployment import ComposeManager

        return json.dumps(ComposeManager.list_available_services(), indent=2)

    return AgentTool(
        name="list_available_services",
        description="Get list of available Docker Compose services that can be started",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        handler=_handler,
    )


def tool_stop_container() -> AgentTool:
    """Tool to stop a Docker container."""

    def _handler(args: dict[str, Any]) -> str:
        from donkit_ragops.rag_builder.deployment import ComposeManager

        parsed = StopContainerArgs(**args)
        return json.dumps(ComposeManager.stop_container(parsed.container_id))

    schema = StopContainerArgs.model_json_schema()

    return AgentTool(
        name="stop_container",
        description=(
            "Stop Docker container,"
            "if want to stop container from another project that occupies the same port"
        ),
        parameters=schema,
        handler=_handler,
    )
