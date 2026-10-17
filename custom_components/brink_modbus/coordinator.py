"""Data update coordinator for a BRINK HRU."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.exceptions import ConnectionException, ModbusException, ModbusIOException
from pymodbus.pdu import ExceptionResponse

from .const import (
    CONF_CONTROL_ENABLED,
    CONF_MODEL,
    CONF_SERIAL_PORT,
    CONNECTION_TYPE_SERIAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    HOLDING_REGISTERS,
    INPUT_REGISTERS,
    SCAN_INTERVAL_FAST,
)
from .transport import (
    async_close_client,
    connection_type,
    create_modbus_client,
    validate_slave_id,
)

_LOGGER = logging.getLogger(__name__)


class _TransportFailure(Exception):
    """A timeout, socket error, or unusable Modbus response."""


def _contiguous_blocks(
    registers: Iterable[tuple[str, dict[str, Any]]],
) -> list[list[tuple[str, dict[str, Any]]]]:
    """Group only exactly contiguous known register definitions."""
    blocks: list[list[tuple[str, dict[str, Any]]]] = []
    for name, config in sorted(registers, key=lambda item: item[1]["address"]):
        if blocks and config["address"] == blocks[-1][-1][1]["address"] + 1:
            blocks[-1].append((name, config))
        else:
            blocks.append([(name, config)])
    return blocks


def _register_value(raw_value: int, config: dict[str, Any]) -> float | int:
    """Apply Brink's documented signed encoding and optional scaling."""
    value = raw_value
    if config.get("signed") and value >= 0x8000:
        value -= 0x10000
    if "scale" in config:
        return value * config["scale"]
    return value


class BrinkCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate serialized, resilient Modbus access to one BRINK unit."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator and its transport client."""
        self.entry = entry
        self.hass = hass
        self.connection_type = connection_type(entry.data)
        self.slave_id = validate_slave_id(entry.data.get("slave_id", DEFAULT_SLAVE_ID))
        self.model = entry.data.get(CONF_MODEL)
        # Entries created before monitoring-only mode deliberately preserve
        # their ability to control the unit. New entries store False explicitly.
        self.control_enabled = bool(entry.data.get(CONF_CONTROL_ENABLED, True))
        self.client = create_modbus_client(entry.data)
        self._transaction_lock = asyncio.Lock()
        self._last_connection_error: str | None = None

        if self.connection_type == CONNECTION_TYPE_SERIAL:
            self.port = str(entry.data[CONF_SERIAL_PORT])
            self.connection_description = self.port
        else:
            self.port = str(entry.data[CONF_HOST])
            self.connection_description = (
                f"{entry.data[CONF_HOST]}:{entry.data.get(CONF_PORT, 502)}"
            )

        _LOGGER.debug(
            "Initialized BRINK coordinator (%s, slave ID %s, controls=%s)",
            self.connection_type,
            self.slave_id,
            self.control_enabled,
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_FAST),
        )

    def _log_connection_failure(self, err: Exception | str) -> None:
        """Log an offline transport once until a subsequent successful read."""
        message = str(err)
        if message != self._last_connection_error:
            _LOGGER.warning("BRINK Modbus transport unavailable: %s", message)
            self._last_connection_error = message

    async def _async_ensure_connected(self) -> None:
        """Connect a client when needed, with PyModbus' bounded backoff."""
        if getattr(self.client, "connected", False):
            return
        try:
            connected = await self.client.connect()
        except (ConnectionException, OSError, TimeoutError) as err:
            raise _TransportFailure(f"Could not connect to {self.connection_description}") from err
        except Exception as err:  # PyModbus may wrap socket errors per transport.
            raise _TransportFailure(f"Could not connect to {self.connection_description}") from err

        if connected is False or not getattr(self.client, "connected", False):
            raise _TransportFailure(f"Could not connect to {self.connection_description}")

    async def _async_read_block(
        self,
        register_type: str,
        block: list[tuple[str, dict[str, Any]]],
    ) -> dict[str, float | int]:
        """Read one known contiguous block and map values to entity keys."""
        address = block[0][1]["address"]
        count = len(block)
        try:
            if register_type == "input":
                result = await self.client.read_input_registers(
                    address, count=count, device_id=self.slave_id
                )
            else:
                result = await self.client.read_holding_registers(
                    address, count=count, device_id=self.slave_id
                )
        except (ConnectionException, ModbusIOException, OSError, TimeoutError) as err:
            raise _TransportFailure(
                f"Read failed at {address} through {self.connection_description}"
            ) from err
        except ModbusException as err:
            raise _TransportFailure(f"Modbus read failed at {address}") from err
        except Exception as err:
            raise _TransportFailure(f"Read failed at {address}") from err

        if result is None or result.isError():
            # An explicit Modbus exception is a response from a healthy device,
            # usually for an optional/unsupported setting. Keep other sensors
            # available. Timeouts and I/O failures are not ExceptionResponse.
            if isinstance(result, ExceptionResponse):
                _LOGGER.debug("BRINK rejected read at register %s: %s", address, result)
                return {}
            raise _TransportFailure(f"No usable Modbus response at register {address}")

        registers = getattr(result, "registers", None)
        if registers is None or len(registers) != count:
            raise _TransportFailure(f"Incomplete Modbus response at register {address}")

        return {
            name: _register_value(registers[index], config)
            for index, (name, config) in enumerate(block)
        }

    async def _async_read_mapped_registers(
        self,
        register_type: str,
        registers: Iterable[tuple[str, dict[str, Any]]],
    ) -> dict[str, float | int]:
        """Read mapped registers while allowing isolated optional failures."""
        data: dict[str, float | int] = {}
        for block in _contiguous_blocks(registers):
            data.update(await self._async_read_block(register_type, block))
        return data

    @staticmethod
    def _polled_holding_registers() -> Iterable[tuple[str, dict[str, Any]]]:
        """Return all non-action holding values used by entities."""
        return (
            (name, config)
            for name, config in HOLDING_REGISTERS.items()
            if name not in {"slave_address", "device_reset"}
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Read current values without performing any writes."""
        try:
            async with self._transaction_lock:
                try:
                    await self._async_ensure_connected()
                    data = await self._async_read_mapped_registers("input", INPUT_REGISTERS.items())
                    data.update(
                        await self._async_read_mapped_registers(
                            "holding", self._polled_holding_registers()
                        )
                    )
                except _TransportFailure:
                    # Close while holding the bus lock so a concurrent command
                    # cannot reconnect between a failed request and cleanup.
                    await async_close_client(self.client)
                    raise
        except _TransportFailure as err:
            self._log_connection_failure(err)
            raise UpdateFailed(str(err)) from err

        if not data:
            err = _TransportFailure("BRINK returned no readable registers")
            self._log_connection_failure(err)
            raise UpdateFailed(str(err))

        self._last_connection_error = None
        return data

    async def async_write_register(self, address: int, value: int) -> bool:
        """Perform one user-authorized holding-register write.

        The coordinator never calls this from setup, reconnect, validation, or
        polling. A refresh happens after releasing the transaction lock, so a
        write cannot deadlock its own follow-up read.
        """
        if not self.control_enabled:
            _LOGGER.warning("Ignoring BRINK write to %s: controls are disabled", address)
            return False

        try:
            async with self._transaction_lock:
                try:
                    await self._async_ensure_connected()
                    result = await self.client.write_register(
                        address, value=value, device_id=self.slave_id
                    )
                    if result is None or result.isError():
                        _LOGGER.warning("BRINK rejected write to register %s: %s", address, result)
                        return False
                except Exception:
                    await async_close_client(self.client)
                    raise
        except (ConnectionException, ModbusException, OSError, TimeoutError) as err:
            self._log_connection_failure(err)
            return False
        except Exception as err:  # noqa: BLE001 - PyModbus may wrap socket errors.
            self._log_connection_failure(err)
            return False

        # This is intentionally outside the lock; async_request_refresh invokes
        # _async_update_data, which acquires the same lock.
        await self.async_request_refresh()
        return True

    async def async_read_all_registers(self) -> dict[str, Any]:
        """Read known mapped registers for diagnostics without writing."""
        try:
            async with self._transaction_lock:
                try:
                    await self._async_ensure_connected()
                    input_data = await self._async_read_mapped_registers(
                        "input", INPUT_REGISTERS.items()
                    )
                    holding_data = await self._async_read_mapped_registers(
                        "holding", HOLDING_REGISTERS.items()
                    )
                except _TransportFailure:
                    await async_close_client(self.client)
                    raise
        except _TransportFailure as err:
            self._log_connection_failure(err)
            return {}

        return {
            **{f"input_{name}": value for name, value in input_data.items()},
            **{f"holding_{name}": value for name, value in holding_data.items()},
        }

    async def disconnect(self) -> None:
        """Close the transport and release its serial port or socket."""
        async with self._transaction_lock:
            try:
                await async_close_client(self.client)
                _LOGGER.debug("Closed BRINK Modbus connection for %s", self.connection_description)
            except Exception as err:  # noqa: BLE001 - cleanup must not block unloading.
                _LOGGER.debug("Error closing BRINK Modbus connection: %s", err)
