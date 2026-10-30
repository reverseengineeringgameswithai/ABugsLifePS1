"""Guards for the F15 (Canyon Showdown stage) evidence.

See ObsidianVault/Experiments/EXP_2026-08-03_phase4_f15_canyon_showdown.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_f15_canyon_showdown.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_status_reflects_synthesis_not_rederivation():
    doc = load_artifact()
    assert "synthesis" in doc["status"].lower()
    assert "D20_hopper" in doc["status"] or "D20" in doc["status"]


def test_synthesis_cites_d20_multi_area_structure():
    doc = load_artifact()
    synth = doc["SYNTHESIS_FROM_D20_2026-08-03"]
    assert "4888" in synth["multi_area_structure"]
    assert "11825" in synth["multi_area_structure"]
    assert "11900" in synth["multi_area_structure"] or "14645" in synth["multi_area_structure"]


def test_synthesis_cites_d20_health_bar_and_defeat_caller():
    doc = load_artifact()
    synth = doc["SYNTHESIS_FROM_D20_2026-08-03"]
    assert "0x800b4ba8" in synth["boss_health_and_defeat"]
    assert "fmv_sequence_completion_check" in synth["boss_health_and_defeat"]
    assert "0x800502C4" in synth["boss_health_and_defeat"] or "0x800502c4" in synth["boss_health_and_defeat"].lower()


def test_synthesis_cites_overlay_identity():
    doc = load_artifact()
    synth = doc["SYNTHESIS_FROM_D20_2026-08-03"]
    assert "LEVEL05/LEVEL1.DAT" in synth["identity_and_scene_binding"]


def test_ending_cutscene_trigger_explains_the_gap():
    doc = load_artifact()
    cutscene = doc["ENDING_CUTSCENE_DISCOVERED_2026-08-03"]
    assert "16,711" in cutscene["trigger"] or "16711" in cutscene["trigger"]
    assert "ending FMV" in cutscene["trigger"]


def test_ending_cutscene_method_stops_movie_and_drives_input_live():
    doc = load_artifact()
    cutscene = doc["ENDING_CUTSCENE_DISCOVERED_2026-08-03"]
    assert "movie.stopPlayback" in cutscene["method"]
    assert "emulator.pressButton" in cutscene["method"]


def test_ending_cutscene_result_describes_multiple_shots():
    doc = load_artifact()
    cutscene = doc["ENDING_CUTSCENE_DISCOVERED_2026-08-03"]
    result = cutscene["result"]
    assert "caravan" in result.lower()
    assert "caterpillar" in result.lower()
    assert "ant colony" in result.lower() or "ant" in result.lower()
    assert "never previously captured" in result.lower() or "never previously" in result.lower()


def test_ending_cutscene_scene_id_stays_15():
    doc = load_artifact()
    cutscene = doc["ENDING_CUTSCENE_DISCOVERED_2026-08-03"]
    assert "scene_id" in cutscene["result"]
    assert "15" in cutscene["result"]


def test_ending_cutscene_in_engine_hypothesis_hedged():
    doc = load_artifact()
    cutscene = doc["ENDING_CUTSCENE_DISCOVERED_2026-08-03"]
    result = cutscene["result"]
    assert "in-engine" in result.lower() or "IN-ENGINE" in result
    assert "not independently confirmed" in result.lower() or "NOT independently confirmed" in result


def test_ending_cutscene_connects_to_existing_fmv_sequence_completion_check():
    doc = load_artifact()
    cutscene = doc["ENDING_CUTSCENE_DISCOVERED_2026-08-03"]
    assert "fmv_bin_load(41)" in cutscene["connects_to_existing_canon"]


def test_not_yet_determined_is_honest_about_terminal_state():
    doc = load_artifact()
    cutscene = doc["ENDING_CUTSCENE_DISCOVERED_2026-08-03"]
    nyd = cutscene["not_yet_determined"]
    assert "credits" in nyd.lower() or "menu" in nyd.lower()
    assert "not" in nyd.lower()


def test_still_open_does_not_claim_solved():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "credits" in still_open.lower() or "terminal" in still_open.lower()
    assert "gate-break opcode" in still_open.lower() or "barrier" in still_open.lower()


def test_registry_status_is_partial_not_unresolved():
    text = REGISTRY.read_text()
    start = text.index("  - id: F15_canyon_showdown")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "status: partial" in block
    assert "status: unresolved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "F15_canyon_showdown"
    assert row["status"] == "partial"
    assert "0x800b4ba8" in " ".join(row["bindings"])
    assert "LEVEL05/LEVEL1.DAT" in " ".join(row["bindings"])


def test_registry_missing_field_reflects_new_residuals():
    text = REGISTRY.read_text()
    start = text.index("  - id: F15_canyon_showdown")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "credits" in block.lower()
    assert "in-engine" in block.lower()


def test_ending_sequence_trigger_cites_operator_100pct_run():
    doc = load_artifact()
    mapped = doc["ENDING_SEQUENCE_FULLY_MAPPED_2026-08-03"]
    assert "100% run" in mapped["trigger"]
    assert "76,310" in mapped["trigger"] or "76310" in mapped["trigger"]


def test_ending_sequence_result_describes_full_timeline():
    doc = load_artifact()
    mapped = doc["ENDING_SEQUENCE_FULLY_MAPPED_2026-08-03"]
    result = mapped["result"]
    assert "Congratulations! Game Complete" in result
    assert "end-credits" in result.lower() or "credits" in result.lower()
    assert "do you want to save" in result.lower()
    assert "67000" in result and "68000" in result


def test_ending_sequence_conclusion_closes_how_it_concludes():
    doc = load_artifact()
    mapped = doc["ENDING_SEQUENCE_FULLY_MAPPED_2026-08-03"]
    conclusion = mapped["conclusion"]
    assert "CLOSES" in conclusion
    assert "final level" in conclusion.lower()


def test_ending_sequence_conclusion_hedges_stage_uniqueness():
    doc = load_artifact()
    mapped = doc["ENDING_SEQUENCE_FULLY_MAPPED_2026-08-03"]
    conclusion = mapped["conclusion"]
    assert "no other stage" in conclusion.lower()
    assert "not independently disproven" in conclusion.lower() or "inferred" in conclusion.lower()


def test_ending_sequence_not_yet_determined_stays_honest():
    doc = load_artifact()
    mapped = doc["ENDING_SEQUENCE_FULLY_MAPPED_2026-08-03"]
    nyd = mapped["not_yet_determined"]
    assert "in-engine" in nyd.lower()
    assert "save prompt" in nyd.lower()


def test_status_update_reflects_two_pass_row():
    doc = load_artifact()
    assert "Two-pass row" in doc["status"] or "two-pass row" in doc["status"].lower()
    assert "Game Complete" in doc["status"]


def test_still_open_update_marks_prior_residuals_closed():
    doc = load_artifact()
    update = doc["STILL_OPEN_2026-08-03_UPDATE"]
    assert "Now closed" in update
    assert "credits" in update.lower()


def test_operator_closed_residuals_retracts_fmv_question():
    doc = load_artifact()
    closed = doc["OPERATOR_CLOSED_RESIDUALS_2026-08-03"]
    assert "fmv is mostly solved" in closed["note"].lower()
    assert "Retracting" in closed["fmv_vs_in_engine"]


def test_operator_closed_residuals_confirms_fliks_journey_destination():
    doc = load_artifact()
    closed = doc["OPERATOR_CLOSED_RESIDUALS_2026-08-03"]
    dest = closed["post_save_prompt_destination"]
    assert "Flik's Journey" in dest
    assert "SAME destination any other level" in dest or "same destination any other level" in dest.lower()


def test_registry_missing_field_no_longer_lists_fmv_or_save_prompt():
    text = REGISTRY.read_text()
    start = text.index("  - id: F15_canyon_showdown")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    missing_start = block.index("missing:")
    missing_end = block.index("\n    fixture_have:")
    missing_field = block[missing_start:missing_end]
    assert "compressed FMV" not in missing_field
    assert "save-prompt choice" not in missing_field


def test_registry_next_marks_row_as_bounded():
    text = REGISTRY.read_text()
    start = text.index("  - id: F15_canyon_showdown")
    end = text.index("\n  - id:", start + 10)
    block = text[start:end]
    assert "bounded" in block.lower()
