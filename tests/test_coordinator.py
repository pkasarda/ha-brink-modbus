"""Coordinator transport, resilience, concurrency, and safety tests."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from pymodbus.pdu import ExceptionResponse

from custom_components.brink_modbus import coordinator as coordinator_module
from custom_components.brink_modbus.const import HOLDING_REGISTERS, INPUT_REGISTERS
from custom_components.brink_modbus.coordinator import BrinkCoordinator
from tests.conftest import FakeEntry, FakeHass


class Response:
    """Minimal successful response compatible with the PyModbus API in use."""

    def __init__(self, registers: list[int]) -> None:
        self.registers = registers

    def isError(self) -> bool:
        return False


class ErrorResponse:
    """A non-Modbus-exception error response, used to model timeouts."""

    def isError(self) -> bool:
        return True


class Client:
    """Async client double with transaction instrumentation."""

    def __init__(self, connected: bool = True, fail_reads: bool = False) -> None:
        self.connected = connected
        self.fail_reads = fail_reads
        self.connect_calls = 0
        self.close_calls = 0
        self.input_calls: list[tuple[int, int, int]] = []
        self.holding_calls: list[tuple[int, int, int]] = []
        self.write_calls: list[tuple[int, int, int]] = []
        self.active_transactions = 0
        self.maximum_active_transactions = 0

    async def connect(self) -> bool:
        self.connect_calls += 1
        self.connected = True
        return True

    async def _response(self, address: int, count: int) -> Response | ErrorResponse:
        self.active_transactions += 1
        self.maximum_active_transactions = max(self.maximum_active_transactions, self.active_transactions)
        try:
            await asyncio.sleep(0)
            if self.fail_reads:
                return ErrorResponse()
            return Response([address + offset for offset in range(count)])
        finally:
            self.active_transactions -= 1

    async def read_input_registers(self, address: int, *, count: int, device_id: int) -> Response | ErrorResponse:
        self.input_calls.append((address, count, device_id))
        return await self._response(address, count)

    async def read_holding_registers(self, address: int, *, count: int, device_id: int) -> Response | ErrorResponse:
        self.holding_calls.append((address, count, device_id))
        return await self._response(address, count)

    async def write_register(self, address: int, *, value: int, device_id: int) -> Response:
        self.write_calls.append((address, value, device_id))
        self.active_transactions += 1
        self.maximum_active_transactions = max(self.maximum_active_transactions, self.active_transactions)
        try:
            await asyncio.sleep(0)
            return Response([])
        finally:
            self.active_transactions -= 1

    def close(self) -> None:
        self.close_calls += 1
        self.connected = False


class RejectingClient(Client):
    """Answer a Modbus exception for any request that covers a rejected address."""

    def __init__(self, rejected: set[int]) -> None:
        super().__init__()
        self.rejected = rejected

    async def read_input_registers(self, address: int, *, count: int, device_id: int) -> Any:
        if self.rejected & set(range(address, address + count)):
            self.input_calls.append((address, count, device_id))
            return ExceptionResponse(4, 2)
        return await super().read_input_registers(address, count=count, device_id=device_id)


def _make_coordinator(
    monkeypatch: pytest.MonkeyPatch,
    client: Client,
    tcp_data: dict[str, Any],
    *,
    control_enabled: bool = False,
    extra: dict[str, Any] | None = None,
) -> BrinkCoordinator:
    monkeypatch.setattr(coordinator_module, "create_modbus_client", lambda data: client)
    return BrinkCoordinator(
        FakeHass(),
        FakeEntry({**tcp_data, "control_enabled": control_enabled, **(extra or {})}),
    )


@pytest.mark.asyncio
async def test_tcp_reads_input_and_holding_registers(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client()
    coordinator = _make_coordinator(monkeypatch, client, tcp_data)

    data = await coordinator._async_update_data()

    assert data["device_type"] == 4004
    assert data["modbus_control"] == 8000
    assert all(call[2] == 20 for call in client.input_calls + client.holding_calls)
    assert client.write_calls == []


@pytest.mark.asyncio
async def test_32bit_values_combine_high_word_first(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client()
    coordinator = _make_coordinator(monkeypatch, client, tcp_data)

    data = await coordinator._async_update_data()

    # The fake client answers each register with its own address.
    assert data["operating_time"] == (4113 << 16) | 4114
    assert data["filter_usage_hours"] == 4115


@pytest.mark.asyncio
async def test_action_registers_are_never_read(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client()
    coordinator = _make_coordinator(monkeypatch, client, tcp_data)

    await coordinator._async_update_data()

    read = {
        address + offset
        for address, count, _ in client.holding_calls
        for offset in range(count)
    }
    # Reading 8010/8011 clears their last result; 7991 is the bus address.
    assert not read & {7991, 8010, 8011}
    assert 8003 in read


@pytest.mark.asyncio
async def test_unsupported_register_does_not_hide_its_block(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = RejectingClient(rejected={4030})
    coordinator = _make_coordinator(monkeypatch, client, tcp_data)

    data = await coordinator._async_update_data()

    assert "supply_fan_status" not in data
    assert data["supply_volume_setpoint"] == 4031
    assert data["supply_volume_actual"] == 4032

    # The rejected address is remembered and not requested on the next poll.
    client.input_calls.clear()
    await coordinator._async_update_data()
    assert coordinator.unsupported_registers == {4030}
    assert all(address != 4030 for address, _, _ in client.input_calls)


def test_serial_number_and_software_version_are_decoded() -> None:
    derived = coordinator_module._derived_values(
        {
            "serial_number_1": 0x4300,
            "serial_number_2": 0x1222,
            "serial_number_3": 0x3701,
            "software_version_type": (ord("S") << 8) | 1,
            "software_version_minor": (2 << 8) | 3,
            "software_version_build": 4567,
        }
    )

    assert derived == {
        "serial_number": "430012223701",
        "software_version": "S1.02.03 build 4567",
    }
    # A non-BCD word is not reported as a serial number.
    assert "serial_number" not in coordinator_module._derived_values(
        {"serial_number_1": 0x4A00, "serial_number_2": 0, "serial_number_3": 0}
    )


@pytest.mark.asyncio
async def test_disconnected_client_reconnects_and_subsequent_poll_succeeds(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client(connected=False)
    coordinator = _make_coordinator(monkeypatch, client, tcp_data)

    first = await coordinator._async_update_data()
    second = await coordinator._async_update_data()

    assert first["device_type"] == 4004
    assert second["device_type"] == 4004
    assert client.connect_calls == 1


@pytest.mark.asyncio
async def test_failed_reads_make_update_unavailable_and_close_transport(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client(fail_reads=True)
    coordinator = _make_coordinator(monkeypatch, client, tcp_data)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert client.close_calls == 1


@pytest.mark.asyncio
async def test_monitoring_mode_blocks_writes_and_never_enables_modbus_control(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client()
    coordinator = _make_coordinator(monkeypatch, client, tcp_data, control_enabled=False)

    assert not await coordinator.async_write_register(8000, 2)
    assert not await coordinator.async_write_register(8002, 200)
    assert client.write_calls == []


@pytest.mark.asyncio
async def test_explicit_control_write_uses_slave_and_refreshes_without_deadlock(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client()
    coordinator = _make_coordinator(monkeypatch, client, tcp_data, control_enabled=True)
    coordinator.async_request_refresh = coordinator._async_update_data  # type: ignore[method-assign]

    assert await asyncio.wait_for(coordinator.async_write_register(8000, 0), timeout=1)
    assert client.write_calls == [(8000, 0, 20)]


@pytest.mark.asyncio
async def test_auto_control_mode_writes_8000_once_before_target(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client()
    coordinator = _make_coordinator(
        monkeypatch, client, tcp_data, control_enabled=True, extra={"auto_control_mode": True}
    )
    coordinator.async_request_refresh = AsyncMock()  # type: ignore[method-assign]
    monkeypatch.setattr(coordinator_module.asyncio, "sleep", AsyncMock())
    coordinator.data = {"modbus_control": 0}

    assert await coordinator.async_ensure_control_mode(2)
    assert await coordinator.async_ensure_control_mode(2)
    assert client.write_calls == [(8000, 2, 20)]


@pytest.mark.asyncio
async def test_auto_control_mode_off_refuses_without_writing(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client()
    coordinator = _make_coordinator(
        monkeypatch, client, tcp_data, control_enabled=True, extra={"auto_control_mode": False}
    )
    coordinator.data = {"modbus_control": 0}

    assert not await coordinator.async_ensure_control_mode(2)
    assert client.write_calls == []


def test_auto_control_mode_defaults(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    legacy = {key: value for key, value in tcp_data.items() if key != "control_enabled"}
    monkeypatch.setattr(coordinator_module, "create_modbus_client", lambda data: Client())

    # Entries from before monitoring-only mode keep both writes and auto-switching.
    assert BrinkCoordinator(FakeHass(), FakeEntry(legacy)).auto_control_mode
    # Monitoring-only entries never switch the control mode.
    assert not BrinkCoordinator(
        FakeHass(), FakeEntry({**tcp_data, "auto_control_mode": True})
    ).auto_control_mode


@pytest.mark.asyncio
async def test_concurrent_poll_and_write_do_not_overlap_transactions(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client()
    coordinator = _make_coordinator(monkeypatch, client, tcp_data, control_enabled=True)
    coordinator.async_request_refresh = AsyncMock()  # type: ignore[method-assign]

    await asyncio.gather(
        coordinator._async_update_data(),
        coordinator.async_write_register(6100, 1),
    )

    assert client.maximum_active_transactions == 1


@pytest.mark.asyncio
async def test_disconnect_closes_client(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, Any]
) -> None:
    client = Client()
    coordinator = _make_coordinator(monkeypatch, client, tcp_data)

    await coordinator.disconnect()

    assert client.close_calls == 1


def test_model_specific_airflow_limits_are_kept_out_of_temperature_settings() -> None:
    from custom_components.brink_modbus.const import get_max_airflow

    assert get_max_airflow("flair_400") == 400
    assert get_max_airflow("flair_325") == 325
    # 6242 is tenths of °C (15.0-40.0 °C per the Brink manual), not an airflow.
    assert HOLDING_REGISTERS["geo_max_temperature"]["max"] == 40.0
    assert HOLDING_REGISTERS["geo_max_temperature"]["scale"] == 0.1
    assert INPUT_REGISTERS["co2_sensor_1"]["address"] == 4201
