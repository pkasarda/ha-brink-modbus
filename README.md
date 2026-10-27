# BRINK Modbus

[![GitHub Release](https://img.shields.io/github/v/release/pkasarda/ha-brink-modbus?style=for-the-badge)](https://github.com/pkasarda/ha-brink-modbus/releases)
[![Validate](https://img.shields.io/github/actions/workflow/status/pkasarda/ha-brink-modbus/validate.yml?branch=main&style=for-the-badge&label=validate)](https://github.com/pkasarda/ha-brink-modbus/actions/workflows/validate.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://hacs.xyz)
[![License](https://img.shields.io/github/license/pkasarda/ha-brink-modbus?style=for-the-badge)](LICENSE)

A local Home Assistant integration for **BRINK Flair** heat-recovery ventilation units. It talks to the unit's UWA2-B controller directly over Modbus and needs no BRINK cloud account.

- Works with **RS485 (USB adapter)**, a **Modbus TCP gateway**, or **RTU-over-TCP**.
- Starts **monitoring-only**: it never writes to the unit until you allow it.
- Reports over 40 values: temperatures, airflow, pressures, fan speeds, bypass, preheater and frost state, filter, operating time and CO₂.
- Controls flow, wall-switch position, bypass mode and thresholds, standby, the filter reset, and the geo heat exchanger.
- Includes English, Slovak, Czech and Polish translations, diagnostics download, and tests in CI.

## Supported devices

| Model | Remote flow range (register 8002) | Status |
| --- | --- | --- |
| Flair 325 / 325 Plus | 0 or 50–325 m³/h | Tested (325 Plus, RS485) |
| Flair 350 | 0 or 50–350 m³/h | Expected to work, untested |
| Flair 400 | 0 or 50–400 m³/h | Expected to work, untested by the maintainer |

Rebranded units with the same UWA2-B controller (for example Wolf CWL) may work too. If you test one, please [open an issue](https://github.com/pkasarda/ha-brink-modbus/issues).

Some registers exist only on newer firmware or with extension modules. When the unit rejects one, it is skipped and every other entity keeps working. **Download diagnostics** lists the registers that were skipped.

## Connections

| Connection | Home Assistant client | Use it for |
| --- | --- | --- |
| Serial RS485 | `AsyncModbusSerialClient`, RTU framing | A local USB-RS485 adapter |
| Modbus TCP gateway | `AsyncModbusTcpClient`, standard MBAP framing | A Modbus TCP-to-RTU gateway such as Waveshare RS485 TO POE ETH (B) |
| RTU-over-TCP | `AsyncModbusTcpClient`, RTU framing | A transparent TCP serial server that carries raw RTU frames |

The BRINK bus settings are 19200 baud, 8 data bits, even parity, 1 stop bit (8E1), slave ID 20. The 4-position wall switch and Modbus control cannot run at the same time.

### Waveshare RS485 TO POE ETH (B)

Use an Ethernet network with an IEEE 802.3af PoE switch/injector, or power the gateway from its supported DC input. Connect the BRINK RS485 bus to the gateway’s isolated RS485 interface according to the BRINK and Waveshare wiring diagrams. Keep A/B polarity consistent; connect signal ground only when the equipment documentation calls for it. Fit bus termination only at the two physical ends of the RS485 run.

1. Put the gateway in **Modbus TCP to RTU** conversion mode (**Modbus TCP Protocol** or **Modbus TCP<->RTU** in Waveshare tools).
2. Set it to **TCP server** mode on port **502**.
3. Set RS485 to **19200 baud, 8E1**, no flow control.

Transparent TCP relays raw RTU frames including the CRC. Choose **RTU-over-TCP** only for a gateway deliberately configured that way.

## Installation

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pkasarda&repository=ha-brink-modbus&category=integration)

**HACS:**
1. Use the button above, or in HACS add `https://github.com/pkasarda/ha-brink-modbus` as a custom repository (type *Integration*).
2. Download **BRINK Modbus** and restart Home Assistant.

**Manual:** copy `custom_components/brink_modbus` into your `config/custom_components/` folder and restart Home Assistant.

Requires Home Assistant 2025.1 or newer. The brand icons need 2026.3 or newer.

## Configuration

[![Open your Home Assistant instance and start setting up BRINK Modbus.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=brink_modbus)

Go to **Settings → Devices & services → Add integration → BRINK Modbus**. Choose the connection type, then fill in:

| Field | Description |
| --- | --- |
| Port (serial) | Serial device; prefer a stable `/dev/serial/by-id/...` path. |
| Baudrate (serial) | 19200 unless the unit was changed. |
| Host / Port (TCP) | Gateway IP or hostname and TCP port, normally 502. |
| Modbus slave ID | Unit address, normally 20. |
| BRINK model | Sets the airflow limits for the controls. |
| Enable writable controls | Off = monitoring only. Nothing is ever written to the unit. |
| Switch Modbus control mode automatically | When on, setting the flow setpoint or switch position first selects the matching Modbus control mode. See [Control mode](#control-mode-register-8000). |

Setup reads the Appliance Type register (4004) once to verify the connection, and refuses a second entry for the same unit.

## Entities

Entities belong to one device per unit. Under **Diagnostics** the device page shows the software version and serial number read from the unit.

| Group | Entities |
| --- | --- |
| Air | Supply/exhaust/outside temperature, supply/exhaust humidity, supply/exhaust pressure, supply/exhaust airflow setpoint and actual, fan RPM |
| State | Active function, ventilation mode, wall-switch position (Flow Switch Position), bypass state, preheater state and power, frost status, frost heater power, frost fan reduction, filter state, filter dirty, filter usage hours |
| CO₂ | CO₂ sensors 1–4 (ppm); their status sensors are disabled by default |
| Controls | Modbus control mode, flow setpoint, power switch position, bypass mode, standby |
| Settings (configuration) | Flow levels 0–3, imbalance allowed and offsets, bypass temperatures (dwelling, outside, hysteresis), filter warning days, CO₂ sensor mode, geo heat exchanger and its temperatures, Reset Filter Warning button |
| Diagnostics | Software version, device type, serial number words, operating time, fan status, fan control type (disabled by default) |

While writable controls are off, every control and setting is unavailable and all monitoring entities keep working.

### Control mode (register 8000)

| Value | Meaning | Unlocks |
| --- | --- | --- |
| Disabled (0) | The unit runs on its own: wall switch, CO₂ sensors | – |
| Switch Control (1) | Home Assistant chooses the switch position | Power Switch Position (8001) |
| Flow Control (2) | Home Assistant sets the airflow | Flow Setpoint (8002) |

The unit resets register 8000 to **Disabled** after a power loss. With **Switch Modbus control mode automatically** on, the next flow or switch command takes control again by itself. With it off, select the mode yourself first. Select **Disabled** to hand control back to the unit. This matters with BRINK wireless CO₂ sensors: in Disabled mode the unit keeps regulating ventilation when Home Assistant or the network is down.

## Actions

All actions accept an optional `config_entry_id`. Without it they use the first BRINK unit. They fail with a clear error while writable controls are off.

| Action | Data | Notes |
| --- | --- | --- |
| `brink_modbus.set_flow_speed` | `speed`: 0 or 50 to the model maximum (m³/h) | Needs Flow Control (or automatic switching) |
| `brink_modbus.set_power_mode` | `mode`: absence / low / normal / high | Needs Switch Control (or automatic switching) |
| `brink_modbus.set_bypass_mode` | `mode`: automatic / closed / open | |
| `brink_modbus.reset_device` | – | Restarts the unit's controller |
| `brink_modbus.read_all_registers` | – | Fires a `brink_modbus_diagnostics` event with all mapped registers; read-only |

## Data updates

The integration polls every 10 seconds. One lock serialises all bus traffic, so polls and commands never overlap, and contiguous registers are read in one request. A register the unit rejects is skipped until the integration reloads. When the connection fails, the entities become unavailable, a single warning is logged, and the integration reconnects on the next poll.

## Examples

**Boost ventilation while cooking** (with automatic control-mode switching on):

```yaml
automation:
  - alias: Kitchen boost
    triggers:
      - trigger: state
        entity_id: binary_sensor.cooker_hood
        to: "on"
    actions:
      - action: number.set_value
        target:
          entity_id: number.brink_flair_325_plus_flow_setpoint
        data:
          value: 250
```

**Filter reminder:** notify when `binary_sensor.<unit>_filter_dirty` turns on. After replacing the filter, press **Reset Filter Warning**.

**Free cooling at night:** set **Bypass Mode** to *Open* when it is cooler outside than inside, and to *Automatic* again in the morning.

## Known limitations

- The unit stores the control mode and remote flow only until a power loss (see [Control mode](#control-mode-register-8000)).
- The 4-position wall switch and Modbus control are mutually exclusive.
- Firmware and options differ, so some entities, such as the CO₂ status sensors or the geo exchanger, can stay unknown on your unit.
- The flow range of a Flair 350 is from the documentation and has not been tested on a unit.

## Troubleshooting

| Symptom | Checks |
| --- | --- |
| No TCP connection | Gateway IP, route/VLAN, TCP server mode, port 502, PoE/DC power, firewall. |
| TCP connects but no Modbus reply | Gateway in Modbus TCP-to-RTU mode (not transparent), slave ID 20, 19200/8E1, A/B polarity, termination. |
| Serial timeout | USB path, permissions, exclusive access, slave ID, wiring, 8E1. |
| Missing CO₂ values | Sensors paired to the Flair, firmware exposes registers 4201/4203/4205/4207. |
| Some entities unknown | The firmware does not implement that register. Diagnostics lists the skipped addresses. |
| Unexpected ventilation behaviour | Check **Modbus Control Mode**. Select **Disabled** to restore autonomous operation. |
| Controls unavailable | Writable controls are off for this entry. Remove it and add it again with controls enabled. |

Download diagnostics from the device page (⋮ → **Download diagnostics**) when you report an issue. Host and serial number are redacted.

## Removal

1. Optionally, select **Modbus Control Mode → Disabled** so the unit regulates itself again.
2. Go to **Settings → Devices & services → BRINK Modbus → ⋮ → Delete**.
3. If you installed through HACS, remove the repository there and restart Home Assistant.

Deleting the entry removes its entities. It does not write anything to the unit.

## References

- BRINK *Modbus UWA2-B/UWA2-E installation regulations* (614882): the full register map
- BRINK *Flair 325 (Plus) installation manual*, chapter 14 (Modbus)
- BRINK [Flair 400 installation instructions](https://www.brinkclimatesystems.fr/wp-content/uploads/2019/02/Manuel-installateur-Flair400.pdf)

## Development

The runtime dependency is PyModbus `>=3.10.0,<4.0.0`. Tests use mocked Modbus clients:

```bash
python -m pip install -r requirements_test.txt
ruff check custom_components tests
python -m pytest -q
```

Contributor and agent notes live in [AGENTS.md](AGENTS.md); release history is in [CHANGELOG.md](CHANGELOG.md). Pull requests are welcome.

## License

MIT, see [LICENSE](LICENSE). Modbus TCP support contributed by Robin Kolk.
