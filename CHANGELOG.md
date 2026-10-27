# Changelog

## 2.8.0 (2026-10-27)
- New sensors (from the BRINK UWA2-B register map): active function, ventilation mode, wall-switch position, supply/exhaust fan status, frost status, frost heater power, frost fan reduction, operating time (32-bit), CO₂ sensor status 1–4 and fan control type. The last two are disabled by default.
- New controls: standby switch (8003), Reset Filter Warning button (8010), filter warning days, bypass temperatures (dwelling, outside, hysteresis).
- Fix: Software Version showed serial-number digits (4012); it now reads 4000-4002. The BCD serial number and the software version appear in the device info.
- Fix: geo heat exchanger temperatures are tenths of °C (shown 50/250 instead of 5.0/25.0 °C).
- Robustness: a register the firmware rejects no longer hides the other registers in the same block, and it is skipped on later polls.
- Diagnostics download (host and serial redacted); entity categories for diagnostic and configuration entities; `quality_scale.yaml`.
- Verified on a Flair 325 Plus (firmware S2.01.21, RS485): every new register is supported.
- README rewritten: supported devices, configuration fields, entities, actions, data updates, examples, limitations, removal.

## 2.7.3 (2026-10-27)
- Brand images in `brand/` (icon, logo, and dark variants), so Home Assistant 2026.3+ and HACS show the BRINK logo. The unused root `icon.png` was removed.
- Docs: AGENTS.md, docs/architecture.md, docs/releasing.md, CHANGELOG.md.

## 2.7.2 (2026-10-27)
- The coordinator passes `config_entry` explicitly (required by current Home Assistant).
- CI tests against Home Assistant 2026.10 on Python 3.14; `hacs.json` declares a minimum Home Assistant version of 2025.1.0.

## 2.7.1 (2026-10-27)
- `sw_version` is passed to the device registry as a string (an int stops working in HA 2026.12).
- CO₂ sensors use `"ppm"` instead of the deprecated `CONCENTRATION_PARTS_PER_MILLION`.

## 2.7.0 (2026-10-27)
- Modbus TCP and RTU-over-TCP transports, monitoring-only mode for new entries, model-specific airflow limits, signed int16 registers, and a test suite. Contributed by Robin Kolk (@kloknibor).
- New `auto_control_mode` option: flow and switch writes set register 8000 first. It is on for existing entries, so Home Assistant retakes control after a power loss.
- `imbalance_allowed` (6033) is now actually polled; earlier versions always reported it as off.
- Services take an optional `config_entry_id` instead of the device target that hassfest rejects; the duplicate `min` in `set_flow_speed` is fixed.
- CI (hassfest, HACS validation, ruff, pytest), MIT license, legacy `strings/` folder removed.

## 2.6.0 (2025-10)
- Initial public release (serial RS485).
