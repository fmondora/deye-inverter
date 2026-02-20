"""Diagnostics support for Solarman Deye.

Provides the "Download Diagnostics" button on the device page in Home
Assistant.  When clicked it reads the inverter holding registers
(configuration) and combines them with the latest sensor readings into
a single JSON document.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_TYPES,
    DOMAIN,
    HOLDING_READ_BLOCKS,
    HOLDING_REGISTER_LABELS,
    WORK_MODES,
)
from .coordinator import SolarmanDeyeCoordinator

# Keys that may reveal private information and should be masked.
REDACT_KEYS = {"serial_number"}


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    """Replace sensitive values with '**REDACTED**'."""
    return {
        k: ("**REDACTED**" if k in REDACT_KEYS else v)
        for k, v in data.items()
    }


def _read_inverter_config(coordinator: SolarmanDeyeCoordinator) -> dict[str, Any]:
    """Read holding registers and return decoded configuration (blocking)."""
    client = coordinator._new_client()
    config: dict[str, Any] = {}

    try:
        for start, count in HOLDING_READ_BLOCKS:
            try:
                values = client.read_holding_registers(
                    register_addr=start, quantity=count
                )
            except Exception:  # noqa: BLE001
                continue
            for i, val in enumerate(values):
                reg = start + i
                label = HOLDING_REGISTER_LABELS.get(reg)
                if label is not None:
                    config[label] = val
    finally:
        try:
            client.disconnect()
        except Exception:  # noqa: BLE001
            pass

    # Decode well-known enumerated values
    if "Work mode" in config:
        raw = config["Work mode"]
        config["Work mode"] = WORK_MODES.get(raw, f"Unknown ({raw})")

    if "Battery type" in config:
        raw = config["Battery type"]
        config["Battery type"] = BATTERY_TYPES.get(raw, f"Unknown ({raw})")

    # Scale voltage registers (stored as ×0.1 V)
    for key in (
        "Battery empty voltage",
        "Battery full voltage",
        "Battery low voltage warning",
    ):
        if key in config:
            config[key] = f"{config[key] * 0.1:.1f} V"

    # Append unit hints to current / SOC fields
    for key in ("Max charge current", "Max discharge current", "Grid charge current limit"):
        if key in config:
            config[key] = f"{config[key]} A"

    for key in ("Battery empty SOC", "Battery shutdown SOC", "Battery low SOC warning"):
        if key in config:
            config[key] = f"{config[key]} %"

    if "Battery capacity" in config:
        config["Battery capacity"] = f"{config['Battery capacity']} Ah"

    # Format time-of-use slots into readable strings
    for slot in range(1, 7):
        sh = config.pop(f"Slot {slot} start hour", None)
        sm = config.pop(f"Slot {slot} start minute", None)
        eh = config.pop(f"Slot {slot} end hour", None)
        em = config.pop(f"Slot {slot} end minute", None)
        en = config.pop(f"Slot {slot} enable", None)
        cd = config.pop(f"Slot {slot} charge/discharge", None)
        soc = config.pop(f"Slot {slot} SOC target", None)
        if sh is not None:
            mode = "Charge" if cd == 0 else "Discharge" if cd == 1 else f"Mode {cd}"
            enabled = "ON" if en == 1 else "OFF"
            config[f"Time slot {slot}"] = (
                f"{sh:02d}:{sm:02d}-{eh:02d}:{em:02d}  "
                f"{mode}  SOC {soc}%  [{enabled}]"
            )

    return config


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: SolarmanDeyeCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Latest sensor readings
    sensor_data = dict(coordinator.data) if coordinator.data else {}

    # Read holding registers for inverter configuration
    try:
        inverter_config = await hass.async_add_executor_job(
            _read_inverter_config, coordinator
        )
    except Exception as err:  # noqa: BLE001
        inverter_config = {"error": str(err)}

    return {
        "config_entry": _redact(dict(entry.data)),
        "options": dict(entry.options),
        "inverter_status": sensor_data,
        "inverter_configuration": inverter_config,
    }
