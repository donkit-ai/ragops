"""Tests for history_manager module."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from donkit.llm import FunctionCall, GenerateResponse, Message, ToolCall

from donkit_ragops.history_manager import (
    FALLBACK_TRUNCATION_NOTICE,
    _emergency_truncate_messages,
    _estimate_token_count,
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


class TestEstimateTokenCount:
    """Tests for _estimate_token_count helper."""

    def test_empty_messages(self):
        """Should return 0 for empty list."""
        assert _estimate_token_count([]) == 0

    def test_simple_text_messages(self):
        """Should count tokens for simple text messages."""
        messages = [
            Message(role="user", content="Hello world"),
            Message(role="assistant", content="Hi there"),
        ]
        result = _estimate_token_count(messages)
        # Should be > 0 and include overhead
        assert result > 8  # At least 4 overhead per message

    def test_none_content(self):
        """Should handle None content gracefully."""
        messages = [
            Message(role="assistant", content=None),
        ]
        result = _estimate_token_count(messages)
        assert result == 4  # Only per-message overhead

    def test_tool_calls_counted(self):
        """Should count tokens from tool calls."""
        messages_without_tools = [
            Message(role="assistant", content=None),
        ]
        messages_with_tools = [
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        function=FunctionCall(
                            name="read_file",
                            arguments='{"path": "/some/very/long/file/path.py"}',
                        ),
                    )
                ],
            ),
        ]
        tokens_without = _estimate_token_count(messages_without_tools)
        tokens_with = _estimate_token_count(messages_with_tools)
        assert tokens_with > tokens_without

    def test_tool_call_id_counted(self):
        """Should count tokens from tool_call_id."""
        messages = [
            Message(role="tool", tool_call_id="call_123", content="result"),
        ]
        result = _estimate_token_count(messages)
        # Should include overhead + content tokens + tool_call_id tokens
        assert result > 4

    def test_large_content_token_count(self):
        """Should produce reasonable token count for large content."""
        large_text = "word " * 50_000  # ~50K words ≈ ~50K+ tokens
        messages = [
            Message(role="user", content=large_text),
        ]
        result = _estimate_token_count(messages)
        # With tiktoken, "word " is 1 token, so ~50K tokens + overhead
        # With fallback (len//4), 250K chars // 4 = 62.5K
        # Either way, should be substantial
        assert result > 10_000


class TestCompressHistoryIfNeeded:
    """Tests for compress_history_if_needed."""

    @pytest.mark.asyncio
    async def test_no_compression_below_threshold(self):
        """Should not compress if estimated tokens below threshold."""
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
        # Create large messages to exceed 220K token threshold
        large_text = "x " * 110_000  # ~110K tokens
        history = [
            Message(role="system", content="System prompt"),
            Message(role="user", content=large_text),
            Message(role="assistant", content=large_text),
            Message(role="user", content="Q2"),
            Message(role="assistant", content="A2"),
        ]

        provider = Mock()
        provider.generate = AsyncMock(
            return_value=GenerateResponse(content="Summary of conversation")
        )

        result = await compress_history_if_needed(history, provider)

        # Should have: system + summary + last turn (Q2 + A2)
        assert len(result) == 4
        assert result[0].role == "system"
        assert result[0].content == "System prompt"
        assert result[1].role == "assistant"
        assert "[CONVERSATION HISTORY SUMMARY]" in result[1].content
        assert result[2].content == "Q2"
        assert result[3].content == "A2"

    @pytest.mark.asyncio
    async def test_compression_preserves_tool_calls(self):
        """Should preserve complete turn with tool calls and results."""
        # Create large messages to exceed 220K token threshold
        large_text = "x " * 110_000  # ~110K tokens
        history = [
            Message(role="system", content="System"),
            Message(role="user", content=large_text),
            Message(role="assistant", content=large_text),
            # Last turn with tool calls
            Message(role="user", content="Q with tool"),
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

        provider = Mock()
        provider.generate = AsyncMock(
            return_value=GenerateResponse(content="Summary of old messages")
        )

        result = await compress_history_if_needed(history, provider)

        # Should have: system + summary + last complete turn (all 4 messages)
        assert len(result) == 6
        assert result[0].role == "system"
        assert result[1].role == "assistant"  # Summary
        assert result[2].content == "Q with tool"
        assert result[3].role == "assistant"
        assert result[3].tool_calls is not None
        assert result[4].role == "tool"
        assert result[5].content == "Final answer"

    @pytest.mark.asyncio
    async def test_compression_failure_uses_mechanical_fallback(self):
        """Should use mechanical fallback when LLM compression fails."""
        large_text = "x " * 110_000  # ~110K tokens to exceed threshold
        history = [
            Message(role="user", content=large_text),
            Message(role="assistant", content=large_text),
            Message(role="user", content="Q2"),
            Message(role="assistant", content="A2"),
        ]

        provider = Mock()
        provider.generate = AsyncMock(side_effect=Exception("LLM failed"))

        result = await compress_history_if_needed(history, provider)

        # Should NOT return original history — should use fallback
        assert result != history
        # Should contain fallback notice + last turn
        assert any(FALLBACK_TRUNCATION_NOTICE in (m.content or "") for m in result)
        # Last turn (Q2 + A2) should be preserved
        assert result[-2].content == "Q2"
        assert result[-1].content == "A2"

    @pytest.mark.asyncio
    async def test_token_threshold_with_tool_calls(self):
        """Should account for tool call tokens when evaluating threshold."""
        # Create history where tool calls push it over the threshold
        # Use "x " pattern to avoid tiktoken compressing repeated single chars
        large_args = '{"data": "' + "x " * 220_000 + '"}'  # ~220K tokens
        history = [
            Message(role="user", content="Do something"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        function=FunctionCall(
                            name="big_tool",
                            arguments=large_args,
                        ),
                    )
                ],
            ),
            Message(role="tool", tool_call_id="call_1", content="Done"),
            Message(role="user", content="Next question"),
            Message(role="assistant", content="Next answer"),
        ]

        provider = Mock()
        provider.generate = AsyncMock(return_value=GenerateResponse(content="Summary"))

        result = await compress_history_if_needed(history, provider)

        # Should compress because tool call arguments are large
        assert len(result) < len(history)
        provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_preserves_system_messages(self):
        """Mechanical fallback should preserve system messages."""
        large_text = "x " * 110_000
        history = [
            Message(role="system", content="Important system prompt"),
            Message(role="user", content=large_text),
            Message(role="assistant", content=large_text),
            Message(role="user", content="Q2"),
            Message(role="assistant", content="A2"),
        ]

        provider = Mock()
        provider.generate = AsyncMock(side_effect=Exception("Context too large"))

        result = await compress_history_if_needed(history, provider)

        assert result[0].role == "system"
        assert result[0].content == "Important system prompt"
        assert any(FALLBACK_TRUNCATION_NOTICE in (m.content or "") for m in result)
        assert result[-2].content == "Q2"
        assert result[-1].content == "A2"

    @pytest.mark.asyncio
    async def test_emergency_truncation_when_last_turn_is_huge(self):
        """Should emergency-truncate individual messages when last turn exceeds threshold."""
        # Old part exceeds threshold to trigger compression
        large_old = "x " * 110_000
        # Last turn tool result is huge — exceeds threshold on its own
        large_tool_result = "y " * 210_000
        history = [
            Message(role="user", content=large_old),
            Message(role="assistant", content=large_old),
            Message(role="user", content="Q2"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        function=FunctionCall(name="big_tool", arguments="{}"),
                    )
                ],
            ),
            Message(role="tool", tool_call_id="call_1", content=large_tool_result),
            Message(role="assistant", content="Final"),
        ]

        provider = Mock()
        provider.generate = AsyncMock(side_effect=Exception("Context too large"))

        result = await compress_history_if_needed(history, provider)

        # Should have used emergency truncation
        assert any(FALLBACK_TRUNCATION_NOTICE in (m.content or "") for m in result)
        # The tool result should be truncated
        tool_msgs = [m for m in result if m.role == "tool"]
        if tool_msgs:
            assert len(tool_msgs[0].content) < len(large_tool_result)
            assert "truncated" in tool_msgs[0].content


class TestEmergencyTruncateMessages:
    """Tests for _emergency_truncate_messages helper."""

    def test_small_messages_unchanged(self):
        """Should not modify messages smaller than the limit."""
        messages = [
            Message(role="user", content="Short question"),
            Message(role="assistant", content="Short answer"),
        ]
        result = _emergency_truncate_messages(messages)
        assert result[0].content == "Short question"
        assert result[1].content == "Short answer"

    def test_large_message_truncated(self):
        """Should truncate messages exceeding EMERGENCY_MSG_MAX_CHARS."""
        large_content = "x" * 50_000
        messages = [
            Message(role="tool", tool_call_id="call_1", content=large_content),
        ]
        result = _emergency_truncate_messages(messages)
        assert len(result[0].content) < len(large_content)
        assert "truncated" in result[0].content
        # Should preserve role and tool_call_id
        assert result[0].role == "tool"
        assert result[0].tool_call_id == "call_1"

    def test_preserves_start_and_end(self):
        """Should keep beginning and end of truncated content."""
        content = "START_MARKER" + "x" * 50_000 + "END_MARKER"
        messages = [
            Message(role="assistant", content=content),
        ]
        result = _emergency_truncate_messages(messages)
        assert result[0].content.startswith("START_MARKER")
        assert result[0].content.endswith("END_MARKER")

    def test_none_content_unchanged(self):
        """Should handle None content gracefully."""
        messages = [
            Message(role="assistant", content=None),
        ]
        result = _emergency_truncate_messages(messages)
        assert result[0].content is None
