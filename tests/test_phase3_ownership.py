"""Phase-3 WP1 guard: the ownership-frontier graph is DERIVED and FRESH.

Phase-2 lesson encoded: the artifact enumerates every registry row (omission
impossible), its gaps are computed (a narrative-only mechanic cannot lose its
gap without gaining an address binding), and the committed JSON must match a
regeneration byte-for-byte modulo the date stamp (no hand edits)."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "analysis" / "phase3_ownership_graph.json"


def _load():
    return json.loads(GRAPH.read_text())


def test_graph_is_fresh_regeneration():
    before = _load()
    proc = subprocess.run([sys.executable, "tools/phase3_ownership_graph.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    after = _load()
    before.pop("generated"), after.pop("generated")
    assert before == after, "committed graph is stale — regenerate and commit"


def test_graph_enumerates_every_registry_row():
    doc = _load()
    reg = yaml.safe_load((ROOT / "analysis" / "mechanics_baseline.yaml").read_text())
    assert sorted(doc["rows"]) == sorted(r["id"] for r in reg["rows"])


def test_gaps_are_computed_not_declared():
    doc = _load()
    reg = {r["id"]: r for r in yaml.safe_load(
        (ROOT / "analysis" / "mechanics_baseline.yaml").read_text())["rows"]}
    for rid, row in doc["rows"].items():
        cited = bool(row["functions"] or row["state"])
        status = reg[rid]["status"]
        # a DISPROVEN row backed by real evidence is a bounded frontier, not a gap;
        # a disproven row WITHOUT evidence still gets a gap (checked below).
        bounded_disproof = status == "disproven" and row.get("disproof_evidence")
        if not cited and status != "not_applicable" and not bounded_disproof:
            assert row["gaps"], rid                # must carry SOME computed gap
        for st in row["state"]:
            if not st["semantic_ids"] and not st["canon"]:
                assert any(st["address"] in g for g in row["gaps"]), (rid, st)
    # totals must reconcile with the row data
    assert doc["totals"]["mechanics"] == len(doc["rows"])
    assert doc["totals"]["state_owned"] == sum(
        1 for r in doc["rows"].values() for s in r["state"] if s["semantic_ids"])


def test_disproven_is_bounded_only_with_real_committed_evidence():
    """The operator's rule, as a CHECKED predicate (not a blanket waiver): a
    `disproven` mechanic is a bounded frontier iff it cites evidence artifacts that
    EXIST. A07 is intentionally not in this category: it is an external lead with a
    mapped frontier. Any future disproven row still needs real evidence."""
    doc = _load()
    reg = {r["id"]: r for r in yaml.safe_load(
        (ROOT / "analysis" / "mechanics_baseline.yaml").read_text())["rows"]}
    disproven = [rid for rid, r in reg.items() if r["status"] == "disproven"]
    for rid in disproven:
        row = doc["rows"][rid]
        ev = row.get("disproof_evidence") or []
        if ev:
            for path in ev:                        # every cited artifact must exist
                assert (ROOT / path).exists(), (rid, path)
            assert not any("unbacked disproof" in g for g in row["gaps"])
        else:
            assert any("unbacked disproof" in g for g in row["gaps"]), rid


def test_a07_is_an_external_lead_with_a_bounded_semantic_frontier():
    """The runtime battery bounds the search but cannot exclude a kick-shaped branch
    inside a named function. A07 therefore stays open as an external lead while its
    known player-function/state frontier remains fully mapped for Phase 3."""
    doc = _load()
    row = doc["rows"]["A07_spin"]
    assert row["registry_status"] == "external_lead"
    assert row["functions"] and row["state"]
    assert not row["gaps"]


def test_semantic_registry_backs_phase2_proven_state():
    """The WP2 expansion: every state address the Phase-2 gate proved must be
    owned in config/semantic_state.yaml."""
    sem = yaml.safe_load((ROOT / "config" / "semantic_state.yaml").read_text())
    addrs = {e.get("address") for e in sem["entries"]}
    for a in (0x800A6594,   # true health
              0x800A6580,   # state word
              0x800A6582,   # grounded
              0x800A657A,   # kick timer
              0x800A6596,   # in-flight berries
              0x80082488, 0x80082380,   # pad held/prev
              0x800B0D18,   # contact pool
              0x80090BF0, 0x800822B8,   # plant slots + cursor
              0x80090748,   # enemy live table
              0x8009FE04,   # chunk-31 actor records
              0x80095358):  # camera struct
        assert a in addrs, f"Phase-2-proven state 0x{a:08X} missing from registry"
