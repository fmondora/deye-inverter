"""Config flow for Solarman Deye integration.

Supports two setup paths:
  - **Auto-discover**: scans the local network via UDP broadcast on port 48899
    and lets the user pick a detected data logger.
  - **Manual**: the user enters IP, serial number, port and slave ID by hand.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from pysolarmanv5 import PySolarmanV5

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_RATED_CYCLES,
    CONF_CO2_FACTOR,
    CONF_PORT,
    CONF_SERIAL,
    CONF_SLAVE_ID,
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_BATTERY_RATED_CYCLES,
    DEFAULT_CO2_FACTOR,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)
from .discovery import DiscoveredDevice, scan_network

_LOGGER = logging.getLogger(__name__)

MANUAL_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_SERIAL): int,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
    }
)


def _test_connection(host: str, serial: int, port: int, slave_id: int) -> bool:
    """Try to read register 59 (running state) to validate the connection."""
    client = None
    try:
        _LOGGER.debug(
            "Testing connection to %s:%s (serial=%s, slave=%s)",
            host, port, serial, slave_id,
        )
        client = PySolarmanV5(
            host, serial, port=port, mb_slave_id=slave_id,
            auto_reconnect=False, socket_timeout=15,
        )
        result = client.read_input_registers(register_addr=59, quantity=1)
        _LOGGER.debug("Connection test OK — register 59 = %s", result)
        return True
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Connection test failed: %s: %s", type(err).__name__, err)
        return False
    finally:
        if client is not None:
            try:
                client.disconnect()
            except Exception:  # noqa: BLE001
                pass


class SolarmanDeyeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solarman Deye."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise flow state."""
        self._discovered_devices: list[DiscoveredDevice] = []

    # ------------------------------------------------------------------
    # Entry point — choose discover or manual
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user choose between auto-discovery and manual entry."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["discover", "manual"],
        )

    # ------------------------------------------------------------------
    # Auto-discovery via UDP broadcast
    # ------------------------------------------------------------------

    async def async_step_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Scan the network and let the user pick a device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            idx = int(user_input["device"])
            device = self._discovered_devices[idx]

            await self.async_set_unique_id(str(device.serial))
            self._abort_if_unique_id_configured()

            ok = await self.hass.async_add_executor_job(
                _test_connection, device.ip, device.serial, DEFAULT_PORT, DEFAULT_SLAVE_ID,
            )
            if ok:
                return self.async_create_entry(
                    title=f"Solarman Deye ({device.ip})",
                    data={
                        CONF_HOST: device.ip,
                        CONF_SERIAL: device.serial,
                        CONF_PORT: DEFAULT_PORT,
                        CONF_SLAVE_ID: DEFAULT_SLAVE_ID,
                    },
                )
            errors["base"] = "cannot_connect"
        else:
            # First visit — run the scan
            self._discovered_devices = await self.hass.async_add_executor_job(
                scan_network
            )

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        device_map = {
            str(i): f"{d.ip}  —  SN {d.serial}  ({d.mac})"
            for i, d in enumerate(self._discovered_devices)
        }

        return self.async_show_form(
            step_id="discover",
            data_schema=vol.Schema(
                {vol.Required("device"): vol.In(device_map)}
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Manual entry
    # ------------------------------------------------------------------

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual configuration entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(str(user_input[CONF_SERIAL]))
            self._abort_if_unique_id_configured()

            ok = await self.hass.async_add_executor_job(
                _test_connection,
                user_input[CONF_HOST],
                user_input[CONF_SERIAL],
                user_input[CONF_PORT],
                user_input[CONF_SLAVE_ID],
            )
            if ok:
                return self.async_create_entry(
                    title=f"Solarman Deye ({user_input[CONF_HOST]})",
                    data=user_input,
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual",
            data_schema=MANUAL_DATA_SCHEMA,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Options flow
    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return SolarmanDeyeOptionsFlow(config_entry)


class SolarmanDeyeOptionsFlow(OptionsFlow):
    """Handle options for Solarman Deye."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=self._config_entry.options.get(
                            "scan_interval", DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                    vol.Optional(
                        CONF_CO2_FACTOR,
                        default=self._config_entry.options.get(
                            CONF_CO2_FACTOR, DEFAULT_CO2_FACTOR
                        ),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.01, max=2.0)),
                    vol.Optional(
                        CONF_BATTERY_CAPACITY,
                        default=self._config_entry.options.get(
                            CONF_BATTERY_CAPACITY, DEFAULT_BATTERY_CAPACITY
                        ),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=100.0)),
                    vol.Optional(
                        CONF_BATTERY_RATED_CYCLES,
                        default=self._config_entry.options.get(
                            CONF_BATTERY_RATED_CYCLES, DEFAULT_BATTERY_RATED_CYCLES
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=100, max=20000)),
                }
            ),
        )
