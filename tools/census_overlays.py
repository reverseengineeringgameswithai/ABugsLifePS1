#!/usr/bin/env python3
"""Census every OVERLAY blob for accesses to a given RAM address.

WHY THIS EXISTS
---------------
The B06/B08 frontier was rebuilt over the resident EXE, and a reviewer correctly
pointed out that resident-image completeness is not whole-game completeness: the
per-level `LEVEL*.BIN` and the shared `MEMORY.BIN` are CdRead-loaded code that runs
in the same address space and can touch the same player state. None of it had ever
been censused.

Overlays reuse one RAM window (Region A for the per-level swap buffer, Region B for
MEMORY.BIN), so an address inside an overlay is only meaningful given which overlay
is loaded — but an access to a RESIDENT address like 0x800A657E is unambiguous no
matter which one is resident, which is exactly what this looks for.

METHOD
------
Same may-constant value analysis as tools/census_address.py, but over a raw blob
mapped at its configured base VA, with the whole blob treated as one region (they
are small — 1.6 KB to 36 KB). Reported per overlay:

  * accesses whose base resolves to the target
  * `lui 0x800A`-rooted address material that the value analysis could not turn into
    a concrete access (a weaker signal, listed so a human can look)
  * the residual: accesses whose base is not derivable from the instruction stream

USAGE
    tools/census_overlays.py 0x800A657E --json analysis/phase4_b06_b08_census_overlays.json
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import yaml

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "census_address", Path(__file__).with_name("census_address.py"))
_ca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ca)

REGS, TOP, s16 = _ca.REGS, _ca.TOP, _ca.s16
LOADS, STORES, WIDTH = _ca.LOADS, _ca.STORES, _ca.WIDTH


class Blob:
    """Minimal Image-alike: one region covering the whole blob."""

    def __init__(self, path: Path, base: int, skip: int = 0):
        self.text = path.read_bytes()[skip:]
        self.base = base + skip
        self.end = self.base + (len(self.text) & ~3)
        self.name = str(path)
        self.funcs = [(self.base, path.name, self.end - self.base)]
        self.starts = [self.base]

    def word(self, va):
        return struct.unpack_from("<I", self.text, va - self.base)[0]

    def owner(self, va):
        return self.funcs[0]

    def extent(self, start):
        return self.end


def scan(blob: Blob, targets: set):
    """Block-based may-constant scan over the whole blob."""
    leaders = sorted(_ca.block_starts(blob, blob.base, blob.end))
    bounds = {b: (leaders[i + 1] if i + 1 < len(leaders) else blob.end)
              for i, b in enumerate(leaders)}
    state = {b: {r: set() for r in REGS} for b in leaders}
    for r in REGS:
        state[blob.base][r] = TOP
    state[blob.base]["zero"] = {0}
    state[blob.base]["sp"] = {_ca.STACK_BASE}

    hits, unresolved = [], []
    work, seen = [blob.base], 0
    while work and seen < 20000:
        b = work.pop()
        seen += 1
        st = {r: (TOP if state[b].get(r) is TOP else set(state[b].get(r, set()))) for r in REGS}
        blo, bhi = b, bounds[b]
        calls = []
        pc = blo
        while pc < bhi:
            w = blob.word(pc)
            op, funct = w >> 26, w & 0x3F
            is_call = (op == 3) or (op == 0 and funct == 0x09)
            _ca.transfer(blob, pc, st, hits, unresolved, targets, calls, blo, bhi)
            if is_call and pc + 4 < bhi:
                _ca.transfer(blob, pc + 4, st, hits, unresolved, targets, calls, blo, bhi)
                for r in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 31):
                    st[REGS[r]] = TOP
                pc += 8
                continue
            pc += 4
        succs = []
        if bhi in state:
            succs.append(bhi)
        for pc in range(blo, bhi, 4):
            ww = blob.word(pc)
            o, rt2, im = ww >> 26, (ww >> 16) & 31, ww & 0xFFFF
            if o in (4, 5, 6, 7) or (o == 1 and rt2 in (0, 1, 16, 17)):
                t = pc + 4 + (s16(im) << 2)
                if t in state:
                    succs.append(t)
            elif o == 2:
                t = (pc & 0xF0000000) | ((ww & 0x3FFFFFF) << 2)
                if t in state:
                    succs.append(t)
        for d in succs:
            if _ca.merge_state(state[d], st):
                work.append(d)
    return hits, unresolved


def address_material(blob: Blob, page: int):
    """Every `lui rX, page` in the blob — weak evidence that the blob computes an
    address in that 64 KB page at all. If a blob contains none, it cannot reach the
    target by a computed absolute address."""
    out = []
    for pc in range(blob.base, blob.end, 4):
        w = blob.word(pc)
        if (w >> 26) == 0x0F and (w & 0xFFFF) == page:
            out.append("0x%08X" % pc)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("address")
    ap.add_argument("--bytes", type=int, default=2)
    ap.add_argument("--config", type=Path, default=Path("config/overlays.yml"))
    ap.add_argument("--extra", action="append", default=[],
                    help="BLOB:BASE for a blob not in overlays.yml, e.g. "
                         "REBUILD/files/BITS/MEMORY.BIN:0x800b5788")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    addr = int(args.address, 0)
    targets = set(range(addr, addr + args.bytes))
    page = (addr >> 16) & 0xFFFF

    cfg = yaml.safe_load(args.config.read_text())
    blobs = []
    for name, spec in (cfg.get("overlays") or {}).items():
        blobs.append((name, Path(spec["blob"]), int(spec["base"])))
    # LEVEL*.BIN carry a 4-byte ID word then code; every per-level blob shares Region A.
    seen_paths = {str(b[1]) for b in blobs}
    region_a = int(cfg["region_a"])
    for p in sorted(Path("REBUILD/files").glob("LEVEL*/LEVEL*.BIN")):
        if str(p) not in seen_paths:
            blobs.append((f"{p.parent.name}_{p.stem}", p, region_a))
    for spec in args.extra:
        path, base = spec.rsplit(":", 1)
        blobs.append((Path(path).stem, Path(path), int(base, 0)))

    seen_blob = set()
    dedup = []
    for name, path, base in sorted(blobs, key=lambda x: x[0]):
        key = (str(path), base)
        if key in seen_blob:
            continue          # overlays.yml and --extra can name the same blob
        seen_blob.add(key)
        dedup.append((name, path, base))
    blobs = dedup

    results, total_hits = [], 0
    for name, path, base in blobs:
        if not path.exists():
            results.append({"overlay": name, "blob": str(path), "error": "missing"})
            continue
        blob = Blob(path, base)
        hits, unresolved = scan(blob, targets)
        seen = {}
        for h in hits:
            seen.setdefault(h["pc"], h)
        hits = sorted(seen.values(), key=lambda x: x["pc"])
        total_hits += len(hits)
        results.append({
            "overlay": name, "blob": str(path), "base": "0x%08X" % base,
            "size": len(blob.text),
            "hits": hits,
            "lui_page_material": len(address_material(blob, page)),
            "unresolved_base_accesses": len(unresolved),
        })

    out = {"target": args.address, "bytes": args.bytes,
           "blobs_scanned": len([r for r in results if "error" not in r]),
           "total_hits": total_hits, "overlays": results,
           "_meaning": ("`hits` are overlay instructions that access the target. "
                        "`lui_page_material` counts `lui rX, 0x%04X` in the blob: zero means "
                        "the blob never even forms an address in that 64 KB page by the "
                        "absolute route, which is a meaningful negative. "
                        "`unresolved_base_accesses` is the residual -- accesses through a "
                        "pointer loaded from memory, which this cannot exclude." % page)}

    print("target %s across %d overlay blobs -- total hits: %d"
          % (args.address, out["blobs_scanned"], total_hits))
    for r in results:
        if "error" in r:
            print("  %-22s MISSING %s" % (r["overlay"], r["blob"]))
            continue
        flag = "  <-- HITS" if r["hits"] else ""
        print("  %-22s %6d B  hits=%-3d lui-page=%-4d unresolved=%-5d%s"
              % (r["overlay"], r["size"], len(r["hits"]), r["lui_page_material"],
                 r["unresolved_base_accesses"], flag))
        for h in r["hits"]:
            print("        %s %s %s" % (h["kind"], h["pc"], h["insn"]))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1) + "\n")
        print("wrote", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
