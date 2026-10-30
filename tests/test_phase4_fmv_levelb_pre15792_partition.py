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

import phase4_fmv_levelb_pre15792_partition as partition  # noqa: E402


def test_pre15792_partition_recomputes_without_promotion():
    document = partition.build()
    assert document == json.loads(partition.OUTPUT.read_text())
    staged = document["offline_localization"][
        "staged_current_toolchain_boundary"
    ]
    assert (staged["frame"], staged["cycle"], staged["pc"], staged["sp"]) == (
        15720,
        8900142073,
        "0x8004FEA4",
        "0x801FFFD0",
    )
    assert staged["paired_equal"] is True
    assert staged["payload_retained"] is False
    excluded = document["offline_localization"]["excluded_later_window"]
    assert excluded == {
        "candidate_hits": 0,
        "candidate_pcs": ["0x8004FD74", "0x8005029C"],
        "failure_frame": 15857,
        "outcome": "falsified",
        "source_artifact":
            "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json",
        "start": 15792,
        "stop": 15856,
    }
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["new_live_escalation_authorized"] is False
    assert document["falsifier"]["outcome"] == "survived"
    assert all(document["falsifier"]["checks"].values())
    sync = document["typed_state"]["frame_sync_wait_latch"]
    assert sync["owner"] == "shared_frame_sync_interrupt_handshake"
    assert sync["legacy_capture_alias"] == "fmv_running_latch"
    assert "wait_latch" not in document["typed_state"]


def test_candidate_predecessors_and_nonintersecting_residual_are_complete():
    document = partition.build()
    static = document["static_partition"]
    assert static["candidate_count"] == 2
    assert static["predecessor_count"] == 4
    assert static["unclassified_callers"] == 0
    assert static["unclassified_predecessors"] == 0
    candidates = static["completed_level_b_candidates"]
    assert [(row["pc"], row["scene"], row["transition"]) for row in candidates] == [
        ("0x8004FD74", 3, 0),
        ("0x8005029C", 6, 128),
    ]
    assert [row["class"] for row in candidates[0]["predecessors"]] == [
        "pending_scene_request_negative"
    ]
    assert [row["class"] for row in candidates[1]["predecessors"]] == [
        "pending_request_acceptance_return_nonzero",
        "pending_scene_request_nonnegative_after_wait",
        "pending_scene_request_nonnegative_loop_tail",
    ]
    assert static["nonintersecting_residuals"] == [{
        "owner": "natural LOSE continuation",
        "pc": "0x800500E4",
        "reason": "scene_setup_and_load(5, 64), not completed-Level-B",
    }]


def test_pending_scene_request_direct_xref_census_is_typed():
    state = partition.build()["typed_state"]["pending_scene_request"]
    assert state["address"] == "0x8009EDCC"
    assert state["width"] == "s32"
    assert state["residency"] == "resident"
    assert state["direct_xref_count"] == 13
    assert state["direct_read_count"] == 10
    assert state["direct_write_count"] == 3
    assert state["unclassified_direct_xrefs"] == 0
    assert [row["instruction"]["pc"] for row in state["direct_xrefs"]] == [
        f"0x{pc:08X}" for pc in partition.EXPECTED_PENDING_XREFS
    ]


def test_early_return_gate_has_one_complete_def_use_chain():
    gate = partition.build()["transitive_return_gate"]
    assert gate["classification"] == \
        "pending_request_acceptance_return_contract"
    assert gate["scene_flow_consumer"]["call"]["pc"] == "0x8004FDF0"
    assert gate["scene_flow_consumer"]["branch"]["pc"] == "0x8004FDF8"
    assert gate["scene_flow_consumer"]["branch_target"] == "0x8005029C"
    assert gate["acceptor"]["result_set_count"] == 1
    assert gate["acceptor"]["result_domain"] == [0, 1]
    assert [
        row["name"] for row in gate["acceptor"]["required_predicates"]
    ] == [
        "decoded_input_bit_zero_present",
        "local_one_shot_clear",
        "pending_scene_request_nonnegative",
    ]
    assert gate["wrapper"]["saved_result_redefinitions"] == 0
    assert gate["def_use_chain"] == [
        "0x8005B63C:s5=1",
        "0x8005B6C8:v0=s5",
        "0x8005B850:s1=v0",
        "0x8005BC40:v0=s1",
        "0x8004FDF8:branch_if_v0_nonzero",
        "0x8005029C:scene_setup_and_load(6,128)",
    ]
    assert gate["unclassified_result_definitions"] == 0
    assert gate["natural_execution_claimed"] is False


@pytest.mark.local_media
@pytest.mark.parametrize("pc", [0x8004FD74, 0x8004FDF8, 0x8004FAA0])
def test_static_partition_mutations_turn_guard_red(pc: int):
    data = bytearray(partition.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        data,
        partition.EXE_HEADER + pc - partition.EXE_BASE,
        0,
    )
    with pytest.raises(
        ValueError,
        match=(
            "function identity|candidate predecessor|direct xref census"
        ),
    ):
        partition.build(exe_data=bytes(data), verify_identity=False)


@pytest.mark.local_media
@pytest.mark.parametrize(
    "pc",
    [
        0x8005B604,  # decoded-input mask
        0x8005B610,  # one-shot rejection
        0x8005B624,  # pending-request sign rejection
        0x8005B63C,  # only accepted-result set
        0x8005B6C8,  # callee return copy
        0x8005B850,  # wrapper result save
        0x8005BC40,  # wrapper return copy
    ],
)
def test_transitive_return_gate_mutations_turn_guard_red(pc: int):
    data = bytearray(partition.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        data,
        partition.EXE_HEADER + pc - partition.EXE_BASE,
        0,
    )
    with pytest.raises(
        ValueError,
        match=(
            "function identity|request-acceptance|saved request|transitive"
        ),
    ):
        partition.build(exe_data=bytes(data), verify_identity=False)


def test_prior_no_hit_cannot_be_rewritten_as_a_positive(monkeypatch):
    original = partition.common.load_json

    def changed_load(path: Path):
        document = original(path)
        if path.name == "phase4_fmv_levelb_two_pc_first_hit_result.json":
            document = copy.deepcopy(document)
            document["observation"]["candidate_pc_hits"] = 1
        return document

    monkeypatch.setattr(partition.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="prior transition/no-hit"):
        partition._prior_evidence()


def test_external_query_receipts_and_outputs_are_hash_load_bearing():
    document = partition.build()
    for token, expected in document["external_dependencies"].items():
        path = partition.RUN_ROOT / token.removeprefix("run:")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
