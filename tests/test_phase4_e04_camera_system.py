"""Guards for the E04 (camera follow and regions) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_e04_camera_system.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_e04_camera_system.json"
PHASE3_RECORD = ROOT / "analysis" / "phase3_camera_record.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_synthesis_matches_the_committed_phase3_record():
    doc = load_artifact()
    synth = doc["COMMITTED_SYNTHESIS_2026-08-03"]
    p3 = json.loads(PHASE3_RECORD.read_text())
    assert p3["struct"]["base"] == "0x80095358"
    assert p3["authority"]["struct_is_derived"] is True
    assert abs(p3["follow_law"]["gap_fraction_per_frame"] - 0.1506) < 1e-6
    assert "0.1506" in synth["struct_and_authority"]
    assert "DERIVED OUTPUT" in synth["struct_and_authority"] or "derived output" in synth["struct_and_authority"].lower()


def test_mode_word_negative_is_the_headline():
    doc = load_artifact()
    survey = doc["STRUCT_SURVEY_2026-08-03"]
    neg = survey["mode_word_negative"]
    assert "no field" in neg.lower()
    assert "separate producers/flags" in neg


def test_field_observations_carefully_hedged():
    doc = load_artifact()
    fields = doc["STRUCT_SURVEY_2026-08-03"]["fields_observed"]
    assert "900" in fields["+0x1E_half"]
    assert "NOT a simple target/actual converging pair" in fields["+0x1A_half"]
    assert "camera-active flag" in fields["+0x22_half"]
    assert "RAMPS" in fields["+0x24_half"]


def test_dual_attribution_flagged_as_inference():
    doc = load_artifact()
    flag = doc["STRUCT_SURVEY_2026-08-03"]["dual_attribution_flag"]
    assert "0x800824DC" in flag
    assert "G_TELESCOPE_ACTIVE" in flag
    assert "not proven" in flag


def test_l1r1_corrections_explicit_not_silent():
    doc = load_artifact()
    l1r1 = doc["L1R1_CAMERA_CONTROLS_2026-08-03"]
    corr = l1r1["corrections_to_the_survey"]
    assert "NOT theta-rate" in corr["+0x18_CORRECTED"]
    assert "8->3" in corr["+0x18_CORRECTED"] and "8->122" in corr["+0x18_CORRECTED"]
    assert "580" in corr["+0x1E_CORRECTED"]
    assert "HIGH byte" in corr["+0x22_CORRECTED"]
    assert "0x0A01" in corr["+0x22_CORRECTED"]
    assert "EXISTS AFTER ALL" in corr["+0x22_CORRECTED"]
    assert "never moved" in corr["thetas_unaffected"]


def test_operator_hint_credited():
    doc = load_artifact()
    l1r1 = doc["L1R1_CAMERA_CONTROLS_2026-08-03"]
    assert "camera nodes" in l1r1["trigger"]
    assert "L1" in l1r1["trigger"] and "R1" in l1r1["trigger"]


def test_operator_facts_confirmed_section():
    doc = load_artifact()
    facts = doc["OPERATOR_FACTS_CONFIRMED_2026-08-03"]
    assert "no rotational cameras exist" in facts["no_rotational_cameras"]
    assert "NOT" in facts["l1_turn_in_place_UNDOCUMENTED_UNTIL_NOW"]
    assert "-15/frame" in facts["l1_turn_in_place_UNDOCUMENTED_UNTIL_NOW"]
    assert "~9%" in facts["r1_camera_lock"]
    assert "LEASH" in facts["r1_camera_lock"]
    assert "0x0A" in facts["submode_codes_observed_so_far"]
    assert "0x0B" in facts["submode_codes_observed_so_far"]


def test_turn_in_place_cross_banked_to_a01():
    a01 = json.loads((ROOT / "analysis" / "phase4_a01_move_run.json").read_text())
    tip = a01["TURN_IN_PLACE_DOCUMENTED_2026-08-03"]
    assert "L1" in tip["trigger"]
    assert "EXACTLY frozen" in tip["live_confirmation"]
    assert "not isolated" in tip["not_traced"]


def test_registry_row_updated():
    text = REGISTRY.read_text()
    start = text.index("  - id: E04_camera_system")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "E04_camera_system"
    assert row["status"] == "partial"
    joined = " ".join(row["bindings"])
    assert "COMMITTED SYNTHESIS 2026-08-03" in joined
    assert "MODE-WORD NEGATIVE 2026-08-03" in joined
    assert "L1/R1 MANUAL CAMERA CONTROLS 2026-08-03" in joined
    assert "OPERATOR FACTS CONFIRMED 2026-08-03" in joined
    assert "bounded 2026-08-03" in row["next"]
