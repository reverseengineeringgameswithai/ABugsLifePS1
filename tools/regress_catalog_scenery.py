#!/usr/bin/env python3
"""Regression checks for the scenery/decor object catalog (§11.3a / step 9).

Covers tools/catalog_scenery.py: pass-1 instance walk, payload bridge (node +0x14/+0x1c by
flag bit3), instancing histogram, payload geometry + shape class. Pure-python, read-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import catalog_scenery as CS  # noqa: E402

DAT = ROOT / "DAT" / "LEVEL01_LEVEL.DAT"


def main() -> int:
    if not DAT.exists():
        raise SystemExit(f"input DAT not found: {DAT}")
    d = DAT.read_bytes()

    recs = list(CS.pass1_records(d))
    if len(recs) != 484:
        raise SystemExit(f"pass-1 instance count {len(recs)} != 484")
    # group by payload; 2 known records (flags 0x14 -> payload 0x2f700) don't decode
    distinct = {}
    valid = {}
    invalid_records = 0
    for x, y, z, flags, node, pay in recs:
        distinct.setdefault(pay, 0); distinct[pay] += 1
        if CS.payload_geom(d, pay) is None:
            invalid_records += 1
        else:
            valid.setdefault(pay, 0); valid[pay] += 1
    if len(distinct) != 152:
        raise SystemExit(f"distinct payloads {len(distinct)} != 152")
    if len(valid) != 151:
        raise SystemExit(f"valid-geometry meshes {len(valid)} != 151")
    if invalid_records != 2:
        raise SystemExit(f"invalid-payload records {invalid_records} != 2 (expected the 0x2f700 pair)")
    top = max(valid.items(), key=lambda kv: kv[1])
    if top != (0x2d460, 93):
        raise SystemExit(f"top mesh {top} != (0x2d460, 93)")
    print(f"catalog OK (484 instances, 152 payloads [151 valid + 1 anomalous 0x2f700], top 0x2d460 x93)")

    # shape_class is stable + sensible
    if CS.shape_class(100, 10, 100) != "flat (ground/decor-mat)":
        raise SystemExit("shape_class: flat case wrong")
    if CS.shape_class(100, 2000, 100) != "tall (upright prop)":
        raise SystemExit("shape_class: tall case wrong")
    # a known tall mesh classifies as tall
    g = CS.payload_geom(d, 0x2f2f8)
    if g is None or CS.shape_class(g[1], g[2], g[3]) != "tall (upright prop)":
        raise SystemExit("shape_class: 0x2f2f8 should be tall")
    print("shape_class OK (flat/tall + known mesh)")
    print("scenery catalog (§11.3a) regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
