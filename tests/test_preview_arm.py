#!/usr/bin/env python3
"""Guards for the dry-run arm preview.

Both of this session's silent runtime failures were statically detectable before
arming anything. These guards hold the tool to catching exactly those two, so it
cannot regress into a check that passes everything.
"""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools/preview_arm.c"


@pytest.fixture(scope="module")
def exe(tmp_path_factory):
    b = tmp_path_factory.mktemp("preview") / "preview"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(b), str(TOOL)], check=True, cwd=ROOT)
    return b


def run(exe, *args):
    return subprocess.run([str(exe), *args], cwd=ROOT, capture_output=True, text=True)


def test_shared_window_breakpoint_is_refused(exe):
    """0x800B4244 is the F10 mask store, but 14 images hold code there. Arming it
    ungated captured another level's execution and 'refuted' a correct claim."""
    r = run(exe, "--breakpoint", "0x800B4244")
    assert r.returncode != 0, "an ambiguous breakpoint must be a hard error"
    assert "AMBIGUOUS" in r.stdout
    assert "DO NOT ARM WITHOUT A SCENE GATE" in r.stdout


def test_resident_breakpoint_is_allowed(exe):
    """The check must not simply refuse everything."""
    r = run(exe, "--breakpoint", "0x8004B3A8")      # Bonus-1 increment, resident
    assert r.returncode == 0, r.stdout[-800:]
    assert "SAFE" in r.stdout


def test_prologue_signature_is_refused(exe):
    """Sibling overlays are built from the same source and open identically; the
    prologue matched 16 images and located the wrong one, 0x38 off."""
    r = run(exe, "--signature", "REBUILD/files/LEVEL06/LEVEL1.BIN:4:32")
    assert r.returncode != 0
    assert "NOT UNIQUE" in r.stdout


def test_data_tail_signature_is_accepted(exe):
    r = run(exe, "--signature", "REBUILD/files/LEVEL06/LEVEL1.BIN:1564:256")
    assert r.returncode == 0, r.stdout[-800:]
    assert "UNIQUE" in r.stdout


def test_overlay_local_watch_is_flagged_as_per_scope(exe):
    """A closure claim over an overlay-local address cannot be phrased globally."""
    r = run(exe, "--watch", "0x800B5774")
    assert "OVERLAY-LOCAL" in r.stdout
    assert "CANNOT be phrased" in r.stdout


def test_preview_states_what_it_cannot_see(exe):
    """A preview that hid its own blind spots would be the false-confidence problem
    it exists to prevent."""
    r = run(exe, "--watch", "0x8008223C")
    assert "NOT VISIBLE TO THIS PREVIEW" in r.stdout
    assert "runtime-computed base" in r.stdout
    assert "is 'none of the forms I can resolve', not 'none'" in r.stdout
