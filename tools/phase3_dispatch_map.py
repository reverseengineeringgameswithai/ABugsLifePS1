#!/usr/bin/env python3
"""Phase-3 WP4: enumerate indirect dispatch — jump tables and their targets.

Reads the pristine EXE (REBUILD/files/SCUS_942.88, LOCAL-ONLY game data;
file_off = vaddr - 0x8000F800) and decodes every known jump table into its
target list, resolving each target against the functions census and symbol
store. Every target that lands outside a censused code function, or in an
unnamed one, is a COMPUTED gap (Phase-2 lesson: no declared verdicts).

Tables covered this increment (the campaign-critical resident set):
  mover_vm_opcodes   0x8001B2F4  26 handlers; interpreter FUNC_8004C13C reads
                                 op from obj[+0x70] program, jr [table+op*4]
  berry_throw        0x8001B1C0   5 handlers, indexed by equipped-berry id
                                 (red/blue/homing/gold/mega); NOT extendable
  plant_behaviors    0x8001B848  13 handlers, indexed by plant type-2
                                 (types 2..14; walker 0x8005BFBC..)

Also enumerated: EVERY indirect-dispatch SITE in resident code — all
`jr <reg!=ra>` and `jalr` instructions inside censused code ranges — so WP4's
"all indirect dispatch enumerated" bullet has a computed bound: sites whose
table is not yet decoded are the visible frontier.

Deliberately NOT here (documented, needs different evidence):
  object_pointer_list 0x80096B98 — kind->descriptor table lives in RAM/BSS,
  populated at LOAD TIME from level data; enumerate per-scene via the
  debugger, not from the EXE image.

Usage: python3 tools/phase3_dispatch_map.py   (requires the local EXE)
Output: analysis/phase3_dispatch_map.json
"""
from __future__ import annotations

import json
import struct
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
EXE_BASE = 0x8000F800

TABLES = {
    "mover_vm_opcodes": {
        "address": 0x8001B2F4, "count": 26,
        "consumer": "0x8004C13C (event/mover VM: op = program[obj+0x70], jr)",
        "index_domain": "opcode 0..25 (see analysis/vm_programs.json for the ISA)",
    },
    "berry_throw": {
        "address": 0x8001B1C0, "count": 5,
        "consumer": "berry throw chain (equipped idx 0x800A6597: "
                    "red0/blue1/homing2/gold3/mega4)",
        "index_domain": "equipped berry id 0..4; table NOT extendable in place",
    },
    "plant_behaviors": {
        "address": 0x8001B848, "count": 13,
        "consumer": "plant behavior walker 0x8005BFBC.. (index = plant type - 2)",
        "index_domain": "plant types 2..14",
    },
}


def fixture_pin(*rels):
    """DoF #1 (provenance): hash-pin the EXE the decode rests on, so the finding
    cannot silently drift onto a different image."""
    import hashlib
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out
def load_functions():
    doc = json.loads((ROOT / "analysis" / "functions.json").read_text())
    res = []
    for f in doc["functions"]:
        if f.get("space") == "resident":
            res.append((int(f["start"], 16), int(f["end"], 16), f))
    res.sort(key=lambda t: t[:2])
    return res


def load_symbols():
    syms = {}
    for line in (ROOT / "symbols" / "re_symbols.sym").read_text().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            try:
                syms[int(parts[0], 16)] = parts[1].strip()
            except ValueError:
                pass
    return syms


