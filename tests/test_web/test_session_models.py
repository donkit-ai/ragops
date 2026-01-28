"""Tests for session models."""

import time

import pytest

from donkit_ragops.web.session.models import SessionInfo, WebSession


def test_web_session_creation():
    """Test WebSession can be created with minimal args."""
    session = WebSession(id="test-123", provider_name="openai")

    assert session.id == "test-123"
    assert session.provider_name == "openai"
    assert session.model is None
    assert session.agent is None
    assert session.history == []
    assert session.websocket is None
    assert session.current_task is None
    assert session.mcp_initialized is False
    assert session.is_connected is False


def test_web_session_touch():
    """Test touch updates last_activity."""
    session = WebSession(id="test-123", provider_name="openai")
    original_time = session.last_activity

    time.sleep(0.01)
    session.touch()

    assert session.last_activity > original_time


def test_web_session_is_expired():
    """Test is_expired correctly detects expiration."""
    session = WebSession(id="test-123", provider_name="openai")

    # Not expired with 1 hour TTL
    assert session.is_expired(3600) is False

    # Manually set last_activity to past
    session.last_activity = time.time() - 7200  # 2 hours ago

    # Now should be expired with 1 hour TTL
    assert session.is_expired(3600) is True


def test_session_info_from_session():
    """Test SessionInfo.from_session creates correct info."""
    session = WebSession(
        id="test-123",
        provider_name="openai",
        model="gpt-4",
    )

    info = SessionInfo.from_session(session)

    assert info.id == "test-123"
    assert info.provider == "openai"
    assert info.model == "gpt-4"
    assert info.is_connected is False
    assert info.message_count == 0
    assert info.mcp_initialized is False
