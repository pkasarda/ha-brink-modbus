"""Config flow for the BRINK Modbus integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from pymodbus.exceptions import ConnectionException, ModbusException, ModbusIOException
from pymodbus.pdu import ExceptionResponse

from .const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_CONTROL_ENABLED,
    CONF_MODEL,
    CONF_SERIAL_PORT,
    CONNECTION_TYPE_RTU_OVER_TCP,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_CONNECTION_TYPE,
    DEFAULT_CONTROL_ENABLED,
    DEFAULT_SLAVE_ID,
    DEFAULT_TCP_PORT,
    DOMAIN,
    SUPPORTED_MODELS,
)
from .transport import (
    async_close_client,
    connection_type,
    create_modbus_client,
    validate_host,
    validate_slave_id,
    validate_tcp_port,
    validate_transport_config,
)

_LOGGER = logging.getLogger(__name__)

CONNECTION_OPTIONS = [
    {"value": CONNECTION_TYPE_TCP, "label": "Modbus TCP Gateway"},
    {"value": CONNECTION_TYPE_SERIAL, "label": "Serial RS485"},
    {"value": CONNECTION_TYPE_RTU_OVER_TCP, "label": "RTU-over-TCP Gateway"},
]


def _model_selector() -> SelectSelector:
    """Return the common BRINK model selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=[{"value": key, "label": label} for key, label in SUPPORTED_MODELS.items()],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _common_connection_schema() -> dict[Any, Any]:
    """Build fields shared by serial and network forms."""
    return {
        vol.Required("slave_id", default=DEFAULT_SLAVE_ID): NumberSelector(
            NumberSelectorConfig(min=1, max=247, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_MODEL, default="flair_400"): _model_selector(),
        vol.Required(CONF_CONTROL_ENABLED, default=DEFAULT_CONTROL_ENABLED): BooleanSelector(),
    }


def connection_schema(transport: str) -> vol.Schema:
    """Return the relevant configuration schema for a selected transport."""
    fields = _common_connection_schema()
    if transport == CONNECTION_TYPE_SERIAL:
        fields = {
            vol.Required(CONF_SERIAL_PORT, default="/dev/ttyUSB0"): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(CONF_BAUDRATE, default=str(DEFAULT_BAUDRATE)): SelectSelector(
                SelectSelectorConfig(
                    options=["9600", "19200", "38400", "57600", "115200"],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            **fields,
        }
    else:
        fields = {
            vol.Required(CONF_HOST): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(CONF_PORT, default=DEFAULT_TCP_PORT): NumberSelector(
                NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
            ),
            **fields,
        }
    return vol.Schema(fields)


def connection_unique_id(data: dict[str, Any]) -> str:
    """Return a stable identifier without changing existing serial IDs."""
    transport = connection_type(data)
    slave_id = validate_slave_id(data.get("slave_id", DEFAULT_SLAVE_ID))
    if transport == CONNECTION_TYPE_SERIAL:
        # Keep the exact pre-TCP entry format so existing serial devices retain
        # their config-entry and entity identifiers.
        return f"{data[CONF_SERIAL_PORT]}_{slave_id}"
    host = validate_host(data[CONF_HOST]).lower()
    port = validate_tcp_port(data.get(CONF_PORT, DEFAULT_TCP_PORT))
    return f"{transport}_{host}_{port}_{slave_id}"


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Connect and read the documented read-only appliance-type register."""
    del hass  # Configuration validation is fully asynchronous in PyModbus.
    validate_transport_config(data)
    slave_id = validate_slave_id(data.get("slave_id", DEFAULT_SLAVE_ID))
    client = create_modbus_client(data)
    try:
        try:
            connected = await client.connect()
        except (ConnectionException, ModbusIOException, OSError, TimeoutError) as err:
            raise CannotConnect("Unable to establish a Modbus connection") from err
        if connected is False or not getattr(client, "connected", False):
            raise CannotConnect("Unable to establish a Modbus connection")

        try:
            # Brink Flair manuals specify input register 4004 as Appliance Type.
            # It is read-only and makes validation safe for monitoring installs.
            result = await client.read_input_registers(4004, count=1, device_id=slave_id)
        except (ConnectionException, ModbusIOException, OSError, TimeoutError) as err:
            raise CannotConnect("No response from the BRINK Modbus device") from err
        except ModbusException as err:
            raise CannotConnect("Modbus request failed while reading Appliance Type") from err

        if result is None or result.isError():
            if isinstance(result, ExceptionResponse):
                raise InvalidResponse("The BRINK rejected the Appliance Type register read")
            raise CannotConnect("No usable response from the BRINK Modbus device")
        if not getattr(result, "registers", None):
            raise InvalidResponse("The BRINK returned an empty Appliance Type response")

        return {
            "title": f"BRINK {SUPPORTED_MODELS[data[CONF_MODEL]]}",
            "device_type": result.registers[0],
        }
    finally:
        try:
            await async_close_client(client)
        except Exception as err:  # noqa: BLE001 - validation failure must remain actionable.
            _LOGGER.debug("Error closing BRINK validation client: %s", err)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle configuration for serial and Ethernet BRINK connections."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the two-step flow."""
        super().__init__()
        self._connection_type = DEFAULT_CONNECTION_TYPE

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the Modbus transport before collecting its settings."""
        if user_input is not None:
            try:
                self._connection_type = connection_type(user_input)
            except ValueError:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(
                                CONF_CONNECTION_TYPE, default=DEFAULT_CONNECTION_TYPE
                            ): SelectSelector(
                                SelectSelectorConfig(
                                    options=CONNECTION_OPTIONS,
                                    mode=SelectSelectorMode.DROPDOWN,
                                )
                            )
                        }
                    ),
                    errors={"base": "invalid_connection_type"},
                )
            return await self.async_step_connection()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONNECTION_TYPE, default=DEFAULT_CONNECTION_TYPE): SelectSelector(
                        SelectSelectorConfig(
                            options=CONNECTION_OPTIONS,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate settings for the selected Modbus transport."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**user_input, CONF_CONNECTION_TYPE: self._connection_type}
            try:
                info = await validate_input(self.hass, data)
            except ValueError:
                errors["base"] = "invalid_input"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pragma: no cover - Home Assistant reports details in logs.
                _LOGGER.exception("Unexpected BRINK configuration validation error")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(connection_unique_id(data))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=data)

        schema = connection_schema(self._connection_type)
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id="connection",
            data_schema=schema,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate that the device could not be reached."""


class InvalidResponse(HomeAssistantError):
    """Error to indicate that a connected device did not accept the request."""
