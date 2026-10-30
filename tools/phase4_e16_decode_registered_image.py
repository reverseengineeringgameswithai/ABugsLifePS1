#!/usr/bin/env python3
"""Decode a pointer-registered LEVEL.RAW chunk (marker 0x28..0x5F) to a PNG.

This is the end-to-end check on the format that tools/phase4_e16_image_header.c
derives from the three table consumers: if the layout is right, the bytes render
as recognisable art; if it is wrong, they render as noise. Confirmed on the
retail data -- marker 0x30 is a menu icon, 0x43 is the memory-card UI text atlas
("please wait / load / save / exit / not an 'a bug's life' save game / press O
to load"), and family-A marker 0x28 is the 320x256 title screen.

    FAMILY A (markers 0x28..0x2F): u32 w @+4, u32 h @+8, 16bpp BGR555 at +16.
    FAMILY B (markers 0x30..0x5F): u16 w @+4, h @+6, palette_bytes @+8,
        depth_flag @+10; palette (768 B = 256 x RGB888) at +12, then indexed
        pixels -- 8bpp when depth_flag == 1, 4bpp (low nibble first) when 0.

The palette being RGB888 rather than the PS1's native RGB555 is a property of
the ON-DISC resource, not of VRAM: the loader converts on upload. It is asserted
here because it is what makes the images decode correctly.

No output is committed -- the source art is copyrighted. Render locally to look.

Usage:
  python3 tools/phase4_e16_decode_registered_image.py --file LEVEL00/LEVEL.RAW \\
      --marker 0x43 --out /tmp/m43.png
  python3 tools/phase4_e16_decode_registered_image.py --list
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import decode_level_raw as DEC  # noqa: E402


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


def decode(blob: bytes):
    """Return (PIL.Image, description) for one decompressed chunk."""
    from PIL import Image

    marker = struct.unpack_from("<I", blob, 0)[0]
    if 0x28 <= marker <= 0x2F:
        w, h = struct.unpack_from("<II", blob, 4)
        px = blob[16:16 + w * h * 2]
        rgb = bytearray()
        for i in range(0, len(px), 2):
            v = px[i] | (px[i + 1] << 8)
            rgb += bytes(((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3))
        return Image.frombytes("RGB", (w, h), bytes(rgb)), f"{w}x{h} 16bpp"

    w, h, pal_bytes, depth_flag = struct.unpack_from("<HHHH", blob, 4)
    pal = blob[12:12 + pal_bytes]
    body = blob[12 + pal_bytes:]
    if depth_flag == 1:
        idx = body[:w * h]
    else:                                    # 4bpp, low nibble first
        idx = bytearray()
        for byte in body[:w * h // 2]:
            idx.append(byte & 0xF)
            idx.append(byte >> 4)
        idx = bytes(idx[:w * h])
    img = Image.new("P", (w, h))
    img.putdata(idx)
    flat = []
    for i in range(256):
        flat += list(pal[i * 3:i * 3 + 3]) if (i * 3 + 3) <= len(pal) else [0, 0, 0]
    img.putpalette(flat)
    return img.convert("RGB"), f"{w}x{h} {8 if depth_flag == 1 else 4}bpp indexed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="LEVEL00/LEVEL.RAW",
                    help="path under REBUILD/files, e.g. LEVEL00/LEVEL.RAW")
    ap.add_argument("--marker", default="0x43")
    ap.add_argument("--out", default="")
    ap.add_argument("--list", action="store_true",
                    help="list every pointer-registered chunk instead of decoding")
    args = ap.parse_args()

    if args.list:
        for p in sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.RAW")):
            try:
                stream, segs = chunks_of(p.read_bytes())
            except Exception:                    # noqa: BLE001
                continue
            for cid, (a, b) in enumerate(segs):
                blob = stream[a:b]
                if len(blob) < 16:
                    continue
                m = struct.unpack_from("<I", blob, 0)[0]
                if 0x28 <= m <= 0x5F:
                    print(f"{p.parent.name}/{p.name:12s} chunk {cid:3d}  marker 0x{m:02x}  "
                          f"{len(blob):8d} B")
        return 0

    src = ROOT / "REBUILD/files" / args.file
    want = int(args.marker, 0)
    stream, segs = chunks_of(src.read_bytes())
    for cid, (a, b) in enumerate(segs):
        blob = stream[a:b]
        if len(blob) >= 16 and struct.unpack_from("<I", blob, 0)[0] == want:
            img, desc = decode(blob)
            out = args.out or f"/tmp/e16_m{want:02x}.png"
            img.save(out)
            print(f"{args.file} chunk {cid} marker 0x{want:02x}: {desc} -> {out}")
            return 0
    print(f"marker 0x{want:02x} not found in {args.file}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
