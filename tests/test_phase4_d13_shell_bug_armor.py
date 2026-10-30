"""Guards for the D13 (shell_bug) armor + aggro evidence.

See ObsidianVault/Experiments/EXP_2026-08-02_phase4_d13_shell_bug_armor.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d13_shell_bug_armor.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_identity_matches_two_independent_fields():
    doc = load_artifact()
    ident = doc["IDENTITY_CONFIRMED"]
    assert "id=18" in ident["result"]
    assert "0x1712" in ident["result"]


def test_armor_sweep_covers_all_five_native_classes():
    doc = load_artifact()
    table = doc["ARMOR_MECHANIC_RESOLVED"]["result_table"]
    assert "red (equip 0, class 2)" in table
    assert table["red (equip 0, class 2)"].startswith("ZERO damage")
    for key in (
        "blue (equip 1, class 5)",
        "homing (equip 2, class 8)",
        "gold (equip 3, class 11)",
        "mega (equip 4, class 45)",
    ):
        assert key in table
        assert "ZERO" not in table[key]


def test_armor_conclusion_is_class_exclusion_not_time_window():
    doc = load_artifact()
    conclusion = doc["ARMOR_MECHANIC_RESOLVED"]["conclusion"]
    assert "NOT a time-based" in conclusion
    assert "only the RED class" in conclusion
    # the residual (exact PC not found) must be stated, not silently omitted
    assert "exact_gate_PC_NOT_FOUND" in doc["ARMOR_MECHANIC_RESOLVED"]


def test_aggro_negative_result_checked_precondition_first():
    doc = load_artifact()
    aggro = doc["AGGRO_NEGATIVE_RESULT"]
    assert "0x64" in aggro["precondition_check"]
    assert aggro["conclusion"].startswith("CONFIRMED NEGATIVE")
    assert "CONTRADICTS" in aggro["conclusion"] or "corrects" in aggro["conclusion"].lower()
    # the shared-bytecode puzzle with canyon_bug must be named as unresolved, not solved
    assert "unresolved_puzzle_named_not_solved" in aggro


def test_method_note_records_the_throw_reliability_fix():
    doc = load_artifact()
    note = doc["METHOD_NOTE_throw_reliability"]
    assert "unreliable" in note
    assert "debugger.resume" in note


def test_id11_program_index_discovery_cross_checked_against_redbug():
    doc = load_artifact()
    finding = doc["ID11_IDENTIFIED_2026-08-02"]
    assert "0x000B" in finding["type_word_data"]
    assert "0x030B" in finding["type_word_data"]
    assert "0x040B" in finding["type_word_data"]
    table = finding["PROGRAM_TABLE_INDEX_DISCOVERY"]
    assert "0x8007745C" in table and "0x800774FC" in table and "0x8007755C" in table
    assert "GAP-0033" in table
    # must not overclaim generality -- only 2 species checked
    assert "NOT_FULLY_GENERALIZED" in finding


def test_id11_visual_identity_distinct_from_shell_bug_and_unnamed():
    doc = load_artifact()
    finding = doc["ID11_IDENTIFIED_2026-08-02"]
    visual = finding["VISUAL_IDENTIFICATION"]
    assert "yellow" in visual.lower() and "black" in visual.lower()
    assert "NOT the same species as shell_bug" in visual
    conclusion = finding["conclusion"]
    assert "No internal or external name is established" in conclusion
    # the "primary family member" speculation must be explicitly superseded, not silently dropped
    assert "SUPERSEDED" in conclusion
    assert "CONFIRMED OUT OF SCOPE" in conclusion


def test_id11_campaign_spread_contradicts_special_status():
    doc = load_artifact()
    finding = doc["ID11_IDENTIFIED_2026-08-02"]
    assert "130 records" in finding["id11_campaign_spread_2026-08-02"]


def test_scope_confirmed_with_operator_and_canyon_bug_checked_statically():
    doc = load_artifact()
    scope = doc["SCOPE_CONFIRMATION_2026-08-02"]
    assert "bird" in scope["trigger"].lower()
    assert "NEVER in LEVEL04" in scope["canyon_bug_static_check"]
    assert scope["conclusion"].startswith("D13_armored_beetles' confirmed, operator-scoped subject is shell_bug")


def test_still_open_is_scoped_to_shell_bug_only():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "Scoped to shell_bug specifically" in still_open
    assert "canyon_bug and id=11 are confirmed out of scope" in still_open


def test_respawn_negative_result_is_explicitly_retracted():
    doc = load_artifact()
    retraction = doc["RESPAWN_TEST_2026-08-02_RETRACTED"]
    assert "RETRACTED" in retraction["retraction"]
    assert "not_independently_reverified" in retraction
    assert "RETRACTED" in doc["STILL_OPEN"]


def test_registry_status_is_partial_not_solved():
    registry = yaml.safe_load(REGISTRY.read_text())
    rows = {r["id"]: r for r in registry["rows"]}
    row = rows["D13_armored_beetles"]
    assert row["status"] == "partial"
    assert row["status"] != "solved"
