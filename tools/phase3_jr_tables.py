#!/usr/bin/env python3
"""Phase-3 WP4: recover the jump table behind every resident `jr` dispatch site.

The dispatch map enumerated 95 `jr <reg>` sites and could attribute exactly one
(the mover-VM's) to a decoded table. The other 94 were the honest frontier. They
are not mysterious, though — they are a compiler idiom, and it can be sliced:

    sltiu vX, vY, N          # bound: N entries
    sll   vZ, vY, 2          # scale by 4
    lui   at, HI             # \\ table base
    addu  at, at, vZ         # /
    lw    vR, LO(at)         # load the handler
    jr    vR

So: for each `jr` site, walk BACKWARD through the containing function looking for
the `lw` that feeds the jumped-to register, recover the table base from the
lui/addiu pair that feeds that `lw`, and take the entry count from the nearest
dominating `sltiu` bound. Then decode the table and resolve every target against
the function census + symbols.

Everything is a COMPUTED verdict: a site whose slice does not close is reported
with the reason it failed, never quietly dropped. That distinction matters — an
undecoded site is a real gap, and a wrongly-decoded one is worse.

Usage: python3 tools/phase3_jr_tables.py   (needs the local pristine EXE)
Output: analysis/phase3_jr_tables.json
"""
from __future__ import annotations

import hashlib
import json
import struct
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
EXE_BASE = 0x8000F800
RAM_LO, RAM_HI = 0x80000000, 0x80200000
MAX_BACK = 80          # instructions to walk back from the jr


def fixture_pin(*rels):
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def load_functions():
    doc = json.loads((ROOT / "analysis" / "functions.json").read_text())
    res = [(int(f["start"], 16), int(f["end"], 16), f)
           for f in doc["functions"] if f.get("space") == "resident"]
    res.sort(key=lambda t: t[:2])
    return res


def load_symbols():
    syms = {}
    for line in (ROOT / "symbols" / "re_symbols.sym").read_text().splitlines():
        p = line.split(None, 1)
        if len(p) == 2:
            try:
                syms[int(p[0], 16)] = p[1].strip()
            except ValueError:
                pass
    return syms


