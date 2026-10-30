"""Falsification guards for Thud's natural reward-volley evidence."""
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
import phase4_thud_volley as volley  # noqa: E402
import ps1_scenario  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_thud_volley.json"
ARTIFACT_SHA256 = "ae923a520f57caeb244c670a27385491aac8359e3077816429d8ab28c6dca05d"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_volley_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert volley.evidence_gaps(doc) == []
    assert doc["summary"] == volley.derive_summary(doc) == {
        "natural_reward_volleys": 7, "allocations_per_volley": 10,
        "total_reward_allocations": 70, "general_action20_allocations": 63,
        "special_action9_allocations": 7,
        "natural_action9_pickups": 4,
        "first_natural_action9_pickup_target": 1433,
        "first_natural_action9_health_delta": 1,
        "natural_action20_grain_pickups": 14, "final_grain": 14,
        "countdown_variant": [20, 9], "recorded_fight_frequency_bound": True,
        "d18_or_f09_completed": 0,
    }
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_thud_volley.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


@pytest.mark.local_media
def test_fixture_and_source_dependencies_remain_hash_pinned():
    doc = load_artifact()
    assert doc["fixture_census"] == volley.thud.build_fixture_census()
    assert doc["source_dependencies"] == volley._source_dependencies()
    assert doc["fixture_census"]["movie"]["sha256"] == volley.thud.MOVIE_SHA256
    assert doc["fixture_census"]["save"]["sha256"] == volley.thud.SAVE_SHA256


def test_seven_natural_volleys_have_exact_cumulative_counts():
    rows = load_artifact()["settled_boundaries"]
    assert [(row["target_movie_frame"], row["snapshot"]["phase_counter"],
             row["snapshot"]["grain"],
             row["cumulative_counts"]["0x800b3ff0"]) for row in rows] == [
        (994, 1, 0, 10), (1336, 2, 0, 20), (1736, 3, 0, 30),
        (2154, 4, 4, 40), (2548, 5, 8, 50), (2964, 6, 12, 60),
        (3334, 7, 14, 70), (3754, 8, 14, 70), (4113, 8, 14, 70),
    ]
    assert rows[-1]["cumulative_counts"] == {
        "0x80054f9c": 14, "0x800589b8": 14, "0x800b3f24": 70,
        "0x800b3f34": 7, "0x800b3f7c": 63, "0x800b3ff0": 70,
        "0x800b3ffc": 70, "0x80058864": 4, "0x80058890": 4,
    }
    assert all(row["cycle_neutral_trace"]["comparison"]["cycle_neutral"]
               is True for row in rows)
    assert rows[-1]["snapshot"]["reward_pool"] == {
        "active_action9_count": 0, "active_action20_count": 0,
        "active_action9_or_20": [],
    }


def test_countdown_control_causally_selects_action9_variant():
    control = load_artifact()["matched_variant_control"]
    assert control["origin_equal"] and all(control["origin_equal"].values())
    assert control["single_field"]["address"] == "0x800b4cb4"
    assert (control["single_field"]["before"],
            control["single_field"]["after"]) == (9, 6)
    assert control["single_field"]["write_differences"] == [
        {"address": "0x800b4cb4", "before": 9, "after": 6}]
    assert control["endpoint_timing_equal"] == {
        "emulator_frame": True, "cycle": False, "movie_frame": True,
        "pc": True, "sp": True,
    }
    assert control["endpoint_cycle_delta_mutation_minus_control"] == -1
    natural = control["control_after"]["slot17"]
    mutation = control["mutation_after"]["slot17"]
    assert (natural["action_id"], natural["lifetime_ttl"], natural["state"]) == \
        (20, 200, 24)
    assert (mutation["action_id"], mutation["lifetime_ttl"],
            mutation["state"], mutation["damage_class"]) == (9, 200, -42, 128)
    runtime = control["runtime_identity"]
    assert (runtime["address"], runtime["length"], runtime["sha256"]) == (
        "0x800b3ed4", 308, volley.thud.POST_RESTORE_CONTINUATION_SHA256)


