"""History management module for conversation compression.

Follows Single Responsibility Principle - handles only history-related operations.
"""

from __future__ import annotations

from donkit.llm import GenerateRequest, LLMModelAbstract, Message
from loguru import logger

HISTORY_COMPRESSION_THRESHOLD = 25  # Compress when user messages exceed this
HISTORY_KEEP_RECENT_TURNS = 1  # Keep last N complete conversation turns after compression

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
    user_msg_count = sum(1 for m in history if m.role == "user")
    if user_msg_count <= HISTORY_COMPRESSION_THRESHOLD:
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
        logger.debug(f"Compressed history: {len(history)} -> {len(new_history)} messages")
        return new_history
    except Exception as e:
        logger.warning(f"Failed to compress history: {e}")
        return history
