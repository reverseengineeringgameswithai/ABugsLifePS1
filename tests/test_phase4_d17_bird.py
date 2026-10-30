"""Guards for the D17 (bird boss, Birdnest) evidence.

See ObsidianVault/Experiments/EXP_2026-08-02_phase4_d17_bird.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d17_bird.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_methodology_finding_launcher_root_cause():
    doc = load_artifact()
    finding = doc["METHODOLOGY_MOVIE_DESYNC_ROOT_CAUSE_2026-08-02"]
    assert "NO [CPU] section" in finding["actual_root_cause"]
    assert "launch_repro_playback.sh" in finding["fix"]
    assert "hp constant at 50 throughout" in finding["consequence_for_prior_data"]
    assert "reproducible` reported true" in finding["consequence_for_prior_data"]


def test_level_identity_is_birdnest_scene_11():
    doc = load_artifact()
    identity = doc["LEVEL_IDENTITY_2026-08-02"]
    assert "scene_id=11" in identity["result"]
    assert "F06_birdnest" in identity["result"]
    assert "Cliffside" in identity["residual"]


def test_two_distinct_bird_manifestations():
    doc = load_artifact()
    manifestations = doc["TWO_DISTINCT_BIRD_MANIFESTATIONS_2026-08-02"]
    assert "0x80090bc0" in manifestations["scripted_setpiece_flyby"]
    assert "id=30" in manifestations["combat_actor_id30"]
    assert "50" in manifestations["combat_actor_id30"]


def test_combat_sequence_defeat_is_a_threshold_not_zero():
    doc = load_artifact()
    seq = doc["COMBAT_SEQUENCE_2026-08-02"]
    defeat = seq["DEFEAT_IS_A_THRESHOLD_NOT_HP_ZERO"]
    assert "does NOT reach 0" in defeat
    assert "18-22" in defeat
    assert "0x800776ac" in defeat
    assert "results screen" in defeat


def test_combat_sequence_matches_operator_frame_annotations():
    doc = load_artifact()
    table = doc["COMBAT_SEQUENCE_2026-08-02"]["frame_cross_check_table"]
    assert "1900" in table["D17.movie.json first_hit_operator"]
    assert "2330" in table["D17.movie.json defeated_operator"]
    assert "2715" in table["D17_Goldberry.movie.json gold_berry_obtained_operator"]
    assert "5055" in table["D17_Goldberry.movie.json final_hit_operator"]


def test_still_open_names_real_residuals():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "shooter" in still_open.lower()
    assert "power-flags bit 0x10" in still_open
    assert "re-engage" in still_open.lower()


def test_cliffside_hazard_encounter():
    doc = load_artifact()
    cliff = doc["CLIFFSIDE_HAZARD_ENCOUNTER_2026-08-02"]
    assert "scene_id=6" in cliff["level_identity"]
    assert "F04_cliffside_canyon" in cliff["level_identity"]
    assert "101" in cliff["same_actor_different_stats"]
    assert "frame 329" in cliff["contact_death_branch"]
    assert "-45" in cliff["contact_death_branch"]
    assert "0x8004A814" in cliff["contact_death_branch"]
    assert "f448" in cliff["recovery_then_respawn"]
    assert "lives" in cliff["recovery_then_respawn"].lower()
    assert "health" in cliff["recovery_then_respawn"].lower()
    assert "4 throughout" in cliff["recovery_then_respawn"]


def test_setpiece_trigger_writer_closed():
    doc = load_artifact()
    writer = doc["SETPIECE_TRIGGER_WRITER_2026-08-02"]
    assert "0x80054554" in writer["result"]
    assert "FUNC_80053814" in writer["result"]
    assert "kind-0x30" in writer["result"] or "KIND-0x30" in writer["result"]
    assert "xrefsTo" in writer["method"]


def test_position_field_correction_present_and_labeled_as_correction():
    doc = load_artifact()
    cliff = doc["CLIFFSIDE_HAZARD_ENCOUNTER_2026-08-02"]
    correction = cliff["POSITION_FIELD_CORRECTION_2026-08-02"]
    assert "CORRECTS an earlier claim" in correction
    assert "f327" in correction
    assert "+0x04/08/0c" in correction
    assert "not retracted" in correction


def test_cliffside_contact_caller_narrowed_not_closed():
    doc = load_artifact()
    cliff = doc["CLIFFSIDE_HAZARD_ENCOUNTER_2026-08-02"]
    caller = cliff["contact_caller_FUNC_8004ABF4"]
    assert "FUNC_8004ABF4" in caller
    assert "SLOT 0" in caller
    assert "not a full closure" in caller.lower()


def test_power_flags_bit_exhaustively_checked():
    doc = load_artifact()
    cliff = doc["CLIFFSIDE_HAZARD_ENCOUNTER_2026-08-02"]
    check = cliff["power_flags_bit_0x10_checked_not_found"]
    assert "8 static store sites" in check or "8 " in check
    assert "0x8004a8e0" in check.lower()
    assert "overlay" in check.lower()


def test_registry_status_is_partial_not_solved():
    registry = yaml.safe_load((ROOT / "tests" / "_d17_row_snapshot.yaml").read_text()) \
        if (ROOT / "tests" / "_d17_row_snapshot.yaml").exists() else None
    if registry is None:
        # mechanics_baseline.yaml may be transiently unparseable due to unrelated
        # concurrent edits elsewhere in the shared file; fall back to a direct
        # substring check on this row's own block rather than failing spuriously.
        text = REGISTRY.read_text()
        start = text.index("- id: D17_bird")
        end = text.index("- id: D18_thud")
        block = text[start:end]
        assert "status: partial" in block
        assert "status: solved" not in block
        return
    rows = {r["id"]: r for r in registry["rows"]}
    row = rows["D17_bird"]
    assert row["status"] == "partial"
    assert row["status"] != "solved"
