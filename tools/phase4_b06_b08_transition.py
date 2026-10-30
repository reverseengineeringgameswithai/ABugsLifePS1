import json, struct, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path.home()/"duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient

def _scratch(name: str) -> "pathlib.Path":
    """Portable scratch dir. Was a hard-coded ~/.claude/jobs/<session>/ path in
    the first committed version of these tools -- machine- AND session-specific, so they
    could not run for anyone else. Override with ABL_SCRATCH."""
    import os, tempfile, pathlib as _p
    # Prefer an explicit override, then the harness job dir. Falling straight to the
    # system temp dir is a poor default here: /tmp is a RAM-backed tmpfs under a user
    # quota on this machine, and prior verification clones had already taken 49 GB of it.
    base = (os.environ.get("ABL_SCRATCH")
            or (os.environ.get("CLAUDE_JOB_DIR") and
                _p.Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp" / "abl-scratch")
            or _p.Path(tempfile.gettempdir()) / "abl-scratch")
    p = _p.Path(base) / name
    p.mkdir(parents=True, exist_ok=True)
    return p

ROOT=Path("~/Downloads/ABL"); TMP=_scratch("trans3")
TMP.mkdir(parents=True, exist_ok=True)
port=int(sys.argv[1]); movie=sys.argv[2]; poke_at=int(sys.argv[3])
SLOT=0x800A657E; SCENE=0x80082504; TICK="0x80048654"; CLEAR="0x8005b268"
subprocess.run(["rm","-rf",str(TMP/"cfg")],check=False)
log=TMP/"launch.log"
with log.open("w") as fh:
    subprocess.run(["bash",str(ROOT/"tools/launch_repro_playback.sh"),"--execution-mode","Interpreter",
                    "--config-dir",str(TMP/"cfg"),"--port",str(port),"--token","debugger-1000",
                    "--disc",str(ROOT/"Disney-Pixar A Bug's Life (v1.0).cue")],
                   cwd=str(ROOT),stdout=fh,stderr=fh,check=False)
t=log.read_text()
if "READY" not in t: raise SystemExit("launch failed\n"+t[-400:])
pid=t.split("pid=")[1].split()[0]
def rd(c,a,n): return bytes.fromhex(c.call("debugger.readMemory",{"address":"0x%08x"%a,"length":n})["hex"])
def sc(c): return struct.unpack("<I",rd(c,SCENE,4))[0]
def sl(c): return struct.unpack("<h",rd(c,SLOT,2))[0]
try:
    c=DebuggerClient("127.0.0.1",port,"ws"); c.authenticate("debugger-1000"); c.transport.sock.settimeout(900)
    n=c.call("movie.load",{"path":movie})["frame_count"]
    c.call("movie.startPlayback",{"load_start_state":True})
    out={"movie":Path(movie).name,"poke_at":poke_at,"scene_before":sc(c)}
    c.call("accessLog.clear",{})
    c.call("accessLog.addWatch",{"address":"0x%08x"%SLOT,"length":2,"type":"write","max_events":200000})
    c.call("debugger.resume",{})
    poked=False; began=time.time(); last=-1; stalls=0
    while time.time()-began<240:
        time.sleep(0.4)
        try: idx=c.call("movie.status",{}).get("playback_index")
        except Exception: idx=last
        if idx is not None and not poked and idx>=poke_at:
            c.call("debugger.writeMemory",{"address":"0x%08x"%SLOT,"hex":struct.pack("<h",20000).hex()})
            poked=True; out["poked_at_actual"]=idx
        if idx==last:
            stalls+=1
            if stalls>=6: break
        else: stalls=0
        last=idx
    out["movie_end"]={"scene":sc(c),"slot":sl(c)}
    # Drive the results/continue screens: the movie's input stops at its last frame, so
    # nothing advances past them and the next level never loads.
    trail=[]
    for i in range(40):
        for btn in ("cross","start"):
            try: c.call("emulator.pressButton",{"button":btn,"frames":3,"port":0,"release_after":True})
            except Exception: pass
        c.call("emulator.advanceFrames",{"frames":180})
        trail.append({"scene":sc(c),"slot":sl(c)})
        if len(trail)>3 and trail[-1]["scene"] not in (0, out["scene_before"]) and trail[-1]["slot"]!=trail[-3]["slot"]:
            break
    out["menu_drive_track"]=trail[::3]
    ev=[];off=0
    while True:
        pg=c.call("accessLog.get",{"offset":off,"limit":10000}); got=pg.get("events") or []
        ev.extend(got)
        if len(got)<10000: break
        off+=len(got)
    E=[{"f":e.get("frame"),"pc":str(e.get("instruction_pc") or e.get("pc") or "").lower(),
        "new":struct.unpack("<h",struct.pack("<H",(e.get("new_value") or 0)&0xFFFF))[0]} for e in ev]
    out["slot_writer_pcs"]=sorted({e["pc"] for e in E})
    out["writes_after_poke"]=[e for e in E if e["pc"]!=TICK][-8:]
    out["last_10_writes"]=E[-10:]
    out["scene_after"]=trail[-1]["scene"]; out["slot_after"]=trail[-1]["slot"]
    # "did gameplay resume" is the real question, not "is the scene number different" --
    # a level can legitimately reload the same scene id.
    gameplay = out["scene_after"] not in (0,)
    ticked_late = any(e["pc"]==TICK and e["new"]<20000 and e["new"]>0 for e in E)
    cleared = any(e["pc"]==CLEAR for e in E)
    out["reached_new_gameplay_scene"]=gameplay
    out["cleared_by_respawn_site"]=cleared
    if not gameplay:
        out["verdict"]="INCONCLUSIVE - never reached a new gameplay scene (final scene %s)"%out["scene_after"]
        out["conclusive"]=False
    elif out["slot_after"]==0 or cleared:
        out["verdict"]="power CLEARED across the transition (slot %s, respawn-site write=%s)"%(out["slot_after"],cleared)
        out["conclusive"]=True
    else:
        out["verdict"]="power SURVIVED into gameplay scene %s with slot %s"%(out["scene_after"],out["slot_after"])
        out["conclusive"]=True
    print(json.dumps(out,indent=1))
    (_scratch("trans3") / "trans3_result.json").write_text(json.dumps(out,indent=1))
finally:
    subprocess.run(["kill",pid],check=False); time.sleep(2)
