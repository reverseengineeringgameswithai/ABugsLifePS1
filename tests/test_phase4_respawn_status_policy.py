"""Falsification guards for C15 status-mask denial breadth."""
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
import phase4_respawn_status_policy as policy  # noqa: E402
import ps1_scenario  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_respawn_status_policy.json"
RECONCILIATION = ROOT / "analysis/phase4_capsule_consumer_reconciliation.json"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_status_policy_recomputes_low_level_predicates():
    doc = load_artifact()
    reconciliation = json.loads(RECONCILIATION.read_text())
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == \
        reconciliation["artifact_sha256_after"]
    assert policy.evidence_gaps(doc) == []
    run = doc["run_provenance"]
    assert run["generator_sha256"] == \
        reconciliation["historical_live_generator_sha256"]
    assert reconciliation["current_generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_respawn_status_policy.py").read_bytes()).hexdigest()
    assert run["duckstation"] == {
        **run["duckstation"],
        "revision": "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5",
        "binary_sha256": (
            "91cbe22b2c2e22ad83d695988ada36bbabb22c65366cb5ec9e8e30784de93af6"),
    }
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


@pytest.mark.local_media
def test_fixture_static_and_capsule_joins_recompute_from_hash_pins():
    doc = load_artifact()
    assert policy.build_fixture_census() == doc["fixture_census"]
    assert policy.build_static_census() == doc["static_census"]
    capsule = policy.build_capsule_first_census(verify_external=False)
    assert capsule["preservation_index_sha256"] == \
        doc["capsule_first_lane"]["preservation_index_sha256"]
    assert capsule["offline_reader_sha256"] == policy.CAPSULE_READER_SHA256
    assert capsule["capsule_count"] == capsule["movie_count"] == 55
    assert capsule["freshness_validator"]["observed_output"].startswith(
        "PASS: 55/55 capsules")
    retained = {row["id"]: row for row in
                doc["capsule_first_lane"]["relevant_capsules"]}
    assert retained["scene_10_pit"]["movie_sha256"] == \
        "c049d9b8075f458f87301134a3cb9998137ae0a82fa5d8d5516dd05b69c99e24"
    assert retained["scene_4_pit"]["movie_sha256"] == \
        "a06c81943700db5bd4e570165d54b098e54c67644cb116fde826bf75db8fee99"
    assert [(row["queries"][0]["typed_result"]["player_status_word"],
             row["queries"][1]["typed_result"]["player_status_word"])
            for row in retained.values()] == [(0x0014, 0x0000), (0x0014, 0x0000)]


def test_exact_one_byte_denials_and_coverage_are_pinned():
    rows = {row["id"]: row for row in load_artifact()["live_cases"]}
    expected = {
        "scene_10_pit": {
            "control": ([-159648, 3628, 1182816], 279, 70,
                        "69862fc68eb617863ab44f7aece54207be1d3b2b64b1461938b10bf6d0230a06"),
            "denial": ([-103436, -4903, 1209759], 14, 14,
                       "17e1bea8f71268382185f61fe0101ea6ec5012ab314333ed8d1b9b6925d4be52"),
            "handler": (766, 136,
                        "7bde93c8dacdf5408edd3eaebb36c7dd6befd1b4efa0b24dcb35f7ff5b645d56"),
        },
        "scene_4_pit": {
            "control": ([727892, 9584, 165941], 31, 31,
                        "7730ff9193091ef95f765f3bf7ce2d98a9188748ad7f2e541b04c377c3b79bb5"),
            "denial": ([744984, 4861, 139049], 13, 13,
                       "1308454b8d41f86727b08f05d737311f87dd9cc5003f1fac65123d518bb7f153"),
            "handler": (768, 138,
                        "3071281b585cee73a428b686ecbf20b9c1e38041b627f93dc784babb69c84d78"),
        },
    }
    for case_id, wanted in expected.items():
        row = rows[case_id]
        assert row["single_variable_guard"]["changed_byte_addresses"] == [
            "0x800A6590"]
        control = row["branches"]["natural_status_control"]["post_reset"]
        denial = row["branches"]["status_bit_0x0010_cleared"]["post_reset"]
        for name, branch in (("control", control), ("denial", denial)):
            coverage = {item["label"]: item for item in
                        branch["cycle_neutral_trace"]["coverage"]}
            writer = coverage["transition_writer"]
            assert (branch["snapshot"]["safe_anchor_xyz"],
                    writer["total_hits"], writer["distinct_pc_count"],
                    writer["pcs_sha256"]) == wanted[name]
            handler = coverage["respawn_transition_state_handler"]
            assert (handler["total_hits"], handler["distinct_pc_count"],
                    handler["pcs_sha256"]) == wanted["handler"]
        assert row["coverage_relation"]["resident_handler_exactly_equal"] is True


