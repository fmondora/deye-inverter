"""Shared fixtures for Solarman Deye tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.const import CONF_HOST

from custom_components.solarman_deye.const import (
    CONF_PORT,
    CONF_SERIAL,
    CONF_SLAVE_ID,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)

MOCK_HOST = "192.168.86.69"
MOCK_SERIAL = 3168688670
MOCK_CONFIG = {
    CONF_HOST: MOCK_HOST,
    CONF_SERIAL: MOCK_SERIAL,
    CONF_PORT: DEFAULT_PORT,
    CONF_SLAVE_ID: DEFAULT_SLAVE_ID,
}


def _build_register_block(start: int, count: int) -> list[int]:
    """Return a list of plausible raw register values for testing.

    Fills every position with 0 except known registers that get
    realistic sample values.
    """
    values = [0] * count

    sample: dict[int, int] = {
        # Status / energy daily
        59: 2,      # Running state = Normal
        60: 35,     # Daily active energy 3.5 kWh
        70: 22,     # Daily battery charge 2.2 kWh
        71: 18,     # Daily battery discharge 1.8 kWh
        72: 500,    # Total battery charge low
        73: 0,      # Total battery charge high
        74: 400,    # Total battery discharge low
        75: 0,
        76: 10,     # Daily grid import 1.0 kWh
        77: 5,      # Daily grid export 0.5 kWh
        78: 300,    # Total grid import low
        79: 5000,   # Grid frequency 50.00 Hz  (also total grid import high on block 1)
        81: 200,    # Total grid export low
        82: 0,
        84: 30,     # Daily load 3.0 kWh
        85: 600,    # Total load low
        86: 0,
        90: 350,    # DC transformer temp 35.0 °C (signed, positive)
        91: 380,    # Radiator temp 38.0 °C
        95: 250,    # Ambient temp 25.0 °C
        96: 1000,   # Total PV low
        97: 0,      # Total PV high → 100.0 kWh
        108: 45,    # Daily PV 4.5 kWh
        109: 3500,  # PV1 voltage 350.0 V
        110: 55,    # PV1 current 5.5 A
        111: 3400,  # PV2 voltage 340.0 V
        112: 52,    # PV2 current 5.2 A
        # Second block (offset 150)
        150: 2300,  # Grid voltage 230.0 V
        154: 2305,  # Inverter voltage 230.5 V
        160: 500,   # Grid current 5.00 A (signed positive)
        164: 480,   # Inverter current 4.80 A
        169: 1150,  # Grid power 1150 W (signed positive)
        172: 1100,  # Grid CT power
        175: 2000,  # Inverter power 2000 W
        178: 850,   # Load power
        182: 1250,  # Battery temp raw → (1250-1000)*0.1 = 25.0 °C
        183: 5200,  # Battery voltage 52.00 V
        184: 75,    # Battery SOC 75 %
        186: 1925,  # PV1 power 1925 W
        187: 1768,  # PV2 power 1768 W
        190: 500,   # Battery current 5.00 A (signed positive)
        191: 260,   # Battery power 260 W
        192: 5000,  # Load frequency 50.00 Hz
        193: 5000,  # Inverter frequency 50.00 Hz
        194: 1,     # Grid connected
    }

    for reg, val in sample.items():
        idx = reg - start
        if 0 <= idx < count:
            values[idx] = val

    return values


@pytest.fixture
def mock_solarman():
    """Patch PySolarmanV5 and return the mock client instance."""
    with patch(
        "custom_components.solarman_deye.coordinator.PySolarmanV5"
    ) as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client

        def _read_input(register_addr: int, quantity: int) -> list[int]:
            return _build_register_block(register_addr, quantity)

        client.read_input_registers.side_effect = _read_input
        yield client


@pytest.fixture
def mock_solarman_config_flow():
    """Patch PySolarmanV5 at the config_flow import path."""
    with patch(
        "custom_components.solarman_deye.config_flow.PySolarmanV5"
    ) as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        client.read_input_registers.return_value = [2]
        yield client
