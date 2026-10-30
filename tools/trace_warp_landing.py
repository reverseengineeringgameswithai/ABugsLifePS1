#!/usr/bin/env python3
"""GAP-0035 live warp-landing capture (SCUS-94288) over the DuckStation external debugger.

WHAT IT PROVES:
  A scene transition into a NON-LEVEL01 level lands via the SAME spawn path as the
  cold LEVEL01 spawn: scene-init FUNC_8005B714(scene_id) -> FUNC_80046B20(player,
  scene_id) reads the resident EXE table 0x80077314 + scene_id*12 and writes the
  whole player block. Confirmed live for scene indices 3, 6, 2 (no crash).

THE CLEAN LEVER (why a plain [0x80082504] poke fails):
  The cold-boot load does NOT use the in-game warp orchestrator FUNC_8005222C
  (no 19->0->restore writes). The shell SM writes scene_id once from the
  level-select table:  scene_id = scene_table[0x80077fa0 + idx*4]  (LEVEL01 = idx1).
  scene-init FUNC_8005B714 is entered AT that write (frame ~3486 in the boot movie),
  LATCHES the index (a0=scene_id), triggers the CD load, waits ~1000 frames, then
  calls the spawn at load-complete (frame ~4518). Because the index is latched at
  scene-init entry, a LATE [0x80082504] poke does not divert the spawn and corrupts
  the flow (crash to BIOS 0xbfc0xxxx -- the documented GAP-0035 wall).
  -> The clean diversion is to overwrite the SELECTION SOURCE scene_table[1]
     (0x80077fa4) BEFORE the front-end reads it; the game then natively loads the
     target stage and spawns table[target], consistently, with no crash.

Halting note: execute breakpoints / execTrace stop_on_hit do NOT halt during movie
  playback (advanceFrames/resume run through them); only the non-halting accessLog /
  execTrace record. So this captures via watches + a pre-write memory poke, no halt.

RUN (isolated instance; never touches your own DuckStation):
  DUCK=${DUCKSTATION_DIR:-~/duckstation}
  "$DUCK"/scripts/debugger-client/launch_debugger_instance.sh start \
      --disc "/abs/Disney-Pixar A Bug's Life (v1.0).cue" --port 23460 --no-fastboot
  python3 tools/trace_warp_landing.py --target 3      # divert cold boot to scene 3
  python3 tools/trace_warp_landing.py --survey        # read scene_id+anchor of per-level saves

Config (host-portable; NO hardcoded paths):
  DUCKSTATION_DIR / ABL_DBG_PORT(23460) / ABL_DBG_TOKEN(debugger-<uid>)
  --movie PATH  (default ./flik_to_level01_stall.mv.movie.json)
  --target N    scene/stage index 1..15 to divert the cold boot to (default 3)
"""
import sys, os, struct, json, argparse
sys.path.insert(0, os.path.join(os.environ.get("DUCKSTATION_DIR", os.path.expanduser("~/duckstation")),
                                "scripts", "debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

PLAYER = 0x800A6500
SCENE_ID = 0x80082504          # current scene/stage id (read by loader + scene-init)
LOADED_STAGE = 0x800822FC      # loaded-stage tracker
SCENE_TABLE = 0x80077FA0       # level-select table {0x11,1,3,2,6,0xa,0xb,4}; LEVEL01 = idx1
SCENE_TABLE_IDX1 = SCENE_TABLE + 4
SPAWN_FN = 0x80046B20          # FUNC_80046B20(a0=player, a1=scene_index)
SPAWN_SRC_LD = 0x80046B88      # s0 = source record ptr = 0x80077314 + index*12
SCENE_INIT = 0x8005B70C        # FUNC_8005B714(a0=scene_id) -- latches index, loads, spawns
START_TABLE = 0x80077314       # resident per-scene spawn table (12-byte records)
DEF_PORT = int(os.environ.get("ABL_DBG_PORT", "23460"))
DEF_TOKEN = os.environ.get("ABL_DBG_TOKEN", "debugger-%d" % os.getuid())


def connect(port, token):
    c = DebuggerClient("127.0.0.1", port, "ws"); c.authenticate(token)
    try: c.transport.sock.settimeout(60)
    except Exception: pass
    return c


def ru32(c, a): return struct.unpack("<I", bytes.fromhex(c.call("debugger.readMemory", {"address": "0x%08x" % a, "length": 4})["hex"]))[0]
def wu32(c, a, v): c.call("debugger.writeMemory", {"address": "0x%08x" % a, "hex": struct.pack("<I", v & 0xffffffff).hex()})
def s32(v): return v - 0x100000000 if v >= 0x80000000 else v
def safe(c, m, p=None):
    try: return c.call(m, p or {})
    except Exception as e: return {"_err": str(e)}


def warp(c, movie, target):
    rec = struct.unpack("<iiI", bytes.fromhex(c.call("debugger.readMemory", {"address": "0x%08x" % (START_TABLE + target * 12), "length": 12})["hex"]))
    safe(c, "movie.stopPlayback"); safe(c, "debugger.clearBreakpoints")
    c.call("movie.load", {"path": movie}); c.call("movie.startPlayback", {"load_start_state": True})
    c.call("emulator.setFastForward", {"enabled": True})
    t = 0
    while t < 3000:                                   # FF through front-end (scene_id still 0)
        n = min(600, 3000 - t); c.call("emulator.advanceFrames", {"frames": n}); t += n
    wu32(c, SCENE_TABLE_IDX1, target)                 # DIVERT: level-select value 1 -> target, before frame ~3486
    c.call("execTrace.clear", {}); c.call("accessLog.clear", {})
    c.call("execTrace.addWatch", {"pc": "0x%08x" % SCENE_INIT, "capture": ["a0", "ra"], "label": "sceneinit"})
    c.call("execTrace.addWatch", {"pc": "0x%08x" % SPAWN_FN, "capture": ["a0", "a1", "ra"], "label": "spawn"})
    c.call("execTrace.addWatch", {"pc": "0x%08x" % SPAWN_SRC_LD, "capture": ["s0"], "label": "srcload"})
    for _ in range(180):
        c.call("emulator.advanceFrames", {"frames": 15}); t += 15
        if ru32(c, PLAYER) != 0: break
    pc = c.call("debugger.status", {}).get("pc", "")
    tr = c.call("execTrace.get", {"limit": 30}).get("events", [])
    def reg(pcv, name):
        for e in tr:
            if e["pc"] == pcv: return e["regs"].get(name)
        return None
    out = {
        "target": target, "scene": ru32(c, SCENE_ID), "stage": ru32(c, LOADED_STAGE) & 0xffff,
        "sceneinit_a0": reg("0x%08x" % SCENE_INIT, "a0"),
        "spawn_a1": reg("0x%08x" % SPAWN_FN, "a1"),
        "src_s0": reg("0x%08x" % SPAWN_SRC_LD, "s0"), "src_expect": "0x%08x" % (START_TABLE + target * 12),
        "liveXZ": (s32(ru32(c, PLAYER)), s32(ru32(c, PLAYER + 8))),
        "anchorXZ": (s32(ru32(c, 0x800A6550)), s32(ru32(c, 0x800A6558))),
        "head": "0x%x" % ru32(c, 0x800A6520), "table_rec_XZhead": (rec[0], rec[1], "0x%x" % rec[2]),
        "pc": pc, "crashed": pc.startswith("0xbfc"),
    }
    return out


def survey(c):
    """Read scene_id + spawn-anchor of per-level saves; cross-check anchor == table[scene_id]."""
    import glob
    rows = []
    for sv in sorted(glob.glob(os.path.join(os.getcwd(), "level*.sav"))):
        if safe(c, "emulator.loadState", {"path": sv}).get("_err"): continue
        c.call("emulator.advanceFrames", {"frames": 2})
        sc = ru32(c, SCENE_ID)
        rec = struct.unpack("<iiI", bytes.fromhex(c.call("debugger.readMemory", {"address": "0x%08x" % (START_TABLE + sc * 12), "length": 12})["hex"])) if 0 < sc < 64 else (0, 0, 0)
        rows.append({"save": os.path.basename(sv), "scene": sc, "stage": ru32(c, LOADED_STAGE) & 0xffff,
                     "anchorXZ": (s32(ru32(c, 0x800A6550)), s32(ru32(c, 0x800A6558))),
                     "table_rec_XZ": (rec[0], rec[1])})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=3)
    ap.add_argument("--port", type=int, default=DEF_PORT)
    ap.add_argument("--token", default=DEF_TOKEN)
    ap.add_argument("--movie", default=os.path.join(os.getcwd(), "flik_to_level01_stall.mv.movie.json"))
    ap.add_argument("--survey", action="store_true", help="survey per-level saves instead of a live warp")
    a = ap.parse_args()
    c = connect(a.port, a.token)
    if a.survey:
        for r in survey(c): print(json.dumps(r))
    else:
        print(json.dumps(warp(c, a.movie, a.target), indent=2))


if __name__ == "__main__":
    main()
