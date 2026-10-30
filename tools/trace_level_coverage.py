#!/usr/bin/env python3
"""Per-level dynamic coverage — which resident functions EXECUTE in each level.

Phase-5 Stage B (trace-based naming). Replays each cold-boot movie in
movies/go_to_end/ (LEVEL00-Training … LEVEL15) on an isolated DuckStation
instance and collects the set of resident functions that EXECUTE per level via
the server-side `movie.coverageToFrame` RPC (coverage-only range watch over the
resident text [0x80010000, 0x800827ff], turbo-advanced through the movie). Each
returned PC maps to its containing census function.

Output: analysis/traces/level_coverage.json (per-level covered function starts).
tools/function_census.py folds these into the `dynamic` discovery signal (→
confidence=confirmed), which feeds the ranker/callgraph/Canon naming. The resident
match metric is unaffected (dynamic is evidence, not a match).

REPLAY CONTRACT (hard-won — do NOT regress):
- The isolated instance MUST run the repro-matched emulation config, else a from_boot
  movie desyncs while `reproducible` STILL reads true (the movie system tracks neither):
    * CPU [CPU] ExecutionMode=CachedInterpreter (default recompiler diverges on timing,
      accumulating → desync "later in the movie"; RE is unaffected — same guest code —
      but sync is required to REACH the traced state);
    * memory card seeded to the pristine owner snapshot before every boot (blank card
      steers BIOS/menu navigation differently → early desync; replay-saves must not
      accumulate across movies).
  `tools/launch_repro_playback.sh` owns this config; `--relaunch` reseeds+relaunches a
  fresh instance per movie via it. The generic fork launcher writes NO [CPU] section and
  CANNOT be used for movie replay.
- from_boot movies MUST start with `movie.startPlayback {load_start_state:true}` so
  the movie API power-cycles and playback is REPRODUCIBLE. `startPlayback {}` (default
  load_start_state:false) or a manual debugger.reset replays on the current state and
  desyncs — verify `movie.status.reproducible == true`.
- The movie supplies every controller input; NEVER hand-advance boot/menu with
  advanceFrames/advanceToFrame.
- Chain coverageToFrame in SMALL (~400f) increments: a whole-movie span blocks long
  enough to drop the WebSocket response (the work still completes, but the coverage
  payload is lost). Reproducibility holds across chained increments.

  # full sweep, fresh repro instance per movie (recommended):
  python tools/trace_level_coverage.py --relaunch --port 23460 --token debugger-1000
  # single movie against an already-running repro instance:
  python tools/trace_level_coverage.py --port 23460 --only LEVEL01
"""
from __future__ import annotations

import argparse
import bisect
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVIE_DIR = ROOT / "movies" / "go_to_end"
CENSUS = ROOT / "analysis" / "functions.json"
OUT = ROOT / "analysis" / "traces" / "level_coverage.json"
LAUNCHER = ROOT / "tools" / "launch_repro_playback.sh"
DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
TEXT_LO, TEXT_HI = 0x80010000, 0x80082800


def _fn_index():
    fns = [r for r in json.loads(CENSUS.read_text())["functions"]
           if r.get("space") == "resident"]
    starts = sorted(int(r["start"], 16) for r in fns)
    by = {int(r["start"], 16): r for r in fns}
    return starts, by


def pc_to_func(pc, starts, by):
    i = bisect.bisect_right(starts, pc) - 1
    if i < 0:
        return None
    st = starts[i]
    return st if pc < int(by[st]["end"], 16) else None


def _ru32(call, a):
    r = call("debugger.readMemory", {"address": f"{a:#x}", "length": 4})
    import struct
    return struct.unpack("<I", bytes.fromhex(r["hex"]))[0] if r.get("hex") else None


def _coverage_segment(call, target, covered, starts, by):
    """One server-side movie.coverageToFrame call: turbo-advance to `target`,
    accumulating the distinct resident PCs hit into `covered`. Returns
    frames_advanced so the caller can detect a stall/desync."""
    r = call("movie.coverageToFrame", {"frame": target, "start": f"{TEXT_LO:#x}",
                                       "end": f"{TEXT_HI - 1:#x}", "max_frames": 100000,
                                       "max_pcs": 200000, "label": "resident_text"})
    cov = r.get("coverage") or {}
    for pc in cov.get("pcs") or []:
        p = int(pc, 16) if isinstance(pc, str) else pc
        if TEXT_LO <= p < TEXT_HI:
            fs = pc_to_func(p, starts, by)
            if fs is not None:
                covered.add(fs)
    return r.get("frames_advanced", 0)


