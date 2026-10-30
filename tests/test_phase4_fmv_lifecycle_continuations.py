"""Adversarial guards for E15's resident post-FMV continuation owners."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_lifecycle_continuations as continuations  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_fmv_lifecycle_continuations.json"
# Updated only after the generator is recomputed from pristine media.
ARTIFACT_SHA256 = "795229096b12258a4d704a5507d98650e247a0bbc415e40feb994386a0491e17"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_lifecycle_continuations_recompute_from_pristine_and_pinned_sources():
    retained = load_artifact()
    assert continuations.build() == retained
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert retained["inputs"]["resident_executable"]["identity_verified"] is True
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert all(
        row["sha256"] == row["expected_sha256"]
        for row in retained["owner_sources"])


def test_all_nine_return_continuations_have_exact_owners_and_partitioned_debt():
    retained = load_artifact()
    assert retained["summary"] == {
        "classified_continuations": 9,
        "direct_calls_inside_windows": 23,
        "direct_loader_calls": 9,
        "exceptional_path_categories": 4,
        "families": 8,
        "loader_direct_calls": 6,
        "native_cd_event_static_edges": 4,
        "owner_sources": 4,
        "resident_cd_event_field_gp_xrefs": 7,
        "transient_player_windows": 5,
        "unclassified_continuations": 0,
        "unclassified_native_cd_event_static_edges": 0,
        "unclassified_repeat_reload_retirement_owners": 0,
        "window_bytes": 1608,
    }
    assert [row["id"] for row in retained["continuations"]] == [
        "boot_dlogo", "boot_title", "boot_intro", "bonus_clip_sequence",
        "game_over_lose", "finale_lev15c", "completed_level_b",
        "all_levels_complete_lev15d", "level_a_reset_handoff",
    ]
    boundary = retained["dimension_boundary"]
    assert boundary["dimension"] == "lifecycle"
    assert boundary["claim"] == "partial"
    assert boundary["closed_sub_boundary"] == \
        "resident_post_fmv_continuation_ownership"
    partition = retained["static_partition"]
    assert partition["runtime_outcomes_claimed"] is False
    assert partition["viewer_policy_claimed"] is False
    assert set(partition["non_intersecting_residuals"]) == {
        "E15_lifecycle_runtime", "E15_campaign_breadth",
        "C17_E14_adjacent_policy", "E12_adjacent_policy",
    }
    player = retained["transient_player_continuations"]
    assert player["static_routing_closed"] is True
    assert player["native_outcomes_claimed"] is False
    assert player["completion_ownership"]["summary"] == {
        "readers": 1, "set_writers": 2, "clear_writers": 1,
        "total_xrefs": 4, "writers": 3}
    assert player["common_teardown"] == {
        "all_player_exit_edges_converge": True,
        "callback_teardown_call": "0x800B74A4",
        "cd_pause_command": {"site": "0x800B7464", "value": "0x0B"},
        "return": "0x800B7524",
        "st_clear_ring_call": "0x800B749C",
        "start": "0x800B7464",
    }
    route = player["native_cd_event_route"]
    assert route["registration"]["event_class"] == "0xF0000003"
    assert route["registration"]["event_spec"] == "0x00008000"
    assert route["registration"]["callback"] == "0x80045D5C"
    assert route["callback"]["store"] == {
        "address": "0x80082484",
        "gp_offset": "0x000006EC",
        "pc": "0x80045D60",
        "type": "u32",
        "value": 1,
    }
    assert route["player_consumer"]["exit_branch"] == {
        "pc": "0x800B7428",
        "taken_when": "loaded value equals 1",
        "target": "0x800B7464",
    }
    assert route["planned_same_anchor_control_basis"][
        "negative_word"] == "0x8C422484"
    assert route["planned_same_anchor_control_basis"][
        "positive_word"] == "0x24020001"
    assert route["runtime_event_delivery_claimed"] is False
    assert route["native_failure_outcome_claimed"] is False


def test_matching_loader_partitions_repeat_reload_and_retirement_ownership():
    retained = load_artifact()
    loader = retained["loader_lifecycle"]
    assert retained["dimension_boundary"]["closed_sub_boundaries"] == [
        "resident_post_fmv_continuation_ownership",
        "per_invocation_reload_and_retirement_ownership",
        "native_cd_event_to_pause_teardown_routing",
    ]
    assert loader["owner"]["source"]["source_status"] == "matching_c"
    assert [(row["pc"], row["target"], row["role"])
            for row in loader["ordered_calls"]] == [
        ("0x8003E7D4", "0x80039478", "pre_player_display_reset"),
        ("0x8003E7E4", "0x8005B440", "optional_transition_pre_hook"),
        ("0x8003E7FC", "0x80046330", "fmv_bin_reload"),
        ("0x8003E80C", "0x8005B4E4", "optional_transition_post_hook"),
        ("0x8003E814", "0x800B6250", "synchronous_fmv_player"),
        ("0x8003E81C", "0x80039854",
         "post_player_display_reinitialization"),
    ]
    assert loader["region_b_reload"] == {
        "destination": "0x800B5788",
        "loader": "0x80046330",
        "occurs_once_per_fmv_bin_load_invocation": True,
        "path": r"fmv\fmv.bin",
        "path_pointer": "0x8001AE6C",
        "repeat_calls_recopy_identical_overlay_bytes": True,
        "unconditional_call": "0x8003E7FC",
    }
    assert loader["retirement_partition"] == {
        "all_post_return_owners_classified": True,
        "common_player_teardown_ends_transient_fmv_use": True,
        "endpoint_nonresidency_does_not_identify_overwrite_instruction": True,
        "fmv_loader_contains_explicit_region_b_clear": False,
        "fmv_loader_contains_explicit_region_b_unload": False,
        "post_return_replacement_owner":
            "resident caller continuation or later Region-B loader",
    }
    assert loader["summary"]["unclassified_loader_edges"] == 0
    assert loader["summary"][
        "unclassified_repeat_reload_retirement_owners"] == 0


def test_transition_call_arguments_progress_scan_and_full_reset_owner_are_exact():
    rows = {row["id"]: row for row in load_artifact()["continuations"]}
    assert [(row["pc"], row["target"])
            for row in rows["game_over_lose"]["direct_calls"]] == [
        ("0x800500E4", "0x8005038C")]
    assert [(row["pc"], row["target"])
            for row in rows["finale_lev15c"]["direct_calls"]] == [
        ("0x8005028C", "0x8005222C")]
    assert rows["completed_level_b"]["window"] == {
        "end": "0x8005036C", "sha256":
        "38ce7971afec42c89fedb004d45765ff63b392b2fbe71a9b9f4d4f5f36ccd5f9",
        "size": 72, "start": "0x80050324"}
    level_a = rows["level_a_reset_handoff"]
    assert level_a["window"]["end"] == "0x8005BC64"
    assert len(level_a["direct_calls"]) == 20
    assert level_a["direct_calls"][1] == {
        "instruction": {
            "mnemonic": "jal 0x8003f358",
            "pc": "0x8005B7CC",
            "word": "0x0C00FCD6",
        },
        "pc": "0x8005B7CC",
        "target": "0x8003F358",
    }


@pytest.mark.local_media
@pytest.mark.parametrize("spec", continuations.CONTINUATIONS,
                         ids=lambda row: row["id"])
def test_each_continuation_window_mutation_fails_closed(spec):
    exe = bytearray(continuations.EXE_PATH.read_bytes())
    offset = (
        continuations.frontier.EXE_HEADER + spec["start"]
        - continuations.frontier.EXE_BASE)
    exe[offset] ^= 1
    with pytest.raises(
            SystemExit,
            match=f"FMV lifecycle continuation window drifted: {spec['id']}"):
        continuations.build(exe_data=bytes(exe), verify_identity=False)


@pytest.mark.local_media
def test_loader_call_census_mutation_fails_closed():
    exe = bytearray(continuations.EXE_PATH.read_bytes())
    offset = (
        continuations.frontier.EXE_HEADER + 0x800500D8
        - continuations.frontier.EXE_BASE)
    exe[offset] ^= 1
    with pytest.raises(
            SystemExit, match="FMV lifecycle continuation call census drifted"):
        continuations.build(exe_data=bytes(exe), verify_identity=False)


@pytest.mark.local_media
def test_matching_loader_lifecycle_mutation_fails_closed():
    exe = bytearray(continuations.EXE_PATH.read_bytes())
    offset = (
        continuations.frontier.EXE_HEADER + 0x8003E7FC
        - continuations.frontier.EXE_BASE)
    exe[offset] ^= 1
    with pytest.raises(
            SystemExit, match="FMV loader lifecycle window drifted"):
        continuations.build(exe_data=bytes(exe), verify_identity=False)


@pytest.mark.local_media
@pytest.mark.parametrize(
    ("pc", "message"),
    [
        (0x80045D60, "native CD event callback window drifted"),
        (0x80045E48, "native CD event registration window drifted"),
    ],
)
def test_native_cd_event_resident_route_mutation_fails_closed(pc, message):
    exe = bytearray(continuations.EXE_PATH.read_bytes())
    offset = continuations.frontier.EXE_HEADER + (
        pc - continuations.frontier.EXE_BASE)
    exe[offset] ^= 1
    with pytest.raises(SystemExit, match=message):
        continuations.build(exe_data=bytes(exe), verify_identity=False)


@pytest.mark.local_media
@pytest.mark.parametrize(
    ("pc", "message"),
    [
        (0x800B70D8, "FMV native CD event consumer key word drifted"),
        (0x800B7420, "FMV transient player continuation window drifted"),
        (0x800B7428, "FMV transient player continuation window drifted"),
        (0x800B7464, "FMV transient player continuation window drifted"),
    ],
)
def test_native_cd_event_player_route_mutation_fails_closed(pc, message):
    fmv = bytearray(continuations.frontier.FMV_PATH.read_bytes())
    offset = pc - continuations.frontier.FMV_BASE
    fmv[offset] ^= 1
    with pytest.raises(SystemExit, match=message):
        continuations.build(fmv_data=bytes(fmv), verify_identity=False)


@pytest.mark.local_media
@pytest.mark.parametrize("spec", continuations.PLAYER_WINDOWS,
                         ids=lambda row: row[0])
def test_each_transient_player_window_mutation_fails_closed(spec):
    identifier, start, _end, _expected_hash = spec
    fmv = bytearray(continuations.frontier.FMV_PATH.read_bytes())
    offset = start - continuations.frontier.FMV_BASE
    fmv[offset] ^= 1
    with pytest.raises(
            SystemExit,
            match=f"FMV transient player continuation window drifted: {identifier}"):
        continuations.build(fmv_data=bytes(fmv), verify_identity=False)
