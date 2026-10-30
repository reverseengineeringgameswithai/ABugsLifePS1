#!/usr/bin/env python3
"""Phase-4 E16 driver: what ARE the pointer-registered LEVEL.RAW chunks?

The LEVEL.RAW loader registers chunks whose subtype marker is 0x28..0x5F by
POINTER into three tables, without interpreting them -- which is why a census
that classifies chunks structurally left 46 of them "unknown". Their format
belongs to whoever reads the tables.

This driver closes that loop. It decompresses every LEVEL*.RAW with the
committed byte-exact codec, selects the pointer-registered chunks, and runs the
compiled C header checker (tools/phase4_e16_image_header.c) over each one. The
layout it checks is not guessed: it is read off the three consumers found by
tools/phase4_e16_table_read_watch.py and disassembled with tools/mips_ea_window.c

    level_texture_stage 0x8003c8bc @0x8003c920 -> level_texture_upload 0x8003cc58
    vram_upload_wait    0x8003c388 @0x8003c3c0 -> LoadImage 0x800628c0
    vram_upload_wait    0x8003c388 @0x8003c5ec -> LoadImage 0x800628c0

All three fetch tbl[marker], then split into two header families: 0x8003c3c0
reads 32-bit fields and takes the payload from +16, while the other two read
u16 fields and take the payload from +12. Both laws are checked here.

Usage: python3 tools/phase4_e16_registered_chunks.py [--out analysis/phase4_e16_registered_chunks.json]
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import decode_level_raw as DEC  # noqa: E402

# marker range -> (table displacement base, which consumer reads it)
TABLE_SPEC = [
    ("markers_0x28_0x2F", 0x8009C170, 0x28, 0x2F, "vram_upload_wait@0x8003c3c0 -> LoadImage"),
    ("markers_0x30_0x57", 0x8009B4E8, 0x30, 0x57, "level_texture_stage@0x8003c920 -> level_texture_upload"),
    ("markers_0x58_0x5F", 0x800A6450, 0x58, 0x5F, "vram_upload_wait@0x8003c5ec -> LoadImage"),
]


def chunks_of(raw: bytes):
    out = bytearray()
    segs = []
    off = 0
    while off + 8 <= len(raw):
        w0 = struct.unpack_from(">I", raw, off)[0]
        w1 = struct.unpack_from(">I", raw, off + 4)[0]
        if w0 == 0xFFFFFFFF:
            break
        a = len(out)
        DEC.decompress_chunk(raw[off:off + 0xE + w1], out)
        segs.append((a, len(out)))
        off += 0xE + w1
    return bytes(out), segs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_registered_chunks.json"))
    ap.add_argument("--tool", default="")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="e16hdr_"))
    tool = args.tool
    if not tool:
        tool = str(tmp / "hdr")
        subprocess.run(["cc", "-O2", "-Werror", "-o", tool,
                        str(ROOT / "tools/phase4_e16_image_header.c")], check=True)

    rows = []
    for p in sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.RAW")):
        key = f"{p.parent.name}/{p.name}"
        try:
            stream, segs = chunks_of(p.read_bytes())
        except Exception as e:                       # noqa: BLE001
            rows.append({"file": key, "ok": False, "reason": str(e)})
            continue
        for cid, (a, b) in enumerate(segs):
            blob = stream[a:b]
            if len(blob) < 4:
                continue
            m = struct.unpack_from("<I", blob, 0)[0]
            if not (0x28 <= m <= 0x5F):
                continue
            cf = tmp / "c.bin"
            cf.write_bytes(blob)
            r = subprocess.run([tool, str(cf), str(cid)], capture_output=True, text=True)
            d = json.loads(r.stdout)
            d["file"] = key
            for name, base, lo, hi, consumer in TABLE_SPEC:
                if lo <= m <= hi:
                    d["table"] = name
                    d["slot_address"] = "0x%08x" % (base + m * 4)
                    d["consumer"] = consumer
            rows.append(d)

    ok = [r for r in rows if r.get("ok")]
    holds = [r for r in ok if r["size_law_holds"]]
    fams = Counter(r["family"] for r in ok)
    depth = Counter(r["depth_bpp"] for r in ok)
    pal = Counter(r["palette_bytes"] for r in ok)
    dims = Counter((r["width"], r["height"]) for r in ok)

    out = {
        "_comment": "Phase-4 E16: the LEVEL.RAW chunks the loader registers BY POINTER "
                    "(markers 0x28..0x5F) and never interprets. Their format is read off "
                    "the three table consumers, then checked against the bytes. "
                    "Regenerate: tools/phase4_e16_registered_chunks.py",
        "generated": str(date.today()),
        "consumers": [{"markers": "0x%02x..0x%02x" % (lo, hi),
                       "table_disp_base": "0x%08x" % base,
                       "true_window": "0x%08x..0x%08x" % (base + lo * 4, base + hi * 4 + 3),
                       "reader": consumer}
                      for name, base, lo, hi, consumer in TABLE_SPEC],
        "slot_addressing": "slot(marker) = DISP_BASE + marker*4 (RAW marker; the "
                           "addiu s4,-lo before the store is only the sltiu bounds check)",
        "format": {
            "family_A_markers_0x28_0x2F": {
                "header": "16 bytes: u32 marker @0, u32 width @+4, u32 height @+8, u32 @+12",
                "pixels": "16bpp direct colour at +16",
                "size_law": "size == 16 + width*height*2",
                "derivation": "the consumer reads `lw v0,4(s4)` / `lw v1,8(s4)` (32-bit) "
                              "and calls LoadImage with `addiu a1,s4,16`",
            },
            "family_B_markers_0x30_0x5F": {
                "header": "12 bytes: u32 marker @0, u16 width @+4, u16 height @+6, "
                          "u16 palette_bytes @+8, u16 depth_flag @+10",
                "palette": "palette_bytes immediately after the header (768 in 43/43)",
                "pixels": "indexed, after the palette; depth_flag 1 = 8bpp, 0 = 4bpp",
                "size_law": "size == 12 + palette_bytes + width*height/(1 if 8bpp else 2)",
                "derivation": "the consumers read `lhu` at +4/+6/+8(/+10) and take the "
                              "payload from +12, then LoadImage / level_texture_upload",
            },
            "why_family_A_looked_malformed": "Read as u16, family A's 32-bit width/height "
                                             "make height and depth_flag look like 0 -- "
                                             "those are the high halves, not real fields.",
            "no_free_parameters": "Both laws come from the consumers, not from fitting "
                                  "sizes; each either holds exactly or does not.",
        },
        "counts": {
            "chunks": len(ok),
            "size_law_holds": len(holds),
            "by_family": dict(fams),
            "by_depth_bpp": {str(k): v for k, v in sorted(depth.items())},
        },
        "upload_path_family_B_2026-08-04": {
            "_comment": "Read from level_texture_stage 0x8003C8BC end to end with "
                        "tools/mips_ea_window.c. Closes how the 4bpp/8bpp split reaches "
                        "this consumer -- it DOES read the +10 flag, 0x298 bytes past the "
                        "table fetch.",
            "depth_flag_consumer": "lh v1,10(s1) at 0x8003CB54. flag != 1 -> rect width "
                                   "w = (w+3)>>2 (4 pixels per 16-bit VRAM word = 4bpp); "
                                   "flag == 1 -> w = w>>1 (2 pixels per word = 8bpp). It "
                                   "rewrites the VRAM RECT width by pixel depth.",
            "CORRECTION_earlier_lead": "I named `andi v0,v0,3` at 0x8003C954 as the "
                                       "4bpp/8bpp lead. WRONG -- it is `or v0,s0,a2` then "
                                       "`andi v0,v0,3`, an ALIGNMENT test choosing between "
                                       "a word copy and the lwl/lwr path. The real answer "
                                       "is the direct read at 0x8003CB54.",
            "rect": "A RECT is built at 0x80089848 (x @+0, y @+2, w @+4 = 0x8008984C, "
                    "h @+6 = 0x8008984E) and passed to LoadImage 0x800628C0 as a0.",
            "pixel_source": "a1 = chunk + 12 + (palette_bytes & ~1)  -- the same "
                            "`12 + round_down_even(u16@+8)` rule already pinned for the "
                            "texture-page path, confirmed here independently.",
            "palette_pipeline": "The 768-byte palette is copied to a stack buffer (sp+32) "
                                "and walked THREE BYTES AT A TIME -- code-level proof of "
                                "256 x RGB888 -- scaling each component to 75% via "
                                "(v*96)>>7.",
            "colour_key": "Entries matching R<5 AND G>=250 AND B<5 are left UNSCALED "
                          "(0x8003C9F0..0x8003CA28). That is the pure-green transparency "
                          "key: in marker 0x30 exactly ONE palette entry matches (index 0 "
                          "= (0,255,0)), it is what all four image corners use, and it is "
                          "50% of the image. Scaling it would turn 255 into 191 and break "
                          "the key.",
            "two_clut_uploads": "level_texture_upload 0x8003CC58 is called twice -- once "
                                "with the chunk's own palette (0x8003C944) and once with "
                                "the 75%-scaled stack copy (0x8003CAE0) -- so a normal and "
                                "a dimmed CLUT are both staged. The dimmed one being a "
                                "menu 'unselected' variant is a READING, not established.",
        },
        "visual_confirmation": {
            "method": "tools/phase4_e16_decode_registered_image.py renders a chunk with "
                      "the consumer-derived layout; a wrong header reading produces noise, "
                      "so recognisable art is an end-to-end confirmation of the format "
                      "(including the palette being 256 x RGB888 on disc, not RGB555).",
            "LEVEL00/LEVEL.RAW marker 0x30": "menu icon -- a radio with music notes on a "
                                             "branch over a green key colour (160x132 8bpp)",
            "LEVEL00/LEVEL.RAW marker 0x43": "memory-card UI text atlas -- 'please wait / "
                                             "load / save / exit / 1 block used / not an "
                                             "\"a bug's life\" save game / press O to load' "
                                             "(256x256 8bpp)",
            "LEVEL00/LEVEL3.RAW marker 0x28": "the title screen -- 320x256 16bpp "
                                              "Disney/Pixar 'a bug's life' leaf logo",
            "note": "Renders are NOT committed: the source art is copyrighted. "
                    "Regenerate locally with the decoder.",
        },
        "palette_bytes_histogram": {str(k): v for k, v in sorted(pal.items())},
        "dimensions_histogram": {f"{w}x{h}": c for (w, h), c in sorted(dims.items())},
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"pointer-registered chunks: {len(ok)}")
    print(f"  size law holds exactly: {len(holds)}/{len(ok)}")
    print(f"  families: {dict(fams)}")
    print(f"  depth:    {dict(depth)}")
    print(f"  palette bytes: {dict(pal)}")
    print(f"  distinct dimensions: {len(dims)}")
    for r in ok:
        if not r["size_law_holds"]:
            print(f"  MISMATCH {r['file']} cid={r['chunk_id']} marker={r['marker']} "
                  f"size={r['size']} expected={r['expected_size']} law={r['size_law']}")
    print(f"wrote {args.out}")
    return 0 if len(holds) == len(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
