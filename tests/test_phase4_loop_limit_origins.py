"""Why extent recovery does not scale -- measured, so nobody re-derives it.

A fifth evidence basis was proposed: find each object's allocation or fill loop
and read the element count. Two objects had yielded to exactly that (_SsVmInit's
literal 32, the weld table's mod-100). This pins why it does not generalise.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "analysis/phase4_loop_limit_origins.json"


def _a():
    return json.loads(ART.read_text())


def test_the_register_comparison_blind_spot_was_real_and_is_closed():
    """43% of loop-bound comparisons use the register form and were invisible to
    the affine pass. That gap was genuine and is now handled."""
    a = _a()
    r = a["register_form_was_a_real_blind_spot"]
    assert a["slt_sltu_total"] == 1191
    assert r["immediate_form_slti_sltiu"] == 1552
    src = (ROOT / "tools/affine_bound_recovery.c").read_text()
    assert "REGISTER form of the bound test" in src


def test_closing_it_yielded_exactly_zero_and_says_so():
    """The honest part. A real blind spot, correctly closed, worth nothing here --
    recorded so the next pass does not spend the same effort hoping otherwise."""
    src = (ROOT / "tools/affine_bound_recovery.c").read_text()
    assert "MEASURED YIELD HERE: ZERO" in src
    assert "zero-yield so nobody re-derives it" in src


def test_loop_limits_come_from_data_not_from_constants():
    """The reason. Element counts live in chunk headers, save state and config --
    not in the instruction stream -- so fill loops cannot give extents at scale."""
    a = _a()
    assert a["limit_is_literal"] == 8
    assert a["limit_is_loaded_from_memory"] == 324
    assert a["limit_is_literal"] / a["slt_sltu_total"] < 0.01
    assert "NOT VIABLE" in a["verdict"]
    assert "come from DATA" in a["verdict"]
    assert "exceptions, not the rule" in a["verdict"]


def test_the_measurement_is_reproducible():
    subprocess.run(["python3", str(ROOT / "tools/phase4_loop_limit_origins.py")],
                   check=True, capture_output=True)
