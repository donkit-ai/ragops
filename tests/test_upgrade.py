"""Tests for upgrade module.

Verifies auto-upgrade functionality:
1. Installation method detection
2. Upgrade command generation
3. Upgrade execution
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from donkit_ragops.upgrade import (
    InstallMethod,
    detect_install_method,
    format_upgrade_instructions,
    get_upgrade_command,
    run_upgrade,
)


# ============================================================================
# Tests: Installation Method Detection
# ============================================================================


def test_detect_install_method_pipx() -> None:
    """Test detection of pipx installation."""
    with patch("sys.executable", "/home/user/.local/pipx/venvs/donkit-ragops/bin/python"):
        method = detect_install_method()
        assert method == InstallMethod.PIPX


def test_detect_install_method_poetry(tmp_path: Path) -> None:
    """Test detection of poetry installation."""
    # Create a pyproject.toml with poetry config
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.poetry]
name = "test"

[tool.poetry.dependencies]
donkit-ragops = "^0.5.0"
"""
    )

    with patch("donkit_ragops.upgrade.Path.cwd", return_value=tmp_path):
        method = detect_install_method()
        assert method == InstallMethod.POETRY


def test_detect_install_method_pip() -> None:
    """Test detection of pip installation (default)."""
    with patch("sys.executable", "/usr/bin/python3"):
        with patch("donkit_ragops.upgrade.Path.cwd") as mock_cwd:
            # Mock cwd and parents to not have pyproject.toml
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_cwd.return_value = mock_path
            mock_path.parents = []

            method = detect_install_method()
            assert method == InstallMethod.PIP


def test_detect_install_method_poetry_non_ragops_project(tmp_path: Path) -> None:
    """Test that poetry is not detected if donkit-ragops not in dependencies."""
    # Create a pyproject.toml without donkit-ragops
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.poetry]
name = "test"

[tool.poetry.dependencies]
requests = "^2.0.0"
"""
    )

    with patch("donkit_ragops.upgrade.Path.cwd", return_value=tmp_path):
        method = detect_install_method()
        assert method == InstallMethod.PIP


# ============================================================================
# Tests: Upgrade Command Generation
# ============================================================================


def test_get_upgrade_command_pipx() -> None:
    """Test upgrade command for pipx."""
    command = get_upgrade_command(InstallMethod.PIPX)
    assert command == ["pipx", "upgrade", "donkit-ragops"]


def test_get_upgrade_command_poetry() -> None:
    """Test upgrade command for poetry."""
    command = get_upgrade_command(InstallMethod.POETRY)
    assert command == ["poetry", "update", "donkit-ragops"]


def test_get_upgrade_command_pip() -> None:
    """Test upgrade command for pip."""
    command = get_upgrade_command(InstallMethod.PIP)
    assert command == [sys.executable, "-m", "pip", "install", "--upgrade", "donkit-ragops"]


def test_get_upgrade_command_unknown() -> None:
    """Test upgrade command for unknown method falls back to pip."""
    command = get_upgrade_command(InstallMethod.UNKNOWN)
    assert command == [sys.executable, "-m", "pip", "install", "--upgrade", "donkit-ragops"]


# ============================================================================
# Tests: Upgrade Execution
# ============================================================================


def test_run_upgrade_success() -> None:
    """Test successful upgrade execution."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Successfully upgraded donkit-ragops"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        success, output = run_upgrade(InstallMethod.PIP)

        assert success is True
        assert "Successfully upgraded" in output
        mock_run.assert_called_once()


def test_run_upgrade_failure() -> None:
    """Test failed upgrade execution."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Permission denied"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        success, output = run_upgrade(InstallMethod.PIP)

        assert success is False
        assert "Permission denied" in output


def test_run_upgrade_timeout() -> None:
    """Test upgrade timeout handling."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 300)):
        success, output = run_upgrade(InstallMethod.PIP)

        assert success is False
        assert "timed out" in output.lower()


def test_run_upgrade_command_not_found() -> None:
    """Test handling when upgrade command is not found."""
    with patch("subprocess.run", side_effect=FileNotFoundError("pipx not found")):
        success, output = run_upgrade(InstallMethod.PIPX)

        assert success is False
        assert "not found" in output.lower()


def test_run_upgrade_auto_detect() -> None:
    """Test upgrade with auto-detected installation method."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result):
        with patch("donkit_ragops.upgrade.detect_install_method") as mock_detect:
            mock_detect.return_value = InstallMethod.PIP

            success, output = run_upgrade(method=None)

            assert success is True
            mock_detect.assert_called_once()


# ============================================================================
# Tests: Format Upgrade Instructions
# ============================================================================


def test_format_upgrade_instructions_pipx() -> None:
    """Test formatted instructions for pipx."""
    instructions = format_upgrade_instructions(InstallMethod.PIPX)
    assert instructions == "pipx upgrade donkit-ragops"


def test_format_upgrade_instructions_poetry() -> None:
    """Test formatted instructions for poetry."""
    instructions = format_upgrade_instructions(InstallMethod.POETRY)
    assert instructions == "poetry update donkit-ragops"


def test_format_upgrade_instructions_pip() -> None:
    """Test formatted instructions for pip."""
    instructions = format_upgrade_instructions(InstallMethod.PIP)
    assert instructions == "pip install --upgrade donkit-ragops"


def test_format_upgrade_instructions_unknown() -> None:
    """Test formatted instructions for unknown method."""
    instructions = format_upgrade_instructions(InstallMethod.UNKNOWN)
    assert instructions == "pip install --upgrade donkit-ragops"
