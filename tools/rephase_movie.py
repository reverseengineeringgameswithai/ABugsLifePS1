#!/usr/bin/env python3
"""Re-phase a DuckStation input movie by shifting its input stream N frames.

WHY THIS EXISTS
---------------
A save-state-anchored movie can replay one frame out of phase with how it was
recorded, and the result is a silent desync: `reproducible` still reports true,
no error is raised, and the run simply drifts off-script.

The cause is in the fork's own input_movie.cpp. Playback compensates for the arm
phase only when

    GetFrameNumber() == s_arm_frame && s_mode == Mode::Playing

i.e. only when arming happened inside a *running* FrameDone. The comment at
input_movie.cpp:33 spells out the other case: "When armed while paused, the first
callback belongs to the next frame." Recording deliberately falls through that
branch ("omitting it shifts the entire movie one frame early on replay").

So record-while-running + replay-while-paused (or the reverse) is off by exactly
one frame. The emulator already knows how to fix this -- `s_play_legacy_delay_pending`
inserts one neutral frame -- but it keys that on the movie `version`, not on the
arm phase, so a current-version movie recorded in the other phase never gets it.

FIXED IN THE FORK (2026-08-01, movie format v4): StartRecording now records the
arm phase as `armed_while_paused`, and StartPlayback inserts the one neutral frame
itself when it is set. New recordings are self-correcting.

So PREFER `--tag-arm-phase` for an existing broken movie: it sets that flag and
leaves the frame array untouched, which is self-describing and survives re-edits.
`--shift` remains for pre-v4 builds and for arbitrary offsets.

USAGE
    tools/rephase_movie.py IN.movie.json OUT.movie.json --tag-arm-phase
    tools/rephase_movie.py IN.movie.json OUT.movie.json --shift +1

  --tag-arm-phase  mark the movie as recorded while paused; the emulator then
                   applies the one-frame delay (equivalent to --shift +1)
  --shift +N   apply inputs N frames LATER (prepend N neutral samples)
  --shift -N   apply inputs N frames EARLIER (drop the first N samples)

DO NOT blanket-apply either mode to the movie corpus. Most existing movies replay
correctly as they are (the Phase-2 oracle: 701 comparisons, 0 mismatch); "fixing"
those breaks them. Correct only a movie you have shown to be one frame early.

The start state, ports, serial and initial_frame are preserved untouched; only
the frame array and `notes` change. Verified empirically on
movies/b06_desync_test.movie.json, where +1 reproduced the recorded run.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def neutral_like(sample):
    """A released-input sample with the same shape as a recorded one."""
    out = copy.deepcopy(sample)
    for port in out:
        if isinstance(port, dict):
            for key, value in port.items():
                if isinstance(value, int):
                    port[key] = 0
        elif isinstance(port, list):
            for i in range(len(port)):
                port[i] = 0
    return out


def tag_arm_phase(doc: dict) -> dict:
    """Mark the movie as recorded while paused; frames are left exactly as they are.

    A v4+ build reads this and inserts one neutral frame before the first sample,
    which is the same correction --shift +1 makes by rewriting the stream. The flag
    is honoured on any version that carries it, so a v3 file can opt in without
    being rewritten.
    """
    if doc.get("armed_while_paused"):
        raise SystemExit("already tagged armed_while_paused")
    out = copy.deepcopy(doc)
    out["armed_while_paused"] = True
    prior = str(doc.get("notes") or "").strip()
    note = ("Tagged armed_while_paused=true by tools/rephase_movie.py: this recording was "
            "armed while the system was paused, so its first post-state frame was never "
            "recorded. A v4+ build inserts the missing neutral frame on playback. "
            "Frame array unchanged.")
    out["notes"] = f"{prior} | {note}" if prior else note
    return out


def rephase(doc: dict, shift: int) -> dict:
    frames = doc.get("frames")
    if not isinstance(frames, list) or not frames:
        raise SystemExit("movie has no frames")
    if shift > 0:
        new_frames = [neutral_like(frames[0]) for _ in range(shift)] + frames
    elif shift < 0:
        if -shift >= len(frames):
            raise SystemExit(f"cannot drop {-shift} of {len(frames)} frames")
        new_frames = frames[-shift:]
    else:
        new_frames = list(frames)
    out = copy.deepcopy(doc)
    out["frames"] = new_frames
    prior = str(doc.get("notes") or "").strip()
    note = (f"Re-phased {shift:+d} frame(s) by tools/rephase_movie.py to correct an "
            f"arm-phase desync (see input_movie.cpp:324 and the comment at :33). "
            f"Input stream only; start state and metadata unchanged.")
    out["notes"] = f"{prior} | {note}" if prior else note
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", type=Path)
    ap.add_argument("dest", type=Path)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--shift", type=int,
                      help="+N applies inputs N frames later; -N applies them earlier")
    mode.add_argument("--tag-arm-phase", action="store_true",
                      help="set armed_while_paused so the emulator applies the delay (preferred)")
    args = ap.parse_args()

    if args.dest.exists():
        raise SystemExit(f"refusing to overwrite {args.dest}; movies are never overwritten")
    doc = json.loads(args.source.read_text(encoding="utf-8"))
    if args.tag_arm_phase:
        out = tag_arm_phase(doc)
        args.dest.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
        print(f"{args.source.name} -> {args.dest.name}: armed_while_paused=true "
              f"({len(out['frames'])} frames unchanged)")
    else:
        out = rephase(doc, args.shift)
        args.dest.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
        print(f"{args.source.name}: {len(doc['frames'])} frames "
              f"-> {args.dest.name}: {len(out['frames'])} frames (shift {args.shift:+d})")
    state = (doc.get("start_state") or {}).get("path")
    if state:
        print(f"  start state unchanged: {Path(str(state)).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
