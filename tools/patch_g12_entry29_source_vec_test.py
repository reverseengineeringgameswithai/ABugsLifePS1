#!/usr/bin/env python3
"""Build the G12 entry29 source-vector visual-geometry diagnostic DAT (Candidate VEC).

Fixed-size four-byte (single changed byte) patch for LEVEL01/LEVEL.DAT only:
DAT offset 0x7388, pristine `f0 d8 ff ff` (-10000) -> `f0 dc ff ff` (-8976), delta +1024.

This is pass-1 entry29's SOURCE RECORD vec[0] (the object render origin), reached at runtime via
trail row 0x1748 +0x10 -> output record -> +0x18 -> source record. G10/G11 CONFIRMED this source
record is consumed by the survivor-list primitive builder fcn.8001ea6c case 0x8001ec44, which reads
vec[3] ([s2+0/4/8]), subtracts the camera position, and feeds the GTE transform that places the
object's payload mesh on screen (fcn.80010000). entry29 is the G9-confirmed survivor (it reaches the
list-write/draw path), unlike the entry24 trail/cull-row tests (G8) which were culling-bounds data and
visually silent.

vec[0] is the lateral (X-like) component. entry29's payload mesh spans only ~+/-54 units on X, so a
+1024 delta is a large, unmistakable lateral translation of the whole drawn object. Culling is decided
by the (unchanged) trail-row body vec, NOT this source vec, so this edit cannot remove the object from
the visibility list; it only changes where the object is DRAWN. Expected effect: the whole entry29
object/chunk renders shifted laterally. Semantics beyond "object render origin" remain UNKNOWN;
collision/pathing impact is UNKNOWN and must not be inferred from this render-path edit.

This script only PRODUCES a candidate patched DAT. It does not build an image and never mutates the
input in place.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


EXPECTED_SIZE = 0x51418
PATCH_OFFSET = 0x7388                      # pass-1 entry29 source record vec[0]
ORIGINAL = bytes.fromhex("f0 d8 ff ff")    # -10000 (little-endian s32), pristine
PATCHED = bytes.fromhex("f0 dc ff ff")     # -8976  (little-endian s32), delta +1024
DELTA = 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def s32(b: bytes) -> int:
    return struct.unpack("<i", b)[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the G12 entry29 source-record vec[0] (DAT 0x7388) visual-geometry diagnostic DAT."
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

    # sanity: the patch must be exactly the original s32 + DELTA, same size
    if s32(PATCHED) - s32(ORIGINAL) != DELTA:
        raise SystemExit("internal error: PATCHED - ORIGINAL != DELTA")
    if len(PATCHED) != len(ORIGINAL) != 4:
        raise SystemExit("internal error: patch is not a 4-byte same-size edit")

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
    print(f"patch_offset: 0x{PATCH_OFFSET:x} (pass-1 entry29 source vec[0], runtime 0x80167b80)")
    print(f"original_bytes: {ORIGINAL.hex(' ')} ({s32(ORIGINAL)})")
    print(f"patched_bytes: {PATCHED.hex(' ')} ({s32(PATCHED)}, delta {DELTA:+d})")
    print(f"revert_bytes: {ORIGINAL.hex(' ')}")
    print(f"sha256_before: {before_sha}")
    print(f"sha256_after: {after_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
