#!/usr/bin/env python3
"""tools/native_mesh_codec.py -- byte-exact codec for the native FUNC_80010000 mesh payload.

The DECODE half of the round-trip already exists in level_editor/scene_importer.py
(decode_payload/_extract_faces), but it is LOSSY for re-encoding: it triangulates quads,
tracks per-batch texpage inheritance, and resyncs past marker words -- so it cannot rebuild
the original bytes. This module keeps the payload in a STRUCTURED form (vertices + the raw
command-stream tokens: batches of quads, plus any resync words) so encode() reproduces the
original bytes EXACTLY. That byte-exact round-trip is the M1 de-risk for the native-terrain
pivot (plan: ~/.claude/plans/steady-stargazing-coral.md); the same structure is the authoring
substrate for M2/M3 (edit verts/quads, re-encode, inject).

Format (see ObsidianVault/Systems/Tier 3 - GTE Render Path.md + geometry_g57_command_stream_texpage.md):
  u32 vertexCount
  Vertex[count]              stride 0x0c: s16 x,y,z ; s16 pad ; u32 attr
  command stream: repeat until 0xFFFFFFFF:
     batch = [u16 ctrl][u16 prim_count] then prim_count x { u16 v0,v1,v2,v3 ; u16 uv0..uv3 }
       (v* = vertex BYTE offsets = idx*0x0c ; uv = lo:U hi:V) -- OR a bare resync u16 word.
  u32 0xFFFFFFFF terminator
`ctrl & 0x1f` = GP0 VRAM texpage; `ctrl & 0x8000` = inherit current page.
"""
from __future__ import annotations
import struct
from dataclasses import dataclass, field

VSTRIDE = 0x0C
PRIM_SZ = 16
TERM = 0xFFFFFFFF


@dataclass
class Vertex:
    x: int; y: int; z: int; pad: int; attr: int


@dataclass
class Prim:
    """One quad primitive: 4 vertex BYTE offsets + 4 packed UV halfwords (lo=U, hi=V)."""
    voff: tuple  # (o0,o1,o2,o3) byte offsets into the vertex table
    uv: tuple    # (uv0,uv1,uv2,uv3) raw u16 (lo=U, hi=V)


@dataclass
class Batch:
    ctrl: int
    prims: list  # list[Prim]


@dataclass
class RawWord:
    """A command-stream u16 the decoder resyncs past (marker / misaligned header). Preserved
    verbatim so the round-trip stays byte-exact."""
    value: int


@dataclass
class Payload:
    verts: list           # list[Vertex]
    stream: list          # ordered list of Batch | RawWord (command stream before terminator)
    trailer: bytes = b""  # any bytes between the terminator and the true payload end (usually b"")
    terminated: bool = True   # False for payloads whose stream runs to the next payload with no 0xFFFFFFFF


def _u16(d, o): return struct.unpack_from("<H", d, o)[0]
def _u32(d, o): return struct.unpack_from("<I", d, o)[0]
def _s16(d, o): return struct.unpack_from("<h", d, o)[0]


def find_terminator(data: bytes, off: int, limit: int) -> int:
    """Vertex table end onward, find the 0xFFFFFFFF command-stream terminator (matches
    decode_payload's search: step by 2, first aligned-or-not 0xFFFFFFFF)."""
    count = _u32(data, off)
    o = off + 4 + count * VSTRIDE
    while o + 4 <= limit:
        if _u32(data, o) == TERM:
            return o
        o += 2
    raise ValueError(f"no 0xFFFFFFFF terminator for payload @0x{off:x} within 0x{limit:x}")


