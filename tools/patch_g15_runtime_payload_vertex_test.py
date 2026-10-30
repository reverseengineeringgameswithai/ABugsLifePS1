#!/usr/bin/env python3
"""Build the G15 runtime-confirmed terrain payload vertex deformation DAT (Candidate TERRAIN-PV).

Fixed-size two-byte (single changed byte) patch for LEVEL01/LEVEL.DAT only:
DAT offset 0x103ae, pristine `86 1c` (7302) -> `86 18` (6278), delta -1024.

This edits one s16 COORDINATE (the `y`) of one PAYLOAD VERTEX (vertex 46) of the payload at
DAT 0x10180 (runtime 0x80170978). That payload was RUNTIME-CONFIRMED drawn by fcn.80010000 (G15
EXEC 0x80010000 a0-log) while the operator was viewing/standing on visible ground. It is a
terrain/ground render surface (LIKELY): 63 vertices, all referenced by the primitive command stream
(190 total references => a connected surface, not sparse decor), wide footprint (X spread 7937),
positive-Y ground stratum (Y 6738..9127, tight median band ~7174-7893), and drawn ONCE per frame
(unique surface, unlike the instanced high-frequency decor pointers 0x8018c234/0x8018c570 which are
tall/small props reused 4-6x). NOTE: the suggested static "primary" 0x8018c234 was REJECTED here -
it is flatness 1.76 (tall), count 37, instanced => decor, not terrain.

Vertex 46 (DAT 0x103a8, xyz (1362,7302,-452)) is near the X/Z centroid and is referenced by 4
primitives, so a single coordinate edit deforms ~4 triangles around a central point. Delta -1024
lowers y to 6278, BELOW the surface min (6738) in PS1 Y-down space => the vertex becomes the highest
point and pokes UP as a spike above the ground surface (maximally visible), while staying well inside
s16 range.

Semantics beyond "payload vertex y coordinate of a runtime-confirmed ground-render surface" are
UNKNOWN; this is render-path only. Collision/pathing impact is UNKNOWN and must not be inferred
(visual terrain != collision).

This script only PRODUCES a candidate patched DAT. It does not build an image and never mutates the
input in place.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


EXPECTED_SIZE = 0x51418
PATCH_OFFSET = 0x103AE                   # payload 0x10180, vertex 46, y component (s16)
ORIGINAL = bytes.fromhex("86 1c")        # 7302 (little-endian s16), pristine
PATCHED = bytes.fromhex("86 18")         # 6278 (little-endian s16), delta -1024
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
        description="Prepare the G15 runtime-confirmed terrain payload vertex-46 y (DAT 0x103ae) deformation DAT."
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
    print(f"patch_offset: 0x{PATCH_OFFSET:x} (payload 0x10180 vertex 46 y; runtime 0x80170ba6, base 0x80170ba4)")
    print(f"original_bytes: {ORIGINAL.hex(' ')} ({s16(ORIGINAL)})")
    print(f"patched_bytes: {PATCHED.hex(' ')} ({s16(PATCHED)}, delta {DELTA:+d})")
    print(f"revert_bytes: {ORIGINAL.hex(' ')}")
    print(f"sha256_before: {before_sha}")
    print(f"sha256_after: {after_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
