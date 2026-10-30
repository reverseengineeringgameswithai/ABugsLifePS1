#!/usr/bin/env python3
"""Decode the LEVEL.RAW chunk-34 "master/world mesh DEFINITION" structural schema (GAP-0023).

METADATA ONLY — emits the header fields, the sub-mesh offset table, and a structural
report; it never writes vertex/colour payload (copyrighted asset data). Reads the tracked
chunk index + the (local, gitignored) decompressed cache produced by tools/dump_level_raw.py.
Defaults resolve from tools/_env.py (ABL_DIR). Requires the decompressed cache
(tools/LEVEL_RAW_decompressed/) — local owner media, not CI: absent -> clean exit 0.

Confirmed first-hand (decomp_off 872396, size 0x2c846, 2026-06-21):
  marker@0x00 = 0x0101 (mesh DEFINITION) · u32@0x04 = 0 (master/world object id) · u16@0x08 = 0
  count@0x0a  = 40 (sub-mesh count; corrects the older "+0x08" note) · pools@0x0c = 4 u32
  offset table @0x2c = monotonic, in-bounds u32 offsets ending just before the vertex/matrix pools.

Open residual (GAP-0023): count@0x0a (40) != the number of offset slots that parse cleanly
(33 on LEVEL01: 32 offsets + 1 empty), and a secondary record/index structure begins right
after the table. The per-record schema + the count semantics need consumer-tracing (the
fcn that walks chunk-34). The model->world *world-origin* transform is GTE-applied at draw
time and is NOT in this chunk -- see the live next-target in the GAP-0023 notes.

    python3 tools/decode_chunk34.py [--raw-cache DIR] [--chunk 34]
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from _env import ABL_DIR  # noqa: F401
except Exception:
    ABL_DIR = os.path.dirname(HERE)

CACHE = os.path.join(HERE, "LEVEL_RAW_decompressed")


def find_chunk(idx, n):
    for r in idx:
        if r.get("chunk") == n:
            return r
    return None


def walk_offset_table(body, size, count, table_off=0x2c):
    """Return (slots, empties, last_offset, first_break_index).

    A slot is valid if it is 0 (empty sub-mesh) or an in-bounds, non-decreasing u32.
    Walk stops at the first entry that is neither -> first_break_index.
    """
    slots = 0
    empties = 0
    last = 0
    i = 0
    limit = (size - table_off) // 4
    while i < limit:
        v = struct.unpack_from("<I", body, table_off + i * 4)[0]
        if v == 0:
            empties += 1
            slots += 1
            i += 1
            continue
        if v < size and v >= last:
            last = v
            slots += 1
            i += 1
            continue
        break  # not a valid offset slot
    return slots, empties, last, i


def decode(cache, chunk_n):
    idx_path = os.path.join(cache, "chunk_index.json")
    dec_path = os.path.join(cache, "LEVEL.RAW.decompressed")
    if not (os.path.exists(idx_path) and os.path.exists(dec_path)):
        print(f"[skip] decompressed cache absent ({cache}); regenerate with "
              f"tools/dump_level_raw.py from owner-supplied LEVEL.RAW.")
        return 0

    idx = json.load(open(idx_path))
    rec = find_chunk(idx, chunk_n)
    if rec is None:
        print(f"[error] chunk {chunk_n} not in {idx_path}")
        return 2
    dec = open(dec_path, "rb").read()
    off, size = rec["decomp_off"], rec["word0"]
    body = dec[off:off + size]

    marker = struct.unpack_from("<H", body, 0x00)[0]
    obj_id = struct.unpack_from("<I", body, 0x04)[0]
    u08 = struct.unpack_from("<H", body, 0x08)[0]
    count = struct.unpack_from("<H", body, 0x0a)[0]
    pools = list(struct.unpack_from("<4I", body, 0x0c))
    slots, empties, last, brk = walk_offset_table(body, size, count)

    print(f"chunk {chunk_n} @ decomp_off {off} size 0x{size:x} ({size} B)")
    print(f"  marker@0x00 = 0x{marker:04x}   {'master/world mesh DEFINITION' if marker == 0x101 else '(unexpected)'}")
    print(f"  obj_id@0x04 = {obj_id}{'  (master/world)' if obj_id == 0 else ''}")
    print(f"  u16@0x08    = {u08}")
    print(f"  count@0x0a  = {count}   (sub-mesh count)")
    print(f"  pools@0x0c  = {[hex(p) for p in pools]}")
    print(f"  offset table @0x2c: {slots} slots ({slots - empties} non-zero + {empties} empty); "
          f"last=0x{last:x} (pools start 0x{pools[1]:x}); parse breaks at index {brk}")

    pools_start = min(p for p in pools if p)
    ok_header = (marker == 0x101 and obj_id == 0 and count > 0)
    ok_table = (last < pools_start) and brk == slots
    if count != slots:
        print(f"  RESIDUAL (GAP-0023): count@0x0a={count} != {slots} parsed offset slots; "
              f"a secondary record/index structure begins at +0x{0x2c + slots * 4:x}. "
              f"Per-record schema + count semantics need consumer-tracing.")
    print(f"  world-origin transform: NOT in chunk (GTE-applied at draw time) -> live capture, see GAP-0023.")
    print(f"  VERDICT: header {'OK' if ok_header else 'MISMATCH'}; "
          f"offset-table {'in-bounds & monotonic' if ok_table else 'irregular'}.")
    return 0 if ok_header else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw-cache", default=CACHE,
                    help="decompressed-cache dir (default: tools/LEVEL_RAW_decompressed/)")
    ap.add_argument("--chunk", type=int, default=34, help="chunk index (default 34)")
    args = ap.parse_args()
    return decode(args.raw_cache, args.chunk)


if __name__ == "__main__":
    sys.exit(main())
