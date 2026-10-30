"""Falsification guards for the static C15 Region-A writer breadth census."""
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

import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_respawn_writer_catalog as catalog  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_respawn_writer_catalog.json"
ARTIFACT_SHA256 = "647b1c23d75b35bf80424cb5c98b618d6afc448a19e629b5730fcbacc3ba6d80"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_catalog_keeps_static_scope_and_c15_open():
    document = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert document["schema"] == "abl-phase4-respawn-writer-catalog/1"
    assert document["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_respawn_writer_catalog.py").read_bytes()).hexdigest()
    assert document["summary"] == {
        "staged_input_count": 11,
        "writer_file_count": 5,
        "direct_write_count": 21,
        "target_write_counts": {
            "safe_anchor_x": 5,
            "safe_anchor_y": 8,
            "safe_anchor_z": 5,
            "safe_anchor_heading": 3,
        },
        "writer_paths": [
            "LEVEL03/LEVEL.BIN", "LEVEL04/LEVEL.BIN", "LEVEL06/LEVEL.BIN",
            "LEVEL08/LEVEL.BIN", "LEVEL10/LEVEL.BIN"],
        "zero_direct_writer_paths": [
            "REBUILD/files/LEVEL00/LEVEL.BIN",
            "REBUILD/files/LEVEL01/LEVEL.BIN",
            "REBUILD/files/LEVEL02/LEVEL.BIN",
            "REBUILD/files/LEVEL05/LEVEL.BIN",
            "REBUILD/files/LEVEL07/LEVEL.BIN",
            "REBUILD/files/LEVEL09/LEVEL.BIN",
        ],
        "new_static_only_variants": [
            "REBUILD/files/LEVEL06/LEVEL.BIN",
            "REBUILD/files/LEVEL08/LEVEL.BIN",
        ],
        "new_static_only_resident_entry_call_sites": [
            {
                "path": "REBUILD/files/LEVEL06/LEVEL.BIN",
                "entry": "0x800B3AEC",
                "resident_call_sites": [
                    "0x8005484c", "0x8005485c", "0x8005b194"],
            },
            {
                "path": "REBUILD/files/LEVEL08/LEVEL.BIN",
                "entry": "0x800B3AE8",
                "resident_call_sites": ["0x8005b1a4"],
            },
        ],
    }
    assert document["writer_functions"]["LEVEL06/LEVEL.BIN"][
        "evidence_scope"] == "static_only"
    assert document["writer_functions"]["LEVEL08/LEVEL.BIN"][
        "evidence_scope"] == "static_only"
    assert "runtime activation" in document["bounded_interpretation"][
        "still_unknown"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["C15_checkpoints"]["state"] == "open"
    assert coverage["counts"] == {
        "baseline_rows": 107, "campaign_complete": 15,
        "reviewed_absent": 1, "complete_total": 16, "open": 91}


@pytest.mark.local_media
def test_catalog_recomputes_from_all_hash_pinned_staged_inputs():
    assert catalog.build_document() == load_artifact()
    document = load_artifact()
    writers = document["writer_functions"]
    assert writers["LEVEL06/LEVEL.BIN"]["sha256"] == \
        "33b21c83ad52f8ef13786de5ff7d48ed615fcae8618d7c8833b64c6b481656be"
    assert writers["LEVEL08/LEVEL.BIN"]["sha256"] == \
        "4b2e8bccbcd42dcb056b267d66a35bb8b7dbfdf9171eccd1a914ff1f67b029c9"
    assert writers["LEVEL06/LEVEL.BIN"]["static_resident_entry_call_sites"] == [
        "0x8005484c", "0x8005485c", "0x8005b194"]
    assert writers["LEVEL08/LEVEL.BIN"]["static_resident_entry_call_sites"] == [
        "0x8005b1a4"]
    assert "loaded-overlay activation" in writers["LEVEL08/LEVEL.BIN"][
        "caller_boundary"]
    level06_values = {
        row["target"]: row["constant_source"]["signed"]
        for row in writers["LEVEL06/LEVEL.BIN"]["direct_writes"]}
    assert level06_values == {
        "safe_anchor_x": 35329, "safe_anchor_y": -85228,
        "safe_anchor_heading": 3063, "safe_anchor_z": -154696}
    level08_values = {
        row["target"]: row["constant_source"]["signed"]
        for row in writers["LEVEL08/LEVEL.BIN"]["direct_writes"]}
    assert level08_values == {
        "safe_anchor_x": -157682, "safe_anchor_y": 5744,
        "safe_anchor_z": -12845, "safe_anchor_heading": 352}
    join = document["existing_live_evidence_join"]
    assert join["artifact_sha256"] == catalog.C15_ARTIFACT_SHA256
    assert join["LEVEL03/LEVEL.BIN"]["selected_row"] == 6
    assert join["LEVEL03/LEVEL.BIN"]["denial_selector_hits"] == 17
    assert join["LEVEL04/LEVEL.BIN"]["access_events"] == 5
    assert join["LEVEL10/LEVEL.BIN"]["access_events"] == 4


@pytest.mark.local_media
def test_store_and_source_mutations_falsify_the_static_census():
    source = bytearray(
        (ROOT / "REBUILD/files/LEVEL06/LEVEL.BIN").read_bytes())
    original = catalog.scan_direct_writes(source)
    assert catalog._expected_tuple(original) == \
        catalog.EXPECTED_WRITES["LEVEL06/LEVEL.BIN"]

    changed_target = copy.copy(source)
    struct.pack_into("<I", changed_target, 0x160, 0xAC236554)
    assert catalog._expected_tuple(catalog.scan_direct_writes(changed_target)) != \
        catalog.EXPECTED_WRITES["LEVEL06/LEVEL.BIN"]

    changed_source = copy.copy(source)
    struct.pack_into("<I", changed_source, 0x158, 0x34038A02)
    changed_rows = catalog.scan_direct_writes(changed_source)
    changed_x = next(row for row in changed_rows
                     if row["target"] == "safe_anchor_x")
    assert changed_x["constant_source"]["signed"] == 35330
    assert changed_rows != original


def test_campaign_registry_consumes_catalog_without_self_certification():
    registry = yaml.safe_load((ROOT / "config/phase4_campaigns.yaml").read_text())
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "safe_respawn_anchor")
    assertions = [
        assertion for group in campaign["evidence"].values()
        for assertion in group
        if assertion["artifact"] == "analysis/phase4_respawn_writer_catalog.json"]
    assert len(assertions) >= 7
    assert all(common.audit_assertion(assertion) == [] for assertion in assertions)
    assert campaign["status"] == "active"
    assert any("LEVEL06" in residual["boundary"]
               for residual in campaign["bounded_residuals"])
