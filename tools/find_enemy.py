#!/usr/bin/env python3
"""Reusable: identify + classify + trace an ABL enemy's position. Hardened.
  python3 find_enemy.py <save.sav> <bx0> <by0> <bx1> <by1> [thresh]
Fixes vs enemy_mover.py: socket recv timeout (no hang on guest-crash),
phase-matched no-force control (animated enemies don't false-flag)."""
import sys, os, struct, time
sys.path.insert(0,'tools'); sys.path.insert(0,os.path.expanduser('~/duckstation/scripts/debugger-client'))
from abl_dbg import D, hexa
from duckstation_debug_client import DebuggerClient
from PIL import Image
from collections import Counter

SAV=sys.argv[1]; BB=tuple(int(x) for x in sys.argv[2:6])
THRESH=int(sys.argv[6]) if len(sys.argv)>6 else 2500
NF=8
class DI(D):
    def __init__(self):
        self.c=DebuggerClient("127.0.0.1",23460,"ws"); self.c.authenticate("debugger-1000")
        try: self.c.transport.sock.settimeout(25)
        except: pass
d=DI()
def hx(v): return struct.pack('<i',v).hex()
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
reload()
fx,fy,fz=d.rs32(0x800a6500),d.rs32(0x800a6504),d.rs32(0x800a6508)
print('Flik',(fx,fy,fz),flush=True)
B0,L=0x80090000,0x30000; raw=d.rmem(B0,L); cands=[]
for o in range(0,L-12,4):
    a=B0+o
    if 0x800a6400<=a<=0x800a6600: continue
    x,y,z=struct.unpack_from('<iii',raw,o)
    if abs(x-fx)<320000 and abs(z-fz)<320000 and -320000<y<-2000 and (x-fx)**2+(z-fz)**2>64:
        cands.append(a)
cands=sorted(set(cands)); kept=[]
for a in cands:
    if not kept or a-kept[-1]>=12: kept.append(a)
print('candidates',len(kept),flush=True)
reload()
for _ in range(NF): d.adv(1)
ctrl='/tmp/fe_ctrl.png'; d.call('emulator.captureFrame',{'path':ctrl}); d.adv(1)
cpx=Image.open(ctrl).convert('RGB').load()
def bchange(out):
    p=Image.open(out).convert('RGB').load(); ch=0
    for y in range(BB[1],BB[3]):
        for x in range(BB[0],BB[2]):
            a=cpx[x,y]; b=p[x,y]
            if abs(a[0]-b[0])+abs(a[1]-b[1])+abs(a[2]-b[2])>70: ch+=1
    return ch
TGT=(fx+700000,-420000,fz+700000)
def test(batch):
    try:
        if not reload(): return None
        w=[{'address':hexa(a+4*i),'hex':hx(v)} for a in batch for i,v in enumerate(TGT)]
        for _ in range(NF): d.call('debugger.scatterWrite',{'writes':w}); d.adv(1)
        out='/tmp/fe_t.png'; d.call('emulator.captureFrame',{'path':out}); d.adv(1)
        return bchange(out)
    except Exception:
        reconnect(); return None
stack=[kept]; found=[]; t=0
while stack and t<150:
    b=stack.pop(); t+=1; ch=test(b)
    if ch is None:
        if len(b)>1: m=len(b)//2; stack+=[b[:m],b[m:]]
        continue
    if ch>THRESH:
        if len(b)==1: found.append((b[0],ch)); print('  render-pos %08x ch=%d'%(b[0],ch),flush=True)
        else: m=len(b)//2; stack+=[b[:m],b[m:]]
# classify + trace each found
print('=== CLASSIFY + TRACE ===',flush=True)
for a,_ in found:
    reload(); p0=d.rs32(a)
    w=[{'address':hexa(0x800a6500),'hex':hx(fx+800000)},{'address':hexa(0x800a6504),'hex':hx(fy)},{'address':hexa(0x800a6508),'hex':hx(fz)}]
    for _ in range(20): d.call('debugger.scatterWrite',{'writes':w}); d.adv(1)
    dx=d.rs32(a)-p0; kind='CHASER' if abs(dx)>40000 else 'STATIONARY/PATROL'
    reload(); d.call('accessLog.addWatch',{'address':hexa(a),'length':12,'type':'write'}); d.adv(30)
    ev=d.call('accessLog.get',{'limit':200}).get('events',[])
    p=d.rs32(a); scaled = 'YES (record=%s)'%str((p>>5 if p%32==0 else None,)) if p%32==0 else 'no'
    print('  %08x: %s dX=%d  pos=%d  /32even=%s  writers=%s'%(a,kind,dx,p, p%32==0, dict(Counter(e.get('pc') for e in ev))),flush=True)
print('DONE',flush=True)
