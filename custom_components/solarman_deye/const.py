"""Constants for the Solarman Deye integration."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)

DOMAIN = "solarman_deye"

CONF_SERIAL = "serial_number"
CONF_PORT = "port"
CONF_SLAVE_ID = "slave_id"

DEFAULT_PORT = 8899
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 30

# CO2 emission factor for the Italian electricity grid (kg CO2 per kWh).
# Source: ISPRA — average Italian grid intensity ~256 g CO2/kWh.
DEFAULT_CO2_FACTOR = 0.256
CONF_CO2_FACTOR = "co2_factor"

# Computed CO2 sensor names (not tied to a Modbus register).
CO2_SENSORS = [
    ("Daily CO2 Saved", "kg", SensorStateClass.TOTAL_INCREASING, 2, "mdi:molecule-co2"),
    ("Total CO2 Saved", "kg", SensorStateClass.TOTAL_INCREASING, 1, "mdi:molecule-co2"),
]

# ---------------------------------------------------------------------------
# Battery cycle tracking
# ---------------------------------------------------------------------------

# Nominal battery capacity in kWh.  Common Deye-compatible packs: 5.12 kWh.
CONF_BATTERY_CAPACITY = "battery_capacity"
DEFAULT_BATTERY_CAPACITY = 5.12

# Rated cycle life of the battery.  LiFePO4 packs are typically rated 6000 cycles.
CONF_BATTERY_RATED_CYCLES = "battery_rated_cycles"
DEFAULT_BATTERY_RATED_CYCLES = 6000

# Computed battery sensors: (name, unit, state_class, precision, icon)
BATTERY_CYCLE_SENSORS = [
    ("Battery Cycles", "cycles", SensorStateClass.TOTAL_INCREASING, 1, "mdi:battery-sync"),
    ("Battery Health", PERCENTAGE, SensorStateClass.MEASUREMENT, 1, "mdi:battery-heart-variant"),
]

# ---------------------------------------------------------------------------
# Modbus register map for Deye single-phase hybrid inverters
# Each entry: (register, name, unit, device_class, state_class, scale, precision, signed)
# ---------------------------------------------------------------------------

REGISTERS_PV = [
    (109, "PV1 Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.1, 1, False),
    (110, "PV1 Current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.1, 1, False),
    (186, "PV1 Power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1, 0, False),
    (111, "PV2 Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.1, 1, False),
    (112, "PV2 Current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.1, 1, False),
    (187, "PV2 Power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1, 0, False),
]

REGISTERS_BATTERY = [
    (184, "Battery SOC", PERCENTAGE, SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, 1, 0, False),
    (183, "Battery Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.01, 2, False),
    (184, None, None, None, None, None, None, None),  # placeholder, SOC already read
    (190, "Battery Current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.01, 2, True),
    (191, "Battery Power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1, 0, True),
    (182, "Battery Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, 0.1, 1, False),
]

REGISTERS_GRID = [
    (150, "Grid Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.1, 1, False),
    (160, "Grid Current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.01, 2, True),
    (169, "Grid Power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1, 0, True),
    (79, "Grid Frequency", UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, 0.01, 2, False),
    (172, "Grid CT Power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1, 0, True),
]

REGISTERS_LOAD = [
    (178, "Load Power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1, 0, False),
    (192, "Load Frequency", UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, 0.01, 2, False),
]

REGISTERS_INVERTER = [
    (175, "Inverter Power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, 1, 0, True),
    (154, "Inverter Voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, 0.1, 1, False),
    (164, "Inverter Current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.01, 2, False),
    (193, "Inverter Frequency", UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, 0.01, 2, False),
]

REGISTERS_TEMPERATURE = [
    (90, "DC Transformer Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, 0.1, 1, True),
    (91, "Radiator Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, 0.1, 1, True),
    (95, "Ambient Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, 0.1, 1, True),
]

REGISTERS_ENERGY_DAILY = [
    (108, "Daily PV Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1, False),
    (70, "Daily Battery Charge Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1, False),
    (71, "Daily Battery Discharge Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1, False),
    (76, "Daily Grid Import Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1, False),
    (77, "Daily Grid Export Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1, False),
    (84, "Daily Load Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1, False),
]

# 32-bit total energy registers: (low_register, high_register, ...)
REGISTERS_ENERGY_TOTAL = [
    (96, 97, "Total PV Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1),
    (72, 73, "Total Battery Charge Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1),
    (74, 75, "Total Battery Discharge Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1),
    (78, 79, "Total Grid Import Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1),
    (81, 82, "Total Grid Export Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1),
    (85, 86, "Total Load Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1),
]

REGISTERS_STATUS = [
    (59, "Running State", None, None, None, 1, 0, False),
    (194, "Grid Connected Status", None, None, None, 1, 0, False),
    (60, "Daily Active Energy", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.1, 1, False),
]

# Running state mapping
RUNNING_STATES = {
    0: "Standby",
    1: "Self-check",
    2: "Normal",
    3: "Alarm",
    4: "Fault",
}

# All 16-bit register definitions combined for building read blocks
ALL_SINGLE_REGISTERS = (
    REGISTERS_PV
    + [r for r in REGISTERS_BATTERY if r[1] is not None]
    + REGISTERS_GRID
    + REGISTERS_LOAD
    + REGISTERS_INVERTER
    + REGISTERS_TEMPERATURE
    + REGISTERS_ENERGY_DAILY
    + REGISTERS_STATUS
)

# Read blocks: contiguous ranges of input registers to fetch efficiently.
# Each tuple is (start_register, count).
READ_BLOCKS = [
    (59, 55),   # 59-113: status, energy daily/total, grid freq, temps, PV
    (150, 45),  # 150-194: grid, inverter, load, battery, PV power, status
]

# ---------------------------------------------------------------------------
# Holding registers — inverter configuration (read on demand for diagnostics)
# Addresses based on Deye SUN-xK-SG04LP1 single-phase hybrid.
# ---------------------------------------------------------------------------

HOLDING_READ_BLOCKS = [
    (100, 15),   # 100-114: work mode, battery settings
    (148, 42),   # 148-189: time-of-use slots (6 × 7 registers)
]

HOLDING_REGISTER_LABELS: dict[int, str] = {
    # System / work mode
    100: "Work mode",
    101: "Grid charge enable",
    # Battery configuration
    102: "Battery type",
    103: "Battery capacity",
    104: "Battery empty voltage",
    105: "Battery full voltage",
    106: "Battery empty SOC",
    107: "Battery shutdown SOC",
    108: "Max charge current",
    109: "Max discharge current",
    110: "Grid charge current limit",
    111: "Battery low voltage warning",
    112: "Battery low SOC warning",
    # Time-of-use slot 1
    148: "Slot 1 start hour",
    149: "Slot 1 start minute",
    150: "Slot 1 end hour",
    151: "Slot 1 end minute",
    152: "Slot 1 enable",
    153: "Slot 1 charge/discharge",
    154: "Slot 1 SOC target",
    # Time-of-use slot 2
    155: "Slot 2 start hour",
    156: "Slot 2 start minute",
    157: "Slot 2 end hour",
    158: "Slot 2 end minute",
    159: "Slot 2 enable",
    160: "Slot 2 charge/discharge",
    161: "Slot 2 SOC target",
    # Time-of-use slot 3
    162: "Slot 3 start hour",
    163: "Slot 3 start minute",
    164: "Slot 3 end hour",
    165: "Slot 3 end minute",
    166: "Slot 3 enable",
    167: "Slot 3 charge/discharge",
    168: "Slot 3 SOC target",
    # Time-of-use slot 4
    169: "Slot 4 start hour",
    170: "Slot 4 start minute",
    171: "Slot 4 end hour",
    172: "Slot 4 end minute",
    173: "Slot 4 enable",
    174: "Slot 4 charge/discharge",
    175: "Slot 4 SOC target",
    # Time-of-use slot 5
    176: "Slot 5 start hour",
    177: "Slot 5 start minute",
    178: "Slot 5 end hour",
    179: "Slot 5 end minute",
    180: "Slot 5 enable",
    181: "Slot 5 charge/discharge",
    182: "Slot 5 SOC target",
    # Time-of-use slot 6
    183: "Slot 6 start hour",
    184: "Slot 6 start minute",
    185: "Slot 6 end hour",
    186: "Slot 6 end minute",
    187: "Slot 6 enable",
    188: "Slot 6 charge/discharge",
    189: "Slot 6 SOC target",
}

WORK_MODES: dict[int, str] = {
    0: "Selling first",
    1: "Zero-export to load",
    2: "Zero-export to CT",
}

BATTERY_TYPES: dict[int, str] = {
    0: "Lead-acid",
    1: "LiFePO4",
    2: "User-defined",
}

# ---------------------------------------------------------------------------
# Firmware update check
# ---------------------------------------------------------------------------

# Device info registers — read once at startup for firmware version.
# Input registers 0-15 contain device identification on Deye hybrids.
DEVICE_INFO_BLOCK = (0, 16)

# Deye device type codes
DEVICE_TYPES: dict[int, str] = {
    2: "String Inverter",
    3: "Single-Phase Hybrid",
    4: "Micro Inverter",
    5: "Three-Phase Hybrid",
}

# URL of the firmware manifest hosted in the GitHub repository.
FIRMWARE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/fmondora/deye-inverter/main/firmware.json"
)

# How often to check for firmware updates (seconds).
FIRMWARE_CHECK_INTERVAL = 86400  # 24 hours
