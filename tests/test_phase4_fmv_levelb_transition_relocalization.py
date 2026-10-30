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

import phase4_fmv_levelb_transition_relocalization as relocalize  # noqa: E402


def test_frame_15816_anchor_is_relocalized_without_promotion():
    document = relocalize.build()
    assert document == json.loads(relocalize.OUTPUT.read_text())
    assert document["observed_anchor"]["frame"] == 15816
    assert document["observed_anchor"]["cycle"] == 8954497636
    assert document["observed_anchor"]["pc"] == "0x8004FEA4"
    assert document["observed_anchor"]["retired_fmv_head_absent"] is True
    assert document["relocalization"]["old_anchor"] == {
        "frame": 15816,
        "start_pc": "0x80046078",
        "outcome": "falsified_repeated",
        "retired": True,
    }
    assert document["relocalization"]["earlier_first_hit_set"] == [
        "0x8004FD74",
        "0x8005029C",
    ]
    assert document["relocalization"]["first_hit_set_complete"] is True
    assert document["relocalization"]["new_live_escalation_authorized"] is False
    assert document["falsifier"]["outcome"] == "survived"
    assert all(document["falsifier"]["checks"].values())
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["summary"]["new_offline_queries"] == 1
    assert document["summary"]["new_live_receipts"] == 0


def test_completed_level_b_boundaries_and_resource_chain_are_exact():
    document = relocalize.build()
    assert [
        (row["pc"], row["a0"], row["a1"])
        for row in document["earlier_transition_boundaries"]
    ] == [
        ("0x8004FD74", 3, 0),
        ("0x8005029C", 6, 128),
    ]
    assert [
        row["pc"] for row in document["nonnegative_boundary_predecessors"]
    ] == ["0x8004FDF8", "0x80050124", "0x80050248"]
    assert [
        row["pc"] for row in document["common_resource_chain"]
    ] == ["0x800503B0", "0x800503CC", "0x8003D310", "0x80046078"]
    assert document["evidence_boundary"]["causal_confirmation"] is None
    assert "exact natural branch" in document["evidence_boundary"]["inference"]


@pytest.mark.local_media
@pytest.mark.parametrize(
    ("pc", "message"),
    [
        (0x8004FD74, "opcode drift|function identity"),
        (0x80050248, "opcode drift|function identity"),
        (0x800503B0, "opcode drift|function identity"),
        (0x8003D30C, "opcode drift|function identity"),
    ],
)
def test_static_boundary_mutations_turn_guard_red(pc: int, message: str):
    data = bytearray(relocalize.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        data,
        relocalize.EXE_HEADER + pc - relocalize.EXE_BASE,
        0,
    )
    with pytest.raises(ValueError, match=message):
        relocalize.build(exe_data=bytes(data), verify_identity=False)


def test_retained_exact_pc_falsifier_cannot_be_promoted(monkeypatch):
    original = relocalize.common.load_json

    def changed_load(path: Path):
        document = original(path)
        if path.name == "phase4_fmv_levelb_region_b_dma_exact_pc_result.json":
            document = copy.deepcopy(document)
            document["claim_boundary"]["dimension_promoted"] = True
        return document

    monkeypatch.setattr(relocalize.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="retained exact-PC falsifier"):
        relocalize._prior_evidence()


def test_external_receipt_and_projection_hashes_are_load_bearing():
    document = relocalize.build()
    for token, expected in document["external_dependencies"].items():
        path = relocalize.RUN_ROOT / token.removeprefix("run:")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
