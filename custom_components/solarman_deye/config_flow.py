"""Config flow for Solarman Deye integration.

Supports two setup paths:
  - **Push mode (recommended)**: the data logger pushes data to HA via
    a passive TCP server.  Configure Server B on the logger's admin page.
  - **Direct polling**: HA actively queries the logger on port 8899.
    May not work if the cloud connection monopolises the logger.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

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

_LOGGER = logging.getLogger(__name__)

PUSH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL): int,
        vol.Optional(CONF_SERVER_PORT, default=DEFAULT_SERVER_PORT): int,
    }
)

POLL_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_SERIAL): int,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
    }
)


class SolarmanDeyeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solarman Deye."""

    VERSION = 1

    # ------------------------------------------------------------------
    # Entry point — choose push or poll
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user choose between push mode and direct polling."""
        if user_input is not None:
            if user_input["setup_method"] == "push":
                return await self.async_step_push()
            return await self.async_step_poll()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("setup_method", default="push"): vol.In(
                        {
                            "push": "Push mode — data logger sends data to HA (recommended)",
                            "poll": "Direct polling — HA queries the data logger",
                        }
                    ),
                }
            ),
        )

    # ------------------------------------------------------------------
    # Push mode — passive server
    # ------------------------------------------------------------------

    async def async_step_push(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure push mode (passive TCP server)."""
        if user_input is not None:
            serial = user_input[CONF_SERIAL]
            server_port = user_input.get(CONF_SERVER_PORT, DEFAULT_SERVER_PORT)

            await self.async_set_unique_id(str(serial))
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Solarman Deye (push:{server_port})",
                data={
                    CONF_MODE: MODE_PUSH,
                    CONF_SERIAL: serial,
                    CONF_SERVER_PORT: server_port,
                    CONF_HOST: "",
                    CONF_PORT: DEFAULT_PORT,
                    CONF_SLAVE_ID: DEFAULT_SLAVE_ID,
                },
            )

        return self.async_show_form(
            step_id="push",
            data_schema=PUSH_DATA_SCHEMA,
        )

    # ------------------------------------------------------------------
    # Direct polling (legacy)
    # ------------------------------------------------------------------

    async def async_step_poll(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure direct polling mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(str(user_input[CONF_SERIAL]))
            self._abort_if_unique_id_configured()

            # Skip connection test — it often fails due to cloud contention.
            return self.async_create_entry(
                title=f"Solarman Deye ({user_input[CONF_HOST]})",
                data={
                    CONF_MODE: "poll",
                    **user_input,
                },
            )

        return self.async_show_form(
            step_id="poll",
            data_schema=POLL_DATA_SCHEMA,
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
                    vol.Optional(
                        CONF_SERVER_PORT,
                        default=self._config_entry.options.get(
                            CONF_SERVER_PORT, DEFAULT_SERVER_PORT
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1024, max=65535)),
                }
            ),
        )
