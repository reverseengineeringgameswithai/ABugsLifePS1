"""Adversarial guards for the E15 callback and synchronous-consumer frontier."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_interface_frontier as frontier  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_fmv_interface_frontier.json"
ARTIFACT_SHA256 = "a886b9bee78bcec55a46d89499f2fc28fe9d0133a382eae521081e5fc2667d90"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_interface_artifact_recomputes_from_hash_verified_pristine_inputs():
    retained = load_artifact()
    assert frontier.build() == retained
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert retained["inputs"]["resident_executable"]["identity_verified"] is True
    assert retained["inputs"]["fmv_bin"]["identity_verified"] is True
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    sources = retained["source_validation"]
    assert sources["all_validated"] is True
    assert len(sources["validated_files"]) == 21
    external = [row for row in sources["validated_files"]
                if row["path"].startswith("asm/hand_written/")]
    assert len(external) == 12
    assert all(row["sha256"] == row["expected_sha256"] for row in external)
    assert any(row["path"] ==
               "asm/hand_written/80070a40_fmv_frame_counter_setter.s"
               for row in external)


def test_callback_install_delivery_optional_slot_and_teardown_are_exact():
    lifecycle = load_artifact()["callback_lifecycle"]
    assert len(lifecycle["functions"]) == 11
    assert lifecycle["setup"] == {
        "ring_call": "0x800B6F9C",
        "ring_records": 32,
        "stream_call": "0x800B6FC4",
        "arguments": {
            "a0": "display_mode_equals_3", "a1": 1,
            "a2": "0x0FFFFFFF", "a3_optional_callback": 0,
            "stack_arg5": 0,
        },
        "optional_callback_slots": {
            "frame_ready": {
                "address": "0x800910F0", "argument": "a3",
                "store": "0x80070B58", "delivery_sites": ["0x80070AA0"],
                "enabled_for_e15": False,
            },
            "sector_ready": {
                "address": "0x800910F4", "argument": "stack_arg5",
                "argument_load": "0x80070B38", "store": "0x80070B88",
                "delivery_sites": ["0x800712DC", "0x80071388"],
                "enabled_for_e15": False,
            },
        },
        "optional_callback_enabled_for_e15": False,
    }
    assert lifecycle["installation"] == {
        "player_cdread2_call": "0x800B704C",
        "mode": "0x000001C0",
        "data_callback_install": {
            "site": "0x800708F0", "api": "CdDataCallback",
            "handler": "0x80070A30",
        },
        "ready_callback_install": {
            "site": "0x80070900", "api": "CdReadyCallback",
            "handler": "0x8007092C",
        },
        "ready_wrapper_target": "0x80070D80",
        "interrupt_delivery_to_data_handler": "0x800716D8",
    }
    assert lifecycle["teardown"]["all_player_exit_edges_converge"] is True
    assert lifecycle["teardown"]["default_backend_clears"] == [
        "0x800709E8", "0x800709F0"]
    assert lifecycle["direct_jal_census"]["0x8006DCF0"] == {
        "direct_call_count": 10,
        "call_sites": [
            "0x80070084", "0x800700A8", "0x80070290", "0x800703A0",
            "0x80070428", "0x80070590", "0x80070670", "0x80070744",
            "0x800708F0", "0x800709E8",
        ],
    }
    assert lifecycle["direct_jal_census"]["0x8006D8D0"][
        "direct_call_count"] == 11
    assert lifecycle["phase3_callback_crosscheck"]["sites"] == {
        "0x80070AA0": {
            "class": "global_slot", "function": "str_data_ready_callback",
            "slot": "0x800910F0"},
        "0x800712DC": {
            "class": "global_slot", "function": "StCdInterrupt",
            "slot": "0x800910F4"},
        "0x80071388": {
            "class": "global_slot", "function": "StCdInterrupt",
            "slot": "0x800910F4"},
    }


def test_all_synchronous_consumers_return_continuations_and_owners_are_closed():
    consumers = load_artifact()["resident_consumers"]
    assert consumers["exhaustive_direct_call_count"] == 9
    assert [(row["owner"], row["call"]["pc"], row["return_pc"])
            for row in consumers["calls"]] == [
        ("boot_dlogo", "0x8004FB5C", "0x8004FB64"),
        ("boot_title", "0x8004FB68", "0x8004FB70"),
        ("boot_intro", "0x8004FB74", "0x8004FB7C"),
        ("bonus_clip_sequence", "0x8004FFD4", "0x8004FFDC"),
        ("game_over_lose", "0x800500D8", "0x800500E0"),
        ("finale_lev15c", "0x80050284", "0x8005028C"),
        ("completed_level_b", "0x8005031C", "0x80050324"),
        ("all_levels_complete_lev15d", "0x8005036C", "0x80050374"),
        ("level_a_reset_handoff", "0x8005B788", "0x8005B790"),
    ]
    assert [row["hook_argument"] for row in consumers["calls"]] == [
        0, 0, 0, -1, 0, 0, -1, -1, 0]
    assert consumers["loader"]["call_contract"] == \
        "synchronous selector dispatch and playback"
    continuation = consumers["level_a_post_fmv_continuation"]
    assert continuation["function_start"] == "0x8005B714"
    assert continuation["function_end"] == "0x8005BC64"
    assert continuation["start"] == "0x8005B790"
    assert continuation["scene_load_call"] == "0x8005B7CC"
    assert continuation["scene_load_target"] == "0x8003F358"
    assert continuation["direct_call_count"] == 20
    assert [row["pc"] for row in continuation["direct_calls"]][0:2] == [
        "0x8005B7A8", "0x8005B7CC"]
    assert [row["pc"] for row in continuation["direct_calls"]][-1] == \
        "0x8005BC38"
    assert consumers["ownership_partition"]["viewer_semantics_inferred"] is False
    assert set(consumers["ownership_partition"]["adjacent_policy"]) == {
        "C17_movie_viewer", "E14_persistence", "E16_overlay_loader", "E12_audio"}


def test_boot_returns_reach_exact_six_target_shell_dispatch_and_partitions():
    dispatch = load_artifact()["resident_consumers"]["main_shell_dispatch"]
    assert dispatch["owner_range"] == ["0x8004FA40", "0x8004FC3C"]
    assert dispatch["dispatch_site"] == "0x8004FC34"
    assert dispatch["table"] == {
        "address": "0x8001B3C4", "entries": 6,
        "sha256": "9f29dc248a56655a207894378cbd2f3f535345704f617938f7e3efa885639da1",
    }
    assert [row["target"] for row in dispatch["targets"]] == [
        "0x8004FC3C", "0x8004FC50", "0x8004FC64", "0x8004FC78",
        "0x8004FC8C", "0x8004FCA0"]
    assert [row["semantics"].get("resolved_scene")
            for row in dispatch["targets"]] == [1, 12, 3, 4, 13, None]
    assert dispatch["downstream_scene_resolution"] == {
        "shared_join": "0x8004FCC0",
        "destination_index_load": "0x8004FCF0",
        "scene_table": "0x80077FA0",
        "scene_table_load": "0x8004FD04",
        "scene_store": {"site": "0x8004FD0C", "address": "0x80082504"},
    }
    assert dispatch["boot_return_dispatch_join"] == {
        "loader_return_pcs": ["0x8004FB64", "0x8004FB70", "0x8004FB7C"],
        "owner_range": ["0x8004FA40", "0x8004FC3C"],
        "dispatch_site": "0x8004FC34", "target_count": 6,
    }
    assert all(row["target_range"][0] == row["target"]
               for row in dispatch["targets"])


def test_exceptional_functions_are_bounded_without_runtime_outcome_inflation():
    exceptional = load_artifact()["exceptional_frontier"]
    assert [row["id"] for row in exceptional["paths"]] == [
        "file_open_failure", "decode_record_absent", "decode_poll_timeout",
        "cd_submit_retry",
    ]
    assert exceptional["paths"][1]["stop_latch_store"] == "0x800B6C84"
    assert exceptional["paths"][2]["budget"] == "0x00800000"
    assert exceptional["runtime_frequency_claimed"] is False
    assert exceptional["malformed_media_behavior_claimed"] is False
    summary = load_artifact()["summary"]
    assert summary["unclassified_callbacks"] == 0
    assert summary["unclassified_direct_consumers"] == 0
    assert summary["complete_frontier_intersections"] == 0


@pytest.mark.local_media
def test_callback_consumer_teardown_and_exception_mutations_fail_closed():
    exe = bytearray(frontier.EXE_PATH.read_bytes())
    offset = frontier.EXE_HEADER + 0x800708EC - frontier.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="callback lifecycle opcode drifted"):
        frontier.build(exe_data=bytes(exe), verify_identity=False)

    fmv = bytearray(frontier.FMV_PATH.read_bytes())
    offset = 0x800B6FB8 - frontier.FMV_BASE
    struct.pack_into("<I", fmv, offset, 1)
    with pytest.raises(SystemExit, match="FMV player lifecycle opcode drifted"):
        frontier.build(fmv_data=bytes(fmv), verify_identity=False)

    exe = bytearray(frontier.EXE_PATH.read_bytes())
    offset = frontier.EXE_HEADER + 0x80070B88 - frontier.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="callback lifecycle opcode drifted"):
        frontier.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(frontier.EXE_PATH.read_bytes())
    offset = frontier.EXE_HEADER + 0x800712DC - frontier.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="callback lifecycle opcode drifted"):
        frontier.build(exe_data=bytes(exe), verify_identity=False)

    fmv = bytearray(frontier.FMV_PATH.read_bytes())
    offset = 0x800B74A4 - frontier.FMV_BASE
    struct.pack_into("<I", fmv, offset, 0)
    with pytest.raises(SystemExit, match="FMV player lifecycle opcode drifted"):
        frontier.build(fmv_data=bytes(fmv), verify_identity=False)

    exe = bytearray(frontier.EXE_PATH.read_bytes())
    offset = frontier.EXE_HEADER + 0x800500E4 - frontier.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="FMV consumer opcode drifted"):
        frontier.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(frontier.EXE_PATH.read_bytes())
    offset = frontier.EXE_HEADER + 0x8005B7CC - frontier.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="level-A post-FMV continuation"):
        frontier.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(frontier.EXE_PATH.read_bytes())
    offset = (frontier.EXE_HEADER + frontier.MAIN_SHELL_DISPATCH_TABLE
              - frontier.EXE_BASE)
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="main-shell dispatch table drifted"):
        frontier.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(frontier.EXE_PATH.read_bytes())
    offset = frontier.EXE_HEADER + 0x8004FCB4 - frontier.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="main-shell dispatch opcode drifted"):
        frontier.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(frontier.EXE_PATH.read_bytes())
    offset = frontier.EXE_HEADER + 0x8004FD04 - frontier.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="main-shell dispatch opcode drifted"):
        frontier.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(frontier.EXE_PATH.read_bytes())
    offset = frontier.EXE_HEADER + 0x8003E7DC - frontier.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="FMV synchronous loader opcode drifted"):
        frontier.build(exe_data=bytes(exe), verify_identity=False)

    fmv = bytearray(frontier.FMV_PATH.read_bytes())
    offset = 0x800B6CF8 - frontier.FMV_BASE
    struct.pack_into("<I", fmv, offset, 0)
    with pytest.raises(SystemExit, match="FMV player lifecycle opcode drifted"):
        frontier.build(fmv_data=bytes(fmv), verify_identity=False)


@pytest.mark.local_media
def test_external_source_pin_and_presence_mutations_fail_closed(
        monkeypatch, tmp_path):
    source = "asm/hand_written/8005b714_gameplay_state_reset_cursor_seed.s"
    current_pin = frontier._manifest_pins()[source]
    bad_manifest = tmp_path / "repro_inputs.sha256"
    bad_manifest.write_text(frontier.SOURCE_MANIFEST.read_text().replace(
        current_pin, "0" * 64, 1))
    original_manifest = frontier.SOURCE_MANIFEST
    monkeypatch.setattr(frontier, "SOURCE_MANIFEST", bad_manifest)
    with pytest.raises(SystemExit, match="FMV frontier ASM source pin drifted"):
        frontier.build()

    monkeypatch.setattr(frontier, "SOURCE_MANIFEST", original_manifest)
    start, end, _ = frontier.CALLER_REGIONS[
        "gameplay_state_reset_cursor_seed"]
    monkeypatch.setitem(
        frontier.CALLER_REGIONS, "gameplay_state_reset_cursor_seed",
        (start, end, "asm/hand_written/does_not_exist.s"))
    with pytest.raises(SystemExit, match="declared FMV frontier source is missing"):
        frontier.build()


def test_registry_promotes_only_complete_frontier_and_keeps_residuals_disjoint():
    registry = yaml.safe_load((ROOT / "config/phase4_campaigns.yaml").read_text())
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "fmv_playback")
    claim = campaign["dimension_claims"]["complete_frontier"]
    assert claim["claim"] == "met"
    assert claim["confidence"] == "confirmed"
    assert len(claim["evidence"]) >= 13
    assert all(row["intersects_dimension"] is False
               for row in claim["residuals"])
    assert "analysis/phase4_fmv_interface_frontier.json" in \
        claim["authoritative_paths"]
    assert campaign["dimension_claims"].get("lifecycle") is None
    assert campaign["dimension_claims"].get("campaign_breadth") is None


def test_schema_binds_interface_without_promoting_adjacent_policy():
    schema = yaml.safe_load((ROOT / "config/phase4_fmv.yaml").read_text())
    assert schema["schema"] == "abl-phase4-fmv/11"
    interface = schema["interface_frontier"]
    slots = interface["callback_chain"]["player_setup"]["st_set_stream"][
        "optional_callback_slots"]
    assert slots["frame_ready"]["enabled"] is False
    assert slots["sector_ready"]["enabled"] is False
    assert interface["resident_consumers"]["direct_call_count"] == 9
    assert interface["source_status"]["unclassified_callbacks"] == 0
    assert interface["resident_consumers"]["return_owner_regions"][0] == [
        0x8004FA40, 0x8004FC3C]
    assert interface["resident_consumers"]["return_owner_regions"][-1] == [
        0x8005B714, 0x8005BC64]
    assert interface["resident_consumers"]["level_a_post_fmv_continuation"][
        "direct_call_count"] == 20
    assert interface["resident_consumers"]["main_shell_dispatch"]["table"][
        "entries"] == 6
    assert "C17 viewer" in interface["boundary"]
