"""Guards for the C15 (death respawn-anchor selection) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_c15_respawn_anchor.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_c15_respawn_anchor.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_death_respawn_always_uses_the_anchor_not_the_table():
    doc = load_artifact()
    mech = doc["CORE_MECHANISM_RESOLVED_2026-08-03"]
    always = mech["death_respawn_always_uses_the_safe_anchor"]
    assert "FUNC_8005B134" in always
    assert "never a fallback" in always.lower() or "never as a fallback" in always.lower()


def test_scene_6_exclusion_verified_against_raw_asm():
    doc = load_artifact()
    mech = doc["CORE_MECHANISM_RESOLVED_2026-08-03"]
    excl = mech["scene_id_6_exclusion_independently_verified"]
    assert "0x80054d00" in excl or "0x80054d0c" in excl
    assert "F04_cliffside_canyon" in excl


def test_live_verification_shows_frozen_vs_tracking_contrast():
    doc = load_artifact()
    live = doc["LIVE_VERIFICATION_2026-08-03"]
    assert "93783" in live["scene_6_anchor_frozen"]
    assert "440" in live["scene_6_anchor_frozen"]
    assert "197091" in live["normal_scene_contrast"]
    assert "53096" in live["normal_scene_contrast"]


def test_death_moment_pinned_to_hardcoded_overlay_write():
    doc = load_artifact()
    live = doc["LIVE_VERIFICATION_2026-08-03"]
    pinned = live["cliffside_death_respawn_pinned_to_instruction_level"]
    assert "0x800B3B00" in pinned
    assert "HARDCODED LITERAL" in pinned
    assert "35329" in pinned


def test_direct_answer_to_operator_question_present():
    doc = load_artifact()
    answer = doc["ANSWER_TO_OPERATOR_QUESTION"]
    assert "special case" in answer.lower()
    assert "Cliffside" in answer


def test_still_open_items_are_genuinely_secondary():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "gate_semantic_meaning" in still_open
    assert "campaign_breadth" in still_open


def test_registry_status_is_partial_with_bounded_exhausted_next():
    text = REGISTRY.read_text()
    start = text.index("  - id: C15_respawn_anchor")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "C15_respawn_anchor"
    assert row["status"] == "partial"
    assert "CORE MECHANISM RESOLVED + LIVE-VERIFIED 2026-08-03" in " ".join(row["bindings"])
    assert "BOUNDED EXHAUSTED 2026-08-03" in row["next"]
