"""History management module for conversation compression.

Follows Single Responsibility Principle - handles only history-related operations.
"""

from __future__ import annotations

from donkit.llm import GenerateRequest, LLMModelAbstract, Message
from loguru import logger

HISTORY_TOKEN_THRESHOLD = 200_000  # Compress when estimated tokens exceed this
HISTORY_KEEP_RECENT_TURNS = 1  # Keep last N complete conversation turns after compression
EMERGENCY_MSG_MAX_CHARS = 8_000  # Max chars per message during emergency truncation

FALLBACK_TRUNCATION_NOTICE = (
    "[CONVERSATION HISTORY TRUNCATED]\n"
    "Previous conversation context was too large to summarize. "
    "Key context may have been lost. The most recent interaction is preserved below.\n"
    "[END TRUNCATION NOTICE]"
)

# Module-level cache for tiktoken encoding
_tiktoken_encoding = None
_tiktoken_loaded = False


def _get_tiktoken_encoding():
    """Lazy-load tiktoken encoding with caching."""
    global _tiktoken_encoding, _tiktoken_loaded
    if _tiktoken_loaded:
        return _tiktoken_encoding
    _tiktoken_loaded = True
    try:
        import tiktoken

        _tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
    except ImportError:
        logger.debug("tiktoken not available, using fallback token estimation")
    except Exception as e:
        logger.warning(f"Failed to load tiktoken encoding: {e}")
    return _tiktoken_encoding


def _count_text_tokens(text: str) -> int:
    """Count tokens in a text string using tiktoken or fallback."""
    if not text:
        return 0
    encoding = _get_tiktoken_encoding()
    if encoding:
        try:
            return len(encoding.encode(text))
        except Exception:
            pass
    return len(text) // 4


def _estimate_token_count(messages: list[Message]) -> int:
    """Estimate total token count across all messages.

    Counts tokens from message content (str or list[ContentPart]),
    tool_calls (function name + arguments), and adds per-message overhead.

    Args:
        messages: List of conversation messages

    Returns:
        Estimated token count
    """
    total = 0
    for message in messages:
        # Per-message overhead (role, formatting tokens)
        total += 4

        # Content tokens
        if isinstance(message.content, str):
            total += _count_text_tokens(message.content)
        elif isinstance(message.content, list):
            for part in message.content:
                if hasattr(part, "content") and isinstance(part.content, str):
                    total += _count_text_tokens(part.content)

        # Tool call tokens
        if message.tool_calls:
            for tool_call in message.tool_calls:
                total += _count_text_tokens(tool_call.function.name)
                total += _count_text_tokens(tool_call.function.arguments)

        # tool_call_id
        if message.tool_call_id:
            total += _count_text_tokens(message.tool_call_id)

    return total


HISTORY_SUMMARY_PROMPT = """Summarize this conversation concisely.
Preserve ALL key information: file paths, project names, configurations, decisions, errors.
Format as bullet points. Be brief but complete."""


def _find_recent_complete_turns(messages: list[Message], num_turns: int) -> list[Message]:
    """Find the last N complete conversation turns.

    A turn starts with a user message and includes all subsequent messages
    (assistant, tool) until the next user message or end of list.

    Args:
        messages: List of conversation messages (no system messages)
        num_turns: Number of complete turns to keep

    Returns:
        List of messages for the last N complete turns
    """
    if not messages:
        return []

    # Find indices where user messages start (beginning of turns)
    user_indices = [i for i, m in enumerate(messages) if m.role == "user"]

    if not user_indices:
        # No user messages - keep all
        return messages

    # Calculate how many turns to keep
    turns_to_keep = min(num_turns, len(user_indices))

    # Start index is where the (last - turns_to_keep)th user message begins
    start_idx = user_indices[-turns_to_keep]

    return messages[start_idx:]


def _emergency_truncate_messages(messages: list[Message]) -> list[Message]:
    """Truncate individual message content that is excessively large.

    Last-resort fallback when even the last turn exceeds the token threshold.
    Preserves message structure (roles, tool_call_ids) while truncating content.
    Keeps 60% from the start and 40% from the end of each oversized message.
    """
    truncated = []
    for msg in messages:
        if isinstance(msg.content, str) and len(msg.content) > EMERGENCY_MSG_MAX_CHARS:
            keep_start = int(EMERGENCY_MSG_MAX_CHARS * 0.6)
            keep_end = EMERGENCY_MSG_MAX_CHARS - keep_start - 100
            orig_len = len(msg.content)
            notice = f"\n\n[... truncated {orig_len} -> {EMERGENCY_MSG_MAX_CHARS} chars ...]\n\n"
            new_content = msg.content[:keep_start] + notice + msg.content[-keep_end:]
            truncated.append(msg.model_copy(update={"content": new_content}))
        else:
            truncated.append(msg)
    return truncated


async def compress_history_if_needed(
    history: list[Message],
    provider: LLMModelAbstract,
) -> list[Message]:
    """Compress history when it exceeds threshold by generating a summary.

    Args:
        history: List of conversation messages
        provider: LLM provider for generating summary

    Returns:
        Compressed history list or original if no compression needed
    """
    estimated_tokens = _estimate_token_count(history)
    if estimated_tokens <= HISTORY_TOKEN_THRESHOLD:
        return history

    # Separate system messages and conversation
    system_msgs = [m for m in history if m.role == "system"]
    conversation_msgs = [m for m in history if m.role != "system"]

    # Find the start of the last N complete turns
    # A turn starts with a user message
    msgs_to_keep = _find_recent_complete_turns(conversation_msgs, HISTORY_KEEP_RECENT_TURNS)
    msgs_to_summarize = conversation_msgs[: len(conversation_msgs) - len(msgs_to_keep)]

    if not msgs_to_summarize:
        return history

    # Generate summary using LLM - pass conversation as messages
    try:
        request = GenerateRequest(
            messages=msgs_to_summarize + [Message(role="user", content=HISTORY_SUMMARY_PROMPT)]
        )
        response = await provider.generate(request)
        summary = response.content or ""
        summary_text = f"[CONVERSATION HISTORY SUMMARY]\n{summary}\n[END SUMMARY]"

        # Build new history: system + summary + recent messages
        new_history = system_msgs + [Message(role="assistant", content=summary_text)] + msgs_to_keep
        logger.debug(
            f"Compressed history: {len(history)} -> {len(new_history)} messages "
            f"(estimated tokens: {estimated_tokens} -> {_estimate_token_count(new_history)})"
        )
        return new_history
    except Exception as e:
        logger.warning(f"LLM-based compression failed: {e}. Using mechanical fallback.")

    # Fallback: mechanical truncation without LLM
    new_history = (
        system_msgs + [Message(role="assistant", content=FALLBACK_TRUNCATION_NOTICE)] + msgs_to_keep
    )

    # If even the fallback exceeds the threshold, emergency-truncate individual messages
    fallback_tokens = _estimate_token_count(new_history)
    if fallback_tokens > HISTORY_TOKEN_THRESHOLD:
        logger.warning(
            f"Fallback still exceeds threshold ({fallback_tokens} > {HISTORY_TOKEN_THRESHOLD}). "
            "Emergency-truncating individual messages."
        )
        new_history = (
            system_msgs
            + [Message(role="assistant", content=FALLBACK_TRUNCATION_NOTICE)]
            + _emergency_truncate_messages(msgs_to_keep)
        )

    logger.debug(
        f"Mechanical fallback compression: {len(history)} -> {len(new_history)} messages "
        f"(estimated tokens: {estimated_tokens} -> {_estimate_token_count(new_history)})"
    )
    return new_history
