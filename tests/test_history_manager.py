"""Tests for history_manager module."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from donkit.llm import GenerateResponse, Message

from donkit_ragops.history_manager import (
    _find_recent_complete_turns,
    compress_history_if_needed,
)


class TestFindRecentCompleteTurns:
    """Tests for _find_recent_complete_turns helper."""

    def test_empty_messages(self):
        """Should return empty list for empty input."""
        result = _find_recent_complete_turns([], num_turns=1)
        assert result == []

    def test_no_user_messages(self):
        """Should return all messages if no user messages."""
        messages = [
            Message(role="assistant", content="Hello"),
            Message(role="assistant", content="World"),
        ]
        result = _find_recent_complete_turns(messages, num_turns=1)
        assert result == messages

    def test_single_turn(self):
        """Should keep only the last complete turn."""
        messages = [
            Message(role="user", content="First question"),
            Message(role="assistant", content="First answer"),
            Message(role="user", content="Second question"),
            Message(role="assistant", content="Second answer"),
        ]
        result = _find_recent_complete_turns(messages, num_turns=1)
        assert len(result) == 2
        assert result[0].content == "Second question"
        assert result[1].content == "Second answer"

    def test_turn_with_tool_calls(self):
        """Should keep assistant message with tool calls and tool results together."""
        from donkit.llm import FunctionCall, ToolCall

        messages = [
            Message(role="user", content="Old question"),
            Message(role="assistant", content="Old answer"),
            Message(role="user", content="New question"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_123",
                        function=FunctionCall(name="test_tool", arguments="{}"),
                    )
                ],
            ),
            Message(role="tool", tool_call_id="call_123", content="Tool result"),
            Message(role="assistant", content="Final answer"),
        ]
        result = _find_recent_complete_turns(messages, num_turns=1)
        # Should keep from "New question" to the end
        assert len(result) == 4
        assert result[0].content == "New question"
        assert result[1].role == "assistant"
        assert result[1].tool_calls is not None
        assert result[2].role == "tool"
        assert result[3].content == "Final answer"

    def test_multiple_turns(self):
        """Should keep last N turns."""
        messages = [
            Message(role="user", content="Q1"),
            Message(role="assistant", content="A1"),
            Message(role="user", content="Q2"),
            Message(role="assistant", content="A2"),
            Message(role="user", content="Q3"),
            Message(role="assistant", content="A3"),
        ]
        result = _find_recent_complete_turns(messages, num_turns=2)
        assert len(result) == 4  # Last 2 turns = 4 messages
        assert result[0].content == "Q2"
        assert result[1].content == "A2"
        assert result[2].content == "Q3"
        assert result[3].content == "A3"

    def test_more_turns_requested_than_available(self):
        """Should return all messages if requesting more turns than available."""
        messages = [
            Message(role="user", content="Q1"),
            Message(role="assistant", content="A1"),
        ]
        result = _find_recent_complete_turns(messages, num_turns=5)
        assert result == messages


class TestCompressHistoryIfNeeded:
    """Tests for compress_history_if_needed."""

    @pytest.mark.asyncio
    async def test_no_compression_below_threshold(self):
        """Should not compress if user messages below threshold."""
        history = [
            Message(role="system", content="System prompt"),
            Message(role="user", content="Q1"),
            Message(role="assistant", content="A1"),
            Message(role="user", content="Q2"),
            Message(role="assistant", content="A2"),
        ]
        provider = Mock()

        result = await compress_history_if_needed(history, provider)

        # Should return original history unchanged
        assert result == history
        provider.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_compression_preserves_system_messages(self):
        """Should preserve system messages when compressing."""
        # Create 26 user messages to exceed threshold of 25
        history = [Message(role="system", content="System prompt")]
        for i in range(1, 27):  # Q1-Q26
            history.append(Message(role="user", content=f"Q{i}"))
            history.append(Message(role="assistant", content=f"A{i}"))

        provider = Mock()
        provider.generate = AsyncMock(
            return_value=GenerateResponse(content="Summary of conversation")
        )

        result = await compress_history_if_needed(history, provider)

        # Should have: system + summary + last turn (Q26 + A26)
        assert len(result) == 4
        assert result[0].role == "system"
        assert result[0].content == "System prompt"
        assert result[1].role == "assistant"
        assert "[CONVERSATION HISTORY SUMMARY]" in result[1].content
        assert result[2].content == "Q26"
        assert result[3].content == "A26"

    @pytest.mark.asyncio
    async def test_compression_preserves_tool_calls(self):
        """Should preserve complete turn with tool calls and results."""
        from donkit.llm import FunctionCall, ToolCall

        # Create 26 user messages to exceed threshold of 25
        history = [Message(role="system", content="System")]
        for i in range(1, 26):  # Q1-Q25
            history.append(Message(role="user", content=f"Q{i}"))
            history.append(Message(role="assistant", content=f"A{i}"))

        # Q26 with tool calls - 26th user message triggers compression
        history.extend([
            Message(role="user", content="Q26 with tool"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_123",
                        function=FunctionCall(name="test_tool", arguments="{}"),
                    )
                ],
            ),
            Message(role="tool", tool_call_id="call_123", content="Tool result"),
            Message(role="assistant", content="Final answer"),
        ])

        provider = Mock()
        provider.generate = AsyncMock(
            return_value=GenerateResponse(content="Summary of old messages")
        )

        result = await compress_history_if_needed(history, provider)

        # Should have: system + summary + last complete turn (all 4 messages)
        assert len(result) == 6
        assert result[0].role == "system"
        assert result[1].role == "assistant"  # Summary
        assert result[2].content == "Q26 with tool"
        assert result[3].role == "assistant"
        assert result[3].tool_calls is not None
        assert result[4].role == "tool"
        assert result[5].content == "Final answer"

    @pytest.mark.asyncio
    async def test_compression_failure_returns_original(self):
        """Should return original history if compression fails."""
        history = [
            Message(role="user", content="Q1"),
            Message(role="assistant", content="A1"),
            Message(role="user", content="Q2"),
            Message(role="assistant", content="A2"),
            Message(role="user", content="Q3"),
            Message(role="assistant", content="A3"),
            Message(role="user", content="Q4"),
            Message(role="assistant", content="A4"),
            Message(role="user", content="Q5"),
            Message(role="assistant", content="A5"),
            Message(role="user", content="Q6"),
            Message(role="assistant", content="A6"),
        ]

        provider = Mock()
        provider.generate = AsyncMock(side_effect=Exception("LLM failed"))

        result = await compress_history_if_needed(history, provider)

        # Should return original history on error
        assert result == history
