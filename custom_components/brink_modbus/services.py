"""BRINK HRU services."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError

from .const import (
    BYPASS_MODE_MAP,
    DOMAIN,
    HOLDING_REGISTERS,
    POWER_SWITCH_MAP,
    get_max_airflow,
)
from .coordinator import BrinkCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_BYPASS_MODE = "set_bypass_mode"
SERVICE_SET_FLOW_SPEED = "set_flow_speed"
SERVICE_SET_POWER_MODE = "set_power_mode"
SERVICE_RESET_DEVICE = "reset_device"
SERVICE_READ_ALL_REGISTERS = "read_all_registers"

SET_BYPASS_MODE_SCHEMA = vol.Schema({vol.Required("mode"): vol.In(["automatic", "closed", "open"])})
# Model-specific limits are checked after the target coordinator is known.
SET_FLOW_SPEED_SCHEMA = vol.Schema({vol.Required("speed"): vol.All(int, vol.Range(min=0, max=400))})
SET_POWER_MODE_SCHEMA = vol.Schema({vol.Required("mode"): vol.In(["absence", "low", "normal", "high"])})


def _get_coordinator(hass: HomeAssistant, call: ServiceCall) -> BrinkCoordinator:
    """Resolve a service target and reject monitoring-only entries clearly."""
    entry_id = call.data.get("config_entry_id")
    if entry_id:
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    else:
        coordinator = next(
            (
                item
                for item in hass.data.get(DOMAIN, {}).values()
                if isinstance(item, BrinkCoordinator)
            ),
            None,
        )
    if not isinstance(coordinator, BrinkCoordinator):
        raise ServiceValidationError("No BRINK HRU device found")
    if not coordinator.control_enabled:
        raise ServiceValidationError(
            "Controls are disabled for this BRINK entry; reconfigure it with writable controls enabled"
        )
    return coordinator


def _map_value(mapping: dict[int, str], option: str, label: str) -> int:
    """Convert a service value to its documented register encoding."""
    for value, text in mapping.items():
        if text.lower() == option:
            return value
    raise ServiceValidationError(f"Invalid {label}: {option}")


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up BRINK HRU services."""

    async def async_set_bypass_mode(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        mode = call.data["mode"]
        success = await coordinator.async_write_register(
            HOLDING_REGISTERS["bypass_mode_setting"]["address"],
            _map_value(BYPASS_MODE_MAP, mode, "bypass mode"),
        )
        if not success:
            raise ServiceValidationError(f"Failed to set bypass mode to {mode}")

    async def async_set_flow_speed(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        speed = call.data["speed"]
        maximum = get_max_airflow(coordinator.model)
        if speed != 0 and not 50 <= speed <= maximum:
            raise ServiceValidationError(
                f"Flow speed must be 0 or between 50 and {maximum} m³/h for this model"
            )
        if not await coordinator.async_ensure_control_mode(2):
            raise ServiceValidationError(
                "Set Modbus Control Mode to Flow Control explicitly before setting flow speed"
            )
        success = await coordinator.async_write_register(
            HOLDING_REGISTERS["flow_setpoint"]["address"], speed
        )
        if not success:
            raise ServiceValidationError(f"Failed to set flow speed to {speed}")

    async def async_set_power_mode(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        if not await coordinator.async_ensure_control_mode(1):
            raise ServiceValidationError(
                "Set Modbus Control Mode to Switch Control explicitly before setting power mode"
            )
        mode = call.data["mode"]
        success = await coordinator.async_write_register(
            HOLDING_REGISTERS["power_switch_position"]["address"],
            _map_value(POWER_SWITCH_MAP, mode, "power mode"),
        )
        if not success:
            raise ServiceValidationError(f"Failed to set power mode to {mode}")

    async def async_reset_device(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        _LOGGER.warning("Triggering a user-requested BRINK device reset")
        success = await coordinator.async_write_register(
            HOLDING_REGISTERS["device_reset"]["address"], 1
        )
        if not success:
            raise ServiceValidationError("Failed to trigger device reset")

    async def async_read_all_registers(call: ServiceCall) -> None:
        """Diagnostic reads remain available in monitoring-only mode."""
        entry_id = call.data.get("config_entry_id")
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id) if entry_id else next(
            (
                item
                for item in hass.data.get(DOMAIN, {}).values()
                if isinstance(item, BrinkCoordinator)
            ),
            None,
        )
        if not isinstance(coordinator, BrinkCoordinator):
            raise ServiceValidationError("No BRINK HRU device found")
        hass.bus.async_fire(
            f"{DOMAIN}_diagnostics",
            {"device_id": entry_id, "registers": await coordinator.async_read_all_registers()},
        )

    hass.services.async_register(DOMAIN, SERVICE_SET_BYPASS_MODE, async_set_bypass_mode, schema=SET_BYPASS_MODE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_FLOW_SPEED, async_set_flow_speed, schema=SET_FLOW_SPEED_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_POWER_MODE, async_set_power_mode, schema=SET_POWER_MODE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_RESET_DEVICE, async_reset_device)
    hass.services.async_register(DOMAIN, SERVICE_READ_ALL_REGISTERS, async_read_all_registers)


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload BRINK HRU services."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_BYPASS_MODE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_FLOW_SPEED)
    hass.services.async_remove(DOMAIN, SERVICE_SET_POWER_MODE)
    hass.services.async_remove(DOMAIN, SERVICE_RESET_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_READ_ALL_REGISTERS)
