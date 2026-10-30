#!/usr/bin/env python3
"""Verify the chaser-move disc edit: load LEVEL01 from ABL_CHASER_MOVE via the
movie, confirm the 3 spawn-area records loaded with the shifted (+2000) waypoints."""
import sys,os,struct,time
sys.path.insert(0,'tools'); sys.path.insert(0,os.path.expanduser('~/duckstation/scripts/debugger-client'))
from abl_dbg import D, hexa
from duckstation_debug_client import DebuggerClient
from _env import ABL_DIR
class DI(D):
    def __init__(self):
        self.c=DebuggerClient("127.0.0.1",23460,"ws"); self.c.authenticate("debugger-1000")
        try: self.c.transport.sock.settimeout(50)
        except: pass
d=DI()
for m in ('movie.stopPlayback','movie.stopRecording','movie.clear'):
    try: d.call(m,{})
    except Exception: pass
print('loadMedia:',d.call('emulator.loadMedia',{'path':os.path.join(ABL_DIR, 'REBUILD/ABL_CHASER_MOVE.cue')}).get('path'),flush=True)
d.call('movie.load',{'path':os.path.join(ABL_DIR, 'flik_to_level01_stall.mv.movie.json')})
d.call('movie.startPlayback',{'load_start_state':True})
recs=[('R1',0x80161144,-5576,-3576),('R2',0x80161208,8564,10564),('R3',0x801612cc,-9416,-7416)]
def check():
    out=[]
    for nm,a,old,new in recs:
        wp1x=d.rs32(a+4)
        out.append((nm,wp1x,new,wp1x==new))
    return out
for batch in range(0,7200,300):
    d.adv(300)
    fl=d.rs32(0x800a6500)
    c=check()
    loaded=all(v==exp for _,v,exp,_ in [(n,v,e,m) for n,v,e,m in c])
    if any(m for _,_,_,m in c) or batch%1200==0:
        print('frame~%d Flik.X=%d  records WP1.X: %s'%(batch+300,fl,['%s=%d(want %d)%s'%(n,v,e,'OK' if m else '') for n,v,e,m in c]),flush=True)
    if all(m for *_,m in c):
        print('=== ALL 3 CHASER RECORDS LOADED WITH NEW WAYPOINTS ===',flush=True)
        # dump first 3 waypoints of R1 to show the whole patrol shifted
        for nm,a,old,new in recs:
            wps=struct.unpack('<9i',d.rmem(a+4,36))
            print('  %s patrol WP1-3 (X,Y,Z): %s'%(nm,[wps[i:i+3] for i in (0,3,6)]),flush=True)
        break
print('DONE',flush=True)
