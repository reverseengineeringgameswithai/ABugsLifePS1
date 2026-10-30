#!/usr/bin/env python3
"""Build one perm disc per enemy, each relocating only that enemy.
 STATIONARY (worm/pill) -> edit LEVEL.RAW chunk-31 record(s) by type (recompress).
 CHASERS  -> edit LEVEL.DAT 0xc4 patrol record (16 waypoints), direct byte edit.
All moves: +DX in X (record units => <<5 runtime). Each disc: pristine base + 1 enemy edit."""
import sys,os,struct,shutil,subprocess
sys.path.insert(0,'tools')
import decode_level_raw as DEC
from recompress_level_raw import compress_chunk
def be32(b,o): return struct.unpack_from('>I',b,o)[0]

R='REBUILD/files/LEVEL01/'
PRISTINE_RAW=R+'LEVEL.RAW.preenemy'
PRISTINE_DAT=R+'LEVEL.DAT.orig'
STAGED_RAW=R+'LEVEL.RAW'
STAGED_DAT=R+'LEVEL.DAT'
DX=2000  # record units (+64000 runtime)

def edit_raw_type(type_code, dX, out):
    raw=open(PRISTINE_RAW,'rb').read()
    chunks=[]; off=0; dec_off=0
    while off+8<=len(raw):
        w0=be32(raw,off); w1=be32(raw,off+4)
        if w0==0xffffffff: break
        cb=raw[off:off+0xe+w1]
        chunks.append({'comp':cb,'h6':raw[off+8:off+0xe],'dec':bytearray(DEC.decompress_chunk(cb)),'w0':w0})
        dec_off+=w0; off+=0xe+w1
    c=chunks[31]; dec=c['dec']; moved=0
    lo=0x4
    while lo+0x1c<=len(dec):
        t=struct.unpack_from('<H',dec,lo+12)[0]
        if t==type_code:
            x=struct.unpack_from('<i',dec,lo)[0]
            struct.pack_into('<i',dec,lo,x+dX); moved+=1
        lo+=0x1c
    blob=bytearray()
    for i,ch in enumerate(chunks):
        blob += compress_chunk(bytes(ch['dec']),ch['h6']) if i==31 else ch['comp']
    blob+=b'\xff\xff\xff\xff'
    open(out,'wb').write(blob)
    return moved

def edit_dat_record(rec_off, dX, out):
    data=bytearray(open(PRISTINE_DAT,'rb').read())
    for i in range(16):
        wo=rec_off+4+i*12
        x=struct.unpack_from('<i',data,wo)[0]
        struct.pack_into('<i',data,wo,x+dX)
    open(out,'wb').write(data)

def build(name):
    subprocess.run(['mkpsxiso','-y','-o',f'ABL_{name}.bin','-c',f'ABL_{name}.cue','abl_autolayout.xml'],
                   cwd='REBUILD',check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print('  built ABL_%s.cue'%name,flush=True)

# ---- STATIONARY discs (RAW edited, DAT pristine) ----
for name,tc in [('WORM',0x2528),('PILL',0x2427)]:
    shutil.copy(PRISTINE_DAT,STAGED_DAT)
    n=edit_raw_type(tc,DX,STAGED_RAW)
    print('%s: moved %d record(s) of type 0x%04x by +%d X'%(name,n,tc,DX),flush=True)
    build(name)

# ---- CHASER discs (DAT edited, RAW pristine) ----
shutil.copy(PRISTINE_RAW,STAGED_RAW)
for name,off in [('CHASER_0B',0x94c),('CHASER_0C',0xa10),('CHASER_0D',0xad4)]:
    edit_dat_record(off,DX,STAGED_DAT)
    print('%s: moved patrol record @0x%x (16 waypoints) by +%d X'%(name,off,DX),flush=True)
    build(name)

# restore staged files to combined-pristine for safety
shutil.copy(PRISTINE_RAW,STAGED_RAW); shutil.copy(PRISTINE_DAT,STAGED_DAT)
print('DONE — staged files restored to pristine',flush=True)
