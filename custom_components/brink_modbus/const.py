"""Constants for BRINK Heat Recovery Unit integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "brink_modbus"
MANUFACTURER = "BRINK"

# Platforms
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SWITCH,
]

# Default configuration
DEFAULT_SLAVE_ID = 20
DEFAULT_BAUDRATE = 19200
DEFAULT_BYTESIZE = 8
DEFAULT_PARITY = "E"
DEFAULT_STOPBITS = 1
DEFAULT_TCP_PORT = 502
DEFAULT_CONNECTION_TYPE = "tcp"
DEFAULT_CONTROL_ENABLED = False
DEFAULT_AUTO_CONTROL_MODE = False

# Configuration entry keys.  ``connection_type`` is deliberately optional when
# reading an entry: releases before TCP support only stored serial settings.
CONF_CONNECTION_TYPE = "connection_type"
CONF_SERIAL_PORT = "port"
CONF_SLAVE_ID = "slave_id"
CONF_BAUDRATE = "baudrate"
CONF_MODEL = "model"
CONF_CONTROL_ENABLED = "control_enabled"
CONF_AUTO_CONTROL_MODE = "auto_control_mode"

CONNECTION_TYPE_SERIAL = "serial"
CONNECTION_TYPE_TCP = "tcp"
CONNECTION_TYPE_RTU_OVER_TCP = "rtu_over_tcp"
CONNECTION_TYPES = (
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    CONNECTION_TYPE_RTU_OVER_TCP,
)

# The remote-control (8002) limits in the Flair installation manuals. Flow
# profile entities use the same model limit in their UI; the generic register
# map retains 325 as a backward-compatible fallback for callers without model
# context.
MODEL_MAX_AIRFLOW = {
    "flair_325": 325,
    "flair_325_plus": 325,
    "flair_350": 350,
    "flair_400": 400,
}

# Supported models
SUPPORTED_MODELS = {
    "flair_325": "FLAIR 325",
    "flair_325_plus": "FLAIR 325 Plus", 
    "flair_350": "FLAIR 350",
    "flair_400": "FLAIR 400",
}

# Update intervals
SCAN_INTERVAL_FAST = 10  # seconds - for temperatures, flows

# Modbus Register Maps
# Based on BRINK "Modbus UWA2-B/UWA2-E" installation regulations (614882-D).
#
# Optional keys per register:
#   "entity": False        read for derived values only, no entity of its own
#   "words": 2             unsigned 32-bit value in two registers, high word first
#   "map": {...}           enumerated status shown as text
#   "category": "diagnostic" / "config"
#   "enabled": False       entity disabled by default for new installs
#   "state_class": "total_increasing"

# Input Registers (Read-Only) - Function Code 04
INPUT_REGISTERS = {
    # System Information
    # 4000-4002 software version and 4010-4012 BCD serial number feed the
    # device info (sw_version / serial_number) and the Software Version sensor.
    "software_version_type": {"address": 4000, "unit": None, "entity": False},
    "software_version_minor": {"address": 4001, "unit": None, "entity": False},
    "software_version_build": {"address": 4002, "unit": None, "entity": False},
    "device_type": {"address": 4004, "unit": None, "category": "diagnostic"},
    "serial_number_1": {"address": 4010, "unit": None, "category": "diagnostic"},
    "serial_number_2": {"address": 4011, "unit": None, "category": "diagnostic"},
    "serial_number_3": {"address": 4012, "unit": None, "entity": False},

    # Operating state
    "active_function": {"address": 4020, "unit": None, "map": "ACTIVE_FUNCTION_MAP"},
    "fan_control_type": {"address": 4021, "unit": None, "map": "FAN_CONTROL_TYPE_MAP", "category": "diagnostic", "enabled": False},
    "ventilation_mode": {"address": 4022, "unit": None, "map": "VENTILATION_MODE_MAP"},
    "supply_fan_status": {"address": 4030, "unit": None, "map": "FAN_STATUS_MAP", "category": "diagnostic"},
    "exhaust_fan_status": {"address": 4040, "unit": None, "map": "FAN_STATUS_MAP", "category": "diagnostic"},
    
    # Pressures (Pa, divided by 10)
    "supply_pressure": {"address": 4023, "signed": True, "unit": "Pa", "scale": 0.1, "device_class": "pressure"},
    "exhaust_pressure": {"address": 4024, "signed": True, "unit": "Pa", "scale": 0.1, "device_class": "pressure"},
    
    # Air Volumes (m³/h)
    "supply_volume_setpoint": {"address": 4031, "unit": "m³/h"},
    "supply_volume_actual": {"address": 4032, "unit": "m³/h"},
    "exhaust_volume_setpoint": {"address": 4041, "unit": "m³/h"},
    "exhaust_volume_actual": {"address": 4042, "unit": "m³/h"},
    
    # Fan RPM
    "supply_fan_rpm": {"address": 4034, "unit": "RPM"},
    "exhaust_fan_rpm": {"address": 4044, "unit": "RPM"},
    
    # Temperatures (°C, divided by 10)
    "supply_air_temperature": {"address": 4036, "signed": True, "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "supply_air_humidity": {"address": 4037, "unit": "%", "device_class": "humidity"},
    "exhaust_air_temperature": {"address": 4046, "signed": True, "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "exhaust_air_humidity": {"address": 4047, "unit": "%", "device_class": "humidity"},
    "outside_temperature": {"address": 4081, "signed": True, "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    
    # Status registers
    "bypass_state": {"address": 4050, "unit": None},
    "preheater_state": {"address": 4060, "unit": None},
    "preheater_power": {"address": 4061, "unit": "%"},
    "frost_status": {"address": 4070, "unit": None, "map": "FROST_STATUS_MAP"},
    "frost_heater_power": {"address": 4071, "unit": "%"},
    "frost_fan_reduction": {"address": 4072, "unit": "%"},
    "flow_switch_position": {"address": 4080, "unit": None, "map": "FLOW_SWITCH_MAP"},
    "filter_state": {"address": 4100, "unit": None},
    "operating_time": {"address": 4113, "words": 2, "unit": "h", "state_class": "total_increasing", "category": "diagnostic"},
    "filter_usage_hours": {"address": 4115, "unit": "h"},
    
    # CO2 Sensors (ppm); status registers precede each value
    "co2_sensor_1_status": {"address": 4200, "unit": None, "map": "CO2_STATUS_MAP", "category": "diagnostic", "enabled": False},
    "co2_sensor_2_status": {"address": 4202, "unit": None, "map": "CO2_STATUS_MAP", "category": "diagnostic", "enabled": False},
    "co2_sensor_3_status": {"address": 4204, "unit": None, "map": "CO2_STATUS_MAP", "category": "diagnostic", "enabled": False},
    "co2_sensor_4_status": {"address": 4206, "unit": None, "map": "CO2_STATUS_MAP", "category": "diagnostic", "enabled": False},
    "co2_sensor_1": {"address": 4201, "unit": "ppm", "device_class": "carbon_dioxide"},
    "co2_sensor_2": {"address": 4203, "unit": "ppm", "device_class": "carbon_dioxide"},
    "co2_sensor_3": {"address": 4205, "unit": "ppm", "device_class": "carbon_dioxide"},
    "co2_sensor_4": {"address": 4207, "unit": "ppm", "device_class": "carbon_dioxide"},
}

# Holding Registers (Read/Write) - Function Code 03/06
HOLDING_REGISTERS = {
    # Flow levels for different power modes
    "flow_level_0_absence": {"address": 6000, "unit": "m³/h", "min": 0, "max": 325},
    "flow_level_1_low": {"address": 6001, "unit": "m³/h", "min": 0, "max": 325},
    "flow_level_2_normal": {"address": 6002, "unit": "m³/h", "min": 0, "max": 325},
    "flow_level_3_high": {"address": 6003, "unit": "m³/h", "min": 0, "max": 325},
    
    # Imbalance settings
    "imbalance_allowed": {"address": 6033, "unit": None, "min": 0, "max": 1},
    "supply_imbalance_offset": {"address": 6035, "signed": True, "unit": "%", "min": -15, "max": 15},
    "exhaust_imbalance_offset": {"address": 6036, "signed": True, "unit": "%", "min": -15, "max": 15},
    
    # Bypass mode setting
    "bypass_mode_setting": {"address": 6100, "unit": None, "min": 0, "max": 2},
    # Bypass thresholds, tenths of °C; min/max/step below are in °C
    "bypass_temperature_dwelling": {"address": 6101, "signed": True, "unit": "°C", "scale": 0.1, "min": 15.0, "max": 35.0, "step": 0.5},
    "bypass_temperature_outside": {"address": 6102, "signed": True, "unit": "°C", "scale": 0.1, "min": 7.0, "max": 15.0, "step": 0.5},
    "bypass_temperature_hysteresis": {"address": 6103, "signed": True, "unit": "°C", "scale": 0.1, "min": 0.0, "max": 5.0, "step": 0.5},

    # Filter
    "filter_warning_days": {"address": 6120, "unit": "d", "min": 1, "max": 365},
    
    # CO2 settings
    "co2_sensor_mode": {"address": 6150, "unit": None, "min": 0, "max": 1},
    
    # Geo heat exchanger settings
    "geo_heat_exchanger": {"address": 6240, "unit": None, "min": 0, "max": 1},
    # Tenths of °C; min/max below are in °C
    "geo_min_temperature": {"address": 6241, "signed": True, "unit": "°C", "scale": 0.1, "min": 0.0, "max": 10.0},
    "geo_max_temperature": {"address": 6242, "signed": True, "unit": "°C", "scale": 0.1, "min": 15.0, "max": 40.0},
    
    # Modbus control settings
    "slave_address": {"address": 7991, "unit": None, "min": 1, "max": 247},
    "modbus_control": {"address": 8000, "unit": None, "min": 0, "max": 2},
    "power_switch_position": {"address": 8001, "unit": None, "min": 0, "max": 3},
    # Register 8002 is model-specific. Use ``get_airflow_limits`` rather than
    # this legacy default when exposing a control or validating a service.
    "flow_setpoint": {"address": 8002, "unit": "m³/h", "min": 50, "max": 325},
    # Write 1 = standby, 2 = normal mode; reads back 1 while in standby.
    "standby": {"address": 8003, "unit": None, "min": 0, "max": 2},
    # Command registers: reading them clears the last result, so never poll.
    "filter_reset": {"address": 8010, "unit": None, "min": 0, "max": 1},
    "device_reset": {"address": 8011, "unit": None, "min": 0, "max": 1},
}

# Holding registers that are actions, not state; the coordinator never reads them.
UNPOLLED_HOLDING_REGISTERS = {"slave_address", "filter_reset", "device_reset"}

# Text mappings for status values
BYPASS_STATE_MAP = {
    0: "Initializing",
    1: "Open", 
    2: "Closed",
    3: "Open",
    4: "Closed",
    255: "Error",
}

FILTER_STATE_MAP = {
    0: "Clean",
    1: "Dirty",
}

PREHEATER_STATE_MAP = {
    0: "Off",
    1: "Starting",
    2: "Active",
    3: "Test mode",
}

ACTIVE_FUNCTION_MAP = {
    0: "Standby",
    1: "Bootloader",
    2: "Non-blocking error",
    3: "Blocking error",
    4: "Manual",
    5: "Holiday",
    6: "Night ventilation",
    7: "Party",
    8: "Bypass boost",
    9: "Normal boost",
    10: "Auto CO2",
    11: "Auto eBus",
    12: "Auto Modbus",
    13: "Auto LAN/WLAN portal",
    14: "Auto LAN/WLAN local",
}

FAN_CONTROL_TYPE_MAP = {
    0: "Initializing",
    1: "Constant flow",
    2: "Constant PWM",
    3: "Off",
    4: "Error",
    5: "Mass balance",
    6: "Standby",
}

VENTILATION_MODE_MAP = {
    0: "Holiday",
    1: "Low",
    2: "Normal",
    3: "High",
    4: "Auto",
}

FAN_STATUS_MAP = {
    2: "No communication",
    3: "Idle",
    4: "Running",
    5: "Blocked",
    6: "Fan error",
}

FROST_STATUS_MAP = {
    0: "Not initialized",
    1: "Power-up delay",
    2: "No frost",
    3: "No frost delay",
    4: "Frost control start delay",
    5: "Wait for icing",
    6: "Ice detected delay",
    7: "Heating",
    8: "Wait for free heater",
    9: "Fan control start delay",
    10: "Fan control wait delay",
    11: "Fan control",
    12: "Fan off delay",
    13: "Fan off",
    14: "Fan restarting",
    15: "Error",
    16: "Test mode",
}

FLOW_SWITCH_MAP = {
    0: "Holiday",
    1: "Low",
    2: "Normal",
    3: "High",
    255: "Invalid",
}

CO2_STATUS_MAP = {
    0: "Error",
    1: "Not initialized",
    2: "Idle",
    3: "Warming up",
    4: "Running",
    5: "Calibrating",
    6: "Self test",
}

BYPASS_MODE_MAP = {
    0: "Automatic",
    1: "Closed", 
    2: "Open",
}

POWER_SWITCH_MAP = {
    0: "Absence",
    1: "Low",
    2: "Normal", 
    3: "High",
    4: "Manual",  # Wall controller or external control active
}

MODBUS_CONTROL_MAP = {
    0: "Disabled",
    1: "Switch Control",
    2: "Flow Control",
}

# Icons for different sensor types
SENSOR_ICONS = {
    "temperature": "mdi:thermometer",
    "pressure": "mdi:gauge",
    "volume": "mdi:fan",
    "rpm": "mdi:speedometer",
    "co2": "mdi:molecule-co2",
    "filter": "mdi:air-filter",
    "bypass": "mdi:valve",
    "preheater": "mdi:heating-coil",
}



def get_max_airflow(model: str | None) -> int:
    """Return the documented Modbus remote-flow maximum for a model."""
    return MODEL_MAX_AIRFLOW.get(model or "", MODEL_MAX_AIRFLOW["flair_325_plus"])


def get_airflow_limits(model: str | None) -> tuple[int, int]:
    """Return the documented non-zero limits for remote register 8002."""
    return (50, get_max_airflow(model))


def map_key(mapping: dict[int, str], option: str) -> int | None:
    """Return the register value for a mapped text (case-insensitive), or None."""
    return next(
        (value for value, text in mapping.items() if text.casefold() == option.casefold()),
        None,
    )
