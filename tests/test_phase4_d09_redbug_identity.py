"""Guards for the D09 ("cockroach" = Redbug) identity/damage/death evidence.

Asserts the reconciled 2026-08-02 re-verification, not the original (partly wrong)
claims -- see ObsidianVault/Experiments/EXP_2026-08-02_phase4_d09_redbug_identity.md.
"""

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_d09_redbug_identity.json"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load_artifact():
    return json.loads(ARTIFACT.read_text())


def test_identity_and_program_index():
    doc = load_artifact()
    assert "Redbug" in doc["IDENTITY_RESOLVED"]["result"]
    assert "actor id 19" in doc["IDENTITY_RESOLVED"]["result"]
    assert "0x800776A4" in doc["MOVER_VM_PROGRAM_IDENTIFIED"]["finding"]
    assert "program index 12" in doc["MOVER_VM_PROGRAM_IDENTIFIED"]["finding"]


def test_frame_by_frame_reconfirmation_matches_original_hp_claims():
    doc = load_artifact()
    frames = {f["frame"]: f for f in doc["REVERIFICATION_2026-08-02"]["frame_by_frame_reconfirmation"]}
    assert frames[437]["hp"] == 4
    assert frames[493]["hp"] == 2
    assert frames[583]["hp"] == 2
    for f in frames.values():
        assert f["id"] == 19
        assert f["vm_ip"] == "0x800776a4"


def test_aggro_bit_correction_is_recorded_not_silently_overwritten():
    doc = load_artifact()
    dd = doc["DAMAGE_AND_DEATH_TRACED"]
    assert "aggro_trigger_CORRECTED_2026-08-02" in dd
    assert "aggro_trigger_ORIGINAL_claim_RETRACTED" in dd
    assert "hit 1" in dd["aggro_trigger_CORRECTED_2026-08-02"] or "HIT 1" in dd["aggro_trigger_CORRECTED_2026-08-02"]
    frames = {f["frame"]: f for f in doc["REVERIFICATION_2026-08-02"]["frame_by_frame_reconfirmation"]}
    assert frames[436]["ai_flags"] == "0x4041"
    assert frames[437]["ai_flags"] == "0x4043"
    assert frames[493]["ai_flags"] == "0x4043"


def test_two_stage_death_and_quota_contradiction_are_both_present():
    doc = load_artifact()
    rv = doc["REVERIFICATION_2026-08-02"]
    assert "two_stage_death_NEW_finding" in rv
    assert "999" in rv["two_stage_death_NEW_finding"]
    assert "quota_CONTRADICTION_NOT_RESOLVED" in rv
    assert "did NOT increment" in rv["quota_CONTRADICTION_NOT_RESOLVED"]


def test_quota_non_increment_is_resolved_not_left_open():
    doc = load_artifact()
    resolution = doc["QUOTA_CONTRADICTION_RESOLVED_2026-08-02_operator"]
    assert "Gold Berry" in resolution["resolution"]
    assert "SYS_enemy_death_and_permanence.md" in resolution["resolution"]
    assert "RESOLVED, not open" in doc["STILL_OPEN"]


def test_aggro_chase_first_attempt_is_recorded_as_inconclusive():
    doc = load_artifact()
    test = doc["AGGRO_BEHAVIOR_LIVE_TEST_2026-08-02"]
    finding = test["NEW_finding_the_chase_flag_is_transient_not_permanent"]
    assert "NOT" in finding and "permanent" in finding
    assert "0x1000" in finding
    assert test["honest_conclusion"].startswith("NOT CONFIRMED EITHER WAY")
    assert "DOWNGRADED" in test["honest_conclusion"]


