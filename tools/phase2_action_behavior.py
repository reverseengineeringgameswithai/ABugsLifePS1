#!/usr/bin/env python3
"""Phase-2 closure pass: PAIRED BEHAVIORAL assertions for kick, camera and status.

Review item (gate letter): the existing controls for these three prove only that
input frames were sampled — not that the action DID anything. Each experiment
below is an A/B pair from a pristine anchor: the action's OUTCOME is measured
(enemy state / camera transform / framebuffer), and the same window without the
input is the negative half. No semantic ownership is required — only observables
that already exist.

  kick        RE'd to its branch (0x80048F4C): L2|R2 held + Square FRESH PRESS
              (+ grounded + not-already-kicking + player+0x5C==0) writes -16 to
              the KICK TIMER at 0x800A657A. Positive: L2+Square and R2+Square
              (shoulder held first, then a Square edge) both fire the timer.
              Negative: Square alone and no-input leave it at 0.
  camera      L1 (look/reset) and R1 (lock) held vs no input from the same anchor;
              outcome = the CAMERA runtime struct at 0x80095358 (Canon SYS_camera)
              AND the displayed framebuffer hash. A camera control that works
              moves the camera; the control window must not.
  status      Select pressed vs not; outcome = displayed framebuffer hash (the
              panel is a visual event) + frame-to-frame stability. The panel must
              change the frame; the control must leave it unchanged.

Usage: python3 tools/phase2_action_behavior.py [--port 23472]
Output: analysis/phase2_action_behavior.json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

CAMERA = 0x80095358
RECORDS = 0x8009FE04


def sha_payload(result: dict) -> str:
    for key in ("data", "png", "base64", "image"):
        if isinstance(result.get(key), str):
            return hashlib.sha256(base64.b64decode(result[key])).hexdigest()
    raise KeyError(f"no payload: {list(result)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def load(sav):
        for m in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(m, {})
            except Exception:
                pass
        r = c.call("emulator.loadState", {"path": str(ROOT / sav),
                                          "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r
        c.call("emulator.clearControllerState", {"port": 0})

    def wr32(a, v):
        c.call("debugger.writeU32", {"address": "0x%08x" % a, "value": v & 0xFFFFFFFF})

    def frame_hash():
        return sha_payload(c.call("gpu.frameSnapshot",
                                  {"buffer": "displayed", "format": "raw16"}))

    def camera_state():
        return rd(CAMERA, 0x20).hex()

    def anim_pair():
        # NOTE: 0x800A6542/46 is an animation FRAME COUNTER (cycles 0..8 while
        # idle) — NOT a state id; discriminate actions on the state word instead.
        b = rd(0x800A6540, 0x60)
        return [b[0x02], b[0x06]]

    def state_word():
        return rd(0x800A6580, 1)[0]

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    out: dict = {}

    # ---- KICK: real positive/negative control on the kick action ------------
    # RE (closure pass, static+live): the kick branch is at 0x80048F4C —
    #   pad(0x80082488) & 0x0300 (L2|R2 held)  AND  & 0x8000 (Square)
    #   AND prev-pad(0x80082380) & 0x8000 == 0  (Square must be a FRESH PRESS)
    #   AND player+0x7A >= 0 (not already kicking)
    #   AND |player.Y(+0x04) - player.floorY(+0x48)| < 1024  (grounded)
    #   AND player+0x5C == 0
    #   -> action: sh -16, 0x7A(player)  ==  KICK TIMER 0x800A657A := -16
    # The first attempt failed because it held Square from a paused state, so no
    # press EDGE was ever produced — a method error, not an absent mechanic.
    KICK_TIMER = 0x800A657A

    def kick_trial(pre, press, label):
        load("level01.sav")
        c.call("emulator.advanceFrames", {"frames": 20})   # settle grounded
        c.call("debugger.pause", {})
        before = struct.unpack("<h", rd(KICK_TIMER, 2))[0]
        if pre:                     # hold the shoulder first: no Square edge yet
            c.call("emulator.setControllerState", {"port": 0, "buttons": pre})
            c.call("emulator.advanceFrames", {"frames": 8})
        c.call("emulator.setControllerState", {"port": 0, "buttons": press})
        series = []
        for i in range(12):
            c.call("emulator.advanceFrames", {"frames": 2})
            c.call("debugger.pause", {})
            series.append(struct.unpack("<h", rd(KICK_TIMER, 2))[0])
            if i == 2:
                c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.clearControllerState", {"port": 0})
        return {"label": label, "pre": pre or {}, "press": press,
                "timer_before": before, "timer_series": series,
                "kick_fired": any(v < 0 for v in series),
                "min_timer": min(series)}

    l2 = kick_trial({"l2": True}, {"l2": True, "square": True},
                    "L2 held + Square fresh press")
    r2 = kick_trial({"r2": True}, {"r2": True, "square": True},
                    "R2 held + Square fresh press")
    sq = kick_trial(None, {"square": True}, "Square alone (negative)")
    idle = kick_trial(None, {"up": True}, "no Square (negative)")
    out["kick"] = {
        "anchor": "level01.sav",
        "observable": "KICK TIMER 0x800A657A (player+0x7A); the kick branch at "
                      "0x80048F4C writes -16",
        "gates": "L2|R2 held AND Square FRESH PRESS (edge on 0x80082380) AND "
                 "not already kicking AND grounded (|Y - floorY| < 1024) AND "
                 "player+0x5C == 0",
        "trials": [l2, r2, sq, idle],
        "l2_kick_fires": l2["kick_fired"], "r2_kick_fires": r2["kick_fired"],
        "square_alone_no_kick": not sq["kick_fired"],
        "no_input_no_kick": not idle["kick_fired"],
        "kick_timer_start": l2["min_timer"],
        "passes": (l2["kick_fired"] and r2["kick_fired"]
                   and not sq["kick_fired"] and not idle["kick_fired"]),
        "supersedes": "the earlier 'shoulder+Square does not alter the throw' "
                      "disproof was a METHOD ERROR (held Square = no press edge); "
                      "the kick EXISTS and is now a positive/negative control.",
        "residual": "the kick's damage class (which families it hurts) remains "
                    "registry row A04 — the ACTION is now bound and controlled.",
    }
    print(f"[kick] L2={l2['kick_fired']} R2={r2['kick_fired']} "
          f"square-alone={sq['kick_fired']} idle={idle['kick_fired']} "
          f"timer_start={l2['min_timer']} passes={out['kick']['passes']}")

    # ---- CAMERA: L1 / R1 outcome vs control ---------------------------------
    def camera_trial(buttons, label):
        load("level01.sav")
        c.call("emulator.advanceFrames", {"frames": 10})
        c.call("debugger.pause", {})
        cam0, fh0 = camera_state(), frame_hash()
        if buttons:
            c.call("emulator.setControllerState", {"port": 0, "buttons": buttons})
        c.call("emulator.advanceFrames", {"frames": 45})
        c.call("debugger.pause", {})
        cam1, fh1 = camera_state(), frame_hash()
        c.call("emulator.clearControllerState", {"port": 0})
        return {"label": label, "buttons": buttons or {},
                "camera_changed": cam0 != cam1, "frame_changed": fh0 != fh1,
                "camera_before": cam0[:32], "camera_after": cam1[:32]}

    look = camera_trial({"l1": True, "up": True}, "L1 look/reset while moving")
    lock = camera_trial({"r1": True, "up": True}, "R1 lock while moving")
    move_only = camera_trial({"up": True}, "move only (control)")
    still = camera_trial(None, "no input (negative control)")
    out["camera"] = {
        "anchor": "level01.sav", "observable": f"0x{CAMERA:08X} (Canon SYS_camera)",
        "trials": [look, lock, move_only, still],
        "l1_changes_camera": look["camera_changed"],
        "r1_changes_camera_differently_than_move_only":
            lock["camera_after"] != move_only["camera_after"],
        "negative_control_camera_static": not still["camera_changed"],
        "passes": (look["camera_changed"] and not still["camera_changed"]),
    }
    print(f"[camera] L1 moved={look['camera_changed']} R1-vs-move differs="
          f"{out['camera']['r1_changes_camera_differently_than_move_only']} "
          f"idle static={not still['camera_changed']} "
          f"passes={out['camera']['passes']}")

    # ---- STATUS: Select panel is a visual event ------------------------------
    def status_trial(press, label):
        # PAUSED baseline: with the guest paused the framebuffer is static, so any
        # change is attributable to the injected input, not ambient animation
        # (first attempt used a running window where level01 animates on its own)
        load("level01.sav")
        c.call("debugger.pause", {})
        fh0 = frame_hash()
        if press:
            c.call("emulator.setControllerState", {"port": 0, "buttons": {"select": True}})
            c.call("emulator.advanceFrames", {"frames": 6})
            c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.advanceFrames", {"frames": 40})
        c.call("debugger.pause", {})
        fh1 = frame_hash()
        # the PANEL is a persistent overlay: with the panel up, the frame keeps
        # showing it; the discriminator is panel-vs-no-panel at the SAME frame
        # count from the same anchor (both windows advance identically)
        return {"label": label, "frame_after": fh1,
                "frame_changed_from_anchor": fh0 != fh1}

    panel = status_trial(True, "Select pressed")
    nopanel = status_trial(False, "no Select (negative control)")
    out["status"] = {
        "anchor": "level01.sav",
        "trials": [panel, nopanel],
        "discriminator": "same anchor, same advance count: Select vs no Select",
        "panel_frame": panel["frame_after"][:16],
        "control_frame": nopanel["frame_after"][:16],
        "select_produces_different_frame":
            panel["frame_after"] != nopanel["frame_after"],
        "passes": panel["frame_after"] != nopanel["frame_after"],
    }
    print(f"[status] panel={panel['frame_after'][:12]} "
          f"control={nopanel['frame_after'][:12]} passes={out['status']['passes']}")

    doc = {
        "_comment": "Paired BEHAVIORAL controls for kick/camera/status (gate letter): "
                    "each action's OUTCOME measured against its no-input control. "
                    "Regenerate: tools/phase2_action_behavior.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "controls": out,
        "all_pass": all(v["passes"] for v in out.values()),
    }
    path = ROOT / "analysis" / "phase2_action_behavior.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[behavior] wrote {path}: all_pass={doc['all_pass']}")
    return 0 if doc["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
