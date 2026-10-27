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
SCAN_INTERVAL_SLOW = 60  # seconds - for settings, diagnostics

# Modbus Register Maps
# Based on BRINK FLAIR 325 Plus documentation

# Input Registers (Read-Only) - Function Code 04
INPUT_REGISTERS = {
    # System Information
    "device_type": {"address": 4004, "type": "int16", "unit": None},
    "serial_number_1": {"address": 4010, "type": "int16", "unit": None},
    "serial_number_2": {"address": 4011, "type": "int16", "unit": None},
    "software_version": {"address": 4012, "type": "int16", "unit": None},
    
    # Pressures (Pa, divided by 10)
    "supply_pressure": {"address": 4023, "type": "int16", "signed": True, "unit": "Pa", "scale": 0.1, "device_class": "pressure"},
    "exhaust_pressure": {"address": 4024, "type": "int16", "signed": True, "unit": "Pa", "scale": 0.1, "device_class": "pressure"},
    
    # Air Volumes (m³/h)
    "supply_volume_setpoint": {"address": 4031, "type": "int16", "unit": "m³/h"},
    "supply_volume_actual": {"address": 4032, "type": "int16", "unit": "m³/h"},
    "exhaust_volume_setpoint": {"address": 4041, "type": "int16", "unit": "m³/h"},
    "exhaust_volume_actual": {"address": 4042, "type": "int16", "unit": "m³/h"},
    
    # Fan RPM
    "supply_fan_rpm": {"address": 4034, "type": "int16", "unit": "RPM"},
    "exhaust_fan_rpm": {"address": 4044, "type": "int16", "unit": "RPM"},
    
    # Temperatures (°C, divided by 10)
    "supply_air_temperature": {"address": 4036, "type": "int16", "signed": True, "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "supply_air_humidity": {"address": 4037, "type": "int16", "unit": "%", "device_class": "humidity"},
    "exhaust_air_temperature": {"address": 4046, "type": "int16", "signed": True, "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "exhaust_air_humidity": {"address": 4047, "type": "int16", "unit": "%", "device_class": "humidity"},
    "outside_temperature": {"address": 4081, "type": "int16", "signed": True, "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    
    # Status registers
    "bypass_state": {"address": 4050, "type": "int16", "unit": None},
    "preheater_state": {"address": 4060, "type": "int16", "unit": None},
    "preheater_power": {"address": 4061, "type": "int16", "unit": "%"},
    "filter_state": {"address": 4100, "type": "int16", "unit": None},
    "filter_usage_hours": {"address": 4115, "type": "int16", "unit": "h"},
    
    # CO2 Sensors (ppm)
    "co2_sensor_1": {"address": 4201, "type": "int16", "unit": "ppm", "device_class": "carbon_dioxide"},
    "co2_sensor_2": {"address": 4203, "type": "int16", "unit": "ppm", "device_class": "carbon_dioxide"},
    "co2_sensor_3": {"address": 4205, "type": "int16", "unit": "ppm", "device_class": "carbon_dioxide"},
    "co2_sensor_4": {"address": 4207, "type": "int16", "unit": "ppm", "device_class": "carbon_dioxide"},
}

# Holding Registers (Read/Write) - Function Code 03/06
HOLDING_REGISTERS = {
    # Flow levels for different power modes
    "flow_level_0_absence": {"address": 6000, "type": "int16", "unit": "m³/h", "min": 0, "max": 325},
    "flow_level_1_low": {"address": 6001, "type": "int16", "unit": "m³/h", "min": 0, "max": 325},
    "flow_level_2_normal": {"address": 6002, "type": "int16", "unit": "m³/h", "min": 0, "max": 325},
    "flow_level_3_high": {"address": 6003, "type": "int16", "unit": "m³/h", "min": 0, "max": 325},
    
    # Imbalance settings
    "imbalance_allowed": {"address": 6033, "type": "int16", "unit": None, "min": 0, "max": 1},
    "supply_imbalance_offset": {"address": 6035, "type": "int16", "signed": True, "unit": "%", "min": -15, "max": 15},
    "exhaust_imbalance_offset": {"address": 6036, "type": "int16", "signed": True, "unit": "%", "min": -15, "max": 15},
    
    # Bypass mode setting
    "bypass_mode_setting": {"address": 6100, "type": "int16", "unit": None, "min": 0, "max": 2},
    
    # CO2 settings
    "co2_sensor_mode": {"address": 6150, "type": "int16", "unit": None, "min": 0, "max": 1},
    
    # Geo heat exchanger settings
    "geo_heat_exchanger": {"address": 6240, "type": "int16", "unit": None, "min": 0, "max": 1},
    "geo_min_temperature": {"address": 6241, "type": "int16", "signed": True, "unit": "°C", "min": 0, "max": 100},
    "geo_max_temperature": {"address": 6242, "type": "int16", "signed": True, "unit": "°C", "min": 150, "max": 400},
    
    # Modbus control settings
    "slave_address": {"address": 7991, "type": "int16", "unit": None, "min": 1, "max": 247},
    "modbus_control": {"address": 8000, "type": "int16", "unit": None, "min": 0, "max": 2},
    "power_switch_position": {"address": 8001, "type": "int16", "unit": None, "min": 0, "max": 3},
    # Register 8002 is model-specific. Use ``get_airflow_limits`` rather than
    # this legacy default when exposing a control or validating a service.
    "flow_setpoint": {"address": 8002, "type": "int16", "unit": "m³/h", "min": 50, "max": 325},
    "device_reset": {"address": 8011, "type": "int16", "unit": None, "min": 0, "max": 1},
}

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

# Device classes
DEVICE_CLASSES = {
    "temperature": "temperature",
    "pressure": "pressure", 
    "carbon_dioxide": "carbon_dioxide",
}


def get_max_airflow(model: str | None) -> int:
    """Return the documented Modbus remote-flow maximum for a model."""
    return MODEL_MAX_AIRFLOW.get(model or "", MODEL_MAX_AIRFLOW["flair_325_plus"])


def get_airflow_limits(model: str | None) -> tuple[int, int]:
    """Return the documented non-zero limits for remote register 8002."""
    return (50, get_max_airflow(model))
