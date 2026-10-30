#!/usr/bin/env python3
"""Dump the resident-image function list as plain text for tools/region_provenance.c.

WHY THIS EXISTS
---------------
`analysis/functions.json` is a ~1MB structured document (resident + overlay + anomaly
data). Writing a JSON parser in C to read three fields out of it is effort spent on the
wrong thing. This replicates EXACTLY the filtering `census_address.Image.__init__` does
-- same field fallbacks (`start`, since that's this file's actual key), same
`base <= addr < end` resident-image filter read from the EXE's own header -- so the C
analysis operates on the identical function set the Python census does. That parity is
what makes a baseline comparison (14 hits, 882 residual) meaningful.

FORMAT
    <addr_hex> <size_decimal> <name>
one function per line, sorted by address. Names in this project are snake_case
identifiers with no whitespace, so simple space-splitting on the C side is safe.

USAGE
    tools/dump_functions_txt.py --exe SCUS_942.88 --functions analysis/functions.json \
        --out analysis/functions_resident.txt
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", type=Path, default=ROOT / "REBUILD" / "files" / "SCUS_942.88")
    ap.add_argument("--functions", type=Path, default=Path("analysis/functions.json"))
    ap.add_argument("--out", type=Path, default=Path("analysis/functions_resident.txt"))
    args = ap.parse_args()

    data = args.exe.read_bytes()
    if data[:8] != b"PS-X EXE":
        raise SystemExit(f"{args.exe}: not a PS-X EXE")
    base = struct.unpack_from("<I", data, 0x18)[0]
    end = base + len(data) - 0x800

    doc = json.loads(args.functions.read_text())
    fns = doc.get("functions", doc) if isinstance(doc, dict) else doc

    recs = []
    for f in fns:
        a = f.get("address") or f.get("addr") or f.get("start")
        if isinstance(a, str):
            a = int(a, 16)
        if a and base <= a < end:
            recs.append((a, int(f.get("size") or 0), f.get("name") or "?"))
    recs.sort()

    with args.out.open("w") as fh:
        fh.write("# base 0x%08X end 0x%08X count %d\n" % (base, end, len(recs)))
        for a, size, name in recs:
            safe_name = name.replace(" ", "_") if name else "?"
            fh.write("0x%08X %d %s\n" % (a, size, safe_name))
    print("wrote %d resident functions to %s (base 0x%08X end 0x%08X)"
          % (len(recs), args.out, base, end))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
