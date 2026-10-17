"""Construction and validation of BRINK Modbus transports."""
from __future__ import annotations

import inspect
import ipaddress
import re
from collections.abc import Mapping
from typing import Any

from homeassistant.const import CONF_HOST, CONF_PORT
from pymodbus import FramerType
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient

from .const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_SERIAL_PORT,
    CONNECTION_TYPE_RTU_OVER_TCP,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPES,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DEFAULT_TCP_PORT,
)

DEFAULT_TIMEOUT = 5
DEFAULT_RETRIES = 1
RECONNECT_DELAY = 1
RECONNECT_DELAY_MAX = 30
_HOSTNAME_RE = re.compile(
    r"(?=.{1,253}\Z)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\Z"
)


def connection_type(config: Mapping[str, Any]) -> str:
    """Get a supported connection type, treating legacy entries as serial."""
    value = config.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_SERIAL)
    if value not in CONNECTION_TYPES:
        raise ValueError(f"Unsupported Modbus connection type: {value!r}")
    return str(value)


def validate_host(host: object) -> str:
    """Validate a TCP hostname or literal IP address without resolving it."""
    if not isinstance(host, str) or not host.strip():
        raise ValueError("A Modbus TCP host is required")

    value = host.strip()
    try:
        ipaddress.ip_address(value)
    except ValueError:
        if not _HOSTNAME_RE.fullmatch(value):
            raise ValueError("Invalid Modbus TCP host name") from None
    return value


def validate_tcp_port(value: object) -> int:
    """Validate a TCP port."""
    try:
        port = int(value)
    except (TypeError, ValueError) as err:
        raise ValueError("Modbus TCP port must be a number") from err
    if not 1 <= port <= 65535:
        raise ValueError("Modbus TCP port must be between 1 and 65535")
    return port


def validate_slave_id(value: object) -> int:
    """Validate a Modbus RTU device address."""
    try:
        slave_id = int(value)
    except (TypeError, ValueError) as err:
        raise ValueError("Modbus slave ID must be a number") from err
    if not 1 <= slave_id <= 247:
        raise ValueError("Modbus slave ID must be between 1 and 247")
    return slave_id


def validate_transport_config(config: Mapping[str, Any]) -> None:
    """Validate the parts of a config entry used to create a client."""
    transport = connection_type(config)
    validate_slave_id(config.get("slave_id", 20))
    if transport == CONNECTION_TYPE_SERIAL:
        serial_port = config.get(CONF_SERIAL_PORT)
        if not isinstance(serial_port, str) or not serial_port.strip():
            raise ValueError("A serial device path is required")
        try:
            baudrate = int(config.get(CONF_BAUDRATE, DEFAULT_BAUDRATE))
        except (TypeError, ValueError) as err:
            raise ValueError("Baudrate must be a number") from err
        if baudrate <= 0:
            raise ValueError("Baudrate must be positive")
        return

    validate_host(config.get(CONF_HOST))
    validate_tcp_port(config.get(CONF_PORT, DEFAULT_TCP_PORT))


def create_modbus_client(config: Mapping[str, Any]) -> AsyncModbusSerialClient | AsyncModbusTcpClient:
    """Create an asynchronous client for a validated integration entry.

    TCP uses PyModbus' SOCKET framer, which supplies standard Modbus TCP MBAP
    framing. RTU-over-TCP deliberately selects the RTU framer on the same TCP
    transport for transparent serial servers.
    """
    validate_transport_config(config)
    transport = connection_type(config)

    common = {
        "timeout": DEFAULT_TIMEOUT,
        "retries": DEFAULT_RETRIES,
        "reconnect_delay": RECONNECT_DELAY,
        "reconnect_delay_max": RECONNECT_DELAY_MAX,
    }
    if transport == CONNECTION_TYPE_SERIAL:
        return AsyncModbusSerialClient(
            port=str(config[CONF_SERIAL_PORT]).strip(),
            baudrate=int(config.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)),
            bytesize=DEFAULT_BYTESIZE,
            parity=DEFAULT_PARITY,
            stopbits=DEFAULT_STOPBITS,
            framer=FramerType.RTU,
            **common,
        )

    host = validate_host(config[CONF_HOST])
    port = validate_tcp_port(config.get(CONF_PORT, DEFAULT_TCP_PORT))
    framer = FramerType.SOCKET
    if transport == CONNECTION_TYPE_RTU_OVER_TCP:
        framer = FramerType.RTU
    return AsyncModbusTcpClient(host=host, port=port, framer=framer, **common)


async def async_close_client(client: Any) -> None:
    """Close a PyModbus client across supported 3.x releases."""
    close = getattr(client, "close", None)
    if close is None:
        return
    result = close()
    if inspect.isawaitable(result):
        await result
