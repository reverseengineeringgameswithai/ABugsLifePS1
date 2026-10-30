#!/usr/bin/env python3
"""Decompress the entire LEVEL01/LEVEL.RAW to disk + a chunk index, for direct inspection."""
import struct, json, decode_level_raw as D
RAW='../REBUILD/files/LEVEL01/LEVEL.RAW'
OUTDIR='LEVEL_RAW_decompressed'
import os; os.makedirs(OUTDIR, exist_ok=True)
data=open(RAW,'rb').read()
def be32(o): return struct.unpack_from('>I',data,o)[0]
def a4(x): return (x+3)&~3
co=0; do=0; idx=[]; full=bytearray()
i=0
while co+8<=len(data):
    w0=be32(co)
    if w0==0xffffffff: break
    w1=be32(co+4)
    dd=bytearray(); D.decompress_chunk(data[co:co+0xe+w1], dd)
    assert len(dd)==w0, (i,len(dd),w0)
    full+=dd; full+=b'\x00'*(a4(w0)-w0)   # match runtime a4 stride
    idx.append({'chunk':i,'comp_off':co,'decomp_off':do,'word0':w0,'word1':w1})
    co+=0xe+w1; do+=a4(w0); i+=1
open(f'{OUTDIR}/LEVEL.RAW.decompressed','wb').write(full)
json.dump(idx, open(f'{OUTDIR}/chunk_index.json','w'), indent=1)
print(f'decompressed {i} chunks -> {len(full)} bytes; index has {len(idx)} chunks')
