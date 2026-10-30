"""Adversarial guards for the E15 callback-teardown ownership proof."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_teardown_ownership as ownership  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_fmv_teardown_ownership.json"
ARTIFACT_SHA256 = "a527f4c25e3fc49b94e6bd10f9e6bc17f5e88efc5e590e12692aed2109709f46"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


@pytest.mark.local_media
def test_artifact_recomputes_from_hash_verified_pristine_inputs():
    retained = load_artifact()
    assert ownership.build() == retained
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert retained["inputs"]["resident_executable"]["identity_verified"] is True
    assert retained["inputs"]["fmv_bin"]["identity_verified"] is True
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_teardown_return_and_live_observer_fact_remain_distinct():
    doc = load_artifact()
    guest = doc["teardown"]["guest_return"]
    assert guest["classification"] == "conventional_balanced_return"
    assert guest["stack_allocation"] == 24
    assert guest["saved_ra"] == {"store": "0x800709B0", "offset": 16}
    assert guest["restored_ra"] == {"load": "0x80070A20", "offset": 16}
    assert guest["return_instruction"] == "0x80070A28"
    assert guest["caller_continuation"] == "0x800B74AC"
    assert guest["synthetic_guest_return_instruction"] is False
    assert doc["retained_live_join"]["function_trace_synthetic_unwind"] is True
    assert doc["reconciliation"]["synthetic_unwind_is_guest_return"] is False


def test_default_ready_slot_xrefs_and_dispatches_are_exhaustive():
    ready = load_artifact()["callback_backends"]["default"]["ready"]
    assert ready["address"] == "0x800818C8"
    assert ready["summary"] == {
        "total_direct_xrefs": 8,
        "reads": 5,
        "writes": 3,
        "guarded_dispatches": 4,
        "all_direct_xrefs_classified": True,
    }
    assert [row["instruction"]["pc"] for row in ready["xrefs"]] == [
        "0x8006D8D4", "0x8006D8DC", "0x8006E5BC", "0x8006E844",
        "0x8006ECB4", "0x8006F010", "0x8006F098", "0x8006F600",
    ]
    assert [row["guarded_dispatch"]["pc"] for row in ready["xrefs"]
            if "guarded_dispatch" in row] == [
        "0x8006E5D8", "0x8006E860", "0x8006ECD0", "0x8006F61C",
    ]
    data = load_artifact()["callback_backends"]["default"]["data"]
    assert data["function"]["behavior"] == "DMACallback(3, a0)"
    assert data["sdk_dispatch"]["jalr"] == "0x8006544C"
    assert "kernel-private" in data["sdk_dispatch"]["storage_boundary"]


def test_endpoint_words_are_mmio_pointer_cells_not_callback_storage():
    table = load_artifact()["cdrom_mmio_pointer_table"]
    assert table["values"] == [
        "0x1F801800", "0x1F801801", "0x1F801802", "0x1F801803"]
    assert table["retained_capture"] == {
        "hex": "0018801f0118801f0218801f0318801f",
        "positive_matches_pristine_table": True,
        "negative_matches_pristine_table": True,
        "captured_words_are_pointer_cells": True,
        "captured_words_are_callback_storage": False,
        "equal_after_capture_is_expected": True,
    }
    assert [(row["pointer_cell"], row["target"], row["store"])
            for row in table["teardown_target_stores"]] == [
        ("0x80081C28", "0x1F801800", "0x80070A04"),
        ("0x80081C34", "0x1F801803", "0x80070A14"),
    ]
    assert load_artifact()["summary"][
        "unresolved_game_owned_teardown_interfaces"] == 0


@pytest.mark.local_media
def test_opcode_xref_pointer_and_live_mutations_fail_closed():
    exe = bytearray(ownership.EXE_PATH.read_bytes())
    offset = ownership.EXE_HEADER + 0x80070A28 - ownership.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="callback teardown opcode drifted"):
        ownership.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(ownership.EXE_PATH.read_bytes())
    offset = ownership.EXE_HEADER + 0x8006E5BC - ownership.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(
            SystemExit, match="ready-callback slot xref census drifted"):
        ownership.build(exe_data=bytes(exe), verify_identity=False)

    exe = bytearray(ownership.EXE_PATH.read_bytes())
    offset = ownership.EXE_HEADER + 0x80081C28 - ownership.EXE_BASE
    struct.pack_into("<I", exe, offset, 0)
    with pytest.raises(SystemExit, match="MMIO pointer table drifted"):
        ownership.build(exe_data=bytes(exe), verify_identity=False)

    fmv = bytearray(ownership.FMV_PATH.read_bytes())
    offset = 0x800B74A4 - ownership.FMV_BASE
    struct.pack_into("<I", fmv, offset, 0)
    with pytest.raises(SystemExit, match="FMV teardown caller/backend opcode"):
        ownership.build(fmv_data=bytes(fmv), verify_identity=False)

    lifecycle = copy.deepcopy(json.loads(ownership.LIFECYCLE_PATH.read_text()))
    lifecycle["observations"]["positive_common_exit"]["callback_teardown"][
        "exit_is_synthetic_unwind"] = False
    with pytest.raises(SystemExit, match="live observation drifted"):
        ownership.build(lifecycle_doc=lifecycle, verify_identity=False)


def test_schema_and_registry_keep_cross_boundary_interfaces_partial():
    schema = yaml.safe_load((ROOT / "config/phase4_fmv.yaml").read_text())
    assert schema["schema"] == "abl-phase4-fmv/11"
    contract = schema["teardown_ownership"]
    assert contract["guest_return"]["classification"] == \
        "conventional_balanced_return"
    assert contract["default_ready_slot"]["direct_xrefs"] == 8
    assert contract["mmio_pointer_table"]["captured_words_are_pointer_cells"] \
        is True
    registry = yaml.safe_load(
        (ROOT / "config/phase4_campaigns.yaml").read_text())
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "fmv_playback")
    claim = campaign["dimension_claims"]["original_interfaces"]
    assert claim["claim"] == "partial"
    assert claim["confidence"] == "partial"
    assert any(row["intersects_dimension"] is True
               for row in claim["residuals"])
    assert campaign["dimension_claims"].get("lifecycle") is None
