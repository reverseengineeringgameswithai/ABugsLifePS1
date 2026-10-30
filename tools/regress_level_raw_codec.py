#!/usr/bin/env python3
"""Regression checks for the LEVEL.RAW codec (CC2): decode byte-exactness, provenance
alignment (the now-fixed tracker), and recompress round-trip.

The decoder (decode_level_raw) is byte-exact; the recompressor (recompress_level_raw) is a
literal-run encoder that round-trips (it balloons, which the auto-layout rebuild tolerates —
CC3). The provenance map (decompressed byte -> compressed offset, or None for match output)
must align 1:1 with the decoded output. (Size-neutral byte-patching is NOT a safe capability:
a literal byte can be an LZ match source, so patching it propagates — robust edits recompress.)

Reads the workspace LEVEL.RAW (owner media), decodes/recompresses in memory; no ISO/emulator,
no mutation.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import decode_level_raw as DEC   # noqa: E402
import recompress_level_raw as REC  # noqa: E402

RAW = ROOT / "REBUILD" / "files" / "LEVEL01" / "LEVEL.RAW"
TOTAL_DECOMP = 1269304   # full LEVEL01 LEVEL.RAW, 69 chunks (CC2 byte-exact decode)


def be32(b, o):
    return struct.unpack_from(">I", b, o)[0]


def split_chunks(raw):
    off = 0
    out = []
    while off + 8 <= len(raw):
        w0 = be32(raw, off); w1 = be32(raw, off + 4)
        if w0 == 0xffffffff:
            break
        out.append(raw[off:off + 0xe + w1]); off += 0xe + w1
    return out


def main() -> int:
    if not RAW.exists():
        raise SystemExit(f"LEVEL.RAW not found: {RAW}")
    raw = RAW.read_bytes()

    full, nch, _end = DEC.decompress_file(raw)
    if nch != 69 or len(full) != TOTAL_DECOMP:
        raise SystemExit(f"decompress_file: {nch} chunks / {len(full)} B != 69 / {TOTAL_DECOMP}")
    print(f"decode OK ({nch} chunks -> {len(full)} B, byte-exact size)")

    chunks = split_chunks(raw)
    if len(chunks) != 69:
        raise SystemExit(f"chunk split {len(chunks)} != 69")

    for ci in (0, 31, 32, 35):
        comp = chunks[ci]
        plain = DEC.decompress_chunk(comp)
        prov = []
        plain2 = DEC.decompress_chunk(comp, prov=prov)
        if bytes(plain) != bytes(plain2):
            raise SystemExit(f"chunk {ci}: prov-mode decode differs from plain decode")
        if len(prov) != len(plain):
            raise SystemExit(f"chunk {ci}: prov length {len(prov)} != decode length {len(plain)}")
        # provenance well-formed: literal entries are valid compressed offsets within the chunk
        for i, p in enumerate(prov):
            if p is not None and not (0 <= p < len(comp)):
                raise SystemExit(f"chunk {ci}: prov[{i}]={p} out of range")
        # NOTE: a literal byte can be an LZ match SOURCE, so patching one compressed byte can
        # propagate (change >1 decoded byte). That's why size-neutral minimal-patch is unsafe
        # for this codec and robust edits must recompress (CC2). We only assert prov ALIGNS.
        # recompress round-trips (the editor path)
        rt = REC.compress_chunk(bytes(plain), comp[8:0xe])
        if bytes(DEC.decompress_chunk(rt)) != bytes(plain):
            raise SystemExit(f"chunk {ci}: recompress round-trip mismatch")
    print("per-chunk OK (prov aligned + in-range; recompress round-trip)")
    print("LEVEL.RAW codec (CC2) regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
