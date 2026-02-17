"""Docker Compose service manager.

Manages lifecycle of Docker Compose services for RAGOps projects:
init, start, stop, status, logs, container management.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from loguru import logger as _logger

from donkit_ragops.rag_builder.deployment.compose_utils import DockerEnvironment
from donkit_ragops.rag_builder.deployment.env_generator import (
    EnvFileGenerator,
    LLMProviderCredentials,
)
from donkit_ragops.schemas.config_schemas import RagConfig

# Package root (where compose files are stored)
PACKAGE_ROOT = Path(__file__).parent.parent.parent
COMPOSE_DIR = PACKAGE_ROOT / "compose"
SERVICES_DIR = COMPOSE_DIR / "services"

COMPOSE_FILE = "docker-compose.yml"

AVAILABLE_SERVICES: dict[str, dict] = {
    "qdrant": {
        "name": "qdrant",
        "description": "Qdrant vector database for RAG",
        "profile": "qdrant",
        "ports": ["6333:6333", "6334:6334"],
        "url": "http://localhost:6333",
    },
    "chroma": {
        "name": "chroma",
        "description": "Chroma vector database for RAG",
        "profile": "chroma",
        "ports": ["8015:8000"],
        "url": "http://localhost:8015",
    },
    "milvus": {
        "name": "milvus",
        "description": "Milvus vector database for RAG",
        "profile": "milvus",
        "ports": ["19530:19530", "9091:9091"],
        "url": "http://localhost:19530",
    },
    "rag-service": {
        "name": "rag-service",
        "description": "RAG Query service",
        "profile": "rag-service",
        "ports": ["8000:8000"],
        "url": "http://localhost:8000",
    },
}

RAG_SERVICE_API = """
Endpoints
- POST /api/query/stream – streaming final response
- POST /api/query/search –
        Returns the most relevant document chunks based on the query.
        This route just use retriever without any options. Result may be inaccurate.
