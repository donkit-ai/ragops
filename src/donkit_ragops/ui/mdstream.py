"""Streaming markdown renderer for CLI output.

Uses Rich's Live display with a sliding window algorithm to render markdown
progressively during LLM response streaming. Stable lines scroll up into
terminal history while the last few lines stay in a live-updating window.

Adapted from aider's mdstream.py approach.
"""

from __future__ import annotations

import io
import time

from rich import box
from rich.console import Console
from rich.live import Live
from rich.markdown import CodeBlock, Heading, Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


class _NoInsetCodeBlock(CodeBlock):
    """Code block with syntax highlighting and no padding."""

    def __rich_console__(self, console, options):
        code = str(self.text).rstrip()
        syntax = Syntax(code, self.lexer_name, theme=self.theme, word_wrap=True, padding=(1, 0))
        yield syntax


class _LeftHeading(Heading):
    """Heading that renders left-justified."""

    def __rich_console__(self, console, options):
        text = self.text
        text.justify = "left"
        if self.tag == "h1":
            yield Panel(text, box=box.HEAVY, style="markdown.h1.border")
        else:
            if self.tag == "h2":
                yield Text("")
            yield text


class _CompactMarkdown(Markdown):
    """Markdown with compact code blocks and left-justified headings."""

    elements = {
        **Markdown.elements,
        "fence": _NoInsetCodeBlock,
        "code_block": _NoInsetCodeBlock,
        "heading_open": _LeftHeading,
    }


class MarkdownStream:
    """Streaming markdown renderer with sliding window display.

    Renders markdown progressively as text is received from LLM streaming.
    Uses Rich Live to maintain a smooth, flicker-free display:
    - Stable older lines are printed to console (terminal scrollback)
    - Last ``live_window`` lines stay in a live-updating region

    Usage::

        mdstream = MarkdownStream()
        for chunk in llm_stream:
            accumulated += chunk
            mdstream.update(accumulated)
        mdstream.update(accumulated, final=True)
    """

    live: Live | None = None
    when: float = 0
    min_delay: float = 1.0 / 20  # 20fps
    live_window: int = 6

    def __init__(
        self,
        mdargs: dict | None = None,
        console: Console | None = None,
    ) -> None:
        self.printed: list[str] = []
        self.mdargs = mdargs or {}
        self._console = console or Console()
        self.live = None
        self._live_started = False

    def _render_markdown_to_lines(self, text: str) -> list[str]:
        """Render markdown text to a list of ANSI-styled lines."""
        string_io = io.StringIO()
        console = Console(file=string_io, force_terminal=True)
        markdown = _CompactMarkdown(text, **self.mdargs)
        console.print(markdown)
        output = string_io.getvalue()
        return output.splitlines(keepends=True)

    def update(self, text: str, *, final: bool = False) -> None:
        """Update the displayed markdown content.

        Call this on every content chunk with the *accumulated* text so far.
        On the last call, pass ``final=True`` to flush and clean up.

        Splits rendered output into "stable" older lines and "unstable" tail.
        Stable lines go to console scrollback; unstable lines stay in the
        Rich Live window for smooth re-rendering.
        """
        if not self._live_started:
            self.live = Live(
                Text(""),
                console=self._console,
                refresh_per_second=1.0 / self.min_delay,
            )
            self.live.start()
            self._live_started = True

        now = time.time()
        if not final and now - self.when < self.min_delay:
            return
        self.when = now

        start = time.time()
        lines = self._render_markdown_to_lines(text)
        render_time = time.time() - start

        self.min_delay = min(max(render_time * 10, 1.0 / 20), 2)

        num_lines = len(lines)
        if not final:
            num_lines -= self.live_window

        if final or num_lines > 0:
            num_printed = len(self.printed)
            show_count = num_lines - num_printed

            if show_count <= 0 and not final:
                # Nothing new to print above the live window; just update live area below
                pass
            else:
                if show_count > 0:
                    show = "".join(lines[num_printed:num_lines])
                    self.live.console.print(Text.from_ansi(show))
                self.printed = lines[:num_lines]

        if final:
            if self.live:
                self.live.update(Text(""))
                self.live.stop()
                self.live = None
            return

        rest = "".join(lines[num_lines:])
        if self.live:
            self.live.update(Text.from_ansi(rest))

    def stop(self) -> None:
        """Force-stop the live display (e.g. on interrupt)."""
        if self.live:
            try:
                self.live.update(Text(""))
                self.live.stop()
            except Exception:
                pass
            self.live = None
        self._live_started = False

    def __del__(self) -> None:
        if self.live:
            try:
                self.live.stop()
            except Exception:
                pass
