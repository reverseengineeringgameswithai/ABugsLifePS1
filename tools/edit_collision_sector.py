#!/usr/bin/env python3
"""Permanent collision-floor edit for A Bug's Life LEVEL.RAW chunk 32 (§2 / matched-bump).

The runtime collision sector table (`0x800A7E48`, 223 × 0x30) is built by the converter
FUNC_80030F60 from a source-record array in **LEVEL.RAW chunk 32**: stride 0x4c, with the
sector origin (X,Y,Z) at +0x08/+0x0c/+0x10 stored `≫5` (the converter just copies `src≪5`
into the runtime origin). The array is at chunk-32 **local offset 0x36570** (global
decompressed 0xcd248). Origin-Y is the additive floor base — **more-negative = up**; editing
`src+0xc` shifts a sector's floor 1:1 at runtime (G33, live-proven).

This decompresses chunk 32, edits sector origin-Y in place, recompresses ONLY chunk 32 (the
proven codec; ~1.3× balloon — fine via an auto-layout rebuild, by-name file loading tolerates
the LBA shift), splices it back, and writes a new LEVEL.RAW. Dry-run unless --write --out.

Sectors can be selected explicitly (--sector i) or by runtime world XZ (--near-xz X:Z:R).
--delta-y is in **runtime/world units** (converted to src by ≫5); --src-delta-y is raw src.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

import decode_level_raw as DEC
import recompress_level_raw as REC

COLL_CHUNK = 32
SECTOR_LOCAL = 0x36570     # chunk-32-local offset of the sector source array
SECTOR_STRIDE = 0x4c
ORIGIN_X, ORIGIN_Y, ORIGIN_Z = 0x08, 0x0c, 0x10
N_SECTORS = 223


def be32(b, o): return struct.unpack_from(">I", b, o)[0]


def split_chunks(raw: bytes) -> list[tuple[int, int, int, bytes]]:
    """(file_off, decomp_size, comp_size, comp_bytes) per chunk (big-endian word0/word1)."""
    off = 0
    out = []
    while off + 8 <= len(raw):
        w0 = be32(raw, off); w1 = be32(raw, off + 4)
        if w0 == 0xffffffff:
            break
        out.append((off, w0, w1, raw[off:off + 0xe + w1]))
        off += 0xe + w1
    return out


def decompress_coll_chunk(raw: bytes) -> tuple[list, bytearray]:
    chunks = split_chunks(raw)
    if len(chunks) <= COLL_CHUNK:
        raise SystemExit(f"LEVEL.RAW has {len(chunks)} chunks, need >{COLL_CHUNK}")
    return chunks, bytearray(DEC.decompress_chunk(chunks[COLL_CHUNK][3]))


def sectors_in_chunk32(dec_len: int) -> int:
    """How many 0x4c-stride sector records fully fit in chunk 32's decompressed bytes.
    The full 223-sector array SPANS into chunk 33 (sectors >= this index live there and
    are NOT editable by this chunk-32-only tool)."""
    return (dec_len - SECTOR_LOCAL) // SECTOR_STRIDE


def sector_origin(dec: bytes, i: int) -> tuple[int, int, int]:
    o = SECTOR_LOCAL + i * SECTOR_STRIDE
    return struct.unpack_from("<iii", dec, o + ORIGIN_X)


def main() -> int:
    ap = argparse.ArgumentParser(description="Edit LEVEL.RAW chunk-32 collision sector origin-Y.")
    ap.add_argument("raw", type=Path, help="source LEVEL.RAW")
    ap.add_argument("--list", action="store_true", help="list sectors (idx, runtime origin XYZ) and exit")
    ap.add_argument("--sector", action="append", default=[], type=lambda s: int(s, 0),
                    metavar="I", help="target sector index; may repeat")
    ap.add_argument("--near-xz", metavar="X:Z:R", help="target all sectors whose runtime origin XZ is within R")
    ap.add_argument("--delta-y", type=int, default=None, help="origin-Y delta in RUNTIME units (>>5 to src)")
    ap.add_argument("--src-delta-y", type=int, default=None, help="origin-Y delta in raw SRC units")
    ap.add_argument("--write", action="store_true", help="write --out; default dry-run")
    ap.add_argument("--out", type=Path, help="output LEVEL.RAW; required with --write")
    args = ap.parse_args()

    raw = args.raw.read_bytes()
    chunks, dec = decompress_coll_chunk(raw)

    if args.list:
        print(f"chunk {COLL_CHUNK}: {len(dec)} B decompressed; sector array @ local {SECTOR_LOCAL:#x}")
        nfit = sectors_in_chunk32(len(dec))
        print(f"  (sectors 0..{nfit-1} are in chunk 32; sectors {nfit}..222 span into chunk 33 — not editable here)")
        for i in range(nfit):
            x, y, z = sector_origin(dec, i)
            print(f"  sec {i:3d}: src({x},{y},{z})  runtime({x<<5},{y<<5},{z<<5})")
        return 0

    if args.write and args.out is None:
        raise SystemExit("--write requires --out")
    if args.out is not None and args.out.resolve() == args.raw.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")

    # resolve target sectors
    targets = set(args.sector)
    if args.near_xz:
        try:
            xs, zs, rs = args.near_xz.split(":")
            wx, wz, r = int(xs, 0), int(zs, 0), int(rs, 0)
        except ValueError:
            raise SystemExit("--near-xz expects X:Z:R (runtime units)")
        for i in range(sectors_in_chunk32(len(dec))):
            ox, _oy, oz = sector_origin(dec, i)
            if abs((ox << 5) - wx) <= r and abs((oz << 5) - wz) <= r:
                targets.add(i)
    nfit = sectors_in_chunk32(len(dec))
    over = [i for i in targets if i >= nfit]
    if over:
        raise SystemExit(f"sector(s) {over} live in chunk 33 (>= {nfit}); this chunk-32-only tool can't edit them yet")
    if not targets:
        raise SystemExit("no target sectors (use --sector / --near-xz; or --list)")
    if args.delta_y is None and args.src_delta_y is None:
        raise SystemExit("provide --delta-y (runtime) or --src-delta-y (src)")
    src_dy = args.src_delta_y if args.src_delta_y is not None else (args.delta_y >> 5)

    print(f"chunk {COLL_CHUNK}: {len(dec)} B; editing {len(targets)} sector(s), src origin-Y += {src_dy}")
    for i in sorted(targets):
        o = SECTOR_LOCAL + i * SECTOR_STRIDE + ORIGIN_Y
        oy = struct.unpack_from("<i", dec, o)[0]
        struct.pack_into("<i", dec, o, oy + src_dy)
        print(f"  sec {i:3d}: src origin-Y {oy} -> {oy + src_dy}  (runtime {oy<<5} -> {(oy+src_dy)<<5})")

    # recompress only chunk 32, splice back
    header6 = chunks[COLL_CHUNK][3][8:0xe]
    newcomp = REC.compress_chunk(bytes(dec), header6)
    if bytes(DEC.decompress_chunk(newcomp)) != bytes(dec):
        raise SystemExit("recompress round-trip mismatch — refusing")
    coff = chunks[COLL_CHUNK][0]
    old_comp_len = len(chunks[COLL_CHUNK][3])
    new_raw = raw[:coff] + newcomp + raw[coff + old_comp_len:]
    print(f"LEVEL.RAW: {len(raw)} -> {len(new_raw)} ({len(new_raw)-len(raw):+d}; chunk32 comp "
          f"{old_comp_len}->{len(newcomp)}). Rebuild with the AUTO-LAYOUT manifest.")

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(new_raw)
        # re-verify the spliced file decompresses and our edit is present
        rc = split_chunks(new_raw)
        chk = DEC.decompress_chunk(rc[COLL_CHUNK][3])
        for i in sorted(targets):
            if struct.unpack_from("<i", chk, SECTOR_LOCAL + i * SECTOR_STRIDE + ORIGIN_Y)[0] != \
               struct.unpack_from("<i", dec, SECTOR_LOCAL + i * SECTOR_STRIDE + ORIGIN_Y)[0]:
                raise SystemExit(f"verify failed: sector {i} edit not present in spliced file")
        print(f"wrote {args.out} ({len(new_raw)} bytes)")
    else:
        print("dry-run only; no LEVEL.RAW written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
