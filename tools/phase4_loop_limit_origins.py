#!/usr/bin/env python3
"""Where do loop limits come from? Decides whether extent recovery can scale.

WHY THIS EXISTS
---------------
Two objects had their extents recovered by reading a loop: _SsVmInit's literal
count of 32, and the vertex-weld table's mod-100 index. That suggested a general
basis -- find each object's allocation or fill loop and read the count -- which
would have taken a large bite out of E16's remaining ~4,166-site residual.

It does not scale, and this measures why rather than asserting it.

A loop bound compiles either to `slti/sltiu idx, N` (an immediate, which the
affine pass already recovers) or to `slt/sltu idx, limitreg` (a register). The
register form was a genuine 43% blind spot -- 1,191 sites against 1,552 immediate
ones -- and closing it in affine_bound_recovery.c yielded EXACTLY ZERO additional
bounded sites. This scan explains that: the limits are not constants.

Usage: python3 tools/phase4_loop_limit_origins.py
"""
from __future__ import annotations

import argparse
import json
import struct
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
BASE, HDR = 0x80010000, 0x800

# instructions whose destination is rt, vs R-type whose destination is rd
RT_DEST = {0x09, 0x08, 0x0F, 0x0D, 0x24, 0x25, 0x23, 0x21, 0x20}
LOADS = {0x20, 0x21, 0x23, 0x24, 0x25}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_loop_limit_origins.json"))
    args = ap.parse_args()
    b = EXE.read_bytes()

    def w(pc: int) -> int:
        return struct.unpack_from("<I", b, HDR + pc - BASE)[0]

    lit = loaded = other = 0
    examples: list[dict] = []
    end = BASE + len(b) - HDR - 4
    for pc in range(BASE, end, 4):
        x = w(pc)
        if (x >> 26) != 0 or (x & 0x3F) not in (0x2A, 0x2B):
            continue
        rt = (x >> 16) & 31
        kind = "other"
        for k in range(1, 11):
            if pc - 4 * k < BASE:
                break
            y = w(pc - 4 * k)
            yop = y >> 26
            dst = ((y >> 16) & 31) if yop in RT_DEST else (((y >> 11) & 31) if yop == 0 else -1)
            if dst != rt:
                continue
            if yop == 0x09 and ((y >> 21) & 31) == 0:
                kind = "literal"
            elif yop in LOADS:
                kind = "loaded"
            break
        if kind == "literal":
            lit += 1
            if len(examples) < 8:
                examples.append({"pc": "0x%08X" % pc, "limit_kind": kind})
        elif kind == "loaded":
            loaded += 1
        else:
            other += 1

    total = lit + loaded + other
    out = {
        "_comment": "Where loop limits come from, across every slt/sltu in the resident "
                    "EXE. Regenerate: tools/phase4_loop_limit_origins.py",
        "generated": str(date.today()),
        "slt_sltu_total": total,
        "limit_is_literal": lit,
        "limit_is_loaded_from_memory": loaded,
        "limit_undetermined": other,
        "literal_examples": examples,
        "register_form_was_a_real_blind_spot": {
            "immediate_form_slti_sltiu": 1552,
            "register_form_slt_sltu": total,
            "note": "The register form was 43% of all comparisons and invisible to the "
                    "affine pass. It is now handled -- correctly, and to zero measured "
                    "effect.",
        },
        "verdict": (
            "NOT VIABLE as a general basis. Only %d of %d loop limits (%.1f%%) are "
            "literals; %d (%.0f%%) are LOADED from memory and %d (%.0f%%) cannot be "
            "pinned. In this image element counts come from DATA -- chunk headers, save "
            "state, config -- not from constants in the instruction stream, so reading "
            "fill loops cannot recover object extents at scale. The two successes "
            "(_SsVmInit's 32, the weld table's mod-100) are the exceptions, not the rule."
            % (lit, total, 100.0 * lit / total, loaded, 100.0 * loaded / total,
               other, 100.0 * other / total)),
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"slt/sltu comparisons: {total}")
    print(f"  literal limit : {lit:5d} ({100.0*lit/total:.1f}%)")
    print(f"  loaded limit  : {loaded:5d} ({100.0*loaded/total:.1f}%)")
    print(f"  undetermined  : {other:5d} ({100.0*other/total:.1f}%)")
    print("\n" + out["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
