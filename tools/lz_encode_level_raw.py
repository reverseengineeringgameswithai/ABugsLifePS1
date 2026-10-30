#!/usr/bin/env python3
"""LEVEL.RAW LZ ENCODER with real back-references (HRE-009 enabler; supersedes the
literal-run-only recompress_level_raw for size-critical chunk edits).

The decoder (tools/decode_level_raw.py, byte-exact port of fcn.8001a1dc) defines the
format; this encoder produces streams that decoder accepts, at compression ratios close
to the original tool's (the literal-run-only encoder GROWS chunks ~1.02x of the raw
size, which overflows LEVEL.RAW's fixed LBA-3069 sector budget for any big chunk edit
-- e.g. the chunk-29 backdrop image, 13072 B raw vs 6963 B originally compressed).

GRAMMAR (from the decoder, empirically verified against the chunk-0 oracle):
  stream = [word0 BE: decompressed size][word1 BE: payload size][6 header bytes]
           [reg byte 0][interleaved payload bytes + reg bytes]
  Bit register: reg byte 0 supplies only its bits 5..0 (top 2 consumed by init, dead);
  every later reg byte supplies its 8 bits MSB->LSB. A reg byte is fetched from the
  stream at the moment the register drains, so reg bytes interleave AFTER whatever
  payload bytes were consumed while the previous register was live.
  SENTINEL QUIRK: the MAIN-loop flag reads are unmasked; when a flag read lands on a
  drained register the reader consumes the sentinel (always 1 -> MATCH label), reloads,
  and the REAL flag is the new reg byte's MSB (1 = match body, 0 = single literal).
  dp_bit-style reads reload BEFORE extracting, so they have no forced values.

  tokens:
    literal pair loop: flag 0, byte, flag2 (0 = another literal + back to MAIN)
    match: flag 1, then LENGTH bits, then DIST-HIGH bits, then dist-low byte:
      len 2: [0]              (fast path; dist high forced 0 -> back dist 1..256)
      len 3: [1,0]
      len 4: [<b1=0 path> 0,0]   len 5: [0,1,0]... encoded below in LEN_BITS
      len 9..263: [1,1,1] + byte (len-8; byte 0 reserved for the terminator)
    dist-high (back dist = (high<<8 | low) + 1, high 0..15):
      0:[0]  1:[1,1,0]  2:[1,0,0,0]  3:[1,0,0,1]
      4..7:[1,b,1,c,1] with high=(2b+c)|4    8..15:[1,b,1,c,0,e] high=(((2b+c)|4)<<1)+e
    literal run (escape len==9 in the short-length tree): [0,1,1,1] + 4 bits n ->
      exactly 4*(n+3) literal bytes (12..72), cheap for long incompressible stretches.
    terminator: flag 1, [1,1,1], byte 0, then one bit 0.
"""
import struct
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decode_level_raw


# --- length encodings (bits after the match flag), from the decoder's tree ---
# len 2..8 fixed bit strings; len>=9 via the long form.
LEN_BITS = {
    2: (1, 0),          # b1=1 b2=0 -> DIST (dist-high forced 0!)
    3: (1, 1, 0),       # b1=1 b2=1 b3=0
    4: (0, 0, 0),       # A470: t0=2*2+0=4, stop
    5: (0, 1, 0),       # t0=5, stop
    6: (0, 0, 1, 0),    # t0=4 -> 3 -> 3*2+0=6
    7: (0, 0, 1, 1),    # -> 7
    8: (0, 1, 1, 0),    # t0=5 -> 4 -> 8
    # (0,1,1,1) = t0==9 -> LITRUN escape
}
LITRUN_BITS = (0, 1, 1, 1)


def dist_high_bits(h):
    if h == 0:  return (0,)
    if h == 1:  return (1, 1, 0)
    if h in (2, 3): return (1, 0, 0, h - 2)
    if 4 <= h <= 7:
        v = h - 4          # (2b+c) = v
        return (1, (v >> 1) & 1, 1, v & 1, 1)
    if 8 <= h <= 15:
        v = h - 8          # ((2b+c)|4)<<1 + e ... (2b+c) = (h>>1)-4, e = h&1
        u = (h >> 1) - 4
        return (1, (u >> 1) & 1, 1, u & 1, 0, h & 1)
    raise ValueError(h)


