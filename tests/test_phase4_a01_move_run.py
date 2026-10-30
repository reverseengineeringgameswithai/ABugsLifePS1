"""Guards for the A01 (analog/D-pad movement and running) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_a01_move_run.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_a01_move_run.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_disposition_is_bounded_exhausted():
    doc = load_artifact()
    assert doc["phase4_disposition"] == "substantiated_partial_bounded_exhausted"


def test_static_chain_covers_direction_through_animation():
    doc = load_artifact()
    chain = " ".join(doc["static_chain"])
    assert "0x80047EBC" in chain
    assert "0x80049240" in chain
    assert "FUNC_8003633C" in chain
    assert "FUNC_800563D4" in chain


def test_walk_vs_run_cap_distinguished():
    doc = load_artifact()
    controls = {c["case"]: c for c in doc["runtime"]["controls"]}
    up = controls["up_8f"]
    walk = controls["up_r2_8f"]
    assert up["component_forward"] == walk["component_forward"]
    assert up["animation"] != walk["animation"]
    assert walk["animation"] == 29


def test_analog_matches_digital_up():
    doc = load_artifact()
    controls = {c["case"]: c for c in doc["runtime"]["controls"]}
    assert controls["analog_full_up_8f"]["matches_digital_up_8f"] is True


def test_release_returns_to_idle():
    doc = load_artifact()
    controls = {c["case"]: c for c in doc["runtime"]["controls"]}
    release = controls["release_after_up_16f_plus_24f"]
    assert release["velocity_x"] == 0
    assert release["velocity_z"] == 0
    assert release["animation"] == 22


def test_static_tool_verifies_clean():
    tool_src = (ROOT / "tools" / "phase4_a01_static.c").read_text()
    assert "0x80048494" in tool_src
    assert "0x300" in tool_src


def test_registry_status_is_partial_with_bounded_next():
    text = REGISTRY.read_text()
    start = text.index("  - id: A01_move_run")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "A01_move_run"
    assert row["status"] == "partial"
    assert "BOUNDED 2026-08-03" in row["next"]
    assert "0x80048494" in " ".join(row["bindings"])
