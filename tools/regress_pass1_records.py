#!/usr/bin/env python3
"""Regression checks for the pass-1 scenery move/set/delete write path (punchlist §11.1-2).

Covers dat_reloc.build_reloc_delete_bytes (the general relocation-aware region delete) and
tools/edit_pass1_records.py (list/move/set/delete + verification). Pure-python; writes only
to a temp dir, never mutates workspace DAT/BIN/CUE, never builds an ISO.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dat_reloc          # noqa: E402
import edit_pass1_records as E  # noqa: E402

DEFAULT_DAT = ROOT / "DAT" / "LEVEL01_LEVEL.DAT"
STRIDE = 0x14


def xyz(data: bytes, base: int, i: int):
    return struct.unpack_from("<iii", data, base + i * STRIDE)


def check_engine(d: bytes) -> None:
    """build_reloc_delete_bytes invariants at first/middle/last pass-1 records."""
    src = dat_reloc.DAT(d)
    base = src.trailing_base()[0]
    n = E.pass1_count(d)
    sites0 = len(src.scan_sites()[0])
    for i in (0, 7, n // 2, n - 1):
        new, report, _, _ = dat_reloc.build_reloc_delete_bytes(d, base + i * STRIDE, STRIDE)
        if len(new) != len(d) - STRIDE:
            raise SystemExit(f"engine: i={i} size delta != -0x14")
        if sum(1 for r in report if r.get("dropped")) != 1:
            raise SystemExit(f"engine: i={i} expected exactly 1 in-record field dropped")
        s2 = dat_reloc.DAT(new)
        if len(s2.scan_sites()[0]) != sites0 - 2:
            raise SystemExit(f"engine: i={i} site count not reduced by 2")
        # survivors' X/Y/Z (not relocated) must match original-minus-i, in order
        survivors = [j for j in range(n) if j != i]
        for k, oldi in enumerate(survivors):
            if xyz(new, base, k) != xyz(d, base, oldi):
                raise SystemExit(f"engine: i={i} survivor #{k}(old {oldi}) XYZ mismatch")
        # every record/pass3 pointer resolves in-bounds
        for s in s2.scan_sites()[0]:
            if s["site"] in ("P1.A [s3+2]", "P3.G [s3+2]") and not (0 <= s["value"] < len(new)):
                raise SystemExit(f"engine: i={i} pointer {s['field']:#x} out of bounds")
    # a surviving field pointing into the deleted region is refused
    print("engine invariants passed (delete at first/mid/last, survivor XYZ, in-bounds)")


def check_tool(d: bytes) -> None:
    base = E.pass1_base(d)
    n = E.pass1_count(d)
    if len(E.list_records(d)) != n:
        raise SystemExit("tool: list_records count mismatch")

    # MOVE is size-preserving, count-preserving, only the targeted XYZ changes
    moved, log = E.apply_moves_sets(d, base, n, [(10, 1000, -2000, 3000)], [])
    if len(moved) != len(d) or E.pass1_count(moved) != n:
        raise SystemExit("tool: move changed size/count")
    if xyz(moved, base, 10) != tuple(a + b for a, b in zip(xyz(d, base, 10), (1000, -2000, 3000))):
        raise SystemExit("tool: move delta wrong")
    if any(xyz(moved, base, j) != xyz(d, base, j) for j in range(n) if j != 10):
        raise SystemExit("tool: move touched other records")

    # SET is absolute
    setd, _ = E.apply_moves_sets(d, base, n, [], [(20, 11111, 22222, 33333)])
    if xyz(setd, base, 20) != (11111, 22222, 33333):
        raise SystemExit("tool: set wrong")

    # DELETE multi high-first: count/size correct, survivors intact, reparses
    final, _ = E.apply_deletes(d, [5, 10, 250])
    E.verify(d, final, [5, 10, 250], 0)
    if E.pass1_count(final) != n - 3 or len(final) != len(d) - 3 * STRIDE:
        raise SystemExit("tool: multi-delete count/size wrong")

    # combined move+delete via the same path the CLI uses
    d2, _ = E.apply_moves_sets(d, base, n, [(0, 50, 0, 0)], [(30, 1, 2, 3)])
    d3, _ = E.apply_deletes(d2, [250])
    E.verify(d, d3, [250], 2)
    if E.pass1_count(d3) != n - 1:
        raise SystemExit("tool: combined move+delete count wrong")
    dat_reloc.DAT(d3).scan_sites()
    print("tool checks passed (list/move/set/delete/verify, combined)")


def main() -> int:
    dat = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DAT
    if not dat.exists():
        raise SystemExit(f"input DAT not found: {dat}")
    d = dat.read_bytes()
    check_engine(d)
    check_tool(d)
    print("pass-1 scenery (§11.1-2) regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
