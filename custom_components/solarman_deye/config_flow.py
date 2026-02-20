"""Config flow for Solarman Deye integration."""

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
    CONF_CO2_FACTOR,
    CONF_PORT,
    CONF_SERIAL,
    CONF_SLAVE_ID,
    DEFAULT_CO2_FACTOR,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_SERIAL): int,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
    }
)


def _test_connection(host: str, serial: int, port: int, slave_id: int) -> bool:
    """Try to read register 59 (running state) to validate the connection."""
    try:
        client = PySolarmanV5(host, serial, port=port, mb_slave_id=slave_id, socket_timeout=10)
        client.read_input_registers(register_addr=59, quantity=1)
        client.disconnect()
    except Exception:  # noqa: BLE001
        return False
    return True


class SolarmanDeyeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solarman Deye."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Prevent duplicate entries for the same serial number
            await self.async_set_unique_id(str(user_input[CONF_SERIAL]))
            self._abort_if_unique_id_configured()

            # Validate connection in executor
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
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

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
                }
            ),
        )
