#!/usr/bin/env python3
"""Phase-2 soak/repeated-use oracle: reload determinism, idle stability, and
pause-cycle stress on pristine anchors.

  reload_x3       load each representative anchor 3 times; the typed snapshot
                  must be identical every time (anchor determinism under reuse).
  idle_soak       advance 3600 frames (1 emulated minute) in 600-frame chunks on
                  the two busiest rosters; per chunk: guest alive, scene stable,
                  typed snapshot recorded (drift documented, not assumed away).
  pause_cycle_x10 10 pause/unpause cycles at one anchor; the game must remain
                  alive, in-scene, and the player must still respond to input
                  afterwards (repeated-use of the pause system).

Usage: python3 tools/phase2_soak.py [--port 23472]
Output: analysis/phase2_soak.json
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

SNAPSHOT_FIELDS = [
    ("scene_id", 0x80082504, "u32"),
    ("player_x", 0x800A6500, "s32"),
    ("player_y", 0x800A6504, "s32"),
    ("player_z", 0x800A6508, "s32"),
    ("health", 0x800A7E2A, "s16"),
    ("lives", 0x800A65A0, "u8"),
    ("grain", 0x800A65A1, "u8"),
    ("enemy_quota", 0x800A658E, "u8"),
]
RELOAD_ANCHORS = ["level01.sav", "level02.sav", "level_09.sav",
                  "level_15.sav", "movies/Bonus_Level_01.movie.sav"]
IDLE_ANCHORS = ["level02.sav", "level05.sav"]   # busiest actor rosters (63 each)
IDLE_CHUNKS, IDLE_CHUNK_FRAMES = 6, 600
PAUSE_CYCLES = 10


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient

    state = {}

    def connect():
        cli = DebuggerClient("127.0.0.1", args.port, "ws")
        cli.authenticate(args.token)
        cli.transport.sock.settimeout(300)
        state["c"] = cli

    connect()

    def call(method, params, retried=False):
        try:
            return state["c"].call(method, params)
        except (ConnectionError, OSError):
            # long advances can outlive the WS session; the emulator keeps going —
            # reconnect, confirm the guest is alive, and retry once (skill rule)
            if retried:
                raise
            connect()
            st = state["c"].call("debugger.status", {})
            assert st.get("valid", True), f"guest dead after reconnect: {st}"
            if method == "emulator.advanceFrames":
                state["c"].call("debugger.pause", {})
                return {"reconnected": True}
            return call(method, params, retried=True)

    class _C:  # thin shim so existing call sites keep working
        def call(self, method, params):
            return call(method, params)
    c = _C()

    def rd(addr, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % addr, "length": n})["hex"])

    def snapshot() -> dict:
        snap = {}
        for name, addr, width in SNAPSHOT_FIELDS:
            raw = rd(addr, {"u8": 1, "s16": 2, "u32": 4, "s32": 4}[width])
            fmt = {"u8": "<B", "s16": "<h", "u32": "<I", "s32": "<i"}[width]
            snap[name] = struct.unpack(fmt, raw)[0]
        return snap

    def load(sav):
        for method in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(method, {})
            except Exception:
                pass
        r = c.call("emulator.loadState", {"path": str(ROOT / sav),
                                          "pause_after_load": True})
        assert r.get("loaded"), r
        c.call("emulator.clearControllerState", {"port": 0})

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    results: dict = {}

    # ---- reload determinism x3 ----------------------------------------------
    reload_res = {}
    for sav in RELOAD_ANCHORS:
        snaps = []
        for _ in range(3):
            load(sav)
            snaps.append(snapshot())
        reload_res[sav] = {"deterministic": snaps[0] == snaps[1] == snaps[2],
                           "snapshot": snaps[0]}
        print(f"[soak] reload_x3 {sav}: deterministic={reload_res[sav]['deterministic']}")
    results["reload_x3"] = reload_res

    # ---- idle soak ------------------------------------------------------------
    idle_res = {}
    for sav in IDLE_ANCHORS:
        load(sav)
        base = snapshot()
        chunks = []
        alive = True
        for i in range(IDLE_CHUNKS):
            c.call("emulator.advanceFrames", {"frames": IDLE_CHUNK_FRAMES})
            c.call("debugger.pause", {})
            st = c.call("debugger.status", {})
            snap = snapshot()
            chunks.append(snap)
            if not st.get("valid", True) or snap["scene_id"] != base["scene_id"]:
                alive = False
                break
        idle_res[sav] = {
            "frames_total": IDLE_CHUNKS * IDLE_CHUNK_FRAMES,
            "base": base, "chunks": chunks,
            "guest_alive_in_scene": alive,
            "health_stable": all(s["health"] == base["health"] for s in chunks),
            "drifting_fields": sorted({k for s in chunks for k in s
                                       if s[k] != base[k]}),
        }
        print(f"[soak] idle {sav}: alive={alive}, drift={idle_res[sav]['drifting_fields']}")
    results["idle_soak"] = idle_res

    # ---- pause cycle x10 -------------------------------------------------------
    load("level02.sav")
    base = snapshot()
    for _ in range(PAUSE_CYCLES * 2):   # toggle pause on/off
        c.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
        c.call("emulator.advanceFrames", {"frames": 3})
        c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.advanceFrames", {"frames": 12})
    c.call("debugger.pause", {})
    after_cycles = snapshot()
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    c.call("emulator.advanceFrames", {"frames": 60})
    c.call("debugger.pause", {})
    moved = snapshot()
    c.call("emulator.clearControllerState", {"port": 0})
    displacement = (abs(moved["player_x"] - after_cycles["player_x"])
                    + abs(moved["player_z"] - after_cycles["player_z"]))
    results["pause_cycle_x10"] = {
        "anchor": "level02.sav", "cycles": PAUSE_CYCLES,
        "base": base, "after_cycles": after_cycles, "after_input": moved,
        "still_in_scene": after_cycles["scene_id"] == base["scene_id"],
        "responds_to_input_after": displacement > 500,
        "displacement_after": displacement,
    }
    print(f"[soak] pause_cycle_x10: in_scene="
          f"{results['pause_cycle_x10']['still_in_scene']}, "
          f"responsive={results['pause_cycle_x10']['responds_to_input_after']}")

    doc = {
        "_comment": "Phase-2 soak/repeated-use oracle on pristine anchors. "
                    "Regenerate: tools/phase2_soak.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "results": results,
    }
    out = ROOT / "analysis" / "phase2_soak.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[soak] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
