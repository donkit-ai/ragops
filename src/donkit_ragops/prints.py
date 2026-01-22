from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from donkit_ragops.ui.styles import StyledText, StyleName, styled_text

try:
    pkg_version = version("donkit-ragops-ce")
except PackageNotFoundError:
    pkg_version = None


RAGOPS_LOGO_TEXT = """
   ████  █████ ████  ██ ██ ██ ████
   ██ ██ ██ ██ ██ ██ ████  ██  ██
   ████  █████ ██ ██ ██ ██ ██  ██
"""

RAGOPS_LOGO_ART = """
           ░░░░░░░░░░░░░░░
        ░░░▓▓░░░  ░░░░░░░░░░░
     ░░░░▓▓▓▓░    ░░░░░░░░░░░░░░
    ░░░░▓▓▓▓▓░    ░░░░░░░░░░░░░░░
  ░░░░░░▓▓▓▓▓     ░░░░░░░░░░░░░░░░░
 ░░░░░░░▓▓▓▓▓     ░░░░░░░░░░░░░░░░░░
 ░░░░░░░▓▓▓▓▓     ░░░░░░░░░░░░░░░░░░
░░░░░   ████████▓▓▓▓▒░░░░░░░░░░░░░░░░
░░░░    ███░  ░███▓▓▓▓░░░░░░░░░░░░░░░
░░░     ██░    ░██▓▓▓▓▓▒░░░░░░░░░░░░░
░░░     ███░  ░███▓▓▓▓▓▓▓▒░░░░░░░░░░░
░░░     ████████▓▓▓▓▓▓▓▓▓▓▓▒░░░░░░░░░
░░░     ▓▓▓▓▓▓▓▓▓▓          ░░░░░░░░░
 ░░     ▓▓▓▓▓▓▓▓▓▓   ░██░   ░░░░░░░░
 ░░     ▓▓▓▓▓▓▓▓▓▓  ░████░  ░░░░░░░░
  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   ░██░   ░░░░░░░
    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓        ░░░░░░░
     ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░
        ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░
           ▓▓▓▓▓▓░░░░░░░░░
"""


def format_header(app_version: str, provider: str, model: str | None = None) -> StyledText:
    """Format compact startup header for append-only CLI.

    Args:
        app_version: Application version
        provider: LLM provider name
        model: Optional model name (not shown for 'donkit' provider as it's managed by backend)

    Returns:
        StyledText for the header
    """
    # Don't show model for donkit provider - it's always managed by backend
    # (hardcoded in local mode, selected by backend in enterprise mode)
    model_str = f"/{model}" if model and provider != "donkit" else ""
    return styled_text(
        (StyleName.INFO, "Donkit RAGOps"),
        (None, f" v{app_version} · {provider}{model_str}"),
    )
