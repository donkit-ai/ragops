"""
MCP Server for managing docker-compose services for RAGOps.

Thin wrapper over ComposeManager from rag_builder.deployment.
"""

import warnings

# Suppress all warnings immediately, before any other imports
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="importlib._bootstrap")
warnings.simplefilter("ignore", DeprecationWarning)
import json
import os
from typing import Literal, Self

from fastmcp import FastMCP
from pydantic import BaseModel, Field, model_validator

from donkit_ragops.rag_builder.config import RagConfigValidator
from donkit_ragops.rag_builder.deployment import ComposeManager
from donkit_ragops.schemas.config_schemas import RagConfig

server = FastMCP(
    "ragops-compose-manager",
)


# --- Pydantic models for MCP tool arguments ---


class InitProjectComposeArgs(BaseModel):
    project_id: str = Field(description="Project ID")
    rag_config: RagConfig = Field(description="RAG service configuration")

    @model_validator(mode="after")
    def _set_default_collection_name(self) -> Self:
        RagConfigValidator.validate_and_fix(self.rag_config, self.project_id)
        return self


class StopContainerArgs(BaseModel):
    container_id: str = Field(description="Container ID or name")


class ServicePort(BaseModel):
    service: Literal["qdrant", "chroma", "milvus", "rag-service"] = Field(
        description="Service name"
    )
    port: str = Field(
        description="Host port mapping in format 'host_port:container_port' (e.g., '6335:6333') "
        "or just host port (e.g., '6335')"
    )


class StartServiceArgs(BaseModel):
    service: Literal["qdrant", "chroma", "milvus", "rag-service"] = Field(
        description="Service name (qdrant, chroma, milvus, rag-service)"
    )
    project_id: str = Field(description="Project ID")
    detach: bool = Field(True, description="Run in detached mode")
    build: bool = Field(False, description="Build images before starting")
    custom_ports: list[ServicePort] | None = Field(
        None,
        description=(
            "Custom port mappings for services. "
            "Example: [{'service': 'qdrant', 'port': '6335:6333'}, "
            "{'service': 'rag-service', 'port': '8001:8000'}]"
        ),
    )


class StopServiceArgs(BaseModel):
    service: str = Field(description="Service name")
    project_id: str = Field(description="Project ID")
    remove_volumes: bool = Field(False, description="Remove volumes")


class ServiceStatusArgs(BaseModel):
    service: str | None = Field(None, description="Service name (optional, default: all)")
    project_id: str = Field(description="Project ID")


class GetLogsArgs(BaseModel):
    service: str = Field(description="Service name")
    tail: int = Field(100, description="Number of lines to show")
    project_id: str = Field(description="Project ID")


# --- MCP Tools (thin wrappers) ---


@server.tool(
    name="list_available_services",
    description="Get list of available Docker Compose services that can be started",
)
async def list_available_services() -> str:
    return json.dumps(ComposeManager.list_available_services(), indent=2)


@server.tool(
    name="init_project_compose",
    description="Initialize docker-compose file in the project directory with RAG configuration",
)
async def init_project_compose(args: InitProjectComposeArgs) -> str:
    result = ComposeManager.init_project(
        project_id=args.project_id,
        rag_config=args.rag_config,
    )
    return json.dumps(result, indent=2)


@server.tool(
    name="list_containers",
    description=(
        "List Docker containers,"
        "if want to analyze whether container from another project occupies the same port"
    ),
)
async def list_containers() -> str:
    return json.dumps(ComposeManager.list_containers(), indent=2)


@server.tool(
    name="stop_container",
    description=(
        "Stop Docker container,"
        "if want to stop container from another project that occupies the same port"
    ),
)
async def stop_container(args: StopContainerArgs) -> str:
    return json.dumps(ComposeManager.stop_container(args.container_id))


@server.tool(
    name="start_service",
    description=(
        "Start a Docker Compose service,"
        "if want to redeploy with another configuration use init_project_compose first"
    ),
)
async def start_service(args: StartServiceArgs) -> str:
    custom_ports = None
    if args.custom_ports:
        custom_ports = {sp.service: sp.port for sp in args.custom_ports}

    result = ComposeManager.start_service(
        service=args.service,
        project_id=args.project_id,
        detach=args.detach,
        build=args.build,
        custom_ports=custom_ports,
    )
    return json.dumps(result, indent=2)


@server.tool(
    name="stop_service",
    description="Stop a Docker Compose service",
)
async def stop_service(args: StopServiceArgs) -> str:
    result = ComposeManager.stop_service(
        service=args.service,
        project_id=args.project_id,
        remove_volumes=args.remove_volumes,
    )
    return json.dumps(result, indent=2)


@server.tool(
    name="service_status",
    description="Check status of Docker Compose services",
)
async def service_status(args: ServiceStatusArgs) -> str:
    result = ComposeManager.service_status(
        project_id=args.project_id,
        service=args.service,
    )
    return json.dumps(result, indent=2)


@server.tool(
    name="get_logs",
    description="Get logs from a Docker Compose service",
)
async def get_logs(args: GetLogsArgs) -> str:
    result = ComposeManager.get_logs(
        service=args.service,
        project_id=args.project_id,
        tail=args.tail,
    )
    return json.dumps(result, indent=2)


def main() -> None:
    server.run(
        transport="stdio",
        log_level=os.getenv("RAGOPS_LOG_LEVEL", "CRITICAL"),
        show_banner=False,
    )


if __name__ == "__main__":
    main()
