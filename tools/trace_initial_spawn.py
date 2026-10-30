#!/usr/bin/env python3
"""GAP-0035 layer-1: trace the initial level-load player spawn over the DuckStation
external-debugger API (write-watch + execTrace), reproducibly.

WHAT IT PROVES (LEVEL01, SCUS-94288):
  The live player block 0x800A6500 (168 bytes / 0xA8, BSS-zero at boot) is first
  filled at level load by FUNC_80046B20(a0=player_block, a1=scene_index), called
  from inside scene-init FUNC_8005B714(scene_id) at 0x8005baa4 (a1 = s2 = a0 =
  scene_id). FUNC_80046B20 reads a RESIDENT EXE table at 0x80077314 + index*12
  (12-byte records); for LEVEL01 index=1 -> 0x80077320:
     record +0 (word0) -> player X   (0x800A6500)
     record +4 (word1) -> player Z   (0x800A6508)
     record +8 (word2) -> heading    (0x800A6520/+0x28/+0x78)
     player Y (0x800A6504) is COMPUTED: FUNC_80037A38(pos) (ground height) - 0x100
  It also writes the previous/render copy (+0x10/14/18) and respawn anchor
  (+0x50/54/58) from the live XYZ, sets flags/counters (+0x94=4,+0x98=17), and
  PRESERVES the lives byte (+0xa0). The struct zero is BIOS memset via helper
  0x8005f7ac (that is why a naive write-watch first flags BIOS PC 0xbfc02bb4).

  => The spawn source is NEITHER LEVEL.DAT nor the LEVEL.BIN-baked area at
     0x80096d18; it is a per-scene table baked in the boot EXE (SCUS_942.88,
     file offset 0x67b14). Disc-editable player-start lever.

HOW TO RUN (isolated instance; never touches your own DuckStation):
  DUCK=${DUCKSTATION_DIR:-~/duckstation}
  "$DUCK"/scripts/debugger-client/launch_debugger_instance.sh start \
      --disc "/abs/Disney-Pixar A Bug's Life (v1.0).cue" --port 23460 --no-fastboot
  python3 tools/trace_initial_spawn.py all          # recon + capture + trace + table
  "$DUCK"/scripts/debugger-client/launch_debugger_instance.sh stop

Config via environment / args (host-portable; NO hardcoded paths):
  DUCKSTATION_DIR  fork checkout (default: ~/duckstation)  -> debugger-client on sys.path
  ABL_DBG_PORT     debugger port   (default: 23460)
  ABL_DBG_TOKEN    auth token      (default: debugger-<uid>, e.g. debugger-1000)
  --movie PATH     boot->LEVEL01 movie (default: ./flik_to_level01_stall.mv.movie.json)
  --exe PATH       boot EXE for the offline table cross-check (default: ./SCUS_942.88)
"""
import sys, os, struct, json, argparse

