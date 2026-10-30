"""The extent audit must catch a NEW truncation and stay quiet about reviewed ones.

F01's census carried a hand-typed extent table whose ends were shorter than the
functions they named, so 7,063 instructions inside the extents it claimed to
cover were never read and every count it reported as a total was a lower bound.
Nothing in that tool could detect it. This suite pins the detector.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_extent_audit as audit  # noqa: E402

RETAINED = ROOT / "analysis/phase4_extent_audit.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RETAINED.read_bytes())


def test_retained_report_is_fresh(tmp_path):
    fresh = tmp_path / "out.json"
    subprocess.run([sys.executable, str(ROOT / "tools/phase4_extent_audit.py"),
                    "--json", str(fresh)], capture_output=True, text=True, cwd=ROOT)
    assert json.loads(fresh.read_bytes()) == json.loads(RETAINED.read_bytes())


def test_no_unreviewed_truncation(report):
    assert report["unacknowledged_declarations"] == 0, report["unacknowledged"]
    assert report["truncated_declarations"] == report["acknowledged_declarations"]


def test_the_sweep_actually_reached_the_repo(report):
    """A detector that scans nothing also reports nothing."""
    assert report["files_scanned"] > 500
    assert report["extent_declarations"] > 500
    assert report["pairs_rejected"]["unnamed"] > 0
    assert report["pairs_rejected"]["glued_into_one_token"] > 0


def test_new_truncation_is_caught_and_a_correct_range_is_not(tmp_path):
    """Positive and negative control in one file.

    Without this the suite proves only that the tool is silent, which is what a
    broken detector also looks like.
    """
    probe = tmp_path / "probe.py"
    probe.write_text(
        "SCAN_RANGE = (0x8004ABF4, 0x8004B000)\n"   # short of the real end
        "GOOD_RANGE = (0x8004ABF4, 0x8004B6DC)\n")  # exactly the real end
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_extent_audit.py"), str(tmp_path)],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 1, proc.stdout
    assert "0x8004b000" in proc.stdout.lower()
    assert "0x8004b6dc" not in proc.stdout.lower().split("real")[0]


def test_the_f01_repair_stays_repaired():
    """The table that caused all this must keep its index-derived SET and ENDS.

    Ends alone are not enough: a fresh verifier found the set was still a subset
    of the tool's own criterion after the ends were fixed. So this asserts the
    stronger property -- that every function the criterion admits is present.
    """
    source = (ROOT / "tools/phase4_f01_frontier_resolve.c").read_text()
    assert "GENERATED from" in source and "SET" in source
    index = json.loads((ROOT / "analysis/phase4_static_frontier_index.json").read_bytes())
    windows = ((0x800823A0, 0x800823A2), (0x80082470, 0x80082472))
    qualifying = set()
    for record in index["records"]:
        if not record.get("entry") or record.get("range_type") != "code":
            continue
        for access in record.get("memory_accesses") or []:
            addr = access.get("address")
            if addr is None:
                continue
            value, width = int(str(addr), 16), int(access.get("width") or 4)
            if any(value < hi and value + width > lo for lo, hi in windows):
                qualifying.add(int(str(record["entry"]), 16))
                break
    declared = {int(m, 16) for m in re.findall(r'\{\s*"[^"]+",\s*(0x[0-9a-fA-F]+),', source)}
    assert qualifying <= declared, (
        f"{len(qualifying - declared)} function(s) meet the criterion but are not "
        f"walked: {sorted(hex(a) for a in qualifying - declared)}")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_extent_audit.py"),
         "tools/phase4_f01_frontier_resolve.c"],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout
    assert " 0 truncated" in proc.stdout or "0 NEW" in proc.stdout


def test_data_extents_are_not_mistaken_for_functions(tmp_path):
    """`master_game_state` spans 0x800823A0..0x800823CC as DATA.

    A schema declaring a two-byte watched window there is not a truncated
    function, and reporting it as one taught the reader to ignore the tool.
    """
    probe = tmp_path / "window.yaml"
    probe.write_text("- {id: transition_request, start: 0x800823A0, end: 0x800823A2}\n")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_extent_audit.py"), str(tmp_path)],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout


def test_acknowledged_rows_all_carry_a_verdict_and_reason():
    doc = yaml.safe_load((ROOT / "config/phase4_extent_audit_acknowledged.yaml").read_text())
    assert doc["acknowledged"]
    for row in doc["acknowledged"]:
        assert row["verdict"] in doc["verdict_meanings"]
        assert row["reason"].strip()


def test_reviewed_verdicts_separate_notation_from_real_truncation(report):
    """The two classes must not be blurred: one is noise, one is coverage loss."""
    verdicts = report["review_verdicts"]
    assert verdicts.get("not_an_extent", 0) > 0
    assert verdicts.get("drift_pin_covers_less_than_the_function", 0) > 0
    # None may be a truncated CENSUS SCAN -- the F01 bug -- so the verdict set is
    # enumerated explicitly. A substring search for "census" was the previous
    # test and it broke the moment a legitimate verdict was named
    # `decomp_segment_not_a_census_extent`: a keyword is not a category.
    allowed = {"not_an_extent", "drift_pin_covers_less_than_the_function",
               "decomp_segment_not_a_census_extent"}
    assert set(verdicts) <= allowed, (
        f"unreviewed verdict class {set(verdicts) - allowed}; if a truncated "
        "census scan has appeared, that is the F01 bug recurring")


def test_out_of_tree_paths_do_not_crash(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_extent_audit.py"), str(tmp_path)],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr
