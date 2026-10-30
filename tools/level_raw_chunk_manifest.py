#!/usr/bin/env python3
"""Emit a METADATA-ONLY role manifest for LEVEL01/LEVEL.RAW's 69 chunks (GAP-0022 / GAP-0005).

Reads the tracked chunk index + the (local, gitignored) decompressed cache and classifies each
chunk by its decompressed content marker. Output is metadata only — sizes, markers, roles, and a
sha256 PREFIX fingerprint — never copyrighted payload bytes ([[Preservation Policy]]).

Classification (evidence: decompressed-content markers, 2026-06-20):
  Region A textures  : marker layout "<page_id u32> 0001 0001 0003 ..." (fixed VRAM frames)
  Region B sprites   : marker u16@0 0x22 (sprite) / 0x24 (cell) ; 0x23 = seed table (chunk 31)
  Region C geometry  : marker u16@0 0x101 mesh-DEFINITION / 0x102 mesh-PAYLOAD (paired by idx@+4),
                       0x103 = collision+sky (chunk 32), 0x104 = chunk 33

Usage:
    python3 tools/level_raw_chunk_manifest.py [--raw <LEVEL.RAW>] [--json out.json] [--md]
Defaults resolve from tools/_env.py (ABL_DIR). Requires the decompressed cache
(tools/LEVEL_RAW_decompressed/, regenerate with dump_level_raw.py) — local media, not CI.
"""
from __future__ import annotations
import argparse, hashlib, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from _env import ABL_DIR  # noqa
except Exception:
    ABL_DIR = os.path.dirname(HERE)

CACHE = os.path.join(HERE, "LEVEL_RAW_decompressed")
IDX = os.path.join(CACHE, "chunk_index.json")
DECOMP = os.path.join(CACHE, "LEVEL.RAW.decompressed")


def classify(marker: int, decomp_size: int, idx4: int):
    """Return (region, subtype, role, confidence)."""
    if marker in (0x101,):
        if idx4 == 0:
            return ("C", "0x101", "master/world mesh DEFINITION (sub-mesh table)", "CONFIRMED-fmt")
        # u2-C 2026-07-09: format-validated across ALL 11 LEVEL.RAW files — 21/21
        # 0x101 chunks parse (submesh count @+0x0a in range), same grammar as the
        # confirmed master DEF.
        return ("C", "0x101", f"per-object mesh DEFINITION (obj 0x{idx4:x})", "CONFIRMED-fmt")
    if marker == 0x102:
        if idx4 == 0:
            return ("C", "0x102", "master/world mesh PAYLOAD (verts+gouraud) = buffer 0x8012c1d0", "CONFIRMED-fmt")
        # u2-C: 13/16 payloads directly chain a 0x101/0x102 DEF group; 3 follow
        # 0x104/0x23 containers (pairing broader than strict adjacency) — stays
        # LIKELY until the 0x104-adjacent cases are consumer-traced.
        return ("C", "0x102", f"per-object mesh PAYLOAD (obj 0x{idx4:x})", "LIKELY")
    if marker == 0x103:
        return ("C", "0x103", "collision plane geom (0x800c1690) + sky color table (0x800c1688)", "CONFIRMED")
    if marker == 0x104:
        # The collision sector array starts at chunk-32 +0x36570 with 0x4c-byte
        # records. Chunk 32 ends four bytes into sector 189, so chunk 33 begins
        # at sector189+4; its apparent 0x104 marker is that record field, not an
        # independent format tag. The first 0xa14 bytes complete sectors 189..222.
        return ("C", "collision-tail",
                "collision sector-source tail (sectors 189-222; first 0xa14 bytes)",
                "CONFIRMED")
    if marker == 0x22:
        # u2-C 2026-07-09: header pinned + format-validated 134/134 across ALL 11
        # levels: [u32 0x22][u32 sprite-id][u16 W][u16 H] then pixel data (dims
        # 24x24 glyphs, 32x48, 16x16... — matches the documented FLIK glyph tiles).
        return ("B", "0x22", "2D sprite ([u32 id @+4][u16 W @+8][u16 H @+10] + pixels)", "CONFIRMED-fmt")
    if marker == 0x23:
        return ("B", "0x23", "seed table (chunk 31; live-proven via G32 disc edit)", "CONFIRMED")
    if marker == 0x24:
        return ("B", "0x24", "2D cell/large sprite", "LIKELY")
    # Region A textures: small page id then the fixed 0001 0001 0003 texture header
    if decomp_size in (33548, 17164):
        return ("A", "tex", "VRAM texture page (id + WxH + bpp + CLUT + pixels)", "CONFIRMED-fmt")
    return ("?", f"0x{marker:x}", "UNKNOWN", "Unknown")


def build():
    idx = json.load(open(IDX))
    dec = open(DECOMP, "rb").read()
    rows = []
    for r in idx:
        do, w0, w1 = r["decomp_off"], r["word0"], r["word1"]
        body = dec[do:do + w0]
        marker = struct.unpack_from("<H", dec, do)[0]
        idx4 = struct.unpack_from("<I", dec, do + 4)[0]
        region, subtype, role, conf = classify(marker, w0, idx4)
        rows.append({
            "chunk": r["chunk"], "comp": w1, "decomp": w0,
            "ratio": round(w0 / w1, 2) if w1 else None,
            "region": region, "marker": f"0x{marker:x}", "subtype": subtype,
            "idx4": idx4, "role": role, "confidence": conf,
            "sha256_16": hashlib.sha256(body).hexdigest()[:16],
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(DECOMP):
        print(f"missing {DECOMP}; run dump_level_raw.py first (local media)", file=sys.stderr)
        return 2
    rows = build()
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
        print(f"wrote {a.json} ({len(rows)} chunks)")
    if a.md or not a.json:
        from collections import Counter
        print(f"| ch | region | marker | comp | decomp | ratio | role | conf |")
        print(f"|---:|:--:|:--:|---:|---:|--:|---|---|")
        for r in rows:
            print(f"| {r['chunk']} | {r['region']} | {r['marker']} | {r['comp']} | {r['decomp']} | {r['ratio']} | {r['role']} | {r['confidence']} |")
        print("\nregion counts:", dict(Counter(r["region"] for r in rows)))
        print("classified (non-Unknown):", sum(1 for r in rows if r["confidence"] != "Unknown"), "/", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