- POST /api/query/evaluation – evaluation or not streaming result.
All POST endpoints use body:
{
  "query": "string"
}
"""


def _apply_custom_port_env(
    env: dict[str, str],
    service: str,
    port_map: dict[str, str],
) -> None:
    """Apply custom port environment variables for docker compose."""
    if service == "qdrant" and "qdrant" in port_map:
        port_mapping = port_map["qdrant"]
        if ":" in port_mapping:
            host_port = port_mapping.split(":")[0]
            env["QDRANT_PORT_HTTP"] = host_port
            env["QDRANT_PORT_GRPC"] = str(int(host_port) + 1)
    elif service == "chroma" and "chroma" in port_map:
        port_mapping = port_map["chroma"]
        if ":" in port_mapping:
            env["CHROMA_PORT"] = port_mapping.split(":")[0]
    elif service == "milvus" and "milvus" in port_map:
        port_mapping = port_map["milvus"]
        if ":" in port_mapping:
            host_port = port_mapping.split(":")[0]
            env["MILVUS_PORT"] = host_port
            env["MILVUS_METRICS_PORT"] = str(int(host_port) + 1)
    elif service == "rag-service" and "rag-service" in port_map:
        port_mapping = port_map["rag-service"]
        if ":" in port_mapping:
            env["RAG_SERVICE_PORT"] = port_mapping.split(":")[0]


def _resolve_ports_and_url(
    service: str,
    port_map: dict[str, str] | None,
) -> tuple[list[str], str | None]:
    """Resolve effective ports and URL for a service, considering custom ports."""
    service_info = AVAILABLE_SERVICES[service]
    ports = list(service_info["ports"])
    url = service_info.get("url")

    if not port_map or service not in port_map:
        return ports, url

    port_mapping = port_map[service]
    host_port = port_mapping.split(":")[0] if ":" in port_mapping else port_mapping
    url = f"http://localhost:{host_port}"

    if service == "qdrant":
        ports = [port_mapping, f"{int(host_port) + 1}:6334"]
    elif service in ("chroma", "rag-service"):
        ports = [port_mapping]
    elif service == "milvus":
        ports = [port_mapping, f"{int(host_port) + 1}:9091"]

    return ports, url


class ComposeManager:
    """Manages Docker Compose services for RAGOps projects."""

    @staticmethod
    def list_available_services() -> dict:
        """Get list of available Docker Compose services.

        Returns:
            Dict with services list and compose directory path.
        """
        return {
            "services": list(AVAILABLE_SERVICES.values()),
            "compose_dir": str(SERVICES_DIR),
        }

    @staticmethod
    def init_project(
        project_id: str,
        rag_config: RagConfig,
        credentials: LLMProviderCredentials | None = None,
        log_level: str | None = None,
    ) -> dict:
        """Initialize docker-compose files in a project directory.

        Copies docker-compose.yml and generates .env file.

        Args:
            project_id: Project identifier.
            rag_config: RAG configuration.
            credentials: LLM credentials. If None, reads from env.
            log_level: Log level for services.

        Returns:
            Dict with status, copied files, and message.
        """
        compose_target = Path(f"projects/{project_id}").resolve()
        compose_target.mkdir(parents=True, exist_ok=True)

        copied_files = []

        source = SERVICES_DIR / COMPOSE_FILE
        target = compose_target / COMPOSE_FILE

        if source.exists():
            shutil.copy2(source, target)
            copied_files.append(f"compose/{COMPOSE_FILE}")
        else:
            return {"status": "error", "message": f"Source compose file not found: {source}"}

        if credentials is None:
            credentials = LLMProviderCredentials.from_env()

        env_content = EnvFileGenerator.generate(
            project_id=project_id,
            rag_config=rag_config,
            credentials=credentials,
            log_level=log_level or os.getenv("RAGOPS_LOG_LEVEL", "INFO"),
        )
        env_file = compose_target / ".env"
        env_file.write_text(env_content)
        copied_files.append("compose/.env")

        return {
            "status": "success",
            "copied_files": copied_files,
            "message": f"Compose files initialized in {compose_target}",
            "rag_config_applied": rag_config is not None,
        }

    @staticmethod
    def list_containers() -> dict:
        """List running Docker containers.

        Returns:
            Dict with status and container list.
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", r"{{json .}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().splitlines():
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                return {"status": "success", "containers": containers}
            else:
                return {
                    "status": "error",
                    "message": "Failed to list containers",
                    "error": result.stderr,
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def stop_container(container_id: str) -> dict:
        """Stop a Docker container by ID or name.

        Args:
            container_id: Container ID or name.

        Returns:
            Dict with status and message.
        """
        try:
            result = subprocess.run(
                ["docker", "stop", container_id],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return {"status": "success", "message": f"Container {container_id} stopped"}
            else:
                return {
                    "status": "error",
                    "message": f"Failed to stop container {container_id}",
                    "error": result.stderr,
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def start_service(
        service: str,
        project_id: str,
        detach: bool = True,
        build: bool = False,
        custom_ports: dict[str, str] | None = None,
        auto_allocate_ports: bool = True,
    ) -> dict:
        """Start a Docker Compose service.

        Args:
            service: Service name (qdrant, chroma, milvus, rag-service).
            project_id: Project identifier.
            detach: Run in detached mode.
            build: Build images before starting.
            custom_ports: Optional custom port mapping {service_name: "host:container"}.
            auto_allocate_ports: When True and custom_ports is None, automatically
                find free ports if default ones are occupied.

        Returns:
            Dict with status, service info, URL, ports.
        """
        docker_ok, docker_msg = DockerEnvironment.check_docker()
        if not docker_ok:
            return {"status": "error", "message": docker_msg}

        compose_ok, compose_msg = DockerEnvironment.check_docker_compose()
        if not compose_ok:
            return {"status": "error", "message": compose_msg}

        if service not in AVAILABLE_SERVICES:
            return {
                "status": "error",
                "message": f"Unknown service: {service}. "
                f"Available: {list(AVAILABLE_SERVICES.keys())}",
            }

        project_path = Path(f"projects/{project_id}").resolve()
        compose_file = project_path / COMPOSE_FILE
        profile = AVAILABLE_SERVICES[service]["profile"]

        if not compose_file.exists():
            return {
                "status": "error",
                "message": f"Compose file not found: {compose_file}. "
                f"Run init_project_compose first.",
            }

        # Auto-allocate free ports when defaults are occupied
        if auto_allocate_ports and custom_ports is None:
            from donkit_ragops.rag_builder.deployment.port_utils import (
                resolve_service_ports,
            )

            try:
                resolved = resolve_service_ports(service)
                if resolved is not None:
                    custom_ports = resolved
                    _logger.info(f"Auto-allocated ports for {service}: {custom_ports}")
            except ValueError:
                _logger.warning(
                    f"Could not auto-allocate ports for {service}, proceeding with defaults"
                )

        cmd = DockerEnvironment.get_compose_command()
        cmd.extend(
            [
                "-f",
                DockerEnvironment.convert_path(compose_file),
                "--project-name",
                f"ragops-{project_id}",
                "--profile",
                profile,
                "up",
            ]
        )

        if detach:
            cmd.append("-d")
        if build:
            cmd.append("--build")

        env = os.environ.copy()
        if custom_ports:
            _apply_custom_port_env(env, service, custom_ports)

        try:
            run_kwargs: dict = {
                "capture_output": True,
                "text": True,
                "timeout": 120,
                "env": env,
            }
            if not DockerEnvironment.is_wsl2():
                run_kwargs["cwd"] = project_path

            result = subprocess.run(cmd, **run_kwargs)

            if result.returncode == 0:
                ports, url = _resolve_ports_and_url(service, custom_ports)
                service_info = AVAILABLE_SERVICES[service]

                success_result = {
                    "status": "success",
                    "service": service,
                    "message": f"{service_info['description']} started successfully",
                    "url": url,
                    "ports": ports,
                    "custom_ports_applied": custom_ports is not None,
                    "output": result.stdout,
                }
                if service == "rag-service":
                    success_result["rag_service_api_reference"] = RAG_SERVICE_API
                return success_result
            else:
                return {
                    "status": "error",
                    "message": "Failed to start service",
                    "error": result.stderr,
                }

        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command timed out after 120 seconds"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def stop_service(
        service: str,
        project_id: str,
        remove_volumes: bool = False,
    ) -> dict:
        """Stop a Docker Compose service.

        Args:
            service: Service name.
            project_id: Project identifier.
            remove_volumes: Remove volumes on stop.

        Returns:
            Dict with status and message.
        """
        if service not in AVAILABLE_SERVICES:
            return {"status": "error", "message": f"Unknown service: {service}"}

        project_path = Path(f"projects/{project_id}").resolve()
        compose_file = project_path / COMPOSE_FILE
        profile = AVAILABLE_SERVICES[service]["profile"]

        if not compose_file.exists():
            return {"status": "error", "message": f"Compose file not found: {compose_file}"}

        cmd = DockerEnvironment.get_compose_command()
        cmd.extend(
            [
                "-f",
                DockerEnvironment.convert_path(compose_file),
                "--project-name",
                f"ragops-{project_id}",
                "--profile",
                profile,
                "down",
            ]
        )

        if remove_volumes:
            cmd.append("-v")

        try:
            run_kwargs: dict = {
                "capture_output": True,
                "text": True,
                "timeout": 60,
            }
            if not DockerEnvironment.is_wsl2():
                run_kwargs["cwd"] = project_path

            result = subprocess.run(cmd, **run_kwargs)
            if result.returncode == 0:
                return {
                    "status": "success",
                    "service": service,
                    "message": f"{service} stopped successfully",
                    "output": result.stdout,
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to stop service",
                    "error": result.stderr,
                }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def service_status(
        project_id: str,
        service: str | None = None,
    ) -> dict:
        """Check status of Docker Compose services.

        Args:
            project_id: Project identifier.
            service: Optional service name. If None, checks all services.

        Returns:
            Dict with service statuses.
        """
        project_path = Path(f"projects/{project_id}").resolve()

        if not project_path.exists():
            return {"status": "error", "message": "Project directory not found"}

        services_to_check = [service] if service else list(AVAILABLE_SERVICES.keys())
        compose_file = project_path / COMPOSE_FILE

        if not compose_file.exists():
            return {"status": "error", "message": f"Compose file not found: {compose_file}"}

        statuses = []
        cmd = DockerEnvironment.get_compose_command()

        for svc in services_to_check:
            if svc not in AVAILABLE_SERVICES:
                continue

            profile = AVAILABLE_SERVICES[svc]["profile"]

            try:
                run_kwargs: dict = {
                    "capture_output": True,
                    "text": True,
                    "timeout": 10,
                }
                if not DockerEnvironment.is_wsl2():
                    run_kwargs["cwd"] = project_path

                result = subprocess.run(
                    [
                        *cmd,
                        "-f",
                        DockerEnvironment.convert_path(compose_file),
                        "--project-name",
                        f"ragops-{project_id}",
                        "--profile",
                        profile,
                        "ps",
                        "--format",
                        "json",
                    ],
                    **run_kwargs,
                )

                if result.returncode == 0 and result.stdout.strip():
                    containers = ComposeManager._parse_ps_json(result.stdout.strip())
                    statuses.append(
                        {
                            "service": svc,
                            "status": "running" if containers else "stopped",
                            "containers": containers,
                        }
                    )
                else:
                    statuses.append({"service": svc, "status": "stopped", "containers": []})

            except Exception as e:
                statuses.append({"service": svc, "status": "error", "error": str(e)})

        return {"services": statuses}

    @staticmethod
    def get_logs(
        service: str,
        project_id: str,
        tail: int = 100,
    ) -> dict:
        """Get logs from a Docker Compose service.

        Args:
            service: Service name.
            project_id: Project identifier.
            tail: Number of log lines to return.

        Returns:
            Dict with service name and logs text.
        """
        if service not in AVAILABLE_SERVICES:
            return {"status": "error", "message": f"Unknown service: {service}"}

        project_path = Path(f"projects/{project_id}").resolve()
        compose_file = project_path / COMPOSE_FILE
        profile = AVAILABLE_SERVICES[service]["profile"]

        if not compose_file.exists():
            return {"status": "error", "message": f"Compose file not found: {compose_file}"}

        cmd = DockerEnvironment.get_compose_command()
        cmd.extend(
            [
                "-f",
                DockerEnvironment.convert_path(compose_file),
                "--project-name",
                f"ragops-{project_id}",
                "--profile",
                profile,
                "logs",
                "--tail",
                str(tail),
                service,
            ]
        )

        try:
            run_kwargs: dict = {
                "capture_output": True,
                "text": True,
                "timeout": 30,
            }
            if not DockerEnvironment.is_wsl2():
                run_kwargs["cwd"] = project_path

            result = subprocess.run(cmd, **run_kwargs)
            return {"service": service, "logs": result.stdout}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _parse_ps_json(stdout: str) -> list[dict]:
        """Parse docker compose ps --format json output.

        Handles array, single object, and NDJSON formats.
        """
        if stdout.startswith("["):
            return json.loads(stdout)
        elif "\n" in stdout:
            return [json.loads(line) for line in stdout.split("\n") if line.strip()]
        else:
            return [json.loads(stdout)]
