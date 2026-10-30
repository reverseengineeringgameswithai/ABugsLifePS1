"""Guard the committed whole-image function census (analysis/functions.json).

CI-safe: all invariants below run against the COMMITTED census + committed
symbol map — no media needed. The regeneration-identity test (committed ==
freshly regenerated) needs the owner's EXE/overlays and is local_media-gated.
"""
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "analysis" / "functions.json"
CSV = ROOT / "analysis" / "functions.csv"
SYMBOLS = ROOT / "symbols" / "re_symbols.sym"

TEXT_LO, TEXT_HI = 0x80010000, 0x80082800
REGION_A, REGION_B = 0x800B39A0, 0x800B5788

CONFIDENCES = {"confirmed", "high", "medium", "low"}
CLASSIFICATIONS = {"game", "sdk_psyq", "bios_thunk", "crt0", "unknown", "data"}
RANGE_TYPES = {"code", "thunk", "jumptable_case_block", "data"}
_HEX = re.compile(r"^0x[0-9a-f]{8}$")


def _doc():
    return json.loads(CENSUS.read_text(encoding="utf-8"))


def _funcs():
    return _doc()["functions"]


def test_schema():
    doc = _doc()
    assert doc["generated_by"] == "tools/function_census.py"
    assert doc["inputs"], "census must record its input hashes"
    funcs = doc["functions"]
    assert funcs
    for r in funcs:
        assert _HEX.match(r["start"]) and _HEX.match(r["end"]), r
        assert int(r["end"], 16) - int(r["start"], 16) == r["size"] > 0, r
        assert r["confidence"] in CONFIDENCES, r
        assert r["classification"] in CLASSIFICATIONS, r
        assert r["range_type"] in RANGE_TYPES, r
        assert r["space"] in ("resident", "overlay"), r
        assert (r["overlay"] is None) == (r["space"] == "resident"), r
        assert r["discovery"], f"function with no discovery signal: {r['start']}"
        for edge in r["callers"] + r["callees"]:
            assert _HEX.match(edge), r


def test_no_overlaps_within_space():
    by_space = defaultdict(list)
    for r in _funcs():
        by_space[(r["space"], r["overlay"])].append(
            (int(r["start"], 16), int(r["end"], 16)))
    for key, ranges in by_space.items():
        ranges.sort()
        for (s1, e1), (s2, e2) in zip(ranges, ranges[1:]):
            assert e1 <= s2, f"overlap in {key}: {s1:#x}..{e1:#x} vs {s2:#x}..{e2:#x}"


def test_boundaries():
    for r in _funcs():
        s, e = int(r["start"], 16), int(r["end"], 16)
        if r["space"] == "resident":
            assert TEXT_LO <= s < e <= TEXT_HI, f"resident fn out of text: {r['start']}"
        else:
            base = REGION_B if r["overlay"] in ("MEMORY",) else REGION_A
            assert s >= base, f"overlay fn below region base: {r['start']} ({r['overlay']})"
            assert e <= 0x80200000


def test_no_function_crosses_known_data_anchor():
    anchors = {int(a, 16) for a in _doc()["data_anchors"]}
    for r in _funcs():
        if r["space"] != "resident":
            continue
        s, e = int(r["start"], 16), int(r["end"], 16)
        for a in anchors:
            assert not (s < a < e), \
                f"code range {r['start']}..{r['end']} swallows data anchor {a:#x}"
            assert s != a, f"data anchor {a:#x} classified as a function start"


def test_verified_r2_lookup_tables_are_data():
    by_start = {r["start"]: r for r in _funcs() if r["space"] == "resident"}
    starts = (
        "0x80017db4", "0x8001a900", "0x80074970", "0x800749a8",
        "0x8007564c", "0x800769a8", "0x80078b54", "0x8007d5c0",
        "0x8007d8b0", "0x8007d8b4", "0x8007d9e0", "0x8007e7c4",
        "0x8007e7cc", "0x8007e7d4", "0x8007e7dc", "0x8007e810",
    )
    for start in starts:
        record = by_start[start]
        assert record["range_type"] == "data", record
        assert record["classification"] == "data", record
        assert "match" not in record, record


def test_delayed_prologues_and_dispatch_cases_are_not_function_starts():
    starts = {r["start"] for r in _funcs() if r["space"] == "resident"}
    false_starts = {
        "0x80013288", "0x800186f0", "0x80027010", "0x80039c38",
        "0x8003d7b8", "0x8003e124", "0x80042494", "0x80042a40",
        "0x80045b04", "0x800510f4", "0x800514a4", "0x80055654",
        "0x80062604", "0x80062b0c", "0x80062c04", "0x80065b54",
        "0x80067f28", "0x80071994", "0x80071eec", "0x80071f54",
        "0x800737c8", "0x80073898",
    }
    assert starts.isdisjoint(false_starts)


