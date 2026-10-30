"""Gate for B09's direct-frontier enumeration.

The load-bearing claim is that two independent methods agree on the writer count,
so the test that matters is the one that would notice if they stopped agreeing.
"""
from __future__ import annotations

import json, struct, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_b09_frontier.py"
ART = ROOT / "analysis/phase4_b09_frontier.json"


@pytest.fixture(scope="module")
def a():
    r = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-600:]
    return json.loads(ART.read_text())


def test_two_methods_agree_on_the_writer_count(a):
    """Canon derived 26 from ori/andi immediates; this derives it from dataflow.
    If these diverge, one of them is wrong and the row must not proceed."""
    assert a["writer_count"] == a["canon_writer_count"] == 26


def test_readers_were_enumerated_not_just_writers(a):
    assert a["reader_count"] > 0
    assert a["direct_sites"] == a["writer_count"] + a["reader_count"]


def test_the_two_suspects_are_wholesale_overwrites(a):
    """The distinction between 'may clear bit 0x20' and 'does clear it'."""
    for pc in ("0x8004867C", "0x800486BC"):
        s = a["suspects"][pc]
        assert s["role"] == "writer"
        assert s["wholesale"] is True, f"{pc} is no longer a wholesale overwrite"


def test_the_suspect_masks_are_read_from_the_image(a):
    """Re-decode independently -- the claim is about specific instructions."""
    img = (ROOT / "REBUILD" / "files" / "SCUS_942.88").read_bytes()
    def w(pc): return struct.unpack_from("<I", img, 0x800 + pc - 0x80010000)[0]
    assert w(0x8004867C) == 0xA6220090        # sh $v0, 0x90($s1)
    assert w(0x80048678) == 0x24020001        # addiu $v0, $zero, 1
    assert w(0x800486BC) == 0xA6200090        # sh $zero, 0x90($s1)


def test_the_residual_is_not_claimed_closed(a):
    """B09 has had no per-site classification pass. Item 2 is advanced, not met."""
    r = a["residual"]
    assert r["unresolved"] > 0
    assert "NOT claimed here" in r["note"]


def test_it_records_why_materialisation_was_the_wrong_tool(a):
    """The scope limit on the technique that closed E16 -- a record FIELD is
    reached by displacement from the record base, so a field-address scan misses
    the real writers."""
    assert "FIELD of the player record" in a["target_is"]
    assert "wrong instrument" in a["target_is"]
