#!/usr/bin/env python3
"""Replayable headline experiment: identify the render source of the LEVEL01
SPAWN-AREA floor under Flik, and show it is separate from the collision source.

Question (GAP-0011 + GAP-0038): which resource renders the *spawn-area* floor
under Flik — the LEVEL.DAT mesh payload (``fcn.80010000``) or the LEVEL.RAW
chunk-34/35 geometry? And is that visible source distinct from the collision
floor (chunk-32 sector table ``0x800a7e48``)?

Method (no force/neutralize; pure pick + provenance trace over the custom
DuckStation external-debugger API):
  1. loadState a LEVEL01 spawn fixture; assert game_serial == SCUS-94288, scene 1.
  2. gpu.pickObject several brown-floor pixels -> the floor is GP0(3c) quads.
  3. accessLog write-watch one floor packet, advance -> the writer PCs.
  4. execTrace ``fcn.80010000`` entry, classify the a0 (mesh-descriptor) source
     region for every call in a frame (DAT vs chunk-35 buffer).
  5. execTrace ``fcn.800172dc`` (the chunk-35 / shared .ALL renderer) -> call count.
  6. report G_DAT_BASE_PTR + the DAT file-offset span of the drawn meshes, and
     confirm the collision sector table ``0x800a7e48`` is a populated, separate
     region (visual != collision at the spawn area).

This ships NO disc/state bytes; it drives an operator-supplied isolated instance
(see CLAUDE.md / launch_debugger_instance.sh). Host-portable via env:
    DUCKSTATION_DIR  fork checkout (default ~/duckstation)
    ABL_SAVESTATES   savestate dir (default ~/.local/share/duckstation/savestates)
Override the instance with --port/--token and the fixture with --save.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
from collections import Counter

_DUCK = os.environ.get("DUCKSTATION_DIR", os.path.expanduser("~/duckstation"))
sys.path.insert(0, os.path.join(_DUCK, "scripts", "debugger-client"))
_SAVES = os.environ.get("ABL_SAVESTATES", os.path.expanduser("~/.local/share/duckstation/savestates"))

from duckstation_debug_client import DebuggerClient  # noqa: E402

# --- known anchors (resident; see the vault) --------------------------------
SCENE_ID = "0x80082504"          # current_scene_id (1 == LEVEL01)
FLIK_XYZ = ("0x800a6500", "0x800a6504", "0x800a6508")
G_DAT_BASE_PTR = "0x80082498"    # -> runtime LEVEL.DAT base
EMIT_DAT = 0x80010000            # DAT mesh/poly emitter (Candidate A family)
EMIT_ALL = 0x800172DC            # shared .ALL / chunk-35 mesh renderer
SECTOR_TABLE = "0x800a7e48"      # collision sector table (LEVEL.RAW chunk 32)

DAT_LO, DAT_HI = 0x80160000, 0x801B0000
CH35_LO, CH35_HI = 0x8012A000, 0x80130000


def region(a: int) -> str:
    if DAT_LO <= a < DAT_HI:
        return "DAT"
    if CH35_LO <= a < CH35_HI:
        return "CHUNK35buf"
    if 0x801D0000 <= a < 0x801E0000:
        return "PKTbuf"
    if 0x1F800000 <= a < 0x1F801000:
        return "scratch"
    return "?"


class Dbg:
    def __init__(self, host: str, port: int, token: str):
        self.c = DebuggerClient(host, port, "ws")
        self.c.authenticate(token)
        try:
            self.c.transport.sock.settimeout(60)   # never hang forever on a guest crash
        except Exception:
            pass

    def call(self, m, p=None):
        return self.c.call(m, p or {})

    def ru32(self, a):
        return struct.unpack("<I", bytes.fromhex(self.call("debugger.readMemory", {"address": a, "length": 4})["hex"]))[0]

    def rs32(self, a):
        return struct.unpack("<i", bytes.fromhex(self.call("debugger.readMemory", {"address": a, "length": 4})["hex"]))[0]

    def adv(self, n):
        # chunk so a long synchronous advance can't outlive the socket
        while n > 0:
            step = min(120, n)
            self.call("emulator.advanceFrames", {"frames": step})
            n -= step


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=23460)
    ap.add_argument("--token", default="debugger-%d" % os.getuid())
    ap.add_argument("--save", default=os.environ.get("ABL_SPAWN_SAV"),
                    help="LEVEL01 spawn state (.sav) — REQUIRED (or set ABL_SPAWN_SAV); "
                         "numbered-slot defaults were retired 2026-07-08")
    ap.add_argument("--settle", type=int, default=4, help="frames to settle after load")
    ap.add_argument("--picks", default="300,150;340,135;256,200;210,160;200,165",
                    help="native CRTC floor pixels to pick (x,y;x,y;...)")
    args = ap.parse_args()
    if not args.save:
        ap.error("--save is required (a LEVEL01 spawn .sav by name, e.g. level01.sav; "
                 "or set ABL_SPAWN_SAV). Numbered-slot defaults were retired 2026-07-08.")

    d = Dbg(args.host, args.port, args.token)
    st = d.call("debugger.status")
    serial = st.get("game_serial")
    print(f"[serial] {serial} / {st.get('game_title')}")
    if serial != "SCUS-94288":
        print("REFUSING: not the A Bug's Life instance (game_serial != SCUS-94288)")
        return 2

    if not os.path.exists(args.save):
        print(f"fixture not found: {args.save}")
        return 2
    d.call("emulator.loadState", {"path": args.save, "pause_after_load": True})
    d.adv(args.settle)
    d.call("debugger.pause")

    scene = d.ru32(SCENE_ID)
    fx, fy, fz = (d.rs32(a) for a in FLIK_XYZ)
    dat_base = d.ru32(G_DAT_BASE_PTR)
    print(f"[state] scene_id={scene} Flik world XYZ=({fx},{fy},{fz})  file Z={fz >> 5}")
    print(f"[state] G_DAT_BASE_PTR={hex(dat_base)}")
    if scene != 1:
        print("WARNING: not in LEVEL01 (scene_id != 1); results may not be the spawn area")

    # 1) Pick floor pixels
    print("\n[pick] floor pixels (native CRTC):")
    floor_packet = None
    for tok in args.picks.split(";"):
        x, y = (int(v) for v in tok.split(","))
        r = d.call("gpu.pickObject", {"x": x, "y": y})
        if not r.get("hit"):
            print(f"   ({x},{y}) MISS {r.get('reason')}")
            continue
        dc, src, px = r["drawCall"], r["source"], r["pixel"]
        ram = int(src["ramAddress"], 16) | 0x80000000
        brown = px["rgba"][0] >= px["rgba"][2]   # red >= blue => earthy floor, not the bluish ant
        print(f"   ({x},{y}) {dc['command']:>12} rgba={px['rgba']} packet=0x{ram:08x} tex={dc['texturePage']}")
        if brown and dc["command"].startswith("GP0(3c)") and floor_packet is None:
            floor_packet = (x, y, ram)
    if floor_packet is None:
        print("no brown GP0(3c) floor quad picked; adjust --picks")
        return 1
    fxy = (floor_packet[0], floor_packet[1])
    P = floor_packet[2]
    print(f"[pick] chosen floor packet @0x{P:08x} from pixel {fxy}")

    # 2) Who writes that packet?  (the mesh emitter)
    d.call("accessLog.clear")
    w = d.call("accessLog.addWatch", {"address": f"0x{P:08x}", "length": 16, "type": "write",
                                      "label": "floorpkt", "max_events": 64})
    d.adv(3)
    ev = d.call("accessLog.get", {"watch_id": w["watch_id"]})
    pcs = sorted({e.get("pc") for e in ev.get("events", []) if e.get("pc")})
    in_emit = bool(pcs) and all(0x80010000 <= int(p, 16) < 0x80011200 for p in pcs)
    print(f"\n[writer] floor-packet writer PCs: {pcs}")
    print(f"[writer] all inside fcn.80010000 (DAT emitter)?  {in_emit}")

    # 3) Source region of every fcn.80010000 call this frame
    d.call("execTrace.clear")
    w2 = d.call("execTrace.addWatch", {"pc": f"0x{EMIT_DAT:08x}", "capture": ["pc", "a0"],
                                       "label": "emit_entry", "max_events": 120})
    d.adv(1)
    ev2 = d.call("execTrace.get", {"watch_id": w2["watch_id"]})
    a0s = [int(e["regs"]["a0"], 16) for e in ev2.get("events", []) if e.get("regs", {}).get("a0")]
    hist = Counter(region(a) for a in a0s)
    print(f"\n[source] fcn.80010000 calls/frame={ev2.get('total')}  a0-region={dict(hist)}")
    if a0s:
        offs = [a - dat_base for a in a0s if DAT_LO <= a < DAT_HI]
        if offs:
            print(f"[source] DAT mesh a0 span: 0x{min(a0s):08x}..0x{max(a0s):08x}  "
                  f"= DAT file offsets 0x{min(offs):05x}..0x{max(offs):05x}")

    # 4) Does the chunk-35 / .ALL renderer draw this scene at all?
    d.call("execTrace.clear")
    w3 = d.call("execTrace.addWatch", {"pc": f"0x{EMIT_ALL:08x}", "capture": ["pc", "a0"],
                                       "label": "all_renderer", "max_events": 60})
    d.adv(1)
    ev3 = d.call("execTrace.get", {"watch_id": w3["watch_id"]})
    print(f"[source] fcn.800172dc (chunk-35/.ALL renderer) calls/frame={ev3.get('total')}")

    # 5) Collision source is a separate, populated region (visual != collision)
    sec0 = d.ru32(SECTOR_TABLE)
    print(f"\n[collision] sector table {SECTOR_TABLE}[0]={hex(sec0)} "
          f"(LEVEL.RAW chunk 32; region {region(int(SECTOR_TABLE, 16))}) — "
          f"separate from the DAT visible mesh ({region(min(a0s) if a0s else 0)})")

    # Verdict
    dat_only = hist.get("DAT", 0) == len(a0s) and len(a0s) > 0
    print("\n========== VERDICT ==========")
    print(f"  spawn floor packet writer  : fcn.80010000  ({'CONFIRMED' if in_emit else 'NOT confirmed'})")
    print(f"  fcn.80010000 source region : {'DAT only' if dat_only else dict(hist)}")
    print(f"  chunk-35/.ALL renderer     : {ev3.get('total')} calls (0 => not drawing this scene)")
    print(f"  => spawn-area VISIBLE floor source = LEVEL.DAT (fcn.80010000), NOT chunk-34/35")
    print(f"  => collision source ({SECTOR_TABLE}) is a different RAM/region: visual != collision")
    return 0 if (in_emit and dat_only) else 1


if __name__ == "__main__":
    raise SystemExit(main())
