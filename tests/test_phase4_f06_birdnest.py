"""Guards for the F06 (Birdnest stage) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_f06_birdnest.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_f06_birdnest.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_status_reflects_synthesis_from_d17():
    doc = load_artifact()
    assert "synthesis" in doc["status"].lower()
    assert "D17_bird" in doc["status"] or "D17" in doc["status"]


def test_synthesis_cites_scene_identity():
    doc = load_artifact()
    synth = doc["SYNTHESIS_FROM_D17_2026-08-03"]
    assert "scene_id=11" in synth["identity_and_scene_binding"]
    assert "Level 6" in synth["identity_and_scene_binding"]


def test_synthesis_cites_full_combat_sequence():
    doc = load_artifact()
    synth = doc["SYNTHESIS_FROM_D17_2026-08-03"]
    seq = synth["boss_objective_full_combat_sequence"]
    assert "gold berry" in seq.lower()
    assert "homing-berry" in seq.lower() or "homing berry" in seq.lower()
    assert "THRESHOLD" in seq
    assert "18-22" in seq or "never reaches 0" in seq.lower()


def test_synthesis_hedges_flyby_vs_combat_relationship():
    doc = load_artifact()
    synth = doc["SYNTHESIS_FROM_D17_2026-08-03"]
    manifestations = synth["boss_identity_and_two_manifestations"]
    assert "hypothesis" in manifestations.lower()
    assert "not confirmed" in manifestations.lower()


def test_results_screen_counters_decoded():
    doc = load_artifact()
    counters = doc["RESULTS_SCREEN_COUNTERS_DECODED_2026-08-03"]
    result = counters["result"]
    assert "FLIK" in result
    assert "seed-token" in result.lower()
    assert "9" in result
    assert "CLOSES" in result


def test_results_screen_grain_discrepancy_flagged_not_resolved():
    doc = load_artifact()
    counters = doc["RESULTS_SCREEN_COUNTERS_DECODED_2026-08-03"]
    caveat = counters["caveat_not_chased"]
    assert "29" in caveat
    assert "00" in caveat
    assert "not resolved" in caveat.lower() or "neither confirmed" in caveat.lower()


def test_still_open_inherits_d17_residuals():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "telescope" in still_open.lower()
    assert "re-engage" in still_open.lower()


def test_registry_status_is_partial_not_unresolved():
    text = REGISTRY.read_text()
    start = text.index("  - id: F06_birdnest")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "status: partial" in block
    assert "status: unresolved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "F06_birdnest"
    assert row["status"] == "partial"
    assert "id=30" in " ".join(row["bindings"])


def test_registry_missing_field_reflects_open_residuals():
    text = REGISTRY.read_text()
    start = text.index("  - id: F06_birdnest")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "telescope" in block.lower()
    assert "cutscene" in block.lower()


def test_registry_reflects_100pct_run_and_new_cutscene():
    text = REGISTRY.read_text()
    start = text.index("  - id: F06_birdnest")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "LEVEL06.movie.json" in block
    assert "12917" in block or "12,917" in block
    assert "Flik's Journey" in block or "flik's journey" in block.lower()


def test_status_reflects_two_pass_row():
    doc = load_artifact()
    assert "Three-pass row" in doc["status"] or "three-pass row" in doc["status"].lower()


def test_100pct_run_full_timeline_documents_cutscene():
    doc = load_artifact()
    mapped = doc["F06_100PCT_RUN_FULL_ENDING_MAPPED_2026-08-03"]
    timeline = mapped["full_timeline"]
    assert "spotlight" in timeline.lower()
    assert "Flik's Journey" in timeline
    assert "9600" in timeline or "9800" in timeline


def test_100pct_run_refutes_per_visit_delta_hypothesis():
    doc = load_artifact()
    mapped = doc["F06_100PCT_RUN_FULL_ENDING_MAPPED_2026-08-03"]
    resolved = mapped["grain_discrepancy_partially_resolved"]
    assert "REFUTED" in resolved
    assert "50/50" in resolved or "4/4" in resolved


def test_100pct_run_leading_hypothesis_not_overclaimed():
    doc = load_artifact()
    mapped = doc["F06_100PCT_RUN_FULL_ENDING_MAPPED_2026-08-03"]
    resolved = mapped["grain_discrepancy_partially_resolved"]
    assert "not yet explained" in resolved.lower() or "not confirmed" in resolved.lower()


def test_operator_clarifies_cutscene_trigger_closes_gating_question():
    doc = load_artifact()
    clarified = doc["OPERATOR_CLARIFIES_CUTSCENE_TRIGGER_2026-08-03"]
    assert "first 100% completion" in clarified["note"].lower()
    assert "CLOSES" in clarified["cutscene_trigger_CLOSED"]


def test_operator_clarifies_surfaces_new_entry_fmv_fact():
    doc = load_artifact()
    clarified = doc["OPERATOR_CLARIFIES_CUTSCENE_TRIGGER_2026-08-03"]
    entry_fmv = clarified["new_fact_entry_fmv"]
    assert "first-ever entry" in entry_fmv.lower() or "first ever entry" in entry_fmv.lower()
    assert "not been captured" in entry_fmv.lower() or "not yet observed" in entry_fmv.lower()


def test_operator_clarifies_decouples_banner_from_cutscene():
    doc = load_artifact()
    clarified = doc["OPERATOR_CLARIFIES_CUTSCENE_TRIGGER_2026-08-03"]
    revised = clarified["revised_understanding_of_the_results_banner"]
    assert "DECOUPLED" in revised
    assert "remains open" in revised.lower()


def test_registry_reflects_operator_clarification():
    text = REGISTRY.read_text()
    start = text.index("  - id: F06_birdnest")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "OPERATOR CLARIFIES CUTSCENE TRIGGER" in block
    assert "level-entry FMV" in block


def test_stopping_point_justified_triages_residuals():
    doc = load_artifact()
    stop = doc["STOPPING_POINT_JUSTIFIED_2026-08-03"]
    assert "not_worth_chasing_now" in stop
    assert "needs_a_fixture_not_available" in stop
    assert "one_promising_lead_not_chased" in stop


def test_stopping_point_flags_seed_plant_as_highest_value_lead():
    doc = load_artifact()
    stop = doc["STOPPING_POINT_JUSTIFIED_2026-08-03"]
    lead = stop["one_promising_lead_not_chased"]
    assert "homing-berry" in lead.lower()
    assert "seed plants" in lead.lower()


def test_stopping_point_not_an_assumption_nothing_remains():
    doc = load_artifact()
    stop = doc["STOPPING_POINT_JUSTIFIED_2026-08-03"]
    assert "not an assumption" in stop["conclusion"].lower()


def test_registry_next_reflects_prioritized_stopping_point():
    text = REGISTRY.read_text()
    start = text.index("  - id: F06_birdnest")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "STOPPING POINT JUSTIFIED" in block
    assert "HIGHEST-VALUE" in block
