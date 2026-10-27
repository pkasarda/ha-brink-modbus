"""BRINK HRU number platform."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HOLDING_REGISTERS, get_airflow_limits, get_max_airflow
from .coordinator import BrinkCoordinator
from .entity import BrinkControlEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BRINK HRU number platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        # Flow levels
        BrinkFlowLevelNumber(coordinator, entry, "flow_level_0_absence", "Flow Level 0 (Absence)"),
        BrinkFlowLevelNumber(coordinator, entry, "flow_level_1_low", "Flow Level 1 (Low)"),
        BrinkFlowLevelNumber(coordinator, entry, "flow_level_2_normal", "Flow Level 2 (Normal)"),
        BrinkFlowLevelNumber(coordinator, entry, "flow_level_3_high", "Flow Level 3 (High)"),
        
        # Flow setpoint (current target)
        BrinkFlowSetpointNumber(coordinator, entry),
        
        # Imbalance settings
        BrinkImbalanceOffsetNumber(coordinator, entry, "supply_imbalance_offset", "Supply Imbalance Offset"),
        BrinkImbalanceOffsetNumber(coordinator, entry, "exhaust_imbalance_offset", "Exhaust Imbalance Offset"),
        
        # Geo heat exchanger temperatures
        BrinkGeoTemperatureNumber(coordinator, entry, "geo_min_temperature", "Geo Min Temperature"),
        BrinkGeoTemperatureNumber(coordinator, entry, "geo_max_temperature", "Geo Max Temperature"),
    ]
    
    async_add_entities(entities)

class BrinkFlowLevelNumber(BrinkControlEntity, NumberEntity):
    """BRINK flow level number entity."""

    def __init__(
        self,
        coordinator: BrinkCoordinator,
        entry: ConfigEntry,
        setting_key: str,
        name: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry)
        self._setting_key = setting_key
        self._config = HOLDING_REGISTERS[setting_key]
        
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{setting_key}"
        self._attr_icon = "mdi:fan"
        self._attr_native_unit_of_measurement = UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
        self._attr_mode = NumberMode.BOX
        
        # Set limits from config
        self._attr_native_min_value = self._config.get("min", 0)
        self._attr_native_max_value = get_max_airflow(coordinator.model)
        self._attr_native_step = 5

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
            
        return self.coordinator.data.get(self._setting_key)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        success = await self.coordinator.async_write_register(
            self._config["address"],
            int(value)
        )
        
        if not success:
            _LOGGER.error("Failed to set %s to %s", self._setting_key, value)

class BrinkFlowSetpointNumber(BrinkControlEntity, NumberEntity):
    """BRINK flow setpoint number entity."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry)
        self._config = HOLDING_REGISTERS["flow_setpoint"]
        
        self._attr_name = "Flow Setpoint"
        self._attr_unique_id = f"{entry.entry_id}_flow_setpoint"
        self._attr_icon = "mdi:fan-speed-3"
        self._attr_native_unit_of_measurement = UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
        self._attr_mode = NumberMode.SLIDER
        
        # Set limits from config
        self._attr_native_min_value, self._attr_native_max_value = get_airflow_limits(
            coordinator.model
        )
        self._attr_native_step = 5

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
            
        return self.coordinator.data.get("flow_setpoint")

    @property
    def available(self) -> bool:
        """The device accepts 8002 only in flow mode, unless it may switch 8000 itself."""
        if not super().available or self.coordinator.data is None:
            return False
        return (
            self.coordinator.auto_control_mode
            or self.coordinator.data.get("modbus_control") == 2
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        # Register 8002 accepts a flow target only in Flow Control mode (2).
        if not await self.coordinator.async_ensure_control_mode(2):
            return
        
        success = await self.coordinator.async_write_register(
            self._config["address"],
            int(value)
        )
        
        if not success:
            _LOGGER.error("Failed to set flow setpoint to %s", value)
        else:
            _LOGGER.info("Successfully set flow setpoint to %s m³/h", value)

class BrinkImbalanceOffsetNumber(BrinkControlEntity, NumberEntity):
    """BRINK imbalance offset number entity."""

    def __init__(
        self,
        coordinator: BrinkCoordinator,
        entry: ConfigEntry,
        setting_key: str,
        name: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry)
        self._setting_key = setting_key
        self._config = HOLDING_REGISTERS[setting_key]
        
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{setting_key}"
        self._attr_icon = "mdi:scale-balance"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_mode = NumberMode.SLIDER
        
        # Set limits from config
        self._attr_native_min_value = self._config.get("min", -15)
        self._attr_native_max_value = self._config.get("max", 15)
        self._attr_native_step = 1

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
            
        return self.coordinator.data.get(self._setting_key)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        success = await self.coordinator.async_write_register(
            self._config["address"],
            int(value)
        )
        
        if not success:
            _LOGGER.error("Failed to set %s to %s", self._setting_key, value)

class BrinkGeoTemperatureNumber(BrinkControlEntity, NumberEntity):
    """BRINK geo heat exchanger temperature number entity."""

    def __init__(
        self,
        coordinator: BrinkCoordinator,
        entry: ConfigEntry,
        setting_key: str,
        name: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry)
        self._setting_key = setting_key
        self._config = HOLDING_REGISTERS[setting_key]
        
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{setting_key}"
        self._attr_icon = "mdi:thermometer"
        self._attr_native_unit_of_measurement = "°C"
        self._attr_mode = NumberMode.BOX
        
        # Set limits from config
        self._attr_native_min_value = self._config.get("min", 0)
        self._attr_native_max_value = self._config.get("max", 400)
        self._attr_native_step = 1

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
            
        return self.coordinator.data.get(self._setting_key)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        success = await self.coordinator.async_write_register(
            self._config["address"],
            int(value)
        )
        
        if not success:
            _LOGGER.error("Failed to set %s to %s", self._setting_key, value)