class Writer:
    """Mirrors the decoder's register mechanics: places reg bytes at the stream
    positions where the reader will fetch them."""
    def __init__(self):
        self.out = bytearray()          # payload+reg byte stream (after the 14-B header)
        self.slot = None                # index of the reg byte being filled
        self.slot_bits = 0              # bits already placed in it
        self.slot_cap = 0               # capacity (6 for byte 0, else 8)
        self._alloc(first=True)

    def _alloc(self, first=False):
        self.slot = len(self.out)
        self.out.append(0)
        self.slot_bits = 0
        self.slot_cap = 6 if first else 8

    def _put(self, v):
        # MSB-first within the byte; byte 0 uses bits 5..0 (cap 6)
        pos = (self.slot_cap - 1) - self.slot_bits
        if v:
            self.out[self.slot] |= (1 << pos)
        self.slot_bits += 1

    def bit(self, v, main_flag=False):
        """Emit one grammar bit. main_flag=True for the unmasked MAIN-loop flag reads
        (they hit the sentinel when the register is drained)."""
        if self.slot_bits < self.slot_cap:
            self._put(v)
            return
        # register drained
        if main_flag:
            # reader consumes the sentinel (forced 1 -> MATCH label), reloads, and the
            # real flag = the new byte's MSB (match-reload path: 1=match body, 0=literal)
            self._alloc()
            self._put(v)
        else:
            # dp_bit reloads before extracting: bit = new byte's MSB
            self._alloc()
            self._put(v)

    def byte(self, b):
        self.out.append(b & 0xFF)


def encode_tokens(tokens, header6=b"\x00\x00\x00\x00\x00\x00", raw_len=0):
    """tokens: list of ('lit', bytes), ('litrun', bytes len 12..72 multiple of 4),
    ('match', length, dist).  dist = back distance (1..4096)."""
    w = Writer()
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t[0] == 'lit':
            data = t[1]
            j = 0
            while j < len(data):
                w.bit(0, main_flag=True)     # flag: literal
                w.byte(data[j]); j += 1
                if j < len(data):
                    w.bit(0, main_flag=True) # flag2: another literal
                    w.byte(data[j]); j += 1
                else:
                    # odd literal: flag2 decides the NEXT token
                    nxt = tokens[i + 1] if i + 1 < n else None
                    if nxt is not None and nxt[0] == 'match':
                        w.bit(1, main_flag=True)   # flag2=1 -> match body
                        _emit_match(w, nxt[1], nxt[2])
                        i += 1                     # consumed the match
                    elif nxt is None:
                        w.bit(1, main_flag=True)   # -> terminator body
                        _emit_terminator(w)
                        return _finish(w, header6, raw_len)
                    else:
                        # next is another literal group / litrun: close the pair loop
                        # cheaply by folding its first byte? keep it simple: flag2=0
                        # requires another literal -- merge groups upstream instead.
                        raise ValueError("adjacent literal groups; merge them upstream")
        elif t[0] == 'litrun':
            data = t[1]
            assert len(data) % 4 == 0 and 12 <= len(data) <= 72
            w.bit(1, main_flag=True)
            for b in LITRUN_BITS: w.bit(b)
            k = len(data) // 4 - 3
            for shift in (3, 2, 1, 0):
                w.bit((k >> shift) & 1)
            for b in data: w.byte(b)
        elif t[0] == 'match':
            w.bit(1, main_flag=True)
            _emit_match(w, t[1], t[2])
        i += 1
    # terminator (no trailing odd literal consumed it)
    w.bit(1, main_flag=True)
    _emit_terminator(w)
    return _finish(w, header6, raw_len)


def _emit_match(w, length, dist):
    d = dist - 1
    high, low = d >> 8, d & 0xFF
    if length == 2:
        assert high == 0, "len-2 matches encode only dist<=256"
        for b in LEN_BITS[2]: w.bit(b)
        w.byte(low)
        return
    if length <= 8:
        for b in LEN_BITS[length]: w.bit(b)
    else:
        assert 9 <= length <= 263
        for b in (1, 1, 1): w.bit(b)
        w.byte(length - 8)
    for b in dist_high_bits(high): w.bit(b)
    w.byte(low)


