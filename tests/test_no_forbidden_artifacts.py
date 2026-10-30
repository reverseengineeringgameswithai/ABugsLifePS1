"""No copyrighted / local-capture artifact is git-tracked (GAP-0002, Preservation Policy).

CI-safe: shells out to ``git ls-files`` only (no media is read). Enforces the
constraint that discs, BIOS, save states, memory cards, screenshots, movies,
RAM dumps, and backups stay out of version control -- their identity is
hash-pinned in tools/fixtures.sha256 instead.
"""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Suffixes that must never be tracked.
FORBIDDEN_SUFFIXES = (
    ".sav", ".mcr", ".state", ".ram",   # saves / memcards / dumps
    ".png", ".bak",                       # screenshots / backups
    ".movie.json", ".loadlock",           # input movies / guard sidecar
    ".cue", ".iso", ".chd", ".img",       # disc images
    ".bin",                               # disc / EXE blobs (oracles allowlisted below)
)

# Intentionally force-added, tiny, non-copyrighted codec oracles (GAP-0022/0024).
ALLOWLIST = {
    "tools/raw_chunk0_compressed.bin",
    "tools/raw_chunk0_decompressed.bin",
}


def _tracked():
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover
        pytest.skip("git not available")
    return [ln for ln in out.splitlines() if ln]


def test_no_forbidden_artifact_tracked():
    offenders = [
        p
        for p in _tracked()
        if p.lower().endswith(FORBIDDEN_SUFFIXES) and p not in ALLOWLIST
    ]
    assert not offenders, "forbidden artifacts tracked: " + ", ".join(offenders)


def test_allowlisted_oracles_are_present():
    # Guard the allowlist itself: if an oracle is renamed/removed, revisit the list.
    tracked = set(_tracked())
    for p in ALLOWLIST:
        assert p in tracked, f"allowlisted oracle no longer tracked: {p}"
