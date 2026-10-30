"""Falsification guards for the bounded C16 Thud boulder death path."""
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
import phase4_c16_thud_boulder_death as boulder  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import ps1_scenario  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_c16_thud_boulder_death.json"
ARTIFACT_SHA256 = "2edd2e159b05476b929469d35055542741375af4e8ce6c77908872e476a6a5be"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_thud_boulder_evidence_recomputes_from_low_level_rows():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert boulder.evidence_gaps(doc) == []
    assert doc["summary"] == boulder.derive_summary(doc)
    assert doc["summary"] == {
        "movies_replayed": 1,
        "arena_row": 4,
        "natural_health_delta": -1,
        "mutation_main_ram_difference_count": 1,
        "fatal_health_lives_master": [-1, 0, 2],
        "natural_and_fatal_row_calls_bound": True,
        "boss_arena_final_life_paths_bounded": 1,
        "death_class_promoted": 0,
        "c16_d18_or_f09_completed": 0,
    }
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_c16_thud_boulder_death.py").read_bytes()
    ).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(
        doc, require_selection=False) == []


@pytest.mark.local_media
def test_fixture_and_context_recompute_from_pristine_pins():
    doc = load_artifact()
    assert boulder.build_fixture_census() == doc["fixture_census"]
    assert boulder.build_context_identity() == doc["context_identity"]
    fixture = doc["fixture_census"]
    assert fixture["movie"]["sha256"] == boulder.thud.MOVIE_SHA256
    assert fixture["movie"]["media_class"] == "pristine_serial"
    assert fixture["save"]["sha256"] == boulder.thud.SAVE_SHA256
    assert fixture["save"]["media_class"] == "pristine"
    context = doc["context_identity"]
    assert context["scene_graph"]["scene_id"] == 14
    assert context["scene_graph"]["phase2_stage_labels"] == [
        "stage09_bug_bar"]
    assert context["retained_arena_evidence"]["trace_cycle_neutral"] is True
    assert context["retained_arena_evidence"]["inside_threshold"] == [
        False, True]


def test_natural_and_fatal_exact_calls_share_the_row4_overlay_caller():
    doc = load_artifact()
    for key, health in (("natural", (3, 2, 0)), ("fatal", (0, -1, 2))):
        row = doc["exact_invocations"][key]
        assert row["entry"] == {
            "pc": "0x8004a700", "ra": "0x800b4ae8",
            "link_call_address": "0x800b4ae0",
            "instruction_word": "0x0c0129c0",
            "resolved_target": "0x8004a700",
            "arguments": {
                "a0": "0x00000000", "a1": "0xffffff2f",
                "a2": "0x801fff18", "a3": "0x00000000"},
            "loop_terminal_register": "0x00000006",
            "inside_rows": [4],
        }
        assert row["before_call"]["player_health"] == health[0]
        assert row["after_return"]["player_health"] == health[1]
        assert row["after_return"]["master_state"] == health[2]
        assert row["row_contact_causally_bound"] is True

    matched = doc["matched_outcomes"]
    assert matched["one_field_control"]["main_ram_differences"] == [{
        "address": "0x800a6594", "before": 3, "after": 0}]
    assert matched["natural_nonfatal"]["snapshot"]["player_health"] == 2
    assert (matched["final_life_death"]["snapshot"]["player_health"],
            matched["final_life_death"]["snapshot"]["lives"],
            matched["final_life_death"]["snapshot"]["master_state"]) == (
                -1, 0, 2)


def test_low_level_mutations_turn_thud_boulder_evidence_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["matched_outcomes"]["one_field_control"][
        "main_ram_differences"][0]["address"] = "0x800a65a0"
    assert "one-field mutation" in " ".join(boulder.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["exact_invocations"]["fatal"]["entry"]["inside_rows"] = [3, 4]
    assert "fatal Thud boulder invocation" in " ".join(
        boulder.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["matched_outcomes"]["final_life_death"]["snapshot"][
        "master_state"] = 0
    assert "matched outcome" in " ".join(boulder.evidence_gaps(mutated))


def test_c16_stays_open_and_scenario_claims_only_measured_state():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "lives_gameover_continue")
    assert campaign["status"] == "active"
    assert boulder.thud.MOVIE_REL in campaign["oracle_fixtures"]
    assert boulder.thud.SAVE_REL in campaign["oracle_fixtures"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["C16_lives_gameover"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91

    scenario = ps1_scenario.load_scenario(
        ROOT / "tools/scenarios/duckstation/"
        "pristine_thud_boulder_final_life.yaml")
    assert scenario["playback"]["movie"] == boulder.thud.MOVIE_REL
    assert scenario["phases"][0]["after"] == [{
        "type": "rpc", "id": "change_only_true_health_to_zero",
        "method": "debugger.writeU16",
        "params": {"address": 0x800A6594, "value": 0},
    }]
    assertion_ids = {
        assertion["id"]
        for phase in scenario["phases"] for assertion in phase["assertions"]
    }
    assert len(assertion_ids) == 13
    assert all("scripted" not in item and "special" not in item
               for item in assertion_ids)
