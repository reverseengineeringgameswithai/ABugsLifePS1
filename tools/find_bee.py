#!/usr/bin/env python3
"""Crash-robust binary search for the bee enemy's render-position address.
Reuses abl_dbg.D (correct API params). Forces candidate position-triplets
off-screen; the address whose force makes the bee vanish from its screen box
is the bee's render position. Reconnects + reloads on guest crash."""
import sys, struct, os, time
sys.path.insert(0, 'tools'); sys.path.insert(0, os.path.expanduser('~/duckstation/scripts/debugger-client'))
from abl_dbg import D, hexa
from duckstation_debug_client import DebuggerClient
from PIL import Image
from _env import ABL_DIR

SAV = os.path.join(ABL_DIR, 'bee.sav')
BB = (404, 285, 468, 318)            # bee screen bbox
THRESH = 700

class DI(D):
    def __init__(self):
        self.c = DebuggerClient("127.0.0.1", 23460, "ws"); self.c.authenticate("debugger-1000")

d = DI()
def reconnect():
    global d
    for _ in range(10):
        try: d = DI(); return
        except Exception: time.sleep(1)

def reload():
    while True:
        try:
            d.call('emulator.loadState', {'path': SAV}); d.adv(6)
            d.call('emulator.clearControllerState', {'port': 0}); return
        except Exception:
            reconnect()

def hx(v): return struct.pack('<i', v).hex()

reload()
fx, fy, fz = d.rs32(0x800a6500), d.rs32(0x800a6504), d.rs32(0x800a6508)
base = os.path.join(ABL_DIR, 'bb_base.png')
d.call('emulator.captureFrame', {'path': base}); d.adv(2)
B0, L = 0x80090000, 0x30000
raw = d.rmem(B0, L)
cands = []
for o in range(0, L - 12, 4):
    a = B0 + o
    if 0x800a6400 <= a <= 0x800a6600: continue
    x, y, z = struct.unpack_from('<iii', raw, o)
    if abs(x - fx) < 260000 and abs(z - fz) < 260000 and -260000 < y < -10000 and (x - fx) ** 2 + (z - fz) ** 2 > 64:
        cands.append(a)
cands = sorted(set(cands)); kept = []
for a in cands:
    if not kept or a - kept[-1] >= 12: kept.append(a)
print('candidates', len(kept), flush=True)
TGT = (fx + 600000, -380000, fz + 600000)
bpx = Image.open(base).convert('RGB').load()

def beechange(out):
    p = Image.open(out).convert('RGB').load(); ch = 0
    for y in range(BB[1], BB[3]):
        for x in range(BB[0], BB[2]):
            a = bpx[x, y]; b = p[x, y]
            if abs(a[0]-b[0]) + abs(a[1]-b[1]) + abs(a[2]-b[2]) > 70: ch += 1
    return ch

def test(batch):
    try:
        reload()
        w = []
        for a in batch:
            for i, v in enumerate(TGT): w.append({'address': hexa(a + 4*i), 'hex': hx(v)})
        for _ in range(8):
            d.call('debugger.scatterWrite', {'writes': w}); d.adv(1)
        out = os.path.join(ABL_DIR, 'bb_t.png')
        d.call('emulator.captureFrame', {'path': out}); d.adv(1)
        return beechange(out)
    except Exception:
        reconnect(); return None

stack = [kept]; found = []; tests = 0
while stack and tests < 80:
    batch = stack.pop(); tests += 1
    ch = test(batch)
    print('test#%d size=%d -> %s' % (tests, len(batch), 'CRASH' if ch is None else ch), flush=True)
    if ch is None:
        if len(batch) > 1:
            m = len(batch)//2; stack += [batch[:m], batch[m:]]
        continue
    if ch > THRESH:
        if len(batch) == 1:
            found.append((batch[0], ch)); print('  *** BEE %08x change=%d' % (batch[0], ch), flush=True)
        else:
            m = len(batch)//2; stack += [batch[:m], batch[m:]]
print('FOUND:', [(hex(a), ch) for a, ch in found], flush=True)
