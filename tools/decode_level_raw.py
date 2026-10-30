#!/usr/bin/env python3
"""LEVEL.RAW decompressor (fcn.8001a1dc) — faithful instruction-level port. G31.

STATUS: BYTE-EXACT (validated chunk0 33548/33548 B; full LEVEL.RAW = 69 chunks -> 1269304 B; seed table found @decomp 0x965d8).  CONFIRMED correct: 9-bit
guard bit-reader (init t2=byte0<<2|2), main loop (literal/match), match length-tree (b1/b2/b3 +
A470 + long-byte), distance (LEN_C/E724/byteswap), LZ copy (incl pre-zeroed history = negative
refs -> 0), and the Nx4 literal-run.  SOLVED: the long-length terminator is NOT byte==0 alone (0x8001a708) — byte==0 -> 0x8001a804 reads one
more bit; bit!=0 continues, ONLY byte==0 AND next-bit==0 terminates.
Oracle: raw_chunk0_{compressed,decompressed}.bin.  Disasm: level_raw_decompressor.asm.
"""

import struct, os
def be32(b,o): return struct.unpack_from('>I',b,o)[0]

def decompress_chunk(comp, out=None, base=None, SRC=None, prov=None):
    word0=be32(comp,0); word1=be32(comp,4)
    v1=[0xe]
    if out is None: out=bytearray()
    base=len(out) if base is None else base
    R={'t2':0,'t7':0,'t0':0,'t1':0}
    def rdreg():                    # byte that refills the bit register
        b=comp[v1[0]]; v1[0]+=1; return b
    def rddata():                   # payload byte (literal / dist-low / long-len / lit-run)
        b=comp[v1[0]]; v1[0]+=1; return b
    if SRC is not None: rdreg, rddata = SRC
    def getref(i):                  # output history; pre-buffer = 0 (zeroed dst)
        return out[i] if i>=0 else 0  # pre-zeroed history
    # --- init (0x8001a2fc) ---
    R['t7']=1
    R['t2']=rdreg()
    R['t2']=R['t2']*2
    R['t2']=R['t2']+R['t7']
    R['t2']=R['t2']*2
    R['t7']=(R['t2']>>8)&1
    label='MAIN'
    # bit read at a decode point: shift, extract, mask; reload if empty
    def dp_bit(reload_to):
        R['t2']=R['t2']*2
        R['t7']=(R['t2']>>8)&1
        R['t2']&=0xff
        if R['t2']==0:
            R['t2']=rdreg(); R['t2']=R['t2']*2+R['t7']; R['t7']=(R['t2']>>8)&1
            return reload_to
        return None
    _steps=[0]
    while True:
        _steps[0]+=1
        if _steps[0]>20000000: raise RuntimeError('decode step guard (no terminator?)')
        if label=='MAIN':                       # 0x8001a658 (flag read, UNMASKED)
            R['t2']=R['t2']*2; R['t7']=(R['t2']>>8)&1
            if R['t7']: label='MATCH'; continue
            _o=v1[0]; out.append(rddata())          # literal 0x8001a66c
            if prov is not None: prov.append(_o)
            R['t2']=R['t2']*2; R['t7']=(R['t2']>>8)&1
            if R['t7']==0:                      # 0x8001a648 loop
                _o=v1[0]; out.append(rddata())
                if prov is not None: prov.append(_o)
                label='MAIN'; continue
            label='MATCH'; continue
        if label=='MATCH':                      # 0x8001a690
            R['t2']&=0xff
            if R['t2']==0:                      # reload (0x8001a628)
                R['t2']=rdreg(); R['t2']=R['t2']*2+R['t7']; R['t7']=(R['t2']>>8)&1
                if R['t7']: label='MATCH_BODY'
                else:
                    _o=v1[0]; out.append(rddata())
                    if prov is not None: prov.append(_o)
                    label='MAIN'
                continue
            label='MATCH_BODY'; continue
        if label=='MATCH_BODY':                 # 0x8001a69c
            R['t0']=2; R['t1']=0
            j=dp_bit('R778')                    # b1
            if j: label=j if j!='R778' else 'A6BC'; 
            label='A6BC' if not j else 'A6BC'
            # b1 path
            if R['t7']==0: label='A470'; continue
            j=dp_bit('R794')                    # b2
            if R['t7']==0: label='DIST'; continue
            R['t0']=R['t0']+1                   # =3
            j=dp_bit('R7B0')                    # b3
            if R['t7']!=0:
                R['t0']=rddata()                # long len 0x8001a708
                if R['t0']==0:                  # 0x8001a714: byte==0 -> 0x8001a804
                    dp_bit('TERM')              # read 1 bit (masked, reload); 
                    if R['t7']!=0:              # 0x8001a834: bit!=0 -> continue (MAIN)
                        label='MAIN'; continue
                    break                       # bit==0 -> TERMINATE (finalize)
                R['t0']=R['t0']+8
            label='LEN_C'; continue
        if label=='A470':                       # 0x8001a470
            dp_bit('a338'); R['t0']=R['t0']*2+R['t7']
            dp_bit('a354')
            if R['t7']==0: label='LEN_C'; continue
            R['t0']=R['t0']-1
            dp_bit('a370'); R['t0']=R['t0']*2+R['t7']
            if R['t0']==9: label='LITRUN'; continue
            label='LEN_C'; continue
        if label=='LEN_C':                      # 0x8001a4e8 distance
            dp_bit('a38c')
            if R['t7']==0: label='DIST'; continue
            dp_bit('a3a8'); R['t1']=R['t1']*2+R['t7']
            dp_bit('a3c4')
            if R['t7']!=0: label='E724'; continue
            if R['t1']!=0: label='SWAP'; continue
            R['t1']=R['t1']+1
            dp_bit('a3e0'); R['t1']=R['t1']*2+R['t7']
            label='SWAP'; continue
        if label=='E724':                       # 0x8001a724
            dp_bit('R7cc'); R['t1']=R['t1']*2+R['t7']; R['t1']=R['t1']|0x4
            dp_bit('R7e8')
            if R['t7']!=0: label='SWAP'; continue
            dp_bit('a3e0b'); R['t1']=R['t1']*2+R['t7']  # ->0x8001a554
            label='SWAP'; continue
        if label=='SWAP':                       # 0x8001a57c byteswap
            t4=(R['t1']<<8)&0xff00; R['t1']=(R['t1']>>8)|t4
            label='DIST'; continue
        if label=='DIST':                       # 0x8001a58c
            s3=R['t1']&0xff00; low=rddata(); R['t1']=low|s3   # dist
            ref=len(out)-R['t1']-1
            for i in range(R['t0']):
                out.append(getref(ref+i))
                if prov is not None: prov.append(None)
            label='MAIN'; continue
        if label=='LITRUN':                     # 0x8001a3fc Nx4 literal run
            R['t0']=3; R['t1']=0
            while True:
                dp_bit('a31c'); R['t1']=R['t1']*2+R['t7']; R['t0']=R['t0']-1
                if R['t0']<0: break
            R['t1']=R['t1']+2
            while R['t1']>=0:
                for _q in range(4):
                    _o=v1[0]; out.append(rddata())
                    if prov is not None: prov.append(_o)
                R['t1']=R['t1']-1
            label='MAIN'; continue
    return out


def decompress_file(data):
    out=bytearray(); off=0; nchunks=0
    while off+8<=len(data):
        word0=be32(data,off); word1=be32(data,off+4)
        if word0==0xffffffff: break
        decompress_chunk(data[off:off+0xe+word1], out)
        off += 0xe + word1; nchunks+=1
    return out, nchunks, off

def validate():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    comp=open('raw_chunk0_compressed.bin','rb').read()
    want=open('raw_chunk0_decompressed.bin','rb').read()
    try: got=decompress_chunk(comp)
    except Exception as e:
        import traceback; traceback.print_exc(); return
    n=min(len(got),len(want)); div=next((i for i in range(n) if got[i]!=want[i]),n)
    ok = (len(got)==len(want) and div>=len(want))
    print(('OK byte-exact!' if ok else 'mismatch')+f'  decoded {len(got)}/{len(want)} B, match {div}'+('' if ok else f' (first div @0x{div:x})'))
    if not ok and div<len(want):
        print('  want',want[max(0,div-3):div+9].hex(),'got',bytes(got[max(0,div-3):div+9]).hex())
if __name__=='__main__': validate()
