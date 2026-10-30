#!/usr/bin/env python3
"""Confirm the pill beetle moved: teleport Flik to its NEW spot, let it spawn,
read live anchor 0x800a0144 (expect (32000,-93184,214816) = edited record<<5)."""
import sys,os,struct
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
def search3(x,y,z):
    pat=struct.pack('<iii',x,y,z); hits=[]
    for bs in range(0x80094000,0x800b0000,0x8000):
        raw=d.rmem(bs,0x8000); o=-1
        while True:
            o=raw.find(pat,o+1)
            if o<0: break
            hits.append(bs+o)
    return hits
print('current Flik (LEVEL01):',flik(),flush=True)
def tele(spot,tag):
    fx,fy,fz=spot
    w=[{'address':hexa(0x800a6500),'hex':hx(fx)},{'address':hexa(0x800a6504),'hex':hx(fy)},{'address':hexa(0x800a6508),'hex':hx(fz)}]
    for _ in range(50): d.call('debugger.scatterWrite',{'writes':w}); d.adv(1)
    d.call('emulator.clearControllerState',{'port':0})
    for _ in range(20): d.adv(1)
    anc=(d.rs32(0x800a0144),d.rs32(0x800a0148),d.rs32(0x800a014c))
    cur=(d.rs32(0x800a0120),d.rs32(0x800a0124),d.rs32(0x800a0128))
    d.call('emulator.captureFrame',{'path':os.path.join(ABL_DIR, '%s.png' % tag)}); d.adv(2)
    print('%s: Flik=%s  pill_anchor(0x800a0144)=%s  pill_cur(0x800a0120)=%s'%(tag,flik(),anc,cur),flush=True)
print('--- NEW pill spot (32000,-94000,214816) ---',flush=True)
tele((32000,-94000,214816),'pill_NEWSPOT')
print('search NEW pill anchor (32000,-93184,214816):',[hex(x) for x in search3(32000,-93184,214816)],flush=True)
print('search OLD pill anchor (-29152,-93184,214816):',[hex(x) for x in search3(-29152,-93184,214816)],flush=True)
print('--- OLD pill spot (-29152,-94000,214816) ---',flush=True)
tele((-29152,-94000,214816),'pill_OLDSPOT')
print('DONE',flush=True)
