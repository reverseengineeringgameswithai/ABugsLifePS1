#!/usr/bin/env python3
"""How many of the non-negative-index discharges could actually have a NEGATIVE index?

WHY THIS GATES THE MOVIE CAMPAIGN
---------------------------------
722 of E16's 851 priority discharges rest on one convention -- array indices are
non-negative -- which is what makes an access based ABOVE a table window unable
to reach it. The packet declares that as a single residual whose
`intersects_dimension` is NOT yet assertable as false, because one known site
breaks the pattern: 0x8005D69C computes `0x800A6300 + (short)a3*4`, a SIGNED
short, where a negative index is representable.

Recording a movie campaign is the declared falsifier for that residual. But a
campaign is only worth recording if the exception is NARROW. If most of the 722
carry a signed index, the convention is wrong in a way no amount of replay would
rescue, and the recording would be wasted.

So: classify every discharged site by whether its index can be negative.

METHOD
------
Each site carries the symbol its index was born from. A symbol is either a
defining PC or an opaque block/function-entry marker. For a PC, the defining
instruction decides the sign domain:

  PROVABLY NON-NEGATIVE   andi (mask), lhu, lbu, srl (logical shift), sltiu/slti
                          results (0/1), addiu from a non-negative
  SIGNED-CAPABLE          sra and the `sll 16 / sra 16` short-cast idiom,
                          lh, lb, subu
  UNKNOWN                 anything else, and opaque block/entry symbols

UNKNOWN is counted separately and never as safe -- it is the honest middle.

Usage: python3 tools/phase4_e16_signed_index_audit.py
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD/files/SCUS_942.88"
FUNCS = ROOT / "analysis/functions_resident.txt"
TARGETS = [("markers_0x30_0x57", 0x8009B5A8, 0x8009B648),
           ("markers_0x28_0x2F", 0x8009C210, 0x8009C230),
           ("markers_0x58_0x5F", 0x800A65B0, 0x800A65D0)]

NONNEG_OPS = {0x0C: "andi", 0x25: "lhu", 0x24: "lbu", 0x0A: "slti", 0x0B: "sltiu"}
SIGNED_OPS = {0x21: "lh", 0x20: "lb"}


def classify(img: bytes, base: int, sym: int) -> tuple[str, str]:
    if sym < 0:
        return "unknown", "negative symbol id"
    u = sym & 0xFFFFFFFF
    if u >= 0x70000000:
        return "unknown", "function-entry value"
    if u >= 0x40000000:
        return "unknown", "block-entry value"
    pc = u | 0x80000000
    off = 0x800 + (pc - base)
    if off < 0 or off + 4 > len(img):
        return "unknown", "defining pc outside the image"
    w = struct.unpack_from("<I", img, off)[0]
    op, funct, sa = w >> 26, w & 0x3F, (w >> 6) & 31
    if op in NONNEG_OPS:
        return "non_negative", NONNEG_OPS[op]
    if op in SIGNED_OPS:
        return "signed_capable", SIGNED_OPS[op]
    if op == 0:
        if funct == 0x02:
            return "non_negative", "srl (logical shift)"
        if funct == 0x03:
            # `sll r,16 / sra r,16` is the short-cast idiom -- look back one word
            prev = struct.unpack_from("<I", img, off - 4)[0] if off >= 4 else 0
            if (prev >> 26) == 0 and (prev & 0x3F) == 0 and ((prev >> 6) & 31) == 16 and sa == 16:
                return "signed_capable", "sll16/sra16 short cast"
            return "signed_capable", "sra (arithmetic shift, sign preserved)"
        if funct == 0x23:
            return "signed_capable", "subu"
        if funct in (0x2A, 0x2B):
            return "non_negative", "slt/sltu result (0 or 1)"
    return "unknown", "op 0x%02x" % op


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_signed_index_audit.json"))
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="e16si_"))
    tool = str(tmp / "abr")
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", tool,
                    str(ROOT / "tools/affine_bound_recovery.c")], check=True)
    sj = tmp / "s.json"
    r = subprocess.run([tool, str(EXE), str(FUNCS), "--interprocedural", "--emit-all",
                        "--json", str(sj), "--verify"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        raise SystemExit("ground-truth verification failed -- refusing to report")

    img = EXE.read_bytes()
    sites = json.loads(sj.read_text())["sites"]

    kinds, reasons, mags = Counter(), Counter(), Counter()
    risk = []
    signed_examples, per_target = [], defaultdict(Counter)
    for s in sites:
        b, st = int(s["base"], 16), abs(s["stride"] or 1)
        for tn, lo, hi in TARGETS:
            if b < hi:            # only bases ABOVE the window use the convention
                continue
            k, why = classify(img, 0x80010000, s["sym"])
            need = abs(-((b - hi) // st + 1))
            mag = ("small(<64)" if need < 64 else
                   "medium(64-1k)" if need < 1024 else "large(>=1k)")
            kinds[k] += 1
            reasons[why] += 1
            per_target[tn][k] += 1
            mags[(mag, k)] += 1
            if need < 64 and k != "non_negative":
                risk.append({"pc": s["pc"], "base": s["base"], "stride": s["stride"],
                             "required_negative_index": need, "kind": k, "target": tn})
            if k == "signed_capable" and len(signed_examples) < 12:
                signed_examples.append({"pc": s["pc"], "base": s["base"],
                                        "stride": s["stride"], "why": why, "target": tn})
            break

    total = sum(kinds.values())
    sc = kinds["signed_capable"]
    out = {
        "_comment": "Does the non-negative-index convention hold for the sites it "
                    "discharges? Gates whether a movie campaign is worth recording. "
                    "Regenerate: tools/phase4_e16_signed_index_audit.py",
        "generated": str(date.today()),
        "why_this_gates_recording": "A campaign is the declared falsifier for the "
                                    "convention residual. It is only worth recording if the "
                                    "exception is NARROW; if most indices are signed, the "
                                    "convention is wrong in a way replay cannot rescue.",
        "sites_discharged_by_the_convention": total,
        "classification": dict(kinds),
        "signed_capable_fraction": round(sc / total, 4) if total else None,
        "defining_instruction_histogram": dict(reasons.most_common()),
        "signed_examples": signed_examples,
        "per_target": {k: dict(v) for k, v in per_target.items()},
        "verdict": None,
    }
    # MAGNITUDE is the missing dimension. The raw signed fraction is the wrong
    # metric: the convention is not being asked to rule out "index -1" (which would
    # be fragile) but "this array runs 1,570 elements BACKWARDS past its own base".
    # Classify by how large a negative index each site would actually need.
    out["by_required_magnitude"] = {f"{m}|{k}": v for (m, k), v in sorted(mags.items())}
    out["true_risk_set"] = {
        "definition": "needs a SMALL (<64) negative index AND is not provably "
                      "non-negative -- i.e. where the convention is doing fragile work",
        "count": len(risk), "sites": risk[:20],
    }
    medium = sum(v for (m, k), v in mags.items() if m == "medium(64-1k)")
    large = sum(v for (m, k), v in mags.items() if m == "large(>=1k)")
    if not risk:
        out["verdict"] = (
            "SAFE TO LEAN ON, with the magnitude stated. ZERO discharged sites need a "
            "small negative index; %d need 64-1k and %d need >= 1k. The convention is "
            "ruling out an array running hundreds to thousands of elements backwards "
            "past its own base, not an off-by-one. %.1f%% of the indices are "
            "signed-CAPABLE, but none of them is asked to be even slightly negative."
            % (medium, large, 100 * sc / total if total else 0))
    else:
        out["verdict"] = (
            "NOT SAFE: %d sites need a SMALL negative index and are not provably "
            "non-negative. Those must be resolved per-site before the convention can "
            "carry this weight." % len(risk))
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"sites discharged by the convention: {total}")
    for k, v in kinds.most_common():
        print(f"   {k:16s} {v:5d}  ({100*v/total:.1f}%)")
    print(f"   true risk set (small negative index, not provably non-neg): {len(risk)}")
    print("\n" + out["verdict"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
