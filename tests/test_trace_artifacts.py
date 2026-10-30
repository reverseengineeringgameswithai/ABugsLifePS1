"""Schema guards for the committed Phase-4 trace artifacts (CI-safe).

Content REGENERATION is live (isolated DuckStation + movie replay via
tools/trace_boot_baseline.py + tools/chunk_evidence.py); these tests only
validate the committed artifacts' shape and internal consistency.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACES = ROOT / "analysis" / "traces"
_HEX = re.compile(r"^0x[0-9a-f]{8}$")


def _load(name):
    return json.loads((TRACES / name).read_text(encoding="utf-8"))


def test_boot_trace_schema():
    doc = _load("boot_trace.json")
    assert doc["disc"]["serial"] == "SCUS-94288"
    assert doc["movie"]["path"] == "flik_to_level01_stall.mv.movie.json"
    assert doc["movie"]["input_frames"] > 0
    assert doc["anchors"], "no anchor watch results"
    for label, rec in doc["anchors"].items():
        assert _HEX.match(rec["pc"]), (label, rec)
        assert rec["hit_count"] >= 0
    # Boot-shadow limitation (see tools/trace_boot_baseline.py): entry0 and
    # the single main-shell call execute in the ~2 frames before watches can
    # be armed (from_boot playback clears instrumentation on its reload), so
    # assert on anchors the design can reliably observe instead.
    assert doc["anchors"]["gameplay_state_machine"]["hit_count"] >= 1
    assert doc["anchors"]["level_raw_lzss_decompress"]["hit_count"] >= 1
    assert doc["state_writes"], "state-variable write watches missing"


def test_overlay_loads_schema():
    doc = _load("overlay_loads.json")
    assert doc["regions"], "no disc-provenance resolutions recorded"
    for label, hist in doc["regions"].items():
        assert isinstance(hist, list) and hist, (label, hist)
        for rec in hist:
            assert rec.get("resolved") is True, (label, rec)
            assert rec.get("file"), f"{label} resolved without a file"
            assert rec.get("_first_seen_by_frame")
    assert "entry_first_exec" in doc


def test_function_hits_csv():
    rows = list(csv.DictReader((TRACES / "function_hits.csv").open()))
    assert rows, "no dynamic function hits recorded"
    for r in rows:
        assert _HEX.match(r["address"]), r
        assert int(r["hits"]) >= 1
    # feeds the census: every hit address must be a resident census start
    census = json.loads((ROOT / "analysis" / "functions.json").read_text())
    starts = {r["start"] for r in census["functions"] if r["space"] == "resident"}
    overlay_targets = set(census["resident_overlay_entry_targets"])
    for r in rows:
        assert r["address"] in starts or r["address"] in overlay_targets, \
            f"trace hit {r['address']} is neither a census start nor an overlay entry"


def test_level_raw_chunks_schema():
    doc = json.loads((ROOT / "analysis" / "level_raw_chunks.json").read_text())
    chunks = doc["chunks"]
    assert len(chunks) == 69
    assert {c["chunk_id"] for c in chunks} == set(range(69))
    for c in chunks:
        assert c["comp_size"] > 0 and c["decomp_size"] > 0
        assert c["confidence"] in ("confirmed", "confirmed_format", "likely")
        if c["runtime_load_observed"]:
            assert c["load_address"] is None or _HEX.match(c["load_address"])
            assert c["decompress_calls_observed"] >= 1
    assert any(c["runtime_load_observed"] for c in chunks), \
        "no chunk has runtime load evidence"
