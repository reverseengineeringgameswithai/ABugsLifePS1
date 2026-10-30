"""Falsification guards for the bounded C16 Bonus-3 contact-death control."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_c16_bonus_death as bonus_death  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_c16_bonus_death.json"
# Updated after the final source-dependent live regeneration.
ARTIFACT_SHA256 = "3f52b12c5da20aa14dbce47fbbc2469bad8600a6c2e52940d83acda722125768"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_bonus3_death_recomputes_from_low_level_evidence():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert bonus_death.evidence_gaps(doc) == []
    assert doc["summary"] == bonus_death.derive_summary(doc)
    assert doc["summary"]["bonus_contexts_bounded"] == 1
    assert doc["summary"]["natural_health_delta"] == -1
    assert doc["summary"]["mutation_main_ram_difference_count"] == 1
    assert doc["summary"]["fatal_health"] == -1
    assert doc["summary"]["respawn_health_lives"] == [4, 4]
    assert doc["summary"]["producer_path_id"] == "proximity_contact"
    assert doc["summary"]["coverage_required_pcs"]["all_present"] is True
    assert doc["summary"]["named_enemy_or_f18_promoted"] == 0
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_c16_bonus_death.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


@pytest.mark.local_media
def test_bonus3_fixture_and_context_recompute_from_central_pristine_pins():
    doc = load_artifact()
    assert bonus_death.build_fixture_census() == doc["fixture_census"]
    assert bonus_death.build_bonus_context_identity() == \
        doc["bonus_context_identity"]
    fixture = doc["fixture_census"]
    assert fixture["movie"]["version"] == 3
    assert fixture["movie"]["frames"] == 5020
    assert fixture["movie"]["media_class"] == "pristine"
    assert fixture["save"]["media_class"] == "pristine"
    context = doc["bonus_context_identity"]
    assert context["phase2_stage_anchor"]["scene_id"] == 3
    assert context["baseline_row"]["id"] == "F18_bonus3_grasshoppers"
    assert context["baseline_row"]["status"] == "partial"
    assert "no named grasshopper" in context["classification"]


def test_one_field_control_exact_caller_and_bounded_suffix_are_retained():
    doc = load_artifact()
    natural = doc["natural_control"]
    assert natural["before"]["snapshot"]["health"] == 1
    assert natural["after"]["snapshot"]["health"] == 0
    causal = doc["causal_health_control"]
    assert causal["mutation"]["main_ram_differences"] == [{
        "address": "0x800a6594", "before": 1, "after": 0}]
    assert causal["fatal_boundary"]["master_state"] == 2
    assert causal["completed_respawn"]["master_state"] == 0
    invocation = doc["fatal_invocation"]
    assert invocation["entry"]["link_call_address"] == "0x8004b4a0"
    assert invocation["entry"]["resolved_target"] == "0x8004a700"
    assert invocation["returned_to"] == "0x8004b4a8"
    assert invocation["caused_fatal_transition"] is True

    for row in doc["cycle_neutral_suffix_traces"]:
        trace = row["cycle_neutral_trace"]
        assert trace["comparison"]["cycle_neutral"] is True
        assert all(item["truncated"] is False for item in trace["coverage"])
    relation = doc["suffix_direct_terminal_relation"]
    assert relation == {
        "emulator_frame_equal": True,
        "pc_sp_equal": True,
        "typed_lifecycle_equal": True,
        "registers_sha256_equal": True,
        "cycle_delta_suffix_minus_direct": -1,
        "main_ram_sha256_equal": False,
        "boundary": relation["boundary"],
    }
    assert "exactly one cycle earlier" in relation["boundary"]
    derived_movie = doc["transient_suffix_recipe"]["derived_movie"]
    assert derived_movie["sha256"] == \
        "da0052f62bafa84e4509169ce14c5daf73406cb90f684c521b1e280c87582b1c"
    assert "start_state.path replaced" in derived_movie["hash_normalization"]


def test_low_level_mutations_turn_bonus3_evidence_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["natural_control"]["after"]["snapshot"]["health"] = 1
    assert "natural Bonus-3 health boundary" in " ".join(
        bonus_death.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["causal_health_control"]["mutation"][
        "main_ram_differences"][0]["address"] = "0x800a65a0"
    assert "causal Bonus-3 lifecycle" in " ".join(
        bonus_death.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["fatal_invocation"]["entry"]["link_call_address"] = "0x80000000"
    assert "fatal invocation attribution" in " ".join(
        bonus_death.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    terminal = mutated["cycle_neutral_suffix_traces"][-1]
    respawn = next(row for row in terminal["cycle_neutral_trace"]["coverage"]
                   if row["label"] == "respawn_transition_state_handler")
    respawn["pcs"].remove("0x8005b348")
    assert "decisive resident PC coverage" in " ".join(
        bonus_death.evidence_gaps(mutated))


def test_c16_remains_open_and_scenario_claims_only_measured_state():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "lives_gameover_continue")
    assert campaign["status"] == "active"
    coverage = phase4_coverage.build()
    assert coverage["rows"]["C16_lives_gameover"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91

    scenario = yaml.safe_load((ROOT / "tools/scenarios/duckstation/"
                               "pristine_bonus3_contact_death.yaml").read_text())
    assert scenario["playback"]["movie"] == \
        "movies/Bonus_Level_03.movie.json"
    assert scenario["phases"][0]["after"] == [{
        "type": "rpc", "id": "change_only_true_health_to_zero",
        "method": "debugger.writeU16",
        "params": {"address": 0x800A6594, "value": 0},
    }]
    assertion_ids = {
        assertion["id"]
        for phase in scenario["phases"] for assertion in phase["assertions"]
    }
    assert len(assertion_ids) == 15
    assert all("grasshopper" not in assertion_id
               for assertion_id in assertion_ids)
