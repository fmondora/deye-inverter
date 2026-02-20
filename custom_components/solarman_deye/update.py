"""Firmware update entity for Solarman Deye.

Checks a community-maintained manifest hosted on GitHub to determine
whether a newer firmware version is available for the inverter.
The integration **cannot** install firmware remotely — it only notifies
the user so they can update via the Solarman app or USB.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.update import UpdateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_SERIAL,
    DOMAIN,
    FIRMWARE_CHECK_INTERVAL,
    FIRMWARE_MANIFEST_URL,
)
from .coordinator import SolarmanDeyeCoordinator

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=FIRMWARE_CHECK_INTERVAL)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the firmware update entity."""
    coordinator: SolarmanDeyeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    serial = entry.data[CONF_SERIAL]
    async_add_entities([SolarmanDeyeUpdateEntity(hass, coordinator, serial)])


class SolarmanDeyeUpdateEntity(UpdateEntity):
    """Represents a firmware update check for a Deye inverter."""

    _attr_has_entity_name = True
    _attr_name = "Firmware Update"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: SolarmanDeyeCoordinator,
        serial: int,
    ) -> None:
        """Initialise the update entity."""
        self._hass = hass
        self._coordinator = coordinator
        self._serial = serial
        self._attr_unique_id = f"solarman_deye_{serial}_firmware_update"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(serial))},
        )
        self._latest_version: str | None = None
        self._release_summary: str | None = None
        self._release_url: str | None = None

    # ------------------------------------------------------------------
    # UpdateEntity properties
    # ------------------------------------------------------------------

    @property
    def installed_version(self) -> str | None:
        """Return the firmware version currently running on the inverter."""
        return self._coordinator.firmware_version

    @property
    def latest_version(self) -> str | None:
        """Return the latest available firmware version (from manifest)."""
        return self._latest_version

    @property
    def release_summary(self) -> str | None:
        """Return release notes for the latest version."""
        return self._release_summary

    @property
    def release_url(self) -> str | None:
        """Return a URL with more information about the update."""
        return self._release_url

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def async_update(self) -> None:
        """Fetch the firmware manifest from GitHub."""
        session = async_get_clientsession(self._hass)
        try:
            resp = await session.get(FIRMWARE_MANIFEST_URL, timeout=15)
            if resp.status != 200:
                _LOGGER.debug(
                    "Firmware manifest returned HTTP %s", resp.status
                )
                return
            manifest: dict[str, Any] = await resp.json(content_type=None)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Failed to fetch firmware manifest", exc_info=True)
            return

        self._latest_version = manifest.get("latest_version")
        self._release_summary = manifest.get("release_notes")
        self._release_url = manifest.get("release_url")