def find_function(funcs, addr):
    lo, hi = 0, len(funcs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        s, e, f = funcs[mid]
        if addr < s:
            hi = mid - 1
        elif addr >= e:
            lo = mid + 1
        else:
            return s, e, f
    return None


def word(exe, va):
    return struct.unpack_from("<I", exe, va - EXE_BASE)[0]


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def last_defs(exe, fstart, pc):
    """Forward-scan the function to `pc`, recording the LAST instruction that
    defines each register. A windowed backward walk misses jump-island bases,
    which are set once far above the loop — this does not."""
    defs = {}
    for va in range(fstart, pc, 4):
        i = word(exe, va)
        op = i >> 26
        fn = i & 0x3F
        if op == 0:                                   # R-type: writes rd
            if fn in (0x08, 0x09):                    # jr / jalr
                continue
            rd = (i >> 11) & 0x1F
            if rd:
                defs[rd] = (va, i, "R")
        elif op in (0x08, 0x09, 0x0C, 0x0D, 0x0E, 0x0F,   # addi/addiu/andi/ori/xori/lui
                    0x20, 0x21, 0x23, 0x24, 0x25, 0x0A, 0x0B):  # loads / slti(u)
            rt = (i >> 16) & 0x1F
            if rt:
                defs[rt] = (va, i, "I")
        elif op == 0x03:                              # jal writes ra
            defs[31] = (va, i, "J")
    return defs


def classify(exe, pc, fstart):
    """What KIND of dispatch is this `jr`? Returns (kind, detail)."""
    reg = (word(exe, pc) >> 21) & 0x1F
    defs = last_defs(exe, fstart, pc)

    seen = set()
    cur = reg
    for _ in range(8):                    # follow `move` chains
        if cur not in defs:
            return "unresolved", "the jr register is never defined in this function"
        va, i, _ = defs[cur]
        op, fn = i >> 26, i & 0x3F
        if op == 0x23:                                        # lw -> a TABLE
            return "table", (va, (i >> 21) & 0x1F, s16(i & 0xFFFF))
        if op == 0 and fn == 0x00:                            # sll -> scaled index
            return "computed", f"jr (index << {(i >> 6) & 0x1F}) — jump into code"
        if op == 0 and fn in (0x21, 0x25):                    # addu/or
            rs, rt = (i >> 21) & 0x1F, (i >> 16) & 0x1F
            if 0 in (rs, rt):                                 # move: follow it
                nxt = rs or rt
                if nxt in seen:
                    break
                seen.add(nxt)
                cur = nxt
                continue
            # base + something: if EITHER operand is a shifted index, it is a
            # jump INTO CODE (unrolled loop / jump island), not a table.
            for r in (rs, rt):
                if r in defs:
                    _, i2, _ = defs[r]
                    if (i2 >> 26) == 0 and (i2 & 0x3F) == 0x00:
                        return "computed", ("jr base + (index << "
                                            f"{(i2 >> 6) & 0x1F}) — unrolled-loop / "
                                            "jump-island dispatch, no table exists")
            return "unresolved", "jr register = addu of two non-shifted values"
        if op in (0x0F, 0x09):                                # lui/addiu constant
            return "computed", "jr to a constant address materialised in-function"
        return "unresolved", f"jr register defined by opcode {op:#04x}"
    return "unresolved", "move chain did not terminate"


def find_lui(exe, fstart, before_va, reg, depth=0):
    """The HI half of a table base. `at` is typically built as
    `lui at, HI` ... `addu at, at, index` — so when the last definition of the
    base register is that addu, the lui must be resolved from BEFORE it, not at
    the same point (where `at` resolves to the addu itself)."""
    if depth > 4 or before_va <= fstart:
        return None
    defs = last_defs(exe, fstart, before_va)
    if reg not in defs:
        return None
    va, i, _ = defs[reg]
    if (i >> 26) == 0x0F:                                  # lui reg, HI
        return (i & 0xFFFF) << 16
    if (i >> 26) == 0 and (i & 0x3F) in (0x21, 0x25):      # addu/or reg, X, Y
        for r in ((i >> 21) & 0x1F, (i >> 16) & 0x1F):
            if r:
                hi = find_lui(exe, fstart, va, r, depth + 1)
                if hi is not None:
                    return hi
    return None


def slice_from_lw(exe, pc, fstart, lw):
    """Recover (table_base, count) from the `lw` that feeds the jr."""
    lw_va, base_reg, lw_imm = lw
    hi_val = find_lui(exe, fstart, lw_va, base_reg)
    if hi_val is None:
        return None, "table base not formed by a lui (gp-relative or passed in)"
    table = hi_val + lw_imm
    if not (RAM_LO <= table < RAM_HI):
        return None, f"recovered base 0x{table:08X} is not in RAM"
    count = None
    for va in range(pc - 4, max(fstart, pc - MAX_BACK * 4) - 1, -4):
        i = word(exe, va)
        if (i >> 26) == 0x0B:                              # sltiu = the bound
            count = i & 0xFFFF
            break
    return (table, count), None


def main() -> int:
    exe = EXE.read_bytes()
    funcs = load_functions()
    syms = load_symbols()
    dmap = json.loads(
        (ROOT / "analysis" / "phase3_dispatch_map.json").read_text())
    sites = [s for s in dmap["indirect_sites"]["sites"] if s["kind"] == "jr"]

    decoded, failed, computed = {}, {}, {}
    for site in sites:
        pc = int(site["pc"], 16)
        fn = find_function(funcs, pc)
        if fn is None:
            failed[site["pc"]] = {"function": site.get("function"),
                                  "reason": "pc outside any censused function"}
            continue
        fstart, _, _ = fn
        kind, detail = classify(exe, pc, fstart)
        if kind == "computed":
            computed[site["pc"]] = {"function": site.get("function"),
                                    "reason": detail}
            continue
        if kind == "unresolved":
            failed[site["pc"]] = {"function": site.get("function"),
                                  "reason": detail}
            continue
        got, why = slice_from_lw(exe, pc, fstart, detail)
        if got is None:
            failed[site["pc"]] = {"function": site.get("function"), "reason": why}
            continue
        table, count = got
        if not count or count > 128:
            failed[site["pc"]] = {
                "function": site.get("function"),
                "table": f"0x{table:08X}",
                "reason": f"no plausible sltiu bound (got {count})"}
            continue
        targets = []
        ok = True
        for i in range(count):
            va = table + i * 4
            if not (EXE_BASE <= va < EXE_BASE + len(exe)):
                ok = False
                break
            t = word(exe, va)
            f = find_function(funcs, t)
            name = None
            if f:
                name = f[2].get("name") or syms.get(f[0])
            if not f or f[2].get("range_type") not in ("code", "thunk"):
                ok = False
            targets.append({"index": i, "target": f"0x{t:08X}", "name": name})
        if not ok:
            failed[site["pc"]] = {
                "function": site.get("function"), "table": f"0x{table:08X}",
                "reason": "a decoded entry does not land in censused code — "
                          "the slice is probably wrong, so it is NOT reported "
                          "as a table"}
            continue
        decoded[site["pc"]] = {
            "function": site.get("function"),
            "table": f"0x{table:08X}",
            "entries": count,
            "distinct_targets": len({t["target"] for t in targets}),
            "named_targets": sum(1 for t in targets if t["name"]),
            "targets": targets,
        }

    doc = {
        "_comment": "Phase-3 WP4: jump tables recovered by BACKWARD-SLICING each "
                    "resident `jr` dispatch site (sltiu bound / sll / lui+addu base "
                    "/ lw / jr). A slice that does not close, or that decodes an "
                    "entry outside censused code, is reported as FAILED with its "
                    "reason — never silently dropped, and never reported as a table "
                    "we are unsure of. Regenerate: tools/phase3_jr_tables.py",
        "generated": date.today().isoformat(),
        "fixture_sha256": fixture_pin("REBUILD/files/SCUS_942.88"),
        "jr_sites": len(sites),
        "decoded_sites": len(decoded),
        "computed_code_jump_sites": len(computed),
        "unresolved_sites": len(failed),
        "classification": {
            "_comment": "A `jr` is not automatically a table dispatch. Two thirds of "
                        "them here jump INTO CODE (base + index<<k — unrolled loops / "
                        "jump islands, heavy in the GTE paths). Those have NO table to "
                        "decode, and reporting them as 'undecoded tables' would have "
                        "been a lie about the size of the frontier.",
            "table_dispatch": len(decoded),
            "computed_code_jump": len(computed),
            "unresolved": len(failed),
        },
        "computed_code_jumps": computed,
        "distinct_tables": len({d["table"] for d in decoded.values()}),
        "total_entries_decoded": sum(d["entries"] for d in decoded.values()),
        "decoded": decoded,
        "failed": failed,
    }
    path = ROOT / "analysis" / "phase3_jr_tables.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[jr-tables] {len(sites)} jr sites: {len(decoded)} TABLE DISPATCHES "
          f"decoded ({doc['distinct_tables']} tables, "
          f"{doc['total_entries_decoded']} entries); "
          f"{len(computed)} COMPUTED CODE JUMPS (no table exists); "
          f"{len(failed)} unresolved")
    from collections import Counter
    for reason, n in Counter(f["reason"].split("(")[0].strip()
                             for f in failed.values()).most_common():
        print(f"    {n:3d}  {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
