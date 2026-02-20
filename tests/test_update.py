"""Tests for the firmware update entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession

from custom_components.solarman_deye.coordinator import SolarmanDeyeCoordinator
from custom_components.solarman_deye.update import SolarmanDeyeUpdateEntity

from .conftest import MOCK_SERIAL


class TestUpdateEntity:
    """Verify firmware update entity behaviour."""

    @pytest.fixture
    def coordinator(self, hass, mock_solarman):
        coord = SolarmanDeyeCoordinator(
            hass,
            host="192.168.86.69",
            serial=MOCK_SERIAL,
            port=8899,
            slave_id=1,
        )
        coord.firmware_version = "1.40.0"
        return coord

    @pytest.fixture
    def entity(self, hass, coordinator):
        return SolarmanDeyeUpdateEntity(hass, coordinator, MOCK_SERIAL)

    def test_installed_version(self, entity):
        assert entity.installed_version == "1.40.0"

    def test_latest_version_none_initially(self, entity):
        assert entity.latest_version is None

    @pytest.mark.asyncio
    async def test_async_update_fetches_manifest(self, hass, entity):
        """Test that async_update parses the firmware manifest."""
        manifest = {
            "latest_version": "1.47.0",
            "release_notes": "Bug fixes and performance improvements.",
            "release_url": "https://example.com/firmware",
        }

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=manifest)

        mock_session = AsyncMock(spec=ClientSession)
        mock_session.get = AsyncMock(return_value=mock_resp)

        with patch(
            "custom_components.solarman_deye.update.async_get_clientsession",
            return_value=mock_session,
        ):
            await entity.async_update()

        assert entity.latest_version == "1.47.0"
        assert entity.release_summary == "Bug fixes and performance improvements."
        assert entity.release_url == "https://example.com/firmware"

    @pytest.mark.asyncio
    async def test_async_update_handles_http_error(self, hass, entity):
        """Test that a non-200 response is handled gracefully."""
        mock_resp = AsyncMock()
        mock_resp.status = 404

        mock_session = AsyncMock(spec=ClientSession)
        mock_session.get = AsyncMock(return_value=mock_resp)

        with patch(
            "custom_components.solarman_deye.update.async_get_clientsession",
            return_value=mock_session,
        ):
            await entity.async_update()

        assert entity.latest_version is None

    @pytest.mark.asyncio
    async def test_async_update_handles_network_error(self, hass, entity):
        """Test that a network failure is handled gracefully."""
        mock_session = AsyncMock(spec=ClientSession)
        mock_session.get = AsyncMock(side_effect=Exception("timeout"))

        with patch(
            "custom_components.solarman_deye.update.async_get_clientsession",
            return_value=mock_session,
        ):
            await entity.async_update()

        assert entity.latest_version is None


class TestDeviceInfoRead:
    """Test that firmware version is read from device info registers."""

    @pytest.fixture
    def coordinator(self, hass, mock_solarman):
        return SolarmanDeyeCoordinator(
            hass,
            host="192.168.86.69",
            serial=MOCK_SERIAL,
            port=8899,
            slave_id=1,
        )

    def test_read_device_info(self, coordinator, mock_solarman):
        """Test firmware version parsed from registers 13-15."""
        # Register 0 = device type, registers 13-15 = version
        device_info_block = [0] * 16
        device_info_block[0] = 3       # Single-Phase Hybrid
        device_info_block[13] = 1      # major
        device_info_block[14] = 47     # minor
        device_info_block[15] = 0      # patch

        mock_solarman.read_input_registers.side_effect = (
            lambda register_addr, quantity: (
                device_info_block
                if register_addr == 0
                else [0] * quantity
            )
        )

        coordinator._read_device_info()

        assert coordinator.device_type == "Single-Phase Hybrid"
        assert coordinator.firmware_version == "1.47.0"
        assert coordinator._device_info_read is True

    def test_read_device_info_failure_is_silent(self, coordinator, mock_solarman):
        """Test that a failure to read device info is non-fatal."""
        mock_solarman.read_input_registers.side_effect = Exception("timeout")

        coordinator._read_device_info()

        assert coordinator._device_info_read is True
        assert coordinator.firmware_version is None
