"""Tests for web configuration."""

from donkit_ragops.web.config import WebConfig, get_web_config


def test_web_config_defaults():
    """Test WebConfig has sensible defaults."""
    config = WebConfig()

    assert config.host == "0.0.0.0"
    assert config.port == 8067
    assert config.reload is False
    assert config.session_ttl_seconds == 7200
    assert config.cleanup_interval_seconds == 300
    assert config.max_upload_size_mb == 100
    assert config.upload_dir == "./uploads"
    assert len(config.cors_origins) > 0


def test_get_web_config():
    """Test get_web_config returns a WebConfig instance."""
    config = get_web_config()
    assert isinstance(config, WebConfig)
