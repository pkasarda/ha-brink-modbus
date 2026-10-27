# Changelog

## Unreleased
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
