"""Falsification guards for the exact Thud completion request evidence."""
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
import phase4_thud_completion as completion  # noqa: E402
import ps1_scenario  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_thud_completion.json"
ARTIFACT_SHA256 = "95a7fa0bcf04244fbb91724413e489023cf297373851df3d77904923c4b5c937"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_completion_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert completion.evidence_gaps(doc) == []
    assert doc["summary"] == completion.derive_summary(doc) == {
        "request_instruction_pc": "0x800b3e84",
        "fade_instruction_pc": "0x800b3e90",
        "counter_transition": [7, 8],
        "master_state_transition": [0, 1],
        "fade_timer_transition": [0, 149],
        "natural_vs_suppressed_scene": [0, 14],
        "natural_vs_suppressed_master_state": [1, 0],
        "retirement_suffix_equal": True,
        "exact_completion_request_bound": True,
        "d18_or_f09_completed": 0,
    }
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_thud_completion.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(
        doc, require_selection=False) == []


@pytest.mark.local_media
def test_fixture_and_source_dependencies_remain_hash_pinned():
    doc = load_artifact()
    assert doc["fixture_census"] == completion.thud.build_fixture_census()
    assert doc["source_dependencies"] == completion._source_dependencies()
    assert doc["fixture_census"]["movie"]["sha256"] == \
        completion.thud.MOVIE_SHA256
    assert doc["fixture_census"]["save"]["sha256"] == \
        completion.thud.SAVE_SHA256


def test_passive_boundaries_bind_request_retirement_and_exit():
    rows = load_artifact()["passive_boundaries"]
    observed = {
        label: (row["target_movie_frame"], row["snapshot"]["movie_frame"],
                row["snapshot"]["scene"], row["snapshot"]["master_state"],
                row["snapshot"]["fade_timer"],
                row["snapshot"]["phase_counter"],
                row["snapshot"]["actor_hp"],
                row["snapshot"]["actor_flags"],
                row["snapshot"]["live_table_0"])
        for label, row in rows.items()
    }
    assert observed == {
        "before_request": (3739, 3738, 14, 0, 0, 7, 48,
                           "0x4055", "0x8009fd80"),
        "after_request": (3742, 3741, 14, 1, 149, 8, 50,
                          "0x4055", "0x8009fd80"),
        "retired": (3903, 3902, 14, 1, 68, 8, 0,
                    "0x0055", "0x00000000"),
        "scene_exit": (4042, 4041, 0, 1, 0, 8, 0,
                       "0x0055", "0x00000000"),
    }
    assert all(row["cycle_neutral_trace"]["comparison"]["cycle_neutral"]
               is True for row in rows.values())
    pcs = set(rows["after_request"]["cycle_neutral_trace"]
              ["coverage"][0]["pcs"])
    assert {"0x800b3db0", "0x800b3db4", "0x800b3e84",
            "0x800b3e90"}.issubset(pcs)


def test_runtime_slice_and_exact_writers_are_bound():
    doc = load_artifact()
    runtime = doc["matched_request_control"]["runtime_identity"]
    assert (runtime["address"], runtime["length"],
            runtime["instruction_count"], runtime["sha256"]) == (
                "0x800b3d9c", 0xFC, 63,
                completion.RUNTIME_SLICE_SHA256)
    decisive = runtime["decisive_instructions"]
    assert decisive["0x800b3db0"]["bytes"] == "ac224cc8"
    assert decisive["0x800b3db4"]["bytes"] == "14430039"
    assert decisive["0x800b3e84"]["bytes"] == "a42223a0"
    assert decisive["0x800b3e90"]["bytes"] == "a4222470"
    writers = doc["writer_attribution"]["decisive_writers"]
    assert (writers["master_state_request"]["instruction_pc"],
            writers["master_state_request"]["value"],
            writers["master_state_request"]["new_value"]) == (
                "0x800b3e84", 0, 1)
    assert (writers["fade_timer_request"]["instruction_pc"],
            writers["fade_timer_request"]["value"],
            writers["fade_timer_request"]["new_value"]) == (
                "0x800b3e90", 0, 150)


def test_single_instruction_control_preserves_retirement_and_blocks_exit():
    matched = load_artifact()["matched_request_control"]
    assert matched["origin_equal"] and all(matched["origin_equal"].values())
    single = matched["single_instruction"]
    assert (single["address"], single["before_word"], single["after_word"],
            single["rpc"]["written"],
            single["rpc"]["code_invalidated"]) == (
                "0x800b3e84", "0xa42223a0", "0x00000000", 4, True)
    assert {row["address"] for row in single["write_differences"]} == {
        f"0x{completion.REQUEST_STORE + offset:08x}" for offset in range(4)}
    control = [row["snapshot"] for row in matched["control"]]
    mutation = [row["snapshot"] for row in matched["mutation"]]
    assert (control[0]["scene"], control[0]["master_state"],
            control[0]["fade_timer"], control[0]["phase_counter"]) == (
                14, 1, 149, 8)
    assert (mutation[0]["scene"], mutation[0]["master_state"],
            mutation[0]["fade_timer"], mutation[0]["phase_counter"]) == (
                14, 0, 149, 8)
    retirement = ("actor_hp", "actor_flags", "live_table_0",
                  "player_position", "actor_position")
    assert all(control[1][key] == mutation[1][key] for key in retirement)
    assert (control[2]["scene"], mutation[2]["scene"]) == (0, 14)
    assert (control[2]["master_state"], mutation[2]["master_state"]) == (1, 0)
    assert all(control[2][key] == mutation[2][key] for key in retirement)


def test_guard_mutations_are_rejected():
    doc = load_artifact()
    changed = copy.deepcopy(doc)
    changed["matched_request_control"]["mutation"][2]["snapshot"]["scene"] = 0
    assert "Thud completion causal scene-exit outcome changed" in \
        completion.evidence_gaps(changed)
    changed = copy.deepcopy(doc)
    changed["writer_attribution"]["decisive_writers"] \
        ["master_state_request"]["instruction_pc"] = "0x800b3e80"
    assert "Thud master_state_request attribution changed" in \
        completion.evidence_gaps(changed)
    changed = copy.deepcopy(doc)
    changed["summary"]["d18_or_f09_completed"] = 1
    assert "Thud completion derived summary changed" in \
        completion.evidence_gaps(changed)


def test_completion_control_scenario_is_declarative_and_bounded():
    scenario = ps1_scenario.load_scenario(
        ROOT / "tools/scenarios/duckstation/"
        "pristine_thud_completion_request_control.yaml")
    assert scenario["id"] == "pristine_thud_completion_request_control"
    assert scenario["target"]["expected_serial"] == "SCUS-94288"
    assert scenario["playback"]["movie"] == "thud_boss_movie.movie.json"
    phases = scenario["phases"]
    assert [row["trigger"]["target"] for row in phases] == \
        [3738, 3740, 3900, 4040]
    write = phases[0]["after"][0]
    assert (write["method"], write["params"]) == (
        "debugger.writeU32", {"address": 0x800B3E84, "value": 0})
    final = {row["id"]: row for row in phases[-1]["assertions"]}
    assert final["completion_suppressed_scene_retained"]["expected"] == 14
    assert final["completion_suppressed_live_slot_remains_clear"]["expected"] == 0
