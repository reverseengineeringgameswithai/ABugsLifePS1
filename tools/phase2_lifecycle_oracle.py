#!/usr/bin/env python3
"""Phase-2 lifecycle oracle: death, respawn, game-over, save/reload, pause.

Bounded experiments from pristine anchors (every mutation is rolled back by the
next loadState; nothing persists):

  death_pit        stage01 anchor -> teleport player below the death plane
                   (Y positive = down; plane ~200000 per the smoke gate) ->
                   sample scene/health/lives/position each 30 frames until the
                   respawn lands -> death->respawn timeline + lives decrement +
                   respawn coordinates.
  game_over        same, after forcing lives=0 first -> observe the game-over
                   scene transition instead of an in-level respawn.
  save_reload      snapshot -> saveState(scratch) -> advance 120 -> loadState ->
                   snapshot; the reloaded snapshot must equal the original on
                   every typed field (save-state determinism contract).
  pause_freeze     stage02 anchor (busiest roster) -> inject Start -> advance 60
                   -> player position/health must be frozen while the frame
                   counter advances; release Start + Start again -> resume ->
                   position free again under held input.

Usage: python3 tools/phase2_lifecycle_oracle.py [--port 23472]
Output: analysis/phase2_lifecycle_oracle.json
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
    ("player_floor", 0x800A6548, "s32"),
    ("player_grounded", 0x800A6582, "u8"),
    ("health_true", 0x800A6594, "s16"),        # REAL health (0 = final hit, <0 = death)
    ("health_display_pulse", 0x800A7E2A, "s16"),  # HUD pulse counter, NOT health
    ("lives", 0x800A65A0, "u8"),
    ("grain", 0x800A65A1, "u8"),
    ("enemy_quota", 0x800A658E, "u8"),
    ("equipped_berry", 0x800A6597, "u8"),
    ("power_word", 0x800A6590, "u8"),
]
DEATH_Y = 400000   # well past the ~200000 death plane (Y positive = down)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)

    def rd(addr, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % addr, "length": n})["hex"])

    def snapshot() -> dict:
        snap = {}
        for name, addr, width in SNAPSHOT_FIELDS:
            raw = rd(addr, {"u8": 1, "s16": 2, "u32": 4, "s32": 4}[width])
            fmt = {"u8": "<B", "s16": "<h", "u32": "<I", "s32": "<i"}[width]
            snap[name] = struct.unpack(fmt, raw)[0]
        st = c.call("debugger.status", {})
        snap["frame"] = st.get("frame_number", st.get("frame"))
        return snap

    def load_anchor(sav="level01.sav"):
        for method in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(method, {})
            except Exception:
                pass
        r = c.call("emulator.loadState",
                   {"path": str(ROOT / sav), "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r
        c.call("emulator.clearControllerState", {"port": 0})

    def wr32(addr, value):
        c.call("debugger.writeU32", {"address": "0x%08x" % addr, "value": value & 0xFFFFFFFF})

    def sample_flow(max_steps=20, step=30):
        flow = []
        for _ in range(max_steps):
            c.call("emulator.advanceFrames", {"frames": step})
            c.call("debugger.pause", {})
            flow.append(snapshot())
        return flow

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    results = {}

    # ---- teleport recovery (negative finding, kept as evidence) --------------
    # A void teleport does NOT kill: the resolver restores footing next tick
    # (Y 400000 -> ~2738 observed). Pit death is a kill-REGION mechanic, not a
    # Y-plane one. Recorded as the warp-recovery oracle.
    load_anchor()
    before_tp = snapshot()
    wr32(0x800A6504, DEATH_Y)
    wr32(0x800A6514, DEATH_Y)
    c.call("emulator.advanceFrames", {"frames": 60})
    c.call("debugger.pause", {})
    after_tp = snapshot()
    results["teleport_recovery"] = {
        "anchor": "level01.sav", "perturbation": f"player_y (+mirror) := {DEATH_Y}",
        "before": before_tp, "after_60f": after_tp,
        "recovered_to_floor": abs(after_tp["player_y"]) < 100000,
        "no_death": after_tp["lives"] == before_tp["lives"],
    }
    print(f"[lifecycle] teleport_recovery: y {DEATH_Y} -> {after_tp['player_y']}, "
          f"lives unchanged={after_tp['lives'] == before_tp['lives']}")

    # ---- death by real contact damage + respawn -------------------------------
    # TRUE health = s16 @ 0x800A6594 (found 2026-07-12 via the mercy-leaf gate
    # `lh 0x6594; sltiu <4` at 0x8004999C and confirmed by the damage applier at
    # 0x8004A880: health -= 1; bgez -> survive, i.e. DEATH FIRES ONLY BELOW ZERO
    # (0 hp is alive/final hit). 0x800A7E2A is only the HUD pulse counter.
    # Method: set hp := 0, teleport onto the first chunk-31 actor of the stage-02
    # roster (pos + prev-tick mirrors), let a REAL contact hit apply -1.
    def contact_death(lives_val, label, anchor="level02.sav"):
        load_anchor(anchor)
        buf = rd(RECORDS := 0x8009FE04, 0x84)
        _rid, ax, ay, az = struct.unpack_from("<Iiii", buf, 0)
        c.call("debugger.writeU16", {"address": "0x%08x" % 0x800A6594, "value": 0})
        if lives_val is not None:
            c.call("debugger.writeU8", {"address": "0x%08x" % 0x800A65A0,
                                        "value": lives_val})
        for addr, val in ((0x800A6500, ax), (0x800A6510, ax),
                          (0x800A6504, ay), (0x800A6514, ay),
                          (0x800A6508, az), (0x800A6518, az)):
            wr32(addr, val)
        before = snapshot()
        flow = sample_flow(max_steps=25, step=60)
        return before, flow

    before, flow = contact_death(None, "death")
    respawn = next((s for s in flow if s["lives"] == before["lives"] - 1), None)
    results["death_contact_respawn"] = {
        "anchor": "level02.sav",
        "perturbation": "true health := 0; teleport onto actor record 0; real contact hit",
        "true_health_address": "0x800A6594 (s16); damage applier 0x8004A880 "
                               "(health-=1, death only if result < 0)",
        "on_hit_side_effects": "0x800A6530 := -1024 (knockback vel); "
                               "0x800A6582/6584/6586/659E zeroed",
        "before": before, "flow": flow,
        "death_observed": respawn is not None,
        "respawn_state": respawn,
        "respawn_health": respawn and respawn["health_true"],
        "respawn_at_spawn_point": respawn is not None and
            abs(respawn["player_x"] - (-16896)) < 2000,
        "laws": ["hp 0 is ALIVE (final hit); death fires when a damage event takes "
                 "hp below zero", "death->respawn ~120-180 frames",
                 "respawn restores hp to 4 (not full 7)",
                 "respawn returns to the level spawn point (lives -= 1)"],
    }
    print(f"[lifecycle] death_contact_respawn: death={respawn is not None}, "
          f"respawn={respawn}")

    # ---- game over: die again on the final life -------------------------------
    before_go, flow_go = contact_death(0, "game over")
    scenes = [s["scene_id"] for s in flow_go]
    died_on_final = next((s for s in flow_go if s["lives"] != 0), None)
    results["game_over_final_life"] = {
        "anchor": "level02.sav",
        "perturbation": "lives := 0 (final life); true health := 0; real contact hit",
        "before": before_go, "flow": flow_go,
        "scene_sequence_compressed": sorted(set(scenes)),
        "left_stage_scene": any(s != before_go["scene_id"] for s in scenes),
        "law": "lives 0 is PLAYABLE (the final life); the death on lives 0 decides "
               "game over",
        "post_final_death_state": died_on_final,
    }
    print(f"[lifecycle] game_over_final_life: scenes {sorted(set(scenes))}, "
          f"post-final-death {died_on_final}")

    # ---- save/reload determinism ---------------------------------------------
    load_anchor()
    original = snapshot()
    scratch = "/tmp/dsrepro-phase2/phase2_lifecycle_scratch.sav"
    c.call("emulator.saveState", {"path": scratch})
    c.call("emulator.advanceFrames", {"frames": 120})
    c.call("debugger.pause", {})
    drifted = snapshot()
    r = c.call("emulator.loadState", {"path": scratch, "pause_after_load": True})
    assert r.get("loaded"), r
    reloaded = snapshot()
    fields = [n for n, _, _ in SNAPSHOT_FIELDS]
    equal = [f for f in fields if original[f] == reloaded[f]]
    results["save_reload"] = {
        "anchor": "level01.sav", "scratch_state": scratch,
        "original": original, "after_120_frames": drifted, "reloaded": reloaded,
        "fields_equal_after_reload": equal,
        "deterministic": len(equal) == len(fields),
    }
    print(f"[lifecycle] save_reload: {len(equal)}/{len(fields)} fields equal after reload")

    # ---- pause freeze / resume ------------------------------------------------
    load_anchor("level02.sav")
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
    c.call("emulator.advanceFrames", {"frames": 3})
    c.call("emulator.clearControllerState", {"port": 0})
    c.call("debugger.pause", {})
    paused_1 = snapshot()
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    c.call("emulator.advanceFrames", {"frames": 60})
    c.call("debugger.pause", {})
    paused_2 = snapshot()
    c.call("emulator.clearControllerState", {"port": 0})
    frozen = [f for f in ("player_x", "player_y", "player_z", "health_true")
              if paused_1[f] == paused_2[f]]
    # unpause and prove motion returns
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
    c.call("emulator.advanceFrames", {"frames": 3})
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    c.call("emulator.advanceFrames", {"frames": 60})
    c.call("debugger.pause", {})
    resumed = snapshot()
    c.call("emulator.clearControllerState", {"port": 0})
    moved = (abs(resumed["player_x"] - paused_2["player_x"])
             + abs(resumed["player_z"] - paused_2["player_z"]))
    results["pause_freeze"] = {
        "anchor": "level02.sav",
        "paused_at": paused_1, "after_60_held_frames": paused_2,
        "player_fields_frozen_under_pause": frozen,
        "frames_advanced_under_pause": paused_2["frame"] - paused_1["frame"],
        "resumed": resumed, "displacement_after_resume": moved,
        "resume_restores_motion": moved > 500,
    }
    print(f"[lifecycle] pause: frozen={frozen}, resume displacement={moved}")

    doc = {
        "_comment": "Phase-2 lifecycle oracle: induced death/respawn, game-over, "
                    "save/reload determinism, pause freeze/resume — bounded pristine-"
                    "anchor experiments, every mutation rolled back by reload. "
                    "Regenerate: tools/phase2_lifecycle_oracle.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "experiments": results,
    }
    out = ROOT / "analysis" / "phase2_lifecycle_oracle.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[lifecycle] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