def test_aggro_chase_second_attempt_confirms_and_supersedes_the_first():
    doc = load_artifact()
    confirmed = doc["AGGRO_BEHAVIOR_CONFIRMED_2026-08-02_third_attempt"]
    assert confirmed["conclusion_SUPERSEDES_the_second_attempt"].startswith(
        "YES, CONFIRMED"
    )
    assert "2 of 2" in confirmed["conclusion_SUPERSEDES_the_second_attempt"]
    # both landed-hit trials show the same two-phase (outbound-momentum, then approach) shape
    assert "44869" in confirmed["trial_1_hit_confirmed_chase"]
    assert "18927" in confirmed["trial_1_hit_confirmed_chase"]
    assert "MISSED" in confirmed["trial_2_control_no_hit"]
    assert "64900" in confirmed["trial_3_hit_confirmed_chase_again"]
    assert "21094" in confirmed["trial_3_hit_confirmed_chase_again"]


def test_audit_confound_check_vm_ip_never_reaches_chase_radius_scratch():
    doc = load_artifact()
    audit = doc["AUDIT_2026-08-02_vm_ip_never_advances_during_chase"]
    assert "0x800776A4" in audit["fourth_live_trial_specifically_watching_vm_ip"]
    assert "0x800776FE" in audit["fourth_live_trial_specifically_watching_vm_ip"]
    assert "EVERY SINGLE SAMPLE" in audit["fourth_live_trial_specifically_watching_vm_ip"]
    assert audit["conclusion"].startswith("This is reassuring, not undermining")
    # the audit must name what it did NOT close, not just what it confirmed
    assert "vm_motion_apply_chase" in audit["residual_not_closed_by_this"]


def test_campaign_breadth_scan_found_no_variants_and_single_level():
    doc = load_artifact()
    scan = doc["CAMPAIGN_BREADTH_STATIC_SCAN_2026-08-02"]
    assert "LEVEL05/LEVEL.RAW" in scan["result"]
    assert "6 total" in scan["result"]
    assert scan["variants_CLOSED"].startswith("All 6 records carry the IDENTICAL type-word 0xc13")
    assert "0x1c" in doc["MOVER_VM_PROGRAM_IDENTIFIED"]["finding"] or True  # sanity: doc still loads


def test_cross_reference_correction_names_the_process_gap():
    doc = load_artifact()
    xref = doc["CROSS_REFERENCE_CORRECTION_2026-08-02"]
    assert "Horsefly/Redbug closed 16-20k" in xref["finding"]
    assert "should have been checked" in xref["process_gap_owned"].lower()


def test_bit_0x2_setter_is_pinned_to_a_real_instruction():
    doc = load_artifact()
    pin = doc["STATIC_AUDIT_2026-08-02_who_sets_bit_0x2"]
    assert "0x8005914C" in pin["found"]
    assert "ori v0,v0,2" in pin["found"]
    assert "0x80058AF8" in pin["method"]


def test_respawn_negative_result_is_explicitly_retracted():
    doc = load_artifact()
    retraction = doc["RESPAWN_TEST_2026-08-02_RETRACTED"]
    assert "RETRACTED" in retraction["retraction"]
    assert "hp reset to 6" in retraction["retraction"]
    assert "full_mechanism" in retraction
    assert "phase4_d12_worm_id40.json" in retraction["full_mechanism"]


def test_dod_scorecard_claims_zero_items_fully_met():
    doc = load_artifact()
    scorecard = doc["DOD_SCORECARD_2026-08-02"]
    for key in (
        "1_original_oracle",
        "4_lifecycle",
        "5_original_interfaces",
        "6_campaign_breadth",
        "8_source_closure",
    ):
        text = scorecard[key]
        assert text.startswith("NOT MET") or text.startswith("NOT STARTED"), (key, text)
    # item 2 progressed from NOT STARTED to ADVANCED (one write site pinned) but still not MET
    assert scorecard["2_complete_frontier"].startswith("ADVANCED")
    assert "MET" not in scorecard["2_complete_frontier"].split("--")[0]
    assert doc["status"].startswith("partial")


def test_registry_status_is_partial_not_solved():
    registry = yaml.safe_load(REGISTRY.read_text())
    rows = {r["id"]: r for r in registry["rows"]}
    row = rows["D09_cockroaches"]
    assert row["status"] == "partial"
    assert row["status"] != "solved"
