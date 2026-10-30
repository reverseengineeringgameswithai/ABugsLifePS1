"""Gate for B06's item-2 re-read against the canonical bar.

This artifact moves another row's DoD item from ADVANCED toward met, so the tests
that matter are the ones that stop it flattering B06:

  * the pass must stay conditional -- the ledger's own
    `strict_full_program_proof` is false, and the declared valid-retail bound
    must be emitted as a residual rather than quietly dropped;
  * the row must not be reported solved (4, 5 and 9 are genuinely open);
  * the enumeration must actually be complete in the ledger, not asserted here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_b06_promotion_residuals.py"
ART = ROOT / "analysis/phase4_b06_promotion_residuals.json"
LEDGER = ROOT / "analysis/phase4_b06_closure_20260804.json"


@pytest.fixture(scope="module")
def a():
    r = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    return json.loads(ART.read_text())


def test_the_enumeration_is_complete_in_the_ledger_itself(a):
    """Read from B06's closure artifact, not from this tool's summary."""
    d = json.loads(LEDGER.read_text())
    m = d["closure_metrics"]
    assert m["unexplained"] == 0
    assert m["classified"] == m["residual_total"] == 251
    ledger = d["candidate_ledger"]
    assert len(ledger) == 251
    assert {e["disposition"] for e in ledger} == {"disjoint"}
    assert all(str(e.get("proof") or "").strip() for e in ledger)


def test_it_passes_the_linter_s_two_rules(a):
    assert a["linter_result"]["rejections"] == []
    assert a["linter_result"]["passes_the_residual_rules"] is True
    assert a["linter_result"]["residual_entries"] >= 13


def test_every_residual_names_its_domain_and_its_proof(a):
    for r in a["bounded_residuals"]:
        assert r["intersects_dimension"] is False
        for k in ("boundary", "evidence", "next_experiment"):
            assert len(str(r[k]).strip()) > 40, f"{k} too thin on {r['boundary'][:40]}"


def test_the_declared_bound_is_itself_a_residual(a):
    """The one thing keeping this from being unconditional must be visible."""
    bounds = [r for r in a["bounded_residuals"] if r["boundary"].startswith("THE DECLARED BOUND")]
    assert len(bounds) == 1
    assert "strict_full_program_proof" in bounds[0]["boundary"]
    assert "False" in bounds[0]["boundary"] or "false" in bounds[0]["boundary"]


def test_the_pass_stays_conditional_and_the_row_is_not_called_solved(a):
    assert "WITHIN THE DECLARED BOUND" in a["verdict"]
    assert "NOT an unconditional pass" in a["verdict"]
    rec = a["recommendation"]
    assert "MET-IN-SCOPE" in rec
    assert "not solved" in rec
    assert "6 of 9" in rec


def test_it_records_the_bar_it_was_judged_against(a):
    bar = a["the_bar"]
    assert "ENUMERATED" in bar and "EXPLICITLY BOUNDED" in bar
    assert "never changes a Phase-4 dimension by itself" in bar
