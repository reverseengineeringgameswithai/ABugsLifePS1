"""Falsification guards for the Riverbed Flight C16 death-law slice."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_c16_flight_death as flight  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import ps1_scenario  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_c16_flight_death.json"
ARTIFACT_SHA256 = "dfa705b97d0091bc171c3ee1193bf5f062ec75f48f4224a8f054347613ef00fd"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_flight_death_recomputes_from_low_level_evidence():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert flight.evidence_gaps(doc) == []
    assert doc["summary"] == flight.derive_summary(doc)
    assert doc["summary"] == {
        "special_stage_contact_paths_bounded": 1,
        "scene": 8,
        "actor_pool_slot": 5,
        "actor_id": 37,
        "producer_path_id": "proximity_contact",
        "natural_fatal_health": -1,
        "ordinary_respawn_health_lives": [4, 2],
        "response_only_health_lives": [0, 3],
        "response_only_main_ram_difference_count": 1,
        "matched_outcome_frame_cycle_pc_sp": True,
        "level08_respawn_initializer_live_qualified": 1,
        "level08_fixed_safe_live_tuple": [-157682, 5744, -12845, 352],
        "distinct_special_death_law_promoted": 0,
        "actor_species_promoted": 0,
        "c16_or_f14_completed": 0,
    }
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_c16_flight_death.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


@pytest.mark.local_media
def test_flight_fixture_and_context_recompute_from_central_pristine_pin():
    doc = load_artifact()
    assert flight.build_fixture_census() == doc["fixture_census"]
    assert flight.build_context_identity() == doc["context_identity"]
    assert flight.build_level08_respawn_static_policy() == doc[
        "shared_c15_level08_respawn_activation"]["static_policy"]
    assert doc["fixture_census"]["save"] == {
        "path": "level_14.sav",
        "sha256": flight.SAVE_SHA256,
        "size": 2069312,
        "media_class": "pristine",
        "manifest": "analysis/phase0_2_external_fixture_set.json",
    }
    context = doc["context_identity"]
    assert context["scene_graph"]["scene_id"] == 8
    assert context["historical_phase2_lead"]["record_index"] == 4
    assert "off-by-one" in context["historical_phase2_lead"]["qualification"]
    assert context["retained_type_word_frontier"]["owner_classification"] == \
        "unclassified_e08_or_downstream_candidate"


def test_exact_actor_call_and_response_only_control_are_bounded():
    doc = load_artifact()
    call = doc["exact_invocation"]
    assert call["entry"]["link_call_address"] == "0x8004b4a0"
    assert call["entry"]["instruction_word"] == "0x0c0129c0"
    assert call["entry"]["s1_actor_pointer"] == "0x800a0014"
    assert call["entry"]["arguments"]["a3"] == "0x00000000"
    assert call["actor_owner"]["source"] == {
        **call["actor_owner"]["source"],
        "type_word": "0x0125",
        "actor_id_low_byte": 37,
        "program_selector_high_byte": 1,
    }
    assert call["actor_contact_causally_bound"] is True

    matched = doc["matched_outcomes"]
    assert matched["response_only_mutation"]["main_ram_differences"] == [{
        "address": "0x800a0070", "before": 17, "after": 145}]
    assert matched["outcome_endpoint_identity"] == {
        "emulator_frame": True, "cycle": True, "pc": True, "sp": True}
    assert matched["natural_ordinary_respawn"]["lives"] == 2
    assert matched["response_only_final"]["lives"] == 3

    natural = doc["passive_traces"]["natural"]["traces"]["180"]
    control = doc["passive_traces"]["response_only"]["traces"]["180"]
    by_label = lambda row: {
        item["label"]: item
        for item in row["cycle_neutral_trace"]["coverage"]}
    assert "0x8005b348" in by_label(natural)[
        "respawn_transition_state_handler"]["pcs"]
    assert by_label(control)["damage_and_death_initiator"]["total_hits"] == 0
    assert by_label(control)["respawn_transition_state_handler"]["total_hits"] == 0


def test_low_level_mutations_turn_flight_evidence_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["matched_outcomes"]["natural_fatal_boundary"]["health"] = 0
    assert "natural lifecycle" in " ".join(flight.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["matched_outcomes"]["response_only_mutation"][
        "main_ram_differences"][0]["address"] = "0x800a6594"
    assert "response-only control" in " ".join(flight.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["exact_invocation"]["entry"]["s1_actor_pointer"] = "0x800a0098"
    assert "exact actor invocation" in " ".join(flight.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    coverage = mutated["passive_traces"]["response_only"]["traces"]["180"][
        "cycle_neutral_trace"]["coverage"]
    next(row for row in coverage if row["label"] ==
         "damage_and_death_initiator")["total_hits"] = 1
    assert "passive trace" in " ".join(flight.evidence_gaps(mutated))


def test_level08_activation_is_exact_complete_causal_and_falsifiable():
    doc = load_artifact()
    activation = doc["shared_c15_level08_respawn_activation"]
    assert flight._level08_activation_gaps(activation) == []
    assert activation["runtime_identity"] == {
        "address": "0x800b3ae8",
        "length": 108,
        "sha256": "4b2e8bccbcd42dcb056b267d66a35bb8b7dbfdf9171eccd1a914ff1f67b029c9",
        "pinned_sha256": "4b2e8bccbcd42dcb056b267d66a35bb8b7dbfdf9171eccd1a914ff1f67b029c9",
        "exact_pristine_match": True,
    }
    assert activation["exact_resident_call"]["pc"] == "0x8005b1a4"
    assert activation["exact_entry"]["pc"] == "0x800b3ae8"
    assert activation["writer_attribution"]["total"] == 7
    branches = {row["label"]: row for row in activation["causal_branches"]}
    assert branches["control"]["after_return"]["safe"] == {
        "x": -157682, "y": 5744, "z": -12845, "heading": 352}
    assert branches["x_source_plus_4096"]["after_return"]["safe"] == {
        "x": -153586, "y": 5744, "z": -12845, "heading": 352}
    assert branches["heading_source_plus_one"]["after_return"]["safe"] == {
        "x": -157682, "y": 5744, "z": -12845, "heading": 353}

    mutated = copy.deepcopy(activation)
    mutated["runtime_identity"]["exact_pristine_match"] = False
    assert "loaded bytes" in " ".join(flight._level08_activation_gaps(mutated))

    mutated = copy.deepcopy(activation)
    initializer = next(row for row in
                       mutated["passive_natural_trace"]["coverage"]
                       if row["label"] ==
                       "level08_fixed_safe_live_initializer")
    initializer["total_hits"] = 26
    assert "passive positive/negative" in " ".join(
        flight._level08_activation_gaps(mutated))

    mutated = copy.deepcopy(activation)
    mutated["writer_attribution"]["events"][0]["field"] = "safe_y"
    assert "direct-write attribution" in " ".join(
        flight._level08_activation_gaps(mutated))

    mutated = copy.deepcopy(activation)
    mutated["causal_branches"][1]["after_return"]["safe"]["x"] -= 1
    assert "source-constant causal" in " ".join(
        flight._level08_activation_gaps(mutated))


def test_c16_and_f14_remain_open_and_scenario_claims_only_measured_state():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "lives_gameover_continue")
    assert campaign["status"] == "active"
    coverage = phase4_coverage.build()
    assert coverage["rows"]["C16_lives_gameover"]["state"] == "open"
    assert coverage["rows"]["F14_riverbed_flight"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91

    scenario_path = ROOT / "tools/scenarios/duckstation/" \
        "pristine_riverbed_flight_actor37_death.yaml"
    scenario = ps1_scenario.load_scenario(scenario_path)
    assert scenario["anchor"]["path"] == flight.SAVE_REL
    assert len(scenario["setup"]) == 8
    assert scenario["phases"][0]["after"][0]["params"] == {
        "address": flight.ACTOR_FLAGS, "value": 0x4091}
    assert scenario["phases"][1]["assertions"][-1] == {
        "id": "flight_control_damage_call_hits", "type": "exec_hit_count",
        "watch": "response_only_damage_call", "op": "eq", "expected": 0}
    assertion_ids = {
        assertion["id"]
        for phase in scenario["phases"] for assertion in phase["assertions"]}
    assert len(assertion_ids) == 15
    assert all("species" not in assertion_id and "script" not in assertion_id
               for assertion_id in assertion_ids)

    level08_path = ROOT / "tools/scenarios/duckstation/" \
        "pristine_scene8_level08_respawn_initializer.yaml"
    level08 = ps1_scenario.load_scenario(level08_path)
    assert level08["anchor"] == {
        "type": "save_state", "path": flight.SAVE_REL,
        "sha256": flight.SAVE_SHA256}
    assert len(level08["setup"]) == 8
    level08_ids = {
        assertion["id"]
        for phase in level08["phases"] for assertion in phase["assertions"]}
    assert len(level08_ids) == 18
    assert all("species" not in assertion_id and "checkpoint_policy" not in
               assertion_id for assertion_id in level08_ids)
