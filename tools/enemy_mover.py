#!/usr/bin/env python3
"""Reusable method to figure out HOW to move a given ABL enemy.

Pipeline (proven on the bee, bee.sav -> 0x80095358):
  1. IDENTIFY  the enemy's runtime render-position address, via a crash-robust
     force-and-frame-diff BINARY SEARCH: force candidate world-position triplets
     off-screen; the address whose force makes the enemy vanish from its screen
     bbox is the render position. (Copies/AI buffers don't move the render -> excluded.)
  2. CLASSIFY  the enemy: teleport Flik far; if the render-pos tracks Flik it is a
     CHASER (player-relative, NO editable location); else it is STATIONARY/PATROL
     (relocatable by editing its position/path record on disc).
  3. TRACE     who writes the render-pos (accessLog) -> the position writer PC, the
     handle to follow to a data record (editable) vs Flik-relative vs procedural.

Usage:
  python3 enemy_mover.py <save.sav> <bx0> <by0> <bx1> <by1>
      <save>        path to a save state with the enemy clearly on screen
      <bx0..by1>    the enemy's screen bounding box (800x610 capture space)

Connects to the isolated DuckStation debugger on port 23460 (token debugger-1000).
IMPORTANT: advanceFrames param is 'frames'; abl_dbg.D handles this. reload recovers
guest crashes (loadState works post-crash). The force target is off-screen so a
false-positive (random memory) just doesn't change the bbox -> it is filtered out.
"""
import sys, os, struct, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/duckstation/scripts/debugger-client'))
from abl_dbg import D, hexa
from duckstation_debug_client import DebuggerClient
from PIL import Image

PORT, TOKEN = 23460, "debugger-1000"
REGION = (0x80090000, 0x30000)
FLIK = (0x800a6500, 0x800a6504, 0x800a6508)

class DI(D):
    def __init__(self):
        self.c = DebuggerClient("127.0.0.1", PORT, "ws"); self.c.authenticate(TOKEN)

def hx(v): return struct.pack('<i', v).hex()

class EnemyMover:
    def __init__(self, save):
        self.save = save; self.d = DI()
    def reconnect(self):
        for _ in range(10):
            try: self.d = DI(); return
            except Exception: time.sleep(1)
    def reload(self):
        while True:
            try:
                self.d.call('emulator.loadState', {'path': self.save}); self.d.adv(6)
                self.d.call('emulator.clearControllerState', {'port': 0}); return
            except Exception: self.reconnect()
    def flik(self):
        return tuple(self.d.rs32(a) for a in FLIK)
    def candidates(self):
        self.reload(); fx, fy, fz = self.flik()
        B0, L = REGION; raw = self.d.rmem(B0, L); out = []
        for o in range(0, L - 12, 4):
            a = B0 + o
            if 0x800a6400 <= a <= 0x800a6600: continue
            x, y, z = struct.unpack_from('<iii', raw, o)
            if abs(x-fx) < 260000 and abs(z-fz) < 260000 and -260000 < y < -2000 and (x-fx)**2+(z-fz)**2 > 64:
                out.append(a)
        out = sorted(set(out)); kept = []
        for a in out:
            if not kept or a - kept[-1] >= 12: kept.append(a)
        return kept, (fx, fy, fz)
    def _bbox_change(self, base_px, out, bb):
        p = Image.open(out).convert('RGB').load(); ch = 0
        for y in range(bb[1], bb[3]):
            for x in range(bb[0], bb[2]):
                a = base_px[x, y]; b = p[x, y]
                if abs(a[0]-b[0])+abs(a[1]-b[1])+abs(a[2]-b[2]) > 70: ch += 1
        return ch
    def identify(self, bb, thresh=700):
        cands, (fx, fy, fz) = self.candidates()
        base = '/tmp/em_base.png'; self.d.call('emulator.captureFrame', {'path': base}); self.d.adv(2)
        base_px = Image.open(base).convert('RGB').load()
        tgt = (fx + 600000, -380000, fz + 600000)
        def test(batch):
            try:
                self.reload()
                w = [{'address': hexa(a + 4*i), 'hex': hx(v)} for a in batch for i, v in enumerate(tgt)]
                for _ in range(8): self.d.call('debugger.scatterWrite', {'writes': w}); self.d.adv(1)
                out = '/tmp/em_t.png'; self.d.call('emulator.captureFrame', {'path': out}); self.d.adv(1)
                return self._bbox_change(base_px, out, bb)
            except Exception:
                self.reconnect(); return None
        stack = [cands]; found = []; tests = 0
        while stack and tests < 120:
            batch = stack.pop(); tests += 1; ch = test(batch)
            if ch is None:
                if len(batch) > 1: m = len(batch)//2; stack += [batch[:m], batch[m:]]
                continue
            if ch > thresh:
                if len(batch) == 1: found.append((batch[0], ch))
                else: m = len(batch)//2; stack += [batch[:m], batch[m:]]
        return found
    def classify(self, addr):
        self.reload(); fx, fy, fz = self.flik(); p0 = self.d.rs32(addr)
        w = [{'address': hexa(FLIK[i] + 0), 'hex': hx(v)} for i, v in
             [(0, fx+700000), (1, fy), (2, fz)]]
        w = [{'address': hexa(FLIK[0]), 'hex': hx(fx+700000)},
             {'address': hexa(FLIK[1]), 'hex': hx(fy)},
             {'address': hexa(FLIK[2]), 'hex': hx(fz)}]
        for _ in range(20): self.d.call('debugger.scatterWrite', {'writes': w}); self.d.adv(1)
        return ('CHASER' if self.d.rs32(addr) - p0 > 60000 else 'STATIONARY/PATROL'), p0, self.d.rs32(addr)
    def trace(self, addr):
        self.reload()
        self.d.call('accessLog.addWatch', {'address': hexa(addr), 'length': 12, 'type': 'write'})
        self.d.adv(30)
        ev = self.d.call('accessLog.get', {'limit': 256}).get('events', [])
        from collections import Counter
        return dict(Counter(e.get('pc') for e in ev))

if __name__ == '__main__':
    save = sys.argv[1]; bb = tuple(int(x) for x in sys.argv[2:6])
    em = EnemyMover(save)
    print('IDENTIFY...'); found = em.identify(bb)
    print('  render-position address(es):', [(hex(a), c) for a, c in found])
    for a, _ in found[:1]:
        kind, p0, p1 = em.classify(a)
        print('CLASSIFY %s: %s (pos %d -> %d after Flik teleport)' % (hex(a), kind, p0, p1))
        print('TRACE writers of %s:' % hex(a), em.trace(a))
