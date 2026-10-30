"""Offline validation of the Phase-2 oracle artifacts.

Guards analysis/phase2_fixture_audit.json, analysis/phase2_stage_baseline.json,
analysis/phase2_row_coverage.json, and the generated stage-identity scenarios:
audit classification integrity, snapshot/mask consistency, full row coverage
(pristine trigger XOR documented blocker), and scenario/baseline agreement.
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

AUDIT = json.loads((ROOT / "analysis" / "phase2_fixture_audit.json").read_text())
BASELINE = json.loads((ROOT / "analysis" / "phase2_stage_baseline.json").read_text())
COVERAGE = json.loads((ROOT / "analysis" / "phase2_row_coverage.json").read_text())
SCEN_DIR = ROOT / "tools" / "scenarios" / "duckstation"

IDENTITY_ANCHORS = 16   # Training + 15 stages
BONUS_ANCHORS = 3


def test_audit_classification_integrity():
    for coll in ("saves", "movies"):
        for rel, e in AUDIT[coll].items():
            assert e.get("sha256") and len(e["sha256"]) == 64, rel
            assert e["media_class"] in ("pristine", "non_pristine", "pristine_serial",
                                        "unknown_serial", "unknown", "unreadable"), rel
            if e["media_class"] == "pristine":
                assert e["media_path"].endswith(("(v1.0).cue", "(v1.0).bin")), rel
    counts = {}
    for coll in ("saves", "movies"):
        for e in AUDIT[coll].values():
            counts[e["media_class"]] = counts.get(e["media_class"], 0) + 1
    assert counts == AUDIT["class_counts"]
    assert counts.get("pristine", 0) >= 100, "pristine save pool collapsed"


def test_baseline_anchor_coverage_and_no_errors():
    stages = BASELINE["stages"]
    roles = {}
    for lbl, st in stages.items():
        assert "error" not in st, f"{lbl}: {st.get('error')}"
        roles[st["role"]] = roles.get(st["role"], 0) + 1
    assert roles["identity"] == IDENTITY_ANCHORS
    assert roles["identity_bonus"] == BONUS_ANCHORS
    assert roles.get("lifecycle_completion", 0) >= 8
    assert roles.get("objective_progress", 0) >= 15


def test_baseline_snapshots_and_masks_consistent():
    for lbl, st in BASELINE["stages"].items():
        a, b = st["anchor"], st["anchor_plus_frames"]
        assert set(a) == set(b), lbl
        stable, volatile = set(st["stable_fields"]), set(st["volatile_fields"])
        assert stable.isdisjoint(volatile), lbl
        assert stable | volatile == set(a), lbl
        for k in stable:
            assert a[k] == b[k], f"{lbl}.{k} claimed stable but differs"
        for k in volatile:
            assert a[k] != b[k], f"{lbl}.{k} claimed volatile but equal"
        assert a["scene_id"] == b["scene_id"], f"{lbl}: scene changed within window"


def test_stage_scene_ids_unique():
    scenes = {}
    for lbl, st in BASELINE["stages"].items():
        if st["role"] == "identity":
            scenes[lbl] = st["anchor"]["scene_id"]
    assert len(set(scenes.values())) == len(scenes), scenes


def test_row_coverage_freshness():
    """The committed artifact must match a fresh regeneration (review: it went
    stale when new pristine fixtures landed without propagation)."""
    import subprocess, sys as _sys
    before = (ROOT / "analysis" / "phase2_row_coverage.json").read_bytes()
    proc = subprocess.run([_sys.executable, "tools/phase2_row_coverage.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    after = (ROOT / "analysis" / "phase2_row_coverage.json").read_bytes()
    assert before == after, "row coverage drifted — regenerate and commit together"


def test_row_coverage_partition():
    rows = yaml.safe_load((ROOT / "analysis" / "mechanics_baseline.yaml").read_text())["rows"]
    cov = COVERAGE["rows"]
    assert sorted(cov) == sorted(r["id"] for r in rows)
    counts = {"pristine_trigger": 0, "blocked": 0}
    for rid, c in cov.items():
        counts[c["status"]] += 1
        if c["status"] == "pristine_trigger":
            assert c["pristine_fixtures"], rid
        else:
            assert c.get("blocker", "").strip(), f"{rid}: blocked without documented blocker"
    assert counts == COVERAGE["counts"]


def test_generated_scenarios_match_baseline():
    import ps1_scenario as ps
    suite = json.loads((SCEN_DIR / "stage_identity_suite.json").read_text())
    assert len(suite["scenarios"]) == IDENTITY_ANCHORS + BONUS_ANCHORS
    for rel in suite["scenarios"]:
        doc = yaml.safe_load((ROOT / rel).read_text())
        ps.validate_scenario(doc)
        label = doc["id"].replace("stage_identity_", "")
        st = BASELINE["stages"][label]
        assert doc["anchor"]["path"] == st["save"]
        assert doc["anchor"]["sha256"] == st["save_sha256"]
        stable = set(st["stable_fields"])
        for assertion in doc["phases"][0]["assertions"]:
            field = assertion["id"].replace(f"{label}_", "")
            assert field in stable, f"{doc['id']}: asserts volatile field {field}"
            assert assertion["expected"] == st["anchor"][field], f"{doc['id']}.{field}"
