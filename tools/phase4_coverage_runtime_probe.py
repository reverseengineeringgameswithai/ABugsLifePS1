#!/usr/bin/env python3
"""Does a recorded movie EXECUTE any of the code the static census still misses?

WHY
---
tools/repair_function_coverage.c took the resident function census from 90.1% to
92.8% by walking each function's CFG. What it cannot reach is code entered only
through a DATA-held dispatch table -- 9,940 bytes in 8 gaps, majority non-zero.
Static analysis is stuck there because the table's contents are data.

At runtime the dispatch RESOLVES. So a trace can do what the walk cannot: prove a
gap is live code by catching it executing, and hand back a concrete PC.

WHAT IT CANNOT DO, stated up front: silence proves nothing. A gap that never
fires may be an error path, a debug routine, or dead library code -- or simply
not exercised by this movie. A hit is evidence; a miss is not.

METHOD
------
`execTrace.addRangeWatch` covers a whole address range in ONE watch, so every
uncovered gap is watched in full -- no sampling, no floor. (A first version used
`execTrace.addWatch`, which takes a single PC and caps at 64 watches, and had to
spread sample points across the gaps; a short routine between two points would
have been missed entirely. The range API removes that limitation.)

A range watch over a known-hot function is the POSITIVE CONTROL. Without it a
clean zero is uninterpretable -- the exact failure that cost a full campaign run
earlier in this project, and which the first run of THIS probe reproduced.

Replay is at 60 Hz (`debugger.resume` + poll), never `movie.advanceToFrame` --
these recordings are state-anchored and frame-stepping them lands the arm-phase
fixup differently (CLAUDE.md).

Usage:
  python3 tools/phase4_coverage_runtime_probe.py \
      --movie movies/Phase4/Interpreter/temp_test_for_coverage.movie.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
AUDIT = ROOT / "analysis/phase4_text_coverage_audit_repaired.json"
MAX_WATCHES = 64

# Control ranges over code that MUST run in any gameplay movie. Ranges, not
# single PCs: the first version used 0x8003A3BC (the loader's table clear), which
# only fires on a level LOAD, and this movie is 815 frames of mid-level play. It
# reported "control did not fire" and the result was uninterpretable -- a bad
# control, not a bad instrument.
CONTROLS = [(0x800409F8, 400, "control_vec_normalize_len"),
            (0x80010000, 0x2D4, "control_emitter_prologue")]


def dense_gaps() -> list[tuple[int, int]]:
    d = json.loads(AUDIT.read_text())
    return [(int(g["start"], 16), g["bytes"]) for g in d["gaps"]
            if g["is_code"] and g["zero_percent"] < 50]


def plan(gaps: list[tuple[int, int]]) -> list[tuple[int, int, str]]:
    """One range watch per gap -- full coverage, not a sample."""
    return [(a, n, "gap_%08X" % a) for a, n in gaps]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--movie", required=True)
    ap.add_argument("--port", type=int, default=23481)
    ap.add_argument("--config-dir", default="/tmp/dsrepro_cov")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_coverage_runtime_probe.json"))
    args = ap.parse_args()

    movie = Path(args.movie)
    if not movie.is_absolute():
        movie = ROOT / movie

    gaps = dense_gaps()
    watches = plan(gaps) + list(CONTROLS)

    subprocess.run([str(ROOT / "tools/launch_repro_playback.sh"),
                    "--config-dir", args.config_dir, "--port", str(args.port),
                    "--disc", str(DISC), "--execution-mode", "Interpreter"], check=True)
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate("debugger-1000")
    c.transport.sock.settimeout(900)

    hits: Counter = Counter()
    frames = 0
    try:
        c.call("movie.load", {"path": str(movie)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        frames = st.get("frame_count") or 0
        c.call("execTrace.clear", {})
        armed = []
        for start, length, label in watches:
            r = c.call("execTrace.addRangeWatch",
                       {"start": "0x%08x" % start, "end": "0x%08x" % (start + length),
                        "label": label, "capture": [], "max_events": 256,
                        "filter": {"max_per_frame": 4}})
            armed.append((r.get("watch_id"), label, start, length))
        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        budget = 60 + frames / 30.0
        while time.time() - began < budget:
            time.sleep(2.0)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception:                                   # noqa: BLE001
                idx = last
            if idx == last:
                stalls += 1
                if stalls >= 6:
                    break
            else:
                stalls = 0
            last = idx
        # Query by watch_id. The first version asked execTrace.get for a LABEL and
        # silently got nothing back, so every count read as zero.
        for wid, label, _s, _n in armed:
            try:
                w = c.call("execTrace.get", {"watch_id": wid})
                n = (w.get("hit_count") if isinstance(w, dict) else 0) or 0
                if not n and isinstance(w, dict):
                    n = len(w.get("events") or [])
                if n:
                    hits[label] = n
            except Exception as e:                              # noqa: BLE001
                hits.setdefault("_query_error_" + label, 0)
                print("  query failed for", label, str(e)[:70])
        final_index = last
    finally:
        try:
            c.call("execTrace.clear", {})
        except Exception:                                       # noqa: BLE001
            pass
        subprocess.run([str(Path.home() / "duckstation/scripts/debugger-client/"
                             "launch_debugger_instance.sh"), "stop",
                        "--config-dir", args.config_dir], check=False)

    control_fired = any(k.startswith("control_") for k in hits)
    gap_hits = {k: v for k, v in hits.items() if k.startswith("gap_")}
    gaps_hit = sorted({k.split("_")[1] for k in gap_hits})

    out = {
        "_comment": "Does a movie execute code the static census still misses? "
                    "Regenerate: tools/phase4_coverage_runtime_probe.py",
        "generated": str(date.today()),
        "movie": str(movie.relative_to(ROOT)),
        "movie_frames": frames,
        "final_playback_index": final_index,
        "uncovered_dense_gaps": [{"start": "0x%08X" % a, "bytes": n} for a, n in gaps],
        "uncovered_dense_bytes": sum(n for _a, n in gaps),
        "watches_armed": len(watches),
        "watch_kind": "range (execTrace.addRangeWatch) -- full coverage of each gap",
        "control_fired": control_fired,
        "gap_hits": gap_hits,
        "distinct_gaps_hit": gaps_hit,
        "method_limits": ("Coverage of the gaps is COMPLETE -- one range watch per gap via "
                          "execTrace.addRangeWatch, not a sample. The limit is the MOVIE, "
                          "not the instrument: a hit proves the gap is live code, a miss "
                          "only says this recording did not execute it. Silence is never "
                          "proof that a region is dead."),
        "verdict": None,
    }
    if not control_fired:
        out["verdict"] = ("INCONCLUSIVE -- no control PC fired, so the instrument cannot be "
                          "shown to have engaged. A zero here means nothing.")
    elif gap_hits:
        out["verdict"] = ("FOUND LIVE CODE -- %d of the %d uncovered gaps executed. Those "
                          "gaps are code the static walk could not reach, and each hit is a "
                          "concrete entry point to seed a function from."
                          % (len(gaps_hit), len(gaps)))
    else:
        out["verdict"] = ("NO GAP CODE OBSERVED -- controls fired, so the instrument worked, "
                          "and NONE of the %d uncovered gaps executed anywhere in this movie "
                          "(full range coverage, not a sample). Consistent with the residual "
                          "being error paths, unused library code, or data -- but NOT proof "
                          "of it: another recording could still reach them." % len(gaps))

    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"movie {movie.name}: {frames} frames, {len(watches)} watches")
    print(f"control fired: {control_fired}   gap hits: {dict(gap_hits) or 'none'}")
    print("\n" + out["verdict"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
