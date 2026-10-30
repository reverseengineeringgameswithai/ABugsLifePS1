"""Guards for the D19 (Molt boss, Battle Arena) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_d19_molt.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d19_molt.json"
TYPE71_ARTIFACT = ROOT / "analysis" / "phase4_d19_type71.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def load_type71_artifact():
    return json.loads(TYPE71_ARTIFACT.read_text())


def test_type71_artifact_confirms_crowd_grant_not_damage():
    doc = load_type71_artifact()
    crowd = doc["crowd_projectile"]
    assert crowd["constructor_type"] == 71
    assert crowd["action_dispatch_target"] == "0x800588FC"
    assert crowd["equip_store_instruction"] == "0xA0206597"
    assert doc["player_throw"]["constructor_type"] == 2
    assert "not the damaging red projectile" in doc["conclusion"]


def test_artifact_status_is_bounded_exhausted():
    doc = load_artifact()
    assert doc["status"] == "partial_high_value_bounded_exhausted"
    assert doc["disposition"] == "move_on"


def test_actor_identity_corrected_from_earlier_hypothesis():
    doc = load_artifact()
    actor = doc["actor"]
    assert actor["id"] == 29
    assert actor["address"] == "0x8009FF90"
    assert actor["hp_initial"] == 50


def test_live_overlay_self_corrected_to_level03():
    doc = load_artifact()
    static = doc["static_inputs"]
    assert static["live_secondary_overlay"] == "REBUILD/files/LEVEL03/LEVEL1.BIN"
    assert static["rejected_initial_overlay_hypothesis"] == "REBUILD/files/LEVEL09/LEVEL.BIN"


def test_guard_rollback_accounts_for_all_dispatches():
    doc = load_artifact()
    dg = doc["damage_and_guard"]
    assert dg["molt_dispatch_events"] == 43
    assert dg["accepted_hp_descents"] == 15
    assert dg["rolled_back_dispatches"] == 28
    assert dg["accepted_hp_descents"] + dg["rolled_back_dispatches"] == dg["molt_dispatch_events"]
    assert dg["accepted_hp_range"] == [50, 20]


def test_crowd_throw_chain_traced_to_red_projectile():
    doc = load_artifact()
    crowd = doc["crowd_throw"]
    assert crowd["contact_type"] == 71
    assert crowd["allocator_call"] == "0x800B43F8 -> 0x8005A0E0"
    assert crowd["fixture_allocations"] == 31


def test_defeat_transition_goal_latch_pc_corrected():
    doc = load_artifact()
    dt = doc["defeat_transition"]
    assert dt["threshold_branch"].startswith("0x800B3DEC")
    assert dt["goal_latch_writer"] == "0x800B3E70 -> 0x800823A0 = 1"


def test_integration_correction_documented():
    doc = load_artifact()
    note = doc["INTEGRATION_CORRECTION_2026-08-03"]["note"]
    assert "0x800B3E6C" in note
    assert "0x800B3E70" in note


def test_instrumentation_flight_check_byte_identical():
    doc = load_artifact()
    flight = doc["instrumentation_flight_check"]
    assert flight["movie_reproducible"] is True
    assert flight["clean_final_frame"] == flight["armed_final_frame"] == 15651
    assert flight["clean_final_cycle"] == flight["armed_final_cycle"] == 8861074013


def test_static_tool_pins_the_corrected_goal_latch_word():
    tool_src = (ROOT / "tools" / "phase4_d19_molt.c").read_text()
    assert "0x800B3E70u, 0xA42223A0u" in tool_src
    assert "0x800B3E6Cu, 0xA42223A0u" not in tool_src


def test_registry_status_is_partial_not_unresolved():
    text = REGISTRY.read_text()
    start = text.index("  - id: D19_molt")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "status: partial" in block
    assert "status: unresolved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "D19_molt"
    assert row["status"] == "partial"
    assert "0x8009FF90" in " ".join(row["bindings"])
    assert "0x800B3E70" in " ".join(row["bindings"])


def test_registry_missing_field_reflects_banking_gap_not_open_facts():
    text = REGISTRY.read_text()
    start = text.index("  - id: D19_molt")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "banking gap" in block.lower()
