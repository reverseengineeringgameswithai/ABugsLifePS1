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

import phase4_fmv_frame_sync_wait_ownership as ownership  # noqa: E402


def test_frame_sync_wait_ownership_recomputes_without_promotion():
    document = ownership.build()
    assert document == json.loads(ownership.OUTPUT.read_text())
    field = document["typed_state"]
    assert field["canonical_name"] == "frame_sync_wait_latch"
    assert field["owner"] == "shared_frame_sync_interrupt_handshake"
    assert field["legacy_capture_alias"] == "fmv_running_latch"
    assert field["direct_xref_count"] == 10
    assert field["direct_read_count"] == 4
    assert field["direct_write_count"] == 6
    assert field["unclassified_direct_xrefs"] == 0
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["lifecycle_promoted"] is False
    assert document["claim_boundary"]["new_live_escalation_authorized"] is False
    assert document["falsifier"]["outcome"] == "survived"
    assert all(document["falsifier"]["checks"].values())


def test_complete_xref_and_shared_helper_censuses_are_typed():
    document = ownership.build()
    field = document["typed_state"]
    assert [row["pc"] for row in field["direct_xrefs"]] == [
        f"0x{pc:08X}" for pc in ownership.EXPECTED_XREFS
    ]
    static = document["pristine_static_ownership"]
    assert static["shared_helper_call_count"] == 5
    assert static["unclassified_helper_callers"] == 0
    assert [row["pc"] for row in static["shared_helper_callers"]] == [
        f"0x{pc:08X}" for pc in ownership.EXPECTED_HELPER_CALLS
    ]
    assert static["fmv_exclusive"] is False
    assert static["owner_classes"] == [
        "context_save_interrupt",
        "pad_subsystem_lifecycle",
        "level_transition",
        "display_loop",
        "gameplay_reset",
        "scene_flow_inline_wait",
    ]


def test_shared_and_inline_protocols_are_instruction_identical():
    protocols = ownership.build()["pristine_static_ownership"]["protocols"]
    shared = protocols["shared_helper"]["instructions"]
    inline = protocols["scene_flow_inline"]["instructions"]
    assert [row["word"] for row in shared] == [row["word"] for row in inline]
    assert protocols["scene_flow_inline"]["control_pc"] == "0x8004FEA4"
    assert [row["clear_pc"] for row in protocols["interrupt_clearers"]] == [
        "0x8001864C",
        "0x80018784",
    ]
    assert [row["pc"] for row in protocols["pad_lifecycle_clearers"]] == [
        "0x8003E848",
        "0x8003E8D8",
    ]


@pytest.mark.local_media
@pytest.mark.parametrize(
    "pc",
    [
        0x8001864C,
        0x8003E848,
        0x8003F330,
        0x8003F340,
        0x8004FEA0,
        0x8004FEB0,
        0x80052338,
    ],
)
def test_load_bearing_static_mutations_turn_guard_red(pc: int):
    data = bytearray(ownership.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        data,
        ownership.EXE_HEADER + pc - ownership.EXE_BASE,
        0,
    )
    with pytest.raises(
        ValueError,
        match=(
            "slice identity|direct xref census|protocol|caller census|"
            "clear/frame_present"
        ),
    ):
        ownership.build(exe_data=bytes(data), verify_identity=False)


def test_retained_boundary_cannot_be_rewritten_as_retirement(monkeypatch):
    original = ownership.common.load_json

    def changed_load(path: Path):
        document = original(path)
        if path.name == "phase4_fmv_levelb_pre15792_partition.json":
            document = copy.deepcopy(document)
            document["offline_localization"][
                "staged_current_toolchain_boundary"
            ]["pc"] = "0x8005029C"
        return document

    monkeypatch.setattr(ownership.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="frame-15720 boundary"):
        ownership._prior_evidence()


def test_work_packet_is_external_and_hash_load_bearing():
    document = ownership.build()
    expected = document["external_dependencies"][
        "run:iteration-1-receipts/work-packet.json"
    ]
    path = Path(ownership.CONFIG["work_packet"]["absolute_path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
