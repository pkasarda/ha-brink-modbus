"""Diagnostics support for BRINK HRU."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {CONF_HOST, "serial_number", "serial_number_1", "serial_number_2", "serial_number_3"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return the entry settings and the last polled register values."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "connection": {
            "type": coordinator.connection_type,
            "controls_enabled": coordinator.control_enabled,
            "auto_control_mode": coordinator.auto_control_mode,
            "last_update_success": coordinator.last_update_success,
            "unsupported_registers": sorted(coordinator.unsupported_registers),
        },
        "data": async_redact_data(dict(coordinator.data or {}), TO_REDACT),
    }
