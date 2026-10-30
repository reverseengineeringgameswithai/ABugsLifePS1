"""Adversarial guards for the E15 decode-helper/outer-loop ownership."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_present_rect_height_helper_loop as owner  # noqa: E402


ARTIFACT = (
    ROOT / "analysis/phase4_fmv_present_rect_height_helper_loop.json"
)


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_helper_ownership_recomputes_from_pristine_and_retained_inputs():
    retained = load_artifact()
    assert owner.build() == retained
    assert retained["inputs"]["fmv_bin"]["identity_verified"] is True
    assert retained["inputs"]["resident_executable"]["identity_verified"] is True
    assert retained["offline_localization"]["receipt_sha256"] == (
        "3412a5254070301df57bbf6d6972043c48ff10cb79102a33bae2f34dc0a14558"
    )
    assert retained["offline_localization"]["external_index_sha256"] == (
        "e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab"
    )
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_helper_is_single_call_wrapper_and_complete_caller_frontier_is_closed():
    document = load_artifact()
    frontier = document["caller_frontier"]
    assert [row["pc"] for row in frontier["commit_direct_callers"]] == [
        "0x800B6C34"
    ]
    assert [row["pc"] for row in frontier["helper_direct_callers"]] == [
        "0x800B70A0", "0x800B7280"
    ]
    assert frontier["jalr_sites"] == []
    assert frontier["raw_target_references"] == []
    assert frontier["unclassified_callers"] == []

    helper = document["helper_single_call_ownership"]
    assert helper["classification"] == "single_call_wrapper_not_loop"
    assert helper["commit_calls_per_invocation"] == 1
    assert helper["back_edges"] == []
    assert helper["commit_call"]["pc"] == "0x800B6C34"
    assert helper["guest_return"]["pc"] == "0x800B6C9C"


def test_commit_abi_computes_only_a0_live_and_rejects_record_typing():
    document = load_artifact()
    abi = document["commit_entry_abi"]
    assert abi["classification"] == "single_semantic_argument_a0"
    assert {
        register: (
            row["access"], row["instruction"]["pc"]
        )
        for register, row in abi["computed_first_accesses"].items()
    } == {
        "a0": ("read", "0x800B6A84"),
        "a1": ("definition", "0x800B6A9C"),
        "a2": ("definition", "0x800B6B8C"),
        "a3": ("definition", "0x800B6B90"),
    }
    assert abi["dead_on_entry_arguments"]["a2"][
        "StGetNext_computed_first_access"
    ]["access"] == "definition"
    assert abi["dead_on_entry_arguments"]["a3"][
        "StGetNext_computed_first_access"
    ]["instruction"]["pc"] == "0x80070C9C"
    assert abi["StGetNext_call"]["external_asm_sha256"] == (
        "3ee73d63990afa5b1d21049fb2945969cbdd3cbd863e8cc4048f062bd9335b94"
    )
    record_decision = document["schema_decisions"]["record_types"]
    assert record_decision["fmv_or_decode_record_ids"] == []
    assert record_decision["decision"].startswith("No record was added")


def test_trace_partitions_as_one_initialization_plus_ten_outer_loop_calls():
    document = load_artifact()
    player = document["player_call_partition"]
    assert player["classification"] == \
        "one_initialization_call_then_outer_loop_calls"
    assert player["initialization_call"]["calls_per_player_invocation"] == 1
    assert player["outer_loop_call"]["calls_per_outer_loop_iteration"] == 1
    assert player["outer_loop_back_edge"]["target"] == "0x800B70E0"
    assert player["outer_loop_back_edge"][
        "can_revisit_initialization_call"
    ] is False
    assert player["fixed_iteration_bound"] is None

    joined = document["retained_trace_join"]
    assert joined["calls"] == 11
    assert [row["call_count"] for row in joined["argument_classes"]] == [
        1, 1, 9
    ]
    assert joined["static_call_site_partition"] == [
        {
            "class_index": 0,
            "owner": "player_initialization_call_0x800B70A0",
            "calls": 1,
        },
        {
            "class_indexes": [1, 2],
            "owner": "player_outer_loop_call_0x800B7280",
            "calls": 10,
        },
    ]
    assert joined["synthetic_exit_indexes"] == [2]


def test_packet_loop_claim_is_falsified_but_corrected_boundary_survives():
    falsifier = load_artifact()["falsifier"]
    assert falsifier["packet_claim"]["outcome"] == "falsified"
    assert falsifier["packet_claim"]["reasons"] == [
        "0x800B6C24_has_no_back_edge",
        "repeated_calls_are_owned_by_outer_player_loop",
        "nine_is_bounded_trace_class_count_not_static_bound",
    ]
    assert falsifier["corrected_claim"]["outcome"] == "survived"
    assert all(falsifier["corrected_claim"]["checks"].values())
    boundary = load_artifact()["claim_boundary"]
    assert boundary["dimension_promoted"] is False
    assert boundary["next_lane"] == "static"


@pytest.mark.local_media
def test_load_bearing_byte_mutations_turn_helper_ownership_red():
    fmv = bytearray(owner.FMV_PATH.read_bytes())
    struct.pack_into(
        "<I",
        fmv,
        0x800B6A88 - owner.FMV_BASE,
        0x00A01021,  # addu v0,a1,zero: illegal read before first definition
    )
    with pytest.raises(
        ValueError, match="argument use-before-definition"
    ):
        owner.build(fmv_data=bytes(fmv), verify_identity=False)

    fmv = bytearray(owner.FMV_PATH.read_bytes())
    struct.pack_into(
        "<I", fmv, 0x800B745C - owner.FMV_BASE, 0
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(fmv_data=bytes(fmv), verify_identity=False)

    exe = bytearray(owner.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        exe,
        owner.EXE_HEADER + 0x80070CA0 - owner.EXE_BASE,
        0x00C01021,  # addu v0,a2,zero: consumes inherited a2
    )
    with pytest.raises(
        ValueError, match="inherited argument access"
    ):
        owner.build(exe_data=bytes(exe), verify_identity=False)


def test_retained_trace_class_mutation_rejects_static_join():
    trace = json.loads(
        (
            ROOT
            / "analysis/phase4_fmv_present_rect_height_function_trace_result.json"
        ).read_text()
    )
    changed = copy.deepcopy(trace)
    changed["observation"]["precise"]["native"]["argument_classes"][2][
        "call_count"
    ] = 8
    with pytest.raises(ValueError, match="trace partition drifted"):
        owner.build(trace_data=changed, verify_identity=False)
