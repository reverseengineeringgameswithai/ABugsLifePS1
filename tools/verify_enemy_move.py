#!/usr/bin/env python3
"""Verify the enemy-move disc edit: swap to ABL_ENEMY_MOVE, play the from-boot
movie to LEVEL01, and confirm the NEW worm/pill records loaded into RAM."""
import sys,os,struct,time
sys.path.insert(0,'tools'); sys.path.insert(0,os.path.expanduser('~/duckstation/scripts/debugger-client'))
from abl_dbg import D, hexa
from duckstation_debug_client import DebuggerClient
from _env import ABL_DIR
class DI(D):
    def __init__(self):
        self.c=DebuggerClient("127.0.0.1",23460,"ws"); self.c.authenticate("debugger-1000")
        try: self.c.transport.sock.settimeout(40)
        except: pass
d=DI()
NEW_WORM=struct.pack('<iii',-1000,-2556,11536)
NEW_PILL=struct.pack('<iii',1000,-2912,6713)
OLD_WORM=struct.pack('<iii',-3299,-2556,11536)
OLD_PILL=struct.pack('<iii',-911,-2912,6713)
print('media before:',d.call('emulator.getMediaInfo',{}).get('path') if True else '',flush=True)
print('loadMedia:',d.call('emulator.loadMedia',{'path':os.path.join(ABL_DIR, 'REBUILD/ABL_ENEMY_MOVE.cue')}),flush=True)
print('movie.load:',d.call('movie.load',{'path':os.path.join(ABL_DIR, 'flik_to_level01_stall.mv.movie.json')}),flush=True)
print('startPlayback:',d.call('movie.startPlayback',{'load_start_state':True}),flush=True)
def search(pat):
    hits=[]
    for bs in range(0x80080000,0x800c0000,0x20000):
        raw=d.rmem(bs,0x20000); o=-1
        while True:
            o=raw.find(pat,o+1)
            if o<0: break
            hits.append(bs+o)
    return hits
found=False
for batch in range(0,7200,300):
    d.adv(300)
    nw=search(NEW_WORM); npl=search(NEW_PILL)
    ow=search(OLD_WORM); op=search(OLD_PILL)
    fl=(d.rs32(0x800a6500),d.rs32(0x800a6504),d.rs32(0x800a6508))
    print('frame~%d Flik=%s  NEWworm@%s NEWpill@%s  OLDworm@%s OLDpill@%s'%(batch+300,fl,[hex(x) for x in nw],[hex(x) for x in npl],[hex(x) for x in ow],[hex(x) for x in op]),flush=True)
    if nw or npl:
        found=True
        print('=== EDIT CONFIRMED IN RAM ===',flush=True)
        # also read the worm/pill anchors if structs populated
        print('worm anchor 0x800a0c9c:',(d.rs32(0x800a0c9c),d.rs32(0x800a0ca0),d.rs32(0x800a0ca4)),flush=True)
        print('pill anchor 0x800a0144:',(d.rs32(0x800a0144),d.rs32(0x800a0148),d.rs32(0x800a014c)),flush=True)
        break
print('DONE found=%s'%found,flush=True)
