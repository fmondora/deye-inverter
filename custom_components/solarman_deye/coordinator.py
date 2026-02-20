"""DataUpdateCoordinator for Solarman Deye."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from pysolarmanv5 import PySolarmanV5

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_BATTERY_RATED_CYCLES,
    DEFAULT_CO2_FACTOR,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_INFO_BLOCK,
    DEVICE_TYPES,
    DOMAIN,
    READ_BLOCKS,
    REGISTERS_BATTERY,
    REGISTERS_ENERGY_DAILY,
    REGISTERS_ENERGY_TOTAL,
    REGISTERS_GRID,
    REGISTERS_INVERTER,
    REGISTERS_LOAD,
    REGISTERS_PV,
    REGISTERS_STATUS,
    REGISTERS_TEMPERATURE,
    RUNNING_STATES,
)

_LOGGER = logging.getLogger(__name__)


class SolarmanDeyeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls the Solarman data logger."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        serial: int,
        port: int,
        slave_id: int,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        co2_factor: float = DEFAULT_CO2_FACTOR,
        battery_capacity: float = DEFAULT_BATTERY_CAPACITY,
        battery_rated_cycles: int = DEFAULT_BATTERY_RATED_CYCLES,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._host = host
        self._serial = serial
        self._port = port
        self._slave_id = slave_id
        self._co2_factor = co2_factor
        self._battery_capacity = battery_capacity
        self._battery_rated_cycles = battery_rated_cycles
        self._client: PySolarmanV5 | None = None
        # Device info — populated once at first successful read.
        self.device_type: str = "Hybrid Inverter"
        self.firmware_version: str | None = None
        self._device_info_read = False
        # Registers received via the passive V5 server (push mode).
        self._pushed_registers: dict[int, int] | None = None

    def receive_pushed_data(self, regs: dict[int, int]) -> None:
        """Called by the V5 server when new register data is pushed."""
        self._pushed_registers = regs
        _LOGGER.debug("Stored %d pushed registers for next update", len(regs))

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _new_client(self) -> PySolarmanV5:
        """Create a fresh PySolarmanV5 client (blocking)."""
        return PySolarmanV5(
            self._host,
            self._serial,
            port=self._port,
            mb_slave_id=self._slave_id,
            auto_reconnect=False,
            socket_timeout=10,
        )

    def _disconnect(self) -> None:
        """Close the current client connection if any."""
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self._client = None

    # ------------------------------------------------------------------
    # Data reading (runs in executor)
    # ------------------------------------------------------------------

    def _read_registers(self) -> dict[int, int]:
        """Connect, read all register blocks, disconnect.

        Opens a fresh connection each poll cycle so the data logger's
        single TCP slot is free between reads.  Retries up to 3 times
        with a short pause to work around data-logger cloud contention.
        """
        last_err: Exception | None = None
        for attempt in range(1, 4):
            self._disconnect()
            try:
                client = self._new_client()
                self._client = client
                regs: dict[int, int] = {}
                for start, count in READ_BLOCKS:
                    values = client.read_input_registers(
                        register_addr=start, quantity=count,
                    )
                    for i, val in enumerate(values):
                        regs[start + i] = val
                return regs
            except Exception as err:  # noqa: BLE001
                last_err = err
                _LOGGER.debug(
                    "Read attempt %s/3 failed: %s — retrying in 2s",
                    attempt, err,
                )
                self._disconnect()
                if attempt < 3:
                    time.sleep(2)

        raise last_err  # type: ignore[misc]

    @staticmethod
    def _signed(value: int) -> int:
        """Convert unsigned 16-bit to signed."""
        return value - 65536 if value >= 32768 else value

    @staticmethod
    def _signed32(value: int) -> int:
        """Convert unsigned 32-bit to signed."""
        return value - 4294967296 if value >= 2147483648 else value

    def _parse(self, regs: dict[int, int]) -> dict[str, Any]:
        """Parse raw registers into sensor values."""
        data: dict[str, Any] = {}

        # --- 16-bit single-register sensors ---
        for group in (
            REGISTERS_PV,
            REGISTERS_GRID,
            REGISTERS_LOAD,
            REGISTERS_INVERTER,
            REGISTERS_TEMPERATURE,
            REGISTERS_ENERGY_DAILY,
            REGISTERS_STATUS,
        ):
            for reg, name, *_, scale, precision, signed in group:
                if name is None:
                    continue
                raw = regs.get(reg)
                if raw is None:
                    continue
                val = self._signed(raw) if signed else raw
                data[name] = round(val * scale, precision)

        # --- Battery (with offset temperature) ---
        for reg, name, *_, scale, precision, signed in REGISTERS_BATTERY:
            if name is None:
                continue
            raw = regs.get(reg)
            if raw is None:
                continue
            if name == "Battery Temperature":
                # Deye stores battery temp with +1000 offset (×0.1 °C)
                data[name] = round((raw - 1000) * 0.1, 1)
            else:
                val = self._signed(raw) if signed else raw
                data[name] = round(val * scale, precision)

        # --- 32-bit total energy ---
        for low, high, name, *_, scale, precision in REGISTERS_ENERGY_TOTAL:
            low_val = regs.get(low)
            high_val = regs.get(high)
            if low_val is None or high_val is None:
                continue
            combined = (high_val << 16) | low_val
            data[name] = round(combined * scale, precision)

        # --- Translate running state to text ---
        if "Running State" in data:
            raw_state = int(data["Running State"])
            data["Running State"] = RUNNING_STATES.get(raw_state, f"Unknown ({raw_state})")

        # --- Grid connected as boolean-like text ---
        if "Grid Connected Status" in data:
            data["Grid Connected Status"] = (
                "Connected" if int(data["Grid Connected Status"]) == 1 else "Disconnected"
            )

        # --- CO2 savings ---
        co2 = self._co2_factor
        daily_pv = data.get("Daily PV Energy")
        if daily_pv is not None:
            data["Daily CO2 Saved"] = round(daily_pv * co2, 2)
        total_pv = data.get("Total PV Energy")
        if total_pv is not None:
            data["Total CO2 Saved"] = round(total_pv * co2, 1)

        # --- Battery cycle tracking ---
        total_discharge = data.get("Total Battery Discharge Energy")
        if total_discharge is not None and self._battery_capacity > 0:
            cycles = total_discharge / self._battery_capacity
            data["Battery Cycles"] = round(cycles, 1)
            # Health: 100% at 0 cycles, 0% at rated cycle life
            health = max(0.0, 100.0 * (1 - cycles / self._battery_rated_cycles))
            data["Battery Health"] = round(health, 1)

        return data

    # ------------------------------------------------------------------
    # Device info (read once)
    # ------------------------------------------------------------------

    def _read_device_info(self) -> None:
        """Read input registers 0-15 for device identification (blocking).

        Called once after the first successful connection.  Failures are
        silently ignored — the data is nice-to-have, not critical.
        """
        if self._device_info_read:
            return
        self._disconnect()
        try:
            client = self._new_client()
            start, count = DEVICE_INFO_BLOCK
            values = client.read_input_registers(register_addr=start, quantity=count)
            # Register 0: device type code
            dev_code = values[0]
            self.device_type = DEVICE_TYPES.get(dev_code, f"Type {dev_code}")
            # Firmware version: registers 13-15 often hold major.minor.patch
            # encoded as plain integers (e.g. 1, 47, 0 → "1.47.0").
            if len(values) > 15:
                major, minor, patch = values[13], values[14], values[15]
                self.firmware_version = f"{major}.{minor}.{patch}"
            client.disconnect()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not read device info registers — skipping")
        self._device_info_read = True

    # ------------------------------------------------------------------
    # Coordinator interface
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the inverter.

        Prefers data received via the passive V5 server (push mode).
        Falls back to direct polling if no pushed data is available.
        """
        # Use pushed data if the V5 server has received any.
        if self._pushed_registers is not None:
            regs = self._pushed_registers
            self._pushed_registers = None
            _LOGGER.debug("Using %d registers from push server", len(regs))
            return self._parse(regs)

        # Fall back to direct polling.
        try:
            regs = await self.hass.async_add_executor_job(self._read_registers)
        except Exception as err:
            self._client = None
            # If we have never had a successful read, return empty data so
            # that the first refresh succeeds and entities are created.
            # They will show 'Unknown' until the inverter wakes up.
            if self.data is None:
                _LOGGER.warning(
                    "Inverter not responding (probably standby / cloud busy) — "
                    "sensors will update when data arrives: %s", err,
                )
                return {}
            raise UpdateFailed(f"Error communicating with inverter: {err}") from err

        # Read device info once after the first successful poll.
        if not self._device_info_read:
            await self.hass.async_add_executor_job(self._read_device_info)

        return self._parse(regs)

    async def async_shutdown(self) -> None:
        """Disconnect the client when HA shuts down."""
        await super().async_shutdown()
        await self.hass.async_add_executor_job(self._disconnect)
