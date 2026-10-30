#!/usr/bin/env python3
"""dump_pass1_palette.py -- build the pass-1 PROP PALETTE (payload -> thumbnail).

Uses the live-proven payload-swap lever: park on a save with a pass-1 record in
front of the camera (acorn.sav / record #214), then for every DISTINCT payload
pointer in the pass-1 table, point record #214's payload at it, advance a few
frames, and captureFrame. Output: one thumbnail per payload + palette.json
mapping payload FILE offsets -> {runtime ptr, example record indices, thumb}.

The palette is what the Blender export UI uses to pick prop models
(see ObsidianVault/Systems/'Tier 3 - Blender Pipeline Plan').

Usage (isolated DuckStation running, LEVEL01 disc):
    python3 tools/dump_pass1_palette.py --save acorn.sav --out build/pass1_palette
"""
import sys, os, struct, math, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser(os.path.join(os.environ.get('DUCKSTATION_DIR','~/duckstation'),'scripts','debugger-client')))
from duckstation_debug_client import DebuggerClient  # noqa

PASS1_BASE = 0x1504
VIEW_REC   = 214          # the record in front of the camera in acorn.sav
STRIDE     = 0x14

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', default='acorn.sav')
    ap.add_argument('--out', default='build/pass1_palette')
    ap.add_argument('--port', type=int, default=23460)
    ap.add_argument('--token', default='debugger-1000')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    class _D:
        def __init__(self):
            self.c = DebuggerClient('127.0.0.1', a.port, 'ws')
            self.c.authenticate(a.token)
            self.c.transport.sock.settimeout(30)
        def call(self, m, p=None): return self.c.call(m, p or {})
        def rmem(self, ad, n): return bytes.fromhex(self.call('debugger.readMemory', {'address': '0x%08x' % ad, 'length': n})['hex'])
        def ru32(self, ad): return struct.unpack('<I', self.rmem(ad, 4))[0]
        def wu32(self, ad, v): return self.call('debugger.writeMemory', {'address': '0x%08x' % ad, 'hex': struct.pack('<I', v & 0xffffffff).hex()})
        def load(self, p):
            if not os.path.isabs(p): p = os.path.abspath(p)
            return self.call('emulator.loadState', {'path': p, 'pause_after_load': True})
    d = _D()
    d.load(a.save); d.call('emulator.advanceFrames', {'frames': 3})
    datbase = d.ru32(0x80082498)
    tab = d.rmem(datbase + PASS1_BASE, STRIDE * 700)
    payloads = {}
    for i in range(700):
        x, = struct.unpack_from('<i', tab, i * STRIDE)
        if abs(x) > 0x40000: break
        ptr, = struct.unpack_from('<I', tab, i * STRIDE + 0x10)
        payloads.setdefault(ptr, []).append(i)
    view_off = datbase + PASS1_BASE + VIEW_REC * STRIDE + 0x10
    orig = d.ru32(view_off)
    print('records scanned: %d, distinct payloads: %d' % (i, len(payloads)))
    meta = {}
    for n, (ptr, recs) in enumerate(sorted(payloads.items())):
        d.wu32(view_off, ptr)
        d.call('emulator.advanceFrames', {'frames': 4})
        fname = 'payload_%06x.png' % (ptr - datbase)
        d.call('emulator.captureFrame', {'path': os.path.abspath(os.path.join(a.out, fname))})
        meta['0x%x' % (ptr - datbase)] = {'runtime_ptr': '0x%08x' % ptr,
                                          'records': recs[:12], 'count': len(recs),
                                          'thumb': fname}
        if n % 10 == 0: print('  %d/%d' % (n, len(payloads)))
    d.wu32(view_off, orig)
    json.dump(meta, open(os.path.join(a.out, 'palette.json'), 'w'), indent=1)
    print('palette written to', a.out)

if __name__ == '__main__':
    main()
