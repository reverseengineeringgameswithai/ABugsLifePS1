#!/usr/bin/env python3
"""Build the G8 entry24 +0x08 render-body diagnostic DAT (Candidate A2).

Stronger same-field escalation of Candidate A. Fixed-size four-byte (single changed byte) patch for
LEVEL01/LEVEL.DAT only:
DAT offset 0x16ec, pristine `9f fa ff ff` (-1377) -> `9f fe ff ff` (-353), delta +1024.

This is pass-1 trail entry24 +0x08, a CONFIRMED non-sentinel render body field read by
fcn.800140a0 (read site 0x800141a0). Candidate A (+256, `9f fb ff ff`) was a valid build that
produced no obvious visual change; A2 keeps the same field, same sign, same 4-byte size, and changes
only one byte, to isolate whether entry24 +0x08 has any visible influence. Field semantics are
UNKNOWN; expected visual effect is UNKNOWN; collision/pathing impact is UNKNOWN.

This script only PRODUCES a candidate patched DAT. It does not build an image and never mutates the
input in place.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED_SIZE = 0x51418
PATCH_OFFSET = 0x16EC
ORIGINAL = bytes.fromhex("9f fa ff ff")  # -1377 (little-endian s32), pristine
PATCHED = bytes.fromhex("9f fe ff ff")   # -353 (little-endian s32), delta +1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the G8 entry24 +0x08 (DAT 0x16ec) render-body diagnostic DAT (Candidate A2)."
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
    print(f"patch_offset: 0x{PATCH_OFFSET:x} (pass-1 trail entry24 +0x08, runtime 0x80161ee4)")
    print(f"original_bytes: {ORIGINAL.hex(' ')} (-1377)")
    print(f"patched_bytes: {PATCHED.hex(' ')} (-353, delta +1024)")
    print(f"revert_bytes: {ORIGINAL.hex(' ')}")
    print(f"sha256_before: {before_sha}")
    print(f"sha256_after: {after_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
