"""Tests for the Solarman Deye config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.solarman_deye.const import (
    CONF_PORT,
    CONF_SERIAL,
    CONF_SLAVE_ID,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)
from custom_components.solarman_deye.discovery import DiscoveredDevice

from .conftest import MOCK_CONFIG, MOCK_HOST, MOCK_SERIAL


# ------------------------------------------------------------------
# Manual flow
# ------------------------------------------------------------------


async def test_manual_flow_success(hass: HomeAssistant, mock_solarman_config_flow):
    """Test a successful manual config flow."""
    # Step 1 — choose setup method
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Step 2 — pick manual
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"setup_method": "manual"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"

    # Step 3 — enter data
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Solarman Deye ({MOCK_HOST})"
    assert result["data"] == MOCK_CONFIG


async def test_manual_flow_connection_failure(hass: HomeAssistant):
    """Test that a connection failure shows an error in manual mode."""
    with patch(
        "custom_components.solarman_deye.config_flow.PySolarmanV5",
        side_effect=Exception("timeout"),
    ), patch(
        "custom_components.solarman_deye.config_flow.socket.create_connection",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"setup_method": "manual"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_CONFIG
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_serial_aborts(hass: HomeAssistant, mock_solarman_config_flow):
    """Test that adding the same serial number twice aborts."""
    # First entry — manual
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"setup_method": "manual"}
    )
    await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    # Second entry — same serial
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"setup_method": "manual"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ------------------------------------------------------------------
# Discovery flow
# ------------------------------------------------------------------


async def test_discover_flow_success(hass: HomeAssistant, mock_solarman_config_flow):
    """Test a successful discovery flow."""
    mock_device = DiscoveredDevice(ip=MOCK_HOST, mac="AA:BB:CC:DD:EE:FF", serial=MOCK_SERIAL)

    with patch(
        "custom_components.solarman_deye.config_flow.scan_network",
        return_value=[mock_device],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"setup_method": "discover"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "discover"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"device": "0"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_SERIAL] == MOCK_SERIAL
        assert result["data"][CONF_HOST] == MOCK_HOST


async def test_discover_flow_no_devices(hass: HomeAssistant):
    """Test that discovery with no results aborts gracefully."""
    with patch(
        "custom_components.solarman_deye.config_flow.scan_network",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"setup_method": "discover"}
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "no_devices_found"
