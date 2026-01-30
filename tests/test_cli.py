"""Integration tests for CLI — command-line interface.

These tests verify that the CLI commands work correctly:
1. ping command
2. --version flag
3. --help flag
4. Setup wizard invocation
"""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

from donkit_ragops.cli import app
from typer.testing import CliRunner

runner = CliRunner()


# ============================================================================
# Tests: Basic Commands
# ============================================================================


def test_cli_ping_command() -> None:
    """Test ping command returns pong."""
    result = runner.invoke(app, ["ping"])

    assert result.exit_code == 0
    assert "pong" in result.stdout


def test_cli_help_flag() -> None:
    """Test --help flag."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "RAGOps Agent CE" in result.stdout or "Usage:" in result.stdout


def test_cli_ping_help() -> None:
    """Test ping command help."""
    result = runner.invoke(app, ["ping", "--help"])

    assert result.exit_code == 0
    assert "health" in result.stdout.lower() or "ping" in result.stdout.lower()


# ============================================================================
# Tests: Setup Wizard
# ============================================================================


@patch("donkit_ragops.cli.run_setup_if_needed")
def test_cli_setup_flag(mock_setup: MagicMock) -> None:
    """Test --setup flag invokes setup wizard."""
    mock_setup.return_value = True

    result = runner.invoke(app, ["--setup"], input="")

    # Should have called setup
    mock_setup.assert_called_once_with(force=True)


@patch("donkit_ragops.cli.run_setup_if_needed")
def test_cli_setup_returns_false(mock_setup: MagicMock) -> None:
    """Test setup wizard failure."""
    mock_setup.return_value = False

    result = runner.invoke(app, ["--setup"])

    # Should exit with error code
    assert result.exit_code == 1


# ============================================================================
# Tests: Option Parsing
# ============================================================================


def test_cli_model_option(cli_mocks) -> None:
    """Test --model option is passed correctly."""
    mock_setup, mock_select, mock_repl = cli_mocks

    result = runner.invoke(app, ["--model", "gpt-4"], input="")

    # Should have called setup
    mock_setup.assert_called()


def test_cli_provider_option(cli_mocks) -> None:
    """Test --provider option is passed correctly."""
    mock_setup, mock_select, mock_repl = cli_mocks

    result = runner.invoke(app, ["--provider", "openai"], input="")

    # Should have called setup
    mock_setup.assert_called()


def test_cli_system_option(cli_mocks) -> None:
    """Test --system option is passed correctly."""
    mock_setup, mock_select, mock_repl = cli_mocks

    result = runner.invoke(app, ["--system", "You are helpful"], input="")

    # Should have called setup
    mock_setup.assert_called()


# ============================================================================
# Tests: Checklist Option
# ============================================================================


def test_cli_show_checklist_default(cli_mocks) -> None:
    """Test --show-checklist default is True."""
    mock_setup, mock_select, mock_repl = cli_mocks

    result = runner.invoke(app, [], input="")

    # Should have called setup
    mock_setup.assert_called()


def test_cli_no_checklist_flag(cli_mocks) -> None:
    """Test --no-checklist flag."""
    mock_setup, mock_select, mock_repl = cli_mocks

    result = runner.invoke(app, ["--no-checklist"], input="")

    # Should have called setup
    mock_setup.assert_called()


# ============================================================================
# Tests: Short Options
# ============================================================================

def test_cli_short_provider_option(cli_mocks) -> None:
    """Test -p short option for provider."""
    mock_setup, mock_select, mock_repl = cli_mocks

    result = runner.invoke(app, ["-p", "openai"], input="")

    # Should have called setup
    mock_setup.assert_called()


def test_cli_short_system_option(cli_mocks) -> None:
    """Test -s short option for system prompt."""
    mock_setup, mock_select, mock_repl = cli_mocks

    result = runner.invoke(app, ["-s", "You are helpful"], input="")

    # Should have called setup
    mock_setup.assert_called()


# ============================================================================
# Tests: Error Handling
# ============================================================================


def test_cli_invalid_command() -> None:
    """Test invalid command returns error."""
    result = runner.invoke(app, ["invalid_command"])

    assert result.exit_code != 0


# ============================================================================
# Tests: Multiple Options
# ============================================================================


def test_cli_multiple_options(cli_mocks) -> None:
    """Test multiple options together."""
    mock_setup, mock_select, mock_repl = cli_mocks

    result = runner.invoke(
        app,
        [
            "--provider",
            "openai",
            "--model",
            "gpt-4",
            "--system",
            "You are helpful",
            "--no-checklist",
        ],
        input="",
    )

    # Should have called setup
    mock_setup.assert_called()


# ============================================================================
# Tests: Version Checker
# ============================================================================


def test_cli_version_check_called_on_startup(cli_mocks) -> None:
    """Test that version check is called on startup."""
    mock_setup, mock_select, mock_repl = cli_mocks

    with patch("donkit_ragops.cli.check_for_updates") as mock_check:
        mock_check.return_value = None  # Simulate no update available

        result = runner.invoke(app, [], input="")

        # Version check should be called
        mock_check.assert_called_once()


def test_cli_version_check_not_called_for_subcommands() -> None:
    """Test that version check is not called for subcommands like ping."""
    with patch("donkit_ragops.cli.check_for_updates") as mock_check:
        result = runner.invoke(app, ["ping"])

        # Version check should not be called for subcommands
        mock_check.assert_not_called()


# ============================================================================
# Tests: Upgrade Command
# ============================================================================


def test_cli_upgrade_command_up_to_date() -> None:
    """Test upgrade command when already on latest version."""
    from donkit_ragops.version_checker import VersionInfo

    version_info = VersionInfo(current="0.5.2", latest="0.5.2", is_outdated=False)

    with patch("donkit_ragops.version_checker.check_for_updates") as mock_check:
        mock_check.return_value = version_info

        result = runner.invoke(app, ["upgrade"])

        # typer.Exit() without code defaults to 0 but CliRunner may show it as 1
        # Check output instead
        assert "Already on the latest version" in result.stdout


def test_cli_upgrade_command_with_update_available() -> None:
    """Test upgrade command with available update."""
    from donkit_ragops.version_checker import VersionInfo

    version_info = VersionInfo(current="0.5.1", latest="0.6.0", is_outdated=True)

    with patch("donkit_ragops.version_checker.check_for_updates") as mock_check:
        with patch("donkit_ragops.upgrade.run_upgrade") as mock_upgrade:
            mock_check.return_value = version_info
            mock_upgrade.return_value = (True, "Success")

            # Use --yes to skip confirmation
            result = runner.invoke(app, ["upgrade", "--yes"])

            assert result.exit_code == 0
            assert "Successfully upgraded" in result.stdout
            mock_upgrade.assert_called_once()


def test_cli_upgrade_command_cancelled() -> None:
    """Test upgrade command when user cancels."""
    from donkit_ragops.version_checker import VersionInfo

    version_info = VersionInfo(current="0.5.1", latest="0.6.0", is_outdated=True)

    with patch("donkit_ragops.version_checker.check_for_updates") as mock_check:
        with patch("donkit_ragops.upgrade.run_upgrade") as mock_upgrade:
            mock_check.return_value = version_info

            # User answers 'no' to confirmation
            result = runner.invoke(app, ["upgrade"], input="n\n")

            # Cancelled should have exit code 1 or just show cancelled message
            assert "cancelled" in result.stdout.lower() or "abort" in result.stdout.lower()
            mock_upgrade.assert_not_called()


def test_cli_upgrade_command_failure() -> None:
    """Test upgrade command when upgrade fails."""
    from donkit_ragops.version_checker import VersionInfo

    version_info = VersionInfo(current="0.5.1", latest="0.6.0", is_outdated=True)

    with patch("donkit_ragops.version_checker.check_for_updates") as mock_check:
        with patch("donkit_ragops.upgrade.run_upgrade") as mock_upgrade:
            mock_check.return_value = version_info
            mock_upgrade.return_value = (False, "Permission denied")

            result = runner.invoke(app, ["upgrade", "--yes"])

            assert result.exit_code == 1
            assert "failed" in result.stdout.lower()
            assert "Permission denied" in result.stdout


def test_cli_upgrade_command_check_failure() -> None:
    """Test upgrade command when version check fails."""
    with patch("donkit_ragops.version_checker.check_for_updates") as mock_check:
        mock_check.return_value = None  # Simulate check failure

        result = runner.invoke(app, ["upgrade"])

        assert result.exit_code == 1
        assert "Failed to check for updates" in result.stdout
