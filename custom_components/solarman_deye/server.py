"""Passive TCP server that receives data pushes from the Solarman data logger.

The data logger can be configured (via its admin console, Server B) to
forward inverter data to this server.  The server parses incoming
Solarman V5 frames, extracts the embedded Modbus register values, and
stores them for the coordinator to consume.
"""

from __future__ import annotations

import asyncio
import logging
import struct
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)

# V5 frame markers
V5_START = 0xA5
V5_END = 0x15

# Frame types sent by the data logger
FRAME_HEARTBEAT = 0x47  # Keep-alive / registration
FRAME_DATA = 0x42       # Data report with register values
FRAME_HELLO = 0x41      # Handshake

# Minimum V5 frame size: start(1) + length(2) + control(2) + seq(2)
#   + serial(4) + type(1) + checksum(1) + end(1) = 14
MIN_FRAME_SIZE = 14

# Offset of the payload inside a V5 data frame (after the fixed header).
# start(1) + length(2) + control(2) + seq(2) + serial(4) + type(1) = 12
HEADER_SIZE = 12


def _parse_v5_frames(data: bytes) -> list[tuple[int, int, bytes]]:
    """Extract V5 frames from a raw byte stream.

    Returns a list of (frame_type, logger_serial, payload) tuples.
    """
    frames: list[tuple[int, int, bytes]] = []
    pos = 0
    while pos < len(data):
        # Find start byte
        start = data.find(V5_START, pos)
        if start == -1 or start + MIN_FRAME_SIZE > len(data):
            break

        # Read length field (2 bytes LE at offset 1)
        length = struct.unpack_from("<H", data, start + 1)[0]
        # Total frame size = start(1) + length_field(2) + length + checksum(1) + end(1)
        frame_size = 1 + 2 + length + 1 + 1
        if start + frame_size > len(data):
            break

        frame = data[start : start + frame_size]

        # Verify end byte
        if frame[-1] != V5_END:
            pos = start + 1
            continue

        # Verify checksum (sum of all bytes except last two, mod 256)
        expected_cs = sum(frame[:-2]) & 0xFF
        if frame[-2] != expected_cs:
            _LOGGER.debug("V5 checksum mismatch — skipping frame")
            pos = start + 1
            continue

        # Extract header fields
        serial = struct.unpack_from("<I", frame, 7)[0]
        frame_type = frame[11]
        payload = frame[HEADER_SIZE:-2]  # between header and checksum+end

        frames.append((frame_type, serial, payload))
        pos = start + frame_size

    return frames


def _extract_registers_from_payload(payload: bytes) -> dict[int, int]:
    """Try to extract Modbus register values from a V5 data-push payload.

    The payload of a data-report frame (type 0x42) typically contains:
      status(1) + sensor_type(2) + delivery_time(4) + power_on_time(4)
      + offset_time(4) + modbus_response(...)

    The modbus_response is: slave(1) + function(1) + byte_count(1) + data(N)
    For function 0x04 (read input registers), data contains N/2 16-bit values.
    """
    regs: dict[int, int] = {}
    if len(payload) < 16:
        return regs

    # Skip status(1) + sensor_type(2) + times(12) = 15 bytes
    modbus = payload[15:]
    if len(modbus) < 5:
        return regs

    slave_id = modbus[0]
    function = modbus[1]
    byte_count = modbus[2]

    if function not in (0x03, 0x04):
        # Not a standard read holding/input registers response
        _LOGGER.debug(
            "Unexpected Modbus function 0x%02x in data push", function
        )
        # Try to parse as raw register dump (some loggers send raw data)
        return _try_raw_register_parse(modbus)

    data_bytes = modbus[3 : 3 + byte_count]
    if len(data_bytes) < byte_count:
        return regs

    # We don't know the starting register from the response alone.
    # But the Deye logger typically reads starting at register 0x003B (59).
    # If byte_count matches our expected ranges, we can map them.
    num_regs = byte_count // 2
    values = struct.unpack(f">{num_regs}H", data_bytes[:num_regs * 2])

    # Heuristic: determine the start register based on the byte count.
    # Common Deye push sizes:
    #   55 registers (110 bytes) starting at reg 59
    #   45 registers (90 bytes) starting at reg 150
    #   100 registers (200 bytes) starting at reg 59
    #   Single block of all registers
    if num_regs >= 90:
        # Large block starting at 59 covering both ranges
        start_reg = 59
    elif num_regs >= 50:
        start_reg = 59
    elif num_regs >= 40:
        start_reg = 150
    else:
        # Small block — assume starting at 59
        start_reg = 59

    for i, val in enumerate(values):
        regs[start_reg + i] = val

    return regs


