#!/usr/bin/env python3
"""Phase-2 completion oracle: replay every go_to_end from-boot movie and record
the per-stage scene timeline + typed end-of-stage snapshots.

The movies in movies/go_to_end/ are FROM-BOOT (embedded from_boot start anchor)
per-stage playthroughs on the pristine image. Under the determinism-matched repro
config (tools/launch_repro_playback.sh, seeded memory card) each replays 1:1.
For every movie this tool records:

  * the scene timeline (sampled every SAMPLE frames): boot/menus -> target stage
    scene -> exit transition — the objective start/completion evidence;
  * a typed snapshot at the last sampled in-stage frame (the completion-adjacent
    anchor; reproducible from movie + frame number, no extra save state needed);
  * the final movie-end state and whether the stage scene was exited (completion
    transition observed) or still active at movie end;
  * pristine-replay acceptance for the fixture-audit caveat (a movie header can
    claim a serial, but only a pristine replay proves the fixture).

Stage scene ids come from analysis/phase2_stage_baseline.json.

Requires the REPRO instance (not the plain debugger launcher — from-boot movies
replay 1:1 only with the recording-matched config):
    tools/launch_repro_playback.sh --config-dir /tmp/dsrepro-phase2 --port 23472 \
        --token debugger-1000 --disc "<pristine>.cue"

Usage: python3 tools/phase2_completion_oracle.py [--port 23472] [--only LEVEL03]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

SAMPLE = 500          # frames between scene samples
SNAPSHOT_FIELDS = [   # keep in sync with tools/phase2_oracle.py
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

# movie file -> baseline stage label (movie names use the stage numbering)
MOVIES = {
    "LEVEL00-Training": "training",
    "LEVEL01": "stage01_anthill", "LEVEL02": "stage02_tunnels",
    "LEVEL03": "stage03_council_chamber", "LEVEL04": "stage04_cliffside_canyon",
    "LEVEL05": "stage05_riverbed_run", "LEVEL06": "stage06_birdnest",
    "LEVEL07": "stage07_city_entrance", "LEVEL08": "stage08_city_square",
    "LEVEL09": "stage09_bug_bar", "LEVEL10": "stage10_clover_forest",
    "LEVEL11": "stage11_the_tree", "LEVEL12": "stage12_battle_arena",
    "LEVEL13": "stage13_anthill_two", "LEVEL14": "stage14_riverbed_flight",
    "LEVEL15": "stage15_canyon_showdown",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--only", help="replay a single movie stem (e.g. LEVEL03)")
    ap.add_argument("--out", default=str(ROOT / "analysis" / "phase2_completion_oracle.json"))
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
    baseline = json.loads((ROOT / "analysis" / "phase2_stage_baseline.json").read_text())
    stage_scene = {lbl: st["anchor"]["scene_id"]
                   for lbl, st in baseline["stages"].items() if st["role"] == "identity"}
    # the training movie start save anchors pre-scene-load; in-level Training is 17
    stage_scene["training"] = 17

    results = {}
    for stem, label in MOVIES.items():
        if args.only and stem != args.only:
            continue
        path = ROOT / "movies" / "go_to_end" / f"{stem}.movie.json"
        target_scene = stage_scene[label]
        loaded = c.call("movie.load", {"path": str(path)})
        frames = loaded["frame_count"]
        started = c.call("movie.startPlayback", {"load_start_state": True})
        if not started.get("playing") or not started.get("reproducible"):
            results[label] = {"movie": str(path.relative_to(ROOT)),
                              "error": f"playback not reproducible: {started}"}
            continue
        timeline = []      # compressed [(first_frame, last_frame, scene), ...]
        last_in_stage = None
        cur = 0
        while cur < frames:
            cur = min(cur + SAMPLE, frames)
            c.call("movie.advanceToFrame", {"frame": cur, "max_frames": frames + 700},
                   timeout=900)
            sc = snapshot()
            if timeline and timeline[-1][2] == sc["scene_id"]:
                timeline[-1][1] = cur
            else:
                timeline.append([cur, cur, sc["scene_id"]])
            if sc["scene_id"] == target_scene:
                last_in_stage = {"frame": cur, "snapshot": sc}
        end = snapshot()
        entered = next((seg[0] for seg in timeline if seg[2] == target_scene), None)
        exited = (end["scene_id"] != target_scene)
        results[label] = {
            "movie": str(path.relative_to(ROOT)),
            "movie_sha256": sha256_file(path),
            "frames": frames,
            "target_scene": target_scene,
            "pristine_replay_accepted": True,
            "scene_timeline": [{"first": a, "last": b, "scene": s} for a, b, s in timeline],
            "entered_stage_frame": entered,
            "stage_exited_by_movie_end": exited,
            "last_in_stage": last_in_stage,
            "movie_end_snapshot": end,
        }
        print(f"[completion] {label}: {frames}f, entered@{entered}, "
              f"exited={exited}, end_scene={end['scene_id']}")

    doc = {
        "_comment": "Phase-2 completion oracle from the go_to_end from-boot movies "
                    "(pristine replay under the repro config). last_in_stage is the "
                    "completion-adjacent anchor, reproducible from movie + frame "
                    "number. Regenerate: tools/phase2_completion_oracle.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "method": {"sample_frames": SAMPLE,
                   "launcher": "tools/launch_repro_playback.sh (determinism-matched, card-seeded)",
                   "acceptance": "movie fixture accepted only via this pristine replay"},
        "stages": results,
    }
    out = Path(args.out)
    if args.only and out.exists():
        prior = json.loads(out.read_text())
        prior["stages"].update(results)
        prior["generated"] = doc["generated"]
        doc = prior
    out.write_text(json.dumps(doc, indent=1) + "\n")
    entered = sum(1 for r in results.values() if r.get("entered_stage_frame") is not None)
    print(f"[completion] wrote {out}: {entered}/{len(results)} movies reached their stage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
