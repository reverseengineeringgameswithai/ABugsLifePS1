#!/usr/bin/env python3
"""F10: watch the Clover Forest objective mask across the operator's Any% run.

Static (tools/phase4_f10_clover_objective.c, 29 pins) says the stage's objective is a
FIVE-BIT MASK at 0x800B5774, completing at 0x1F, with a parallel countdown at
0x800B577C and a resident scene-7-gated HUD reading the mask once per bit.

A mask predicts something a counter does not: the five writes must set five DISTINCT
bits, and re-touching a collected piece must be a no-op. That is what this checks.

RESULT (operator's Any% run, movie-relative frames): init at 770 sets mask 0 and the
parallel word to 5; five collections at 4031/5064/7480/8333/10461 set bits
0x10, 0x04, 0x08, 0x02, 0x01 -- OUT OF ORDER, which is the point. A counter would
have been indistinguishable from a mask in a linear run; the out-of-order sequence
shows the pieces are individually identified and order-independent. The parallel word
runs 5->4->3->2->1->0 in lockstep, so it is the "remaining" readout and there are
exactly five pieces. On the fifth the latch is set at 0x800B44B0, the pinned PC.
"""
import json, subprocess, sys, time
from pathlib import Path
ROOT = Path("~/Downloads/ABL")
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient

MASK, COUNT, LATCH, FADE, SCENE = 0x800B5774, 0x800B577C, 0x800823A0, 0x80082470, 0x80082504
MOVIE = ROOT / "movies/Phase4/Interpreter/Any% Runs/LEVEL10_cloverforest.movie.json"
PORT = 23901
cfg = Path("/tmp/abl-scratch/f10-%d/cfg" % PORT); cfg.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(["rm","-rf",str(cfg)], check=False)
log = cfg.parent / "launch.log"
with log.open("w") as fh:
    subprocess.run(["bash", str(ROOT/"tools/launch_repro_playback.sh"),
                    "--execution-mode","Interpreter","--config-dir",str(cfg),
                    "--port",str(PORT),"--token","debugger-1000",
                    "--disc",str(ROOT/"Disney-Pixar A Bug's Life (v1.0).cue")],
                   cwd=str(ROOT), stdout=fh, stderr=fh, check=False)
t = log.read_text(); assert "READY" in t, t[-600:]
pid = t.split("pid=")[1].split()[0]
out = {"row":"F10_clover_forest","movie":MOVIE.name,
       "static_prediction":"mask 0x800B5774 takes five DISTINCT bits then 0x1F -> latch 1, fade 120"}
try:
    c = DebuggerClient("127.0.0.1", PORT, "ws"); c.authenticate("debugger-1000")
    c.transport.sock.settimeout(1800)
    st = c.call("movie.load", {"path": str(MOVIE.resolve())})
    out["frames"] = st.get("frame_count")
    anchor = int((json.loads(MOVIE.read_text()).get("start_state") or {}).get("frame") or 0)
    out["anchor"] = anchor
    assert c.call("movie.startPlayback", {"load_start_state": True}).get("playing")
    c.call("accessLog.clear", {})
    for a, ln in ((MASK,4),(COUNT,4),(LATCH,2),(FADE,2)):
        c.call("accessLog.addWatch", {"address":"0x%08x"%a,"length":ln,
                                      "type":"write","max_events":200000})
    c.call("debugger.resume", {})
    began, last, stalls = time.time(), -1, 0
    while time.time()-began < 2400:
        time.sleep(0.5)
        try: idx = c.call("movie.status", {}).get("playback_index")
        except Exception: idx = last
        if idx == last:
            stalls += 1
            if stalls >= 24: break
        else: stalls = 0
        last = idx
    ev, off = [], 0
    while True:
        p = c.call("accessLog.get", {"offset":off,"limit":10000})
        g = p.get("events") or []; ev.extend(g)
        if len(g) < 10000: break
        off += len(g)
finally:
    subprocess.run(["kill", pid], check=False); time.sleep(2)

by = {}
for e in ev:
    a = int(str(e.get("address","0")),16) & 0x1FFFFFFF | 0x80000000
    b = max((w for w in (MASK,COUNT,LATCH,FADE) if w <= a < w+4), default=None)
    if b is None: continue
    by.setdefault(b, []).append({"mf": (e.get("frame") or 0)-anchor,
                                 "pc": str(e.get("instruction_pc") or e.get("pc") or "").lower(),
                                 "v": e.get("new_value")})
m = by.get(MASK, [])
out["mask_writes"] = m[:60]
seq = [x["v"] for x in m if x["v"] is not None]
trans = [x for i,x in enumerate(m) if i==0 or x["v"]!=m[i-1]["v"]]
out["mask_transitions"] = trans[:40]
out["mask_reached_1f"] = 0x1F in seq
newbits, prev = [], 0
for x in trans:
    v = x["v"] or 0
    if v & ~prev: newbits.append({"mf":x["mf"],"new_bit":hex(v & ~prev),"mask":hex(v)})
    prev = v
out["distinct_bits_set"] = newbits
out["count_writes"] = by.get(COUNT, [])[:40]
out["latch_writes"] = by.get(LATCH, [])[:20]
out["fade_writes"] = by.get(FADE, [])[:20]
(ROOT/"analysis/phase4_f10_clover_objective.json").write_text(json.dumps(out,indent=1)+"\n")
print(json.dumps({k:out[k] for k in ("frames","anchor","mask_reached_1f",
                 "distinct_bits_set","mask_transitions","latch_writes","fade_writes")},
                 indent=1)[:2600])
