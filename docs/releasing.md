# Releasing

1. Bump `version` in `custom_components/brink_modbus/manifest.json` (semver) and add a `CHANGELOG.md` entry.
2. Push to `main` and wait for the **Validate** workflow (hassfest, HACS validation, ruff + pytest) to go green.
3. Create a GitHub release whose tag `vX.Y.Z` matches the manifest version. HACS installs releases, not commits.
4. Before a release that changes register handling or control logic, test it on a real unit:
   - every entity still has a value,
   - the Modbus control mode is unchanged,
   - the Home Assistant log has no `brink_modbus` warnings (including deprecation notices).

## CI notes
- Pin the `homeassistant` test version to a release that matches the Python version in `.github/workflows/validate.yml`. HA 2026.x needs Python ≥ 3.14.2, and Dependabot bumps that ignore this cannot install.
- Brand images live in `custom_components/brink_modbus/brand/` (HA 2026.3+ serves them; HACS shows them in the store). `dark_*` variants have white text on a transparent background.
- HACS does not delete files that a release no longer ships. Mention removed files in the release notes.
