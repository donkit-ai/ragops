"""Tests for rag_builder.deployment.compose_manager."""

import json
from unittest.mock import MagicMock, patch

from donkit_ragops.rag_builder.deployment.compose_manager import (
    AVAILABLE_SERVICES,
    ComposeManager,
    _apply_custom_port_env,
    _resolve_ports_and_url,
)


class TestApplyCustomPortEnv:
    def test_qdrant_ports(self):
        env = {}
        _apply_custom_port_env(env, "qdrant", {"qdrant": "7333:6333"})
        assert env["QDRANT_PORT_HTTP"] == "7333"
        assert env["QDRANT_PORT_GRPC"] == "7334"

    def test_chroma_port(self):
        env = {}
        _apply_custom_port_env(env, "chroma", {"chroma": "9000:8000"})
        assert env["CHROMA_PORT"] == "9000"

    def test_milvus_ports(self):
        env = {}
        _apply_custom_port_env(env, "milvus", {"milvus": "29530:19530"})
        assert env["MILVUS_PORT"] == "29530"
        assert env["MILVUS_METRICS_PORT"] == "29531"

    def test_rag_service_port(self):
        env = {}
        _apply_custom_port_env(env, "rag-service", {"rag-service": "9000:8000"})
        assert env["RAG_SERVICE_PORT"] == "9000"

    def test_no_matching_service(self):
        env = {}
        _apply_custom_port_env(env, "qdrant", {"chroma": "9000:8000"})
        assert env == {}

    def test_no_colon_in_port(self):
        env = {}
        _apply_custom_port_env(env, "qdrant", {"qdrant": "7333"})
        assert env == {}


class TestResolvePortsAndUrl:
    def test_default_ports(self):
        ports, url = _resolve_ports_and_url("qdrant", None)
        assert ports == ["6333:6333", "6334:6334"]
        assert url == "http://localhost:6333"

    def test_custom_qdrant_ports(self):
        ports, url = _resolve_ports_and_url("qdrant", {"qdrant": "7333:6333"})
        assert ports == ["7333:6333", "7334:6334"]
        assert url == "http://localhost:7333"

    def test_custom_chroma_port(self):
        ports, url = _resolve_ports_and_url("chroma", {"chroma": "9000:8000"})
        assert ports == ["9000:8000"]
        assert url == "http://localhost:9000"

    def test_custom_milvus_ports(self):
        ports, url = _resolve_ports_and_url("milvus", {"milvus": "29530:19530"})
        assert ports == ["29530:19530", "29531:9091"]
        assert url == "http://localhost:29530"

    def test_custom_rag_service_port(self):
        ports, url = _resolve_ports_and_url("rag-service", {"rag-service": "9000:8000"})
        assert ports == ["9000:8000"]
        assert url == "http://localhost:9000"

    def test_service_not_in_port_map(self):
        ports, url = _resolve_ports_and_url("qdrant", {"chroma": "9000:8000"})
        assert ports == ["6333:6333", "6334:6334"]
        assert url == "http://localhost:6333"


class TestComposeManager:
    def test_list_available_services(self):
        result = ComposeManager.list_available_services()
        assert "services" in result
        assert "compose_dir" in result
        assert len(result["services"]) == 4
        names = {s["name"] for s in result["services"]}
        assert names == {"qdrant", "chroma", "milvus", "rag-service"}

    def test_stop_container_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = ComposeManager.stop_container("abc123")
        assert result["status"] == "success"
        assert "abc123" in result["message"]

    def test_stop_container_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "no such container"
        with patch("subprocess.run", return_value=mock_result):
            result = ComposeManager.stop_container("abc123")
        assert result["status"] == "error"

    def test_list_containers_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ID":"abc","Names":"test"}\n{"ID":"def","Names":"test2"}'
        with patch("subprocess.run", return_value=mock_result):
            result = ComposeManager.list_containers()
        assert result["status"] == "success"
        assert len(result["containers"]) == 2

    def test_list_containers_empty(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            result = ComposeManager.list_containers()
        assert result["status"] == "success"
        assert result["containers"] == []

    def test_start_service_unknown_service(self):
        with patch(
            "donkit_ragops.rag_builder.deployment.compose_manager.DockerEnvironment.check_docker",
            return_value=(True, "ok"),
        ), patch(
            "donkit_ragops.rag_builder.deployment.compose_manager.DockerEnvironment.check_docker_compose",
            return_value=(True, "ok"),
        ):
            result = ComposeManager.start_service("nonexistent", "test-project")
        assert result["status"] == "error"
        assert "Unknown service" in result["message"]

    def test_stop_service_unknown(self):
        result = ComposeManager.stop_service("nonexistent", "test-project")
        assert result["status"] == "error"
        assert "Unknown service" in result["message"]

    def test_get_logs_unknown_service(self):
        result = ComposeManager.get_logs("nonexistent", "test-project")
        assert result["status"] == "error"
        assert "Unknown service" in result["message"]

    def test_service_status_project_not_found(self):
        result = ComposeManager.service_status("nonexistent-project-xyz-12345")
        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_parse_ps_json_array(self):
        data = [{"Name": "c1"}, {"Name": "c2"}]
        result = ComposeManager._parse_ps_json(json.dumps(data))
        assert len(result) == 2

    def test_parse_ps_json_single(self):
        result = ComposeManager._parse_ps_json('{"Name": "c1"}')
        assert len(result) == 1
        assert result[0]["Name"] == "c1"

    def test_parse_ps_json_ndjson(self):
        ndjson = '{"Name": "c1"}\n{"Name": "c2"}'
        result = ComposeManager._parse_ps_json(ndjson)
        assert len(result) == 2
