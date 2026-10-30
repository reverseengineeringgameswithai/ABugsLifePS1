"""Falsification guards for the actor-owned C16 Thumper death control."""
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
import phase4_c16_thumper_death as thumper  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import ps1_scenario  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_c16_thumper_death.json"
# Updated after the final source-dependent live regeneration.
ARTIFACT_SHA256 = "04121d81e349a8ebec58bc8b8db5bbccc45b1c364c6a0306319b7e572bf8d8f8"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_thumper_death_recomputes_from_low_level_evidence():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert thumper.evidence_gaps(doc) == []
    assert doc["summary"] == thumper.derive_summary(doc)
    assert doc["summary"] == {
        "movies_replayed": 1,
        "natural_health_delta": -1,
        "mutation_main_ram_difference_count": 1,
        "fatal_health": -1,
        "ordinary_respawn_health_lives": [4, 3],
        "producer_path_id": "proximity_contact",
        "actor_owner_id": 16,
        "actor_owner_address": "0x8009fe04",
        "natural_and_fatal_actor_bound": True,
        "boss_actor_causation_bounded": 1,
        "d16_or_f03_completed": 0,
    }
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_c16_thumper_death.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


@pytest.mark.local_media
def test_thumper_fixture_and_context_recompute_from_central_pristine_pins():
    doc = load_artifact()
    assert thumper.build_fixture_census() == doc["fixture_census"]
    assert thumper.build_context_identity() == doc["thumper_context_identity"]
    fixture = doc["fixture_census"]
    assert fixture["movie"]["sha256"] == thumper.MOVIE_SHA256
    assert fixture["movie"]["media_class"] == "pristine_serial"
    assert fixture["save"]["sha256"] == thumper.SAVE_SHA256
    assert fixture["save"]["media_class"] == "pristine"
    context = doc["thumper_context_identity"]
    assert context["scene_graph"]["scene_id"] == 2
    assert context["scene_graph"]["phase2_stage_labels"] == [
        "stage03_council_chamber"]
    assert context["required_mechanics_consumers"] == [
        "mechanics:C16_lives_gameover", "mechanics:D16_thumper"]


def test_exact_natural_and_fatal_calls_bind_the_live_thumper_actor():
    doc = load_artifact()
    natural = doc["exact_invocations"]["natural"]
    fatal = doc["exact_invocations"]["fatal"]
    for row, health_pair in ((natural, (4, 3)), (fatal, (0, -1))):
        assert row["entry"] == {
            "pc": "0x8004a700", "ra": "0x8004b4a8",
            "link_call_address": "0x8004b4a0",
            "instruction_word": "0x0c0129c0",
            "resolved_target": "0x8004a700",
            "arguments": {
                "a0": "0xfffffab4", "a1": "0xfffffb71",
                "a2": "0x801fff40", "a3": "0x00000000"},
            "s1_actor_pointer": "0x8009fe04",
        }
        actor = row["actor_owner"]
        assert (actor["pool_slot"], actor["id"], actor["xyz"], actor["hp"],
                actor["callback"], actor["authored_record_backlink"]) == (
                    1, 16, [8935, 51936, -623], 24,
                    "0x8004a0f4", "0x80094a54")
        neighbor = row["neighbor_control"]
        assert (neighbor["pool_slot"], neighbor["id"],
                neighbor["callback"]) == (2, 10, "0x8004a180")
        assert row["before_call"]["health"] == health_pair[0]
        assert row["after_return"]["health"] == health_pair[1]
        assert row["actor_causally_bound"] is True

    lifecycle = doc["one_field_fatal_lifecycle"]
    assert lifecycle["mutation"]["main_ram_differences"] == [{
        "address": "0x800a6594", "before": 4, "after": 0}]
    assert lifecycle["fatal_boundary"]["master_state"] == 2
    assert (lifecycle["ordinary_respawn"]["scene"],
            lifecycle["ordinary_respawn"]["health"],
            lifecycle["ordinary_respawn"]["lives"]) == (2, 4, 3)


def test_low_level_mutations_turn_thumper_evidence_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["natural_control"]["after"]["snapshot"]["health"] = 4
    assert "natural Thumper damage boundary" in " ".join(
        thumper.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["one_field_fatal_lifecycle"]["mutation"][
        "main_ram_differences"][0]["address"] = "0x800a65a0"
    assert "one-field Thumper fatal lifecycle" in " ".join(
        thumper.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["exact_invocations"]["fatal"]["entry"][
        "s1_actor_pointer"] = "0x8009fe88"
    assert "fatal Thumper actor attribution" in " ".join(
        thumper.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["natural_control"]["after"]["cycle_neutral_trace"][
        "comparison"]["cycle_neutral"] = False
    assert "natural Thumper trace neutrality" in " ".join(
        thumper.evidence_gaps(mutated))


def test_c16_remains_open_and_scenario_claims_only_measured_state():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "lives_gameover_continue")
    assert campaign["status"] == "active"
    coverage = phase4_coverage.build()
    assert coverage["rows"]["C16_lives_gameover"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91

    scenario_path = ROOT / "tools/scenarios/duckstation/" \
        "pristine_thumper_actor_death.yaml"
    scenario = ps1_scenario.load_scenario(scenario_path)
    assert scenario["playback"]["movie"] == thumper.MOVIE_REL
    assert scenario["phases"][0]["after"] == [{
        "type": "rpc", "id": "change_only_true_health_to_zero",
        "method": "debugger.writeU16",
        "params": {"address": 0x800A6594, "value": 0},
    }]
    assertion_ids = {
        assertion["id"]
        for phase in scenario["phases"] for assertion in phase["assertions"]
    }
    assert len(assertion_ids) == 16
    assert all("defeat" not in assertion_id and "phase" not in assertion_id
               for assertion_id in assertion_ids)
