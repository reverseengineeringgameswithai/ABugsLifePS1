#!/usr/bin/env python3
"""Build the G28 Candidate A floor/top-surface visual diagnostic DAT (same-size, reversible).

G28 Candidate A floor/top-surface visual diagnostic
---------------------------------------------------
Fixed-size two-byte (single changed byte) patch for LEVEL01/LEVEL.DAT only:
DAT offset 0x18992, pristine `89 13` (0x1389 = 5001) -> `89 17` (0x1789 = 6025), delta +0x0400 / +1024.

This edits one s16 COORDINATE (the `y`) of payload vertex 16 of Candidate A, the count-validated
fcn.80010000 payload at DAT 0x188cc (runtime payload base 0x801790c4, vertex base 0x801790c8).
G27 decoded Candidate A as the strongest floor/top-surface candidate (count 83, flatness 0.154,
Y-band 316, 4502x4502 world-space footprint, DAT-backed). G28 runtime confirmation then showed:
  - READ watch on the Candidate A vertex base 0x801790c8 hit repeatedly in the active render path;
  - EXEC 0x80010718 (post-mfc2 SXY0/1/2 projection site) hit while Candidate A was active
    (a0 = 0x801790c8, ra = 0x800206a0, payload base = a0 - 4 = 0x801790c4, count 83), with plausible
    lower/central screen-space SXY values.
So Candidate A is a VALID DAT-BACKED payload whose vertices reach the projection/emission path. This
patch raises v16.y by +1024 so that, IF Candidate A is the visible floor/top-surface, a local
out-of-plane deformation should appear (1024 ~= 3x its tight Y-core band of 316).

Vertex 16 is the most-central, multiply-referenced vertex (refs=5, ~mid-floor, not a cull-prone edge
tip). Address math: DAT 0x18992 = 0x188cc + 4 + 16*0xc + 2; runtime vertex base 0x80179188, y at
0x8017918a.

UNCERTAINTY (do not overclaim):
  - The Y-sign -> screen-up/down mapping is UNCONFIRMED; +1024 produces a clear out-of-plane outlier
    in either visual direction. If +1024 over-distorts/clips, the documented fallback is -1024
    (-> 3977 = 0x0f89, bytes `89 0f`, single byte 0x18993 13 -> 0f).
  - Candidate A's floor role is LIKELY (shape + DAT-backed + runtime-read + projection-path), NOT a
    proven walkable surface. Visual floor != collision floor.
  - Collision/pathing impact is UNKNOWN and must NOT be inferred from any visible result.

This touches ONLY LEVEL01/LEVEL.DAT. It does not touch any collision/pathing files. It only PRODUCES
a candidate patched DAT: it does not build an image and never mutates the input in place.

Build (only when explicitly instructed; pristine source DAT/LEVEL01_LEVEL.DAT, sha1 b376cb50...):
    python3 tools/patch_g28_candidate_a_floor_y_test.py \
        DAT/LEVEL01_LEVEL.DAT DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST.DAT
    python3 tools/rebuild_with_patched_dat.py \
        --patched-dat DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST.DAT \
        --target files/LEVEL01/LEVEL.DAT \
        --out-bin ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.bin \
        --out-cue ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.cue \
        --write --report DAT/LEVEL01_LEVEL_G28_CANDIDATE_A_FLOOR_Y_TEST_REBUILD.md
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


EXPECTED_SIZE = 0x51418
PRISTINE_SHA1 = "b376cb506f437a1cda721fd13766ddbca7c6a247"
PATCH_OFFSET = 0x18992                    # Candidate A (DAT 0x188cc), vertex 16, y component (s16)
ORIGINAL = bytes.fromhex("89 13")         # 0x1389 = 5001 (little-endian s16), pristine
PATCHED = bytes.fromhex("89 17")          # 0x1789 = 6025 (little-endian s16), delta +1024
DELTA = 1024


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        description="Prepare the G28 Candidate A floor/top-surface visual diagnostic DAT "
        "(vertex 16 y @ DAT 0x18992, +1024, same-size)."
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

    if len(PATCHED) != len(ORIGINAL) or len(ORIGINAL) != 2:
        raise SystemExit("internal error: patch is not a 2-byte same-size edit")
    if s16(PATCHED) - s16(ORIGINAL) != DELTA:
        raise SystemExit("internal error: PATCHED - ORIGINAL != DELTA")

    data = bytearray(args.input_dat.read_bytes())
    if len(data) != EXPECTED_SIZE:
        raise SystemExit(f"unexpected DAT size {len(data)}; expected {EXPECTED_SIZE}")

    before_sha1 = sha1_file(args.input_dat)
    if before_sha1 != PRISTINE_SHA1:
        # Not fatal (a rebuilt-but-identical DAT could differ in provenance), but make it loud.
        print(f"WARNING: input sha1 {before_sha1} != pristine {PRISTINE_SHA1}")

    found = bytes(data[PATCH_OFFSET : PATCH_OFFSET + len(ORIGINAL)])
    if found != ORIGINAL:
        raise SystemExit(
            f"refusing to patch: unexpected bytes at 0x{PATCH_OFFSET:x}: {found.hex(' ')}; "
            f"expected pristine {ORIGINAL.hex(' ')}"
        )

    before_sha256 = sha256_file(args.input_dat)
    data[PATCH_OFFSET : PATCH_OFFSET + len(PATCHED)] = PATCHED

    args.output_dat.parent.mkdir(parents=True, exist_ok=True)
    args.output_dat.write_bytes(data)
    after_sha256 = sha256_file(args.output_dat)

    verify = args.output_dat.read_bytes()
    if len(verify) != EXPECTED_SIZE:
        raise SystemExit("output size verification failed (not same-size)")
    if verify[PATCH_OFFSET : PATCH_OFFSET + len(PATCHED)] != PATCHED:
        raise SystemExit("output patch verification failed")

    print("label: G28 Candidate A floor/top-surface visual diagnostic")
    print(f"input: {args.input_dat}")
    print(f"output: {args.output_dat}")
    print(f"size: {EXPECTED_SIZE} (0x{EXPECTED_SIZE:x}); same-size only")
    print(f"payload: Candidate A @ DAT 0x188cc (runtime base 0x801790c4, vertex base 0x801790c8, count 83)")
    print(f"patch_offset: 0x{PATCH_OFFSET:x} (vertex 16 y; runtime base 0x80179188, y at 0x8017918a)")
    print(f"original_bytes: {ORIGINAL.hex(' ')} (0x{s16(ORIGINAL) & 0xffff:04x} = {s16(ORIGINAL)})")
    print(f"patched_bytes: {PATCHED.hex(' ')} (0x{s16(PATCHED) & 0xffff:04x} = {s16(PATCHED)}, delta {DELTA:+d})")
    print(f"revert_bytes: {ORIGINAL.hex(' ')} (restore at DAT 0x{PATCH_OFFSET:x})")
    print(f"sha1_before: {before_sha1}")
    print(f"sha256_before: {before_sha256}")
    print(f"sha256_after: {after_sha256}")
    print("note: render-path visual diagnostic only; collision/pathing UNKNOWN; touches no collision/pathing files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
