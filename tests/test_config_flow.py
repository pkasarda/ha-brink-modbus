"""Configuration schemas and validation tests."""
from __future__ import annotations

import asyncio
from unittest.mock import Mock

import pytest
from homeassistant.data_entry_flow import AbortFlow
from pymodbus.pdu import ExceptionResponse

from custom_components.brink_modbus import config_flow


class Response:
    """Minimal PyModbus-like successful response."""

    def __init__(self, registers: list[int]) -> None:
        self.registers = registers

    def isError(self) -> bool:
        return False


class ValidationClient:
    """Client double which records all Modbus operations."""

    def __init__(self, response: object | Exception) -> None:
        self.connected = False
        self.response = response
        self.reads: list[tuple[int, int, int]] = []
        self.write_calls: list[object] = []
        self.closed = False

    async def connect(self) -> bool:
        self.connected = True
        return True

    async def read_input_registers(self, address: int, *, count: int, device_id: int) -> object:
        self.reads.append((address, count, device_id))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    async def write_register(self, *args: object, **kwargs: object) -> None:
        self.write_calls.append((args, kwargs))

    def close(self) -> None:
        self.closed = True


def test_connection_type_step_defaults_to_tcp() -> None:
    flow = config_flow.ConfigFlow()
    result = asyncio.run(flow.async_step_user())
    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_connection_type_selection_shows_the_matching_second_form() -> None:
    flow = config_flow.ConfigFlow()

    result = await flow.async_step_user({"connection_type": "serial"})

    assert result["step_id"] == "connection"
    field_names = {str(marker.schema) for marker in result["data_schema"].schema}
    assert "port" in field_names
    assert "baudrate" in field_names


def test_serial_and_tcp_connection_schemas_have_correct_fields() -> None:
    serial_fields = {str(marker.schema) for marker in config_flow.connection_schema("serial").schema}
    tcp_fields = {str(marker.schema) for marker in config_flow.connection_schema("tcp").schema}
    assert "port" in serial_fields
    assert "baudrate" in serial_fields
    assert "host" in tcp_fields
    assert "baudrate" not in tcp_fields


@pytest.mark.asyncio
async def test_tcp_validation_reads_4004_uses_slave_and_never_writes(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, object]
) -> None:
    client = ValidationClient(Response([123]))
    monkeypatch.setattr(config_flow, "create_modbus_client", Mock(return_value=client))

    result = await config_flow.validate_input(None, tcp_data)  # type: ignore[arg-type]

    assert result["device_type"] == 123
    assert client.reads == [(4004, 1, 20)]
    assert client.write_calls == []
    assert client.closed


@pytest.mark.asyncio
async def test_validation_timeout_closes_client(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, object]
) -> None:
    client = ValidationClient(TimeoutError())
    monkeypatch.setattr(config_flow, "create_modbus_client", Mock(return_value=client))

    with pytest.raises(config_flow.CannotConnect):
        await config_flow.validate_input(None, tcp_data)  # type: ignore[arg-type]
    assert client.closed
    assert client.write_calls == []


@pytest.mark.asyncio
async def test_validation_modbus_exception_is_invalid_response(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, object]
) -> None:
    client = ValidationClient(ExceptionResponse(4, 2))
    monkeypatch.setattr(config_flow, "create_modbus_client", Mock(return_value=client))

    with pytest.raises(config_flow.InvalidResponse):
        await config_flow.validate_input(None, tcp_data)  # type: ignore[arg-type]
    assert client.write_calls == []


def test_unique_ids_are_stable_and_distinguish_network_entries(tcp_data: dict[str, object]) -> None:
    assert config_flow.connection_unique_id({"port": "/dev/ttyUSB0", "slave_id": 20}) == "/dev/ttyUSB0_20"
    assert config_flow.connection_unique_id(tcp_data) == "tcp_192.0.2.20_502_20"
    assert config_flow.connection_unique_id({**tcp_data, "port": 1502}) != config_flow.connection_unique_id(tcp_data)


@pytest.mark.asyncio
async def test_config_flow_rejects_an_existing_unique_id(
    monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, object]
) -> None:
    flow = config_flow.ConfigFlow()
    flow.hass = object()  # validate_input is replaced below.
    flow._connection_type = "tcp"
    observed_unique_ids: list[str] = []

    async def fake_validate(_: object, __: dict[str, object]) -> dict[str, object]:
        return {"title": "BRINK FLAIR 400", "device_type": 1}

    async def fake_set_unique_id(value: str) -> None:
        observed_unique_ids.append(value)

    def abort_duplicate() -> None:
        raise AbortFlow("already_configured")

    monkeypatch.setattr(config_flow, "validate_input", fake_validate)
    monkeypatch.setattr(flow, "async_set_unique_id", fake_set_unique_id)
    monkeypatch.setattr(flow, "_abort_if_unique_id_configured", abort_duplicate)

    with pytest.raises(AbortFlow, match="already_configured"):
        await flow.async_step_connection(tcp_data)
    assert observed_unique_ids == ["tcp_192.0.2.20_502_20"]
