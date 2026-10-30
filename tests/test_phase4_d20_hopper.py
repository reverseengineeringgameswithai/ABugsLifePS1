"""Guards for the D20 (Hopper boss) evidence.

See ObsidianVault/Experiments/EXP_2026-08-02_phase4_d20_hopper.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d20_hopper.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_identity_corrected_id22_is_hopper():
    doc = load_artifact()
    identity = doc["IDENTITY_CORRECTED_2026-08-02"]
    assert "0x80095358" in identity["prior_claim"]
    assert "id=22" in identity["conclusion"]
    assert "Thumper" in identity["why_distrusted"]


def test_identity_cross_checks_type_word_rule():
    doc = load_artifact()
    identity = doc["IDENTITY_CORRECTED_2026-08-02"]
    assert "0x00011c16" in identity["type_word_cross_check"]
    assert "low byte 0x16 = 22" in identity["type_word_cross_check"]


def test_still_open_no_longer_treats_white_berry_spawn_as_unsolved():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "overlay" in still_open.lower()
    assert "gate" in still_open.lower()


def test_white_berry_chain_damage_side_closes_against_canon_code():
    doc = load_artifact()
    chain = doc["WHITE_BERRY_PRODUCER_CHAIN_2026-08-02"]
    assert "0x80058A48" in chain["damage_side_callers"]
    assert "0x8004B4A0" in chain["damage_side_callers"]
    assert "D15" in chain["damage_side_callers"]


def test_white_berry_chain_spawn_side_matches_d15_allocator():
    doc = load_artifact()
    chain = doc["WHITE_BERRY_PRODUCER_CHAIN_2026-08-02"]
    assert "0x8005a1d8" in chain["spawn_side"]
    assert "0x8005A0E0" in chain["spawn_side"]


def test_white_berry_chain_caller_is_overlay_resident():
    doc = load_artifact()
    chain = doc["WHITE_BERRY_PRODUCER_CHAIN_2026-08-02"]
    assert "0x800b46d4" in chain["spawn_caller_is_overlay_resident"]
    assert "Thumper" in chain["spawn_caller_is_overlay_resident"]


def test_operator_recorded_full_fight_locates_finale():
    doc = load_artifact()
    fight = doc["OPERATOR_RECORDED_FULL_FIGHT_2026-08-02"]
    assert "D20.movie.json" in fight["fixture"]
    assert "16,711" in fight["fixture"] or "16711" in fight["fixture"]
    assert "level complete" in fight["result"].lower()
    assert "bird" in fight["result"].lower()
    assert "16100" in fight["result"] and "16300" in fight["result"]


def test_atta_chase_confirmed_out_of_scope_not_speculative():
    doc = load_artifact()
    fight = doc["OPERATOR_RECORDED_FULL_FIGHT_2026-08-02"]
    assert "LEVEL 14" in fight["significance"]
    assert "F14_riverbed_flight" in fight["significance"]
    assert "OUT OF SCOPE" in fight["significance"] or "OUT of scope" in fight["significance"].lower()


def test_deaths_noted_as_poor_gameplay_not_mechanic_finding():
    doc = load_artifact()
    fight = doc["OPERATOR_RECORDED_FULL_FIGHT_2026-08-02"]
    assert "poor gameplay" in fight["result"]
    assert "nothing to do with solving Hopper" in fight["result"]


def test_finale_trigger_traced_to_exact_instruction():
    doc = load_artifact()
    finale = doc["FINALE_TRIGGER_TRACED_2026-08-02"]
    assert "0x800503ac" in finale["result"]
    assert "36166" in finale["result"]
    assert "scene_setup_and_load" in finale["result"]
    assert "FUNC_8005038C" in finale["result"]


def test_finale_trigger_rules_out_thumper_defeat_flag_reuse():
    doc = load_artifact()
    finale = doc["FINALE_TRIGGER_TRACED_2026-08-02"]
    state = finale["id22_own_state_during_transition"]
    assert "0x80090bee" in state
    assert "does NOT reuse" in state or "not reuse" in state.lower()


def test_finale_trigger_net_assessment_notes_generic_machinery():
    doc = load_artifact()
    finale = doc["FINALE_TRIGGER_TRACED_2026-08-02"]
    assert "generic" in finale["net_assessment"].lower()
    assert "contact_walker" in finale["net_assessment"]


def test_status_reflects_bounded_exhaustion():
    doc = load_artifact()
    assert "BOUNDED" in doc["status"]
    assert "core combat/chase/defeat mechanism" in doc["status"]


def test_aggro_chase_mechanism_confirmed_via_shared_gate():
    doc = load_artifact()
    aggro = doc["AGGRO_CHASE_MECHANISM_CONFIRMED_2026-08-03"]
    assert "FUNC_8004C13C" in aggro["movement_driver_identified"]
    assert "0x8004cd64" in aggro["movement_driver_identified"]
    assert "0x8004cdcc" in aggro["movement_driver_identified"]
    assert "flags(+0x5c) bit 0x2" in aggro["chase_gate_confirmed"]
    assert "SET at every single sample" in aggro["chase_gate_confirmed"]
    assert "CLEAR" in aggro["chase_gate_confirmed"]


def test_aggro_chase_self_correction_documented():
    doc = load_artifact()
    aggro = doc["AGGRO_CHASE_MECHANISM_CONFIRMED_2026-08-03"]
    correction = aggro["self_correction"]
    assert "WRONG" in correction
    assert "2026-07-03" in correction
    assert "stale" in correction.lower()


def test_aggro_chase_does_not_reuse_camera_function():
    doc = load_artifact()
    aggro = doc["AGGRO_CHASE_MECHANISM_CONFIRMED_2026-08-03"]
    assert "camera_follow_update" in aggro["method"] or "FUNC_8004DF18" in aggro["method"]


def test_status_reflects_four_pass_session():
    doc = load_artifact()
    assert "Nine-pass" in doc["status"] or "nine-pass" in doc["status"].lower()


def test_phase_structure_section1_health_drain_confirmed():
    doc = load_artifact()
    phase = doc["PHASE_STRUCTURE_INVESTIGATED_2026-08-03"]
    result = phase["opening_encounter_health_drain"]
    assert "0x800590e4" in result
    assert "20 -> 18" in result or "-2" in result
    assert "0x800b418c" in result
    assert "0x80058af8" in result


def test_phase_structure_ui_bar_not_exhaustively_ruled_out():
    doc = load_artifact()
    phase = doc["PHASE_STRUCTURE_INVESTIGATED_2026-08-03"]
    ui = phase["ui_health_bar_not_found_but_not_exhaustively_ruled_out"]
    assert "NOT exhaustive" in ui
    assert "no separate on-screen bar" in ui.lower() or "no separate on-screen" in ui


def test_phase_structure_section2_patrol_confirmed_gate_not_isolated():
    doc = load_artifact()
    phase = doc["PHASE_STRUCTURE_INVESTIGATED_2026-08-03"]
    section2 = phase["second_section_patrol_after_hit"]
    assert "CONFIRMED structurally" in section2
    assert "NOT isolated" in section2 or "not isolated" in section2.lower()


def test_phase_structure_section3_not_investigated():
    doc = load_artifact()
    phase = doc["PHASE_STRUCTURE_INVESTIGATED_2026-08-03"]
    assert "NOT investigated" in phase["third_section_mountain_climb"]


def test_status_reflects_structure_not_fully_exhausted():
    doc = load_artifact()
    assert "NOT" in doc["status"]
    assert "5" in doc["status"] or "five" in doc["status"].lower() or "Five" in doc["status"]


def test_mountain_climb_confirmed_via_monotonic_elevation():
    doc = load_artifact()
    climb = doc["MOUNTAIN_CLIMB_CONFIRMED_2026-08-03"]
    assert "11900" in climb["trigger"]
    assert "14645" in climb["trigger"]
    assert "MONOTONICALLY" in climb["result"]
    assert "338,000" in climb["result"] or "338000" in climb["result"]


def test_mountain_climb_hopper_not_chasing():
    doc = load_artifact()
    climb = doc["MOUNTAIN_CLIMB_CONFIRMED_2026-08-03"]
    hopper_state = climb["hopper_during_the_climb"]
    assert "FALSE" in hopper_state
    assert "not pursuing" in hopper_state.lower() or "never actively chasing" in hopper_state.lower() or "not actively chasing" in hopper_state.lower()


def test_mountain_climb_corrects_bird_cutscene_onset():
    doc = load_artifact()
    climb = doc["MOUNTAIN_CLIMB_CONFIRMED_2026-08-03"]
    correction = climb["bird_cutscene_onset_correction"]
    assert "16100" in correction
    assert "15700" in correction
    assert "16166" in correction


def test_mountain_climb_conclusion_all_three_sections_located():
    doc = load_artifact()
    climb = doc["MOUNTAIN_CLIMB_CONFIRMED_2026-08-03"]
    assert "CONFIRMED" in climb["conclusion"]
    assert "11900" in climb["conclusion"]
    assert "14645" in climb["conclusion"]


def test_status_reflects_six_pass_session_and_all_sections_located():
    doc = load_artifact()
    assert "Nine-pass" in doc["status"] or "nine-pass" in doc["status"].lower()
    assert "3-section" in doc["status"]


def test_status_reflects_seven_pass_session():
    doc = load_artifact()
    assert "Nine-pass" in doc["status"] or "nine-pass" in doc["status"].lower()


def test_gates_trigger_matches_operator_annotations():
    doc = load_artifact()
    gates = doc["GATES_AND_REAL_HP_DRAIN_CONFIRMED_2026-08-03"]
    assert "4702" in gates["trigger"]
    assert "4888" in gates["trigger"]
    assert "11825" in gates["trigger"]


def test_gates_method_fixes_late_arm_methodology_gap():
    doc = load_artifact()
    gates = doc["GATES_AND_REAL_HP_DRAIN_CONFIRMED_2026-08-03"]
    assert "frame 0" in gates["method"]
    assert "mf5549" in gates["method"]


def test_real_hp_drain_corrects_prior_20_baseline():
    doc = load_artifact()
    gates = doc["GATES_AND_REAL_HP_DRAIN_CONFIRMED_2026-08-03"]
    drain = gates["real_hp_drain_from_30"]
    assert "initializes to 30" in drain
    assert "0x80049ca0" in drain
    assert "0x800b433c" in drain
    assert "0x800b418c" in drain
    assert "0x800590e4" in drain


def test_floor_crossing_correlates_with_flee_and_chase_gate():
    doc = load_artifact()
    gates = doc["GATES_AND_REAL_HP_DRAIN_CONFIRMED_2026-08-03"]
    correlation = gates["floor_crossing_correlates_with_flee"]
    assert "4702" in correlation
    assert "chase gate" in correlation.lower()


def test_ui_health_bar_discrepancy_honestly_flagged():
    doc = load_artifact()
    gates = doc["GATES_AND_REAL_HP_DRAIN_CONFIRMED_2026-08-03"]
    ui = gates["ui_health_bar_still_not_found"]
    assert "not find" in ui.lower() or "did not find" in ui.lower()
    assert "unresolved discrepancy" in ui


def test_both_wooden_gates_confirmed_destroyed():
    doc = load_artifact()
    gates = doc["GATES_AND_REAL_HP_DRAIN_CONFIRMED_2026-08-03"]
    first = gates["first_wooden_gate_confirmed"]
    second = gates["second_wooden_barrier_confirmed"]
    assert "4888" in first
    assert "11825" in second
    assert "GONE" in second or "gone" in second.lower()


def test_gate_interpretation_is_hedged_not_confirmed():
    doc = load_artifact()
    gates = doc["GATES_AND_REAL_HP_DRAIN_CONFIRMED_2026-08-03"]
    interp = gates["interpretation_hedged"]
    assert "hypothesis" in interp.lower()
    assert "NOT independently confirmed" in interp or "not independently confirmed" in interp.lower()


def test_still_open_reflects_gate_opcode_and_hud_residuals():
    doc = load_artifact()
    still_open = doc["STILL_OPEN"]
    assert "gate" in still_open.lower()
    assert "0x800A6594" in still_open


def test_real_health_bar_found_corrects_prior_not_found_claim():
    doc = load_artifact()
    bar = doc["REAL_HEALTH_BAR_FOUND_2026-08-03"]
    assert "falsifies" in bar["trigger"].lower()
    assert "0x800b4ba8" in bar["method"]
    assert "hud_800526f4.c" in bar["method"]


def test_real_health_bar_load_start_state_bug_documented():
    doc = load_artifact()
    bar = doc["REAL_HEALTH_BAR_FOUND_2026-08-03"]
    assert "load_start_state" in bar["method"]
    assert "FALSE" in bar["method"]


def test_real_health_bar_full_writer_trace_reaches_zero():
    doc = load_artifact()
    bar = doc["REAL_HEALTH_BAR_FOUND_2026-08-03"]
    trace = bar["full_writer_trace"]
    assert "mf1170" in trace
    assert "0->30" in trace
    assert "mf4697" in trace
    assert "0x800b4164" in trace
    assert "mf15490" in trace
    assert "2->0" in trace
    assert "0x800b428c" in trace


def test_real_health_bar_segment_formula_visually_confirmed():
    doc = load_artifact()
    bar = doc["REAL_HEALTH_BAR_FOUND_2026-08-03"]
    formula = bar["segment_formula_visually_confirmed"]
    assert "ceil(value/6)" in formula
    assert "4/5" in formula
    assert "1/5" in formula


def test_real_health_bar_corrects_prior_pass_decoy_field():
    doc = load_artifact()
    bar = doc["REAL_HEALTH_BAR_FOUND_2026-08-03"]
    correction = bar["correction_to_prior_pass"]
    assert "SUPERSEDES" in correction
    assert "decoy" in correction.lower()
    assert "0x800b4ba8" in correction


def test_real_health_bar_generalizes_to_thumper_without_claiming_solved():
    doc = load_artifact()
    bar = doc["REAL_HEALTH_BAR_FOUND_2026-08-03"]
    gen = bar["generalization_to_thumper"]
    assert "0x800b4cc8" in gen
    assert "NOT verified live this pass" in gen or "not verified live this pass" in gen.lower()
    assert "not claimed as solved for thumper" in gen.lower() or "not claimed solved for thumper" in gen.lower()


def test_status_reflects_eight_pass_session():
    doc = load_artifact()
    assert "Nine-pass" in doc["status"] or "nine-pass" in doc["status"].lower()
    assert "0x800b4ba8" in doc["status"]


def test_defeat_caller_closed_via_matched_breakpoint():
    doc = load_artifact()
    followup = doc["DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03"]
    item1 = followup["item1_defeat_caller_CLOSED"]
    assert "0x800502d8" in item1["result"]
    assert "fmv_sequence_completion_check" in item1["result"]
    assert "0x800502c4" in item1["result"].lower() or "0x800502C4" in item1["result"]
    assert "a0=4, a1=0x80" in item1["result"] or "a1=128" in item1["result"]


def test_defeat_caller_conclusion_confirms_strongest_candidate():
    doc = load_artifact()
    followup = doc["DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03"]
    item1 = followup["item1_defeat_caller_CLOSED"]
    assert "fmv_sequence_completion_check" in item1["conclusion"]
    assert "CLOSES" in item1["conclusion"]


def test_overlay_identity_closed_as_level05_level1_dat():
    doc = load_artifact()
    followup = doc["DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03"]
    item2 = followup["item2_overlay_file_identity_CLOSED"]
    assert "LEVEL05/LEVEL1.DAT" in item2["result"]
    assert "unambiguously" in item2["result"].lower() or "ambiguous:false" in item2["result"].lower()


def test_overlay_identity_refutes_thumper_sharing_hypothesis():
    doc = load_artifact()
    followup = doc["DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03"]
    item2 = followup["item2_overlay_file_identity_CLOSED"]
    assert "REFUTES" in item2["conclusion"]
    assert "LEVEL04/LEVEL1.BIN" in item2["conclusion"]


def test_overlay_identity_documents_index0_correction_to_warp_tool():
    doc = load_artifact()
    followup = doc["DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03"]
    item2 = followup["item2_overlay_file_identity_CLOSED"]
    assert "index 0" in item2["method"].lower() or "index0" in item2["method"].lower() or "INDEX 0" in item2["method"]
    assert "index 1" in item2["method"].lower() or "idx1" in item2["method"].lower() or "index 1" in item2["method"]


def test_gate_opcode_predicate_fires_near_operator_named_frame():
    doc = load_artifact()
    followup = doc["DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03"]
    item3 = followup["item3_gate_break_opcode_PARTIAL"]
    assert "4700" in item3["result"] or "4701" in item3["result"]
    assert "0x800a0224" in item3["result"]
    assert "0x800B3BD4" in item3["method"] or "0x800b3bd4" in item3["method"].lower()


def test_gate_opcode_honestly_reported_as_not_closed():
    doc = load_artifact()
    followup = doc["DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03"]
    item3 = followup["item3_gate_break_opcode_PARTIAL"]
    assert "PARTIAL" in item3["conclusion"]
    assert "not" in item3["conclusion"].lower()
    assert "hundreds" in item3["result"].lower()


def test_net_assessment_reports_two_closed_one_partial():
    doc = load_artifact()
    followup = doc["DEFEAT_CALLER_OVERLAY_AND_GATE_OPCODE_2026-08-03"]
    assert "Two of the three" in followup["net_assessment"]


def test_registry_status_is_partial_not_solved():
    text = REGISTRY.read_text()
    start = text.index("  - id: D20_hopper")
    end = text.index("  # ── E. World")
    block = text[start:end]
    assert "status: partial" in block
    assert "status: solved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "D20_hopper"
    assert row["status"] == "partial"
    assert "0x80095358" in " ".join(row["bindings"])
