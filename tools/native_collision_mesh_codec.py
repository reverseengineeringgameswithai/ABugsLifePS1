#!/usr/bin/env python3
"""tools/native_collision_mesh_codec.py — byte-exact codec for ABL per-sector collision-mesh BLOCKS
(LEVEL.RAW chunk 32). Decoded 2026-07-06 via live disasm of the candidate-builder FUNC_80037320 + floor
resolver FUNC_80038090 (see src_re/collision_source_converter_80030f60.c "FULLY DECODED FORMAT").

BLOCK = sequence of GROUPS, terminated by a group whose marker s16 < 0. GROUP header (12 B) then records:
    +0x00 s16 marker (>=0 valid)   +0x02 s16 count
    +0x04 s16 aabb.minX  +0x06 s16 aabb.extX  +0x08 s16 aabb.minZ  +0x0a s16 aabb.extZ   (sector-local >>5)
    +0x0c: count * 0x20-byte PLANE records.  group size = 12 + count*0x20.
PLANE record (0x20 B, floor when normal.y<0):
    +0x00 normal.x  +0x02 normal.y  +0x04 normal.z   (|normal|==0x4000)
    +0x06 V0.x      +0x08 V0.y      +0x0a V0.z        (ref, sector-local, <<5 at use)
    +0x0c edge1.x +0x0e edge1.y +0x10 edge1.z
    +0x12 edge2.x +0x14 edge2.y +0x16 edge2.z       (V1/V2 = V0 + edge1/edge2)
    +0x18 fp.minX +0x1a fp.extX +0x1c s8 fp.minYhi(*64 + V0.y) +0x1d u8 fp.extY(*64)
    +0x1e s8 fp.minZhi(*64 + V0.z) +0x1f s8 fp.extZ(*64)  (player candidate footprint)
  FOOTPRINT (decoded 2026-07-06, byte-exact vs real records): X = [rec+0x18, +rec+0x1a]; Z fine-test extent =
  rec+0x1f*64 (candidate builder, gates selection); grid-builder over-inflates Z to rec+0x1f*4096. The player
  builder FUNC_8003633C also gates against the packed Y range at rec+0x1c/+0x1d; the enemy-only builder does
  not. Real records use SMALL footprints (rec+0x1f ~6-19); TILE an area with many small tris, don't use one big
  quad (inflates the grid AABB, breaks selection).
  WINDING: real FLOOR triangles are CLOCKWISE ((V1-V0)x(V2-V0) < 0); the point-in-poly floor test needs CW.
  FRAME: -Y is UP (a floor catches a falling Flik only when ABOVE him = more negative Y).

This module is geometry-only (no chunk-32 splice/recompress — that's the emitter/collision tool). It exists to
(1) prove the format via byte-exact round-trip, (2) give the emitter a structured builder for records/groups.
"""
from __future__ import annotations
import math
import struct
from dataclasses import dataclass, field
from typing import List

REC_SIZE = 0x20
GROUP_HDR = 0x0c
NORMAL_ONE = 0x4000


@dataclass
class Plane:
    raw: bytes  # the exact 0x20 bytes (authoritative for round-trip)

    # --- typed accessors (decode on demand; the emitter builds via from_fields) ---
    def s16(self, off): return struct.unpack_from("<h", self.raw, off)[0]
    @property
    def normal(self): return (self.s16(0), self.s16(2), self.s16(4))
    @property
    def v0(self): return (self.s16(6), self.s16(8), self.s16(0xa))
    @property
    def edge_vectors(self):
        """The two complete XYZ vectors consumed by FUNC_80032610.

        Phase-4 disassembly and the LEVEL01 native-terrain round trip establish
        that +0x0c..+0x16 is two packed ``SVECTOR``-style edges, not three X/Z
        polygon deltas.  Keeping this accessor byte-literal prevents a normal-
        based reconstruction from hiding a corrupt on-disc layout.
        """
        return (struct.unpack_from("<3h", self.raw, 0x0c),
                struct.unpack_from("<3h", self.raw, 0x12))

    @property
    def deltas(self):
        """Compatibility X/Z projection of the two encoded triangle edges."""
        return tuple((dx, dz) for dx, _dy, dz in self.edge_vectors)
    @property
    def footprint(self):  # (minX, extX, minZ, extZ) sector-local file-frame
        minx, extx = self.s16(0x18), self.s16(0x1a)
        minz_hi, extz = struct.unpack_from("<bb", self.raw, 0x1e)
        v0z = self.s16(0xa)
        return (minx, extx, v0z + minz_hi * 64, extz * 64)

    @property
    def vertical_footprint(self):
        """Return the player-builder Y candidate range in sector-local file units.

        FUNC_8003633C reads record bytes +0x1c/+0x1d exactly like the packed Z
        range at +0x1e/+0x1f: signed min-Y delta and unsigned extent, both in
        64-file-unit steps.  The enemy-only builder does not read this pair,
        which is why the field was previously mistaken for padding.
        """
        miny_hi, exty = struct.unpack_from("<bB", self.raw, 0x1c)
        return (self.v0[1] + miny_hi * 64, exty * 64)

    @staticmethod
    def from_fields(normal, v0, edge_vectors, fp, vertical_fp=None) -> "Plane":
        """Pack a native triangle record from two complete XYZ edge vectors."""
        b = bytearray(REC_SIZE)
        struct.pack_into("<3h", b, 0, *[int(v) for v in normal])
        struct.pack_into("<3h", b, 6, *[int(v) for v in v0])
        if len(edge_vectors) != 2 or any(len(edge) != 3 for edge in edge_vectors):
            raise ValueError("collision plane needs exactly two XYZ edge vectors")
        edge1, edge2 = edge_vectors
        struct.pack_into("<3h", b, 0x0c, *[int(value) for value in edge1])
        struct.pack_into("<3h", b, 0x12, *[int(value) for value in edge2])
        minx, extx, minz, extz = fp
        struct.pack_into("<h", b, 0x18, int(minx)); struct.pack_into("<h", b, 0x1a, int(extx))
        if vertical_fp is None:
            ys = [int(v0[1]),
                  int(v0[1]) + int(edge1[1]),
                  int(v0[1]) + int(edge2[1])]
            vertical_fp = (min(ys), max(ys) - min(ys))
        miny, exty = (int(value) for value in vertical_fp)
        if exty < 0:
            raise ValueError("collision Y footprint extent must be non-negative")
        miny_hi = math.floor((miny - int(v0[1])) / 64)
        quantized_miny = int(v0[1]) + miny_hi * 64
        exty_hi = math.ceil((miny + exty - quantized_miny) / 64)
        if not -128 <= miny_hi <= 127 or not 0 <= exty_hi <= 255:
            raise ValueError("collision Y footprint exceeds packed byte range")
        struct.pack_into("<bB", b, 0x1c, miny_hi, exty_hi)
        minz_hi = int(round((minz - v0[2]) / 64.0)); extz_hi = int(round(extz / 64.0))
        struct.pack_into("<bb", b, 0x1e, max(-128, min(127, minz_hi)), max(-128, min(127, extz_hi)))
        return Plane(bytes(b))


