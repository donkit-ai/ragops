"""Auto-upgrade functionality for donkit-ragops.

Detects installation method (pip, pipx, poetry, curl installer) and
executes appropriate upgrade command.
"""

from __future__ import annotations

import subprocess
import sys
from enum import Enum
from pathlib import Path


class InstallMethod(Enum):
    """Package installation method."""

    PIPX = "pipx"
    PIP = "pip"
    POETRY = "poetry"
    UNKNOWN = "unknown"


def detect_install_method() -> InstallMethod:
    """Detect how donkit-ragops was installed.

    Returns:
        InstallMethod enum value
    """
    executable = Path(sys.executable)

    # Check if running from pipx
    # pipx installs to ~/.local/pipx/venvs/ or similar paths
    if "pipx" in str(executable):
        return InstallMethod.PIPX

    # Check if running from poetry virtual environment
    # Poetry venvs usually have pyproject.toml in parent directories
    current_dir = Path.cwd()
    for parent in [current_dir, *current_dir.parents]:
        if (parent / "pyproject.toml").exists():
            try:
                with (parent / "pyproject.toml").open() as f:
                    content = f.read()
                    # Check if donkit-ragops is in dependencies
                    if "donkit-ragops" in content and "[tool.poetry" in content:
                        return InstallMethod.POETRY
            except (OSError, UnicodeDecodeError):
                pass

    # Default to pip
    return InstallMethod.PIP


def get_upgrade_command(method: InstallMethod) -> list[str]:
    """Get upgrade command for installation method.

    Args:
        method: Installation method

    Returns:
        Command as list of strings
    """
    if method == InstallMethod.PIPX:
        return ["pipx", "upgrade", "donkit-ragops"]
    elif method == InstallMethod.POETRY:
        return ["poetry", "update", "donkit-ragops"]
    elif method == InstallMethod.PIP:
        return [sys.executable, "-m", "pip", "install", "--upgrade", "donkit-ragops"]
    else:
        # Fallback to pip
        return [sys.executable, "-m", "pip", "install", "--upgrade", "donkit-ragops"]


def run_upgrade(method: InstallMethod | None = None) -> tuple[bool, str]:
    """Run upgrade command.

    Args:
        method: Installation method (auto-detected if None)

    Returns:
        Tuple of (success, output_message)
    """
    if method is None:
        method = detect_install_method()

    command = get_upgrade_command(method)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
            check=False,
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            return False, error_msg

    except subprocess.TimeoutExpired:
        return False, "Upgrade timed out after 5 minutes"
    except FileNotFoundError:
        tool = command[0]
        return False, f"{tool} not found. Please install it or use a different method."
    except Exception as e:
        return False, f"Unexpected error: {e}"


def format_upgrade_instructions(method: InstallMethod) -> str:
    """Get manual upgrade instructions for installation method.

    Args:
        method: Installation method

    Returns:
        Formatted instruction string
    """
    if method == InstallMethod.PIPX:
        return "pipx upgrade donkit-ragops"
    elif method == InstallMethod.POETRY:
        return "poetry update donkit-ragops"
    elif method == InstallMethod.PIP:
        return "pip install --upgrade donkit-ragops"
    else:
        return "pip install --upgrade donkit-ragops"
