#!/usr/bin/env python3
"""Boot→LEVEL01 load/execution evidence capture (Phase 4 — docs/SUBSTRATE.md).

Replays the pinned from-boot movie (flik_to_level01_stall.mv.movie.json) on the
ISOLATED DuckStation debugger instance with bounded non-halting instrumentation:

  execTrace   entry PCs of the loader/decompressor/state-machine anchors, the
              SFX path, and the full resident→overlay entry surface from the
              census (analysis/functions.json), each capturing ra (+args where
              the callee's a0/a1 carry src/dst)
  accessLog   write watches on the main-shell substate / scene-select /
              current-scene globals
  transferLog kept recording; transferLog.resolve maps the known load
              destinations (Region A/B, LEVEL.RAW heap, LEVEL.DAT image, mesh
              buffer) back to disc file/LBA — resolved once per window so the
              100k ring buffer can't age them out

Outputs (committed, bytes-free metadata):
  analysis/traces/boot_trace.json     run metadata + watch milestones + state
                                      writes + disc-provenance resolutions
  analysis/traces/overlay_loads.json  per-region load provenance + first-exec
  analysis/traces/function_hits.csv   address,name,hits,first_frame — feeds
                                      tools/function_census.py `dynamic` signal

RELAUNCH THE INSTANCE FIRST — a previously-instrumented/replayed instance
degrades (verified 2026-07-08: same script, stale instance -> 18/62 PCs hit
and 0/6 provenance resolutions; fresh instance -> 48/62 and 6/6). Known
project gotcha: relaunch + fresh movie per clean run.

Requires the instance from CLAUDE.md:
  ~/duckstation/scripts/debugger-client/launch_debugger_instance.sh start \
      --disc "Disney-Pixar A Bug's Life (v1.0).cue" --port 23460 --no-fastboot
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACES = ROOT / "analysis" / "traces"
MOVIE = ROOT / "flik_to_level01_stall.mv.movie.json"
sys.path.insert(0, os.path.expanduser("~/duckstation/scripts/debugger-client"))

# Resident anchors (symbol names from symbols/re_symbols.sym / docs).
ANCHORS = [
    # (pc, label, capture, max_events)
    (0x8005F690, "entry0",                    ["pc", "ra"], 8),
    (0x8004FA40, "main_shell_state_machine",  ["pc", "ra"], 8),
    (0x8004ECD4, "gameplay_state_machine",    ["pc", "ra"], 64),
    (0x80046330, "universal_file_reader",     ["pc", "ra", "a0", "a1"], 2048),
    (0x8003D620, "region_a_overlay_loader",   ["pc", "ra", "a0", "a1"], 256),
    (0x8003F5B8, "memory_bin_loader",         ["pc", "ra", "a0", "a1"], 64),
    (0x8001A1DC, "level_raw_lzss_decompress", ["pc", "ra", "a0", "a1", "a2"], 4096),
    (0x8003A318, "level_raw_load_orchestrator", ["pc", "ra", "a0", "a1"], 64),
    (0x800224EC, "render_driver",             ["pc", "ra"], 8),
    (0x80050994, "sfx_dispatch",              ["pc", "ra", "a0"], 512),
    (0x80042FA0, "vab_load",                  ["pc", "ra", "a0", "a1"], 64),
]
STATE_GLOBALS = [
    (0x8008243C, "main_shell_substate"),
    (0x8008245C, "scene_select_index"),
    (0x80082504, "current_scene_id"),
]
# Known load destinations to resolve back to disc provenance.
RESOLVE_ADDRS = [
    (0x800B39A4, "region_a_code"),
    (0x800B5788, "region_b_base"),
    (0x800BD518, "memory_bin_init"),
    (0x80115AAC, "level_raw_compressed_base"),
    (0x801607F8, "level_dat_image"),
    (0x8012C1D0, "chunk35_mesh_buffer"),
]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=23460)
    ap.add_argument("--token", default="debugger-%d" % os.getuid())
    ap.add_argument("--window", type=int, default=60, help="frames per advance window")
    ap.add_argument("--margin", type=int, default=240,
                    help="extra frames after the movie input span")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(60)

    st = c.call("debugger.status")
    if st.get("game_serial") != "SCUS-94288":
        raise SystemExit(f"REFUSING: wrong game {st.get('game_serial')}")
    movie_meta = json.loads(MOVIE.read_text())
    total_frames = len(movie_meta["frames"]) + args.margin

    fork_rev = subprocess.run(["git", "-C", os.path.expanduser("~/duckstation"),
                               "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()

    # --- arm instrumentation, start the from-boot replay, re-arm if the
    # reset cleared anything (movie reset is not documented to clear watches,
    # but verify rather than assume) ---
    c.call("debugger.pause")
    print(f"[trace] loading movie ({len(movie_meta['frames'])} frames, from_boot)")
    c.call("movie.load", {"path": str(MOVIE)})
    census = json.loads((ROOT / "analysis" / "functions.json").read_text())
    overlay_entries = sorted(int(a, 16) for a in census["resident_overlay_entry_targets"])

    def arm():
        c.call("execTrace.clear")
        c.call("accessLog.clear")
        watches, acc = {}, {}
        for pc, label, cap, maxev in ANCHORS:
            r = c.call("execTrace.addWatch", {"pc": f"{pc:#x}", "label": label,
                                              "capture": cap, "max_events": maxev})
            watches[r["watch_id"]] = (pc, label)
        for pc in overlay_entries:
            r = c.call("execTrace.addWatch", {"pc": f"{pc:#x}", "label": f"ovl_{pc:08x}",
                                              "capture": ["pc", "ra"], "max_events": 64})
            watches[r["watch_id"]] = (pc, f"ovl_{pc:08x}")
        for addr, label in STATE_GLOBALS:
            r = c.call("accessLog.addWatch", {"address": f"{addr:#x}", "length": 4,
                                              "type": "write", "max_events": 4096})
            acc[r["watch_id"]] = (addr, label)
        c.call("transferLog.clear")
        c.call("transferLog.start")
        return watches, acc

    # from_boot playback re-loads the game, which CLEARS all non-halting
    # instrumentation (verified empirically 2026-07-08: arming before playback
    # loses transferLog + most exec watches even though stale watch bookkeeping
    # still lists them). So: start playback, let the reset land, THEN arm.
    # Known boot shadow: PCs that only execute in the first ~2 frames (crt0
    # entry0, the single main-shell call) are unobservable by this design.
    c.call("movie.startPlayback", {})
    c.call("emulator.advanceFrames", {"frames": 2})   # let the reset land
    frame_base = c.call("debugger.status").get("frame")
    watches, acc = arm()
    print(f"[trace] armed {len(watches)} exec watches, {len(acc)} write watches, transferLog")

    # --- windowed replay ---
    # transferLog records DMA targets as PHYSICAL addresses, so resolve with
    # the KSEG0 bit stripped. The same RAM is reused by successive loads
    # (loading screen -> level payload), so keep the HISTORY of distinct
    # resolutions per label, resolved every window before the 100k ring ages
    # the events out.
    resolved: dict[str, list[dict]] = {label: [] for _, label in RESOLVE_ADDRS}
    frame = 2
    while frame < total_frames:
        step = min(args.window, total_frames - frame)
        c.call("emulator.advanceFrames", {"frames": step})
        frame += step
        for addr, label in RESOLVE_ADDRS:
            r = c.call("transferLog.resolve", {"address": f"{addr & 0x1FFFFFFF:#x}"})
            if r.get("resolved"):
                hist = resolved[label]
                key = (r.get("file"), r.get("fileOffset"), r.get("lba"))
                if not hist or (hist[-1].get("file"), hist[-1].get("fileOffset"),
                                hist[-1].get("lba")) != key:
                    r["_first_seen_by_frame"] = frame
                    r["_address"] = f"{addr:#010x}"
                    hist.append(r)
        ms = c.call("movie.status")
        if not ms.get("playing"):
            print(f"[trace] movie playback ended at frame ~{frame}")
            if frame < len(movie_meta["frames"]):
                print("[trace] WARNING: ended before input span; check truncation")
            break
        if frame % 600 < args.window:
            n_res = sum(1 for h in resolved.values() if h)
            print(f"[trace] frame {frame}/{total_frames}, resolved {n_res}/{len(RESOLVE_ADDRS)}")

    c.call("debugger.pause")
    final = c.call("debugger.status")

    # --- harvest ---
    exec_events = {}
    for wid, (pc, label) in watches.items():
        r = c.call("execTrace.get", {"watch_id": wid, "offset": 0, "limit": 10000})
        evs = r.get("events", [])
        exec_events[label] = {
            "pc": f"{pc:#010x}", "hit_count": next(
                (w.get("hit_count") for w in r.get("watches", [])
                 if w.get("watch_id") == wid), len(evs)),
            "truncated": r.get("truncated", False),
            "first": evs[0] if evs else None,
            "last": evs[-1] if evs else None,
            "events": evs if len(evs) <= 4096 else evs[:4096],
        }
    state_writes = {}
    for wid, (addr, label) in acc.items():
        r = c.call("accessLog.get", {"watch_id": wid, "offset": 0, "limit": 4096})
        state_writes[label] = {"address": f"{addr:#010x}", "events": r.get("events", [])}

    # --- cleanup instrumentation (instance stays up for follow-ups) ---
    c.call("execTrace.clear")
    c.call("accessLog.clear")
    c.call("transferLog.clear")

    resolved = {k: v for k, v in resolved.items() if v}
    TRACES.mkdir(parents=True, exist_ok=True)
    meta = {
        "generated_by": "tools/trace_boot_baseline.py",
        "disc": {"serial": st.get("game_serial"), "title": st.get("game_title")},
        "movie": {"path": MOVIE.name, "sha256": sha256(MOVIE),
                  "input_frames": len(movie_meta["frames"]),
                  "created": movie_meta.get("created")},
        "fork_rev": fork_rev,
        "final_frame": final.get("frame"),
        "frame_base_absolute": frame_base,
        "note": "TWO frame clocks: event `frame` fields use the emulator's "
                "ABSOLUTE counter (which does not reset with movie playback); "
                "`_first_seen_by_frame` on provenance records is movie-relative "
                "(loop frames). movie_frame = absolute - frame_base_absolute. "
                "Deterministic modulo async CD scheduling (treat ±1 as identical).",
    }
    boot = {
        **meta,
        "anchors": {lbl: {k: v for k, v in rec.items() if k != "events"}
                    for lbl, rec in exec_events.items() if not lbl.startswith("ovl_")},
        "anchor_events": {lbl: rec["events"] for lbl, rec in exec_events.items()
                          if not lbl.startswith("ovl_")},
        "state_writes": state_writes,
        "disc_provenance": resolved,
    }
    (TRACES / "boot_trace.json").write_text(json.dumps(boot, indent=1, sort_keys=True) + "\n")

    ovl = {
        **meta,
        "regions": resolved,
        "entry_first_exec": {
            lbl[4:]: {"first": rec["first"], "hits": rec["hit_count"]}
            for lbl, rec in exec_events.items()
            if lbl.startswith("ovl_") and rec["first"]},
        "loader_calls": {
            "region_a_overlay_loader": exec_events["region_a_overlay_loader"]["events"],
            "memory_bin_loader": exec_events["memory_bin_loader"]["events"],
        },
    }
    (TRACES / "overlay_loads.json").write_text(json.dumps(ovl, indent=1, sort_keys=True) + "\n")

    syms = {}
    for r in census["functions"]:
        if r["space"] == "resident":
            syms[int(r["start"], 16)] = r["name"]
    with (TRACES / "function_hits.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["address", "name", "hits", "first_frame"])
        w.writeheader()
        for lbl, rec in sorted(exec_events.items(), key=lambda kv: kv[1]["pc"]):
            if not rec["hit_count"]:
                continue
            addr = int(rec["pc"], 16)
            w.writerow({"address": rec["pc"], "name": syms.get(addr, lbl),
                        "hits": rec["hit_count"],
                        "first_frame": (rec["first"] or {}).get("frame", "")})

    n_hit = sum(1 for r in exec_events.values() if r["hit_count"])
    n_res = sum(1 for h in resolved.values() if h)
    print(f"[trace] wrote {TRACES}/boot_trace.json overlay_loads.json function_hits.csv "
          f"({n_hit}/{len(exec_events)} watched PCs hit; "
          f"{n_res}/{len(RESOLVE_ADDRS)} regions resolved)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
