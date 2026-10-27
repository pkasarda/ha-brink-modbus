"""BRINK HRU button platform."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    """Set up BRINK HRU button platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [BrinkFilterResetButton(coordinator, entry), BrinkDeviceResetButton(coordinator, entry)]
    )


class BrinkFilterResetButton(BrinkControlEntity, ButtonEntity):
    """Reset the filter warning and counter after a filter change (8010)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Reset Filter Warning"
        self._attr_unique_id = f"{entry.entry_id}_filter_reset"
        self._attr_icon = "mdi:air-filter"

    async def async_press(self) -> None:
        """Write the reset command; the unit clears 8010 itself."""
        await self._async_write(HOLDING_REGISTERS["filter_reset"]["address"], 1)


class BrinkDeviceResetButton(BrinkControlEntity, ButtonEntity):
    """Restart the unit's controller (8011). The unit returns to Modbus control Disabled."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_name = "Reset Device"
        self._attr_unique_id = f"{entry.entry_id}_device_reset"

    async def async_press(self) -> None:
        """Trigger the appliance reset."""
        _LOGGER.warning("Triggering a user-requested BRINK device reset")
        await self._async_write(HOLDING_REGISTERS["device_reset"]["address"], 1)
