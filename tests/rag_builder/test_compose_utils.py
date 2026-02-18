"""Tests for rag_builder.deployment.compose_utils."""

from pathlib import Path
from unittest.mock import patch

from donkit_ragops.rag_builder.deployment import DockerEnvironment


class TestDockerEnvironment:
    def test_check_docker_running(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            ok, msg = DockerEnvironment.check_docker()
            assert ok is True
            assert msg == "Docker is running"

    def test_check_docker_not_running(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            ok, msg = DockerEnvironment.check_docker()
            assert ok is False
            assert "not running" in msg

    def test_check_docker_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            ok, msg = DockerEnvironment.check_docker()
            assert ok is False
            assert "not installed" in msg

    def test_check_docker_compose_new_syntax(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Docker Compose version v2.24.0"
            ok, msg = DockerEnvironment.check_docker_compose()
            assert ok is True

    def test_convert_path_non_wsl(self):
        with patch.object(DockerEnvironment, "is_wsl2", return_value=False):
            result = DockerEnvironment.convert_path(Path("/Users/test/project"))
            assert result == "/Users/test/project"

    def test_get_compose_command_new(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            cmd = DockerEnvironment.get_compose_command()
            assert cmd == ["docker", "compose"]

    def test_get_compose_command_legacy(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            cmd = DockerEnvironment.get_compose_command()
            assert cmd == ["docker-compose"]
