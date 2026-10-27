"""BRINK HRU binary sensor platform."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BrinkCoordinator
from .entity import BrinkEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BRINK HRU binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        BrinkFilterDirtyBinarySensor(coordinator, entry),
        BrinkPreheaterActiveBinarySensor(coordinator, entry),
        BrinkModbusControlActiveBinarySensor(coordinator, entry),
        BrinkImbalanceAllowedBinarySensor(coordinator, entry),
        BrinkGeoHeatExchangerBinarySensor(coordinator, entry),
        BrinkCO2SensorActiveBinarySensor(coordinator, entry),
    ]
    
    async_add_entities(entities)

class BrinkFilterDirtyBinarySensor(BrinkEntity, BinarySensorEntity):
    """BRINK filter dirty binary sensor."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Filter Dirty"
        self._attr_unique_id = f"{entry.entry_id}_filter_dirty"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:air-filter"

    @property
    def is_on(self) -> bool | None:
        """Return true if filter is dirty."""
        if self.coordinator.data is None:
            return None
            
        filter_state = self.coordinator.data.get("filter_state")
        return filter_state == 1  # 1 = dirty

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        if self.is_on:
            return "mdi:air-filter-outline"  # Dirty filter
        return "mdi:air-filter"  # Clean filter

class BrinkPreheaterActiveBinarySensor(BrinkEntity, BinarySensorEntity):
    """BRINK preheater active binary sensor."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Preheater Active"
        self._attr_unique_id = f"{entry.entry_id}_preheater_active"
        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_icon = "mdi:heating-coil"

    @property
    def is_on(self) -> bool | None:
        """Return true if preheater is active."""
        if self.coordinator.data is None:
            return None
            
        preheater_state = self.coordinator.data.get("preheater_state")
        return preheater_state == 2  # 2 = active

class BrinkModbusControlActiveBinarySensor(BrinkEntity, BinarySensorEntity):
    """BRINK Modbus control active binary sensor."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Modbus Control Active"
        self._attr_unique_id = f"{entry.entry_id}_modbus_control_active"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:connection"

    @property
    def is_on(self) -> bool | None:
        """Return true if Modbus control is active."""
        if self.coordinator.data is None:
            return None
            
        modbus_control = self.coordinator.data.get("modbus_control")
        return modbus_control in [1, 2]  # 1 = switch control, 2 = flow control

class BrinkImbalanceAllowedBinarySensor(BrinkEntity, BinarySensorEntity):
    """BRINK imbalance allowed binary sensor."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Imbalance Allowed"
        self._attr_unique_id = f"{entry.entry_id}_imbalance_allowed"
        # Mirrors the switch of the same name; kept for existing installs.
        self._attr_entity_registry_enabled_default = False
        self._attr_icon = "mdi:scale-balance"

    @property
    def is_on(self) -> bool | None:
        """Return true if imbalance is allowed."""
        if self.coordinator.data is None:
            return None
            
        imbalance_allowed = self.coordinator.data.get("imbalance_allowed")
        return imbalance_allowed == 1

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        if self.is_on:
            return "mdi:scale-unbalanced"
        return "mdi:scale-balance"

class BrinkGeoHeatExchangerBinarySensor(BrinkEntity, BinarySensorEntity):
    """BRINK geo heat exchanger binary sensor."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "Geo Heat Exchanger"
        self._attr_unique_id = f"{entry.entry_id}_geo_heat_exchanger"
        # Mirrors the switch of the same name; kept for existing installs.
        self._attr_entity_registry_enabled_default = False
        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_icon = "mdi:heat-pump"

    @property
    def is_on(self) -> bool | None:
        """Return true if geo heat exchanger is enabled."""
        if self.coordinator.data is None:
            return None
            
        geo_exchanger = self.coordinator.data.get("geo_heat_exchanger")
        return geo_exchanger == 1

class BrinkCO2SensorActiveBinarySensor(BrinkEntity, BinarySensorEntity):
    """BRINK CO2 sensor active binary sensor."""

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        
        self._attr_name = "CO2 Sensor Active"
        self._attr_unique_id = f"{entry.entry_id}_co2_sensor_active"
        # Mirrors the switch of the same name; kept for existing installs.
        self._attr_entity_registry_enabled_default = False
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:molecule-co2"

    @property
    def is_on(self) -> bool | None:
        """Return true if CO2 sensor mode is active."""
        if self.coordinator.data is None:
            return None
            
        co2_mode = self.coordinator.data.get("co2_sensor_mode")
        return co2_mode == 1
