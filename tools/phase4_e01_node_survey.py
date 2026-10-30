#!/usr/bin/env python3
"""Phase 4 E01: campaign-wide survey of the fcn.80010000 floor/scenery NODE arrays.

The LEVEL01-proven structure (level_editor/scene_importer.py, GAP-0023): a contiguous
run of 0x18-stride records, each

    +0x00/04/08  s32 world anchor T_obj (x, y, z)
    +0x0c        pad
    +0x10        constant marker 0xC0080000
    +0x14        payload file offset (points at an fcn.80010000 vertex payload)

The marker makes the array findable without a per-level profile: scan every
0x4-aligned offset for runs of records whose +0x10 reads the marker, keep runs of
length >= MIN_RUN, and validate each record's payload offset lands inside the file.

LEVEL01 ground truth (node_base=0x45F0) doubles as the scanner's self-check.

Usage: python3 tools/phase4_e01_node_survey.py [--out analysis/phase4_e01_node_survey.json]
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

MARKER = 0xC0080000
STRIDE = 0x18
MIN_RUN = 4

REPO = Path(__file__).resolve().parents[1]
LEVEL01_KNOWN_NODE_BASE = 0x45F0


def scan_dat(path: Path) -> dict:
    """Find 0x18-stride runs whose +0x10 field repeats one nonzero constant and whose
    +0x14 payload offsets are strictly increasing and inside the file. The marker
    constant is per-level (LEVEL01's is 0xC0080000), so it is DISCOVERED per run,
    not assumed."""
    data = path.read_bytes()
    n = len(data)
    runs = []
    off = 0
    while off + STRIDE <= n:
        marker = struct.unpack_from("<I", data, off + 0x10)[0] if off + 0x14 <= n else 0
        first_pay = struct.unpack_from("<I", data, off + 0x14)[0] if off + STRIDE <= n else 0
        if marker != 0 and first_pay < n:
            start = off
            count = 0
            payload_ok = 0
            prev_pay = -1
            monotonic = True
            pay_min, pay_max = None, None
            t_min = [None] * 3
            t_max = [None] * 3
            while off + STRIDE <= n and struct.unpack_from("<I", data, off + 0x10)[0] == marker:
                t = struct.unpack_from("<iii", data, off)
                pay = struct.unpack_from("<I", data, off + 0x14)[0]
                if pay >= n:
                    break
                if pay <= prev_pay:
                    monotonic = False
                prev_pay = pay
                payload_ok += 1
                pay_min = pay if pay_min is None else min(pay_min, pay)
                pay_max = pay if pay_max is None else max(pay_max, pay)
                for i in range(3):
                    t_min[i] = t[i] if t_min[i] is None else min(t_min[i], t[i])
                    t_max[i] = t[i] if t_max[i] is None else max(t_max[i], t[i])
                count += 1
                off += STRIDE
            if count >= MIN_RUN and monotonic:
                runs.append({
                    "base": hex(start),
                    "count": count,
                    "marker": hex(marker),
                    "payload_offsets_in_file": payload_ok,
                    "payload_range": [hex(pay_min), hex(pay_max)] if pay_min is not None else None,
                    "t_obj_min": t_min,
                    "t_obj_max": t_max,
                })
                continue
            off = start + 4
            continue
        off += 4
    return {"file": str(path.relative_to(REPO)), "size": n, "runs": runs}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "analysis" / "phase4_e01_node_survey.json"))
    args = ap.parse_args()

    results = []
    for lvl_dir in sorted((REPO / "REBUILD" / "files").glob("LEVEL*")):
        for dat in sorted(lvl_dir.glob("*.DAT")):
            results.append(scan_dat(dat))

    # self-check against LEVEL01's proven profile
    l01 = next(r for r in results if r["file"].endswith("LEVEL01/LEVEL.DAT"))
    main_runs = [r for r in l01["runs"] if int(r["base"], 16) == LEVEL01_KNOWN_NODE_BASE]
    self_check = {
        "level01_expected_node_base": hex(LEVEL01_KNOWN_NODE_BASE),
        "found": bool(main_runs),
        "found_count": main_runs[0]["count"] if main_runs else None,
    }
    if not main_runs:
        raise SystemExit("SELF-CHECK FAILED: LEVEL01 node base 0x45F0 not found by the scanner")

    out = {
        "_comment": "Phase 4 E01 campaign node-array survey. Regenerate: tools/phase4_e01_node_survey.py",
        "marker": hex(MARKER),
        "stride": hex(STRIDE),
        "min_run": MIN_RUN,
        "self_check": self_check,
        "levels": results,
        "summary": {
            r["file"]: [{"base": run["base"], "count": run["count"]} for run in r["runs"]]
            for r in results
        },
    }
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"wrote {args.out}")
    for r in results:
        runs = ", ".join(f"{run['base']}x{run['count']}" for run in r["runs"]) or "NONE"
        print(f"  {r['file']}: {runs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
