"""Validate the advisory headline-fixture manifest (GAP-0002 / GAP-0040).

CI-safe: parses tools/fixtures.sha256 (committed text). Hash verification of a
fixture is ADVISORY -- a fixture absent on this host (clean clone) is skipped,
never failed; a fixture present with a different hash is fixture drift and fails.
No copyrighted media is read unless it already exists on the host.
"""
import hashlib
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools" / "fixtures.sha256"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Every GAP-0040 headline experiment must have a pinned fixture role here.
# (Numbered-slot savestate roles spawn-floor-level01 / level02-scene3-default /
# fixture-scus2 were RETIRED 2026-07-08 -- slots get overwritten by normal play;
# replay tools take an explicit --save now.)
REQUIRED_ROLES = {
    "pristine-disc-cue",
    "from-boot-movie-level01",   # G29 arms (--movie)
}


def _rows():
    rows = []
    for ln in MANIFEST.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split(None, 2)  # path may contain spaces (disc filename does)
        assert len(parts) == 3, f"malformed manifest line: {ln!r}"
        rows.append(tuple(parts))  # (sha256, role, path)
    return rows


def _resolve(path: str) -> Path:
    saves = os.environ.get(
        "ABL_SAVESTATES", os.path.expanduser("~/.local/share/duckstation/savestates")
    )
    path = path.replace("$ABL_SAVESTATES", saves)
    p = Path(os.path.expanduser(path))
    return p if p.is_absolute() else (ROOT / p)


def test_manifest_format_valid():
    rows = _rows()
    assert rows, "fixtures manifest has no entries"
    roles = [r for _, r, _ in rows]
    for digest, role, path in rows:
        assert _HEX64.match(digest), f"bad sha256 for {role}: {digest!r}"
        assert role and "/" not in role and " " not in role, f"bad role token: {role!r}"
        assert path, f"empty path for {role}"
    assert len(roles) == len(set(roles)), f"duplicate roles: {roles}"


def test_required_headline_roles_present():
    roles = {r for _, r, _ in _rows()}
    missing = REQUIRED_ROLES - roles
    assert not missing, f"missing required fixture roles: {sorted(missing)}"


def test_present_fixtures_match_pinned_hash():
    # Advisory: skip absent fixtures (clean clone); fail drift on present ones.
    checked = 0
    for digest, role, path in _rows():
        p = _resolve(path)
        if not p.exists():
            continue
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        assert h.hexdigest() == digest, f"fixture drift: {role} ({p})"
        checked += 1
    # Informational only; a clean clone legitimately checks zero.
    print(f"verified {checked} present fixture(s) against pinned hashes")
