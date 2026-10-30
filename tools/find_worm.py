#!/usr/bin/env python3
"""Hardened force-and-frame-diff search for the worm render-position (stationary enemy).
Adds a socket recv timeout so a guest-crash can't block the search."""
import sys, os, struct, time
sys.path.insert(0,'tools'); sys.path.insert(0,os.path.expanduser('~/duckstation/scripts/debugger-client'))
from abl_dbg import D, hexa
from duckstation_debug_client import DebuggerClient
from PIL import Image
from _env import ABL_DIR

SAV=os.path.join(ABL_DIR, 'worm.sav')
BB=(310,130,540,360); THRESH=2500
class DI(D):
    def __init__(self):
        self.c=DebuggerClient("127.0.0.1",23460,"ws"); self.c.authenticate("debugger-1000")
        try: self.c.transport.sock.settimeout(25)
        except Exception: pass
d=DI()
def reconnect():
    global d
    for _ in range(15):
        try: d=DI(); return
        except Exception: time.sleep(1)
def reload():
    for _ in range(20):
        try:
            d.call('emulator.loadState',{'path':SAV})
            for _ in range(6): d.call('emulator.advanceFrames',{'frames':1})
            d.call('emulator.clearControllerState',{'port':0}); return True
        except Exception: reconnect()
    return False
def hx(v): return struct.pack('<i',v).hex()
reload()
fx,fy,fz=d.rs32(0x800a6500),d.rs32(0x800a6504),d.rs32(0x800a6508)
print('Flik',(fx,fy,fz),flush=True)
B0,L=0x80090000,0x30000; raw=d.rmem(B0,L)
cands=[]
for o in range(0,L-12,4):
    a=B0+o
    if 0x800a6400<=a<=0x800a6600: continue
    x,y,z=struct.unpack_from('<iii',raw,o)
    if abs(x-fx)<300000 and abs(z-fz)<300000 and -300000<y<-2000 and (x-fx)**2+(z-fz)**2>64:
        cands.append(a)
cands=sorted(set(cands)); kept=[]
for a in cands:
    if not kept or a-kept[-1]>=12: kept.append(a)
print('candidates',len(kept),flush=True)
NF=8  # force/advance frames; control uses the SAME count so animation phase matches
# phase-matched CONTROL: reload + NF adv with NO force
reload()
for _ in range(NF): d.adv(1)
ctrl='/tmp/worm_ctrl.png'; d.call('emulator.captureFrame',{'path':ctrl}); d.adv(1)
cpx=Image.open(ctrl).convert('RGB').load()
def bchange(out):
    p=Image.open(out).convert('RGB').load(); ch=0
    for y in range(BB[1],BB[3],1):
        for x in range(BB[0],BB[2],1):
            a=cpx[x,y]; b=p[x,y]
            if abs(a[0]-b[0])+abs(a[1]-b[1])+abs(a[2]-b[2])>70: ch+=1
    return ch
TGT=(fx+700000,-420000,fz+700000)
def test(batch):
    try:
        if not reload(): return None
        w=[{'address':hexa(a+4*i),'hex':hx(v)} for a in batch for i,v in enumerate(TGT)]
        for _ in range(NF): d.call('debugger.scatterWrite',{'writes':w}); d.adv(1)
        out='/tmp/worm_t.png'; d.call('emulator.captureFrame',{'path':out}); d.adv(1)
        return bchange(out)   # diff vs phase-matched control -> only position-force shows
    except Exception:
        reconnect(); return None
stack=[kept]; found=[]; t=0
while stack and t<140:
    b=stack.pop(); t+=1; ch=test(b)
    print('test#%d size=%d -> %s'%(t,len(b),'CRASH' if ch is None else ch),flush=True)
    if ch is None:
        if len(b)>1: m=len(b)//2; stack+=[b[:m],b[m:]]
        continue
    if ch>THRESH:
        if len(b)==1: found.append((b[0],ch)); print('  *** WORM %08x ch=%d'%(b[0],ch),flush=True)
        else: m=len(b)//2; stack+=[b[:m],b[m:]]
print('FOUND:',[(hex(a),c) for a,c in found],flush=True)
