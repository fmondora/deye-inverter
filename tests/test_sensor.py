"""Tests for Solarman Deye sensor entity creation."""

from __future__ import annotations

import pytest

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)

from custom_components.solarman_deye.const import DOMAIN
from custom_components.solarman_deye.sensor import SolarmanDeyeSensor
from custom_components.solarman_deye.coordinator import SolarmanDeyeCoordinator

from .conftest import MOCK_SERIAL


class TestSolarmanDeyeSensor:
    """Test sensor attribute setup."""

    @pytest.fixture
    def coordinator(self, hass, mock_solarman):
        return SolarmanDeyeCoordinator(
            hass,
            host="192.168.86.69",
            serial=MOCK_SERIAL,
            port=8899,
            slave_id=1,
        )

    def test_unique_id(self, coordinator):
        sensor = SolarmanDeyeSensor(
            coordinator=coordinator,
            serial=MOCK_SERIAL,
            name="PV1 Voltage",
            unit=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            precision=1,
        )
        assert sensor.unique_id == f"solarman_deye_{MOCK_SERIAL}_pv1_voltage"

    def test_device_info(self, coordinator):
        sensor = SolarmanDeyeSensor(
            coordinator=coordinator,
            serial=MOCK_SERIAL,
            name="Grid Power",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            precision=0,
        )
        assert sensor.device_info["manufacturer"] == "Deye"
        assert (DOMAIN, str(MOCK_SERIAL)) in sensor.device_info["identifiers"]

    def test_icon_set_when_provided(self, coordinator):
        sensor = SolarmanDeyeSensor(
            coordinator=coordinator,
            serial=MOCK_SERIAL,
            name="Daily CO2 Saved",
            unit="kg",
            device_class=None,
            state_class=SensorStateClass.TOTAL_INCREASING,
            precision=2,
            icon="mdi:molecule-co2",
        )
        assert sensor.icon == "mdi:molecule-co2"

    def test_no_icon_by_default(self, coordinator):
        sensor = SolarmanDeyeSensor(
            coordinator=coordinator,
            serial=MOCK_SERIAL,
            name="PV1 Power",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            precision=0,
        )
        assert not hasattr(sensor, "_attr_icon")

    def test_energy_sensor_state_class(self, coordinator):
        sensor = SolarmanDeyeSensor(
            coordinator=coordinator,
            serial=MOCK_SERIAL,
            name="Total PV Energy",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            precision=1,
        )
        assert sensor.state_class is SensorStateClass.TOTAL_INCREASING
        assert sensor.device_class is SensorDeviceClass.ENERGY

    def test_native_value_none_when_no_data(self, coordinator):
        sensor = SolarmanDeyeSensor(
            coordinator=coordinator,
            serial=MOCK_SERIAL,
            name="PV1 Power",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            precision=0,
        )
        sensor._update_native_value()
        assert sensor.native_value is None

    def test_native_value_from_coordinator_data(self, coordinator):
        sensor = SolarmanDeyeSensor(
            coordinator=coordinator,
            serial=MOCK_SERIAL,
            name="PV1 Power",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            precision=0,
        )
        coordinator.data = {"PV1 Power": 1925}
        sensor._update_native_value()
        assert sensor.native_value == 1925
