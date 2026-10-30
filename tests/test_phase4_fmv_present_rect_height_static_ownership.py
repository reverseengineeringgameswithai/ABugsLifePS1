"""Adversarial guards for the E15 presentation-height static owner."""
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

import phase4_fmv_present_rect_height_static_ownership as owner  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_fmv_present_rect_height_static_ownership.json"


@pytest.mark.local_media
def test_present_height_static_owner_recomputes_from_pristine_inputs():
    retained = json.loads(ARTIFACT.read_text())
    assert owner.build() == retained
    assert retained["inputs"]["resident_executable"]["identity_verified"] is True
    assert retained["inputs"]["fmv_bin"]["identity_verified"] is True
    assert retained["offline_localization"]["external_index"]["sha256"] == (
        "e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab"
    )
    for path, expected in retained["source_dependencies"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_cached_height_pointer_alias_and_all_callers_are_exact():
    document = json.loads(ARTIFACT.read_text())
    publish = document["overlay_cached_height_publish"]
    assert publish["player_boundary_base"] == "0x800CABE0"
    assert [row["pc"] for row in publish["direct_callers"]["0x800B6A7C"]] == [
        "0x800B6C34"
    ]
    assert [row["pc"] for row in publish["direct_callers"]["0x800B6C24"]] == [
        "0x800B70A0", "0x800B7280"
    ]
    assert publish["direct_callers"]["unclassified"] == []
    assert publish["cached_height_load"]["source_address"] == "0x800B9A5C"
    assert [
        (row["pc"], row["offset"], row["destination"], row["field"])
        for row in publish["height_stores"]
    ] == [
        ("0x800B6BE8", "0x1E", "0x800CABFE", "rect_bank_1_h"),
        ("0x800B6BEC", "0x16", "0x800CABF6", "rect_bank_0_h"),
        ("0x800B6BF0", "0x2A", "0x800CAC0A", "present_rect_h"),
    ]


def test_loadimage_driver_table_and_dws_clamp_are_classified():
    document = json.loads(ARTIFACT.read_text())
    sdk = document["resident_sdk_normalization"]
    dispatch = sdk["LoadImage_dispatch"]
    assert dispatch["driver_pointer_address"] == "0x8007FBC0"
    assert dispatch["driver_pointer_value"] == "0x8007FB80"
    assert dispatch["driver_2"] == "0x800646B8"
    assert dispatch["driver_8"] == "0x800640CC"
    assert dispatch["vtable"][8] == {"index": 8, "value": "0x800640CC"}
    assert sdk["_dws_clamp"]["height_store"] == {
        "pc": "0x80064178",
        "word": "0xA6240006",
        "mnemonic": "sh a0,6(s1)",
        "field": "RECT.h",
        "classification": "downstream SDK bounds normalization",
    }
    assert document["source_status"]["status"] == {
        "LoadImage": "matching_c",
        "_dws": "hash_pinned_external_asm",
        "gpu_present_drawotag_vsync": "hash_pinned_external_asm",
        "fmv_player": "documentation_grade_semantic_c",
    }


def test_retained_saturated_pc_join_is_complete_but_not_promoted():
    document = json.loads(ARTIFACT.read_text())
    joined = document["runtime_writer_join"]
    assert joined["writer_pc_counts"] == {
        "0x80064178": 28,
        "0x800b6bf0": 3,
        "0x800b6f18": 1,
    }
    assert joined["unclassified_writer_pcs"] == []
    assert joined["complete_sequence_closed"] is False
    assert document["falsifier"]["outcome"] == "survived"
    assert all(document["falsifier"]["checks"].values())
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["next_lane"] == "live"
    assert "Do not repeat the broad" in document["claim_boundary"]["next_method"]


@pytest.mark.local_media
def test_opcode_and_vtable_mutations_turn_static_ownership_red():
    fmv = bytearray(owner.FMV_PATH.read_bytes())
    struct.pack_into(
        "<I", fmv, 0x800B6BF0 - owner.FMV_BASE, 0
    )
    with pytest.raises(ValueError, match="opcode drift"):
        owner.build(fmv_data=bytes(fmv), verify_identity=False)

    fmv = bytearray(owner.FMV_PATH.read_bytes())
    struct.pack_into(
        "<I", fmv, 0x800B7280 - owner.FMV_BASE, 0
    )
    with pytest.raises(ValueError, match="opcode drift|caller census"):
        owner.build(fmv_data=bytes(fmv), verify_identity=False)

    exe = bytearray(owner.EXE_PATH.read_bytes())
    struct.pack_into(
        "<I",
        exe,
        owner.EXE_HEADER + 0x8007FBA0 - owner.EXE_BASE,
        0x80064308,
    )
    with pytest.raises(ValueError, match="vtable drifted"):
        owner.build(exe_data=bytes(exe), verify_identity=False)


def test_prior_result_mutation_rejects_the_runtime_join(monkeypatch):
    original = owner._prior_evidence
    static, prior, hashes = original()
    changed = copy.deepcopy(prior)
    changed["observation"]["precise"]["native"]["writer_pc_counts"][
        "0x80064178"
    ] = 27
    monkeypatch.setattr(
        owner, "_prior_evidence", lambda: (static, changed, hashes)
    )
    with pytest.raises(ValueError, match="writer PC count drifted"):
        owner.build(verify_identity=False)
