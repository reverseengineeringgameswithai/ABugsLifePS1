"""Guards for the A02 (slow walking) evidence, synthesized from A01_move_run.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_a02_slow_walk.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_a02_slow_walk.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_status_reflects_a01_synthesis():
    doc = load_artifact()
    assert "A01_move_run synthesis" in doc["status"]
    assert "zero new live instrumentation" in doc["status"]


def test_walk_gate_and_animation_gate_are_independent():
    doc = load_artifact()
    synth = doc["SYNTHESIZED_FROM_A01_2026-08-03"]
    assert "0x80048494" in synth["walk_gate"]
    assert "0x80056474" in synth["animation_gate"]
    assert "independent" in synth["live_counterfactual"].lower()


def test_turn_law_shared_not_separate():
    doc = load_artifact()
    synth = doc["SYNTHESIZED_FROM_A01_2026-08-03"]
    assert "no separate slow-walk turning law" in synth["turn_law"]


def test_honestly_flags_ratio_not_re_derived():
    doc = load_artifact()
    synth = doc["SYNTHESIZED_FROM_A01_2026-08-03"]
    assert "0.605x" in synth["not_re_derived"]
    assert "not superseded" in synth["not_re_derived"]


def test_still_open_names_longer_window_need():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "60+ frame" in still_open or "60+" in still_open


def test_registry_status_is_partial_bounded():
    text = REGISTRY.read_text()
    start = text.index("  - id: A02_slow_walk")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "A02_slow_walk"
    assert row["status"] == "partial"
    assert "SYNTHESIZED FROM A01_move_run" in " ".join(row["bindings"])
    assert "bounded via A01 synthesis" in row["next"]