def decode(data: bytes, off: int, term: int | None = None, limit: int | None = None) -> Payload:
    """Decode the payload at `off` into a Payload. `term` = terminator offset; if None it is
    searched within `limit` (next payload / EOF), and a payload with NO 0xFFFFFFFF before `limit`
    decodes with terminated=False and stream running to `limit`."""
    count = _u32(data, off)
    if not (0 < count < 100000):
        raise ValueError(f"implausible vertex count {count} @0x{off:x}")
    vbase = off + 4
    verts = [Vertex(_s16(data, vbase + i * VSTRIDE), _s16(data, vbase + i * VSTRIDE + 2),
                    _s16(data, vbase + i * VSTRIDE + 4), _s16(data, vbase + i * VSTRIDE + 6),
                    _u32(data, vbase + i * VSTRIDE + 8)) for i in range(count)]
    cmd_start = vbase + count * VSTRIDE
    terminated = True
    if term is None:
        lim = limit if limit is not None else len(data)
        try:
            term = find_terminator(data, off, lim)
        except ValueError:
            term = lim            # no terminator before the boundary
            terminated = False
    max_off = count * VSTRIDE
    stream: list = []
    o = cmd_start
    while o + 4 <= term:
        ctrl = _u16(data, o); cnt = _u16(data, o + 2); base = o + 4
        # SAME batch-validity test as scene_importer._extract_faces (first 2 prims aligned+in-range)
        valid = (1 <= cnt and base + cnt * PRIM_SZ <= term and all(
            0 <= _u16(data, base + p * PRIM_SZ + k * 2) < max_off
            and _u16(data, base + p * PRIM_SZ + k * 2) % VSTRIDE == 0
            for p in range(min(cnt, 2)) for k in range(4)))
        if valid:
            prims = []
            for p in range(cnt):
                pb = base + p * PRIM_SZ
                prims.append(Prim(tuple(_u16(data, pb + k * 2) for k in range(4)),
                                  tuple(_u16(data, pb + 8 + k * 2) for k in range(4))))
            stream.append(Batch(ctrl, prims))
            o = base + cnt * PRIM_SZ
        else:
            stream.append(RawWord(ctrl))
            o += 2
    # any odd byte between the last consumed word and the terminator (o != term) -> preserve
    trailer = data[o:term] if o != term else b""
    return Payload(verts, stream, trailer, terminated)


def encode(p: Payload) -> bytes:
    """Serialize a Payload back to bytes (count + verts + command stream + terminator)."""
    out = bytearray()
    out += struct.pack("<I", len(p.verts))
    for v in p.verts:
        out += struct.pack("<hhhhI", v.x, v.y, v.z, v.pad, v.attr)
    for tok in p.stream:
        if isinstance(tok, Batch):
            out += struct.pack("<HH", tok.ctrl, len(tok.prims))
            for pr in tok.prims:
                out += struct.pack("<4H", *pr.voff) + struct.pack("<4H", *pr.uv)
        else:  # RawWord
            out += struct.pack("<H", tok.value)
    out += p.trailer
    if p.terminated:
        out += struct.pack("<I", TERM)
    return bytes(out)


def roundtrip_ok(data: bytes, off: int, limit: int | None = None) -> tuple[bool, int, int]:
    """Decode+encode the payload at off; return (byte_identical, enc_len, orig_span_len).
    Handles both terminated payloads and no-terminator payloads that run to `limit`."""
    lim = limit if limit is not None else len(data)
    try:
        end = find_terminator(data, off, lim) + 4
    except ValueError:
        end = lim                    # no terminator -> spans to the next payload boundary
    span = data[off:end]
    enc = encode(decode(data, off, limit=lim))
    return (enc == span, len(enc), len(span))


if __name__ == "__main__":
    import sys
    dat = sys.argv[1] if len(sys.argv) > 1 else "DAT/LEVEL01_LEVEL.DAT"
    data = open(dat, "rb").read()
    # Candidate A @ 0x188cc + siblings B/C/D/E from the investigation
    for name, off in [("A", 0x188cc), ("B", 0x38870), ("C", 0x38cb0), ("D", 0x38548), ("E", 0x2d460)]:
        try:
            ok, el, ol = roundtrip_ok(data, off)
            print(f"payload {name} @0x{off:05x}: roundtrip {'OK' if ok else 'MISMATCH'} (enc {el} / orig {ol} B)")
        except Exception as e:
            print(f"payload {name} @0x{off:05x}: ERROR {e}")
