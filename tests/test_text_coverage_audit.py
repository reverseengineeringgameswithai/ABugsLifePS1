"""Gate for tools/text_coverage_audit.c.

The audit exists because a false negative got past every static pass: an E16
campaign movie caught 0x80010BF4 reading a table window, and that address is in
no function in analysis/functions_resident.txt. These tests pin the properties
that make the audit worth trusting -- above all that it distinguishes DROPPED
CODE from padding, since "9.9% uncovered" and "46 KB of live code unscanned" are
very different claims and only the second one invalidates a residual figure.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools/text_coverage_audit.c"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
FUNCS = ROOT / "analysis/functions_resident.txt"

# The access the campaign found, and the loop back-edge that exposed the hole.
FOUND_ACCESS = 0x80010BF4
LOOP_HEAD = 0x800102D4


@pytest.fixture(scope="module")
def tool(tmp_path_factory):
    out = tmp_path_factory.mktemp("tca") / "tca"
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", str(out), str(SRC)],
                   check=True)
    return out


@pytest.fixture(scope="module")
def result(tool, tmp_path_factory):
    j = tmp_path_factory.mktemp("tcaj") / "r.json"
    r = subprocess.run([str(tool), str(EXE), str(FUNCS), "--json", str(j)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(j.read_text())


def test_builds_werror_clean():
    """-Werror is the project's standing rule for static ASM probes."""
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-o", str(Path(d) / "x"), str(SRC)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_refuses_a_non_pristine_image(tool):
    """Self-verification must fail loudly, not emit plausible numbers.

    The pins are instructions, so corrupting the pinned word is exactly the
    failure mode that matters: an image whose code has shifted underneath a
    hard-coded address."""
    with tempfile.TemporaryDirectory() as d:
        bad = Path(d) / "bad.exe"
        img = bytearray(EXE.read_bytes())
        off = 0x800 + (0x80010C88 - 0x80010000)
        img[off:off + 4] = b"\x00\x00\x00\x00"
        bad.write_bytes(bytes(img))
        r = subprocess.run([str(tool), str(bad), str(FUNCS)],
                           capture_output=True, text=True)
        assert r.returncode != 0
        assert "pinned" in r.stderr.lower()


def test_coverage_is_the_number_that_was_being_assumed(result):
    """998 functions over ~90% of the text -- the figure no pass had measured."""
    assert result["listed_functions"] == 998
    assert 89.0 < result["covered_percent"] < 91.0
    assert result["text_bytes"] == 0x80082800 - 0x80010000
    assert result["covered_bytes"] + result["uncovered_bytes"] == result["text_bytes"]


def test_the_gap_is_overwhelmingly_code_not_padding(result):
    """The distinction that makes this a finding rather than a footnote."""
    assert result["dropped_code_bytes"] > 40000
    assert result["dropped_code_bytes"] > 100 * result["unreferenced_bytes"]
    assert result["dropped_code_gaps"] < result["gap_count"]


def test_the_found_access_lies_in_a_dropped_code_gap(result):
    """The campaign's find must be explained by the audit, not merely coexist."""
    hit = [g for g in result["gaps"]
           if int(g["start"], 16) <= FOUND_ACCESS < int(g["start"], 16) + g["bytes"]]
    assert len(hit) == 1, "the found access must fall in exactly one gap"
    assert hit[0]["is_code"], "and that gap must be reached code"
    assert int(hit[0]["start"], 16) == LOOP_HEAD


def test_gaps_are_disjoint_and_ordered(result):
    gaps = result["gaps"]
    prev_end = 0
    for g in gaps:
        s = int(g["start"], 16)
        assert s >= prev_end, "gaps must not overlap"
        prev_end = s + g["bytes"]
    assert sum(g["bytes"] for g in gaps) == result["uncovered_bytes"]


def test_code_classification_carries_its_evidence(result):
    """A gap called CODE must name a real transfer into it -- no bare assertions."""
    for g in result["gaps"]:
        if g["is_code"]:
            assert g["direct_entries"] > 0
            dst = int(g["sample_dst"], 16)
            assert int(g["start"], 16) <= dst < int(g["start"], 16) + g["bytes"]
        else:
            assert g["direct_entries"] == 0
