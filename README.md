# Solarman Deye - Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Custom integration for Home Assistant that reads **all available data** from Deye/Sunsynk hybrid inverters via the Solarman V5 protocol over LAN.

## Features

- **Auto-discovery**: finds Solarman data loggers on the network via UDP broadcast (port 48899)
- **~40 sensors**: PV, battery, grid, load, inverter, temperatures, daily/total energy, status
- **CO2 savings tracking**: daily and total CO2 avoided thanks to solar production (Italian grid default, configurable)
- **Battery cycle tracking**: equivalent full charge cycles and estimated battery health percentage
- **Diagnostics / About page**: download inverter configuration (work mode, battery settings, time-of-use slots) from the device page
- **Energy Dashboard ready**: all energy sensors use `TOTAL_INCREASING` state class for seamless integration
- **Config flow UI**: set up entirely from the Home Assistant interface
- **Efficient polling**: reads Modbus registers in contiguous blocks (2 reads per cycle)
- **Auto-reconnect**: recovers automatically from connection drops

## Sensors

| Category | Sensors |
|---|---|
| **PV** | PV1/PV2 Voltage, Current, Power |
| **Battery** | SOC, Voltage, Current, Power, Temperature |
| **Grid** | Voltage, Current, Power, Frequency, CT Power |
| **Load** | Power, Frequency |
| **Inverter** | Power, Voltage, Current, Frequency |
| **Temperature** | DC Transformer, Radiator, Ambient |
| **Daily Energy** | PV, Battery Charge/Discharge, Grid Import/Export, Load |
| **Total Energy** | PV, Battery Charge/Discharge, Grid Import/Export, Load |
| **Status** | Running State, Grid Connected, Daily Active Energy |
| **CO2** | Daily CO2 Saved, Total CO2 Saved |
| **Battery Cycles** | Battery Cycles, Battery Health |

## Installation via HACS

1. Open HACS in Home Assistant
2. Click the **three dots** menu (top right) and select **Custom repositories**
3. Add this repository URL and select category **Integration**
4. Click **Download**
5. Restart Home Assistant

## Manual Installation

Copy the `custom_components/solarman_deye` folder into your Home Assistant `custom_components` directory and restart.

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **Solarman Deye**
3. Choose **Auto-discover on network** or **Manual configuration**

### Auto-discovery

The integration sends a UDP broadcast on port 48899. All Solarman data loggers on the local network respond with their IP, MAC and serial number. Select the device you want to add.

### Manual

Enter:
- **IP Address**: your data logger's LAN IP (e.g. `192.168.86.69`)
- **Serial Number**: the data logger serial number
- **Port**: `8899` (default)
- **Slave ID**: `1` (default)

### Options

After setup, click **Configure** on the integration to change:

- **Update interval** (default: 30 seconds)
- **CO2 emission factor** (default: 0.256 kg CO2/kWh - Italian grid average, ISPRA)
- **Battery capacity** (default: 5.12 kWh) - used to compute equivalent full cycles
- **Battery rated cycle life** (default: 6000 for LiFePO4) - used to estimate battery health %

## Diagnostics / About

To view the inverter configuration (work mode, battery type and limits, time-of-use schedules):

1. Go to **Settings > Devices & Services > Solarman Deye**
2. Click on the device
3. Click **Download Diagnostics**

The JSON file contains the full inverter configuration read from holding registers, plus the current sensor readings.

## Energy Dashboard

Go to **Settings > Dashboards > Energy** and assign:

| Section | Sensor |
|---|---|
| Solar production | Total PV Energy |
| Battery charge | Total Battery Charge Energy |
| Battery discharge | Total Battery Discharge Energy |
| Grid consumption | Total Grid Import Energy |
| Return to grid | Total Grid Export Energy |

## Requirements

- Deye/Sunsynk single-phase hybrid inverter
- Solarman data logger on the local network (port 8899)
- Home Assistant 2024.1+

## License

MIT - see [LICENSE](LICENSE).

## Author

**Francesco Mondora**
