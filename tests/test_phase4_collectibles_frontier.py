"""Falsifiable guards for the Phase-4 grain/harvester static frontier."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_collectibles_frontier as frontier  # noqa: E402
import phase4_common  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_collectibles_frontier.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_frontier_recomputes_from_pinned_pristine_and_derived_evidence():
    retained = load(ARTIFACT)
    rebuilt = frontier.build()
    assert rebuilt == retained
    assert retained["schema"] == "abl-phase4-collectibles-frontier/1"
    assert retained["valid"] is True
    assert retained["errors"] == []
    assert retained["campaign"] == {
        "dimension_promoted": False,
        "family": "collectibles_equipment_rewards",
        "first_unmet_dimension": "original_oracle",
        "id": "grain_collection_harvester",
        "next_lane": "static",
        "rows": [
            "C01_grain_pickup",
            "C02_fifty_grain_reward",
            "C13_grain_harvester",
        ],
    }
    external = retained["inputs"]["external_index"]
    assert external["media_class"] == "derived_pristine_evidence"
    assert external["preservation_required"] is True
    assert phase4_common.sha256(Path(external["path"])) == external["sha256"]
    for anchor in retained["inputs"]["anchors"]:
        assert anchor["from_boot"] is False
        assert phase4_common.sha256(
            ROOT / anchor["movie"]["path"]) == anchor["movie"]["sha256"]
        assert phase4_common.sha256(
            ROOT / anchor["start_state"]["path"]) == \
            anchor["start_state"]["sha256"]


def test_c13_movie_lead_joins_actor35_asset_stage01_and_powerup_bit():
    document = load(ARTIFACT)
    offline = document["offline_localization"]["C13_grain_harvester"]
    assert offline["records"] == 618
    assert offline["actor_ids_observed"] == [9, 10, 11, 13, 14, 35, 39, 40]
    assert offline["unique_level_signature_matches"] == ["stage01_anthill"]
    assert offline["frame_0"]["actor"] == {
        "address": "0x800a1dfc",
        "id": 35,
        "slot": 63,
        "source": "0x8009511c",
        "vm_ip": "0x8007798c",
        "x": 97920,
        "y": -10531,
        "z": 778208,
    }
    assert offline["pickup_boundary"] == {
        "actor_player_delta": [0, 192, 0],
        "actor_xyz": [94989, -11621, 775598],
        "movie_frame": 83,
        "player_xyz": [94989, -11813, 775598],
        "powerup_flags_after": 128,
        "powerup_flags_before": 8,
    }
    assert offline["attached_suffix"] == {
        "distinct_actor_player_deltas": [[0, 192, 0]],
        "first_movie_frame": 83,
        "last_movie_frame": 617,
        "powerup_bit_persistent": True,
        "records": 535,
    }

    static = document["static_frontier"]
    asset = static["actor_asset_ownership"]
    assert asset["actor_id"] == 35
    assert asset["actor_jump_table_entry"] == "0x8001BC64"
    assert asset["case_target"] == "0x8005E17C"
    assert asset["asset_string"] == "chars3\\flikharv"
    assert asset["asset_string_va"] == "0x8001BA90"
    assert [row["level"] for row in asset["authored_levels"]] == [
        "stage01_anthill",
        "stage02_tunnels",
        "stage05_riverbed_run",
        "stage08_city_square",
        "stage10_clover_forest",
        "stage11_the_tree",
    ]
    assert all(row["slot"] == 63 and row["address"] == "0x800a1dfc"
               for row in asset["authored_levels"])
    assert static["equip_and_follow"]["powerup_flag"] == {
        "address": "0x800A6590",
        "bit": "0x0080",
        "writer": "0x80051EB0",
    }


def test_grain_source_metadata_and_convergence_law_are_distinct_from_pickup_radius():
    static = load(ARTIFACT)["static_frontier"]
    source = static["grain_attraction_source"]
    assert source["kind"] == 0x14
    assert source["constructor_type"] == 0x51
    assert source["squared_distance_max"] == 0x15F8F
    assert source["post_constructor_target_store"] == {
        "pc": "0x80053C58", "value": -1}
    assert source["metadata"] == {
        "action_id": 20,
        "active_gate": 200,
        "field_2a": 100,
        "flags": 0xEA,
        "phase": 210,
        "radius_add": 100,
        "row_hex": "1400c800d20000016400640016000000ea808080",
        "selector": 0,
        "state": 22,
    }
    convergence = static["grain_convergence"]
    assert convergence["precondition"] == (
        "flags bit 0x08, active_gate > 0 and target +0x10 == -1")
    assert convergence["source_squared_distance_max"] == 0x15F8F
    assert convergence["pickup_walker_radius"] == {
        "base": 300, "radius_add": 100, "total": 400}
    assert convergence["heading_law"] == (
        "delta=(atan2(playerX-recordX, playerZ-recordZ)-heading)&0xFFF; "
        "add delta>>2 when delta<0x800, otherwise add (0x800-delta)>>2")
    assert "0x2000" in convergence["vertical_law"]


def test_c01_c02_boundaries_and_unreachable_progress_branch_are_not_overclaimed():
    document = load(ARTIFACT)
    c01 = document["offline_localization"]["C01_grain_pickup"]
    assert c01["grain_transition"] == [10, 12]
    assert c01["grain_event_frames"] == [196, 540]
    assert all(row["records"] == 5 for row in c01["effect_signature_per_event"])
    assert all(row["action_ids"] == [4] and row["radius_adds"] == [100]
               for row in c01["effect_signature_per_event"])

    c02 = document["offline_localization"]["C02_fifty_grain_reward"]
    assert c02["grain_transition"] == [49, 50]
    assert c02["grain_event_frames"] == [160]
    assert c02["true_health_transition"] == [4, 4]
    assert c02["same_frame_spu_ram_changed"] is False

    reward = document["static_frontier"]["fifty_grain_reward"]
    assert reward["progress_branch"] == {
        "comparison_pc": "0x80055078",
        "left_address": "0x80090B80",
        "reachable": False,
        "right_address": "0x800B3988",
    }
    assert reward["reachable_health_store"] == {
        "address": "0x800A6594", "pc": "0x80055124", "value": 4}


def test_semantic_state_uses_resident_halfword_and_harvester_writer():
    semantic = phase4_common.load_yaml(ROOT / "config/semantic_state.yaml")
    entry = next(row for row in semantic["entries"]
                 if row["id"] == "original.player_powerup_flags")
    assert entry["address"] == 0x800A6590
    assert entry["width"] == "u16"
    assert {row.get("address") for row in entry["writers"]} >= {
        0x80051EB0, 0x8005CECC}
    assert entry["invariants"][0]["max"] == 65535
    assert "0x80 grain harvester" in entry["invariants"][0]["context"]


@pytest.mark.parametrize(
    ("path", "value", "expected_gap"),
    [
        (
            ("offline_localization", "C13_grain_harvester",
             "pickup_boundary", "actor_player_delta"),
            [1, 192, 0],
            "C13 harvester follow delta changed",
        ),
        (
            ("static_frontier", "grain_attraction_source",
             "squared_distance_max"),
            0x15F90,
            "grain attraction source radius changed",
        ),
        (
            ("static_frontier", "fifty_grain_reward",
             "progress_branch", "reachable"),
            True,
            "grain-50 progress branch reachability changed",
        ),
    ],
)
def test_artifact_mutations_trip_the_bounded_guard(path, value, expected_gap):
    mutated = deepcopy(load(ARTIFACT))
    cursor = mutated
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    assert expected_gap in frontier.evidence_gaps(mutated)


def test_instruction_word_falsifier_rejects_a_one_byte_pristine_slice_mutation():
    executable = bytearray(
        (ROOT / frontier.CONFIG["inputs"]["executable"]["path"]).read_bytes())
    pc = 0x80051EB0
    expected = int(frontier.CONFIG["expected_words"][pc])
    assert frontier.exe_word(executable, pc) == expected
    executable[frontier.exe_offset(pc)] ^= 0x01
    assert frontier.exe_word(executable, pc) != expected
