"""Port availability utilities for Docker services.

Provides functions to check port availability and automatically
find free ports when default ones are occupied.
"""

from __future__ import annotations

import socket

from loguru import logger

from donkit_ragops.rag_builder.deployment.compose_manager import AVAILABLE_SERVICES

# Default host ports per service (extracted from AVAILABLE_SERVICES port mappings).
# Each entry maps service name -> list of default host ports.
_DEFAULT_HOST_PORTS: dict[str, list[int]] = {
    "qdrant": [6333, 6334],
    "chroma": [8015],
    "milvus": [19530, 19531],
    "rag-service": [8000],
}


def is_port_available(port: int, host: str = "localhost") -> bool:
    """Check whether a TCP port is available for binding.

    Args:
        port: Port number to check.
        host: Host address to check against.

    Returns:
        True if the port is free, False if it is in use.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        return result != 0


def find_free_port(
    start_port: int,
    host: str = "localhost",
    max_attempts: int = 100,
) -> int:
    """Find the first available port starting from *start_port*.

    Args:
        start_port: Port number to start scanning from.
        host: Host address to check against.
        max_attempts: Maximum number of consecutive ports to try.

    Returns:
        The first available port found.

    Raises:
        ValueError: If no free port is found within *max_attempts*.
    """
    for offset in range(max_attempts):
        candidate = start_port + offset
        if is_port_available(candidate, host):
            return candidate
    raise ValueError(f"No free port found in range {start_port}-{start_port + max_attempts - 1}")


def resolve_service_ports(
    service: str,
    host: str = "localhost",
) -> dict[str, str] | None:
    """Check default ports for a service and return custom_ports if any are busy.

    If all default ports are available, returns ``None`` (no remapping needed).
    If any default port is occupied, finds a free alternative and returns a
    ``custom_ports`` dict suitable for :func:`ComposeManager.start_service`.

    The function understands port semantics per service:
    - **qdrant**: 2 ports (HTTP + gRPC at HTTP+1)
    - **chroma**: 1 port
    - **milvus**: 2 ports (main + metrics at main+1)
    - **rag-service**: 1 port

    Args:
        service: Service name (must be a key in ``AVAILABLE_SERVICES``).
        host: Host address to check against.

    Returns:
        A dict like ``{"qdrant": "7333:6333"}`` when remapping is needed,
        or ``None`` when default ports are free.

    Raises:
        ValueError: If *service* is not in ``AVAILABLE_SERVICES``.
    """
    if service not in AVAILABLE_SERVICES:
        raise ValueError(
            f"Unknown service: {service}. Available: {list(AVAILABLE_SERVICES.keys())}"
        )

    default_ports = _DEFAULT_HOST_PORTS.get(service, [])
    if not default_ports:
        return None

    # Check if all default ports are free
    all_free = all(is_port_available(p, host) for p in default_ports)
    if all_free:
        return None

    # Need to remap: find a free base port
    primary_default = default_ports[0]
    new_base = find_free_port(primary_default, host)

    # For multi-port services, ensure consecutive ports are also free
    num_ports = len(default_ports)
    if num_ports > 1:
        while True:
            consecutive_ok = all(is_port_available(new_base + i, host) for i in range(num_ports))
            if consecutive_ok:
                break
            new_base = find_free_port(new_base + 1, host)

    # Build custom_ports mapping: "host_port:container_port"
    container_port = _get_container_port(service)
    custom_ports = {service: f"{new_base}:{container_port}"}

    logger.info(f"Port {primary_default} busy for {service}, remapped to {new_base}")

    return custom_ports


def _get_container_port(service: str) -> int:
    """Extract the primary container port from AVAILABLE_SERVICES."""
    ports_list = AVAILABLE_SERVICES[service]["ports"]
    # First port mapping: "host:container" -> take container part
    first_mapping = ports_list[0]
    return int(first_mapping.split(":")[1])
