#!/usr/bin/env python3
"""Parse a LEVEL.RAW (compressed, A Bug's Life SCUS-94288) into its chunk table and
locate which chunk a decompressed runtime address comes from.

LEVEL.RAW = sequence of chunks (G24/G25):
  per chunk: [word0:BE32 decompressed size][word1:BE32 compressed size][6-byte header][word1 compressed bytes]
  next chunk at +0xe+word1 ; terminator word0 == 0xffffffff
  runtime: compressed loads at COMP_BASE (G22 0x80115aac); decompressor writes fp, fp += align4(word0) per chunk,
           ending at FP_TOP (G25 0x8015fcbc). s5 (compressed cursor) += word1+0xe per chunk.

The COMPRESSED walk (file offsets) is exact (validated vs G25 anchor coff=0xa7ae3 -> a0=0x801bd58f).
The DECOMPRESSED runtime offsets carry a small drift because per-subtype fp advances aren't uniformly
align4(word0) (texture/VRAM chunks etc.) — chunk identity is robust, exact byte offset needs the decoder/runtime.

Usage: parse_level_raw_chunks.py <LEVEL.RAW> [runtime_addr_hex]
"""
import struct, sys

COMP_BASE = 0x80115aac   # G22 runtime compressed load base
FP_TOP    = 0x8015fcbc   # G25 decompressor output top (a1 final)

def a4(x): return (x + 3) & ~3

def parse(path):
    data = open(path, 'rb').read(); N = len(data)
    be = lambda o: struct.unpack('>I', data[o:o+4])[0]
    chunks = []; c = 0; dec = 0
    while c + 8 <= N:
        w0 = be(c)
        if w0 == 0xffffffff: break
        w1 = be(c + 4)
        if w1 == 0 or c + 0xe + w1 > N + 0x400: break
        chunks.append(dict(i=len(chunks), coff=c, w0=w0, w1=w1, doff=dec))
        dec += a4(w0); c += w1 + 0xe
    return chunks, dec, c

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'REBUILD/files/LEVEL01/LEVEL.RAW'
    addr = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x8012c1d0
    chunks, total, cend = parse(path)
    base = FP_TOP - total
    print(f'{path}: {len(chunks)} chunks, total_decompressed=0x{total:x}, compressed_end=0x{cend:x}, est_base=0x{base:08x}')
    # validate against G25 anchor (compressed file offset 0xa7ae3)
    for k in chunks:
        if k['coff'] == 0xa7ae3:
            print(f'  anchor chunk {k["i"]} coff=0x{k["coff"]:x} comp=0x{k["w1"]:x} dec=0x{a4(k["w0"]):x} '
                  f'-> est decrt=0x{base+k["doff"]:08x} (G25 a0=0x801bd58f / a1=0x80143438)')
    # locate addr
    for k in chunks:
        s = base + k['doff']; e = s + a4(k['w0'])
        if s <= addr < e:
            print(f'  >>> addr 0x{addr:08x} -> CHUNK {k["i"]}: file_coff=0x{k["coff"]:x} '
                  f'comp=0x{k["w1"]:x} dec=0x{a4(k["w0"]):x} est_decrt=[0x{s:08x},0x{e:08x}) off_in_dec~0x{addr-s:x}')
            for j in range(max(0, k['i']-2), min(len(chunks), k['i']+3)):
                q = chunks[j]; qs = base + q['doff']
                print(f'      chunk {q["i"]:2}: coff=0x{q["coff"]:06x} comp=0x{q["w1"]:05x} dec=0x{a4(q["w0"]):05x} est_decrt=0x{qs:08x}')
            break

if __name__ == '__main__':
    main()
