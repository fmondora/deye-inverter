"""Network discovery for Solarman data loggers via UDP broadcast.

Solarman / LSW-3 data loggers listen on UDP port 48899 for a specific
broadcast message and reply with their IP, MAC address and serial number.
"""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

DISCOVERY_PORT = 48899
DISCOVERY_MESSAGE = b"WIFIKIT-214028-READ"
DISCOVERY_TIMEOUT = 3.0


@dataclass
class DiscoveredDevice:
    """A Solarman data logger found on the local network."""

    ip: str
    mac: str
    serial: int


def scan_network(timeout: float = DISCOVERY_TIMEOUT) -> list[DiscoveredDevice]:
    """Send a UDP broadcast and collect responses from Solarman loggers.

    Returns a list of discovered devices, which may be empty if no loggers
    are reachable or the broadcast is blocked by the network.
    """
    devices: list[DiscoveredDevice] = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    try:
        sock.sendto(DISCOVERY_MESSAGE, ("255.255.255.255", DISCOVERY_PORT))
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                text = data.decode("utf-8", errors="ignore").strip()
                parts = text.split(",")
                if len(parts) >= 3:
                    try:
                        serial = int(parts[2].strip())
                    except ValueError:
                        continue
                    devices.append(
                        DiscoveredDevice(
                            ip=parts[0].strip(),
                            mac=parts[1].strip(),
                            serial=serial,
                        )
                    )
            except socket.timeout:
                break
    except OSError as err:
        _LOGGER.warning("Discovery broadcast failed: %s", err)
    finally:
        sock.close()

    return devices
