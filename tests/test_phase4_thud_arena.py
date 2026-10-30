"""Falsification guards for the six-row Thud rolling-arena evidence."""
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
import phase4_thud_arena as arena  # noqa: E402
import ps1_scenario  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_thud_arena.json"
ARTIFACT_SHA256 = "5680b4cb34b9af76f03850ce541126cc0c8d73d4ffd32190fd286e13100f723a"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_six_row_evidence_recomputes_from_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert arena.evidence_gaps(doc) == []
    assert doc["summary"] == arena.derive_summary(doc) == {
        "arena_rows": 6,
        "path_records": 6,
        "distinct_model_hashes": 6,
        "natural_contact_rows": [2, 3, 4, 0],
        "controlled_contact_rows": [5, 1],
        "all_contact_rows": [0, 1, 2, 3, 4, 5],
        "contact_health_delta": -1,
        "counter8_phase_points": 5,
        "d18_or_f09_completed": 0,
    }
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_thud_arena.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(
        doc, require_selection=False) == []


@pytest.mark.local_media
def test_fixture_and_source_dependencies_remain_hash_pinned():
    doc = load_artifact()
    assert doc["fixture_census"] == arena.thud.build_fixture_census()
    assert doc["source_dependencies"] == arena._source_dependencies()
    assert doc["fixture_census"]["movie"]["sha256"] == arena.thud.MOVIE_SHA256
    assert doc["fixture_census"]["save"]["sha256"] == arena.thud.SAVE_SHA256


def test_each_row_has_exact_path_pass2_and_bounded_model_identity():
    rows = load_artifact()["runtime_census"]["rows"]
    assert len(rows) == 6
    for index, row in enumerate(rows):
        path = row["dynamic_type_record"]
        join = row["pass2_join"]
        model = row["model_identity"]
        assert (row["row"], path["type"], path["point_count"],
                path["byte_length"], path["sha256"]) == (
                    index, index, 58, 700, arena.PATH_HASHES[index])
        assert (path["first_point"], path["last_point"]) == \
            arena.PATH_ENDPOINTS[index]
        assert join["table"] == "0x8010a134"
        assert join["object"] == f"0x{0x8010A058 + index * 0x14:08x}"
        assert model == {
            "mesh_pointer": f"0x{arena.MESH_POINTERS[index]:08x}",
            "next_mesh_pointer": f"0x{arena.MESH_POINTERS[index + 1]:08x}",
            "byte_length": (arena.MESH_POINTERS[index + 1] -
                            arena.MESH_POINTERS[index]),
            "sha256": arena.MESH_HASHES[index],
            "retention": "Hash/address metadata only; mesh bytes are not retained.",
        }
    assert len({row["dynamic_type_record"]["sha256"] for row in rows}) == 6
    assert len({row["model_identity"]["sha256"] for row in rows}) == 6


def test_decoded_policy_and_tables_cover_all_six_rows():
    census = load_artifact()["runtime_census"]
    assert census["save_owned_code"] == {
        "address": "0x800b4814", "length": 0x310,
        "sha256": arena.thud.ARENA_BLOCK_SHA256,
        "classification": "save-owned Region-A runtime; not staged provenance",
    }
    assert census["pass2_table"] == {
        "global": "0x80082338", "runtime_base": "0x8010a134",
        "last_index": 9, "rotation_rows": 10, "collision_rows": 6,
    }
    assert census["policy_tables"] == {
        "angular_increment_s16": [-100, 120, 90, -144, -110, 128,
                                  32, 32, 32, 64],
        "ramp_cap_s16": list(arena.CAPS),
        "squared_distance_u32": list(arena.THRESHOLDS),
        "current_ramp_u32": list(arena.CAPS),
        "path_phase_u32": [8596, 11552, 5448, 12058, 2616, 5640],
    }
    policy = census["decoded_policy"]
    assert policy["path_source"] == "0x80096da0+row*4"
    assert policy["transform_call"] == "0x800b49e0"
    assert policy["collision_candidate_call"] == "0x800b4a04"
    assert policy["distance_compare"] == "0x800b4a60"
    assert policy["contact_ramp_clear"] == "0x800b4a88"
    assert policy["contact_speed_negation_store"] == "0x800b4aa8"
    assert policy["damage_call"] == "0x800b4ae0"


def test_four_natural_contacts_have_passive_cycle_neutral_boundaries():
    rows = load_artifact()["natural_contacts"]
    expected = {
        2: ([4, 3], [-90, 90], [112, 0], 139469),
        3: ([3, 2], [144, -144], [100, 0], 468282),
        4: ([3, 2], [-110, 110], [104, 0], 420045),
        0: ([4, 3], [-100, 100], [92, 0], 463089),
    }
    for item in rows:
        transition = item["observed_transition"]
        health, speed, ramp, distance = expected[item["row"]]
        assert transition == {
            "health": health, "speed": speed, "ramp": ramp,
            "inside_rows_post": [item["row"]],
        }
        selected = item["post"]["selected_row"]
        assert selected["squared_distance"] == distance
        assert selected["inside"] is True
        for side in ("pre", "post"):
            trace = item["passive_traces"][side]
            assert trace["comparison"]["cycle_neutral"] is True
            assert all(row["truncated"] is False
                       for row in trace["coverage"])


