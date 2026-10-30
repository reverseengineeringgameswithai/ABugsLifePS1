#!/usr/bin/env python3
"""Regression checks for the LEVEL.DAT coord-record editor (§3 enemy/object movement data).

Covers tools/edit_dat_coord_record.py: discovery of the type-1 mover waypoints + type-11/12/13
zones, size-preserving translate, set-entry, and the only-this-record-changed guard. Pure-python;
writes only to a temp dir.
"""
from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import edit_dat_coord_record as E  # noqa: E402

DAT = ROOT / "DAT" / "LEVEL01_LEVEL.DAT"
PT = 0xc


def main() -> int:
    if not DAT.exists():
        raise SystemExit(f"input DAT not found: {DAT}")
    d = DAT.read_bytes()

    # discovery: the mover waypoints (0x468 type 1, 104) + 3 zones (types 11/12/13, 16) must appear
    recs = {off: (typ, cnt) for off, typ, cnt in E.coord_records(d)}
    if recs.get(0x468) != (1, 104):
        raise SystemExit(f"discovery: rec1 mover waypoints != (1,104): {recs.get(0x468)}")
    for off, want in ((0x94c, (11, 16)), (0xa10, (12, 16)), (0xad4, (13, 16))):
        if recs.get(off) != want:
            raise SystemExit(f"discovery: zone @ {off:#x} != {want}: {recs.get(off)}")
    # type-0x3f pickups (rec0) must NOT be listed
    if 0x4 in recs:
        raise SystemExit("discovery: type-0x3f rec0 must be excluded")
    print(f"discovery OK (mover waypoints 0x468 type1 x104; zones 11/12/13)")

    # translate the mover waypoints; size-preserving, only that record changes, deltas applied
    import subprocess
    TOOL = ROOT / "tools" / "edit_dat_coord_record.py"
    with tempfile.TemporaryDirectory(prefix="coordrec_regress_") as tmp:
        out = Path(tmp) / "wp.DAT"
        p = subprocess.run([sys.executable, str(TOOL), str(DAT), "--record", "0x468",
                            "--move", "6000:-7:8", "--write", "--out", str(out)],
                           cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.returncode != 0:
            print(p.stdout); raise SystemExit("move failed")
        o = out.read_bytes()
        if len(o) != len(d):
            raise SystemExit("move changed file size")
        # wp0 shifted by the delta; bytes outside rec1 unchanged
        ox, oy, oz = struct.unpack_from("<iii", d, 0x46c)
        nx, ny, nz = struct.unpack_from("<iii", o, 0x46c)
        if (nx, ny, nz) != (ox + 6000, oy - 7, oz + 8):
            raise SystemExit(f"move delta wrong: {(nx,ny,nz)} != {(ox+6000,oy-7,oz+8)}")
        span = 4 + 104 * PT
        if d[:0x468] != o[:0x468] or d[0x468 + span:] != o[0x468 + span:]:
            raise SystemExit("move touched bytes outside rec1")

        # set-entry on a zone; absolute coords land
        out2 = Path(tmp) / "z.DAT"
        p = subprocess.run([sys.executable, str(TOOL), str(DAT), "--record", "0x94c",
                            "--set-entry", "0:111:222:333", "--write", "--out", str(out2)],
                           cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.returncode != 0:
            print(p.stdout); raise SystemExit("set-entry failed")
        if struct.unpack_from("<iii", out2.read_bytes(), 0x94c + 4) != (111, 222, 333):
            raise SystemExit("set-entry value wrong")

        # editing a non-coord record (type-0x3f rec0 @ 0x4) is refused
        p = subprocess.run([sys.executable, str(TOOL), str(DAT), "--record", "0x4",
                            "--move", "1:0:0", "--write", "--out", Path(tmp) / "x.DAT"],
                           cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.returncode == 0 or "not a top-level coord record" not in p.stdout:
            raise SystemExit("type-0x3f record should be refused")
    print("edit checks OK (translate, set-entry, only-record-changed, non-coord refused)")
    print("dat coord-record (§3) regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
