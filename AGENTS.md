# AGENTS.md: ha-brink-modbus

Home Assistant custom integration (`custom_components/brink_modbus`) for BRINK Flair 325/350/400 heat-recovery units over Modbus RTU (RS485), Modbus TCP, or RTU-over-TCP. Distributed via HACS from GitHub releases. User docs: `README.md`.

## Always
- Python 3.14, Home Assistant 2026.10 (`requirements_test.txt`). Before every commit run `ruff check custom_components tests` and `pytest -q`. The tests use mocked Modbus clients; there is no hardware in CI.
- **Never change `unique_id`s, entity names, or the serial `connection_unique_id` format.** Existing installs depend on them.
- **Register 8000 (Modbus control mode) is safety-relevant.** Only a user action writes it: the select entity, or a flow/switch write while `auto_control_mode` is on. Setup, polling, and reconnects never write.
- Entries created before 2.7.0 have no `control_enabled` / `auto_control_mode` keys and must default to `True`. New entries default to monitoring-only.
- All Modbus I/O goes through `BrinkCoordinator` (one transaction lock). Never call the client from entities.
- Keep `strings.json` and `translations/{en,sk,cs,pl}.json` in sync when changing config-flow fields.

## Read when needed
- Changing the coordinator, transport, entities, or the control-mode logic → `docs/architecture.md`
- Adding or changing registers → `custom_components/brink_modbus/const.py` (register map) and the BRINK manual links in `README.md`
- Releasing → `docs/releasing.md`
- What changed and why → `CHANGELOG.md`
