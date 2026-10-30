#!/usr/bin/env python3
"""Phase-3 WP8 / gate bullet 2: STATIC reader/writer xrefs for owned state.

The census has a CALL graph (functions.json callers/callees) but no DATA xrefs —
nothing in the repo can answer "which instructions read or write address A".
So `config/semantic_state.yaml` has 43 hand-curated `writers` (never checked
against the image) and NO `readers` at all, and the Phase-3 exit gate asks for
readers/writers on every owned state.

This scans the pristine EXE for every load/store and resolves its effective
address where that is STATICALLY possible:

  gp-relative     base register is $gp (r28, = 0x80081D98) -> addr = gp + imm
  absolute        base built by `lui` (+ optional `addiu` low half) in the same
                  function -> addr = base + imm

  pointer-based   base is a runtime value (a record field via a base register, a
                  malloc'd block, an argument). THE ADDRESS CANNOT BE KNOWN
                  STATICALLY. These are counted and reported as
                  `not_statically_resolvable`, NOT as "no readers" — a zero-reader
                  claim that is really a limitation of the method is exactly the
                  confident-but-wrong artifact this project keeps unwinding.

It then VERIFIES the hand-declared writers: a declared writer this scan cannot
see is reported as a contradiction (WP9), not silently dropped — it may be a real
error, or it may be a pointer-based write the method cannot see, and the report
says which.

DELIBERATELY NOT written back into config/semantic_state.yaml: re-serialising that
file would destroy its curated comments and per-entry notes, and the data is already
here in machine-readable form. The registry POINTS at this artifact instead, and the
depth check (tools/phase3_semantic_depth.py) reads it — one source of truth, no
duplicated copy to drift.

Usage: python3 tools/phase3_xrefs.py
Output: analysis/phase3_xrefs.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from phase3_jr_tables import (EXE_BASE, find_function, last_defs,  # noqa: E402
                              load_functions, load_symbols, s16, word)

EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
GP = 0x80081D98          # config/overlays.yml: overlays share the resident $gp
# Overlay code is swapped into this RAM window from LEVEL*.BIN / MEMORY.BIN; it is
# NOT part of the resident EXE image this tool scans.
OVERLAY_LO, OVERLAY_HI = 0x800B39A4, 0x800BE5E8

LOADS = {0x20: "lb", 0x21: "lh", 0x23: "lw", 0x24: "lbu", 0x25: "lhu"}
STORES = {0x28: "sb", 0x29: "sh", 0x2B: "sw"}


def fixture_pin(*rels):
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def resolve_base(exe, fstart, pc, reg):
    """The constant value of `reg` at `pc`, or None if it is a runtime pointer.

    Handles the two forms the compiler emits for a global:
        lui  at, HI                 -> base = HI<<16
        lui  v0, HI ; addiu v0, LO  -> base = HI<<16 + LO
    Anything else (addu of a pointer, a loaded value, an argument) is NOT
    statically knowable, and saying so is the point.
    """
    if reg == 28:
        return GP
    defs = last_defs(exe, fstart, pc)
    if reg not in defs:
        return None
    va, i, _ = defs[reg]
    op = i >> 26
    if op == 0x0F:                                   # lui reg, HI
        return (i & 0xFFFF) << 16
    if op == 0x09:                                   # addiu reg, src, LO
        src = (i >> 21) & 0x1F
        lo = s16(i & 0xFFFF)
        if src == reg or src != 0:
            d2 = last_defs(exe, fstart, va)
            if src in d2:
                _, i2, _ = d2[src]
                if (i2 >> 26) == 0x0F:               # ...whose src was a lui
                    return ((i2 & 0xFFFF) << 16) + lo
        return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args()

    exe = EXE.read_bytes()
    funcs = load_functions()
    syms = load_symbols()

    sem = yaml.safe_load((ROOT / "config" / "semantic_state.yaml").read_text())
    owned = {e["address"]: e for e in sem["entries"]
             if isinstance(e.get("address"), int)}

    readers = defaultdict(list)
    writers = defaultdict(list)
    ptr_stores_in_fn = defaultdict(int)      # fn start -> # pointer-based stores
    stats = {"loads": 0, "stores": 0, "gp_relative": 0, "absolute": 0,
             "pointer_based": 0}

    for fstart, fend, f in funcs:
        if f.get("range_type") not in ("code", "thunk"):
            continue
        fname = f.get("name") or syms.get(fstart)
        for pc in range(fstart, min(fend, EXE_BASE + len(exe)), 4):
            i = word(exe, pc)
            op = i >> 26
            if op not in LOADS and op not in STORES:
                continue
            is_load = op in LOADS
            stats["loads" if is_load else "stores"] += 1
            base_reg = (i >> 21) & 0x1F
            base = resolve_base(exe, fstart, pc, base_reg)
            if base is None:
                stats["pointer_based"] += 1
                if not is_load:
                    ptr_stores_in_fn[fstart] += 1
                continue
            stats["gp_relative" if base_reg == 28 else "absolute"] += 1
            addr = base + s16(i & 0xFFFF)
            if addr in owned:
                rec = {"pc": f"0x{pc:08X}", "function": fname,
                       "op": (LOADS if is_load else STORES)[op]}
                (readers if is_load else writers)[addr].append(rec)

    # --- verify the hand-declared writers -----------------------------------
    # Two things the first pass got wrong, both mine:
    #  * the registry declares writers as FUNCTION addresses (0x8005BDBC =
    #    plant_spawn), while this scan finds INSTRUCTION PCs — so a declared
    #    writer matches if any found PC lies INSIDE the function it names;
    #  * mod_private entries are written by MOD CAVES, which do not exist in the
    #    pristine image at all. Verifying them against pristine is a category
    #    error, so they are excluded from the contradiction list and reported
    #    separately.
    def enclosing(addr):
        f = find_function(funcs, addr)
        return (f[0], f[1]) if f else None

    contradictions, mod_private_skipped, pointer_based_writers = [], [], []
    overlay_declared = []
    per_entry = {}
    for addr, e in sorted(owned.items()):
        found_w = writers.get(addr, [])
        found_r = readers.get(addr, [])
        declared = [w.get("address") for w in (e.get("writers") or [])
                    if isinstance(w.get("address"), int)]
        found_pcs = {int(w["pc"], 16) for w in found_w}
        missing = []
        for d in declared:
            if d in found_pcs:
                continue
            span = enclosing(d)                       # a FUNCTION-level match
            if span and any(span[0] <= pc < span[1] for pc in found_pcs):
                continue
            missing.append(f"0x{d:08X}")
        # A declared writer this scan cannot see is only a CONTRADICTION if the
        # named function contains no pointer-based store either. Tables and
        # records (plant_slots, contact_pool, the camera struct) are written
        # through a cursor/base register — invisible to a static absolute-address
        # scan BY CONSTRUCTION. Blaming the registry for that would be the method
        # blaming the data.
        unverifiable = []
        overlay_writers = []
        real_missing = []
        for d in missing:
            da = int(d, 16)
            if OVERLAY_LO <= da <= OVERLAY_HI:
                # Overlay code is NOT in the resident EXE image at all (it lives
                # in LEVEL*.BIN / MEMORY.BIN and is swapped into this RAM window).
                # A resident-image scan cannot see it — that is a scope fact, not
                # a contradiction.
                overlay_writers.append(d)
            elif (span := enclosing(da)) and ptr_stores_in_fn.get(span[0]):
                unverifiable.append(d)
            else:
                real_missing.append(d)
        missing = real_missing
        if overlay_writers:
            overlay_declared.append({
                "entry": e["id"], "address": f"0x{addr:08X}",
                "declared_writers": overlay_writers,
                "why": "the declared writer lies in OVERLAY space "
                       f"(0x{OVERLAY_LO:08X}..0x{OVERLAY_HI:08X}) — overlay code is "
                       "not part of the resident EXE image, so this scan cannot "
                       "see it. Verifying it needs the overlay blob."})
        if unverifiable:
            pointer_based_writers.append({
                "entry": e["id"], "address": f"0x{addr:08X}",
                "declared_writers": unverifiable,
                "why": "the named function writes this state through a POINTER "
                       "(cursor/base register), which a static absolute-address "
                       "scan cannot attribute. NOT a contradiction — a limit of "
                       "the method, stated rather than hidden."})
        if missing and e["namespace"] == "mod_private":
            mod_private_skipped.append({
                "entry": e["id"], "declared_writers": missing,
                "why": "mod_private state is written by MOD CAVE code, which does "
                       "not exist in the pristine image — not verifiable here, and "
                       "not a contradiction."})
        elif missing:
            contradictions.append({
                "entry": e["id"], "address": f"0x{addr:08X}",
                "declared_writers_not_seen_statically": missing,
                "note": "either a real error in the hand-curated registry, or a "
                        "POINTER-BASED write this static method cannot see (e.g. "
                        "the address is reached through a record base register). "
                        "Reported, not dropped.",
            })
        row = {
            "address": f"0x{addr:08X}",
            "readers": found_r,
            "writers": found_w,
            "reader_count": len(found_r),
            "writer_count": len(found_w),
            "statically_referenced": bool(found_r or found_w),
        }
        if not row["statically_referenced"]:
            # WHY there is no static xref matters enormously. A TABLE is read with
            # an INDEX (lui + addu idx + lw), which this scan cannot resolve BY
            # DESIGN — but its consumers are already enumerated in the dispatch
            # map. Reading "no readers" as "nothing touches it" would be flatly
            # wrong, so say which case this is.
            row["no_static_xref_because"] = (
                "accessed by INDEX (a table read as base + idx*4) — consumers are "
                "enumerated in analysis/phase3_dispatch_map.json and "
                "analysis/phase3_jr_tables.json, NOT lost"
                if e.get("kind") == "table" else
                "reached only through a runtime POINTER, or written by overlay/mod "
                "code outside this image — NOT evidence that nothing touches it")
        per_entry[e["id"]] = row

    silent = [i for i, v in per_entry.items() if not v["statically_referenced"]]

    doc = {
        "_comment": "Phase-3 STATIC data xrefs: which instructions read/write each "
                    "OWNED semantic address. Resolves gp-relative and lui-formed "
                    "absolute accesses. Accesses through a RUNTIME POINTER cannot "
                    "be resolved statically and are counted separately — an entry "
                    "with no static xref is 'not statically referenced', which is "
                    "NOT the same as 'nothing touches it'. Hand-declared writers "
                    "are VERIFIED here; ones this scan cannot see are reported as "
                    "contradictions rather than dropped. "
                    "Regenerate: python3 tools/phase3_xrefs.py",
        "generated": date.today().isoformat(),
        "fixture_sha256": fixture_pin("REBUILD/files/SCUS_942.88"),
        "gp": f"0x{GP:08X}",
        "scan_stats": stats,
        "entries_owned": len(owned),
        "entries_with_static_xrefs": len(owned) - len(silent),
        "entries_without_static_xrefs": silent,
        "declared_writer_contradictions": contradictions,
        "mod_private_not_verifiable_against_pristine": mod_private_skipped,
        "declared_writers_via_pointer_unverifiable": pointer_based_writers,
        "declared_writers_in_overlay_space": overlay_declared,
        "entries": per_entry,
    }
    path = ROOT / "analysis" / "phase3_xrefs.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")

    print(f"[xrefs] scanned {stats['loads']} loads + {stats['stores']} stores: "
          f"{stats['absolute']} absolute, {stats['gp_relative']} gp-relative, "
          f"{stats['pointer_based']} pointer-based (NOT statically resolvable)")
    print(f"[xrefs] {doc['entries_with_static_xrefs']}/{len(owned)} owned entries "
          f"have static xrefs")
    print(f"[xrefs] declared writers via POINTER (method limit, not an error): "
          f"{len(pointer_based_writers)}")
    print(f"[xrefs] declared writers in OVERLAY space (outside this image): "
          f"{len(overlay_declared)}")
    print(f"[xrefs] REAL contradictions (declared writer function stores nothing): "
          f"{len(contradictions)}")
    for c in contradictions[:6]:
        print(f"    {c['entry']}: {c['declared_writers_not_seen_statically']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
