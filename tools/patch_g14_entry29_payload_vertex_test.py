#!/usr/bin/env python3
"""Build the G14 entry29 payload referenced-vertex deformation diagnostic DAT (Candidate PV14).

Fixed-size two-byte (single changed byte) patch for LEVEL01/LEVEL.DAT only:
DAT offset 0x2f3a6, pristine `bf f9` (-1601) -> `bf f5` (-2625), delta -1024.

This is a single s16 COORDINATE of one PAYLOAD VERTEX (entry29 payload vertex 14, the `y` component),
not a trail/cull row and not a source-record transform field. G11 decoded the payload reached via the
entry29 source record (`source +0x1c` = DAT 0x2f2f8): `{u32 count; Vertex verts[N] stride 0xc =
(s16 x; s16 y; s16 z; s16 pad; u32 attr); primitive command stream}`. entry29 count = 34; vertex 14 is
at DAT 0x2f3a4 (x@+0, y@+2, z@+4).

WHY vertex 14 (over G13's vertex 0): a full decode of entry29's primitive command stream
(0x2f494..0x2f59c, terminated by 0xffff 0xffff) shows all 34 vertices are referenced, 28 of them
exactly twice. Vertex 14 is (a) referenced by 2 primitives (so a single coord edit deforms 2 triangles,
unlike a refs=1 vertex whose lone triangle may be backface-culled/occluded and silent), and (b) a
near-APEX vertex: the mesh spans Y 0..-1769 (tall/narrow, X only +/-60), and v14 y=-1601 sits in the
top silhouette cluster. v13/v16 are the literal apex tip (y=-1769) but are each referenced only once.
v14 is therefore the strongest visible+robust single-vertex target.

Delta -1024 pushes v14.y from -1601 to -2625 (further negative = upward), well past the apex cluster
(~-1769), creating a spike ~58% of the object's Y extent above its current position -> a clearly
visible, distinctive deformation, while staying well inside s16 range. This is a DIRECT mesh-data
deformation. G12 (source origin) and G13 (mid-body vertex 0, +512) were valid/read but visually silent;
G14 changes a near-apex multiply-referenced vertex by a larger delta.

Semantics beyond "payload vertex y coordinate" are UNKNOWN; collision/pathing impact is UNKNOWN and
must not be inferred from this render-path edit.

This script only PRODUCES a candidate patched DAT. It does not build an image and never mutates the
input in place.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


EXPECTED_SIZE = 0x51418
PATCH_OFFSET = 0x2F3A6                   # entry29 payload vertex 14, y component (s16)
ORIGINAL = bytes.fromhex("bf f9")        # -1601 (little-endian s16), pristine
PATCHED = bytes.fromhex("bf f5")         # -2625 (little-endian s16), delta -1024
DELTA = -1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def s16(b: bytes) -> int:
    return struct.unpack("<h", b)[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the G14 entry29 payload vertex-14 y-coordinate (DAT 0x2f3a6) deformation DAT."
    )
    parser.add_argument("input_dat", type=Path)
    parser.add_argument("output_dat", type=Path)
    parser.add_argument("--force", action="store_true", help="allow overwriting output_dat")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input_dat.exists():
        raise SystemExit(f"input DAT not found: {args.input_dat}")
    if args.input_dat.resolve() == args.output_dat.resolve():
        raise SystemExit("refusing to patch in place; input and output paths must differ")
    if args.output_dat.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing output without --force: {args.output_dat}")

    # sanity: same-size 2-byte s16 edit, exactly +DELTA
    if len(PATCHED) != len(ORIGINAL) != 2:
        raise SystemExit("internal error: patch is not a 2-byte same-size edit")
    if s16(PATCHED) - s16(ORIGINAL) != DELTA:
        raise SystemExit("internal error: PATCHED - ORIGINAL != DELTA")

    data = bytearray(args.input_dat.read_bytes())
    if len(data) != EXPECTED_SIZE:
        raise SystemExit(f"unexpected DAT size {len(data)}; expected {EXPECTED_SIZE}")

    found = bytes(data[PATCH_OFFSET : PATCH_OFFSET + len(ORIGINAL)])
    if found != ORIGINAL:
        raise SystemExit(
            f"refusing to patch: unexpected bytes at 0x{PATCH_OFFSET:x}: {found.hex(' ')}; "
            f"expected pristine {ORIGINAL.hex(' ')}"
        )

    before_sha = sha256_file(args.input_dat)
    data[PATCH_OFFSET : PATCH_OFFSET + len(PATCHED)] = PATCHED

    args.output_dat.parent.mkdir(parents=True, exist_ok=True)
    args.output_dat.write_bytes(data)
    after_sha = sha256_file(args.output_dat)

    verify = args.output_dat.read_bytes()
    if len(verify) != EXPECTED_SIZE:
        raise SystemExit("output size verification failed")
    if verify[PATCH_OFFSET : PATCH_OFFSET + len(PATCHED)] != PATCHED:
        raise SystemExit("output patch verification failed")

    print(f"input: {args.input_dat}")
    print(f"output: {args.output_dat}")
    print(f"size: {EXPECTED_SIZE}")
    print(f"patch_offset: 0x{PATCH_OFFSET:x} (entry29 payload vertex 14, y; runtime 0x8018fb9e)")
    print(f"original_bytes: {ORIGINAL.hex(' ')} ({s16(ORIGINAL)})")
    print(f"patched_bytes: {PATCHED.hex(' ')} ({s16(PATCHED)}, delta {DELTA:+d})")
    print(f"revert_bytes: {ORIGINAL.hex(' ')}")
    print(f"sha256_before: {before_sha}")
    print(f"sha256_after: {after_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
