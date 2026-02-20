"""Tests for the Solarman network discovery module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.solarman_deye.discovery import (
    DISCOVERY_MESSAGE,
    DISCOVERY_PORT,
    DiscoveredDevice,
    scan_network,
)


def test_scan_parses_response():
    """Test that a valid UDP response is parsed into a DiscoveredDevice."""
    mock_sock = MagicMock()
    responses = [
        (b"192.168.86.69,AA:BB:CC:DD:EE:FF,2504221369", ("192.168.86.69", DISCOVERY_PORT)),
    ]

    def _recvfrom(bufsize):
        if responses:
            return responses.pop(0)
        import socket
        raise socket.timeout

    mock_sock.recvfrom.side_effect = _recvfrom

    with patch("custom_components.solarman_deye.discovery.socket.socket", return_value=mock_sock):
        devices = scan_network(timeout=1.0)

    assert len(devices) == 1
    assert devices[0] == DiscoveredDevice(ip="192.168.86.69", mac="AA:BB:CC:DD:EE:FF", serial=2504221369)
    mock_sock.sendto.assert_called_once_with(DISCOVERY_MESSAGE, ("255.255.255.255", DISCOVERY_PORT))


def test_scan_no_response():
    """Test that an empty network returns an empty list."""
    import socket as socket_mod

    mock_sock = MagicMock()
    mock_sock.recvfrom.side_effect = socket_mod.timeout

    with patch("custom_components.solarman_deye.discovery.socket.socket", return_value=mock_sock):
        devices = scan_network(timeout=0.1)

    assert devices == []


def test_scan_ignores_invalid_responses():
    """Test that malformed responses are silently skipped."""
    mock_sock = MagicMock()
    responses = [
        (b"garbage data", ("10.0.0.1", DISCOVERY_PORT)),
        (b"192.168.1.1,AA:BB,not_a_number", ("192.168.1.1", DISCOVERY_PORT)),
        (b"192.168.1.2,CC:DD:EE:FF:00:11,9999999", ("192.168.1.2", DISCOVERY_PORT)),
    ]

    def _recvfrom(bufsize):
        if responses:
            return responses.pop(0)
        import socket
        raise socket.timeout

    mock_sock.recvfrom.side_effect = _recvfrom

    with patch("custom_components.solarman_deye.discovery.socket.socket", return_value=mock_sock):
        devices = scan_network(timeout=1.0)

    # Only the last response has a valid serial
    assert len(devices) == 1
    assert devices[0].serial == 9999999
