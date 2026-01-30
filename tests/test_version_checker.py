"""Tests for version checker module.

Verifies version checking functionality:
1. Version parsing and comparison
2. PyPI version fetching
3. Cache management
4. Update notifications
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from donkit_ragops.version_checker import (
    VersionInfo,
    _compare_versions,
    _get_cached_version_info,
    _parse_version,
    _save_version_cache,
    check_for_updates,
)


# ============================================================================
# Tests: Version Parsing and Comparison
# ============================================================================


def test_parse_version_normal() -> None:
    """Test parsing normal semantic version."""
    assert _parse_version("0.5.1") == (0, 5, 1)
    assert _parse_version("1.2.3") == (1, 2, 3)
    assert _parse_version("10.20.30") == (10, 20, 30)


def test_parse_version_invalid() -> None:
    """Test parsing invalid version strings."""
    assert _parse_version("invalid") == (0, 0, 0)
    assert _parse_version("") == (0, 0, 0)
    assert _parse_version("1.2.x") == (0, 0, 0)


def test_compare_versions_newer() -> None:
    """Test comparing versions when latest is newer."""
    assert _compare_versions("0.5.1", "0.5.2") is True
    assert _compare_versions("0.5.1", "0.6.0") is True
    assert _compare_versions("0.5.1", "1.0.0") is True


def test_compare_versions_same() -> None:
    """Test comparing identical versions."""
    assert _compare_versions("0.5.1", "0.5.1") is False


def test_compare_versions_older() -> None:
    """Test comparing versions when latest is older."""
    assert _compare_versions("0.5.2", "0.5.1") is False
    assert _compare_versions("1.0.0", "0.5.1") is False


# ============================================================================
# Tests: Cache Management
# ============================================================================


def test_save_and_get_cached_version_info(tmp_path: Path) -> None:
    """Test saving and retrieving cached version info."""
    cache_file = tmp_path / "version_check.json"

    version_info = VersionInfo(current="0.5.1", latest="0.5.2", is_outdated=True)

    with patch("donkit_ragops.version_checker.CACHE_FILE", cache_file):
        _save_version_cache(version_info)

        cached = _get_cached_version_info()

        assert cached is not None
        assert cached.current == "0.5.1"
        assert cached.latest == "0.5.2"
        assert cached.is_outdated is True


def test_get_cached_version_info_expired(tmp_path: Path) -> None:
    """Test that expired cache returns None."""
    cache_file = tmp_path / "version_check.json"

    # Create expired cache (timestamp in the past)
    cache_data = {
        "current": "0.5.1",
        "latest": "0.5.2",
        "is_outdated": True,
        "timestamp": time.time() - (25 * 60 * 60),  # 25 hours ago
    }

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("w") as f:
        json.dump(cache_data, f)

    with patch("donkit_ragops.version_checker.CACHE_FILE", cache_file):
        cached = _get_cached_version_info()
        assert cached is None


def test_get_cached_version_info_missing(tmp_path: Path) -> None:
    """Test that missing cache returns None."""
    cache_file = tmp_path / "nonexistent" / "version_check.json"

    with patch("donkit_ragops.version_checker.CACHE_FILE", cache_file):
        cached = _get_cached_version_info()
        assert cached is None


def test_get_cached_version_info_corrupted(tmp_path: Path) -> None:
    """Test that corrupted cache returns None."""
    cache_file = tmp_path / "version_check.json"

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("w") as f:
        f.write("invalid json{{{")

    with patch("donkit_ragops.version_checker.CACHE_FILE", cache_file):
        cached = _get_cached_version_info()
        assert cached is None


# ============================================================================
# Tests: PyPI Integration
# ============================================================================


def test_check_for_updates_newer_available() -> None:
    """Test checking for updates when newer version is available."""
    with patch("donkit_ragops.version_checker._fetch_latest_version_from_pypi") as mock_fetch:
        mock_fetch.return_value = "0.6.0"

        result = check_for_updates("0.5.1", use_cache=False)

        assert result is not None
        assert result.current == "0.5.1"
        assert result.latest == "0.6.0"
        assert result.is_outdated is True


def test_check_for_updates_same_version() -> None:
    """Test checking for updates when on latest version."""
    with patch("donkit_ragops.version_checker._fetch_latest_version_from_pypi") as mock_fetch:
        mock_fetch.return_value = "0.5.1"

        result = check_for_updates("0.5.1", use_cache=False)

        assert result is not None
        assert result.current == "0.5.1"
        assert result.latest == "0.5.1"
        assert result.is_outdated is False


def test_check_for_updates_newer_local() -> None:
    """Test checking for updates when local version is newer (dev version)."""
    with patch("donkit_ragops.version_checker._fetch_latest_version_from_pypi") as mock_fetch:
        mock_fetch.return_value = "0.5.1"

        result = check_for_updates("0.6.0", use_cache=False)

        assert result is not None
        assert result.current == "0.6.0"
        assert result.latest == "0.5.1"
        assert result.is_outdated is False


def test_check_for_updates_fetch_failure() -> None:
    """Test checking for updates when PyPI fetch fails."""
    with patch("donkit_ragops.version_checker._fetch_latest_version_from_pypi") as mock_fetch:
        mock_fetch.return_value = None

        result = check_for_updates("0.5.1", use_cache=False)

        assert result is None


def test_check_for_updates_uses_cache(tmp_path: Path) -> None:
    """Test that check_for_updates uses cache when available."""
    cache_file = tmp_path / "version_check.json"

    # Create valid cache
    cache_data = {
        "current": "0.5.1",
        "latest": "0.5.2",
        "is_outdated": True,
        "timestamp": time.time(),
    }

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("w") as f:
        json.dump(cache_data, f)

    with patch("donkit_ragops.version_checker.CACHE_FILE", cache_file):
        with patch("donkit_ragops.version_checker._fetch_latest_version_from_pypi") as mock_fetch:
            result = check_for_updates("0.5.1", use_cache=True)

            # Should not call PyPI if cache is valid
            mock_fetch.assert_not_called()

            assert result is not None
            assert result.latest == "0.5.2"


def test_check_for_updates_ignores_cache_when_version_changed(tmp_path: Path) -> None:
    """Test that check_for_updates ignores cache if current version changed."""
    cache_file = tmp_path / "version_check.json"

    # Create cache for different version
    cache_data = {
        "current": "0.5.0",
        "latest": "0.5.2",
        "is_outdated": True,
        "timestamp": time.time(),
    }

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("w") as f:
        json.dump(cache_data, f)

    with patch("donkit_ragops.version_checker.CACHE_FILE", cache_file):
        with patch("donkit_ragops.version_checker._fetch_latest_version_from_pypi") as mock_fetch:
            mock_fetch.return_value = "0.5.3"

            result = check_for_updates("0.5.1", use_cache=True)

            # Should fetch from PyPI because version changed
            mock_fetch.assert_called_once()

            assert result is not None
            assert result.current == "0.5.1"
            assert result.latest == "0.5.3"


# ============================================================================
# Tests: Notification Display
# ============================================================================


def test_print_update_notification_outdated(capsys) -> None:
    """Test that notification is printed for outdated version."""
    from donkit_ragops.version_checker import print_update_notification

    version_info = VersionInfo(current="0.5.1", latest="0.6.0", is_outdated=True)

    print_update_notification(version_info)

    captured = capsys.readouterr()
    assert "0.6.0" in captured.out
    assert "0.5.1" in captured.out
    assert "donkit-ragops upgrade" in captured.out


def test_print_update_notification_up_to_date(capsys) -> None:
    """Test that no notification is printed when up to date."""
    from donkit_ragops.version_checker import print_update_notification

    version_info = VersionInfo(current="0.5.1", latest="0.5.1", is_outdated=False)

    print_update_notification(version_info)

    captured = capsys.readouterr()
    # Should print nothing
    assert captured.out == ""
