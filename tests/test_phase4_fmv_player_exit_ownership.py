"""Adversarial guards for E15's post-helper exit ownership."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_player_exit_ownership as owner  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_fmv_player_exit_ownership.json"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_player_exit_ownership_recomputes_from_pristine_and_closed_query():
    retained = load_artifact()
    assert owner.build() == retained
    assert retained["inputs"]["fmv_bin"]["identity_verified"] is True
    assert retained["inputs"]["resident_executable"][
        "identity_verified"
    ] is True
    assert retained["offline_localization"]["receipt_sha256"] == (
        "244e5b5ac038d6b9b805a13581007d36cfe4cd268e3f8881c8ed80d7e2b4aa0d"
    )
    assert retained["offline_localization"]["external_index_sha256"] == (
        "e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab"
    )
    assert len(retained["offline_localization"]["zero_match_terms"]) == 10
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_complete_exit_entry_frontier_has_no_unclassified_edges():
    frontier = load_artifact()["exit_entry_frontier"]
    assert [
        (row["pc"], row["target"]) for row in frontier["encoded_edges"]
    ] == [
        ("0x800B6E44", "0x800B7468"),
        ("0x800B70BC", "0x800B7468"),
        ("0x800B7294", "0x800B7464"),
        ("0x800B7428", "0x800B7464"),
        ("0x800B7430", "0x800B7464"),
        ("0x800B7444", "0x800B6E38"),
    ]
    assert frontier["fallthrough_edges"] == [{
        "pc": "0x800B745C",
        "predicate": "decoded_frame_index_not_less_than_selected_limit",
        "delay_slot": "0x800B7460",
        "target": "0x800B7464",
    }]
    assert frontier["unclassified_encoded_edges"] == []
    assert frontier["unclassified_fallthrough_edges"] == []


def test_five_predicates_bind_exact_sources_and_routes():
    predicates = {
        row["id"]: row for row in
        load_artifact()["post_helper_predicates"]
    }
    assert list(predicates) == [
        "decode_stop_latch",
        "resident_cd_event",
        "controller_skip_countdown",
        "completion_request",
        "decoded_index_selected_limit",
    ]
    assert predicates["decode_stop_latch"]["source_writer"] == "0x800B6C84"
    assert predicates["resident_cd_event"]["source_writer"] == "0x80045D60"
    skip = predicates["controller_skip_countdown"]
    assert skip["source_address"] == "0x80082412"
    assert skip["mask_value"] == "0x4008"
    assert skip["seed_value"] == 1
    assert skip["exit_sentinel"] == 12
    assert skip["command_route"] == ["CdlPause(11)", "common_teardown"]
    assert predicates["completion_request"]["command_route"] == [
        "CdlStop(8)", "CdlPause(11)", "common_teardown"
    ]
    assert predicates["decoded_index_selected_limit"][
        "false_fallthrough"
    ] == "0x800B7464"


def test_controller_producer_and_cd_command_partition_are_explicit():
    document = load_artifact()
    controller = document["controller_producer_chain"]
    assert controller["resident_function"]["start"] == "0x8003A2DC"
    assert controller["resident_function"]["end"] == "0x8003A314"
    assert controller["prior_state_store"]["pc"] == "0x8003A2F0"
    assert controller["current_state_store"]["pc"] == "0x8003A300"
    assert controller["player_mask"]["word"] == "0x30424008"
    assert controller["countdown_compare"]["pc"] == "0x800B7430"

    commands = document["cd_command_partition"]
    assert commands["completion_only_stop"]["command"] == 8
    assert commands["completion_only_stop"]["join_delay_slot"][
        "word"
    ] == "0x2404000B"
    assert commands["shared_pause"]["command"] == 11
    assert commands["shared_pause"]["classification"] == (
        "stream_teardown_not_frontend_pause_shell"
    )
    assert commands["common_teardown"]["return"]["pc"] == "0x800B7524"


def test_static_join_preserves_runtime_and_dimension_boundaries():
    document = load_artifact()
    assert document["falsifier"]["outcome"] == "survived"
    assert all(document["falsifier"]["checks"].values())
    assert document["runtime_control_join"]["changed_frames"] == list(
        range(334, 343)
    )
    boundary = document["claim_boundary"]
    assert boundary["closed_sub_boundary"] == (
        "post_helper_exit_and_cd_command_ownership"
    )
    assert boundary["dimension_promoted"] is False
    assert boundary["lifecycle_promoted"] is False
    assert boundary["next_lane"] == "static"
    assert any(
        "native delivery frequency" in residual
        for residual in boundary["not_claimed"]
    )
    assert document["summary"]["unclassified_exit_edges"] == 0


@pytest.mark.local_media
def test_load_bearing_pristine_mutations_turn_exit_ownership_red():
    fmv = bytearray(owner.FMV_PATH.read_bytes())
    struct.pack_into(
        "<I",
        fmv,
        0x800B740C - owner.FMV_BASE,
        0x30420008,  # weaken the controller mask
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(fmv_data=bytes(fmv), verify_identity=False)

    fmv = bytearray(owner.FMV_PATH.read_bytes())
    struct.pack_into(
        "<I",
        fmv,
        0x800B73FC - owner.FMV_BASE,
        0x10000019,  # add a new encoded edge to 0x800B7464
    )
    with pytest.raises(ValueError, match="edge census drifted"):
        owner.build(fmv_data=bytes(fmv), verify_identity=False)

    exe = bytearray(owner.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        exe,
        owner.EXE_HEADER + 0x8003A300 - owner.EXE_BASE,
        0xA4202412,  # stop publishing the polled controller value
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(exe_data=bytes(exe), verify_identity=False)
