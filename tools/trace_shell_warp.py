#!/usr/bin/env python3
"""GAP-0035 in-game warp TRIGGER / shell-vs-gameplay investigation (SCUS-94288)
over the DuckStation external debugger.

WHAT IT ESTABLISHES (companion to tools/trace_warp_landing.py, which proved the LANDING):
  The level-transition LOAD orchestrator FUNC_8005222C is reached ONLY from the
  shell-phase state machine (substate-5 load case 0x8004fca0, + a 2nd caller
  0x8005028c gated on state byte 0x8009b888). It does NOT run during the cold boot
  (which uses the substate-0 path: scene_id = scene_table[idx] then scene-init) nor
  during gameplay.

  Per-frame top loop (region 0x8004fe70): a GATE [0x8008224e] selects dispatch --
      gate == 0  -> GAMEPLAY loop  0x8004ecd4 (+ dispatcher 0x80054964(scene_id))
      gate != 0  -> SHELL/menu     0x8004f478 (its own sub-state machine; reaches the
                                                substate machine -> substate 5 -> orch)
  scene_id [0x80082504] is the native PRE-LATCH selection result: scene_id =
  scene_table[ [0x8008245c] ] (scene_table @ 0x80077fa0). [0x8008245c] (scene-table
  index) is the safe pre-latch lever (front-end/overlay writes it; the shell common
  tail commits scene_id).

  WHY mid-gameplay scene_id pokes crash: during gameplay scene_id is READ ~15x/frame
  by gameplay + overlay consumers; mutating it -> wrong per-frame dispatch -> BIOS
  crash (observed pc ~0xbfc02bac). Forcing substate=5 ALONE or gate=1 ALONE does NOT
  crash (the shell SM simply isn't the active dispatch during gameplay).

ADDRESSES
  shell SM / substate machine 0x8004fa40 ; substate [0x8008243c] ; dispatch jr [0x8001b3c4+sub*4]
  scene-table index [0x8008245c] ; scene_table 0x80077fa0 ; scene_id [0x80082504]
  gameplay loop 0x8004ecd4 ; dispatcher 0x80054964 ; gameplay<->shell gate [0x8008224e]
  shell/menu handler 0x8004f478 ; orchestrator FUNC_8005222C 0x8005222c (callers 0x8004fca8,0x8005028c)
  scene-init FUNC_8005B714 0x8005b70c ; spawn FUNC_80046B20 0x80046b20

RUN (isolated instance; never touches your own DuckStation):
  DUCK=${DUCKSTATION_DIR:-~/duckstation}
  "$DUCK"/scripts/debugger-client/launch_debugger_instance.sh start \
      --disc "/abs/Disney-Pixar A Bug's Life (v1.0).cue" --port 23460 --no-fastboot
  python3 tools/trace_shell_warp.py boot     # substate/scene_id/orchestrator across cold boot
  python3 tools/trace_shell_warp.py loops    # which loop runs in-level + scene_id readers (needs a *.sav)
  python3 tools/trace_shell_warp.py crash    # reproduce scene_id-poke crash + isolate safe levers (needs a *.sav)
  python3 tools/trace_shell_warp.py trigger  # capture native transition lever [0x800823a0] (type scan; needs a *.sav)

Config (host-portable; NO hardcoded paths): DUCKSTATION_DIR / ABL_DBG_PORT(23460) /
  ABL_DBG_TOKEN(debugger-<uid>) ; --movie (default ./flik_to_level01_stall.mv.movie.json)
  ; --sav (default ./level02.sav).
"""
import sys, os, struct, json, argparse
sys.path.insert(0, os.path.join(os.environ.get("DUCKSTATION_DIR", os.path.expanduser("~/duckstation")),
                                "scripts", "debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

SUBSTATE = 0x8008243C      # shell-SM substate (dispatch jr [0x8001b3c4 + sub*4])
SCENE_IDX = 0x8008245C     # scene-table index (pre-latch selection source)
SCENE_ID = 0x80082504      # current scene id (hot per-frame dispatch key)
GATE = 0x8008224E          # gameplay(0) <-> shell(!=0) selector
PLAYER = 0x800A6500
ORCH = 0x8005222C          # FUNC_8005222C (shell-only load orchestrator)
SCENE_INIT = 0x8005B70C    # FUNC_8005B714
SPAWN = 0x80046B20         # FUNC_80046B20
GAMELOOP = 0x8004ECD4
DISPATCH = 0x80054964
SHELL_SM = 0x8004FA40
TRANS_STATE = 0x800823A0   # transition-state lever (resident initiators set 1/2/6 -> fade handler progresses)
DEF_PORT = int(os.environ.get("ABL_DBG_PORT", "23460"))
DEF_TOKEN = os.environ.get("ABL_DBG_TOKEN", "debugger-%d" % os.getuid())


def connect(port, token):
    c = DebuggerClient("127.0.0.1", port, "ws"); c.authenticate(token)
    try: c.transport.sock.settimeout(60)
    except Exception: pass
    return c


def ru(c, a, n=4): return int.from_bytes(bytes.fromhex(c.call("debugger.readMemory", {"address": "0x%08x" % a, "length": n})["hex"]), "little")
def wu(c, a, v, n=4): c.call("debugger.writeMemory", {"address": "0x%08x" % a, "hex": int(v & (2**(8*n)-1)).to_bytes(n, "little").hex()})
def pc(c): return c.call("debugger.status", {}).get("pc", "")
def safe(c, m, p=None):
    try: return c.call(m, p or {})
    except Exception as e: return {"_err": str(e)}


def boot(c, movie):
    """Trace substate/idx/scene_id writes + orchestrator/scene-init/spawn across the cold boot."""
    safe(c, "movie.stopPlayback"); safe(c, "debugger.clearBreakpoints")
    c.call("movie.load", {"path": movie}); c.call("movie.startPlayback", {"load_start_state": True})
    c.call("emulator.setFastForward", {"enabled": True})
    t = 0
    while t < 2800:
        n = min(600, 2800 - t); c.call("emulator.advanceFrames", {"frames": n}); t += n
    c.call("emulator.advanceFrames", {"frames": 1}); t += 1
    for a, lbl in [(SUBSTATE, "sub"), (SCENE_IDX, "idx"), (SCENE_ID, "scene")]:
        c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": 2 if a != SCENE_ID else 4, "type": "write", "label": lbl, "max_events": 4000})
    for a, lbl in [(ORCH, "orch"), (SCENE_INIT, "sceneinit"), (SPAWN, "spawn")]:
        c.call("execTrace.addWatch", {"pc": "0x%08x" % a, "capture": ["a0", "a1", "ra"], "label": lbl, "max_events": 40})
    while t < 4700:
        c.call("emulator.advanceFrames", {"frames": 10}); t += 10
        if ru(c, PLAYER): break
    ex = c.call("execTrace.get", {"limit": 60}).get("events", [])
    print("orchestrator ran during cold boot:", any(e["pc"] == "0x%08x" % ORCH for e in ex), "(expect False)")
    for e in ex:
        print("  EXEC pc=%s f=%s regs=%s" % (e["pc"], e["frame"], json.dumps(e.get("regs", {}))))


def loops(c, sav):
    """Which top loop runs in-level, and how many consumers read scene_id per frame."""
    safe(c, "emulator.loadState", {"path": sav}); c.call("emulator.advanceFrames", {"frames": 2})
    print("scene_id=%d gate[0x8008224e]=%d substate=%d" % (ru(c, SCENE_ID), ru(c, GATE, 2), ru(c, SUBSTATE, 2)))
    for a, lbl in [(SHELL_SM, "shellSM"), (GAMELOOP, "gameLoop"), (DISPATCH, "dispatcher")]:
        c.call("execTrace.addWatch", {"pc": "0x%08x" % a, "capture": ["a0"], "label": lbl, "max_events": 30})
    c.call("emulator.advanceFrames", {"frames": 3})
    from collections import Counter
    hits = Counter(e["pc"] for e in c.call("execTrace.get", {"limit": 200}).get("events", []))
    print("loop hits/3f:", dict(hits), "(gameLoop=0x8004ecd4 runs; shellSM=0x8004fa40 should be 0)")
    c.call("execTrace.clear", {}); c.call("accessLog.clear", {})
    c.call("accessLog.addWatch", {"address": "0x%08x" % SCENE_ID, "length": 4, "type": "read", "label": "sr", "max_events": 80})
    c.call("emulator.advanceFrames", {"frames": 1})
    rd = c.call("accessLog.get", {"limit": 80}).get("events", [])
    print("scene_id readers in 1 gameplay frame: %d distinct PCs" % len({e["pc"] for e in rd}))


def crash(c, sav):
    """Reproduce the mid-gameplay scene_id-poke crash; isolate substate=5 / gate=1 as safe."""
    def run(label, addr, val, n=2):
        safe(c, "emulator.loadState", {"path": sav}); c.call("emulator.advanceFrames", {"frames": 2})
        wu(c, addr, val, n)
        for i in range(5):
            safe(c, "emulator.advanceFrames", {"frames": 1}); p = pc(c)
            if p.startswith("0xbfc"):
                print("  %-26s -> CRASH at %s (frame +%d)" % (label, p, i + 1)); return
        print("  %-26s -> no crash (pc=%s)" % (label, pc(c)))
    print("isolating the unsafe write:")
    run("poke scene_id (3->6)", SCENE_ID, 6, 4)
    run("force substate=5 alone", SUBSTATE, 5, 2)
    run("force gate=1 alone", GATE, 1, 2)


def trigger(c, sav):
    """Capture the NATIVE transition trigger: the transition-state lever [0x800823a0].
    Resident initiators (0x800496d8=type1, 0x8004a8b4=type2, 0x8004b3c0=type6, called by the
    per-scene overlay verbs on level-exit) set [0x800823a0] + a fade color + helpers. Poking it
    from gameplay: type-6 reproducibly engages the native gameplay->shell SM->scene-init path
    (scene-init FUNC_8005B714(a0=destination)); other types crash (need companion state) or are
    inert. The destination is shell-SM-selected (defaults to invalid scene 16 in this forced
    context -> crash; a clean level->level landing needs the overlay's exit setup, GAP-0033)."""
    for V in (1, 2, 3, 4, 5, 6, 7, 8):
        safe(c, "emulator.loadState", {"path": sav}); c.call("emulator.advanceFrames", {"frames": 2})
        base = ru(c, SCENE_ID)
        c.call("execTrace.clear", {})
        c.call("execTrace.addWatch", {"pc": "0x%08x" % SCENE_INIT, "capture": ["a0"], "label": "si", "max_events": 8})
        c.call("execTrace.addWatch", {"pc": "0x%08x" % ORCH, "capture": ["fp"], "label": "orch", "max_events": 8})
        wu(c, TRANS_STATE, V, 2)
        res = "inert"
        for i in range(20):
            safe(c, "emulator.advanceFrames", {"frames": 15})
            p = pc(c)
            if p.startswith("0xbfc"): res = "CRASH@%s" % p; break
            if ru(c, SCENE_ID) != base: res = "transition -> scene %d (pc=%s)" % (ru(c, SCENE_ID), p); break
        ev = c.call("execTrace.get", {"limit": 8}).get("events", [])
        si = [e["regs"].get("a0") for e in ev if e["pc"] == "0x%08x" % SCENE_INIT]
        print("  [0x800823a0]=%d -> %-34s scene-init a0=%s" % (V, res, si or "-"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["boot", "loops", "crash", "trigger"])
    ap.add_argument("--port", type=int, default=DEF_PORT)
    ap.add_argument("--token", default=DEF_TOKEN)
    ap.add_argument("--movie", default=os.path.join(os.getcwd(), "flik_to_level01_stall.mv.movie.json"))
    ap.add_argument("--sav", default=os.path.join(os.getcwd(), "level02.sav"))
    a = ap.parse_args()
    c = connect(a.port, a.token)
    if a.cmd == "boot": boot(c, a.movie)
    elif a.cmd == "loops": loops(c, a.sav)
    elif a.cmd == "crash": crash(c, a.sav)
    elif a.cmd == "trigger": trigger(c, a.sav)


if __name__ == "__main__":
    main()