def find_function(funcs, addr):
    lo, hi = 0, len(funcs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        start, end, f = funcs[mid]
        if addr < start:
            hi = mid - 1
        elif addr >= end:
            lo = mid + 1
        else:
            return f
    return None


KNOWN_TABLE_CONSUMERS = {
    # dispatch-site pc -> the decoded table it drives. 0x8004C220 verified in
    # the EXE bytes: sltiu v0,v1,26 (opcode bound) ... lw v0,-0x4D0C(at)
    # [= 0x8001B2F4] ... jr v0.
    0x8004C220: "mover_vm_opcodes",
}


def scan_indirect_sites(exe, funcs, syms):
    """All jr <reg != ra> / jalr sites inside resident censused code."""
    sites = []
    for start, end, f in funcs:
        if f.get("range_type") not in ("code", "thunk"):
            continue
        lo = max(start, EXE_BASE)
        off = lo - EXE_BASE
        for pc in range(lo, min(end, EXE_BASE + len(exe)), 4):
            w = struct.unpack_from("<I", exe, off)[0]
            off += 4
            if (w & 0xFC000000) == 0 and (w & 0x3F) in (0x08, 0x09):
                rs = (w >> 21) & 0x1F
                if (w & 0x3F) == 0x08 and rs == 31:
                    continue                      # jr ra = return
                fname = f.get("name") or syms.get(start)
                sites.append({
                    "pc": f"0x{pc:08X}",
                    "kind": "jalr" if (w & 0x3F) == 0x09 else "jr",
                    "reg": rs,
                    "function_start": f["start"],
                    "function": fname,
                    "table": KNOWN_TABLE_CONSUMERS.get(pc),
                })
    return sites


def main() -> int:
    exe = EXE.read_bytes()
    funcs = load_functions()
    syms = load_symbols()
    out, gaps = {}, []

    for name, spec in TABLES.items():
        off = spec["address"] - EXE_BASE
        targets = []
        for i in range(spec["count"]):
            t = struct.unpack_from("<I", exe, off + i * 4)[0]
            f = find_function(funcs, t)
            entry = {"index": i, "target": f"0x{t:08X}"}
            if f is None or f.get("range_type") not in ("code", "thunk"):
                entry["resolution"] = "NOT A CENSUSED CODE FUNCTION"
                gaps.append(f"{name}[{i}] -> 0x{t:08X} outside censused code")
            else:
                fstart = int(f["start"], 16)
                fname = f.get("name") or syms.get(fstart)
                entry["function_start"] = f["start"]
                entry["name"] = fname
                entry["classification"] = f.get("classification")
                entry["is_entry_point"] = fstart == t
                if not fname:
                    gaps.append(f"{name}[{i}] -> 0x{t:08X} in UNNAMED function "
                                f"{f['start']}")
            targets.append(entry)
        distinct = {e["target"] for e in targets}
        named = sum(1 for e in targets if e.get("name"))
        out[name] = {**{k: (f"0x{v:08X}" if k == "address" else v)
                        for k, v in spec.items()},
                     "distinct_targets": len(distinct),
                     "named_targets": f"{named}/{len(targets)}",
                     "targets": targets}

    sites = scan_indirect_sites(exe, funcs, syms)
    jr_sites = [x for x in sites if x["kind"] == "jr"]
    unattributed = [x for x in jr_sites if not x["table"]]
    doc = {
        "_comment": "Phase-3 WP4 indirect-dispatch map: jump tables decoded "
                    "from the pristine EXE, targets resolved against the "
                    "functions census + symbols. Gaps are computed. "
                    "Regenerate: tools/phase3_dispatch_map.py (needs the "
                    "LOCAL EXE - REBUILD/files/SCUS_942.88).",
        "generated": date.today().isoformat(),
        "exe": {"path": "REBUILD/files/SCUS_942.88", "base": f"0x{EXE_BASE:08X}"},
        "fixture_sha256": fixture_pin("REBUILD/files/SCUS_942.88"),
        "tables": out,
        "not_yet_covered": {
            "object_pointer_list_0x80096B98": "RAM/BSS kind->descriptor table, "
                "populated at load time — enumerate per-scene via the debugger",
            "sfx_dispatch": "SFX trigger dispatch (Canon sfx-replacement) — bind "
                "in the audio campaign",
            "jr_table_decoding": "94 jr-dispatch sites enumerated below still "
                "need their tables located + decoded — the WP4 frontier",
        },
        "indirect_sites": {
            "_comment": "every jr <reg!=ra> / jalr inside resident censused "
                        "code — the computed WP4 bound; jr sites without a "
                        "decoded table are the remaining frontier",
            "total": len(sites),
            "jalr": len(sites) - len(jr_sites),
            "jr_table_dispatch": len(jr_sites),
            "jr_with_decoded_table": len(jr_sites) - len(unattributed),
            "sites": sites,
        },
        "gaps": gaps,
    }
    path = ROOT / "analysis" / "phase3_dispatch_map.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    total = sum(t["count"] for t in TABLES.values())
    print(f"[dispatch] {len(TABLES)} tables, {total} slots decoded; "
          f"{len(gaps)} gaps")
    print(f"[dispatch] indirect sites: {len(sites)} total "
          f"({len(jr_sites)} jr-dispatch, {len(sites) - len(jr_sites)} jalr); "
          f"{len(unattributed)} jr sites without a decoded table")
    for g in gaps:
        print(f"  GAP {g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
