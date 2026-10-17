"""Tests for Modbus transport construction and entry compatibility."""
from __future__ import annotations

from unittest.mock import Mock

import pytest
from pymodbus import FramerType
from pymodbus.framer import FramerRTU

from custom_components.brink_modbus import transport


def test_legacy_entry_uses_serial_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client_class = Mock(return_value=object())
    monkeypatch.setattr(transport, "AsyncModbusSerialClient", client_class)

    transport.create_modbus_client({"port": "/dev/ttyUSB0", "slave_id": 20})

    assert client_class.call_args.kwargs["port"] == "/dev/ttyUSB0"
    assert client_class.call_args.kwargs["framer"] is FramerType.RTU
    assert transport.connection_type({"port": "/dev/ttyUSB0"}) == "serial"


def test_new_serial_entry_preserves_8e1(monkeypatch: pytest.MonkeyPatch) -> None:
    client_class = Mock(return_value=object())
    monkeypatch.setattr(transport, "AsyncModbusSerialClient", client_class)

    transport.create_modbus_client(
        {"connection_type": "serial", "port": "/dev/serial/by-id/brink", "baudrate": "19200", "slave_id": 20}
    )

    assert client_class.call_args.kwargs["port"] == "/dev/serial/by-id/brink"
    assert client_class.call_args.kwargs["baudrate"] == 19200
    assert client_class.call_args.kwargs["bytesize"] == 8
    assert client_class.call_args.kwargs["parity"] == "E"
    assert client_class.call_args.kwargs["stopbits"] == 1


def test_tcp_uses_mbap_socket_framer(monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, object]) -> None:
    client_class = Mock(return_value=object())
    monkeypatch.setattr(transport, "AsyncModbusTcpClient", client_class)

    transport.create_modbus_client(tcp_data)

    assert client_class.call_args.kwargs["host"] == "192.0.2.20"
    assert client_class.call_args.kwargs["port"] == 502
    assert client_class.call_args.kwargs["framer"] is FramerType.SOCKET


def test_rtu_over_tcp_uses_rtu_framer(monkeypatch: pytest.MonkeyPatch, tcp_data: dict[str, object]) -> None:
    client_class = Mock(return_value=object())
    monkeypatch.setattr(transport, "AsyncModbusTcpClient", client_class)

    transport.create_modbus_client({**tcp_data, "connection_type": "rtu_over_tcp", "port": 1502})

    assert client_class.call_args.kwargs["framer"] is FramerType.RTU
    assert client_class.call_args.kwargs["port"] == 1502


@pytest.mark.asyncio
async def test_installed_pymodbus_accepts_rtu_framing_on_tcp(tcp_data: dict[str, object]) -> None:
    """Verify the optional mode against the actual pinned PyModbus client."""
    client = transport.create_modbus_client(
        {**tcp_data, "connection_type": "rtu_over_tcp", "port": 1502}
    )
    try:
        assert isinstance(client.ctx.framer, FramerRTU)
    finally:
        client.close()


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"connection_type": "udp", "port": "/dev/ttyUSB0"}, "Unsupported"),
        ({"connection_type": "tcp", "host": "brink.local", "port": 0}, "between 1 and 65535"),
        ({"connection_type": "tcp", "host": "bad host!", "port": 502}, "host"),
        ({"connection_type": "tcp", "host": "brink.local", "port": 502, "slave_id": 248}, "slave ID"),
    ],
)
def test_invalid_transport_settings_are_rejected(config: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        transport.create_modbus_client(config)
