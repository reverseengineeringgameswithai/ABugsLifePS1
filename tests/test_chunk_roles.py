"""CI-safe checks on the committed LEVEL.RAW chunk-role manifest (GAP-0022).

Validates the metadata-only manifest (tools/level_raw_chunk_roles.json) without any
copyrighted payload or local media — the manifest is committed; the generator
(tools/level_raw_chunk_manifest.py) needs the local decompressed cache and is not run here.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools" / "level_raw_chunk_roles.json"


def _rows():
    return json.loads(MANIFEST.read_text())


def test_manifest_present_and_complete():
    rows = _rows()
    assert len(rows) == 69, "LEVEL01 LEVEL.RAW has 69 chunks"
    assert [r["chunk"] for r in rows] == list(range(69)), "chunks 0..68 in order"


def test_every_chunk_classified():
    rows = _rows()
    # 80% acceptance target; we expect 100% (no Unknown)
    classified = [r for r in rows if r["confidence"] != "Unknown"]
    assert len(classified) >= int(0.8 * len(rows)), "at least 80% classified"
    assert len(classified) == len(rows), "all 69 classified (no Unknown)"


def test_regions_and_markers_sane():
    rows = _rows()
    for r in rows:
        assert r["region"] in {"A", "B", "C", "?"}
        assert r["comp"] > 0 and r["decomp"] > 0
        assert r["marker"].startswith("0x")
        assert len(r["sha256_16"]) == 16
    # known anchors
    by = {r["chunk"]: r for r in rows}
    assert by[31]["region"] == "B" and by[31]["marker"] == "0x23"   # seed table
    assert by[32]["marker"] == "0x103"                               # collision + sky
    assert by[34]["marker"] == "0x101" and by[34]["idx4"] == 0       # master mesh def
    assert by[35]["marker"] == "0x102" and by[35]["idx4"] == 0       # master mesh payload
