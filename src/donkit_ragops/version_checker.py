"""Version checker for donkit-ragops package.

Checks PyPI for newer versions and notifies users about available updates.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import NamedTuple

import httpx

PYPI_PACKAGE_URL = "https://pypi.org/pypi/donkit-ragops/json"
CACHE_FILE = Path.home() / ".cache" / "donkit-ragops" / "version_check.json"
CACHE_TTL_SECONDS = 12 * 60 * 60  # 24 hours


class VersionInfo(NamedTuple):
    """Version information from PyPI."""

    current: str
    latest: str
    is_outdated: bool


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse semantic version string into tuple of integers.

    Args:
        version: Version string like "0.5.1"

    Returns:
        Tuple of version components like (0, 5, 1)
    """
    try:
        return tuple(int(x) for x in version.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _compare_versions(current: str, latest: str) -> bool:
    """Compare two semantic versions.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        True if latest is newer than current
    """
    return _parse_version(latest) > _parse_version(current)


def _get_cached_version_info() -> VersionInfo | None:
    """Get cached version info if not expired.

    Returns:
        Cached VersionInfo or None if cache is expired or missing
    """
    if not CACHE_FILE.exists():
        return None

    try:
        with CACHE_FILE.open() as f:
            data = json.load(f)

        # Check if cache is expired
        if time.time() - data.get("timestamp", 0) > CACHE_TTL_SECONDS:
            return None

        return VersionInfo(
            current=data["current"],
            latest=data["latest"],
            is_outdated=data["is_outdated"],
        )
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def _save_version_cache(version_info: VersionInfo) -> None:
    """Save version info to cache.

    Args:
        version_info: VersionInfo to cache
    """
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE_FILE.open("w") as f:
            json.dump(
                {
                    "current": version_info.current,
                    "latest": version_info.latest,
                    "is_outdated": version_info.is_outdated,
                    "timestamp": time.time(),
                },
                f,
            )
    except OSError:
        # Silently fail if can't write cache
        pass


def _fetch_latest_version_from_pypi() -> str | None:
    """Fetch latest version from PyPI.

    Returns:
        Latest version string or None if request fails
    """
    try:
        response = httpx.get(PYPI_PACKAGE_URL, timeout=2.0)
        response.raise_for_status()
        data = response.json()
        return data["info"]["version"]
    except (httpx.HTTPError, KeyError, json.JSONDecodeError):
        return None


def check_for_updates(current_version: str, use_cache: bool = True) -> VersionInfo | None:
    """Check if newer version is available on PyPI.

    Args:
        current_version: Current installed version
        use_cache: Whether to use cached result (default: True)

    Returns:
        VersionInfo with update status or None if check fails
    """
    # Try cache first
    if use_cache:
        cached = _get_cached_version_info()
        if cached is not None and cached.current == current_version:
            return cached

    # Fetch from PyPI
    latest_version = _fetch_latest_version_from_pypi()
    if latest_version is None:
        return None

    # Compare versions
    is_outdated = _compare_versions(current_version, latest_version)

    version_info = VersionInfo(
        current=current_version,
        latest=latest_version,
        is_outdated=is_outdated,
    )

    # Save to cache
    _save_version_cache(version_info)

    return version_info


def print_update_notification(version_info: VersionInfo) -> None:
    """Print update notification if newer version is available.

    Args:
        version_info: VersionInfo to display
    """
    if not version_info.is_outdated:
        return

    from donkit_ragops.ui import get_ui
    from donkit_ragops.ui.styles import StyleName, styled_text

    ui = get_ui()

    ui.print("")
    ui.print("━" * 60, StyleName.DIM)
    ui.print_styled(
        styled_text(
            (StyleName.WARNING, "⚠️  New version available: "),
            (StyleName.SUCCESS, version_info.latest),
            (StyleName.DIM, f" (current: {version_info.current})"),
        )
    )
    ui.print_styled(
        styled_text(
            (StyleName.DIM, "Upgrade with: "),
            (StyleName.INFO, "donkit-ragops upgrade"),
        )
    )
    ui.print("━" * 60, StyleName.DIM)
    ui.print("")
