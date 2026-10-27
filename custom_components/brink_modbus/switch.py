"""BRINK HRU switch platform."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HOLDING_REGISTERS
from .coordinator import BrinkCoordinator
from .entity import BrinkControlEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BRINK HRU switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        BrinkImbalanceAllowedSwitch(coordinator, entry),
        BrinkCO2SensorModeSwitch(coordinator, entry),
        BrinkGeoHeatExchangerSwitch(coordinator, entry),
        BrinkDeviceResetSwitch(coordinator, entry),
        BrinkStandbySwitch(coordinator, entry),
    ]
    
    async_add_entities(entities)

class BrinkImbalanceAllowedSwitch(BrinkControlEntity, SwitchEntity):
    """BRINK imbalance allowed switch."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Imbalance Allowed"
        self._attr_unique_id = f"{entry.entry_id}_imbalance_allowed_switch"
        self._attr_icon = "mdi:scale-balance"

    @property
    def is_on(self) -> bool | None:
        """Return true if imbalance is allowed."""
        if self.coordinator.data is None:
            return None
            
        return self.coordinator.data.get("imbalance_allowed") == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on imbalance allowance."""
        await self._async_write(HOLDING_REGISTERS["imbalance_allowed"]["address"], 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off imbalance allowance."""
        await self._async_write(HOLDING_REGISTERS["imbalance_allowed"]["address"], 0)

class BrinkCO2SensorModeSwitch(BrinkControlEntity, SwitchEntity):
    """BRINK CO2 sensor mode switch."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "CO2 Sensor Mode"
        self._attr_unique_id = f"{entry.entry_id}_co2_sensor_mode_switch"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_icon = "mdi:molecule-co2"

    @property
    def is_on(self) -> bool | None:
        """Return true if CO2 sensor mode is enabled."""
        if self.coordinator.data is None:
            return None
            
        return self.coordinator.data.get("co2_sensor_mode") == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on CO2 sensor mode."""
        await self._async_write(HOLDING_REGISTERS["co2_sensor_mode"]["address"], 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off CO2 sensor mode."""
        await self._async_write(HOLDING_REGISTERS["co2_sensor_mode"]["address"], 0)

class BrinkGeoHeatExchangerSwitch(BrinkControlEntity, SwitchEntity):
    """BRINK geo heat exchanger switch."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Geo Heat Exchanger"
        self._attr_unique_id = f"{entry.entry_id}_geo_heat_exchanger_switch"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_icon = "mdi:heat-pump"

    @property
    def is_on(self) -> bool | None:
        """Return true if geo heat exchanger is enabled."""
        if self.coordinator.data is None:
            return None
            
        return self.coordinator.data.get("geo_heat_exchanger") == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on geo heat exchanger."""
        await self._async_write(HOLDING_REGISTERS["geo_heat_exchanger"]["address"], 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off geo heat exchanger."""
        await self._async_write(HOLDING_REGISTERS["geo_heat_exchanger"]["address"], 0)

class BrinkDeviceResetSwitch(BrinkControlEntity, SwitchEntity):
    """BRINK device reset switch."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Device Reset"
        self._attr_unique_id = f"{entry.entry_id}_device_reset_switch"
        # A "switch" that reboots the unit fires on bulk turn_on calls; the
        # Reset Device button replaces it. Kept (disabled) for existing installs.
        self._attr_entity_registry_enabled_default = False
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_icon = "mdi:restart"

    @property
    def is_on(self) -> bool | None:
        """Return false - reset is momentary action."""
        return False  # Reset is always off, it's a momentary action

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Trigger device reset."""
        _LOGGER.warning("Triggering BRINK device reset")
        
        await self._async_write(HOLDING_REGISTERS["device_reset"]["address"], 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off - no action needed for reset."""


class BrinkStandbySwitch(BrinkControlEntity, SwitchEntity):
    """Put the unit in standby (8003: write 1 = standby, 2 = normal; reads 1 in standby)."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry)
        self._attr_name = "Standby"
        self._attr_unique_id = f"{entry.entry_id}_standby"
        self._attr_icon = "mdi:power-sleep"

    @property
    def is_on(self) -> bool | None:
        """Return true while the unit is in standby (also when set by another interface)."""
        if self.coordinator.data is None or self.coordinator.data.get("standby") is None:
            return None
        return self.coordinator.data["standby"] == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the unit in standby."""
        await self._async_write(HOLDING_REGISTERS["standby"]["address"], 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Return the unit to normal mode."""
        await self._async_write(HOLDING_REGISTERS["standby"]["address"], 2)