_DUCK = os.environ.get("DUCKSTATION_DIR", os.path.expanduser("~/duckstation"))
sys.path.insert(0, os.path.join(_DUCK, "scripts", "debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

PLAYER = 0x800A6500          # live player block base (X); Y=+4, Z=+8
BLOCK_LEN = 0xA8             # player struct size (zeroed by memset at spawn)
SPAWN_FN = 0x80046B20        # FUNC_80046B20(a0=player, a1=index)
SPAWN_SRC_LD = 0x80046B88    # lw v0,0(s0): s0 = source record ptr
TABLE = 0x80077314           # resident per-scene start table, stride 12
DEF_PORT = int(os.environ.get("ABL_DBG_PORT", "23460"))
DEF_TOKEN = os.environ.get("ABL_DBG_TOKEN", "debugger-%d" % os.getuid())


def connect(port, token):
    c = DebuggerClient("127.0.0.1", port, "ws")
    c.authenticate(token)
    # the socket hangs forever on a guest crash otherwise (CLAUDE.md)
    try:
        c.transport.sock.settimeout(60)
    except Exception:
        pass
    return c


def ru32(c, a):
    h = c.call("debugger.readMemory", {"address": "0x%08x" % a, "length": 4})["hex"]
    return struct.unpack("<I", bytes.fromhex(h))[0]


def rmem(c, a, n):
    return bytes.fromhex(c.call("debugger.readMemory", {"address": "0x%08x" % a, "length": n})["hex"])


def s32(v):
    return v - 0x100000000 if v >= 0x80000000 else v


def safe(c, m, p=None):
    try:
        return c.call(m, p or {})
    except Exception as e:
        return {"_err": str(e)}


def start_movie(c, movie):
    safe(c, "movie.stopPlayback")
    fc = c.call("movie.load", {"path": movie}).get("frame_count")
    pb = c.call("movie.startPlayback", {"load_start_state": True})
    safe(c, "emulator.setFastForward", {"enabled": True})
    return fc, pb


def fast_to(c, target, frm=0):
    """advance (no watch) to a target frame; returns new frame counter."""
    while frm < target:
        n = min(600, target - frm)
        c.call("emulator.advanceFrames", {"frames": n})
        frm += n
    return frm


def cmd_recon(c, movie):
    print("== RECON: replay boot->LEVEL01, find spawn frame (X first non-zero) ==")
    fc, _ = start_movie(c, movie)
    print("movie frames:", fc)
    frm = 0
    while frm < fc + 200:
        c.call("emulator.advanceFrames", {"frames": 200}); frm += 200
        x = ru32(c, PLAYER)
        if frm % 800 == 0 or x:
            print("  f~%5d X=%9d Z=%9d scene=%d" %
                  (frm, s32(x), s32(ru32(c, PLAYER + 8)), ru32(c, 0x80082504)))
        if x:
            print("  >>> spawn happened in (%d,%d]; X=0x%x Z=0x%x" %
                  (frm - 200, frm, x, ru32(c, PLAYER + 8)))
            return frm
    print("  spawn not observed")
    return None


def cmd_capture(c, movie, arm_at=3800):
    print("== CAPTURE: arm broad WRITE-watch before spawn, find first writer of X ==")
    start_movie(c, movie)
    frm = fast_to(c, arm_at)
    assert ru32(c, PLAYER) == 0, "X already non-zero at arm point %d" % arm_at
    c.call("emulator.advanceFrames", {"frames": 1}); frm += 1   # settle before addWatch
    c.call("accessLog.addWatch", {"address": "0x%08x" % PLAYER, "length": BLOCK_LEN,
                                   "type": "write", "label": "playerblock", "max_events": 40000})
    while frm < arm_at + 900:
        c.call("emulator.advanceFrames", {"frames": 20}); frm += 20
        if ru32(c, PLAYER):
            break
    fw = c.call("accessLog.findFirstWrite", {"address": "0x%08x" % PLAYER}).get("writer", {})
    print("  findFirstWrite X:", json.dumps(fw))
    ev = c.call("accessLog.get", {"limit": 10000}).get("events", [])
    real = [e for e in ev if e["pc"] != "0xbfc02bb4"]   # drop the BIOS memset bytes
    print("  retained events: %d (%d non-memset). Field writes by the spawn fn:" % (len(ev), len(real)))
    for e in real[:40]:
        nv = e.get("new_value")
        print("    f=%s pc=%s addr=%s new=%s" %
              (e["frame"], e["pc"], e["address"], hex(nv) if isinstance(nv, int) else nv))
    return real


def cmd_trace(c, movie, arm_at=3800):
    print("== TRACE: execTrace at spawn entry + source-load -> a0/a1/ra + src ptr ==")
    start_movie(c, movie)
    frm = fast_to(c, arm_at)
    c.call("emulator.advanceFrames", {"frames": 1}); frm += 1
    c.call("execTrace.addWatch", {"pc": "0x%08x" % SPAWN_FN,
                                  "capture": ["a0", "a1", "a2", "ra", "sp", "gp"], "max_events": 50})
    c.call("execTrace.addWatch", {"pc": "0x%08x" % SPAWN_SRC_LD,
                                  "capture": ["s0", "v0", "s3"], "max_events": 50})
    while frm < arm_at + 900:
        c.call("emulator.advanceFrames", {"frames": 20}); frm += 20
        if ru32(c, PLAYER):
            break
    for e in c.call("execTrace.get", {"limit": 200}).get("events", []):
        print("  pc=%s frame=%s regs=%s" % (e["pc"], e["frame"], json.dumps(e.get("regs", {}))))


def cmd_table(c, exe, n=18):
    print("== TABLE: resident start table @0x%08x (runtime) vs EXE file ==" % TABLE)
    buf = rmem(c, TABLE, n * 12)
    fbuf = None
    if exe and os.path.exists(exe):
        data = open(exe, "rb").read()
        foff = TABLE - 0x80010000 + 0x800     # PS-EXE: text VA 0x80010000, file hdr 0x800
        fbuf = data[foff:foff + n * 12]
        print("  EXE file offset of table: 0x%x (cross-check)" % foff)
    print("  idx        X            Z         heading   match")
    for i in range(n):
        o = i * 12
        w0, w1, w2 = struct.unpack_from("<III", buf, o)
        ok = "==EXE" if (fbuf and fbuf[o:o + 12] == buf[o:o + 12]) else ""
        print("  %3d %11d %11d  0x%08x  %s" % (i, s32(w0), s32(w1), w2, ok))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="all",
                    choices=["recon", "capture", "trace", "table", "all"])
    ap.add_argument("--port", type=int, default=DEF_PORT)
    ap.add_argument("--token", default=DEF_TOKEN)
    ap.add_argument("--movie", default=os.path.join(os.getcwd(), "flik_to_level01_stall.mv.movie.json"))
    ap.add_argument("--exe", default=str(ROOT / "REBUILD" / "files" / "SCUS_942.88"))
    a = ap.parse_args()
    c = connect(a.port, a.token)
    if a.cmd in ("recon", "all"):
        cmd_recon(c, a.movie)
    if a.cmd in ("capture", "all"):
        cmd_capture(c, a.movie)
    if a.cmd in ("trace", "all"):
        cmd_trace(c, a.movie)
    if a.cmd in ("table", "all"):
        cmd_table(c, a.exe)


if __name__ == "__main__":
    main()
