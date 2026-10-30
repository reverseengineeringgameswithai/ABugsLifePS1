from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_region_b_replacement_ownership as owner  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_fmv_region_b_replacement_ownership.json"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_generated_region_b_replacement_artifact_is_current():
    retained = load_artifact()
    assert retained == owner.build()
    assert retained["schema"] == (
        "abl-phase4-fmv-region-b-replacement-ownership/2"
    )
    assert retained["inputs"]["resident_executable"]["identity_verified"]
    assert retained["offline_localization"]["receipt_sha256"] == (
        "8fe4e94a84381d1106ae0df087db27347865dc0ed4db3320029b8268c22c6326"
    )
    assert len(retained["offline_localization"]["zero_match_terms"]) == 10
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_natural_lose_anchor_and_first_materialization_are_exact():
    document = load_artifact()
    assert document["natural_anchor"] == {
        "selector": 46,
        "transition_hook_enabled": 0,
        "caller": "0x800500D8",
        "return_pc": "0x800500E0",
        "movie_reproducible": True,
        "source_artifact": "analysis/phase4_fmv_lose_lifecycle.json",
    }
    census = document["region_b_materialization_census"]
    expected = [{
        "lui_pc": "0x8003D308",
        "low_pc": "0x8003D30C",
        "register": 5,
        "value": "0x800B5788",
    }]
    assert census["natural_lose_matches"] == expected
    assert census["completed_level_b_matches"] == expected
    assert census["unclassified_matches"] == []


def test_replacement_chain_binds_selector_path_destination_and_cdread():
    document = load_artifact()
    chain = {row["stage"]: row for row in document["replacement_chain"]}
    dispatch = chain["E16_resource_dispatch"]
    assert dispatch["pc"] == "0x8003D310"
    assert dispatch["selector"] == 0
    assert dispatch["path"] == "bits\\memory.bin"
    assert dispatch["path_address"] == "0x8001ADFC"
    assert dispatch["destination"] == "0x800B5788"
    transfer = chain["resident_cd_transfer"]
    assert transfer["pc"] == "0x80046078"
    assert transfer["destination_instruction"]["word"] == "0x02602821"
    assert document["summary"]["display_direct_calls"] == 19


def test_completed_level_b_transition_and_persistence_policy_are_exact():
    document = load_artifact()
    assert document["completed_level_b_anchor"] == {
        "selector": 11,
        "transition_hook_enabled": -1,
        "caller": "0x8005031C",
        "return_pc": "0x80050324",
        "first_movie_frame": 14382,
        "scene_flow_entry_state_s0": 1,
        "completion_writer": "0x800B6B24",
        "common_exit_ordered": True,
        "source_artifact": "analysis/phase4_fmv_levelb_first_call.json",
    }
    policy = document["completed_level_b_replacement_policy"]
    assert policy["player_return"]["region_b_materializations"] == 0
    assert policy["player_return"]["optional_call"]["selector"] == 41
    assert policy["natural_scene_flow_join"]["return_pc"] == "0x80050144"
    assert [
        (row["scene"], row["transition"])
        for row in policy["conditional_transition_requests"]
    ] == [(3, 0), (6, 128)]
    assert policy["common_resource_policy"] == {
        "scene_setup_non_skip_transitions": [0, 128],
        "resource_dispatch_selector": 0,
        "path": "bits\\memory.bin",
        "destination": "0x800B5788",
        "byte_owner": "E16_streaming_overlays",
        "transition_owner": "resident_scene_flow_dispatcher",
    }
    persistence = policy["persistence_partition"]
    assert persistence["ordinary_progress_scan_calls_save_serializer"] is False
    assert persistence["c17_movie_viewer_unlock_field"] == "0x8009B889"
    assert persistence["c17_unlock_field_written"] is False
    assert persistence["e14_serialization_policy_claimed"] is False


def test_ownership_and_nonpromotion_boundaries_are_explicit():
    document = load_artifact()
    assert document["falsifier"]["outcome"] == "survived"
    assert all(document["falsifier"]["checks"].values())
    ownership = document["ownership"]
    assert ownership["replacement_byte_owner"] == "E16_streaming_overlays"
    assert ownership["lose_transition_choice_owner"] == (
        "C16_death_lives_game_over"
    )
    assert ownership["completed_level_b_transition_choice_owner"] == (
        "resident_scene_flow_dispatcher"
    )
    assert ownership["E14_frontend_save_intersects_selected_path"] is False
    assert ownership[
        "C17_movie_viewer_unlock_intersects_selected_path"
    ] is False
    assert ownership["first_byte_cycle_claimed"] is False
    boundary = document["claim_boundary"]
    assert boundary["closed_sub_boundaries"] == [
        "game_over_lose_region_b_replacement_ownership",
        "completed_level_b_region_b_replacement_ownership",
    ]
    assert boundary["dimension_promoted"] is False
    assert boundary["lifecycle_promoted"] is False
    assert boundary["next_lane"] == "live"


@pytest.mark.local_media
def test_load_bearing_pristine_mutations_turn_replacement_guard_red():
    exe = bytearray(owner.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        exe,
        owner.EXE_HEADER + 0x800503D0 - owner.EXE_BASE,
        0x24040001,
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(owner.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        exe,
        owner.EXE_HEADER + 0x80050134 - owner.EXE_BASE,
        0x00000000,
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(owner.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        exe,
        owner.EXE_HEADER + 0x8004FD74 - owner.EXE_BASE,
        0x00000000,
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(owner.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        exe,
        owner.EXE_HEADER + 0x800502A0 - owner.EXE_BASE,
        0x2405FFFF,
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(owner.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        exe,
        owner.EXE_HEADER + 0x8003D30C - owner.EXE_BASE,
        0x24A5578C,
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(owner.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        exe,
        owner.EXE_HEADER + 0x80046074 - owner.EXE_BASE,
        0x00002821,
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(exe_data=bytes(exe), verify_identity=False)
