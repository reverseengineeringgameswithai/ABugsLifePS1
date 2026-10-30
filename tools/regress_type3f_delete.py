#!/usr/bin/env python3
"""Regression checks for the type-0x3f DELETE path (punchlist CC5).

Covers tools/delete_type3f_entries.py, dat_reloc.build_reloc_delete, and the
apply_level_placements `delete` op. Writes only to a temp dir; never mutates
workspace DAT/BIN/CUE and never builds an ISO.
"""

from __future__ import annotations

import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "delete_type3f_entries.py"
APPLY = ROOT / "tools" / "apply_level_placements.py"
INSERT = ROOT / "tools" / "insert_type3f_entries.py"
DEFAULT_DAT = ROOT / "DAT" / "LEVEL01_LEVEL.DAT"


def run(cmd: list[str], expect: int = 0) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run([str(c) for c in cmd], cwd=ROOT, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(f"command exited {proc.returncode}, expected {expect}: {' '.join(map(str, cmd))}")
    return proc


def count(path: Path, rec_off: int = 4) -> int:
    return struct.unpack_from("<H", path.read_bytes(), rec_off)[0]


def reparse_ok(path: Path) -> int:
    """Re-run the relocation scanner over a DAT; return its site count (raises on parse error)."""
    sys.path.insert(0, str(ROOT / "tools"))
    import dat_reloc
    sites, _ = dat_reloc.DAT(path.read_bytes()).scan_sites()
    return len(sites)


def engine_invariants(dat: Path) -> None:
    """Direct dat_reloc invariants: round-trip + size/count + survivor identity."""
    sys.path.insert(0, str(ROOT / "tools"))
    import dat_reloc
    d = dat.read_bytes()
    rec_off = 4
    dat_reloc.T3F_HDR = rec_off
    dat_reloc.INSERT_OFF = rec_off + 4 + count(dat) * 0x10

    # round-trip: delete(append(X)) == X, byte-exact
    ne = bytes.fromhex("40130000ceffffffb9f1ffff14000000")
    appended, *_ = dat_reloc.build_reloc_insert(d, ne)
    dat_reloc.T3F_HDR = rec_off
    back, *_ = dat_reloc.build_reloc_delete(appended, rec_off + 4 + count(dat) * 0x10)
    if back != d:
        raise SystemExit("regression failed: delete(append(X)) != X (not byte-exact)")

    # all baked offsets bumped, site count preserved, file re-parses
    del0, report, before_sites, _ = dat_reloc.build_reloc_delete(d, rec_off + 4)
    after_sites, _ = dat_reloc.DAT(del0).scan_sites()
    if not (len(before_sites) == len(report) == len(after_sites)):
        raise SystemExit("regression failed: delete changed relocation-site count")
    if sum(1 for r in report if r["bumped"]) != len(report):
        raise SystemExit("regression failed: not every baked offset was bumped on delete")
    if struct.unpack_from("<H", del0, rec_off)[0] != count(dat) - 1:
        raise SystemExit("regression failed: count did not drop by 1")

    # middle delete shifts subsequent entries up correctly
    x2 = struct.unpack_from("<i", d, rec_off + 4 + 2 * 0x10)[0]
    del1, *_ = dat_reloc.build_reloc_delete(d, rec_off + 4 + 1 * 0x10)
    if struct.unpack_from("<i", del1, rec_off + 4 + 1 * 0x10)[0] != x2:
        raise SystemExit("regression failed: middle delete did not shift survivors up")
    print("engine invariants passed (round-trip, site-count, count, survivor shift)")


def main() -> int:
    dat = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DAT
    if not dat.exists():
        raise SystemExit(f"input DAT not found: {dat}")
    base_count = count(dat)
    base_size = dat.stat().st_size

    engine_invariants(dat)

    with tempfile.TemporaryDirectory(prefix="type3f_delete_regress_") as tmp:
        t = Path(tmp)
        run([sys.executable, "-m", "py_compile", str(TOOL)])

        # CLI guards: no index, out==in, FLIK/telescope without override all refuse.
        run([sys.executable, str(TOOL), str(dat)], expect=1)               # refuses: at least one index
        run([sys.executable, str(TOOL), str(dat), "--delete-index", "50"], expect=1)   # FLIK letter
        run([sys.executable, str(TOOL), str(dat), "--delete-index", "67"], expect=1)   # telescope 0x30

        # single grain delete (kind 0x14) writes a file of size-0x10, count-1, re-parses.
        single = t / "single.DAT"
        run([sys.executable, str(TOOL), str(dat), "--delete-index", "0",
             "--write", "--out", str(single), "--report", str(t / "single.md")])
        if single.stat().st_size != base_size - 0x10 or count(single) != base_count - 1:
            raise SystemExit("regression failed: single delete size/count wrong")
        if reparse_ok(single) != 1248:
            raise SystemExit("regression failed: single delete did not re-parse to 1248 sites")
        if "final scan" not in (t / "single.md").read_text():
            raise SystemExit("regression failed: report missing verification section")

        # multi-delete (3 grains) high-index-first; size-0x30, count-3.
        multi = t / "multi.DAT"
        run([sys.executable, str(TOOL), str(dat), "--delete-index", "0",
             "--delete-index", "10", "--delete-index", "49",
             "--write", "--out", str(multi)])
        if multi.stat().st_size != base_size - 0x30 or count(multi) != base_count - 3:
            raise SystemExit("regression failed: multi delete size/count wrong")
        reparse_ok(multi)

        # override flags actually permit the gated deletes.
        run([sys.executable, str(TOOL), str(dat), "--delete-index", "50",
             "--allow-flik-letter", "--write", "--out", t / "flik.DAT"])
        run([sys.executable, str(TOOL), str(dat), "--delete-index", "67",
             "--allow-telescope", "--write", "--out", t / "scope.DAT"])

        # apply_level_placements delete op (spec runner) matches the standalone tool.
        spec = t / "del.yaml"
        spec.write_text(
            "source_dat: " + str(dat) + "\n"
            "operations:\n  - op: delete\n    entry: 0\n")
        viaspec = t / "viaspec.DAT"
        run([sys.executable, str(APPLY), str(spec), "--write", "--out", str(viaspec)])
        if viaspec.read_bytes() != single.read_bytes():
            raise SystemExit("regression failed: apply_level_placements delete != standalone delete")

        # insert-then-delete via the two wrappers round-trips byte-exact.
        appended = t / "app.DAT"
        run([sys.executable, str(INSERT), str(dat), "--append-new", "0x14:1:2:3",
             "--write", "--out", str(appended)])
        restored = t / "restored.DAT"
        run([sys.executable, str(TOOL), str(appended), "--delete-index", str(base_count),
             "--write", "--out", str(restored)])
        if restored.read_bytes() != dat.read_bytes():
            raise SystemExit("regression failed: wrapper insert->delete did not restore original")

    print("type-0x3f delete regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
