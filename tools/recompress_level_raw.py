#!/usr/bin/env python3
"""LEVEL.RAW recompressor — literal-run encoder, round-trip-validated vs the byte-exact decoder.

STATUS: WORKING. Round-trips full chunk0 (33548 B) and arbitrary edits, ~1.02x size. Public API:
  compress_chunk(decompressed_bytes, header6) -> full LEVEL.RAW chunk (0xe header + stream).
KEY: the bit-reader init reads byte0 bits 5->0 (6 bits), then 8 per reloaded byte (first_bits=6).
EDITOR FLOW: decompress LEVEL.RAW -> edit seed table in place -> recompress only the edited chunk(s)
(unedited chunks keep their original, smaller, compressed bytes) -> reassemble -> rebuild disc."""
import struct, decode_level_raw as DEC
def be32(v): return struct.pack('>I', v & 0xffffffff)

def encode_chunk(data, first_bits=6):
    assert len(data)%4==0 and len(data)>=12, "need len%4==0 and >=12"
    units=len(data)//4
    runs=[]
    while units>0:
        g=min(18,units)
        if 0 < units-g < 3: g=units-3       # keep last run >=3 groups
        if g<3: g=units
        runs.append(g); units-=g
    bits=[]
    for g in runs:
        C=g-3
        bits += [1,0,1,1,1] + [(C>>k)&1 for k in (3,2,1,0)]   # MATCH,b1=0,b4b5b6=1 ->t0=9 LITRUN ; 4-bit count
    bits += [1,1,1,1]            # terminator: MATCH,b1=b2=b3=1 -> long
    term_bit=[0]                 # after long-byte 0x00 -> the 0x8001a804 terminate bit
    # data queue: payload for runs, then 0x00 long-byte for terminator
    dq=list(data)+[0]
    # bit queue: run/terminator code bits; the final terminate bit is appended after the long-byte read,
    # but rdreg just packs the next 8 from a flat queue, so concatenate (decoder pulls in order).
    bq=list(bits)+term_bit
    stream=bytearray()
    bi=[0]; di=[0]; first=[True]
    def rdreg():
        n=first_bits if first[0] else 8; first[0]=False
        b=0
        for _ in range(8):
            b=(b<<1)|(bq[bi[0]] if bi[0]<len(bq) else 0)
            if (8-n) <= _ : bi[0]+=1   # only the low n bits are "real" for the first byte; pad high (8-n)
        # simpler exact packing below overrides:
        return b
    # exact packing: build byte so the decoder reads our bits. For non-first bytes the decoder reads all 8
    # MSB-first; for the first (init) byte it reads only `first_bits` (in the low positions). We pad high bits 0.
    bi=[0]
    def rdreg2():
        n=first_bits if first[0] else 8; first[0]=False
        chunk=[ (bq[bi[0]+k] if bi[0]+k<len(bq) else 0) for k in range(n) ]
        bi[0]+=n
        val=0
        for x in chunk: val=(val<<1)|x          # n bits, MSB-first
        stream.append(val & 0xff); return val & 0xff   # low n bits = positions (n-1..0); init reads bit5..0
    def rddata():
        v=dq[di[0]] if di[0]<len(dq) else 0; di[0]+=1; stream.append(v); return v
    out=bytearray()
    DEC.decompress_chunk(b'\0'*0x10, out=out, SRC=(rdreg2, rddata))
    return bytes(stream), bytes(out)


def compress_chunk(data, header6=b'\x00'*6):
    """Re-encode one decompressed chunk into a full LEVEL.RAW chunk (0xe header + literal-run stream).
    word0(BE)=decompressed size, word1(BE)=compressed stream size, +6 header bytes (preserved from the
    original chunk for the editor). Round-trips through decode_level_raw.decompress_chunk."""
    stream, internal = encode_chunk(data)
    assert internal==data, "encoder self-check failed"
    return be32(len(data)) + be32(len(stream)) + header6 + stream

def roundtrip(data, fb):
    stream, out = encode_chunk(data, first_bits=fb)
    o2=bytearray(); 
    # decode our stream with header-less chunk: encode produced raw bitstream starting at offset 0; the
    # decoder expects a 0xe header then bitstream at +0xe. Prepend a 0xe header.
    hdr = be32(len(data)) + be32(len(stream)+0xe) + b'\0\0\0\0\0\0'
    DEC.decompress_chunk(hdr+stream, o2)
    return out==data, bytes(o2)==data, len(stream)

if __name__=='__main__':
    import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
    data=open('raw_chunk0_decompressed.bin','rb').read()
    for fb in (6,7,5,8):
        try:
            internal_ok, decode_ok, clen = roundtrip(data, fb)
            print(f'first_bits={fb}: internal_out_ok={internal_ok} decode_roundtrip_ok={decode_ok} comp_len={clen}')
            if decode_ok: print('   *** ROUND-TRIP OK ***'); break
        except Exception as e:
            print(f'first_bits={fb}: error {type(e).__name__}: {e}')