def _try_raw_register_parse(data: bytes) -> dict[int, int]:
    """Attempt to parse data as a raw register value dump.

    Some data loggers don't use standard Modbus framing in their push
    messages.  Instead they send raw 16-bit register values starting
    from register 0.
    """
    regs: dict[int, int] = {}
    if len(data) < 4:
        return regs

    num_regs = len(data) // 2
    values = struct.unpack(f">{num_regs}H", data[:num_regs * 2])
    for i, val in enumerate(values):
        regs[i] = val

    return regs


def _build_v5_ack(frame_type: int, serial: int, sequence: int = 0) -> bytes:
    """Build a minimal V5 acknowledgement frame."""
    payload = bytearray()
    payload += bytes([V5_START])
    payload += struct.pack("<H", 11)  # length: control(2)+seq(2)+serial(4)+type(1)+status(1)+padding(1)
    payload += struct.pack("<H", 0x1010)  # control code (server response)
    payload += struct.pack("<H", sequence)
    payload += struct.pack("<I", serial)
    payload += bytes([frame_type])
    payload += bytes([0x01])  # status: OK
    payload += bytes([0x00])  # padding
    cs = sum(payload) & 0xFF
    payload += bytes([cs])
    payload += bytes([V5_END])
    return bytes(payload)


class SolarmanV5Server:
    """Async TCP server that receives data pushes from a Solarman logger."""

    def __init__(
        self,
        port: int,
        serial: int,
        on_data: Callable[[dict[int, int]], None],
    ) -> None:
        """Initialise the server.

        Args:
            port: TCP port to listen on.
            serial: Expected logger serial number.
            on_data: Callback invoked with {register: value} when new data arrives.
        """
        self._port = port
        self._serial = serial
        self._on_data = on_data
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        """Start listening for connections."""
        self._server = await asyncio.start_server(
            self._handle_client, "0.0.0.0", self._port
        )
        _LOGGER.info(
            "Solarman V5 passive server listening on port %s", self._port
        )

    async def stop(self) -> None:
        """Stop the server."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            _LOGGER.info("Solarman V5 passive server stopped")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a single TCP connection from the data logger."""
        peer = writer.get_extra_info("peername")
        _LOGGER.debug("Data logger connected from %s", peer)

        try:
            while True:
                data = await asyncio.wait_for(reader.read(4096), timeout=300)
                if not data:
                    break

                frames = _parse_v5_frames(data)
                for frame_type, serial, payload in frames:
                    _LOGGER.debug(
                        "V5 frame: type=0x%02x serial=%s payload=%d bytes",
                        frame_type, serial, len(payload),
                    )

                    # Send ACK to keep the logger happy
                    try:
                        ack = _build_v5_ack(frame_type, serial)
                        writer.write(ack)
                        await writer.drain()
                    except Exception:  # noqa: BLE001
                        pass

                    # Only process data from our logger
                    if serial != self._serial:
                        _LOGGER.debug(
                            "Ignoring frame from unknown serial %s", serial
                        )
                        continue

                    if frame_type == FRAME_DATA:
                        regs = _extract_registers_from_payload(payload)
                        if regs:
                            _LOGGER.debug(
                                "Received %d register values via push",
                                len(regs),
                            )
                            self._on_data(regs)
                        else:
                            _LOGGER.debug(
                                "Data frame with no parseable registers "
                                "(payload hex: %s)",
                                payload.hex(),
                            )
                    elif frame_type in (FRAME_HEARTBEAT, FRAME_HELLO):
                        _LOGGER.debug("Heartbeat/hello from logger")
                    else:
                        _LOGGER.debug(
                            "Unknown frame type 0x%02x (payload hex: %s)",
                            frame_type, payload.hex(),
                        )
        except asyncio.TimeoutError:
            _LOGGER.debug("Logger connection timed out")
        except ConnectionResetError:
            _LOGGER.debug("Logger disconnected")
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Logger connection error", exc_info=True)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
            _LOGGER.debug("Logger connection closed")
