"""Soundness gate for region_provenance.c's TIER 3 (EXCLUDED_OUT_OF_BOUND).

Tier 3 excludes an access by reading a bounds check out of the disassembly and
proving the index needed to reach the target is beyond it. Its own header
discloses the assumption that makes it the weakest tier: that the detected
comparison "genuinely gates the index at the region's formation point, not just
'a comparison against this register happened somewhere'".

That assumption used to fail, and these gates keep it failed-and-fixed rather
than trusting prose. The counterexample is 0x8003BF48 in the LEVEL.RAW loader,
which the tool excluded while runtime evidence shows it firing 36 times.
"""
import json
import subprocess

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools/region_provenance.c"
CEX = ROOT / "tools/phase4_e16_bound_hint_counterexample.c"
def _pristine_exe() -> Path:
    """The pristine resident executable, wherever this checkout keeps it.

    `ROOT/"SCUS_942.88"` is a convenience copy in the operator's working tree and
    is `.gitignore`d, so hardcoding it made this test ERROR on a clean checkout --
    which is exactly what an independent verifier has. The soundness gate on the
    analyser's weakest tier therefore did not execute for the one reader whose
    execution mattered most. `REBUILD/files/` is the canonical location.
    """
    for candidate in (ROOT / "REBUILD/files/SCUS_942.88", ROOT / "REBUILD" / "files" / "SCUS_942.88"):
        if candidate.is_file():
            return candidate
    pytest.skip("pristine SCUS_942.88 not present in this checkout")


EXE = None  # resolved per-test so collection never depends on an untracked file


def test_counterexample_tool_compiles_and_self_verifies():
    """The counterexample is proven from the pristine bytes by a SEPARATE
    implementation, so it is not the analysis agreeing with itself."""
    binp = "/tmp/_e16bh_gate"
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", binp, str(CEX)],
                   check=True)
    r = subprocess.run([binp, str(_pristine_exe())], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    out = json.loads(r.stdout)
    assert all(c["ok"] for c in out["checks"])
    assert out["true_index_range"] == [48, 87]
    assert out["reported_idx_bound"] == 32          # what the unfixed tool claimed
    assert "UNSOUND" in out["verdict"]


def test_the_fix_is_present_and_explained():
    """Both halves of the fix must stay: bounds apply per-EDGE, and a bound is
    dropped when the delay slot rewrites the register it names."""
    src = SRC.read_text()
    assert "SOUNDNESS FIX 2026-08-04" in src
    assert "cmp_src" in src and "edge_true_is_fallthrough" in src
    # captured at the branch, before the delay slot runs
    assert "before its delay slot runs" in src
    # and invalidated when the delay slot clobbers the compared register
    assert "delay slot that rewrites the compared" in src


def test_b06_frontier_stays_reconciled_through_every_analyser_change():
    """The soundness fix itself did NOT move B06 -- its artifact recorded
    excluded_out_of_bound == 0 in scope, so its then-251 residual never depended
    on the unsound tier. The mask bound added later DID move it, soundly, to 192.

    Pinning a moving number is not the point; the invariant is. Whatever the
    analyser learns, the baseline must hold, no known-real access may ever be
    excluded, and the reconciliation must stay exact."""
    a = json.loads((ROOT / "analysis/phase4_region_provenance.json").read_text())
    res, v = a["result"], a["validation"]
    assert res["baseline_residual"] == 416          # the fixed denominator
    assert res["excluded_alignment"] == 159         # untouched by both changes
    assert res["excluded_negative_index"] == 6      # untouched by both changes
    assert res["still_open_after_region_provenance"] == 192
    assert v["hit_set_matches_python"] is True
    assert v["c_exclusions_colliding_with_python_hits (MUST be empty)"] == []
    assert v["reconciles_exactly"] is True


# ---- E16 frontier: the item-2 attempt and its honest negative ----

FRONTIER = ROOT / "analysis/phase4_e16_frontier.json"


def _fr():
    return json.loads(FRONTIER.read_text())


def test_escape_test_is_no_longer_structurally_blind_to_regions():
    """The escape argument is the whole lever for item 2 here. Before the fix the
    analyser inspected K_CONST only, so for a target whose pointers are always
    K_REGION it could never report an escape -- a guaranteed, meaningless zero."""
    src = SRC.read_text()
    assert "structurally BLIND" in src
    assert "g_region_undecided" in src
    # and the undecidable case must be counted, not silently resolved either way
    assert "COUNTED" in src and "vacuous" in src


def test_item_2_is_reported_as_NOT_met_with_the_reason_recorded():
    """A negative result is the deliverable here; it must not be softened."""
    v = _fr()["verdict"]
    assert v["item_2_met"] is False
    assert _fr()["the_escape_argument"]["established"] is False
    assert "neither is\n" not in v["wall"]  # sanity: single-line field
    assert "row-specific" in v["wall"] and "B06" in v["wall"]


def test_the_zeroes_are_qualified_not_presented_as_closure():
    """0 escaping stores and 0 arg-passing sites look like the argument holding.
    They range over DECIDABLE values only, and the artifact has to say so."""
    e = _fr()["the_escape_argument"]
    assert "DECIDABLE values only" in e["why_that_is_NOT_enough"]
    for t in _fr()["per_table"].values():
        assert t["full_width_escaping_stores"] == 0
        assert t["arg_passing_call_sites"] == 0
        assert t["undecided_unbounded_regions"] > 0      # which is why it is not closure


def test_scope_is_the_tables_only_not_the_whole_row():
    """Item 2 is a per-subsystem bar. Closing three tables would not close E16."""
    s = _fr()["scope"]
    assert "ONLY" in s["covered"]
    for missing in ("overlay region A", "0x8007EFE8", "high heap"):
        assert missing in s["NOT_covered"]
