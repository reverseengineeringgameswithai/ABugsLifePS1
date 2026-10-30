#!/usr/bin/env python3
"""Trace mosquito + spider spawn/position: find the position writer, dump the
struct, and test whether any field is a STATIC home (survives a Flik teleport)
vs Flik-relative chase. Determines if they have an editable home record."""
import sys,os,struct,time
sys.path.insert(0,'tools'); sys.path.insert(0,os.path.expanduser('~/duckstation/scripts/debugger-client'))
from abl_dbg import D, hexa
from duckstation_debug_client import DebuggerClient
from collections import Counter
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
ENEMY=0x80095358
for nm in ['mosquito','spider_walking']:
    print('\n========== %s =========='%nm,flush=True)
    gl(os.path.join(ABL_DIR, '%s.sav' % nm))
    fx,fy,fz=d.rs32(0x800a6500),d.rs32(0x800a6504),d.rs32(0x800a6508)
    # dump struct BEFORE teleport
    pre=struct.unpack('<32i',d.rmem(ENEMY-0x10,0x80))
    # write-watch the enemy position
    d.call('accessLog.addWatch',{'address':hexa(ENEMY),'length':12,'type':'write'})
    d.adv(25)
    ev=d.call('accessLog.get',{'limit':256}).get('events',[])
    d.call('accessLog.removeAllWatches',{}) if False else None
    writers=dict(Counter(e.get('pc') for e in ev))
    print('Flik=(%d,%d,%d) enemy@%08x pos=%s'%(fx,fy,fz,ENEMY,(d.rs32(ENEMY),d.rs32(ENEMY+4),d.rs32(ENEMY+8))),flush=True)
    print('POSITION WRITERS:',writers,flush=True)
    # teleport Flik far, dump struct AFTER, find which fields tracked vs stayed
    gl(os.path.join(ABL_DIR, '%s.sav' % nm))
    w=[{'address':hexa(0x800a6500),'hex':hx(fx+700000)},{'address':hexa(0x800a6504),'hex':hx(fy)},{'address':hexa(0x800a6508),'hex':hx(fz)}]
    for _ in range(20): d.call('debugger.scatterWrite',{'writes':w}); d.adv(1)
    post=struct.unpack('<32i',d.rmem(ENEMY-0x10,0x80))
    print('struct fields (off from %08x): pre -> post  [/32 = record-scaled]'%(ENEMY-0x10),flush=True)
    for i in range(32):
        a=ENEMY-0x10+i*4
        pv,qv=pre[i],post[i]
        if abs(pv)<3000000 and (pv!=0 or qv!=0):
            tag=''
            if pv==qv: tag='STATIC'
            elif abs(qv-pv)>50000: tag='TRACKS-FLIK'
            sc=' /32' if pv%32==0 and abs(pv)>1000 else ''
            if tag: print('  +%02x (%08x): %11d -> %11d  %s%s'%(i*4,a,pv,qv,tag,sc),flush=True)
print('\nDONE',flush=True)
