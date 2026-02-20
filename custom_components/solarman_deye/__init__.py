"""Solarman Deye integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CO2_FACTOR, CONF_PORT, CONF_SERIAL, CONF_SLAVE_ID, DEFAULT_CO2_FACTOR, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import SolarmanDeyeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solarman Deye from a config entry."""
    coordinator = SolarmanDeyeCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        serial=entry.data[CONF_SERIAL],
        port=entry.data[CONF_PORT],
        slave_id=entry.data[CONF_SLAVE_ID],
        scan_interval=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
        co2_factor=entry.options.get(CONF_CO2_FACTOR, DEFAULT_CO2_FACTOR),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: SolarmanDeyeCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok
