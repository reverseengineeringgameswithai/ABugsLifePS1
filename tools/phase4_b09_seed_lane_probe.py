#!/usr/bin/env python3
"""B09: can super jump co-exist with a launch plant? Read the five seed lanes.

THE ROW QUESTION
----------------
B09's last named item is "super-jump's interaction with plants/dandelion/cannon",
recorded in the registry as unstarted and unscoped. This scopes it, and the
scoping decides most of it.

Super jump is BLUE tier 4. The launch plants are all BROWN-lane outputs --
tier 1/2/3/4 = mushroom / propeller / dandelion / cannon. Different lanes, each a
packed byte at 0x800A6598..0x800A659C: high nibble = selected output, low nibble =
highest available (Seed_plant_output_binding). So the interaction is possible only
where BOTH lanes reach the required tier in the same stage.

MEASURED on the operator's B08_SuperJump_EOL movie (the bird level,
LEVEL01/LEVEL1.DAT -- one of only three stage files carrying 4 blue tokens):

    idx 91     brown=1/1  blue=0/0
    idx 1729   brown=1/1  blue=4/4     <- super jump

Brown never leaves 1/1 all level. Tier 1 is MUSHROOM, so dandelion (3) and cannon
(4) are unavailable there. Blue climbing 0->4 with collection confirms the lane
model end to end.

WHAT THIS DOES NOT SHOW
-----------------------
Campaign-wide impossibility. Canon records the token-upgrade write as `n * 17` --
a token SETS the tier rather than incrementing it -- and the bird level has ZERO
orange tokens, which is why brown sits at baseline 1. The other two stages with
blue >= 4 have ONE orange token each and the tier those author is unmeasured.

Usage: python3 tools/phase4_b09_seed_lane_probe.py
"""
import sys, time, subprocess, json
from pathlib import Path
sys.path.insert(0, str(Path.home()/"duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient
ROOT=Path("~/Downloads/ABL")
LANES=[(0x800A6598,"brown"),(0x800A6599,"blue"),(0x800A659A,"green"),
       (0x800A659B,"purple"),(0x800A659C,"yellow")]
subprocess.run([str(ROOT/"tools/launch_repro_playback.sh"),"--config-dir","/tmp/dsrepro_lane",
  "--port","23485","--disc",str(ROOT/"Disney-Pixar A Bug's Life (v1.0).cue"),
  "--execution-mode","Interpreter"],check=True)
c=DebuggerClient("127.0.0.1",23485,"ws"); c.authenticate("debugger-1000"); c.transport.sock.settimeout(900)
c.call("movie.load",{"path":str(ROOT/"movies/Phase4/Interpreter/B08_SuperJump_EOL.movie.json")})
st=c.call("movie.startPlayback",{"load_start_state":True}); fr=st.get("frame_count") or 0
c.call("debugger.resume",{})
seen={}; began=time.time(); last=-1; stalls=0
while time.time()-began < 90+fr/30.0:
    time.sleep(1.5)
    try:
        idx=c.call("movie.status",{}).get("playback_index")
        hx=c.call("debugger.readMemory",{"address":"0x800a6598","length":5})["hex"]
        b=bytes.fromhex(hx)
        key=tuple(b)
        if key not in seen: seen[key]=idx
    except Exception: idx=last
    if idx==last:
        stalls+=1
        if stalls>=8: break
    else: stalls=0
    last=idx
subprocess.run([str(Path.home()/"duckstation/scripts/debugger-client/launch_debugger_instance.sh"),
  "stop","--config-dir","/tmp/dsrepro_lane"],check=False)
print("distinct lane states seen (first playback_index):")
for k,idx in sorted(seen.items(), key=lambda kv: kv[1] or 0):
    print("  idx %-7s  " % idx + "  ".join("%s=%X/%X"%(n,(v>>4)&0xF,v&0xF) for (a,n),v in zip(LANES,k)))
