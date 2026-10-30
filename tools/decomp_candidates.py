#!/usr/bin/env python3
"""Rank unmatched resident functions by C-matchability (docs/SUBSTRATE.md).

Reads the census (analysis/functions.json) + the EXE bytes, computes per-
function features, EXCLUDES already-matched functions and the classes the
byte-splat substrate v1 can't handle yet (switch/jr-table + rodata, > ~0x200 B,
gp-heavy), scores the rest, and writes analysis/decomp_candidates.json (+ a
printed top-N). "behavior-known" (has a src_re file or a real Canon name) boosts
rank so understood functions — which also promote a Canon note on match — come
first.

  python tools/decomp_candidates.py [--top 20] [--include-gp] [--max-size 0x200]
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import exe_read  # noqa: E402

CENSUS = ROOT / "analysis" / "functions.json"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
SRC_RE = ROOT / "src_re"
CANON_FUNCS = ROOT / "ObsidianVault" / "Canon" / "Functions"
OUT = ROOT / "analysis" / "decomp_candidates.json"

TEXT_LO = 0x80010000
BSS_START = 0x80082200   # >= here is data (BSS overlap); last real code ~0x8008219c
DEFAULT_MAX_SIZE = 0x200
# a real function carries at least one code-structural signal; a record with
# ONLY `symbol` is a .sym-named DATA global that leaked into the text range.
CODE_SIGNALS = {"r2", "jal_target", "j_target", "prologue", "reachable",
                "ghidra", "psyq", "jumptable", "entry", "gap_code", "dynamic"}


def _words(exe: bytes, s: int, e: int) -> list[int]:
    off = s - TEXT_LO + 0x800
    return [struct.unpack_from("<I", exe, off + i)[0] for i in range(0, e - s, 4)]


def _features(exe: bytes, r: dict) -> dict:
    s, e = int(r["start"], 16), int(r["end"], 16)
    ws = _words(exe, s, e)
    uses_gp = any((w >> 26) in range(0x20, 0x2c) and (w >> 21) & 0x1f == 28 for w in ws)
    has_frame = any((w & 0xFFFF8000) == 0x27BD8000 for w in ws)   # addiu sp,-N
    # jr to a register other than $ra (31) => computed jump == switch/jr-table
    jr_table = any((w >> 26) == 0 and (w & 0x3F) == 0x08 and ((w >> 21) & 0x1f) != 31
                   for w in ws)
    # a complete function ends in a return: `jr ra` (0x03e00008) or a `j`.
    # missing one => the census extent is truncated (bad match target).
    has_return = any(w == 0x03E00008 or (w >> 26) == 2 for w in ws)
    # fragment: a control-flow edge leaves out the TOP (target < start). A conditional
    # branch or plain `j` to before the function start means r2 split the tail/epilogue
    # of a LARGER routine — not a real function entry (e.g. the seed-plant handlers,
    # which are loop-tails of ~1KB dispatchers). Byte-matchable but semantically bogus.
    fragment = False
    for i, w in enumerate(ws):
        pc = s + i * 4
        op = w >> 26
        if op in (1, 4, 5, 6, 7):                       # regimm / beq / bne / blez / bgtz
            tgt = pc + 4 + ((((w & 0xFFFF) ^ 0x8000) - 0x8000) << 2)
            if tgt < s:
                fragment = True
        elif op == 2:                                    # j (not jal — jal back = normal call)
            tgt = (pc & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
            if tgt < s:
                fragment = True
    return {"size": e - s, "n_callees": len(r["callees"]), "n_callers": len(r["callers"]),
            "uses_gp": uses_gp, "has_frame": has_frame, "jr_table": jr_table,
            "has_return": has_return, "fragment": fragment,
            "dynamic": "dynamic" in (r.get("discovery") or [])}


def _behavior_known(r: dict) -> bool:
    """Has a src_re pseudocode file or a real (non-FUNC_) Canon name."""
    if r["name"] and not r["name"].startswith("FUNC_"):
        return True
    tag = r["start"].replace("0x", "")
    if SRC_RE.is_dir() and any(tag in p.name for p in SRC_RE.glob("*.c")):
        return True
    if CANON_FUNCS.is_dir() and any(tag.upper() in p.name.upper()
                                    for p in CANON_FUNCS.glob("FUNC_*")):
        return True
    return False


def _score(f: dict, known: bool) -> float:
    """Higher = easier + higher-value. Small, few callees, no frame, known."""
    s = 100.0
    s -= f["size"] / 8.0            # smaller is easier
    s -= f["n_callees"] * 4.0       # fewer calls is easier
    s -= 20 if f["has_frame"] else 0
    s += 40 if known else 0         # understood functions first (Canon value)
    s += min(f["n_callers"], 8) * 2  # well-referenced = more useful
    s += 15 if f.get("dynamic") else 0  # runtime-confirmed (Phase-5 dynamic coverage) first
    return round(s, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--include-gp", action="store_true", help="don't exclude gp-relative fns")
    ap.add_argument("--include-fragments", action="store_true",
                    help="don't exclude r2-split fragments (branch/j out the top)")
    ap.add_argument("--max-size", type=lambda x: int(x, 0), default=DEFAULT_MAX_SIZE)
    ap.add_argument("--classes", help="comma list to keep (e.g. game,unknown); default all")
    args = ap.parse_args()
    keep_classes = set(args.classes.split(",")) if args.classes else None

    census = json.loads(CENSUS.read_text())
    exe = EXE.read_bytes()
    cands, excluded = [], {"matched": 0, "size": 0, "jr_table": 0, "gp": 0, "not_code": 0}
    for r in census["functions"]:
        if r["space"] != "resident":
            continue
        if r.get("match"):
            excluded["matched"] += 1
            continue
        if (r["range_type"] != "code" or not (set(r["discovery"]) & CODE_SIGNALS)
                or int(r["start"], 16) >= BSS_START or "_OBJ_" in (r["name"] or "")):
            excluded["not_code"] += 1
            continue
        f = _features(exe, r)
        if not f["has_return"]:      # truncated census extent, not a whole function
            excluded["truncated"] = excluded.get("truncated", 0) + 1
            continue
        if f["size"] > args.max_size:
            excluded["size"] += 1
            # Substrate v3: sub-classify the oversized bucket so the byte-yield opportunity
            # is visible — LINEAR oversized fns match today (no new machinery, just --max-size),
            # gp needs the small_data path, jr_table needs the pooled-table mechanism.
            sb = excluded.setdefault("size_breakdown", {"linear": 0, "gp": 0, "jr_table": 0})
            if f["jr_table"]:
                sb["jr_table"] += 1
            elif f["uses_gp"]:
                sb["gp"] += 1
            else:
                sb["linear"] += 1
            continue
        if f["jr_table"]:
            excluded["jr_table"] += 1
            continue
        if f["fragment"] and not args.include_fragments:
            excluded["fragment"] = excluded.get("fragment", 0) + 1
            continue
        if f["uses_gp"] and not args.include_gp:
            excluded["gp"] += 1
            continue
        if keep_classes is not None and r["classification"] not in keep_classes:
            excluded.setdefault("class", 0)
            excluded["class"] += 1
            continue
        known = _behavior_known(r)
        cands.append({"start": r["start"], "end": r["end"], "name": r["name"],
                      "classification": r["classification"],
                      "behavior_known": known, "score": _score(f, known),
                      "callees": r["callees"], **f})
    cands.sort(key=lambda c: (-c["score"], c["start"]))

    doc = {"generated_by": "tools/decomp_candidates.py",
           "params": {"max_size": f"{args.max_size:#x}", "include_gp": args.include_gp},
           "excluded_counts": excluded, "total_candidates": len(cands),
           "candidates": cands}
    OUT.write_text(json.dumps(doc, indent=1) + "\n")

    print(f"[candidates] {len(cands)} matchable (excluded: "
          f"{excluded['matched']} matched, {excluded['size']} too-big, "
          f"{excluded['jr_table']} jr-table, {excluded['gp']} gp)")
    print(f"\n  {'addr':10} {'sz':>4} {'ce':>2} {'kn':>2} {'score':>6}  name")
    for c in cands[:args.top]:
        print(f"  {c['start']} {c['size']:>4} {c['n_callees']:>2} "
              f"{'Y' if c['behavior_known'] else '-':>2} {c['score']:>6.1f}  "
              f"{c['name'] or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
