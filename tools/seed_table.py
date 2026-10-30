#!/usr/bin/env python3
"""Typed parser/editor for the LEVEL.RAW chunk-31 seed-placement table.

Chunk 31 (PROPACK content marker ``0x23``) is the on-disk source for Flik's
plantable seeds — a system SEPARATE from the type-0x3f pickups (see the
``seed-planting-system`` note). This module is the editor-facing typed layer:
it parses the seed records out of the *decompressed* chunk, lets the editor move
a seed (edit X/Y/Z; metadata preserved verbatim), re-serializes, and then wraps
the EXISTING LEVEL.RAW codec (``decode_level_raw`` / ``recompress_level_raw``) to
splice the re-encoded chunk back onto the disc image. No parallel codec is
introduced here.

Schema — CONFIRMED against LEVEL01 (it reproduces the two operator-proven moves:
record #19 X=4837 "stuck" seed beside Flik, and record #26 X=6184 start seed):

    decompressed chunk 31:
      +0x00  u32   marker = 0x23
      +0x04  seed records, stride 0x1c, to end of chunk (LEVEL01 = 64 slots):
         +0x00  s32  X      (file coords; runtime world = X << 5)
         +0x04  s32  Y
         +0x08  s32  Z
         +0x0c  16 bytes    metadata (kind / flags / rooted-state, e.g. the
                            stuck-seed signature ``0b 03 .. 64 38 00 19 00``);
                            opaque to the editor and PRESERVED on a move.

A record is "active" when any of its XYZ or metadata bytes are non-zero
(LEVEL01 = 32 active of 64 slots). Inactive slots are zero padding; the editor
surfaces only active seeds by default but the parser returns every slot so the
table length is never silently changed.

This module contains NO copyrighted bytes; its tests drive it with synthetic
seed tables. The on-disc LEVEL.RAW it edits is owner-supplied local media.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, replace
from typing import Iterator

import decode_level_raw
import recompress_level_raw


# --- chunk-31 seed table geometry (confirmed; see module docstring) ----------
SEED_CHUNK_INDEX = 31
SEED_MARKER = 0x23
SEED_TABLE_OFFSET = 0x04
SEED_RECORD_STRIDE = 0x1C
SEED_META_LEN = 0x10
RUNTIME_SHIFT = 5            # runtime world coordinate = file coordinate << 5

# LEVEL.RAW chunk container layout (matches decode_level_raw / dump_level_raw):
#   +0x00 u32 BE word0 = decompressed size
#   +0x04 u32 BE word1 = compressed stream size
#   +0x08 6 bytes      = header (not consumed by the decompressor; preserved)
#   +0x0e ...          = compressed stream (word1 bytes)
CHUNK_HEADER_LEN = 0x0E
CHUNK_HEADER6_OFFSET = 0x08
CHUNK_TERMINATOR = 0xFFFFFFFF


@dataclass(frozen=True)
class SeedRecord:
    """One 0x1c-byte seed-placement record from chunk 31."""

    index: int
    offset: int             # chunk-local byte offset of this record
    x: int
    y: int
    z: int
    meta: bytes             # 16 opaque metadata bytes (+0x0c..+0x1b), preserved

    @property
    def is_active(self) -> bool:
        return self.x != 0 or self.y != 0 or self.z != 0 or any(self.meta)

    @property
    def runtime_xyz(self) -> tuple[int, int, int]:
        return self.x << RUNTIME_SHIFT, self.y << RUNTIME_SHIFT, self.z << RUNTIME_SHIFT


@dataclass(frozen=True)
class ChunkSpan:
    """A located LEVEL.RAW chunk (byte span + container header)."""

    index: int
    comp_off: int           # byte offset of the chunk's word0 within LEVEL.RAW
    word0: int              # decompressed size
    word1: int              # compressed stream size
    header6: bytes          # the 6 preserved container-header bytes

    @property
    def end(self) -> int:
        return self.comp_off + CHUNK_HEADER_LEN + self.word1


# ---------------------------------------------------------------------------
# Seed-record parse / serialize (pure; operates on a decompressed chunk)
# ---------------------------------------------------------------------------
def parse_seed_table(chunk: bytes) -> list[SeedRecord]:
    """Parse every seed record out of a decompressed chunk-31 buffer.

    Validates the ``0x23`` marker, then walks fixed 0x1c-byte records from
    +0x04 to the end of the buffer. Raises ``ValueError`` if the buffer is not a
    seed chunk or is malformed, so the editor never edits the wrong chunk.
    """
    if len(chunk) < SEED_TABLE_OFFSET + SEED_RECORD_STRIDE:
        raise ValueError(f"seed chunk too small: {len(chunk)} bytes")
    marker = struct.unpack_from("<I", chunk, 0)[0]
    if marker != SEED_MARKER:
        raise ValueError(f"not a seed chunk: marker 0x{marker:x} != 0x{SEED_MARKER:x}")
    body = len(chunk) - SEED_TABLE_OFFSET
    if body % SEED_RECORD_STRIDE != 0:
        raise ValueError(
            f"seed table body {body} not a whole number of 0x{SEED_RECORD_STRIDE:x}-byte records"
        )
    count = body // SEED_RECORD_STRIDE
    records: list[SeedRecord] = []
    for index in range(count):
        off = SEED_TABLE_OFFSET + index * SEED_RECORD_STRIDE
        x, y, z = struct.unpack_from("<iii", chunk, off)
        meta = bytes(chunk[off + 0x0C : off + SEED_RECORD_STRIDE])
        records.append(SeedRecord(index=index, offset=off, x=x, y=y, z=z, meta=meta))
    return records


def serialize_seed_table(chunk: bytes, records: list[SeedRecord]) -> bytes:
    """Write seed records back into a copy of ``chunk`` (length preserved).

    Only the record fields are written (X/Y/Z + the 16 metadata bytes); the
    chunk marker, any trailing padding, and the buffer length are untouched, so
    the table stays layout-compatible with the codec and the disc allocation.
    """
    buf = bytearray(chunk)
    for rec in records:
        if len(rec.meta) != SEED_META_LEN:
            raise ValueError(f"record #{rec.index} metadata must be {SEED_META_LEN} bytes")
        if rec.offset + SEED_RECORD_STRIDE > len(buf):
            raise ValueError(f"record #{rec.index} overruns chunk")
        struct.pack_into("<iii", buf, rec.offset, rec.x, rec.y, rec.z)
        buf[rec.offset + 0x0C : rec.offset + SEED_RECORD_STRIDE] = rec.meta
    if len(buf) != len(chunk):
        raise ValueError("serialize changed chunk length")
    return bytes(buf)


def move_record(records: list[SeedRecord], index: int, dx: int, dy: int, dz: int) -> list[SeedRecord]:
    """Return a new record list with seed ``index`` translated by (dx, dy, dz)."""
    rec = _select(records, index)
    moved = replace(rec, x=rec.x + dx, y=rec.y + dy, z=rec.z + dz)
    return [moved if r.index == index else r for r in records]


def set_record(records: list[SeedRecord], index: int, x: int, y: int, z: int) -> list[SeedRecord]:
    """Return a new record list with seed ``index`` set to absolute (x, y, z)."""
    rec = _select(records, index)
    moved = replace(rec, x=x, y=y, z=z)
    return [moved if r.index == index else r for r in records]


def _select(records: list[SeedRecord], index: int) -> SeedRecord:
    for rec in records:
        if rec.index == index:
            return rec
    raise ValueError(f"no seed record #{index} (have 0..{len(records) - 1})")


# ---------------------------------------------------------------------------
# LEVEL.RAW chunk read / splice (wraps the existing codec — no new codec)
# ---------------------------------------------------------------------------
def iter_chunks(raw: bytes) -> Iterator[ChunkSpan]:
    """Yield a ChunkSpan for each chunk in a LEVEL.RAW image."""
    off = 0
    index = 0
    while off + 8 <= len(raw):
        word0 = struct.unpack_from(">I", raw, off)[0]
        if word0 == CHUNK_TERMINATOR:
            break
        word1 = struct.unpack_from(">I", raw, off + 4)[0]
        header6 = bytes(raw[off + CHUNK_HEADER6_OFFSET : off + CHUNK_HEADER_LEN])
        span = ChunkSpan(index=index, comp_off=off, word0=word0, word1=word1, header6=header6)
        if span.end > len(raw):
            raise ValueError(f"chunk {index} overruns LEVEL.RAW ({span.end} > {len(raw)})")
        yield span
        off = span.end
        index += 1


def find_chunk(raw: bytes, index: int) -> ChunkSpan:
    for span in iter_chunks(raw):
        if span.index == index:
            return span
    raise ValueError(f"chunk index {index} not found in LEVEL.RAW")


def read_chunk_decompressed(raw: bytes, index: int) -> tuple[ChunkSpan, bytes]:
    """Locate chunk ``index`` and return (span, its decompressed bytes)."""
    span = find_chunk(raw, index)
    comp = raw[span.comp_off : span.end]
    out = bytearray()
    decode_level_raw.decompress_chunk(comp, out)
    if len(out) != span.word0:
        raise ValueError(f"chunk {index} decompressed to {len(out)} != word0 {span.word0}")
    return span, bytes(out)


def read_seed_chunk(raw: bytes, index: int = SEED_CHUNK_INDEX) -> tuple[ChunkSpan, list[SeedRecord]]:
    """Read + parse the seed table from a LEVEL.RAW image."""
    span, decompressed = read_chunk_decompressed(raw, index)
    return span, parse_seed_table(decompressed)


def splice_chunk(raw: bytes, index: int, new_decompressed: bytes) -> bytes:
    """Re-encode ``new_decompressed`` for chunk ``index`` and splice it in place.

    Preserves the chunk's 6 container-header bytes, re-encodes via the proven
    ``recompress_level_raw.compress_chunk`` (literal-run encoder, ~1.02x), and
    asserts the new chunk decodes back byte-exact before returning the new image.
    Unedited chunks keep their original (smaller) compressed bytes.
    """
    span = find_chunk(raw, index)
    new_chunk = recompress_level_raw.compress_chunk(new_decompressed, header6=span.header6)
    verify = bytearray()
    decode_level_raw.decompress_chunk(new_chunk, verify)
    if bytes(verify) != new_decompressed:
        raise ValueError("re-encoded chunk does not round-trip; refusing to splice")
    return raw[: span.comp_off] + new_chunk + raw[span.end :]


def active_count(records: list[SeedRecord]) -> int:
    return sum(1 for r in records if r.is_active)