def _emit_terminator(w):
    for b in (1, 1, 1): w.bit(b)
    w.byte(0)
    w.bit(0)


def _finish(w, header6, raw_len):
    body = bytes(w.out)
    return struct.pack(">II", raw_len, len(body)) + bytes(header6) + body


# ---------------------------------------------------------------------------
# greedy tokenizer: hash-chain matcher, window 4096, len 2..263
# ---------------------------------------------------------------------------
def tokenize(data):
    n = len(data)
    head = {}
    prev = [-1] * n
    tokens = []
    lit = bytearray()

    def flush_lit():
        nonlocal lit
        if not lit:
            return
        buf = bytes(lit); lit = bytearray()
        # carve litruns out of long stretches (4*(k+3), 12..72 bytes each)
        while len(buf) >= 12:
            take = min(72, len(buf) - (len(buf) % 4)) if len(buf) >= 72 else (len(buf) // 4) * 4
            take = min(72, take)
            if take < 12:
                break
            tokens.append(('litrun', buf[:take]))
            buf = buf[take:]
        if buf:
            tokens.append(('lit', buf))

    i = 0
    while i < n:
        best_len = 0; best_dist = 0
        if i + 2 <= n:
            key = data[i:i+2]
            j = head.get(key, -1)
            tries = 0
            while j >= 0 and tries < 64:
                dist = i - j
                if dist > 4096:
                    break
                # extend
                l = 0
                maxl = min(263, n - i)
                while l < maxl and data[j + l] == data[i + l]:
                    l += 1
                if l > best_len or (l == best_len and dist < best_dist):
                    # len-2 only valid for dist<=256
                    if l >= 3 or (l == 2 and dist <= 256):
                        best_len, best_dist = l, dist
                j = prev[j]
                tries += 1
        if best_len >= 2:
            flush_lit()
            tokens.append(('match', best_len, best_dist))
            end = i + best_len
            while i < end:
                if i + 2 <= n:
                    key = data[i:i+2]
                    prev[i] = head.get(key, -1)
                    head[key] = i
                i += 1
        else:
            lit.append(data[i])
            if i + 2 <= n:
                key = data[i:i+2]
                prev[i] = head.get(key, -1)
                head[key] = i
            i += 1
    flush_lit()
    # merge adjacent lit groups (litrun carving can leave lit,lit sequences)
    merged = []
    for t in tokens:
        if t[0] == 'lit' and merged and merged[-1][0] == 'lit':
            merged[-1] = ('lit', merged[-1][1] + t[1])
        else:
            merged.append(list(t) if t[0] == 'lit' else t)
    return [tuple(t) if isinstance(t, list) else t for t in merged]


def compress_chunk(data, header6=b"\x00\x00\x00\x00\x00\x00"):
    """Drop-in alternative to recompress_level_raw.compress_chunk with REAL LZ.
    Returns the full chunk (14-B header + stream) and asserts a byte-exact round-trip."""
    tokens = tokenize(bytes(data))
    chunk = encode_tokens(tokens, header6=header6, raw_len=len(data))
    verify = bytearray()
    decode_level_raw.decompress_chunk(chunk, verify)
    if bytes(verify) != bytes(data):
        n = min(len(verify), len(data))
        div = next((k for k in range(n) if verify[k] != data[k]), n)
        raise AssertionError(f"round-trip mismatch at 0x{div:x} ({len(verify)}/{len(data)} B)")
    return chunk


if __name__ == "__main__":
    # self-test against the pinned chunk-0 oracle
    here = os.path.dirname(os.path.abspath(__file__))
    want = open(os.path.join(here, "raw_chunk0_decompressed.bin"), "rb").read()
    orig = open(os.path.join(here, "raw_chunk0_compressed.bin"), "rb").read()
    chunk = compress_chunk(want, header6=orig[8:14])
    print(f"chunk0: raw {len(want)} B, original {len(orig)} B, re-encoded {len(chunk)} B "
          f"({len(chunk)/len(orig):.3f}x of original) -- round-trip OK")
