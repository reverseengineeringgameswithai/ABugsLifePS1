"""Guards for the Phase-4 control-plane data-quality repair."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import fixture_reference_sets  # noqa: E402
import knowledge_closure_audit  # noqa: E402


def test_fixture_shorthand_expands_to_centrally_pinned_paths():
    rows = yaml.safe_load(
        (ROOT / "analysis/mechanics_baseline.yaml").read_text())["rows"]
    fixture_reference_sets.validate_rows(rows)
    central_doc = json.loads(
        (ROOT / "analysis/phase2_fixture_audit.json").read_text())
    central = {**central_doc["saves"], **central_doc["movies"]}
    corrected = {
        row["id"]: fixture_reference_sets.resolve_row(row)
        for row in rows if row["id"] in fixture_reference_sets.load()["rows"]
    }

    assert corrected["E04_camera_system"] == [
        "level01.sav",
        "canyon_bug.sav",
        "level_09.sav",
        "level_12.sav",
        "training_all_stuff_collected_ending.sav",
        "movies/Phase4/Interpreter/C17_MovieViewer.movie.sav",
    ]
    assert "movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json" \
        in corrected["E16_streaming_overlays"]
    assert all(path in central for paths in corrected.values() for path in paths
               if path.endswith((".sav", ".json")))


def test_retained_missing_pin_findings_are_not_reingested_as_sources():
    stale = {"missing_fixture_pins": [{"path": "not-a-source.sav"}],
             "real_fixture": "level01.sav"}
    assert "not-a-source.sav" in list(
        knowledge_closure_audit.recursive_strings(stale))
    assert list(knowledge_closure_audit.recursive_strings(
        stale, skip_keys={"missing_fixture_pins"})) == [
        "real_fixture", "level01.sav"]


def test_vab_bank_loader_partition_includes_the_two_gap_words():
    segments = yaml.safe_load((ROOT / "config/segments.yml").read_text())
    row = next(item for item in segments["attempted"]
               if item["start"] == 0x80042E94)
    assert row["end"] == 0x80042FA0

    exe = (ROOT / "REBUILD/files/SCUS_942.88").read_bytes()
    load_address = struct.unpack_from("<I", exe, 0x18)[0]
    offset = 0x800 + 0x80042F90 - load_address
    assert struct.unpack_from("<6I", exe, offset) == (
        0x0C01AC4C,  # jal 0x8006b130
        0x2405FFFF,  # delay slot: addiu a1, zero, -1
        0xA7820410,  # sh v0, 1040(gp)
        0x00021400,  # sll v0, v0, 16
        0x00022C03,  # callable suffix starts: sra a1, v0, 16
        0x04A10007,  # bgez a1, 0x80042fc4
    )
    source = (ROOT / row["source"]).read_text()
    assert "sh\t$v0,1040($gp)" in source
    assert "sll\t$v0,$v0,16" in source
