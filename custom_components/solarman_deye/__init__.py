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
    CONF_PORT,
    CONF_SERIAL,
    CONF_SERVER_PORT,
    CONF_SLAVE_ID,
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_BATTERY_RATED_CYCLES,
    DEFAULT_CO2_FACTOR,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SERVER_PORT,
    DOMAIN,
)
from .coordinator import SolarmanDeyeCoordinator
from .server import SolarmanV5Server

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.UPDATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solarman Deye from a config entry."""
    serial = entry.data[CONF_SERIAL]
    server_port = entry.options.get(CONF_SERVER_PORT, DEFAULT_SERVER_PORT)

    coordinator = SolarmanDeyeCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        serial=serial,
        port=entry.data[CONF_PORT],
        slave_id=entry.data[CONF_SLAVE_ID],
        scan_interval=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
        co2_factor=entry.options.get(CONF_CO2_FACTOR, DEFAULT_CO2_FACTOR),
        battery_capacity=entry.options.get(CONF_BATTERY_CAPACITY, DEFAULT_BATTERY_CAPACITY),
        battery_rated_cycles=entry.options.get(CONF_BATTERY_RATED_CYCLES, DEFAULT_BATTERY_RATED_CYCLES),
    )

    # Start the passive V5 server so the data logger can push data to us.
    v5_server = SolarmanV5Server(
        port=server_port,
        serial=serial,
        on_data=coordinator.receive_pushed_data,
    )
    try:
        await v5_server.start()
    except OSError as err:
        _LOGGER.warning(
            "Could not start V5 passive server on port %s: %s — "
            "push mode disabled, will use direct polling only",
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
