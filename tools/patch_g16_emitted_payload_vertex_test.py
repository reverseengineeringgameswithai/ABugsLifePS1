#!/usr/bin/env python3
"""Build the G16 emitted-primitive terrain payload vertex deformation DAT (Candidate EMITTED-PV).

Fixed-size two-byte (single changed byte) patch for LEVEL01/LEVEL.DAT only:
DAT offset 0x3573a, pristine `b9 1a` (6841) -> `b9 16` (5817), delta -1024.

This edits one s16 COORDINATE (the `y`) of payload vertex 10 of the payload at DAT 0x356bc
(runtime 0x80195eb4). UNLIKE G12-G15 (which were vertex-READ-confirmed but visually silent), this
vertex has SCREEN-SPACE EMISSION EVIDENCE: a G16 runtime log (EXEC 0x800108b4, the packet-store gate
past all RTPS/RTPT/NCLIP/AVSZ4 reject branches in fcn.80010000) showed payload 0x356bc emitting >=5
primitives while the operator viewed visible terrain/ground. Hits 1-5 were the first primitive
command's quads (verts 0..19); vertex 10 sits in that observed-emitted set, near its X/Z centroid.

Payload 0x356bc = static survey candidate e128: 230 verts, wide+flat (X spread 5838, Z 6700), positive-Y
ground stratum (5093..8332), flatness ~0.48 -> terrain/ground render (LIKELY). vertex 10 xyz
(-2155, 6841, 4768). Delta -1024 lifts y to 5817 (toward the surface top), a clear local bump that
stays on-screen (a larger delta risks the spike projecting off the top -> screen-bound reject).

Semantics beyond "payload vertex y of a runtime-confirmed emitted ground-render surface" are UNKNOWN;
render-path only. Collision/pathing impact is UNKNOWN and must not be inferred (visual terrain !=
collision).

This script only PRODUCES a candidate patched DAT. It does not build an image and never mutates the
input in place.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


EXPECTED_SIZE = 0x51418
PATCH_OFFSET = 0x3573A                   # payload 0x356bc, vertex 10, y component (s16)
ORIGINAL = bytes.fromhex("b9 1a")        # 6841 (little-endian s16), pristine
PATCHED = bytes.fromhex("b9 16")         # 5817 (little-endian s16), delta -1024
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
        description="Prepare the G16 emitted-payload terrain vertex-10 y (DAT 0x3573a) deformation DAT."
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
    print(f"patch_offset: 0x{PATCH_OFFSET:x} (payload 0x356bc vertex 10 y; runtime 0x80195f32, base 0x80195f30)")
    print(f"original_bytes: {ORIGINAL.hex(' ')} ({s16(ORIGINAL)})")
    print(f"patched_bytes: {PATCHED.hex(' ')} ({s16(PATCHED)}, delta {DELTA:+d})")
    print(f"revert_bytes: {ORIGINAL.hex(' ')}")
    print(f"sha256_before: {before_sha}")
    print(f"sha256_after: {after_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
