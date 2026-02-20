"""Sensor platform for Solarman Deye integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BATTERY_CYCLE_SENSORS,
    CO2_SENSORS,
    CONF_SERIAL,
    DOMAIN,
    REGISTERS_BATTERY,
    REGISTERS_ENERGY_DAILY,
    REGISTERS_ENERGY_TOTAL,
    REGISTERS_GRID,
    REGISTERS_INVERTER,
    REGISTERS_LOAD,
    REGISTERS_PV,
    REGISTERS_STATUS,
    REGISTERS_TEMPERATURE,
)
from .coordinator import SolarmanDeyeCoordinator
from .server import SolarmanV5Server


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solarman Deye sensors from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SolarmanDeyeCoordinator = entry_data["coordinator"]
    server: SolarmanV5Server | None = entry_data.get("server")
    serial = entry.data[CONF_SERIAL]

    entities: list[SensorEntity] = []

    # --- 16-bit register sensors ---
    for group in (
        REGISTERS_PV,
        REGISTERS_BATTERY,
        REGISTERS_GRID,
        REGISTERS_LOAD,
        REGISTERS_INVERTER,
        REGISTERS_TEMPERATURE,
        REGISTERS_ENERGY_DAILY,
        REGISTERS_STATUS,
    ):
        for entry_def in group:
            # Skip placeholder rows
            if entry_def[1] is None:
                continue
            _, name, unit, dev_class, state_class, _scale, precision, _signed = entry_def
            entities.append(
                SolarmanDeyeSensor(
                    coordinator=coordinator,
                    serial=serial,
                    name=name,
                    unit=unit,
                    device_class=dev_class,
                    state_class=state_class,
                    precision=precision,
                )
            )

    # --- 32-bit total energy sensors ---
    for entry_def in REGISTERS_ENERGY_TOTAL:
        _, _, name, unit, dev_class, state_class, _scale, precision = entry_def
        entities.append(
            SolarmanDeyeSensor(
                coordinator=coordinator,
                serial=serial,
                name=name,
                unit=unit,
                device_class=dev_class,
                state_class=state_class,
                precision=precision,
            )
        )

    # --- CO2 and battery cycle sensors ---
    for name, unit, state_class, precision, icon in CO2_SENSORS + BATTERY_CYCLE_SENSORS:
        entities.append(
            SolarmanDeyeSensor(
                coordinator=coordinator,
                serial=serial,
                name=name,
                unit=unit,
                device_class=None,
                state_class=state_class,
                precision=precision,
                icon=icon,
            )
        )

    # --- Server diagnostic sensors ---
    if server is not None:
        entities.append(
            ServerStatusSensor(server, serial, "Server Status", "mdi:server-network")
        )
        entities.append(
            ServerStatusSensor(server, serial, "Frames Received", "mdi:counter")
        )
        entities.append(
            ServerStatusSensor(server, serial, "Last Data Received", "mdi:clock-outline")
        )

    async_add_entities(entities)


class ServerStatusSensor(SensorEntity):
    """Diagnostic sensor showing V5 server status."""

    _attr_has_entity_name = True

    def __init__(
        self,
        server: SolarmanV5Server,
        serial: int,
        name: str,
        icon: str,
    ) -> None:
        """Initialise the server status sensor."""
        self._server = server
        self._sensor_name = name
        self._attr_unique_id = f"solarman_deye_{serial}_{name.lower().replace(' ', '_')}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(serial))},
            name=f"Solarman Deye {serial}",
            manufacturer="Deye",
        )

    @property
    def native_value(self) -> str | int | None:
        """Return the current value."""
        if self._sensor_name == "Server Status":
            return self._server.status
        if self._sensor_name == "Frames Received":
            return self._server.frames_received
        if self._sensor_name == "Last Data Received":
            return self._server.last_frame_time
        return None

    @property
    def available(self) -> bool:
        """Server sensors are always available."""
        return True


class SolarmanDeyeSensor(CoordinatorEntity[SolarmanDeyeCoordinator], SensorEntity):
    """Representation of a Solarman Deye sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SolarmanDeyeCoordinator,
        serial: int,
        name: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        precision: int,
        icon: str | None = None,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._sensor_name = name
        self._attr_unique_id = f"solarman_deye_{serial}_{name.lower().replace(' ', '_')}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_suggested_display_precision = precision
        if icon is not None:
            self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(serial))},
            name=f"Solarman Deye {serial}",
            manufacturer="Deye",
            model=coordinator.device_type,
            sw_version=coordinator.firmware_version,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_native_value()
        self.async_write_ha_state()

    def _update_native_value(self) -> None:
        if self.coordinator.data is None:
            self._attr_native_value = None
            return
        self._attr_native_value = self.coordinator.data.get(self._sensor_name)

    @property
    def available(self) -> bool:
        """Return True if the sensor has a value."""
        return super().available and self.coordinator.data is not None
