#!/usr/bin/env python3
"""Phase-2 action-window extraction: mine the pristine from-boot movies' input
streams for per-action frame windows (OFFLINE — no emulator).

Every recorded frame carries the full pad state, so rising edges and hold
patterns identify where each manual control was exercised. Combined with each
movie's scene timeline (analysis/phase2_completion_oracle.json), every event is
attributed to its stage and to in-stage vs menu context. The output is the work
list for the per-action live oracle (tools/phase2_action_oracle.py): for each
action class, WHERE in which movie it can be observed natively.

Action classes (recognizers over pad state):
  jump              cross rising edge (no recent cross)
  double_tap_cross  two cross edges <= 20 frames apart (abdomen bounce / slide arm)
  square_action     square edge, no L2/R2 held (throw / pickup / drop / handstand)
  kick              square edge while L2 or R2 held
  triangle_action   triangle edge (seed color change)
  slow_walk         L2 or R2 held >= 30 frames with movement input, no square
  camera_look       L1 edge          camera_lock  R1 edge
  pause             start edge       status       select edge
  circle_negative   circle edge (manual assigns no action — negative control)

Usage: python3 tools/phase2_action_windows.py
Output: analysis/phase2_action_windows.json
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVIE_DIRS = ["movies/go_to_end", "movies/100% Runs"]
DOUBLE_TAP_MAX = 20
WALK_MIN_HOLD = 30


def movement_active(pad: dict) -> bool:
    if any(pad.get(d) for d in ("up", "down", "left", "right")):
        return True
    return abs(pad.get("lx", 128) - 128) > 24 or abs(pad.get("ly", 128) - 128) > 24


def extract(frames: list) -> dict:
    events = {k: [] for k in ("jump", "double_tap_cross", "square_action", "kick",
                              "triangle_action", "slow_walk", "camera_look",
                              "camera_lock", "pause", "status", "circle_negative")}
    prev: dict = {}
    last_cross_edge = None
    walk_start = None
    for entry in frames:
        i = entry["frame"]
        pad = entry.get("ports", {}).get("0", {}) or {}
        def edge(btn):
            return pad.get(btn) and not prev.get(btn)
        shoulder_held = pad.get("l2") or pad.get("r2")
        if edge("cross"):
            events["jump"].append(i)
            if last_cross_edge is not None and i - last_cross_edge <= DOUBLE_TAP_MAX:
                events["double_tap_cross"].append(last_cross_edge)
            last_cross_edge = i
        if edge("square"):
            events["kick" if shoulder_held else "square_action"].append(i)
        if edge("triangle"):
            events["triangle_action"].append(i)
        if edge("l1"):
            events["camera_look"].append(i)
        if edge("r1"):
            events["camera_lock"].append(i)
        if edge("start"):
            events["pause"].append(i)
        if edge("select"):
            events["status"].append(i)
        if edge("circle"):
            events["circle_negative"].append(i)
        if shoulder_held and movement_active(pad) and not pad.get("square"):
            if walk_start is None:
                walk_start = i
        else:
            if walk_start is not None and i - walk_start >= WALK_MIN_HOLD:
                events["slow_walk"].append(walk_start)
            walk_start = None
        prev = pad
    return events


def in_stage(frame: int, timeline: list, target_scene: int) -> bool:
    for seg in timeline:
        if seg["scene"] == target_scene and seg["first"] <= frame <= seg["last"]:
            return True
    return False


def main() -> int:
    completion = json.loads(
        (ROOT / "analysis" / "phase2_completion_oracle.json").read_text())
    by_movie = {st["movie"]: (lbl, st) for lbl, st in completion["stages"].items()}

    movies = {}
    totals: dict = {}
    for d in MOVIE_DIRS:
        for path in sorted((ROOT / d).glob("*.movie.json")):
            rel = str(path.relative_to(ROOT))
            doc = json.loads(path.read_text())
            events = extract(doc["frames"])
            stage_label, stage = by_movie.get(rel, (None, None))
            entry = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "frames": len(doc["frames"]),
                "stage": stage_label,
                "events": {},
            }
            for action, hits in events.items():
                rec = {"count": len(hits), "frames": hits[:400]}
                if stage is not None:
                    tl, scene = stage["scene_timeline"], stage["target_scene"]
                    rec["in_stage_frames"] = [f for f in hits if in_stage(f, tl, scene)][:400]
                    rec["in_stage_count"] = len([f for f in hits if in_stage(f, tl, scene)])
                entry["events"][action] = rec
                key = (action, "in_stage" if stage is not None else "total")
                totals.setdefault(action, {"total": 0, "in_stage": 0})
                totals[action]["total"] += len(hits)
                if stage is not None:
                    totals[action]["in_stage"] += rec.get("in_stage_count", 0)
            movies[rel] = entry
            print(f"[actions] {rel}: " + " ".join(
                f"{a}={e['count']}" for a, e in entry["events"].items() if e["count"]))

    doc = {
        "_comment": "Phase-2 per-action frame windows mined OFFLINE from the pristine "
                    "from-boot movies' recorded pad streams; in_stage_* uses the "
                    "completion oracle's scene timelines. Work list for "
                    "tools/phase2_action_oracle.py. Regenerate: "
                    "tools/phase2_action_windows.py.",
        "generated": date.today().isoformat(),
        "recognizers": {"double_tap_max_frames": DOUBLE_TAP_MAX,
                        "walk_min_hold_frames": WALK_MIN_HOLD},
        "totals": totals,
        "movies": movies,
    }
    out = ROOT / "analysis" / "phase2_action_windows.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[actions] wrote {out}")
    print("[actions] totals (in-stage/total):")
    for action, t in sorted(totals.items()):
        print(f"  {action:18s} {t['in_stage']:5d}/{t['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
