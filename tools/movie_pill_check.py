#!/usr/bin/env python3
"""Fresh boot of the edited disc -> movie to LEVEL01 -> teleport Flik to the
pill beetle's NEW spot -> confirm live anchor 0x800a0144 == (32000,-93184,214816)."""
import sys,os,struct,time
sys.path.insert(0,'tools'); sys.path.insert(0,os.path.expanduser('~/duckstation/scripts/debugger-client'))
from abl_dbg import D, hexa
from duckstation_debug_client import DebuggerClient
from _env import ABL_DIR
def conn():
    for _ in range(30):
        try:
            c=DebuggerClient("127.0.0.1",23460,"ws"); c.authenticate("debugger-1000")
            c.transport.sock.settimeout(60); return c
        except Exception: time.sleep(1)
    raise RuntimeError('no connect')
class DI(D):
    def __init__(self): self.c=conn()
d=DI()
def hx(v): return struct.pack('<i',v).hex()
def flik(): return (d.rs32(0x800a6500),d.rs32(0x800a6504),d.rs32(0x800a6508))
def search3(x,y,z):
    pat=struct.pack('<iii',x,y,z); hits=[]
    for bs in range(0x80094000,0x800b0000,0x8000):
        raw=d.rmem(bs,0x8000); o=-1
        while True:
            o=raw.find(pat,o+1)
            if o<0: break
            hits.append(bs+o)
    return hits
for m in ('movie.stopPlayback','movie.stopRecording','movie.clear'):
    try: d.call(m,{})
    except Exception: pass
print('movie.load:',d.call('movie.load',{'path':os.path.join(ABL_DIR, 'flik_to_level01_stall.mv.movie.json')}).get('has_movie'),flush=True)
d.call('movie.startPlayback',{'load_start_state':True})
for _ in range(22): d.adv(300)
print('after playback Flik=',flik(),flush=True)
d.call('emulator.setControllerState',{'port':0,'buttons':{'cross':True}})
for _ in range(6): d.adv(1)
d.call('emulator.clearControllerState',{'port':0})
for _ in range(20): d.adv(1)
print('post-stall Flik=',flik(),flush=True)
# gentle teleport to NEAR the pill (exact anchor Y, slight X offset so Flik isn't inside it)
PILL=(32000,-93184,214816)
spot=(PILL[0]-12000,PILL[1],PILL[2])
w=[{'address':hexa(0x800a6500),'hex':hx(spot[0])},{'address':hexa(0x800a6504),'hex':hx(spot[1])},{'address':hexa(0x800a6508),'hex':hx(spot[2])}]
ok=True
for i in range(45):
    try: d.call('debugger.scatterWrite',{'writes':w}); d.adv(1)
    except Exception as e:
        print('crash at frame',i,e,flush=True); ok=False; break
if ok:
    d.call('emulator.clearControllerState',{'port':0})
    for _ in range(15): d.adv(1)
    anc=(d.rs32(0x800a0144),d.rs32(0x800a0148),d.rs32(0x800a014c))
    cur=(d.rs32(0x800a0120),d.rs32(0x800a0124),d.rs32(0x800a0128))
    d.call('emulator.captureFrame',{'path':os.path.join(ABL_DIR, 'pill_NEWSPOT.png')}); d.adv(2)
    print('PILL anchor(0x800a0144)=%s  cur(0x800a0120)=%s  Flik=%s'%(anc,cur,flik()),flush=True)
    print('search NEW pill anchor (32000,-93184,214816):',[hex(x) for x in search3(32000,-93184,214816)],flush=True)
    print('search OLD pill anchor (-29152,-93184,214816):',[hex(x) for x in search3(-29152,-93184,214816)],flush=True)
print('DONE',flush=True)
