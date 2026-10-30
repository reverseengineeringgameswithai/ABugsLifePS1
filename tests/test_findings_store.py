"""Semantic integrity of the committed findings store (GAP-0002 / GAP-0008).

CI-safe: parses only the tracked YAML backup; no emulator, media, or saves.
Guards against an accidental ``findings.save`` overwrite silently dropping the
M7 headline evidence even if the byte-hash manifest is later re-baselined.
"""
from pathlib import Path

import check_findings_store as cfs  # tools/ is on sys.path via tests/conftest.py

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "src_re_geometry" / "re_findings_backup.yaml"


def _data():
    return cfs.load_findings(str(STORE))


def test_findings_yaml_parses():
    data = _data()
    assert isinstance(data, dict)
    assert isinstance(data.get("findings"), list) and data["findings"], "non-empty findings list"


def test_all_invariants_hold():
    # The single source of truth for the headline invariants; empty == OK.
    assert cfs.check_invariants(_data()) == []


def test_f13_is_sole_confirmed_visible_floor():
    findings = _data()["findings"]
    confirmed_visible = [
        f["id"]
        for f in findings
        if f.get("confidence") == "CONFIRMED" and "visible-floor" in (f.get("tags") or [])
    ]
    assert confirmed_visible == ["f13"], confirmed_visible


def test_f5_and_f10_are_not_confirmed_visible_floor_answers():
    by_id = {f["id"]: f for f in _data()["findings"]}
    for fid in ("f5", "f10"):
        assert fid in by_id, f"{fid} should remain in the store as a superseded record"
        assert by_id[fid]["confidence"] != "CONFIRMED", fid
        assert "visible-floor" not in (by_id[fid].get("tags") or []), fid


def test_f13_retains_m7_evidence_anchors():
    f13 = next(f for f in _data()["findings"] if f["id"] == "f13")
    text = cfs._finding_text(f13)
    for anchor in cfs.M7_ANCHORS:
        assert anchor in text, f"missing M7 evidence anchor: {anchor}"