def test_libpad_and_counter_ranges_are_sdk_classified():
    resident = [r for r in _funcs() if r["space"] == "resident"]
    for record in resident:
        start = int(record["start"], 16)
        if 0x8006607C <= start < 0x800661E8 or 0x800718E0 <= start < 0x80074970:
            expected = "bios_thunk" if record["range_type"] == "thunk" else "sdk_psyq"
            assert record["classification"] == expected, record
    names = {r["name"] for r in resident}
    assert {"GetRCnt", "PadGetState", "PadInitDirect", "_padSioRW2"} <= names


def test_jal_anomalies_empty():
    doc = _doc()
    assert doc["jal_anomalies"] == {}, (
        "unexplained jal targets — every direct call must resolve to a census "
        f"start or the recorded cross-space entry surface: {doc['jal_anomalies']}")


def test_every_text_symbol_is_a_census_start():
    starts = {int(r["start"], 16): r for r in _funcs() if r["space"] == "resident"}
    missing, mismatched = [], []
    for ln in SYMBOLS.read_text().splitlines():
        mo = re.match(r"^([0-9A-Fa-f]{8})\s+(\S+)", ln)
        if not mo:
            continue
        addr, name = int(mo.group(1), 16), mo.group(2)
        if not (TEXT_LO <= addr < TEXT_HI):
            continue
        if "_OBJ_" in name or name.startswith("provisional_"):
            continue  # interior basic-block labels, not function starts
        rec = starts.get(addr)
        if rec is None:
            missing.append(f"{addr:#010x} {name}")
        elif rec["name"] != name:
            mismatched.append(f"{addr:#010x} census={rec['name']!r} sym={name!r}")
    assert not missing, f"symbols absent from census: {missing[:10]}"
    assert not mismatched, f"census/sym name drift: {mismatched[:10]}"


def test_overlay_entry_surface_recorded():
    doc = _doc()
    targets = doc["resident_overlay_entry_targets"]
    assert targets, "resident->overlay jal surface missing"
    # the canonical Region A universal entry must be part of the surface
    assert "0x800b39a4" in targets
    for t, rec in targets.items():
        assert _HEX.match(t)
        assert rec["n_sites"] >= 1 and rec["callers"]


def test_csv_matches_json():
    rows = CSV.read_text().splitlines()
    assert len(rows) - 1 == len(_funcs()), "functions.csv row count != census"
    assert rows[0].startswith("start,end,size,space,overlay,name,")


def test_match_provenance():
    """`match` field: only on attempted resident starts, value asm/c per source
    extension; and it must agree with config/segments.yml. Also assert all five
    DoD categories are representable in the census."""
    import yaml
    seg = yaml.safe_load((ROOT / "config" / "segments.yml").read_text())
    want = {}
    for a in seg.get("attempted") or []:
        va = a["start"] if isinstance(a["start"], int) else int(a["start"], 16)
        want[f"{va:#010x}"] = "c" if str(a["source"]).endswith(".c") else "asm"
    funcs = _funcs()
    got = {r["start"]: r["match"] for r in funcs if "match" in r}
    assert got == want, f"census match provenance {got} != segments {want}"
    for r in funcs:
        if "match" in r:
            assert r["space"] == "resident" and r["match"] in ("asm", "c")
    # five distinguishable categories (milestone DoD)
    assert any(r.get("match") == "asm" for r in funcs)            # asm match
    assert any(r.get("match") == "c" for r in funcs)              # C match
    assert any(r["classification"] == "sdk_psyq" for r in funcs)  # library symbol
    assert any(r["classification"] in ("game", "unknown")
               and "match" not in r for r in funcs)               # unknown game fn
    assert any("dynamic" in r["discovery"] for r in funcs)        # dyn-confirmed


@pytest.mark.local_media
def test_regeneration_is_identical():
    """Committed census == freshly regenerated census (byte-identical)."""
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (CENSUS, CSV, ROOT / "analysis" / "code_coverage.md")}
    proc = subprocess.run([sys.executable, "tools/function_census.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in (CENSUS, CSV, ROOT / "analysis" / "code_coverage.md")}
    assert before == after, (
        "census drift: an input changed (new symbols/psyq/ghidra/trace data?) — "
        "regenerate and commit analysis/ together with the input change")
