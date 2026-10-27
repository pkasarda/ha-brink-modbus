"""Smoke tests for all entity platforms."""
from __future__ import annotations

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.brink_modbus import (
    binary_sensor,
    button,
    diagnostics,
    number,
    select,
    sensor,
    switch,
)
from custom_components.brink_modbus.const import DOMAIN
from tests.conftest import FakeEntry, FakeHass


class PlatformCoordinator:
    """Enough coordinator state to construct platform entities."""

    def __init__(self) -> None:
        self.data = {
            "software_version": "S1.02.03 build 4567",
            "serial_number": "430012223701",
            "modbus_control": 0,
            "active_function": 12,
        }
        self.last_update_success = True
        self.control_enabled = False
        self.auto_control_mode = False
        self.connection_type = "tcp"
        self.unsupported_registers = {4030}
        self.model = "flair_400"


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", [sensor, binary_sensor, number, select, switch, button])
async def test_all_platforms_create_entities(platform: object) -> None:
    hass = FakeHass()
    entry = FakeEntry({"model": "flair_400"})
    hass.data[DOMAIN] = {entry.entry_id: PlatformCoordinator()}
    added: list[object] = []

    await platform.async_setup_entry(hass, entry, added.extend)  # type: ignore[attr-defined]

    assert added


@pytest.mark.asyncio
async def test_mapped_sensor_and_device_info() -> None:
    hass = FakeHass()
    entry = FakeEntry({"model": "flair_400"})
    hass.data[DOMAIN] = {entry.entry_id: PlatformCoordinator()}
    added: list[object] = []

    await sensor.async_setup_entry(hass, entry, added.extend)

    by_key = {entity.unique_id.removeprefix(f"{entry.entry_id}_"): entity for entity in added}
    assert by_key["active_function"].native_value == "Auto Modbus"
    assert by_key["software_version"].native_value == "S1.02.03 build 4567"
    assert by_key["active_function"].device_info["serial_number"] == "430012223701"
    # Existing unique_ids stay stable.
    assert {"supply_air_temperature", "bypass_state", "flow_setpoint", "software_version"} <= set(by_key)


@pytest.mark.asyncio
async def test_diagnostics_redact_host_and_serial() -> None:
    hass = FakeHass()
    entry = FakeEntry({"model": "flair_400", "host": "192.0.2.20"})
    hass.data[DOMAIN] = {entry.entry_id: PlatformCoordinator()}

    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["host"] == "**REDACTED**"
    assert result["data"]["serial_number"] == "**REDACTED**"
    assert result["data"]["active_function"] == 12


class WritingCoordinator(PlatformCoordinator):
    """Records writes and can simulate a rejected write."""

    def __init__(self, accept: bool = True) -> None:
        super().__init__()
        self.control_enabled = True
        self.accept = accept
        self.writes: list[tuple[int, int]] = []

    async def async_write_register(self, address: int, value: int) -> bool:
        self.writes.append((address, value))
        return self.accept


@pytest.mark.asyncio
async def test_temperature_settings_are_written_in_tenths() -> None:
    coordinator = WritingCoordinator()
    entity = number.BrinkGeoTemperatureNumber(
        coordinator, FakeEntry({"model": "flair_325_plus"}), "bypass_temperature_dwelling", "x"
    )

    await entity.async_set_native_value(22.5)

    assert coordinator.writes == [(6101, 225)]


@pytest.mark.asyncio
async def test_rejected_write_raises_for_ui_and_automations() -> None:
    coordinator = WritingCoordinator(accept=False)
    entity = number.BrinkFilterWarningDaysNumber(coordinator, FakeEntry({"model": "flair_325_plus"}))

    with pytest.raises(HomeAssistantError):
        await entity.async_set_native_value(90)


def test_map_key_is_case_insensitive() -> None:
    from custom_components.brink_modbus.const import BYPASS_MODE_MAP, map_key

    assert map_key(BYPASS_MODE_MAP, "open") == 2
    assert map_key(BYPASS_MODE_MAP, "Closed") == 1
    assert map_key(BYPASS_MODE_MAP, "sideways") is None
