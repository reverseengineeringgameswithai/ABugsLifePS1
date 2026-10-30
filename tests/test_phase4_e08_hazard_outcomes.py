"""Guards for cycle-neutral E08 routing from existing E10 hazard leads."""
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

import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_e08_hazard_outcomes as hazards  # noqa: E402
import ps1_scenario  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_e08_hazard_outcomes.json"
ARTIFACT_SHA256 = "4c26dbd2bbc35366d66ca6b9338a9b52a3308ea647ec02e15a4cbd55f4a5d5db"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_e10_hazard_fixture_census_recomputes_from_central_pins():
    retained = load_artifact()["fixture_census"]
    assert hazards.build_fixture_census() == retained
    assert retained["count"] == 8
    assert all(row["movie"]["version"] == 3 for row in retained["pairs"])
    assert all(row["save"]["media_class"] == "pristine"
               for row in retained["pairs"])


def test_retained_hazard_outcomes_recompute_from_low_level_boundaries():
    document = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert hazards.evidence_gaps(document) == []
    summary = document["summary"]
    assert summary["movies_replayed"] == 8
    assert summary["replays_with_health_or_lives_change"] == 8
    assert summary["controlled_type_words"] == []
    assert summary["newly_controlled_unclassified_type_words"] == []
    assert summary["unclassified_with_native_outcome_controls"] == 19
    assert summary["unclassified_without_native_outcome_control"] == 28
    assert summary["unclassified_with_native_outcome_controls"] + \
        summary["unclassified_without_native_outcome_control"] == 47
    assert summary["row_or_class_owners_promoted"] == 0
    assert all(
        replay["cycle_neutral_trace"]["comparison"]["cycle_neutral"] is True
        for replay in document["replays"])


def test_low_level_player_and_trace_mutations_turn_hazard_evidence_red():
    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["replays"][0]["player_delta"]["changed_fields"] = {}
    assert "player delta" in " ".join(hazards.evidence_gaps(mutated))

    mutated = copy.deepcopy(document)
    mutated["replays"][0]["cycle_neutral_trace"]["comparison"][
        "cycle_neutral"] = False
    assert "cycle-neutral trace" in " ".join(hazards.evidence_gaps(mutated))

    mutated = copy.deepcopy(document)
    mutated["summary"]["row_or_class_owners_promoted"] = 1
    assert "partition" in " ".join(hazards.evidence_gaps(mutated))

    mutated = copy.deepcopy(document)
    activation = mutated["shared_c15_level06_respawn_activation"]
    activation["passive_boundary"]["after"]["cycle_neutral_trace"][
        "coverage"][0]["total_hits"] = 41
    assert "activation coverage" in " ".join(hazards.evidence_gaps(mutated))

    mutated = copy.deepcopy(document)
    activation = mutated["shared_c15_level06_respawn_activation"]
    activation["causal_branches"][1]["after_return"]["safe"]["x"] = 35329
    assert "causal field effects" in " ".join(hazards.evidence_gaps(mutated))


@pytest.mark.local_media
def test_scene6_level06_activation_recomputes_from_low_level_evidence():
    activation = load_artifact()["shared_c15_level06_respawn_activation"]
    assert activation["static_policy"] == \
        hazards.build_level06_respawn_static_policy()
    assert hazards._level06_activation_gaps(activation) == []
    assert activation["runtime_identity"]["sha256"] == \
        "33b21c83ad52f8ef13786de5ff7d48ed615fcae8618d7c8833b64c6b481656be"
    assert [event["instruction_pc"] for event in
            activation["writer_attribution"]["events"]] == [
                "0x800b3b00", "0x800b3b24", "0x800b3b30", "0x800b3b3c"]
    assert [branch["after_return"]["safe"] for branch in
            activation["causal_branches"]] == [
        {"x": 35329, "y": -85228, "z": -154696, "heading": 3063},
        {"x": 93783, "y": -85228, "z": -154696, "heading": 3063},
        {"x": 35329, "y": -83752, "z": -154696, "heading": 3063},
        {"x": 35329, "y": -85228, "z": -134554, "heading": 3063},
        {"x": 35329, "y": -85228, "z": -154696, "heading": 3064},
    ]


@pytest.mark.local_media
def test_scene6_level06_activation_is_banked_as_a_declarative_scenario():
    path = ROOT / (
        "tools/scenarios/duckstation/"
        "pristine_scene6_level06_respawn_initializer.yaml")
    scenario = yaml.safe_load(path.read_text())
    ps1_scenario.validate_scenario(scenario)
    assertions = [row for phase in scenario["phases"]
                  for row in phase["assertions"]]
    assert [phase["trigger"]["target"] for phase in scenario["phases"]] == [
        487, 489]
    assert len(assertions) == 16
    assert scenario["phases"][0]["after"] == [{
        "type": "exec_trace_start", "id": "level06_fixed_initializer_entry",
        "pc": 0x800B3AEC, "capture": ["pc", "ra", "v1"], "max_events": 4,
    }]
    movie = ROOT / scenario["playback"]["movie"]
    save_rel, save = ps1_scenario.central_state_fixture(
        movie.with_suffix(".sav"))
    assert save_rel == \
        "movies/Phase4/E10/hazard_ground_bird_LEVEL04.movie.sav"
    assert save["sha256"] == \
        "ff1c5fb1a2779ebf82caed0fd1777b8549685becdbf6d24072d3f78dec91caf1"


def test_hazard_leads_do_not_complete_e08_or_promote_filename_owners():
    document = load_artifact()
    assert document["bounded_interpretation"]["forbidden_claim"].startswith(
        "Do not assign E08/E10 ownership")
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "props_movers_gates")
    assert campaign["status"] == "active"
    assert common.audit_campaign(campaign, registry, common.finding_index()) == [
        "props_movers_gates: status is not completed"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["E08_props_movers_gates"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91