def test_two_negative_rows_are_bound_by_one_field_matched_controls():
    rows = load_artifact()["threshold_controls"]
    expected = {
        5: ("0x800b4c20", 490000, 1000000, 916961,
            [2, 1], [128, -128], [88, 0]),
        1: ("0x800b4c10", 250000, 700000, 607965,
            [4, 3], [120, -120], [96, 0]),
    }
    for item in rows:
        address, old, new, distance, health, speed, ramp = expected[item["row"]]
        assert item["single_field"] == {
            "address": address, "width": "u32", "from": old, "to": new}
        assert item["observed"] == {
            "squared_distance": distance, "health": health,
            "speed": speed, "ramp": ramp,
            "control_inside": False, "mutation_inside": True,
        }
        for key in ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                    "main_ram_sha256", "registers_sha256"):
            assert item["control"]["before"][key] == \
                item["mutation"]["before"][key]
        expected_endpoint = {
            5: ({"emulator_frame": True, "cycle": True,
                 "movie_frame": True, "sp": True, "pc": False},
                {"cycle_delta_mutation_minus_control": 0}),
            1: ({"emulator_frame": True, "cycle": True,
                 "movie_frame": True, "sp": True, "pc": False},
                {"cycle_delta_mutation_minus_control": 0}),
        }
        alignment, relation = expected_endpoint[item["row"]]
        assert item["endpoint_alignment"] == alignment
        assert item["endpoint_relation"] == relation
        assert item["control"]["after"]["player_position"] == \
            item["mutation"]["after"]["player_position"]
        assert item["control"]["after"]["selected_row"]["position"] == \
            item["mutation"]["after"]["selected_row"]["position"]
        changed = {row["address"] for row in
                   item["mutation"]["write_differences"]}
        base_address = int(address, 0)
        assert changed and changed <= {
            f"0x{base_address + offset:08x}" for offset in range(4)}


def test_counter8_linkage_is_passive_and_does_not_overclaim_completion():
    linkage = load_artifact()["counter8_phase_linkage"]
    assert linkage["row_loop_cumulative_counts"] == [
        11226, 11448, 11694, 11712, 12120]
    states = [
        (point["snapshot"]["scene"], point["snapshot"]["master_state"],
         point["snapshot"]["phase_counter"])
        for point in linkage["points"]]
    assert states == [(14, 1, 8)] * 4 + [(0, 1, 8)]
    assert "rather than assuming" in linkage["observation"]
    assert all(point["trace"]["comparison"]["cycle_neutral"] is True
               for point in linkage["points"])
    assert load_artifact()["bounded_open_frontier"]["still_open"].startswith(
        "Other boss attacks")


def test_mutations_fail_the_recomputed_evidence_guards():
    original = load_artifact()
    mutations = []
    changed = copy.deepcopy(original)
    changed["runtime_census"]["rows"][0]["model_identity"]["sha256"] = "0" * 64
    mutations.append(changed)
    changed = copy.deepcopy(original)
    changed["runtime_census"]["rows"][3]["dynamic_type_record"]["point_count"] = 57
    mutations.append(changed)
    changed = copy.deepcopy(original)
    changed["natural_contacts"][0]["passive_traces"]["post"][
        "comparison"]["cycle_neutral"] = False
    mutations.append(changed)
    changed = copy.deepcopy(original)
    changed["threshold_controls"][0]["mutation"]["write_differences"].append(
        {"address": "0x800b4c30", "before": 0, "after": 1})
    mutations.append(changed)
    assert all(arena.evidence_gaps(document) for document in mutations)


def test_declarative_scenarios_pin_natural_and_controlled_rows():
    scenario_paths = (
        ROOT / "tools/scenarios/duckstation/pristine_thud_six_row_arena.yaml",
        ROOT / "tools/scenarios/duckstation/pristine_thud_arena_row1_control.yaml",
        ROOT / "tools/scenarios/duckstation/pristine_thud_arena_row5_control.yaml",
    )
    scenarios = [ps1_scenario.load_scenario(path) for path in scenario_paths]
    assert [row["id"] for row in scenarios] == [
        "pristine_thud_six_row_arena",
        "pristine_thud_arena_row1_control",
        "pristine_thud_arena_row5_control",
    ]
    for scenario in scenarios:
        assert scenario["target"]["expected_serial"] == "SCUS-94288"
        assert scenario["playback"]["movie"] == arena.thud.MOVIE_REL
        assert scenario["playback"]["require_reproducible"] is True
