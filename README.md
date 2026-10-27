# BRINK Modbus

Local Home Assistant integration for BRINK Flair ventilation units. It reads the unit directly over Modbus and does not use BRINK cloud services.

Supported models are Flair 325, Flair 325 Plus, Flair 350, and Flair 400.

## Supported connections

| Connection | Home Assistant client | Use it for |
| --- | --- | --- |
| Serial RS485 | `AsyncModbusSerialClient`, RTU framing | A local USB-RS485 adapter |
| Modbus TCP gateway | `AsyncModbusTcpClient`, standard MBAP framing | A Modbus TCP-to-RTU gateway such as Waveshare RS485 TO POE ETH (B) |
| RTU-over-TCP | `AsyncModbusTcpClient`, RTU framing | A transparent TCP serial server that carries raw RTU frames |

The normal choice for a Waveshare Modbus gateway is **Modbus TCP gateway**. Its Modbus TCP-to-RTU mode accepts standard Modbus TCP frames on port 502 and performs the RTU conversion itself. Do not choose RTU-over-TCP for this mode.

Existing serial entries do not need migration: an entry without `connection_type` continues to use serial RTU, with the same config-entry and entity identifiers. Existing entries retain control access for backwards compatibility; new entries begin in monitoring-only mode. Existing entries also keep **automatic control-mode switching**: setting the flow setpoint (or the power switch position) first writes the matching register 8000 mode, so automations retake control after a power loss resets the unit to Disabled. New entries choose this with the *Switch Modbus control mode automatically* option (off by default); with it off, select the required control mode explicitly.

## Safety and autonomous CO₂ control

New installations are monitoring-only by default. Monitoring reads sensors and holding-register state, but never writes register 8000 or any other register. Register 8000 is only ever written by a user action: the Modbus Control Mode select, or a flow/switch write with automatic control-mode switching enabled. Setup validation also performs one read-only input-register request only. Startup, reconnects, and polling do not write to the unit.

This matters when BRINK wireless CO₂ sensors are fitted: with register 8000 left at `0`, the Flair remains responsible for its own ventilation regulation if Home Assistant, the network, or the gateway is offline.

The Flair installation manual documents remote-control register 8000 as:

| Value | Meaning |
| --- | --- |
| `0` | Modbus control disabled; autonomous operation |
| `1` | Switch control; required before writing switch position 8001 |
| `2` | Flow control; required before writing flow setpoint 8002 |

To use controls, explicitly enable **Enable writable controls** when adding the entry. Select **Modbus Control Mode** yourself before changing a power mode or flow setpoint, or enable *Switch Modbus control mode automatically* to let those controls write the matching mode first. Without that option, the integration never changes the mode as a side effect of another control. Select **Disabled** to return to autonomous control.

The documented remote-flow range for 8002 is `0` or `50` through the model maximum:

| Model | Maximum m³/h |
| --- | ---: |
| Flair 325 | 325 |
| Flair 325 Plus | 325 |
| Flair 350 | 350 |
| Flair 400 | 400 |

