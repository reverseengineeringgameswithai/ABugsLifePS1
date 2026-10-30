#!/usr/bin/env python3
"""tools/fmv_frame_table.py -- read/patch ABL's per-movie FMV frame-count table.

SOLVED 2026-07-04 (see src_re/fmv_player_streaming.c): each FMV plays for a HARDCODED
frame count baked into the FMV.BIN player overlay as a 40-case jump table of
`addiu a1, zero, <FRAME_COUNT>` immediates, in manifest order. The overlay decode loop
stops the movie when `current_frame >= total-2`, where `total` is that per-movie count
(RAM 0x80131EEE). The overlay loads verbatim to 0x800B5788, so each immediate is a 2-byte
edit in the FMV.BIN file. Patching a movie's count to a longer replacement STR's frame
count makes the game play the whole clip (proven: TT 440->900 = full 30s).

Table layout: 40 entries, each `?? ?? 05 24` (addiu a1,zero,imm); imm = low halfword.
Entries appear in the same order as the manifest path strings at the top of FMV.BIN.
"""
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FMVBIN = ROOT / "REBUILD" / "files" / "FMV" / "FMV.BIN"
OVERLAY_BASE = 0x800B5788                 # FMV.BIN loads here verbatim (file offset 0)
SCAN_LO, SCAN_HI = 0x0B00, 0x0F00         # code region holding the frame-count jump table


def manifest_movies(data: bytes):
    """Ordered list of NUL-terminated movie paths from the FMV.BIN manifest header."""
    out, i = [], 8
    while i < 0x320:
        j = data.index(b"\x00", i)
        s = data[i:j].decode("latin1", "replace")
        if s and s.upper().endswith(".STR"):
            out.append(s)
        i = j + 1
        while i < 0x320 and data[i] == 0:
            i += 1
    return out


def frame_table(data: bytes):
    """[(file_offset, frame_count), ...] of the addiu-a1-zero immediates, in table order."""
    ents = []
    for o in range(SCAN_LO, SCAN_HI, 4):
        if data[o + 2] == 0x05 and data[o + 3] == 0x24:      # addiu a1, zero, imm
            ents.append((o, struct.unpack_from("<H", data, o)[0]))
    return ents


def _norm(name: str):
    return name.replace("\\", "/").upper().rsplit("/", 1)[-1]   # basename, upper


def find_entry(data: bytes, target: str):
    """Return (file_offset, current_count) of the frame-count entry for a movie
    (matched by basename, e.g. 'LEV1A.STR' or 'BUGSFMV1/LEV1A.STR'). Raises if not found."""
    movies = manifest_movies(data)
    table = frame_table(data)
    if len(table) != len(movies):
        raise SystemExit(f"table/manifest mismatch ({len(table)} vs {len(movies)}) — "
                         "FMV.BIN layout changed; re-derive in fmv_player_streaming.c")
    tb = _norm(target)
    for (off, cnt), name in zip(table, movies):
        if _norm(name) == tb:
            return off, cnt
    raise SystemExit(f"movie {target!r} not found in FMV.BIN manifest "
                     f"(known: {[_norm(m) for m in movies]})")


def patch_count(fmvbin_path, target: str, new_count: int):
    """Set a movie's hardcoded frame count in FMV.BIN (in place). Returns (offset, old, new)."""
    if not 1 <= new_count <= 0xFFFF:
        raise SystemExit(f"frame count {new_count} out of 16-bit range")
    p = Path(fmvbin_path)
    d = bytearray(p.read_bytes())
    off, old = find_entry(bytes(d), target)
    struct.pack_into("<H", d, off, new_count)                # rewrite the immediate halfword
    p.write_bytes(d)
    return off, old, new_count


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("set")
    p.add_argument("--target", required=True, help="movie, e.g. BUGSFMV3/TT.STR or LEV1A.STR")
    p.add_argument("--count", type=int, required=True, help="new frame count")
    p.add_argument("--file", default=str(FMVBIN), help="FMV.BIN path (default REBUILD copy)")
    a = ap.parse_args()
    if a.cmd == "list":
        d = FMVBIN.read_bytes()
        for (off, cnt), name in zip(frame_table(d), manifest_movies(d)):
            print(f"  {off:#06x}  {cnt:5}  {name}")
    else:
        off, old, new = patch_count(a.file, a.target, a.count)
        print(f"[ok] {a.target}: frame count {old} -> {new} at FMV.BIN offset {off:#06x}")
