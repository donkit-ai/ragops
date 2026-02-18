"""Tests for rag_builder.deployment.port_utils."""

import socket
from unittest.mock import patch

import pytest

from donkit_ragops.rag_builder.deployment.port_utils import (
    find_free_port,
    is_port_available,
    resolve_service_ports,
)


class TestIsPortAvailable:
    def test_free_port(self):
        # Use a high port unlikely to be in use
        with patch("donkit_ragops.rag_builder.deployment.port_utils.socket.socket") as mock_sock_cls:
            mock_sock = mock_sock_cls.return_value.__enter__.return_value
            mock_sock.connect_ex.return_value = 1  # non-zero = port free
            assert is_port_available(59999) is True

    def test_occupied_port(self):
        with patch("donkit_ragops.rag_builder.deployment.port_utils.socket.socket") as mock_sock_cls:
            mock_sock = mock_sock_cls.return_value.__enter__.return_value
            mock_sock.connect_ex.return_value = 0  # zero = port in use
            assert is_port_available(8080) is False

    def test_custom_host(self):
        with patch("donkit_ragops.rag_builder.deployment.port_utils.socket.socket") as mock_sock_cls:
            mock_sock = mock_sock_cls.return_value.__enter__.return_value
            mock_sock.connect_ex.return_value = 1
            assert is_port_available(9999, host="127.0.0.1") is True
            mock_sock.connect_ex.assert_called_with(("127.0.0.1", 9999))


class TestFindFreePort:
    def test_finds_first_available(self):
        # Port 8000 busy, 8001 busy, 8002 free
        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            side_effect=[False, False, True],
        ):
            assert find_free_port(8000) == 8002

    def test_returns_start_if_free(self):
        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            return_value=True,
        ):
            assert find_free_port(6333) == 6333

    def test_raises_when_all_occupied(self):
        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            return_value=False,
        ):
            with pytest.raises(ValueError, match="No free port found"):
                find_free_port(8000, max_attempts=5)

    def test_max_attempts_respected(self):
        call_count = 0

        def _mock_available(port, host="localhost"):
            nonlocal call_count
            call_count += 1
            return False

        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            side_effect=_mock_available,
        ):
            with pytest.raises(ValueError):
                find_free_port(8000, max_attempts=10)
        assert call_count == 10


class TestResolveServicePorts:
    def test_all_free_returns_none(self):
        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            return_value=True,
        ):
            result = resolve_service_ports("qdrant")
            assert result is None

    def test_qdrant_port_busy(self):
        def _mock_available(port, host="localhost"):
            # Default ports 6333, 6334 are busy; 6335+ are free
            return port >= 6335

        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            side_effect=_mock_available,
        ):
            result = resolve_service_ports("qdrant")
            assert result is not None
            assert "qdrant" in result
            # Should remap to 6335:6333 (first pair of consecutive free ports)
            assert result["qdrant"] == "6335:6333"

    def test_chroma_port_busy(self):
        def _mock_available(port, host="localhost"):
            # 8015 busy, 8016 free
            return port != 8015

        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            side_effect=_mock_available,
        ):
            result = resolve_service_ports("chroma")
            assert result is not None
            assert "chroma" in result
            assert result["chroma"] == "8016:8000"

    def test_rag_service_port_busy(self):
        def _mock_available(port, host="localhost"):
            # 8000 busy, 8001 free
            return port != 8000

        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            side_effect=_mock_available,
        ):
            result = resolve_service_ports("rag-service")
            assert result is not None
            assert "rag-service" in result
            assert result["rag-service"] == "8001:8000"

    def test_milvus_ports_busy(self):
        def _mock_available(port, host="localhost"):
            # 19530, 19531 busy; 19532+ free
            return port >= 19532

        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            side_effect=_mock_available,
        ):
            result = resolve_service_ports("milvus")
            assert result is not None
            assert "milvus" in result
            assert result["milvus"] == "19532:19530"

    def test_unknown_service_raises(self):
        with pytest.raises(ValueError, match="Unknown service"):
            resolve_service_ports("nonexistent")

    def test_milvus_needs_consecutive_ports(self):
        """When first free port has its +1 occupied, skip to next pair."""
        call_log = []

        def _mock_available(port, host="localhost"):
            call_log.append(port)
            # 19530, 19531 busy (defaults)
            # 19532 free but 19533 busy
            # 19534, 19535 both free
            busy = {19530, 19531, 19533}
            return port not in busy

        with patch(
            "donkit_ragops.rag_builder.deployment.port_utils.is_port_available",
            side_effect=_mock_available,
        ):
            result = resolve_service_ports("milvus")
            assert result is not None
            assert result["milvus"] == "19534:19530"
