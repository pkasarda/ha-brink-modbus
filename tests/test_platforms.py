"""Smoke tests for all entity platforms."""
from __future__ import annotations

import pytest

from custom_components.brink_modbus import binary_sensor, number, select, sensor, switch
from custom_components.brink_modbus.const import DOMAIN
from tests.conftest import FakeEntry, FakeHass


class PlatformCoordinator:
    """Enough coordinator state to construct platform entities."""

    def __init__(self) -> None:
        self.data = {"software_version": 1, "modbus_control": 0}
        self.last_update_success = True
        self.control_enabled = False
        self.model = "flair_400"


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", [sensor, binary_sensor, number, select, switch])
async def test_all_platforms_create_entities(platform: object) -> None:
    hass = FakeHass()
    entry = FakeEntry({"model": "flair_400"})
    hass.data[DOMAIN] = {entry.entry_id: PlatformCoordinator()}
    added: list[object] = []

    await platform.async_setup_entry(hass, entry, added.extend)  # type: ignore[attr-defined]

    assert added
