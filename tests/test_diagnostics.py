"""Tests for the diagnostics platform."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.solarman_deye.diagnostics import _read_inverter_config
from custom_components.solarman_deye.coordinator import SolarmanDeyeCoordinator


class TestReadInverterConfig:
    """Verify that holding registers are read and decoded."""

    @pytest.fixture
    def coordinator(self, hass, mock_solarman):
        return SolarmanDeyeCoordinator(
            hass,
            host="192.168.86.69",
            serial=2504221369,
            port=8899,
            slave_id=1,
        )

    def test_reads_holding_registers(self, coordinator, mock_solarman):
        """Test that holding registers are read and labelled."""
        # Mock read_holding_registers to return known values
        def _read_holding(register_addr: int, quantity: int) -> list[int]:
            values = [0] * quantity
            sample = {
                100: 1,     # Work mode = Zero-export to load
                102: 1,     # Battery type = LiFePO4
                103: 100,   # Battery capacity 100 Ah
                104: 470,   # Empty voltage 47.0 V
                105: 545,   # Full voltage 54.5 V
                106: 10,    # Empty SOC 10%
                107: 5,     # Shutdown SOC 5%
                108: 30,    # Max charge current 30 A
                109: 30,    # Max discharge current 30 A
            }
            for reg, val in sample.items():
                idx = reg - register_addr
                if 0 <= idx < quantity:
                    values[idx] = val
            return values

        mock_solarman.read_holding_registers.side_effect = _read_holding

        config = _read_inverter_config(coordinator)

        assert config["Work mode"] == "Zero-export to load"
        assert config["Battery type"] == "LiFePO4"
        assert config["Battery capacity"] == "100 Ah"
        assert config["Battery empty voltage"] == "47.0 V"
        assert config["Max charge current"] == "30 A"
        assert config["Battery shutdown SOC"] == "5 %"
