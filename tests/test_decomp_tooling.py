"""Guard the decompilation-campaign tooling (CI-safe on committed artifacts).

Covers the candidate ranker (analysis/decomp_candidates.json) and the progress
metric (analysis/decomp_progress.json): schema, excluded-class filtering, ranker
determinism, and consistency of the progress metric with the census `match`
field. No compiler or media needed.
"""
import json

import pytest
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "analysis" / "decomp_candidates.json"
PROGRESS = ROOT / "analysis" / "decomp_progress.json"
CENSUS = ROOT / "analysis" / "functions.json"
_HEX = re.compile(r"^0x[0-9a-f]{8}$")
BSS_START = 0x80082200


def _census():
    return json.loads(CENSUS.read_text())["functions"]


def test_candidates_schema_and_exclusions():
    doc = json.loads(CANDIDATES.read_text())
    cands = doc["candidates"]
    assert doc["total_candidates"] == len(cands)
    matched = {r["start"] for r in _census() if r.get("match")}
    for c in cands:
        assert _HEX.match(c["start"]), c
        assert 0 < c["size"] <= int(doc["params"]["max_size"], 16)
        assert not c["jr_table"], f"{c['start']} is a jr-table fn (excluded class)"
        assert c["has_return"], f"{c['start']} extent truncated (no return)"
        assert int(c["start"], 16) < BSS_START, f"{c['start']} in data region"
        assert c["start"] not in matched, f"{c['start']} already matched"
        if not doc["params"]["include_gp"]:
            assert not c["uses_gp"], f"{c['start']} uses gp (excluded by default)"


def test_candidates_sorted_by_score():
    cands = json.loads(CANDIDATES.read_text())["candidates"]
    keys = [(-c["score"], c["start"]) for c in cands]
    assert keys == sorted(keys), "candidates not in rank order"


@pytest.mark.local_media
def test_candidates_deterministic(tmp_path):
    """Regenerating the ranker with the same inputs is byte-identical."""
    before = CANDIDATES.read_bytes()
    p = subprocess.run([sys.executable, "tools/decomp_candidates.py"],
                       cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert CANDIDATES.read_bytes() == before, "candidate ranking is not deterministic"


ASM2C_QUEUE = ROOT / "analysis" / "asm_to_c_queue.json"


@pytest.mark.local_media
def test_asm_to_c_queue_deterministic_and_valid():
    """The asm->C selector regenerates byte-identically and only lists .s entries
    (ready rows are plain/gp; jr_table/fragment/no_return are deferred)."""
    before = ASM2C_QUEUE.read_bytes()
    p = subprocess.run([sys.executable, "tools/asm_to_c_candidates.py"],
                       cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert ASM2C_QUEUE.read_bytes() == before, "asm->C queue is not deterministic"
    q = json.loads(ASM2C_QUEUE.read_text())
    assert q, "empty queue"
    for r in q:
        assert _HEX.match(r["start"])
        assert r["ready"] == (r["convert"] in ("plain", "gp"))


def test_progress_schema_and_census_consistency():
    prog = json.loads(PROGRESS.read_text())
    res = [r for r in _census() if r["space"] == "resident"]
    m = prog["matched"]
    assert prog["resident_functions"] == len(res)
    # matched counts must equal the census `match` field
    n_asm = sum(1 for r in res if r.get("match") == "asm")
    n_c = sum(1 for r in res if r.get("match") == "c")
    assert m["asm"]["functions"] == n_asm
    assert m["c"]["functions"] == n_c
    assert m["functions"] == n_asm + n_c
    assert 0 <= m["pct_functions"] <= 100 and 0 <= m["pct_bytes"] <= 100
    # bytes add up
    assert m["asm"]["bytes"] + m["c"]["bytes"] == m["bytes"]
