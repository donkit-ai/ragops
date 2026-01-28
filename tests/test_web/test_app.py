"""Tests for web application factory and browser opening functionality."""

from unittest.mock import MagicMock, patch


class TestBrowserOpening:
    """Tests for automatic browser opening functionality."""

    def test_get_browser_url_with_localhost(self):
        """Test that localhost remains localhost."""
        from donkit_ragops.web.app import _get_browser_url

        result = _get_browser_url("localhost", 8067)
        assert result == "http://localhost:8067"

    def test_get_browser_url_with_0_0_0_0(self):
        """Test that 0.0.0.0 is converted to localhost."""
        from donkit_ragops.web.app import _get_browser_url

        result = _get_browser_url("0.0.0.0", 8067)
        assert result == "http://localhost:8067"

    def test_get_browser_url_with_specific_ip(self):
        """Test that specific IPs are preserved."""
        from donkit_ragops.web.app import _get_browser_url

        result = _get_browser_url("192.168.1.100", 8067)
        assert result == "http://192.168.1.100:8067"

    @patch("donkit_ragops.web.app.webbrowser.open")
    @patch("donkit_ragops.web.app.threading.Thread")
    def test_open_browser_success(self, mock_thread, mock_webbrowser_open):
        """Test that browser opens successfully with correct URL."""
        from donkit_ragops.web.app import _open_browser

        # Create a mock thread instance
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        test_url = "http://localhost:8067"
        _open_browser(test_url, delay=0)

        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    @patch("donkit_ragops.web.app.webbrowser.open")
    @patch("donkit_ragops.web.app.time.sleep")
    @patch("donkit_ragops.web.app.logger")
    def test_open_browser_failure(self, mock_logger, mock_sleep, mock_webbrowser_open):
        """Test that browser opening failure is handled gracefully."""
        from donkit_ragops.web.app import _open_browser

        # Make webbrowser.open raise an exception
        mock_webbrowser_open.side_effect = Exception("Browser not found")

        test_url = "http://localhost:8067"
        _open_browser(test_url, delay=0)

        # Wait for thread to complete
        import time

        time.sleep(0.1)

        # Should log warning but not crash
        mock_logger.warning.assert_called()

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        from fastapi import FastAPI

        from donkit_ragops.web.app import create_app
        from donkit_ragops.web.config import WebConfig

        config = WebConfig(host="localhost", port=8067)
        app = create_app(config)

        assert isinstance(app, FastAPI)
        assert app.state.config == config

    def test_create_app_registers_routes(self):
        """Test that create_app registers all expected routes."""
        from donkit_ragops.web.app import create_app
        from donkit_ragops.web.config import WebConfig

        config = WebConfig(host="localhost", port=8067)
        app = create_app(config)

        # Check that routes are registered
        route_paths = [route.path for route in app.routes]

        # Health routes should be present
        assert "/health" in route_paths
        assert "/health/ready" in route_paths
