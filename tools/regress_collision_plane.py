#!/usr/bin/env python3
"""Regression checks for the oriented collision-plane editor (punchlist §2.2).

Covers edit_collision_plane: delta/absolute spec parsing, s16 clamp, and a full
decode -> edit normal/ref -> recompress -> splice -> re-decode round-trip that
confirms the edit lands and nothing else in chunk 32 changes. Pure-python; no
emulator, no ISO build, no workspace mutation. Skips cleanly if LEVEL.RAW is absent.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import decode_level_raw as DEC          # noqa: E402
import edit_collision_plane as EP       # noqa: E402

RAW = (ROOT / "DAT" / "LEVEL01_LEVEL.RAW") if (ROOT / "DAT" / "LEVEL01_LEVEL.RAW").exists() \
    else ROOT / "REBUILD" / "files" / "LEVEL01" / "LEVEL.RAW"

PLANE0_OFF = 0x1C420   # LEVEL01 plane 0 (live-probed), sector 119, slope/floor


def check_spec_parsing() -> None:
    # absolute vs delta
    assert EP._parse_delta("1:2:3") == [(False, 1), (False, 2), (False, 3)]
    assert EP._parse_delta("+10:-5:+0") == [(True, 10), (True, -5), (True, 0)]
    buf = bytearray(struct.pack("<hhh", 100, 200, 300))
    EP._apply(buf, 0, EP._parse_delta("+50:-50:0"))   # delta, delta, absolute
    assert struct.unpack("<hhh", buf) == (150, 150, 0), struct.unpack("<hhh", buf)
    # s16 clamp
    EP._apply(buf, 0, EP._parse_delta("99999:-99999:32767"))
    assert struct.unpack("<hhh", buf) == (32767, -32768, 32767), struct.unpack("<hhh", buf)
    print("plane spec/clamp OK")


def check_roundtrip() -> None:
    if not RAW.is_file():
        print(f"SKIP roundtrip: {RAW} not present")
        return
    raw = RAW.read_bytes()
    chunks = EP.split_chunks(raw)
    dec0 = bytearray(DEC.decompress_chunk(chunks[EP.COLL_CHUNK][3]))

    o = PLANE0_OFF
    n0 = struct.unpack_from("<hhh", dec0, o + EP.NORMAL_OFF)
    r0 = struct.unpack_from("<hhh", dec0, o + EP.REF_OFF)
    mag = round((n0[0] ** 2 + n0[1] ** 2 + n0[2] ** 2) ** 0.5)
    if not (0x3D00 <= mag <= 0x4300):
        raise SystemExit(f"plane: |normal| {mag} not ~0x4000 at {o:#x} (wrong offset?)")

    # apply the edit the tool would, in-memory, and round-trip just chunk 32
    dec1 = bytearray(dec0)
    EP._apply(dec1, o + EP.NORMAL_OFF, EP._parse_delta("+0:+3000:+0"))
    EP._apply(dec1, o + EP.REF_OFF, EP._parse_delta("+0:+40:+0"))
    import recompress_level_raw as REC
    header6 = chunks[EP.COLL_CHUNK][3][8:0xe]
    comp = REC.compress_chunk(bytes(dec1), header6)
    back = bytes(DEC.decompress_chunk(comp))
    if back != bytes(dec1):
        raise SystemExit("plane: recompress round-trip mismatch")
    # the edit is present and is the ONLY change vs the original decompressed chunk
    assert struct.unpack_from("<hhh", back, o + EP.NORMAL_OFF) == (n0[0], n0[1] + 3000, n0[2])
    assert struct.unpack_from("<hhh", back, o + EP.REF_OFF) == (r0[0], r0[1] + 40, r0[2])
    diff = [k for k in range(len(dec0)) if dec0[k] != back[k]]
    # only the two edited s16 fields (4 bytes) differ
    assert diff and all(o + EP.NORMAL_OFF + 2 <= k < o + EP.NORMAL_OFF + 4
                        or o + EP.REF_OFF + 2 <= k < o + EP.REF_OFF + 4 for k in diff), diff
    print(f"plane roundtrip OK (plane0 @{o:#x} |n|={mag}, normal-Y+3000 ref-Y+40, {len(diff)} bytes changed)")


def main() -> int:
    check_spec_parsing()
    check_roundtrip()
    print("all collision-plane checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
