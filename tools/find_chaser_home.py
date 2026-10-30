#!/usr/bin/env python3
"""Test whether a 'chaser' actually leashes to a HOME/patrol center: hold Flik
far away for a long time and watch if the enemy stops following and returns to
a fixed center. Dump struct+globals to find a static (record-backed) home."""
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
def hx(v): return struct.pack('<i',v).hex()
def gl(save):
    d.call('emulator.loadState',{'path':save})
    for _ in range(6): d.call('emulator.advanceFrames',{'frames':1})
    d.call('emulator.clearControllerState',{'port':0})
E=0x80095358
def epos(): return (d.rs32(E),d.rs32(E+4),d.rs32(E+8))
for nm in ['mosquito','spider_walking']:
    print('\n========== %s =========='%nm,flush=True)
    gl(os.path.join(ABL_DIR, '%s.sav' % nm))
    fx,fy,fz=d.rs32(0x800a6500),d.rs32(0x800a6504),d.rs32(0x800a6508)
    print('Flik=(%d,%d,%d) enemy start=%s'%(fx,fy,fz,epos()),flush=True)
    # hold Flik very far for a long time
    far=(fx+1500000,fy,fz)
    w=[{'address':hexa(0x800a6500),'hex':hx(far[0])},{'address':hexa(0x800a6504),'hex':hx(far[1])},{'address':hexa(0x800a6508),'hex':hx(far[2])}]
    traj=[]
    for step in range(12):
        for _ in range(20): d.call('debugger.scatterWrite',{'writes':w}); d.adv(1)
        traj.append(epos())
    print('enemy trajectory (Flik held far, every 20f):',flush=True)
    for i,p in enumerate(traj): print('   t%02d %s'%((i+1)*20,p),flush=True)
    # after de-aggro, sample patrol center: collect 40 frames of positions
    pts=[]
    for _ in range(40):
        for _ in range(3): d.call('debugger.scatterWrite',{'writes':w}); d.adv(1)
        pts.append(epos())
    cx=sum(p[0] for p in pts)//len(pts); cy=sum(p[1] for p in pts)//len(pts); cz=sum(p[2] for p in pts)//len(pts)
    print('patrol-center estimate (centroid)=(%d,%d,%d)  /32=(%s,%s,%s)'%(cx,cy,cz,cx%32==0,cy%32==0,cz%32==0),flush=True)
    # dump struct + globals for static /32 coords near the center
    raw=d.rmem(0x80090b00,0x120);
    print('candidate static globals near center in 0x80090b00..0x80090c20:',flush=True)
    for o in range(0,0x120-12,4):
        x,y,z=struct.unpack_from('<iii',raw,o)
        if abs(x-cx)<60000 and abs(z-cz)<60000 and -300000<y<-1000:
            print('   @%08x XYZ=(%d,%d,%d)'%(0x80090b00+o,x,y,z),flush=True)
print('\nDONE',flush=True)
