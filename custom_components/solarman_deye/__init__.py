"""Solarman Deye integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_RATED_CYCLES,
    CONF_CO2_FACTOR,
    CONF_MODE,
    CONF_PORT,
    CONF_SERIAL,
    CONF_SERVER_PORT,
    CONF_SLAVE_ID,
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_BATTERY_RATED_CYCLES,
    DEFAULT_CO2_FACTOR,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SERVER_PORT,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    MODE_PUSH,
)
from .coordinator import SolarmanDeyeCoordinator
from .server import SolarmanV5Server

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.UPDATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solarman Deye from a config entry."""
    serial = entry.data[CONF_SERIAL]
    mode = entry.data.get(CONF_MODE, "poll")
    is_push = mode == MODE_PUSH

    # Server port: options override > data > default
    server_port = entry.options.get(
        CONF_SERVER_PORT,
        entry.data.get(CONF_SERVER_PORT, DEFAULT_SERVER_PORT),
    )

    coordinator = SolarmanDeyeCoordinator(
        hass,
        host=entry.data.get(CONF_HOST, ""),
        serial=serial,
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        slave_id=entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID),
        scan_interval=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
        co2_factor=entry.options.get(CONF_CO2_FACTOR, DEFAULT_CO2_FACTOR),
        battery_capacity=entry.options.get(CONF_BATTERY_CAPACITY, DEFAULT_BATTERY_CAPACITY),
        battery_rated_cycles=entry.options.get(CONF_BATTERY_RATED_CYCLES, DEFAULT_BATTERY_RATED_CYCLES),
    )

    v5_server: SolarmanV5Server | None = None

    if is_push:
        # Push mode: start the passive V5 server, disable polling.
        v5_server = SolarmanV5Server(
            port=server_port,
            serial=serial,
            on_data=coordinator.receive_pushed_data,
        )
        try:
            await v5_server.start()
            coordinator.enable_push_mode()
            _LOGGER.info(
                "Push mode active — listening on port %s for serial %s",
                server_port, serial,
            )
        except OSError as err:
            _LOGGER.error(
                "Could not start V5 passive server on port %s: %s",
                server_port, err,
            )
            v5_server = None

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "server": v5_server,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator: SolarmanDeyeCoordinator = entry_data["coordinator"]
        server: SolarmanV5Server | None = entry_data.get("server")
        await coordinator.async_shutdown()
        if server is not None:
            await server.stop()
    return unload_ok
