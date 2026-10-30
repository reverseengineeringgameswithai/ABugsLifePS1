#!/usr/bin/env python3
"""Step 1: replay the movie to the LEVEL01 stall on the edited disc, then
calibrate Flik's d-pad -> world movement and measure distance to the moved worm."""
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
def flik(): return (d.rs32(0x800a6500),d.rs32(0x800a6504),d.rs32(0x800a6508))
def hold(btns,n):
    d.call('emulator.setControllerState',{'port':0,'buttons':btns})
    for _ in range(n): d.call('emulator.advanceFrames',{'frames':1})
    d.call('emulator.clearControllerState',{'port':0})
for m in ('movie.stopPlayback','movie.stopRecording','movie.clear'):
    try: d.call(m,{})
    except Exception: pass
print('loadMedia:',d.call('emulator.loadMedia',{'path':os.path.join(ABL_DIR, 'REBUILD/ABL_ENEMY_MOVE.cue')}).get('path'),flush=True)
d.call('movie.load',{'path':os.path.join(ABL_DIR, 'flik_to_level01_stall.mv.movie.json')})
d.call('movie.startPlayback',{'load_start_state':True})
# play through the 6470-frame movie
for _ in range(22): d.adv(300)
print('after playback Flik=',flik(),flush=True)
# exit the stall with CROSS
hold({'cross':True},6); d.call('emulator.clearControllerState',{'port':0})
for _ in range(4): d.adv(10)
sp=flik(); print('post-stall Flik=',sp,flush=True)
WORM=(-32000,-81792,369152)
import math
print('WORM target=',WORM,' distXZ=%.0f'%math.hypot(WORM[0]-sp[0],WORM[2]-sp[2]),flush=True)
# calibrate d-pad -> world
for b in ['up','down','left','right']:
    p0=flik(); hold({b:True},12); p1=flik()
    print('hold %-5s: dX=%+d dZ=%+d'%(b,p1[0]-p0[0],p1[2]-p0[2]),flush=True)
d.call('emulator.captureFrame',{'path':os.path.join(ABL_DIR, 'nav_poststall.png')}); d.adv(2)
print('DONE',flush=True)
