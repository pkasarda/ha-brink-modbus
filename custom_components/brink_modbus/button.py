"""BRINK HRU button platform."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
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
    async_add_entities([BrinkFilterResetButton(coordinator, entry)])


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
        if not await self.coordinator.async_write_register(
            HOLDING_REGISTERS["filter_reset"]["address"], 1
        ):
            _LOGGER.error("Failed to reset the filter warning")