@dataclass
class Group:
    marker: int
    aabb: tuple            # (minX, extX, minZ, extZ)
    planes: List[Plane] = field(default_factory=list)


def decode_block(data: bytes, off: int = 0, max_end: int | None = None):
    """Walk groups from `off` until a marker<0 header (the block terminator) or max_end.
    Returns (groups, end_off) where end_off is the offset of the byte AFTER the terminator header."""
    if max_end is None:
        max_end = len(data)
    groups = []
    p = off
    while p + 4 <= max_end:                         # terminator only needs marker+count (4 B)
        marker, count = struct.unpack_from("<2h", data, p)
        if marker < 0:
            return groups, p + 4  # terminator group header (marker + count consumed by the game's bgez)
        aminx, aextx, aminz, aextz = struct.unpack_from("<4h", data, p + 4)
        if count < 0 or p + GROUP_HDR + count * REC_SIZE > max_end:
            # a valid group never overruns its block; this is a non-mesh block (e.g. the chunk-32
            # relocation region @0x35830+, sectors 178-188) or a bad offset — refuse rather than
            # emit short records that break downstream field reads.
            raise ValueError(f"malformed collision block: group @0x{p:x} count={count} overruns "
                             f"max_end=0x{max_end:x} (not a group/record mesh)")
        recs = []
        rp = p + GROUP_HDR
        for _ in range(count):
            recs.append(Plane(bytes(data[rp:rp + REC_SIZE])))
            rp += REC_SIZE
        groups.append(Group(marker, (aminx, aextx, aminz, aextz), recs))
        p = rp
    return groups, p


def encode_block(groups: List[Group], terminator: bytes | None = None) -> bytes:
    """Serialize groups + a terminator header (marker<0). Byte-exact inverse of decode_block for real blocks
    when `terminator` supplies the original terminator header bytes (else a minimal 0xFFFF,0 header)."""
    out = bytearray()
    for g in groups:
        out += struct.pack("<6h", g.marker, len(g.planes), *g.aabb)
        for pl in g.planes:
            assert len(pl.raw) == REC_SIZE
            out += pl.raw
    out += terminator if terminator is not None else struct.pack("<2h", -1, 0)
    return bytes(out)


if __name__ == "__main__":
    # Round-trip proof on the confirmed sector-119 block (chunk-32 0x1bf90, 16 groups / 180 planes).
    dec = open("tools/LEVEL_RAW_decompressed/LEVEL.RAW.decompressed", "rb").read()
    C0 = 617688
    chunk = dec[C0:C0 + 236944]
    b119 = 0x1bf90
    groups, end = decode_block(chunk, b119)
    nplanes = sum(len(g.planes) for g in groups)
    print(f"sec119 block @0x{b119:x}: {len(groups)} groups, {nplanes} planes, terminator at 0x{end:x}")
    # re-encode the groups (without terminator) and compare to the original group bytes
    orig = chunk[b119:end - 4]                       # groups only (exclude terminator header)
    re = encode_block(groups, terminator=b"")        # groups only
    print("groups round-trip byte-exact:", re == orig, f"({len(re)} vs {len(orig)} B)")
    # Per-record typed round trip. Footprint packing is lossy for odd Z, so
    # retain the already-decoded packed vertical footprint explicitly.
    p0 = groups[3].planes[0]
    rebuilt = Plane.from_fields(p0.normal, p0.v0, p0.edge_vectors, p0.footprint,
                                p0.vertical_footprint)
    print("record from_fields typed fields match:",
          rebuilt.normal == p0.normal and rebuilt.v0 == p0.v0
          and rebuilt.edge_vectors == p0.edge_vectors
          and rebuilt.vertical_footprint == p0.vertical_footprint)
