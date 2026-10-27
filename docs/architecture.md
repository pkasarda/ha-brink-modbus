# Architecture

## Data flow
`__init__.py` creates one `BrinkCoordinator` per config entry (`hass.data[DOMAIN][entry_id]`), forwards the platforms, and registers the services once, for the first entry.

`transport.py` holds the pure helpers: it validates the config and builds the PyModbus client. The client is `AsyncModbusSerialClient` for `serial`, or `AsyncModbusTcpClient` with the `SOCKET` framer for `tcp` or the `RTU` framer for `rtu_over_tcp`. An entry without `connection_type` is a pre-2.7 serial entry.

`coordinator.py` is a `DataUpdateCoordinator` that polls every `SCAN_INTERVAL_FAST` seconds:
- It reads `INPUT_REGISTERS` and `HOLDING_REGISTERS` from `const.py`, grouping contiguous addresses into one request. Values marked `"signed": True` are converted from int16, `"scale"` is applied, and `"words": 2` combines two registers (high word first) into an unsigned 32-bit value.
- A Modbus exception reply (unsupported register on this firmware) is retried register by register, so it never hides its neighbours. The rejected address goes into `unsupported_registers` and is skipped until reload; diagnostics show the set. Timeouts and I/O errors are transport failures instead: the client is closed and the update fails.
- `UNPOLLED_HOLDING_REGISTERS` (7991 bus address, 8010 filter reset, 8011 device reset) are never read. Reading 8010/8011 clears their last result.
- After each poll `_derived_values()` builds `software_version` (4000-4002) and the BCD `serial_number` (4010-4012). `BrinkEntity` puts both into the device info.
- One `asyncio.Lock` serialises every transaction (polls and writes). After a failure the client is closed and reconnected on the next poll.
- `async_write_register()` is the only write path. It refuses writes when `control_enabled` is False and requests a refresh after releasing the lock, so it cannot deadlock.
- `async_ensure_control_mode(mode)` returns True if register 8000 already holds `mode`. Otherwise, with `auto_control_mode` on, it writes 8000, waits 0.5 s and returns True. With it off, it returns False.

Entities (`sensor`, `binary_sensor`, `number`, `select`, `switch`, `button`) only read `coordinator.data` and call the coordinator for writes. `BrinkControlEntity` is unavailable while controls are disabled.

## Control mode (register 8000)
| 8000 | Meaning | Unlocks |
| --- | --- | --- |
| 0 | Disabled; the unit runs on its own (wall switch, CO₂ sensors) | nothing |
| 1 | Switch control | 8001 power switch position |
| 2 | Flow control | 8002 flow setpoint (0 or 50 to the model maximum) |

A power loss resets 8000 to 0. `auto_control_mode` exists so automations that set the flow setpoint retake control without having to set the mode themselves. With the option on, the flow-setpoint number and the power-switch select stay available in every mode. With it off, they are available only in their own mode.

## Config entry keys
`connection_type`, `port` (serial path or TCP port), `host`, `baudrate`, `slave_id`, `model`, `control_enabled`, `auto_control_mode`. See the "Always" rules in `AGENTS.md` for the legacy defaults.

## Services
`set_bypass_mode`, `set_flow_speed`, `set_power_mode`, `reset_device` and `read_all_registers` take an optional `config_entry_id`; without it they use the first entry. Do not add `target:` to `services.yaml`, because hassfest rejects device filters there.

## Register definitions (`const.py`)
Every entry has `address` and `type`. The optional keys are documented at the top of the map: `entity: False`, `words`, `map` (name of a value map in `const.py`; the sensor becomes an ENUM text sensor), `category`, `enabled`, `state_class`, plus `min`/`max`/`step` in user units for writable settings. Register meanings come from the BRINK *Modbus UWA2-B/UWA2-E* document (614882). The Flair 325 manual, chapter 14, documents only a subset. Some firmware reports humidity in whole percent, although the UWA2-B document says tenths.
