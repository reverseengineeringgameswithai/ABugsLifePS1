#!/usr/bin/env python3
"""Live-test the DuckStation cd.* overlay API (the "swap disc" alternative).

Instead of booting REBUILD/ABL_STUCK_SEED_TEST.cue, we overlay only the changed
sectors of LEVEL01/LEVEL.RAW onto the *running* base disc, reload a pre-level save,
advance so the game streams LEVEL.RAW off the (now overlaid) CD, and confirm the
stuck seed beside Flik relocated (file X 4837 -> ~1000).

Splits the overlay into small cd.overrideSectors calls (a single ~1MB frame resets
the connection); the edit is a contiguous tail-shift of 220 sectors.
"""
import base64, json, os
from abl_dbg import D
from _env import ABL_SAVESTATES

S = 2048
BASE_LBA = 3069                      # on-disc LBA of LEVEL01/LEVEL.RAW
ORIG = 'REBUILD/files/LEVEL01/LEVEL.RAW'
PATCH = 'tools/LEVEL_stuckseed.RAW'
PRELEVEL = os.path.join(ABL_SAVESTATES, 'SCUS-94288_seed_prelevel.sav')

# seed verifier
TARGET = 0x800a074c
BASE0, STRIDE, N = 0x800a0014, 0x84, 26
CHUNK = 4                            # sectors per override call (server resets >~16KB/msg)

d = D()
orig = open(ORIG, 'rb').read()
patch = open(PATCH, 'rb').read()
span = (max(len(orig), len(patch)) + S - 1) // S
orig = orig.ljust(span * S, b'\0')
patch = patch.ljust(span * S, b'\0')
changed = [i for i in range(span) if orig[i*S:(i+1)*S] != patch[i*S:(i+1)*S]]
lo, hi = changed[0], changed[-1]
print(f'changed sectors {len(changed)} (contiguous {lo}..{hi}); disc LBA {BASE_LBA+lo}..{BASE_LBA+hi}')

print('clear stale overlays', json.dumps(d.call('cd.clearOverlays')))
# install in chunks
sec = lo
while sec <= hi:
    end = min(sec + CHUNK - 1, hi)
    payload = patch[sec*S:(end+1)*S]
    r = d.call('cd.overrideSectors', {'lba': BASE_LBA + sec,
                                      'base64': base64.b64encode(payload).decode()})
    sec = end + 1
print(f'  installed override LBA {BASE_LBA+lo}..{BASE_LBA+hi}')
lst = d.call('cd.listOverlays')
print('installed:', lst['count'], 'overlays,', lst['total_sectors'], 'sectors')

# force a fresh level load so the game re-reads LEVEL.RAW off the overlaid CD
print('loadState prelevel', json.dumps(d.load(PRELEVEL))[:120])
d.adv(600); d.adv(300)

lst = d.call('cd.listOverlays')
served = sum(o['served_count'] for o in lst['overlays'])
print(f'served sectors after load: {served}  (>0 means the game read the overlay)')

# verify seed moved
x = d.rs32(TARGET+4); f40 = d.ru32(TARGET+0x40)
print(f'stuck seed base 0x{TARGET:08x}: file X={x>>5} (expect ~1000, was 4837), +0x40={f40}')
moved = abs((x>>5) - 1000) <= 3
print('\n=== all rooted seeds (+0x40=3) ===')
for i in range(N):
    b = BASE0 + i*STRIDE
    if d.ru32(b+0x40) == 3:
        print(f'  #{i:2d} 0x{b:08x}: file=({d.rs32(b+4)>>5},{d.rs32(b+8)>>5},{d.rs32(b+0xc)>>5})')
print('\nRESULT:', 'PASS — overlay API served the edited LEVEL.RAW; seed relocated without a disc swap'
      if moved and served > 0 and f40 == 3 else
      f'FAIL/INCONCLUSIVE (moved={moved} served={served} f40={f40})')