def trace_movie(call, movie: Path, chunk: int, starts, by, budget_s: float) -> dict:
    """Replay a from-boot movie and collect resident coverage via the server-side
    `movie.coverageToFrame` RPC — a single call installs a coverage-only range watch,
    turbo-advances the whole span, returns the distinct PCs, and removes the watch.
    No client-side chunk loop => no free-running desync and no instrumentation churn.
    Two segments (to n//2, then n) let us read a MID-level scene-id as a
    gameplay-quality gate while still covering the full movie."""
    call("movie.stopPlayback")
    call("movie.load", {"path": str(movie)})
    # DOCUMENTED reproducible path for a from_boot movie: load_start_state:true
    # power-cycles through the movie API and starts REPRODUCIBLE playback. Do NOT
    # manually debugger.reset, and do NOT hand-advance boot/menu with advanceFrames
    # — the movie supplies every controller input. (docs/external-debugger-movie.md)
    call("movie.startPlayback", {"start_frame": 0, "load_start_state": True})
    reproducible = bool(call("movie.status").get("reproducible"))
    nframes = len(json.loads(movie.read_text())["frames"])
    covered: set[int] = set()
    idx, max_idx, gameplay_scene, t0 = 0, 0, None, time.monotonic()
    completed = False
    # Chain SMALL coverageToFrame increments: each is a full server-side coverage
    # pass (reproducible, no free-running) that returns in ~2-3s; larger spans block
    # long enough to drop the WebSocket response. Reproducibility holds across chunks.
    while idx < nframes:
        if time.monotonic() - t0 > budget_s:
            break
        target = min(idx + chunk, nframes)
        _coverage_segment(call, target, covered, starts, by)
        ms = call("movie.status")
        new_idx = ms.get("playback_index", idx) or 0
        max_idx = max(max_idx, new_idx)
        # Past the load+FMV region (~movie midpoint) sample current_scene_id; keep the
        # LAST nonzero one as the level's representative gameplay scene (0/0xffffffff =
        # boot/menu/transition). This becomes the empirical scene->level table.
        if new_idx >= nframes // 2:
            s = _ru32(call, 0x80082504)
            if s not in (None, 0, 0xffffffff):
                gameplay_scene = s
        if ms.get("playing") is False:                # movie ran to its end: on the final
            completed = True                          # frame playback stops and playback_index
            break                                     # resets to 0 — that's completion, not a stall
        if new_idx <= idx:                            # no forward progress but still playing -> real stall
            break
        idx = new_idx
    # reached_end: the movie signalled completion, or we advanced to (near) the last frame
    reached_end = completed or max_idx >= nframes - 2
    scenes = [gameplay_scene] if gameplay_scene is not None else []
    print(f"[cov] {movie.stem}: reproducible={reproducible} {max_idx}/{nframes} frames, "
          f"reached_end={reached_end} {len(covered)} functions, "
          f"scene={hex(gameplay_scene) if gameplay_scene is not None else '?'}")
    return {"covered": covered, "frames": max_idx, "reproducible": reproducible,
            "scene_ids": [f"{x:#x}" for x in scenes], "reached_end": reached_end, "stopped": "ok"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=24242)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--chunk", type=int, default=400, help="frames per coverageToFrame increment")
    ap.add_argument("--only", help="single movie stem, e.g. LEVEL01")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--budget", type=float, default=180.0, help="per-movie wall-clock seconds")
    ap.add_argument("--relaunch", action="store_true",
                    help="reseed+relaunch a fresh repro instance (launch_repro_playback.sh) per movie")
    ap.add_argument("--config-dir", default="/tmp/dsrepro", help="isolated config dir for --relaunch")
    ap.add_argument("--fresh", action="store_true", help="ignore/overwrite prior level_coverage.json")
    args = ap.parse_args()

    sys.path.insert(0, str(Path.home() / "duckstation" / "scripts" / "debugger-client"))
    from duckstation_debug_client import DebuggerClient, RpcError  # noqa: E402

    conn = {"c": None}

    def _connect():
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(args.timeout)
        conn["c"] = c

    def call(m, p=None):
        # resilient: an oversized/slow window can drop the socket though the guest
        # is fine (state recovers) — reconnect once and retry rather than abort.
        for attempt in (1, 2):
            try:
                return conn["c"].call(m, p or {})
            except RpcError:
                return {}
            except (ConnectionError, OSError):
                if attempt == 2:
                    return {}
                _connect()
        return {}

    def relaunch():
        # reseed card + relaunch a fresh instance on the repro-matched config, then
        # reconnect to it. Guarantees identical boot card + CPU mode per movie (and
        # clears from_boot-playback instrumentation churn — see duckstation-trace-gotchas).
        r = subprocess.run(
            ["bash", str(LAUNCHER), "--config-dir", args.config_dir, "--port", str(args.port),
             "--token", args.token, "--disc", str(DISC)],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"launch_repro_playback failed:\n{r.stdout}\n{r.stderr}")
        print(f"[cov] {r.stdout.strip().splitlines()[-1]}")
        time.sleep(1)
        _connect()

    if not args.relaunch:
        _connect()
        st = call("debugger.status")
        if st.get("game_serial") != "SCUS-94288":
            raise SystemExit(f"wrong game: {st.get('game_serial')}")

    movies = sorted(MOVIE_DIR.glob("*.movie.json"))
    if args.only:
        movies = [m for m in movies if m.stem.startswith(args.only)]
    if not movies:
        raise SystemExit(f"no movies in {MOVIE_DIR}")

    starts, by = _fn_index()
    prev = {} if args.fresh else (json.loads(OUT.read_text()) if OUT.exists() else {})
    levels = prev.get("levels", {})
    level_scenes = prev.get("level_scenes", {})
    desynced = prev.get("desynced", [])

    def flush():
        # write after EVERY movie so a mid-run instance crash never wipes progress
        fn_levels: dict[str, list[str]] = {}
        for lv, addrs in levels.items():
            for a in addrs:
                fn_levels.setdefault(a, []).append(lv)
        covered_all = set(fn_levels)
        unk = sum(1 for a in covered_all
                  if by.get(int(a, 16), {}).get("classification") == "unknown")
        OUT.write_text(json.dumps({
            "generated_by": "tools/trace_level_coverage.py",
            "text_range": [f"{TEXT_LO:#x}", f"{TEXT_HI:#x}"],
            "levels": levels, "level_scenes": level_scenes, "desynced": desynced,
            "function_levels": fn_levels,
            "summary": {"functions_covered": len(covered_all),
                        "unknown_covered": unk, "resident_total": len(starts),
                        "levels_ok": len(levels)},
        }, indent=1) + "\n")
        return len(covered_all), unk

    for m in movies:
        stem = m.stem.replace(".movie", "")
        if args.relaunch:
            relaunch()
            st = call("debugger.status")
            if st.get("game_serial") != "SCUS-94288":
                raise SystemExit(f"wrong game after relaunch: {st.get('game_serial')}")
        res = trace_movie(call, m, args.chunk, starts, by, args.budget)
        # quality gate (coverage-fix era: movie replay under coverage is now cycle-neutral,
        # so we can assert full completion, not just "some scene"): trust coverage only from a
        # REPRODUCIBLE replay that REACHED (near) the final frame AND landed in a nonzero
        # gameplay scene. Anything else => desync / early stop; record separately, don't fold.
        if res.get("reproducible") and res.get("reached_end") and res["scene_ids"]:
            levels[stem] = sorted(f"{a:#010x}" for a in res["covered"])
            level_scenes[stem] = {"scene_ids": res["scene_ids"], "reproducible": True,
                                  "reached_end": True}
        else:
            desynced.append(stem)
            print(f"[cov] {stem}: NOT TRUSTED (reproducible={res.get('reproducible')}, "
                  f"reached_end={res.get('reached_end')}, scenes={res['scene_ids']})")
        tot, unk = flush()   # incremental checkpoint
        print(f"[cov]   checkpoint: {tot} fns ({unk} unknown) across {len(levels)} levels")
    print(f"[cov] DONE — {len(levels)} levels ok, {len(desynced)} not-trusted: {desynced}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
