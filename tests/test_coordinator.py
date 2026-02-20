"""Tests for the SolarmanDeyeCoordinator data parsing logic."""

from __future__ import annotations

import pytest

from custom_components.solarman_deye.coordinator import SolarmanDeyeCoordinator


# ---------------------------------------------------------------------------
# Unit helpers — _signed / _signed32
# ---------------------------------------------------------------------------

class TestSignedConversion:
    """Verify 16-bit and 32-bit signed conversion helpers."""

    def test_positive_value_unchanged(self):
        assert SolarmanDeyeCoordinator._signed(100) == 100

    def test_max_positive(self):
        assert SolarmanDeyeCoordinator._signed(32767) == 32767

    def test_negative_value(self):
        # 0xFFFF → -1
        assert SolarmanDeyeCoordinator._signed(65535) == -1

    def test_boundary(self):
        # 0x8000 → -32768
        assert SolarmanDeyeCoordinator._signed(32768) == -32768

    def test_signed32_positive(self):
        assert SolarmanDeyeCoordinator._signed32(1000) == 1000

    def test_signed32_negative(self):
        assert SolarmanDeyeCoordinator._signed32(4294967295) == -1


# ---------------------------------------------------------------------------
# Parsing — _parse
# ---------------------------------------------------------------------------

class TestParse:
    """Verify that _parse converts raw registers to sensor values correctly."""

    @pytest.fixture
    def coordinator(self, hass, mock_solarman):
        """Create a coordinator instance (not started)."""
        return SolarmanDeyeCoordinator(
            hass,
            host="192.168.86.69",
            serial=2504221369,
            port=8899,
            slave_id=1,
        )

    @pytest.fixture
    def parsed(self, coordinator, mock_solarman):
        """Read mock registers and parse them."""
        regs = coordinator._read_registers()
        return coordinator._parse(regs)

    # --- PV ---
    def test_pv1_voltage(self, parsed):
        assert parsed["PV1 Voltage"] == 350.0

    def test_pv1_current(self, parsed):
        assert parsed["PV1 Current"] == 5.5

    def test_pv1_power(self, parsed):
        assert parsed["PV1 Power"] == 1925

    def test_pv2_power(self, parsed):
        assert parsed["PV2 Power"] == 1768

    # --- Battery ---
    def test_battery_soc(self, parsed):
        assert parsed["Battery SOC"] == 75

    def test_battery_voltage(self, parsed):
        assert parsed["Battery Voltage"] == 52.0

    def test_battery_temperature(self, parsed):
        # raw 1250 → (1250-1000)*0.1 = 25.0
        assert parsed["Battery Temperature"] == 25.0

    # --- Grid ---
    def test_grid_voltage(self, parsed):
        assert parsed["Grid Voltage"] == 230.0

    def test_grid_power(self, parsed):
        assert parsed["Grid Power"] == 1150

    # --- Load ---
    def test_load_power(self, parsed):
        assert parsed["Load Power"] == 850

    # --- Inverter ---
    def test_inverter_power(self, parsed):
        assert parsed["Inverter Power"] == 2000

    # --- Temperature ---
    def test_dc_transformer_temp(self, parsed):
        assert parsed["DC Transformer Temperature"] == 35.0

    def test_ambient_temp(self, parsed):
        assert parsed["Ambient Temperature"] == 25.0

    # --- Energy daily ---
    def test_daily_pv_energy(self, parsed):
        assert parsed["Daily PV Energy"] == 4.5

    def test_daily_load_energy(self, parsed):
        assert parsed["Daily Load Energy"] == 3.0

    # --- Energy total (32-bit) ---
    def test_total_pv_energy(self, parsed):
        # low=1000, high=0 → 1000 * 0.1 = 100.0
        assert parsed["Total PV Energy"] == 100.0

    # --- Status ---
    def test_running_state(self, parsed):
        assert parsed["Running State"] == "Normal"

    def test_grid_connected(self, parsed):
        assert parsed["Grid Connected Status"] == "Connected"

    # --- CO2 ---
    def test_daily_co2_saved(self, parsed):
        # 4.5 kWh * 0.256 = 1.152 → rounded 1.15
        assert parsed["Daily CO2 Saved"] == pytest.approx(1.15, abs=0.01)

    def test_total_co2_saved(self, parsed):
        # 100.0 kWh * 0.256 = 25.6
        assert parsed["Total CO2 Saved"] == pytest.approx(25.6, abs=0.1)

    # --- Battery cycles ---
    def test_battery_cycles(self, parsed):
        # Total Battery Discharge Energy: low=400, high=0 → 400 * 0.1 = 40.0 kWh
        # Default capacity = 5.12 kWh → 40.0 / 5.12 = 7.8125 → rounded 7.8
        assert parsed["Battery Cycles"] == pytest.approx(7.8, abs=0.1)

    def test_battery_health(self, parsed):
        # cycles ≈ 7.8, rated = 6000 → health = 100 * (1 - 7.8/6000) ≈ 99.9%
        assert parsed["Battery Health"] == pytest.approx(99.9, abs=0.1)


class TestBatteryCyclesCustomCapacity:
    """Verify battery cycle calculation with a custom capacity."""

    @pytest.fixture
    def coordinator(self, hass, mock_solarman):
        return SolarmanDeyeCoordinator(
            hass,
            host="192.168.86.69",
            serial=2504221369,
            port=8899,
            slave_id=1,
            battery_capacity=10.0,
            battery_rated_cycles=3000,
        )

    @pytest.fixture
    def parsed(self, coordinator, mock_solarman):
        regs = coordinator._read_registers()
        return coordinator._parse(regs)

    def test_cycles_with_larger_battery(self, parsed):
        # 40.0 kWh / 10.0 kWh = 4.0 cycles
        assert parsed["Battery Cycles"] == 4.0

    def test_health_with_lower_rated_cycles(self, parsed):
        # 4.0 / 3000 → health = 100 * (1 - 4/3000) ≈ 99.9
        assert parsed["Battery Health"] == pytest.approx(99.9, abs=0.1)
