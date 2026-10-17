"""Packaging metadata checks for HACS installations."""

import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parent.parent


def test_hacs_manifest_is_present_and_valid() -> None:
    """HACS needs root metadata before it can install a custom repository."""
    hacs_manifest = json.loads((REPOSITORY_ROOT / "hacs.json").read_text())

    assert hacs_manifest["name"] == "BRINK Modbus"
    assert hacs_manifest["render_readme"] is True
