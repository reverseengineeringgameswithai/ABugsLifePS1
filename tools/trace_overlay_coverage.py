#!/usr/bin/env python3
"""Per-overlay dynamic coverage — which OVERLAY functions execute in each scene.

Overlay analogue of tools/trace_level_coverage.py (which covers only the resident
text). Replays each pristine cold-boot movie in movies/go_to_end/ on a REPRODUCIBLE
DuckStation (tools/launch_repro_playback.sh — a from-boot movie desyncs without the
recorded [CPU] mode + card seed), installs a coverage-only range watch over the
overlay window [region_a, overlay_hi) via movie.coverageToFrame, and maps the hit
PCs to (overlay, function-start) using the census.

Region-A (0x800B39A0) holds the level's swap overlay; a level's movie exercises its
_LEVEL/_LEVEL1 variants. Region-B (0x800B5788) holds MEMORY.BIN (menu/save/title),
exercised by the boot/menu at the START of every movie. A Region-A PC is assigned to
whichever of THIS level's overlay variants has a census fn-start covering it; a
Region-B PC is MEMORY. Coverage gaps are logged, never guessed.

PRISTINE MEDIA ONLY (movies) — never modded saves (the modding-safety EXE-code gate
constraint). Throwaway instance; never operator port 2346.

  python tools/trace_overlay_coverage.py --relaunch --port 23460 --token debugger-1000
  python tools/trace_overlay_coverage.py --relaunch --only LEVEL01     # one movie
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVIE_DIR = ROOT / "movies" / "go_to_end"
CENSUS = ROOT / "analysis" / "functions.json"
OUT = ROOT / "analysis" / "traces" / "overlay_coverage.json"
LAUNCHER = ROOT / "tools" / "launch_repro_playback.sh"
DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"

REGION_A = 0x800B39A0
REGION_B = 0x800B5788
OVL_LO, OVL_HI = 0x800B39A0, 0x800BE000


def _overlay_index():
    """{overlay: sorted [(start,end,addrhex)]} for overlay code fns, from census."""
    fj = json.loads(CENSUS.read_text())
    by = {}
    for f in fj["functions"]:
        if f.get("space") == "overlay" and f.get("range_type") == "code":
            by.setdefault(f["overlay"], []).append(
                (int(f["start"], 16), int(f["end"], 16), f["start"]))
    for ov in by:
        by[ov].sort()
    return by


def _pc_to_start(pc, spans):
    import bisect
    i = bisect.bisect_right(spans, (pc, 1 << 62)) - 1
    if i >= 0 and spans[i][0] <= pc < spans[i][1]:
        return spans[i][2]
    return None


def level_variants(stem, ovl_by):
    """Overlay names for a movie stem: LEVEL01 -> LEVEL01_LEVEL, LEVEL01_LEVEL1."""
    lvl = stem.split("-")[0]                      # LEVEL00-Training -> LEVEL00
    return [ov for ov in ovl_by if ov.startswith(lvl + "_")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=23460)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--chunk", type=int, default=400)
    ap.add_argument("--only", help="single movie stem, e.g. LEVEL01")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--budget", type=float, default=200.0)
    ap.add_argument("--relaunch", action="store_true")
    ap.add_argument("--config-dir", default="/tmp/dsrepro")
    ap.add_argument("--fresh", action="store_true")
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
        r = subprocess.run(["bash", str(LAUNCHER), "--config-dir", args.config_dir,
                            "--port", str(args.port), "--token", args.token, "--disc", str(DISC)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"launch_repro_playback failed:\n{r.stdout}\n{r.stderr}")
        print(f"[ovl-cov] {r.stdout.strip().splitlines()[-1]}")
        time.sleep(1)
        _connect()

    if not args.relaunch:
        _connect()

    ovl_by = _overlay_index()
    movies = sorted(MOVIE_DIR.glob("*.movie.json"))
    if args.only:
        movies = [m for m in movies if m.stem.startswith(args.only)]

    prev = {} if args.fresh else (json.loads(OUT.read_text()) if OUT.exists() else {})
    overlays = prev.get("overlays", {})       # overlay -> {fn_start: hitcount-ish}
    per_movie = prev.get("per_movie", {})

    for movie in movies:
        stem = movie.stem.replace(".movie", "")
        if args.relaunch:
            relaunch()
        call("movie.stopPlayback")
        call("movie.load", {"path": str(movie)})
        call("movie.startPlayback", {"start_frame": 0, "load_start_state": True})
        repro = bool(call("movie.status").get("reproducible"))
        nframes = len(json.loads(movie.read_text())["frames"])
        variants = level_variants(stem, ovl_by)
        raw_a, raw_b = set(), set()
        idx, t0 = 0, time.monotonic()
        while idx < nframes and time.monotonic() - t0 < args.budget:
            target = min(idx + args.chunk, nframes)
            r = call("movie.coverageToFrame", {"frame": target, "start": hex(OVL_LO),
                                               "end": hex(OVL_HI - 1), "max_frames": 100000,
                                               "max_pcs": 200000, "label": "ovl"})
            for pc in (r.get("coverage") or {}).get("pcs") or []:
                p = int(pc, 16) if isinstance(pc, str) else pc
                if REGION_B <= p < OVL_HI:
                    raw_b.add(p)
                elif REGION_A <= p < REGION_B:
                    raw_a.add(p)
            ms = call("movie.status")
            ni = ms.get("playback_index", idx) or 0
            if ms.get("playing") is False:
                break
            if ni <= idx:
                break
            idx = ni
        # map Region-B -> MEMORY; Region-A -> this level's variant(s)
        mem_starts = {_pc_to_start(p, ovl_by.get("MEMORY", [])) for p in raw_b}
        mem_starts.discard(None)
        a_starts = {}
        for ov in variants:
            spans = ovl_by[ov]
            hit = {_pc_to_start(p, spans) for p in raw_a}
            hit.discard(None)
            if hit:
                a_starts[ov] = sorted(hit)
        for s in mem_starts:
            overlays.setdefault("MEMORY", {})[s] = overlays.get("MEMORY", {}).get(s, 0) + 1
        for ov, starts in a_starts.items():
            for s in starts:
                overlays.setdefault(ov, {})[s] = overlays.get(ov, {}).get(s, 0) + 1
        per_movie[stem] = {"reproducible": repro, "reached_frame": idx, "nframes": nframes,
                           "region_a_pcs": len(raw_a), "region_b_pcs": len(raw_b),
                           "mem_fns": len(mem_starts),
                           "level_variant_fns": {ov: len(v) for ov, v in a_starts.items()}}
        print(f"[ovl-cov] {stem}: repro={repro} frame={idx}/{nframes} "
              f"A_pcs={len(raw_a)} B_pcs={len(raw_b)} MEM_fns={len(mem_starts)} "
              f"{ {ov: len(v) for ov, v in a_starts.items()} }")

    doc = {"generated_by": "tools/trace_overlay_coverage.py",
           "overlay_window": [hex(OVL_LO), hex(OVL_HI)],
           "overlays": {ov: {s: overlays[ov][s] for s in sorted(overlays[ov])}
                        for ov in sorted(overlays)},
           "per_movie": {k: per_movie[k] for k in sorted(per_movie)}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    tot = sum(len(m) for m in overlays.values())
    print(f"[ovl-cov] wrote {OUT.relative_to(ROOT)}: {tot} covered overlay fns "
          f"across {len(overlays)} overlays")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
