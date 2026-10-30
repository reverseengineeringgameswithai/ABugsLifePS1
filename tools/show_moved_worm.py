#!/usr/bin/env python3
"""Option 1: with LEVEL01 loaded from the edited disc (via the movie), teleport
Flik to the worm's NEW spot so it spawns there, capture it + read the live anchor;
then check the OLD spot is empty. Proves the perm disc edit moved the worm in-game."""
import sys,os,struct,time
sys.path.insert(0,'tools'); sys.path.insert(0,os.path.expanduser('~/duckstation/scripts/debugger-client'))
from abl_dbg import D, hexa
from duckstation_debug_client import DebuggerClient
from _env import ABL_DIR
class DI(D):
    def __init__(self):
        self.c=DebuggerClient("127.0.0.1",23460,"ws"); self.c.authenticate("debugger-1000")
        try: self.c.transport.sock.settimeout(60)
        except: pass
d=DI()
def hx(v): return struct.pack('<i',v).hex()
def flik(): return (d.rs32(0x800a6500),d.rs32(0x800a6504),d.rs32(0x800a6508))
def search_anchor(val):
    pat=struct.pack('<i',val); hits=[]
    for bs in range(0x80094000,0x800b0000,0x8000):
        raw=d.rmem(bs,0x8000); o=-1
        while True:
            o=raw.find(pat,o+1)
            if o<0: break
            hits.append(bs+o)
    return hits
print('current Flik (should be LEVEL01):',flik(),flush=True)
def teleport_and_cap(spot,tag,Ywalk=None):
    fx,fy,fz=spot
    w=[{'address':hexa(0x800a6500),'hex':hx(fx)},{'address':hexa(0x800a6504),'hex':hx(fy)},{'address':hexa(0x800a6508),'hex':hx(fz)}]
    # hold Flik at the spot for a while so streaming/spawn triggers fire
    for _ in range(50):
        d.call('debugger.scatterWrite',{'writes':w}); d.adv(1)
    # release and let it settle
    d.call('emulator.clearControllerState',{'port':0})
    for _ in range(20): d.adv(1)
    anc=(d.rs32(0x800a0c9c),d.rs32(0x800a0ca0),d.rs32(0x800a0ca4))
    cur=(d.rs32(0x800a0c78),d.rs32(0x800a0c7c),d.rs32(0x800a0c80))
    d.call('emulator.captureFrame',{'path':os.path.join(ABL_DIR, '%s.png' % tag)}); d.adv(2)
    print('%s: Flik=%s worm_anchor(0x800a0c9c)=%s worm_cur(0x800a0c78)=%s'%(tag,flik(),anc,cur),flush=True)
    return anc
# NEW spot (worm record edited to X=-1000 -> anchor -32000)
print('--- teleport to NEW worm spot (-32000,-82449,369152) ---',flush=True)
teleport_and_cap((-32000,-82449,369152),'worm_NEWSPOT')
print('search RAM for anchor X=-32000:',[hex(x) for x in search_anchor(-32000)],flush=True)
print('search RAM for old anchor X=-105568:',[hex(x) for x in search_anchor(-105568)],flush=True)
# OLD spot (where the worm used to be on pristine)
print('--- teleport to OLD worm spot (-105568,-82449,369152) ---',flush=True)
teleport_and_cap((-105568,-82449,369152),'worm_OLDSPOT')
print('DONE',flush=True)
