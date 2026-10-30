#!/usr/bin/env python3
"""Phase-2 per-action oracle: typed state deltas around native action instances.

For each action class, replays pristine from-boot movies (repro config) to
sampled in-stage action frames from analysis/phase2_action_windows.json and
captures typed snapshots at event-15 / event+2 / event+12 / event+32 — the
native positive controls for the manual-control matrix.

Two probes the recorded runs never exercise are synthesized at the stage01
anchor with injected input:
  * slow_walk — displacement over 60 held frames: R2+up vs up alone;
  * circle_negative — Circle held 30 frames; expected null state delta.

Requires the REPRO instance (movies replay 1:1 only there):
    tools/launch_repro_playback.sh --config-dir /tmp/dsrepro-phase2 --port 23472 \
        --token debugger-1000 --disc "<pristine>.cue"

Usage: python3 tools/phase2_action_oracle.py [--port 23472]
Output: analysis/phase2_action_oracle.json
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
    ("health", 0x800A7E2A, "s16"),
    ("lives", 0x800A65A0, "u8"),
    ("grain", 0x800A65A1, "u8"),
    ("enemy_quota", 0x800A658E, "u8"),
    ("equipped_berry", 0x800A6597, "u8"),
    ("power_word", 0x800A6590, "u8"),
]
SAMPLE_OFFSETS = (-15, 2, 12, 32)
PER_CLASS_LIMIT = 6

# movies chosen for class variety (kicks + double-taps live in the 100% runs)
SAMPLED_MOVIES = [
    "movies/go_to_end/LEVEL00-Training.movie.json",
    "movies/go_to_end/LEVEL03.movie.json",
    "movies/go_to_end/LEVEL15.movie.json",
    "movies/100% Runs/LEVEL01.movie.json",
]
CLASSES = ("jump", "double_tap_cross", "square_action", "kick",
           "triangle_action", "camera_look", "camera_lock", "status")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(900)

    def rd(addr: int, n: int) -> bytes:
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % addr, "length": n})["hex"])

    def snapshot() -> dict:
        snap = {}
        for name, addr, width in SNAPSHOT_FIELDS:
            raw = rd(addr, {"u8": 1, "s16": 2, "u32": 4, "s32": 4}[width])
            fmt = {"u8": "<B", "s16": "<h", "u32": "<I", "s32": "<i"}[width]
            snap[name] = struct.unpack(fmt, raw)[0]
        return snap

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    windows = json.loads((ROOT / "analysis" / "phase2_action_windows.json").read_text())

    # ---- movie-sampled native action instances ------------------------------
    samples: dict = {k: [] for k in CLASSES}
    for rel in SAMPLED_MOVIES:
        mv = windows["movies"][rel]
        # collect this movie's chosen events in ascending frame order
        chosen = []
        for cls in CLASSES:
            have = len(samples[cls])
            if have >= PER_CLASS_LIMIT:
                continue
            ev = mv["events"][cls]
            # movies without a completion timeline (100% Runs) fall back to a
            # post-menu cutoff: every go_to_end run entered its stage by ~6500
            frames = ev.get("in_stage_frames")
            if frames is None:
                frames = [f for f in ev.get("frames", []) if f >= 6500]
            for f in frames[:max(0, PER_CLASS_LIMIT - have)]:
                chosen.append((f, cls))
        if not chosen:
            continue
        chosen.sort()
        for method in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(method, {})
            except Exception:
                pass
        c.call("movie.load", {"path": str(ROOT / rel)})
        started = c.call("movie.startPlayback", {"load_start_state": True})
        assert started.get("playing") and started.get("reproducible"), rel
        total = mv["frames"]
        for event_frame, cls in chosen:
            series = {}
            skip = False
            for off in SAMPLE_OFFSETS:
                target = event_frame + off
                st = c.call("debugger.status", {})
                cur = st.get("frame_number", st.get("frame"))
                if target < cur:      # ordering collision with a previous event
                    skip = True
                    break
                c.call("movie.advanceToFrame",
                       {"frame": target, "max_frames": total + 700}, timeout=900)
                series[f"{off:+d}"] = snapshot()
            if not skip:
                samples[cls].append({"movie": rel, "event_frame": event_frame,
                                     "snapshots": series})
        print(f"[action_oracle] {rel}: sampled "
              f"{sum(1 for s in samples.values() for e in s if e['movie'] == rel)} events")

    # ---- synthetic probes at the stage01 anchor -----------------------------
    def load_anchor():
        r = c.call("emulator.loadState",
                   {"path": str(ROOT / "level01.sav"), "pause_after_load": True})
        assert r.get("loaded"), r

    def held_displacement(buttons: dict, frames: int) -> dict:
        load_anchor()
        before = snapshot()
        c.call("emulator.setControllerState", {"port": 0, "buttons": buttons})
        c.call("emulator.advanceFrames", {"frames": frames})
        c.call("debugger.pause", {})
        after = snapshot()
        c.call("emulator.clearControllerState", {"port": 0})
        return {"buttons": buttons, "frames": frames, "before": before, "after": after,
                "dx": after["player_x"] - before["player_x"],
                "dz": after["player_z"] - before["player_z"]}

    run = held_displacement({"up": True}, 60)
    walk = held_displacement({"up": True, "r2": True}, 60)
    circle = held_displacement({"circle": True}, 30)
    circle["null_delta_fields"] = sorted(
        k for k in circle["before"]
        if circle["before"][k] == circle["after"][k])
    synthetic = {
        "slow_walk": {
            "run_60f": run, "walk_60f": walk,
            "displacement_ratio_x": (walk["dx"] / run["dx"]) if run["dx"] else None,
            "displacement_ratio_z": (walk["dz"] / run["dz"]) if run["dz"] else None,
        },
        "circle_negative": circle,
    }

    doc = {
        "_comment": "Phase-2 per-action oracle: typed snapshots at -15/+2/+12/+32 "
                    "frames around native in-stage action instances (replayed from "
                    "the pristine from-boot movies under the repro config), plus "
                    "synthetic slow-walk and circle negative-control probes at the "
                    "stage01 anchor. Regenerate: tools/phase2_action_oracle.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "sample_offsets": list(SAMPLE_OFFSETS),
        "per_class_limit": PER_CLASS_LIMIT,
        "movie_samples": samples,
        "synthetic_probes": synthetic,
    }
    out = ROOT / "analysis" / "phase2_action_oracle.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    counts = {k: len(v) for k, v in samples.items()}
    print(f"[action_oracle] wrote {out}: samples={counts}")
    print(f"  slow-walk displacement ratio x/z: "
          f"{synthetic['slow_walk']['displacement_ratio_x']}, "
          f"{synthetic['slow_walk']['displacement_ratio_z']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