The Flair 400 remote-control table and register meanings are documented in BRINK’s [Flair 400 installation instructions](https://www.brinkclimatesystems.fr/wp-content/uploads/2019/02/Manuel-installateur-Flair400.pdf). In particular, it specifies input register 4004 as Appliance Type and documents 8000–8002, including the 400 m³/h Flair 400 limit.

## Waveshare RS485 TO POE ETH (B)

Use an Ethernet network with an IEEE 802.3af PoE switch/injector, or power the gateway from its supported DC input. Connect the BRINK RS485 bus to the gateway’s isolated RS485 interface according to the BRINK and Waveshare wiring diagrams. Keep A/B polarity consistent; connect signal ground only when the equipment documentation calls for it. Fit bus termination only at the two physical ends of the RS485 run, as required by the installation documentation.

Configure the gateway as follows:

1. Put it in **Modbus TCP to RTU** conversion mode, called **Modbus TCP Protocol** or **Modbus TCP<->RTU** in Waveshare tools/firmware.
2. Set it to **TCP server** mode.
3. Use TCP port **502**.
4. Set the RS485 serial settings to **19200 baud, 8 data bits, even parity, 1 stop bit (8E1)**, with no flow control.
5. Set the BRINK Modbus slave ID to **20**, unless you intentionally use another value.

The [Waveshare manual](https://files.waveshare.com/upload/4/4d/RS485-to-eth-b-user-manual-EN-v1.33.pdf) states that this conversion mode changes the gateway port to 502 and bridges the requested slave ID, function code, register address, and quantity to RTU.

Transparent TCP is different: it relays serial bytes and expects RTU framing, including the RTU CRC, across the socket. Use the separate RTU-over-TCP choice only for a gateway deliberately configured this way. It is not the standard Waveshare Modbus gateway setting.

## Install and configure

1. In HACS, open **Integrations**, choose the menu, select **Custom repositories**, and add `https://github.com/pkasarda/ha-brink-modbus` as an **Integration** repository.
2. Install **BRINK Modbus** through HACS and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**, then select **BRINK Modbus**.
4. Select **Modbus TCP Gateway**.
5. Enter the Waveshare gateway IP address or hostname, port `502`, and slave ID `20`.
6. Select **Flair 400**.
7. Leave **Enable writable controls** switched off to preserve autonomous CO₂ regulation.
8. Finish setup, then verify supply/exhaust airflow and the installed CO₂ sensor values.
9. Enable controls only when intentional. Select a Modbus control mode explicitly before issuing a related flow or power command.

For a USB adapter instead, select **Serial RS485**, provide a stable path such as `/dev/serial/by-id/...`, set 19200 baud, slave ID 20, and the correct model. Serial uses 8E1 by default.

## Entities

The integration retains the existing device hierarchy and entity identifiers. Monitoring includes appliance type, software information, supply/exhaust airflow setpoints and actual flow, fan RPM, temperatures, humidity where available, pressure, bypass/filter/preheater state, filter usage, and CO₂ inputs 1–4 where the BRINK firmware exposes them. The coordinator also reads holding state for bypass, Modbus control mode, power position, CO₂ sensor mode, imbalance, geo heat exchanger, and flow settings.

When writable controls are disabled, number, select, and switch controls are unavailable while all monitoring entities remain usable. Diagnostic register reads remain read-only.

## Troubleshooting

| Symptom | Checks |
| --- | --- |
| No TCP connection | Confirm the gateway IP, route/VLAN, TCP server mode, port 502, PoE/DC power, and firewall rules. |
| TCP connects but no Modbus reply | Confirm the gateway is in Modbus TCP-to-RTU conversion mode rather than transparent mode; check slave ID 20, 19200/8E1, A/B polarity, termination, and BRINK Modbus configuration. |
| Serial timeout | Check the USB device path, permissions, exclusive access, slave ID, wiring, and 8E1 settings. |
| Incorrect or missing CO₂ values | Confirm the wireless BRINK sensors are paired to the Flair and that the installed firmware exposes the corresponding 4201/4203/4205/4207 input registers. |
| Some entities unavailable | A firmware or hardware option may not implement every documented/legacy register. The integration keeps other successful reads available. |
| Gateway offline | Entities become unavailable after failed reads. The integration retries on later polling intervals and recovers when the gateway returns. |
| Unexpected ventilation behaviour | Check register 8000 using the Modbus Control Mode entity. Select **Disabled** to restore autonomous operation. In monitoring-only mode the integration cannot write this register. |
| Controls are unavailable | Reconfigure the entry with writable controls enabled, then select Switch Control or Flow Control explicitly when required. |

## Development

The runtime dependency is PyModbus `>=3.10.0,<4.0.0`. The tested APIs use `device_id` for Modbus requests, synchronous `close()`, and `AsyncModbusTcpClient` with either `FramerType.SOCKET` (standard TCP) or `FramerType.RTU` (transparent RTU-over-TCP).

Run the test suite after installing development requirements:

```bash
python -m pip install -r requirements_test.txt
python -m pytest -q
python -m compileall -q custom_components
```

Tests use mocked Modbus clients; no physical gateway or BRINK unit is exercised by the automated suite.

Contributor and agent notes live in [AGENTS.md](AGENTS.md); release history is in [CHANGELOG.md](CHANGELOG.md).

## License

MIT, see [LICENSE](LICENSE). Modbus TCP support contributed by Robin Kolk.
