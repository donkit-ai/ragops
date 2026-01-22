"""Tests for web API routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from donkit_ragops.web.app import create_app
from donkit_ragops.web.config import WebConfig
from donkit_ragops.web.session.models import SessionInfo, WebSession


@pytest.fixture
def test_config():
    """Create test configuration."""
    return WebConfig(
        host="127.0.0.1",
        port=8001,
        upload_dir="./test_uploads",
        session_ttl_seconds=60,
    )


@pytest.fixture
def app(test_config):
    """Create test app."""
    return create_app(test_config)


@pytest.fixture
def client(app):
    """Create test client."""
    with TestClient(app) as c:
        yield c


class TestHealthRoutes:
    """Tests for health check endpoints."""

    def test_health_returns_ok(self, client):
        """Test /health returns ok status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_ready_returns_status(self, client):
        """Test /health/ready returns ready status."""
        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "sessions" in data


class TestSessionRoutes:
    """Tests for session management endpoints."""

    @pytest.mark.skip(reason="Integration test - requires LLM provider configuration")
    def test_create_session_with_defaults(self, client):
        """Test creating a session with default settings."""
        with patch(
            "donkit_ragops.web.session.manager.get_provider"
        ) as mock_provider, patch(
            "donkit_ragops.web.session.manager.MCPClient"
        ) as mock_mcp:
            # Mock the provider
            mock_provider.return_value = MagicMock()

            response = client.post("/api/v1/sessions", json={})

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert data["provider"] is not None

    @pytest.mark.skip(reason="Integration test - requires LLM provider configuration")
    def test_create_session_with_provider(self, client):
        """Test creating a session with specific provider."""
        with patch(
            "donkit_ragops.web.session.manager.get_provider"
        ) as mock_provider, patch(
            "donkit_ragops.web.session.manager.MCPClient"
        ) as mock_mcp:
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/api/v1/sessions",
                json={"provider": "openai", "model": "gpt-4"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "openai"

    def test_get_session_not_found(self, client):
        """Test getting a non-existent session returns 404."""
        response = client.get("/api/v1/sessions/nonexistent-id")

        assert response.status_code == 404

    def test_delete_session_not_found(self, client):
        """Test deleting a non-existent session returns 404."""
        response = client.delete("/api/v1/sessions/nonexistent-id")

        assert response.status_code == 404
