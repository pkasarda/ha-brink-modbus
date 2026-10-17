"""BRINK HRU select platform."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BYPASS_MODE_MAP,
    DOMAIN,
    HOLDING_REGISTERS,
    MODBUS_CONTROL_MAP,
    POWER_SWITCH_MAP,
)
from .coordinator import BrinkCoordinator
from .entity import BrinkControlEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BRINK HRU select platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        BrinkBypassModeSelect(coordinator, entry),
        BrinkPowerSwitchSelect(coordinator, entry),
        BrinkModbusControlSelect(coordinator, entry),
    ]
    
    async_add_entities(entities)

class BrinkBypassModeSelect(BrinkControlEntity, SelectEntity):
    """BRINK bypass mode select entity."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Bypass Mode"
        self._attr_unique_id = f"{entry.entry_id}_bypass_mode_select"
        self._attr_icon = "mdi:valve"
        self._attr_options = list(BYPASS_MODE_MAP.values())

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        if self.coordinator.data is None:
            return None
            
        mode_value = self.coordinator.data.get("bypass_mode_setting")
        if mode_value is None:
            return None
        
        # Return mapped value or None if not in map (select will show as not set)
        mapped = BYPASS_MODE_MAP.get(mode_value)
        if mapped is None:
            _LOGGER.warning("Unknown bypass mode value: %s (expected 0-2)", mode_value)
        return mapped

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the numeric value for the selected option
        mode_value = None
        for value, text in BYPASS_MODE_MAP.items():
            if text == option:
                mode_value = value
                break
                
        if mode_value is None:
            _LOGGER.error("Invalid bypass mode option: %s", option)
            return
            
        # Write to holding register
        success = await self.coordinator.async_write_register(
            HOLDING_REGISTERS["bypass_mode_setting"]["address"],
            mode_value
        )
        
        if not success:
            _LOGGER.error("Failed to set bypass mode to %s", option)

class BrinkPowerSwitchSelect(BrinkControlEntity, SelectEntity):
    """BRINK power switch position select entity."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Power Switch Position"
        self._attr_unique_id = f"{entry.entry_id}_power_switch_select"
        self._attr_icon = "mdi:toggle-switch"
        # Exclude value 4 (Manual) - it's read-only, cannot be set
        self._attr_options = [v for k, v in POWER_SWITCH_MAP.items() if k != 4]
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Power switch only works in Switch Control mode (1), after writable
        # controls were explicitly enabled for this config entry.
        if not super().available or self.coordinator.data is None:
            return False
        
        control_mode = self.coordinator.data.get("modbus_control")
        if control_mode != 1:
            return False
        
        return super().available

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        if self.coordinator.data is None:
            _LOGGER.debug("Power switch: coordinator data is None")
            return None
            
        switch_value = self.coordinator.data.get("power_switch_position")
        if switch_value is None:
            _LOGGER.warning(
                "Power switch: register value is None. Available keys: %s",
                list(self.coordinator.data.keys())
            )
            return None
        
        # Return mapped value or None if not in map (select will show as not set)
        mapped = POWER_SWITCH_MAP.get(switch_value)
        if mapped is None:
            _LOGGER.warning("Unknown power switch value: %s (expected 0-4)", switch_value)
            return None
        
        _LOGGER.debug("Power switch: value=%s, mapped=%s", switch_value, mapped)
        return mapped

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the numeric value for the selected option
        switch_value = None
        for value, text in POWER_SWITCH_MAP.items():
            if text == option:
                switch_value = value
                break
                
        if switch_value is None:
            _LOGGER.error("Invalid power switch option: %s", option)
            return
        
        # Brink requires an explicit Switch Control mode change before register
        # 8001 accepts a switch position. Do not change 8000 as a side effect.
        current_control_mode = self.coordinator.data.get("modbus_control") if self.coordinator.data else None
        
        if current_control_mode != 1:
            _LOGGER.warning(
                "Power switch requires explicit Switch Control mode; current mode is %s",
                current_control_mode,
            )
            return
            
        # Write to holding register
        success = await self.coordinator.async_write_register(
            HOLDING_REGISTERS["power_switch_position"]["address"],
            switch_value
        )
        
        if not success:
            _LOGGER.error("Failed to set power switch to %s", option)
        else:
            _LOGGER.info("Successfully set power switch to %s (value: %s)", option, switch_value)

class BrinkModbusControlSelect(BrinkControlEntity, SelectEntity):
    """BRINK Modbus control mode select entity."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Modbus Control Mode"
        self._attr_unique_id = f"{entry.entry_id}_modbus_control_select"
        self._attr_icon = "mdi:connection"
        self._attr_options = list(MODBUS_CONTROL_MAP.values())

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        if self.coordinator.data is None:
            return None
            
        control_value = self.coordinator.data.get("modbus_control")
        if control_value is None:
            return None
        
        # Return mapped value or None if not in map (select will show as not set)
        mapped = MODBUS_CONTROL_MAP.get(control_value)
        if mapped is None:
            _LOGGER.warning("Unknown modbus control value: %s (expected 0-2)", control_value)
        return mapped

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the numeric value for the selected option
        control_value = None
        for value, text in MODBUS_CONTROL_MAP.items():
            if text == option:
                control_value = value
                break
                
        if control_value is None:
            _LOGGER.error("Invalid modbus control option: %s", option)
            return
            
        # Write to holding register
        success = await self.coordinator.async_write_register(
            HOLDING_REGISTERS["modbus_control"]["address"],
            control_value
        )
        
        if not success:
            _LOGGER.error("Failed to set modbus control to %s", option)
