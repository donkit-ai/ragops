"""Docker Compose utilities.

Provides Docker environment detection and path conversion utilities
that were previously embedded in compose_manager_server.py.
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

# Cache for WSL2 detection
_is_wsl2_cache: bool | None = None


class DockerEnvironment:
    """Utilities for working with Docker environment."""

    @staticmethod
    def check_docker() -> tuple[bool, str]:
        """Check if Docker is installed and running.

        Returns:
            Tuple of (is_available, message).
        """
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True, "Docker is running"
            return False, "Docker is installed but not running"
        except FileNotFoundError:
            return False, "Docker is not installed"
        except subprocess.TimeoutExpired:
            return False, "Docker command timed out"
        except Exception as e:
            return False, f"Error checking Docker: {str(e)}"

    @staticmethod
    def check_docker_compose() -> tuple[bool, str]:
        """Check if docker-compose is installed.

        Returns:
            Tuple of (is_available, version_string).
        """
        # Try 'docker compose' (new syntax) first
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
        except Exception:
            pass

        # Fallback to 'docker-compose' (legacy)
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, "docker-compose command failed"
        except FileNotFoundError:
            return False, "docker-compose is not installed"
        except Exception as e:
            return False, f"Error checking docker-compose: {str(e)}"

    @staticmethod
    def is_wsl2() -> bool:
        """Detect WSL2 environment (with caching).

        Returns:
            True if running on Windows with Docker in WSL2.
        """
        global _is_wsl2_cache

        if _is_wsl2_cache is not None:
            return _is_wsl2_cache

        if platform.system() != "Windows":
            _is_wsl2_cache = False
            return False

        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.OperatingSystem}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            _is_wsl2_cache = "linux" in result.stdout.lower()
            return _is_wsl2_cache
        except Exception:
            _is_wsl2_cache = False
            return False

    @staticmethod
    def convert_path(path: Path) -> str:
        """Convert Windows path to WSL2 format if needed.

        Example:
            C:\\Users\\... -> /mnt/c/Users/...

        Args:
            path: Path to convert.

        Returns:
            Converted path string.
        """
        path_str = str(path)

        if not DockerEnvironment.is_wsl2():
            return path_str

        # Convert Windows path to WSL2 format
        if len(path_str) > 2 and path_str[1] == ":":
            drive = path_str[0].lower()
            rest = path_str[2:].replace("\\", "/")
            return f"/mnt/{drive}{rest}"

        return path_str

    @staticmethod
    def get_compose_command() -> list[str]:
        """Get the appropriate docker-compose command.

        Returns:
            Command as list: ['docker', 'compose'] or ['docker-compose'].
        """
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return ["docker", "compose"]
        except Exception:
            pass

        return ["docker-compose"]
