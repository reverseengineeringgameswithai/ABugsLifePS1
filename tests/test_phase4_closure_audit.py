#!/usr/bin/env python3
"""Guard: this session's domain-closure claims, re-checked against addressing forms.

F10's polish claimed a bit had "exactly one setter" and a live edge trace refuted it.
Since every closure claim this session came from a static scan, the question was
whether the scanner or the claim was at fault. It was neither the general scanner nor
the claims -- it was an AD HOC two-instruction pattern match used in one place.

This keeps that answer checkable, and keeps the two scanners' complementary blind
spots recorded: strict constant-tracking misses variable-index stores; a base
heuristic would mis-attribute unrelated accesses in the same page.
"""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools/phase4_closure_audit.c"


@pytest.fixture(scope="module")
def audit(tmp_path_factory):
    exe = tmp_path_factory.mktemp("audit") / "audit"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(exe), str(TOOL)], check=True, cwd=ROOT)
    return subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True)


def test_every_closure_survives_the_wider_scan(audit):
    assert audit.returncode == 0, audit.stdout[-3000:]
    assert "every closure claim survives the wider scan" in audit.stdout


def test_the_general_scanner_was_never_the_blind_spot(audit):
    """It finds 0x8004EB6C, the site the ad-hoc pattern missed -- so the counter
    closures built on it stand."""
    assert "it DOES find 0x8004EB6C" in audit.stdout
    assert "not the scanner the counter closures were built on" in audit.stdout


def test_gp_is_resolved_unconditionally():
    """$gp is a proven constant. Without special-casing it, one `lw gp,x(sp)`
    anywhere silently drops every later gp-relative access -- which made the audit's
    own first run report 1 store where the census correctly found 7."""
    src = TOOL.read_text()
    assert "PROVEN CONSTANT" in src
    assert "rs == 28" in src


def test_the_two_scanners_blind_spots_are_recorded():
    src = TOOL.read_text()
    assert "VARIABLE-INDEX store" in src
    assert "Neither scanner" in src