def test_status_policy_falsification_mutations_turn_red():
    doc = load_artifact()

    mutated = copy.deepcopy(doc)
    mutated["live_cases"][0]["single_variable_guard"][
        "changed_byte_addresses"].append("0x800A6591")
    assert "one-byte status diff" in " ".join(policy.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    denial = mutated["live_cases"][0]["branches"][
        "status_bit_0x0010_cleared"]["post_reset"]
    denial["snapshot"]["live_xyz"][0] += 1
    assert "retain prior tuple" in " ".join(policy.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    coverage = mutated["live_cases"][1]["branches"][
        "status_bit_0x0010_cleared"]["post_reset"][
            "cycle_neutral_trace"]["coverage"]
    writer = next(row for row in coverage if row["label"] == "transition_writer")
    writer["pcs"].append("0x800b3c94")
    assert "denial executed" in " ".join(policy.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live_cases"][1]["coverage_relation"][
        "resident_handler_exactly_equal"] = False
    assert "handler coverage diverged" in " ".join(policy.evidence_gaps(mutated))


def test_status_denial_scenarios_validate_and_pin_central_fixtures():
    expected = {
        "pristine_scene10_pit_status_denial.yaml": (
            {144, 145},
            "959bf87da9deb91fbdb1633175aebefc9de329d5aa4d7ef9ce18df0f34bc6a06"),
        "pristine_scene4_pit_status_denial.yaml": (
            {204, 205},
            "9e2cee6d4847c758ad6bae1e396fd7de31830f5b55220e63719a50cc1806973a"),
    }
    for name, (targets, fixture_sha) in expected.items():
        path = ROOT / "tools/scenarios/duckstation" / name
        scenario = ps1_scenario.load_scenario(path)
        assert sum(len(phase["assertions"])
                   for phase in scenario["phases"]) == 22
        assert {phase["trigger"]["target"]
                for phase in scenario["phases"]} == targets
        assert scenario["phases"][0]["after"][0] == {
            "type": "rpc",
            "id": scenario["phases"][0]["after"][0]["id"],
            "method": "debugger.writeU16",
            "params": {"address": 0x800A6590, "value": 4},
        }
        save = Path(scenario["playback"]["movie"]).with_suffix(".sav")
        _, fixture = ps1_scenario.central_state_fixture(ROOT / save)
        assert fixture["media_class"] == "pristine"
        assert fixture["sha256"] == fixture_sha


def test_status_policy_schema_keeps_generalization_gaps_open():
    schema = yaml.safe_load(
        (ROOT / "config/phase4_respawn_status_policy.yaml").read_text())
    assert schema["schema"] == "abl-phase4-respawn-status-policy/1"
    assert schema["campaign_state"] == "active_partial"
    assert schema["artifact"] == {
        "path": "analysis/phase4_respawn_status_policy.json",
        "sha256": hashlib.sha256(ARTIFACT.read_bytes()).hexdigest(),
    }
    assert schema["known_status_gated_writers"] == [
        "LEVEL03 nearest-row selector",
        "LEVEL10 nearest-row selector",
        "LEVEL04 fixed-tuple selector",
    ]
    assert set(schema["still_open"]) == {
        "Source, setter/clearer, whole-word semantics and general activation policy of status mask 0x0010.",
        "Indirect/additional overlay writers, other actor/scripted/exceptional death classes, remaining stages and lifecycle persistence.",
    }
