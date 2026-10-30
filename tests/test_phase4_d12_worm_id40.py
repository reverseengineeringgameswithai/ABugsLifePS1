"""Guards for the D12 (worm, id=40) armor + anchor + strike evidence.

See ObsidianVault/Experiments/EXP_2026-08-02_phase4_d12_worm_id40.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d12_worm_id40.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_identity_matches_two_independent_fields():
    doc = load_artifact()
    ident = doc["IDENTITY_CONFIRMED"]
    assert "id=40" in ident["result"]
    assert "0x2528" in ident["result"]


def test_armor_sweep_matches_shell_bug_exactly():
    doc = load_artifact()
    table = doc["ARMOR_MECHANIC_CONFIRMED"]["result_table"]
    assert table["red (equip 0, class 2)"].startswith("ZERO damage")
    assert "-2" in table["blue (equip 1, class 5)"]
    assert "-4" in table["gold (equip 3, class 11)"]
    assert "-3" in table["mega (equip 4, class 45)"]
    conclusion = doc["ARMOR_MECHANIC_CONFIRMED"]["conclusion"]
    assert "EXACT match to shell_bug's own D13 result" in conclusion
    assert "SECOND species" in conclusion


def test_anchor_is_stronger_than_shell_bug():
    doc = load_artifact()
    finding = doc["STATIONARY_ANCHORED_CONFIRMED"]
    assert "SNAPPED BACK" in finding["position_poke_test"]
    assert "STRONGER tether than shell_bug" in finding["position_poke_test"]


def test_strike_mechanic_measured_with_health_drop_and_knockback():
    doc = load_artifact()
    strike = doc["STRIKE_MECHANIC_DISCOVERED_2026-08-02"]
    assert "4 -> 3" in strike["result"]
    assert "knockback" in strike["result"].lower()
    assert strike["conclusion"].startswith("CONFIRMED")
    # the drift-explains-earlier-sessions claim must be explicit, not implied
    assert "EXPLAINS" in strike["result"]


def test_strike_mechanism_traced_to_native_call_statically():
    doc = load_artifact()
    trace = doc["STRIKE_MECHANISM_STATIC_TRACE_2026-08-02"]
    assert "0x80057b84" in trace["bytecode_trace"]
    assert "player_proximity[700]" in trace["bytecode_trace"]
    assert "player_proximity[1200]" in trace["bytecode_trace"]
    assert "vm_native_aimed_drop_spawn" in trace["native_identity"]
    assert "spawn_drop" in trace["native_behavior"]
    assert "21/22/23" in trace["native_behavior"]
    assert "p[0]==40" in trace["native_behavior"]
    assert "NOT" in trace["interpretation"]
    assert "contact_vs_actor_handler" in trace["interpretation"]


def test_respawn_negative_result_is_explicitly_retracted():
    doc = load_artifact()
    retraction = doc["RESPAWN_TEST_2026-08-02_RETRACTED"]
    assert "RETRACTED" in retraction["retraction"]
    assert "identical_flaw_in_two_sibling_rows" in retraction


def test_respawn_mechanism_asm_trace_present():
    doc = load_artifact()
    mech = doc["RESPAWN_MECHANISM_2026-08-02"]
    assert "0x80049ca4" in mech["asm_trace_the_reset_write"]
    assert "0x80049c2c" in mech["asm_trace_the_actual_reinit_routine"].lower()
    assert "CORRECTION_2026-08-02_not_the_documented_bitmask_function" in mech
    assert "CALLER_NOT_CONFIRMED" in mech
    assert "UNRESOLVED" in mech["asm_trace_the_admission_check_UNRESOLVED_CONTRADICTION"] or \
        "NOT resolved" in mech["asm_trace_the_admission_check_UNRESOLVED_CONTRADICTION"]


def test_wallworm_identity_and_stationary():
    doc = load_artifact()
    sweep = doc["WALL_WORM_ID41_SWEEP_2026-08-02"]
    assert "id=41" in sweep["identity"]
    assert "0x2629" in sweep["identity"]
    assert "unchanged" in sweep["stationary_confirmed"]


def test_wallworm_armor_matches_with_red_caveat():
    doc = load_artifact()
    armor = doc["WALL_WORM_ID41_SWEEP_2026-08-02"]["armor_sweep"]
    table = armor["result_table"]
    assert "-2" in table["blue (equip 1, class 5)"]
    assert "-4" in table["gold (equip 3, class 11)"]
    assert "-3" in table["mega (equip 4, class 45)"]
    assert "CAVEAT" in table["red (equip 0, class 2)"]


def test_wallworm_strike_confirmed_negative():
    doc = load_artifact()
    strike = doc["WALL_WORM_ID41_SWEEP_2026-08-02"]["strike_test_NEGATIVE"]
    assert strike["conclusion"].startswith("CONFIRMED NEGATIVE")
    assert "reached and evaluated FALSE" in strike["result"] or "reached and evaluated false" in strike["result"].lower()
    assert "400" in strike["method"] and "80 units" in strike["method"]


def test_campaign_breadth_and_earthworm_bonus_data():
    doc = load_artifact()
    scan = doc["CAMPAIGN_BREADTH_STATIC_SCAN_2026-08-02"]
    assert "15 records across 5 levels" in scan["result"]
    assert "11 records" in scan["bonus_earthworm_data_not_pursued_further"]
    assert "LEVEL03" in scan["bonus_earthworm_data_not_pursued_further"]


def test_still_open_names_earthworm_and_wall_worm_as_untested():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "earthworm" in still_open
    assert "wall_worm" in still_open


def test_earthworm_identity_and_no_strike_mechanic():
    doc = load_artifact()
    sweep = doc["EARTHWORM_ID12_SWEEP_2026-08-02"]
    assert "id=12" in sweep["identity_and_hp"]
    assert "1" in sweep["identity_and_hp"]
    assert "0x800775c8" in sweep["static_program_NO_strike_mechanic"]
    assert "no player_proximity opcode and no call_native" in sweep["static_program_NO_strike_mechanic"].lower() or \
        "NO player_proximity opcode and NO call_native" in sweep["static_program_NO_strike_mechanic"]


def test_earthworm_homing_live_confirmed_others_testimony_only():
    doc = load_artifact()
    sweep = doc["EARTHWORM_ID12_SWEEP_2026-08-02"]
    homing = sweep["armor_homing_LIVE_CONFIRMED"]
    assert "1 -> 0" in homing
    assert "+2.0s" in homing
    testimony = sweep["armor_red_blue_gold_mega_OPERATOR_TESTIMONY_ONLY"]
    assert "NOT independently live re-verified" in testimony
    assert "no armour" in testimony.lower()


def test_earthworm_method_lesson_anchor_field_caution():
    doc = load_artifact()
    sweep = doc["EARTHWORM_ID12_SWEEP_2026-08-02"]
    assert "method_lesson_anchor_field_is_not_flik_coordinate_space" in sweep


def test_grub_identity_correction():
    doc = load_artifact()
    grub = doc["GRUB_IDENTITY_AND_FULL_ARMOR_SWEEP_2026-08-02"]
    assert "NOT an earthworm" in grub["identity_correction"]
    assert "grub" in grub["identity_correction"].lower()
    assert "we already established this" in grub["trigger"]


def test_grub_full_armor_sweep_all_five_classes():
    doc = load_artifact()
    grub = doc["GRUB_IDENTITY_AND_FULL_ARMOR_SWEEP_2026-08-02"]
    result = grub["full_armor_sweep_result"]
    assert "green/homing" in result
    assert "blue" in result
    assert "gold" in result
    assert "mega" in result
    assert "ALL FIVE" in result
    assert "NO ARMOR AT ALL" in result


def test_grub_method_breakthroughs_documented():
    doc = load_artifact()
    grub = doc["GRUB_IDENTITY_AND_FULL_ARMOR_SWEEP_2026-08-02"]
    assert "0x800a6596" in grub["method_breakthrough_pressButton_auto_pause"]
    assert "debugger.resume" in grub["method_breakthrough_pressButton_auto_pause"]
    assert "left" in grub["method_breakthrough_facing"]
    assert "default orientation" in grub["method_breakthrough_facing"]


def test_grub_aggro_confirmed_positive():
    doc = load_artifact()
    aggro = doc["GRUB_AGGRO_2026-08-02"]
    assert "1 -> 8" in aggro["method"] or "1 -> 8" in aggro["method"].replace("1->8", "1 -> 8")
    assert "test-only" in aggro["method"].lower() or "test intervention" in aggro["method"].lower()
    assert "0x4001 -> 0x4003" in aggro["result"]
    assert "APPROACH-THEN-RETREAT" in aggro["result"]
    assert aggro["conclusion"].startswith("Grub DOES chase")


def test_grub_aggro_diverges_from_mite_and_shell_bug():
    doc = load_artifact()
    aggro = doc["GRUB_AGGRO_2026-08-02"]
    assert "mite" in aggro["conclusion"].lower()
    assert "shell_bug" in aggro["conclusion"].lower()


def test_registry_status_is_partial_not_solved():
    text = REGISTRY.read_text()
    start = text.index("  - id: D12_centipedes_earthworms")
    end = text.index("  - id: D13_armored_beetles")
    block = text[start:end]
    assert "status: partial" in block
    assert "status: solved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "D12_centipedes_earthworms"
    assert row["status"] == "partial"
