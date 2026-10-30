#!/usr/bin/env python3
"""Edit an oriented COLLISION PLANE (wall/slope) in A Bug's Life LEVEL.RAW chunk 32 (§2.2).

Besides the flat per-sector floor (`edit_collision_sector.py`, origin-Y), LEVEL collision
has a small set of oriented planes — the walls/slopes — resolved by the SWEPT collision
function FUNC_800345CC (see src_re/collision_plane_resolver_800345cc.c). Each plane is a
0x20-byte record in chunk 32:

    s16 normal @ +0x00/+0x02/+0x04   (|normal| == 0x4000 fixed-point 1.0 — keep ~unit)
    s16 ref    @ +0x06/+0x08/+0x0a   (a point on the plane, sector-local; value is <<5 at use)

Tilt the normal to change a wall/slope angle; move the ref to reposition it; zero the normal
to disable a plane. The planes are SCATTERED in chunk 32 and located via runtime tables, so
get their chunk-32 offsets first with **tools/probe_collision_planes.py** (live), then edit
here by offset. LEVEL01 (live-probed) planes: 0x1c420, 0x1cc30, 0x1cc50, 0x1cc70 (sector 119),
0x303f8, 0x30418 (sector 166).

Recompresses ONLY chunk 32 (~1.3x balloon) and splices a new LEVEL.RAW; rebuild the disc with
tools/build_autolayout_disc.py (the chunk-32 rebuild path is in-game proven). Dry-run unless
--write --out.

Examples:
  # show a plane's current normal/ref
  edit_collision_plane.py LEVEL.RAW --offset 0x1c420 --show
  # tilt plane normal-Y by +2000 and lift its ref-Y by +50, write
  edit_collision_plane.py LEVEL.RAW --offset 0x1c420 --normal +0:+2000:+0 --ref +0:+50:+0 \
      --write --out build/x.RAW
  # disable a plane (degenerate normal -> swept test never crosses it)
  edit_collision_plane.py LEVEL.RAW --offset 0x303f8 --zero-normal --write --out build/x.RAW
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

import decode_level_raw as DEC
import recompress_level_raw as REC

COLL_CHUNK = 32
NORMAL_OFF = 0x00     # s16 x/y/z
REF_OFF = 0x06        # s16 x/y/z
PLANE_LEN = 0x20


def be32(b, o): return struct.unpack_from(">I", b, o)[0]


def split_chunks(raw: bytes):
    off, out = 0, []
    while off + 8 <= len(raw):
        w0, w1 = be32(raw, off), be32(raw, off + 4)
        if w0 == 0xffffffff:
            break
        out.append((off, w0, w1, raw[off:off + 0xe + w1]))
        off += 0xe + w1
    return out


def _triple(dec: bytes, base: int):
    return struct.unpack_from("<hhh", dec, base)


def _parse_delta(spec: str) -> list[tuple[bool, int]]:
    """'x:y:z' where each is an absolute value or a +N/-N delta -> [(is_delta, n)]*3."""
    parts = spec.split(":")
    if len(parts) != 3:
        raise SystemExit(f"expected x:y:z, got {spec!r}")
    out = []
    for p in parts:
        p = p.strip()
        if p and p[0] in "+-" and p not in ("+", "-"):
            out.append((True, int(p, 0)))      # delta
        else:
            out.append((False, int(p, 0)))     # absolute
    return out


def _apply(dec: bytearray, base: int, spec: list[tuple[bool, int]]):
    for k, (is_delta, n) in enumerate(spec):
        cur = struct.unpack_from("<h", dec, base + k * 2)[0]
        val = (cur + n) if is_delta else n
        val = max(-32768, min(32767, val))
        struct.pack_into("<h", dec, base + k * 2, val)


def main() -> int:
    ap = argparse.ArgumentParser(description="Edit a chunk-32 oriented collision plane (wall/slope).")
    ap.add_argument("raw", type=Path, help="source LEVEL.RAW")
    ap.add_argument("--offset", type=lambda s: int(s, 0), required=True,
                    metavar="CHUNK32_OFF", help="plane record offset within chunk 32 (from probe)")
    ap.add_argument("--show", action="store_true", help="print the plane's normal/ref and exit")
    ap.add_argument("--normal", metavar="X:Y:Z", help="set/Δ normal (use +N/-N for delta)")
    ap.add_argument("--ref", metavar="X:Y:Z", help="set/Δ ref point (use +N/-N for delta)")
    ap.add_argument("--zero-normal", action="store_true", help="disable the plane (degenerate normal)")
    ap.add_argument("--write", action="store_true", help="write --out; default dry-run")
    ap.add_argument("--out", type=Path, help="output LEVEL.RAW; required with --write")
    args = ap.parse_args()

    raw = args.raw.read_bytes()
    chunks = split_chunks(raw)
    if len(chunks) <= COLL_CHUNK:
        raise SystemExit(f"LEVEL.RAW has {len(chunks)} chunks, need >{COLL_CHUNK}")
    dec = bytearray(DEC.decompress_chunk(chunks[COLL_CHUNK][3]))
    o = args.offset
    if o < 0 or o + PLANE_LEN > len(dec):
        raise SystemExit(f"offset {o:#x} outside chunk 32 ({len(dec)} B)")

    n0 = _triple(dec, o + NORMAL_OFF)
    r0 = _triple(dec, o + REF_OFF)
    mag = round((n0[0] ** 2 + n0[1] ** 2 + n0[2] ** 2) ** 0.5)
    print(f"plane @chunk32+{o:#x}: normal={n0} (|n|={mag}; unit~0x4000) ref={r0}")
    if args.show:
        return 0

    if not (args.normal or args.ref or args.zero_normal):
        raise SystemExit("nothing to do (use --normal / --ref / --zero-normal, or --show)")
    if args.write and args.out is None:
        raise SystemExit("--write requires --out")
    if args.out is not None and args.out.resolve() == args.raw.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")

    if args.zero_normal:
        struct.pack_into("<hhh", dec, o + NORMAL_OFF, 0, 0, 0)
    if args.normal:
        _apply(dec, o + NORMAL_OFF, _parse_delta(args.normal))
    if args.ref:
        _apply(dec, o + REF_OFF, _parse_delta(args.ref))
    n1 = _triple(dec, o + NORMAL_OFF)
    r1 = _triple(dec, o + REF_OFF)
    print(f"  -> normal={n1} ref={r1}")

    header6 = chunks[COLL_CHUNK][3][8:0xe]
    newcomp = REC.compress_chunk(bytes(dec), header6)
    if bytes(DEC.decompress_chunk(newcomp)) != bytes(dec):
        raise SystemExit("recompress round-trip mismatch — refusing")
    coff = chunks[COLL_CHUNK][0]
    old_comp_len = len(chunks[COLL_CHUNK][3])
    new_raw = raw[:coff] + newcomp + raw[coff + old_comp_len:]
    print(f"LEVEL.RAW: {len(raw)} -> {len(new_raw)} ({len(new_raw)-len(raw):+d}; chunk32 comp "
          f"{old_comp_len}->{len(newcomp)}). Rebuild with tools/build_autolayout_disc.py.")

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(new_raw)
        rc = split_chunks(new_raw)
        chk = DEC.decompress_chunk(rc[COLL_CHUNK][3])
        if _triple(chk, o + NORMAL_OFF) != n1 or _triple(chk, o + REF_OFF) != r1:
            raise SystemExit("verify failed: edit not present in spliced file")
        print(f"wrote {args.out} ({len(new_raw)} bytes)")
    else:
        print("dry-run only; no LEVEL.RAW written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