def test_natural_action9_pickup_increments_true_health_at_exact_boundary():
    doc = load_artifact()
    pre, post = doc["first_natural_action9_pickup"]
    assert (pre["target_movie_frame"], post["target_movie_frame"]) == (1432, 1433)
    assert (pre["snapshot"]["movie_frame"], post["snapshot"]["movie_frame"]) == \
        (1431, 1432)
    assert (pre["snapshot"]["health"], post["snapshot"]["health"]) == (2, 3)
    assert (pre["cumulative_counts"]["0x80058864"],
            post["cumulative_counts"]["0x80058864"]) == (0, 1)
    assert (pre["cumulative_counts"]["0x80058890"],
            post["cumulative_counts"]["0x80058890"]) == (0, 1)
    for row, ttl in ((pre, 62), (post, 1)):
        action9 = [record for record in
                   row["snapshot"]["reward_pool"]["active_action9_or_20"]
                   if record["action_id"] == 9]
        assert action9 == [{
            "slot": 47, "action_id": 9, "lifetime_ttl": ttl,
            "position": [126549, -348, -14770], "velocity": [0, 0, 0],
            "radius_add": 100, "state": 7, "flags": 226,
        }]
        assert row["cycle_neutral_trace"]["comparison"]["cycle_neutral"] is True
    static = doc["static_action9_handler"]
    assert (static["address"], static["length"], static["sha256"]) == (
        "0x80058864", 56, volley.ACTION9_HANDLER_SHA256)
    assert {name: row["word"] for name, row in
            static["decisive_words"].items()} == {
        "handler_state_7": "0x24100007", "health_load": "0x94620000",
        "health_increment": "0x24420001", "health_store": "0xa4620000",
    }


def test_guard_mutations_are_rejected():
    doc = load_artifact()
    changed = copy.deepcopy(doc)
    changed["settled_boundaries"][-1]["cumulative_counts"]["0x800b3f34"] = 6
    assert "Thud volley final exact execution counts changed" in \
        volley.evidence_gaps(changed)
    changed = copy.deepcopy(doc)
    changed["matched_variant_control"]["mutation_after"]["slot17"]["action_id"] = 20
    assert "Thud volley action variant outcome changed" in volley.evidence_gaps(changed)
    changed = copy.deepcopy(doc)
    changed["first_natural_action9_pickup"][1]["snapshot"]["health"] = 2
    assert "Thud first natural action-9 pickup outcome changed" in \
        volley.evidence_gaps(changed)
    changed = copy.deepcopy(doc)
    changed["summary"]["d18_or_f09_completed"] = 1
    assert "Thud volley derived summary changed" in volley.evidence_gaps(changed)


def test_reward_variant_scenario_is_declarative_and_bounded():
    scenario = ps1_scenario.load_scenario(
        ROOT / "tools/scenarios/duckstation/"
        "pristine_thud_reward_variant_control.yaml")
    assert scenario["id"] == "pristine_thud_reward_variant_control"
    assert scenario["target"]["expected_serial"] == "SCUS-94288"
    assert scenario["playback"]["movie"] == "thud_boss_movie.movie.json"
    assert [row["trigger"]["target"] for row in scenario["phases"]] == [969, 970]
    write = scenario["phases"][0]["after"][0]
    assert (write["method"], write["params"]) == (
        "debugger.writeU32", {"address": 0x800B4CB4, "value": 6})
    assertions = {row["id"]: row for row in scenario["phases"][1]["assertions"]}
    assert assertions["volley_variant_slot17_action"]["expected"] == 9
    assert assertions["volley_variant_slot17_ttl"]["expected"] == 200


def test_natural_action9_scenario_is_declarative_and_read_only():
    scenario = ps1_scenario.load_scenario(
        ROOT / "tools/scenarios/duckstation/"
        "pristine_thud_action9_natural_pickup.yaml")
    assert scenario["id"] == "pristine_thud_action9_natural_pickup"
    assert scenario["target"]["expected_serial"] == "SCUS-94288"
    assert scenario["playback"]["movie"] == "thud_boss_movie.movie.json"
    assert [row["trigger"]["target"] for row in scenario["phases"]] == [1431, 1432]
    assert all("after" not in row for row in scenario["phases"])
    before = {row["id"]: row for row in scenario["phases"][0]["assertions"]}
    after = {row["id"]: row for row in scenario["phases"][1]["assertions"]}
    assert before["action9_pre_health"]["expected"] == 2
    assert before["action9_pre_slot47_ttl"]["expected"] == 62
    assert after["action9_post_health"]["expected"] == 3
    assert after["action9_post_slot47_ttl"]["expected"] == 1
