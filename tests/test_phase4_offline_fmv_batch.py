"""Falsification guards for the generated E15 FMV offline batch."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_offline_fmv_batch as batch  # noqa: E402


def document() -> dict:
    return json.loads(batch.OUTPUT.read_text())


def test_fmv_batch_recomputes_from_exact_preserved_capsule():
    doc = document()
    external = Path(doc["external_index"]["absolute_path"])
    rebuilt_external, rebuilt_summary = batch.build(external)
    assert batch.render(rebuilt_external) == external.read_bytes()
    assert batch.render(rebuilt_summary) == batch.OUTPUT.read_bytes()


def test_fmv_batch_pins_reader_capsule_and_all_queue_queries():
    doc = document()
    assert doc["schema"] == "abl-phase4-offline-fmv-batch/1"
    assert doc["valid"] is True and doc["errors"] == []
    assert doc["campaign_closed"] is False and doc["live_escalation"] is None
    assert doc["selected_rows"] == [{
        "row_id": "E15_fmv", "queue_rank": 5,
        "classification": "offline_partial", "completion_state": "open",
        "capsules": [
            "movies/Phase4/C16_gameover_continue.movie.json",
            "movies/Phase4/E15_fmv_skip.movie.json",
        ],
    }]
    offline = doc["offline_batch"]
    assert offline["reader_sha256"] == \
        "b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde"
    assert offline["capsule_count"] == 2
    assert offline["reconstructed_records"] == 4549
    assert offline["reconstructed_records_by_capsule"] == {
        "movies/Phase4/C16_gameover_continue.movie.json": 4007,
        "movies/Phase4/E15_fmv_skip.movie.json": 542,
    }
    assert offline["query_count"] == len(offline["exact_queue_queries"]) == 18
    assert {
        movie: sum(query["capsule_movie"] == movie
                   for query in offline["exact_queue_queries"])
        for movie in offline["reconstructed_records_by_capsule"]
    } == {
        "movies/Phase4/C16_gameover_continue.movie.json": 9,
        "movies/Phase4/E15_fmv_skip.movie.json": 9,
    }
    assert {query["domain"] for query in offline["exact_queue_queries"]} == {
        "manifest/registers/ram/vram/spu/block_flow", "block_flow", "ram",
        "vram", "spu"}
    assert doc["external_index"] == {
        "absolute_path": str(
            Path.home() / "Downloads/ABL-external-evidence/derived/Phase4/"
            "fmv-lifecycle-v2/index.json"),
        "sha256": "e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab",
        "bytes": 16060589,
        "schema": "abl-phase4-external-fmv-index/1",
        "media_class": "external game-derived evidence; never commit",
        "preservation_required": True,
    }


def test_fmv_batch_indexes_both_current_capsules():
    doc = document()
    assert [(row["movie"], row["records"]) for row in doc["capsule_summaries"]] == [
        ("movies/Phase4/C16_gameover_continue.movie.json", 4007),
        ("movies/Phase4/E15_fmv_skip.movie.json", 542),
    ]
    assert doc["derived_findings"]["primary_movie"] == \
        "movies/Phase4/E15_fmv_skip.movie.json"


def test_fmv_residency_initialization_and_retirement_are_distinct():
    findings = document()["derived_findings"]
    assert findings["overlay_resident_intervals"] == [{"start": 69, "end": 416}]
    sequence = findings["initialization_sequence"]
    assert [(item["movie_frame"], item["completion_request"],
             item["selected_frame_limit"]) for item in sequence] == [
        (69, 721840489, 1), (86, 0, 1), (168, 0, 0), (183, 0, 386)]
    selected = {item["movie_frame"]: item for item in findings["selected_boundaries"]}
    assert selected[333]["pc"] == "0x80070d00"
    assert selected[343]["pc"] == "0x80065340"
    assert selected[416]["typed_state"]["overlay_resident"] is True
    assert selected[417]["typed_state"]["overlay_resident"] is False
    assert selected[417]["typed_state"]["completion_request"] is None
    assert selected[417]["typed_state"]["selected_frame_limit"] is None
    assert selected[541]["typed_state"]["str_backloc"] == 73


def test_fmv_domain_correlations_remain_bounded():
    findings = document()["derived_findings"]
    assert {key: len(value) for key, value in
            findings["range_change_frames"].items()} == {
        "actor_pool": 0, "contact_pool": 0,
        "fmv_boot_buffer_end": 0, "fmv_boot_buffer_start": 0,
        "full_spu_ram": 143, "full_vram": 118, "player_block": 541}
    assert findings["range_change_intervals"]["full_spu_ram"] == [
        {"start": 1, "end": 9}, {"start": 229, "end": 362}]
    assert findings["window_top_blocks"]["pretrigger_and_input"][0] == {
        "pc": "0x800b681c", "count": 47585}
    assert findings["window_top_blocks"]["immediate_skip_response"][4] == {
        "pc": "0x80065340", "count": 107756}
    assert "not exact writer or producer attribution" in \
        document()["bounded_conclusions"][4]


def test_fmv_summary_excludes_raw_external_domains():
    text = batch.OUTPUT.read_text()
    for forbidden in ("raw_ram", "raw_vram", "raw_spu_ram", "capsule_chunks",
                      "movie_bytes", "save_bytes"):
        assert forbidden not in text
    assert document()["external_index"]["media_class"].endswith("never commit")


def test_fmv_guard_rejects_banked_finding_drift(monkeypatch):
    expected = deepcopy(batch.CONFIGURATION["expected_findings"])
    expected["overlay_resident_intervals"] = [{"start": 69, "end": 417}]
    monkeypatch.setitem(batch.CONFIGURATION, "expected_findings", expected)
    with pytest.raises(ValueError, match="overlay-residency interval drifted"):
        batch.build(Path(document()["external_index"]["absolute_path"]))
