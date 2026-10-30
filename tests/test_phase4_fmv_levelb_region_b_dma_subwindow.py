from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_region_b_dma_subwindow as subwindow  # noqa: E402


def test_exact_pc_subwindow_is_static_and_nonpromoting():
    document = subwindow.build()
    assert document["falsifier"]["outcome"] == "survived"
    assert document["transfer_geometry"] == {
        "file_bytes": 36448,
        "sector_bytes": 2048,
        "sector_count": 18,
        "padded_transfer_bytes": 36864,
        "sector_tail_overlap_bytes": 416,
        "pre_cdread_tail_save": {
            "pc": "0x80046068",
            "destination": "0x8009B890",
            "source": "0x800B5788+36448",
            "bytes": 416,
        },
        "post_cdread_tail_restore": {
            "pc": "0x800460B8",
            "destination": "0x800B5788+36448",
            "source": "0x8009B890",
            "bytes": 416,
        },
        "tail_copies_are_dma": False,
    }
    window = document["exact_pc_subwindow"]
    assert window["start"]["pc"] == "0x80046078"
    assert window["start"]["boundary"] == "before_instruction"
    assert window["start"]["register_assertions"] == {
        "a0": 18,
        "a1": "0x800B5788",
    }
    assert window["stop"]["pc"] == "0x800460C4"
    assert window["cdread_submissions_between_stops"] == 1
    assert window["later_universal_loader_retry_excluded"] is True
    assert document["cdread_direct_call_census"]["unclassified_calls"] == []
    assert document["claim_boundary"]["next_lane"] == "static"
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["summary"]["new_offline_queries"] == 0
    assert document["summary"]["new_live_receipts"] == 0
    assert subwindow.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


def test_cdread_call_opcode_mutation_fails():
    data = bytearray(subwindow.EXE_PATH.read_bytes())
    offset = (
        subwindow.EXE_HEADER + 0x80046078 - subwindow.EXE_BASE
    )
    data[offset:offset + 4] = (0).to_bytes(4, "little")
    with pytest.raises(ValueError, match="opcode drift|function slice"):
        subwindow.build(exe_data=bytes(data), verify_identity=False)


def test_memory_bin_extent_mutation_fails():
    data = subwindow.MEMORY_PATH.read_bytes()[:-1]
    with pytest.raises(ValueError, match="byte extent"):
        subwindow.build(memory_data=data, verify_identity=False)


def test_destination_liveness_mutation_fails():
    data = bytearray(subwindow.EXE_PATH.read_bytes())
    offset = (
        subwindow.EXE_HEADER + 0x80046074 - subwindow.EXE_BASE
    )
    data[offset:offset + 4] = (0x00002821).to_bytes(4, "little")
    with pytest.raises(ValueError, match="opcode drift|function slice"):
        subwindow.build(exe_data=bytes(data), verify_identity=False)


def test_global_second_cdread_call_must_remain_classified():
    data = bytearray(subwindow.EXE_PATH.read_bytes())
    offset = (
        subwindow.EXE_HEADER + 0x8006FFEC - subwindow.EXE_BASE
    )
    data[offset:offset + 4] = (0).to_bytes(4, "little")
    with pytest.raises(
        ValueError,
        match="opcode drift|function slice|direct-call census",
    ):
        subwindow.build(exe_data=bytes(data), verify_identity=False)


def test_prior_rejected_method_cannot_be_rewritten_as_evidence(monkeypatch):
    original = subwindow.common.load_json

    def changed_load(path: Path):
        document = original(path)
        if path.name == "phase4_fmv_levelb_region_b_dma_late_result.json":
            document = copy.deepcopy(document)
            document["observation"]["precise"]["receipt_present"] = True
        return document

    monkeypatch.setattr(subwindow.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="rejected late-DMA"):
        subwindow._prior_evidence()


def test_work_packet_falsifier_is_load_bearing(monkeypatch):
    original = subwindow.common.load_json

    def changed_load(path: Path):
        document = original(path)
        if path.name == "iteration-2-work-packet.json":
            document = copy.deepcopy(document)
            document["falsifier"] = "accept destination drift"
        return document

    monkeypatch.setattr(subwindow.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="work packet semantic"):
        subwindow._work_packet()
