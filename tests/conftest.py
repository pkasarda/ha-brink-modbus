"""Test helpers for the BRINK custom integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest


@dataclass
class FakeEntry:
    """Small runtime-compatible config entry used by coordinator/platform tests."""

    data: dict[str, Any]
    entry_id: str = "test-entry"


class FakeHass:
    """The subset of Home Assistant needed for coordinator construction."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}


@pytest.fixture
def tcp_data() -> dict[str, Any]:
    """A safe TCP configuration for tests."""
    return {
        "connection_type": "tcp",
        "host": "192.0.2.20",
        "port": 502,
        "slave_id": 20,
        "model": "flair_400",
        "control_enabled": False,
    }
