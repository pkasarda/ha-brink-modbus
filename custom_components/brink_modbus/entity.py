"""Base entity for BRINK HRU integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, SUPPORTED_MODELS
from .coordinator import BrinkCoordinator


class BrinkEntity(CoordinatorEntity[BrinkCoordinator]):
    """Base entity for BRINK HRU."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BrinkCoordinator, entry: ConfigEntry) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._entry = entry
        
        # Set device info once for all entities
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"BRINK {SUPPORTED_MODELS.get(entry.data.get('model', 'unknown'), 'HRU')}",
            "manufacturer": MANUFACTURER,
            "model": SUPPORTED_MODELS.get(entry.data.get("model", "unknown"), "Unknown"),
        }
        # Derived by the coordinator from registers 4000-4012 when the unit reports them.
        data = coordinator.data or {}
        if data.get("software_version"):
            self._attr_device_info["sw_version"] = data["software_version"]
        if data.get("serial_number"):
            self._attr_device_info["serial_number"] = data["serial_number"]


class BrinkControlEntity(BrinkEntity):
    """Base for a writable entity that honours monitoring-only mode."""

    @property
    def available(self) -> bool:
        """Controls are unavailable until the user explicitly enables them."""
        return self.coordinator.control_enabled and super().available

    async def _async_write(self, address: int, value: int) -> None:
        """Write one register; raise so the UI and automations see a failure."""
        if not await self.coordinator.async_write_register(address, value):
            raise HomeAssistantError(f"BRINK did not accept the write to register {address}")

    async def _async_ensure_control_mode(self, mode: int) -> None:
        """Make sure register 8000 allows the following write, or raise."""
        if not await self.coordinator.async_ensure_control_mode(mode):
            raise HomeAssistantError(
                f"BRINK Modbus control mode must be {mode}; select it or enable automatic switching"
            )

