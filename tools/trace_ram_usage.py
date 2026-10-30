#!/usr/bin/env python3
"""Runtime used-memory tracer for the modding-safety map (msm m2/m3).

Two complementary signals over the DuckStation debugger API (throwaway instance):
  * WRITTEN (value): snapshot full RAM (readMemory, no interpreter penalty), advance,
    re-snapshot, diff -> bytes whose VALUE changed. Breadth; misses memset-of-zero.
  * WRITTEN (access): accessLog write-watches over a small region catch EVERY store,
    incl. memset-to-zero of already-zero bytes (the 0x8007FDC0 workspace hazard).
    Capped at 256 B x 64 watches ~= 16 KiB — use only on the acute cave zone.
  * EXECUTE: movie.coverageToFrame over the text range (cycle-neutral).

  m2 validation (this entrypoint):  python tools/trace_ram_usage.py --validate
     write-watch the 6 known FORBIDDEN ranges + the 2 proven-safe caves through the
     boot->LEVEL01 movie; forbidden must show writes, safe caves must not.

Owner-media-gated (needs the running throwaway instance on port 23460 + the disc).
Emits ranges only, never RAM bytes.
"""
from __future__ import annotations
import argparse, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import ABL_DIR, DEBUGGER_CLIENT  # noqa: E402
sys.path.insert(0, DEBUGGER_CLIENT)
from duckstation_debug_client import DebuggerClient  # noqa: E402

PORT, TOKEN = 23460, "debugger-1000"
CAVE_ZONE = (0x8007EFE8, 0x80082200)   # acute zone: all 6 forbidden ranges live here
FORBIDDEN = [(0x8007EFE8, 0x8007F0D8), (0x8007F130, 0x8007F170), (0x8007FDC0, 0x80080BE0),
             (0x800814BC, 0x80081530), (0x80081058, 0x800810A4), (0x80082030, 0x8008203C)]
SAFE_CAVES = [(0x800810C0, 0x800814BC, "blackberry_run"), (0x8007F174, 0x8007F376, "grain_hud_run")]


def connect():
    c = DebuggerClient("127.0.0.1", PORT, "ws")
    c.authenticate(TOKEN)
    c.transport.sock.settimeout(120)
    st = c.call("debugger.status", {})
    assert st.get("game_serial") == "SCUS-94288", st
    return c


def call(c, m, p=None):
    try:
        return c.call(m, p or {})
    except Exception as e:
        return {"_err": str(e)[:140]}


def arm_write_watches(c, ranges):
    """Arm 256-B write watches tiling each (start,end). Returns count armed."""
    n = 0
    for start, end, *lbl in ranges:
        a = start
        while a < end:
            seg = min(256, end - a)
            r = call(c, "accessLog.addWatch",
                     {"address": hex(a), "length": seg, "type": "write",
                      "label": f"{a:#x}", "max_events": 4000})
            if "_err" not in r:
                n += 1
            a += seg
    return n


GAME_CODE = (0x80010000, 0x800B39A0)   # resident EXE + overlay windows (exclude BIOS/CD loader)


def _int(v):
    return int(v, 16) if isinstance(v, str) else v


def collect_written(c, game_pc_only=True):
    """Addresses that fired a write watch. When game_pc_only, keep only writes whose
    WRITER PC is game code — excludes the BIOS/CD loader populating the EXE image at
    load (which harmlessly writes the mod's own bytes into a cave). Returns a set."""
    written = set()
    off = 0
    while True:
        r = call(c, "accessLog.get", {"offset": off, "limit": 10000})
        evs = r.get("events") or []
        for e in evs:
            pc = _int(e.get("pc") or 0)
            if game_pc_only and not (GAME_CODE[0] <= pc < GAME_CODE[1]):
                continue
            written.add(_int(e.get("address")))
        if len(evs) < 10000:
            break
        off += len(evs)
    return written


def validate(c):
    print("[msm m2] API method check:")
    for m, p in (("accessLog.addWatch", {"address": "0x8007fdc0", "length": 16, "type": "write"}),
                 ("accessLog.run", {"frames": 1}), ("accessLog.get", {"limit": 5}),
                 ("movie.coverageToFrame", {"frame": 1, "start": "0x80010000", "end": "0x80010004"})):
        r = call(c, m, p)
        print(f"   {m}: {'OK' if '_err' not in r else r['_err']}")
    call(c, "accessLog.clear")

    # drive boot->LEVEL01 with write-watches on forbidden + safe caves
    mv = os.path.abspath("flik_to_level01_stall.mv.movie.json")
    call(c, "emulator.setTurbo", {"enabled": True})
    call(c, "movie.load", {"path": mv})
    call(c, "movie.startPlayback", {"load_start_state": True})   # loadState -> arm AFTER
    watch_ranges = [(a, b, "forbidden") for a, b in FORBIDDEN] + SAFE_CAVES
    n = arm_write_watches(c, watch_ranges)
    print(f"[msm m2] armed {n} write-watches over forbidden+safe zone; driving movie...")
    # advance through the movie in chunks (watches persist across advanceToFrame)
    for target in range(600, 4300, 600):
        r = call(c, "movie.advanceToFrame", {"frame": min(target, 4253), "max_frames": 8000})
        if "_err" in r:
            break
    written = collect_written(c)
    print(f"[msm m2] {len(written)} distinct addresses written in the watched zone\n")

    print("FORBIDDEN ranges (method must flag as WRITTEN):")
    for a, b in FORBIDDEN:
        hit = sum(1 for w in written if a <= w < b)
        print(f"  {a:#x}-{b:#x}: {'WRITTEN ✓ (%d bytes)' % hit if hit else 'not written ✗'}")
    print("\nSAFE caves (method must leave UNwritten):")
    for a, b, lbl in SAFE_CAVES:
        hit = sum(1 for w in written if a <= w < b)
        print(f"  {a:#x}-{b:#x} {lbl}: {'WRITTEN ✗ (%d)' % hit if hit else 'clean ✓'}")
    call(c, "accessLog.clear")


def memcheck(c):
    """Write-watch the current candidate_free survivors through boot->LEVEL01 to catch
    game-code writes that VALUE snapshot-diff misses (memset-of-zero / store-of-same
    value — e.g. the 0x80081cf0 controller gp-global). Writes a ram_usage cache entry."""
    import json
    mm = json.load(open(f"{ABL_DIR}/analysis/memory_map.json"))
    surv = [(int(r["start"], 16), int(r["end"], 16)) for r in mm["regions"] if r["class"] == "candidate_free"]
    disc = f"{ABL_DIR}/Disney-Pixar A Bug's Life (v1.0).cue"
    call(c, "debugger.pause"); call(c, "emulator.bootSystem", {"path": disc, "force": True})
    call(c, "emulator.setTurbo", {"enabled": True})
    mv = f"{ABL_DIR}/flik_to_level01_stall.mv.movie.json"
    call(c, "movie.load", {"path": mv}); call(c, "movie.startPlayback", {"load_start_state": True})
    arm_write_watches(c, [(s, e, "surv") for s, e in surv])
    for t in range(600, 4300, 600):
        if "_err" in call(c, "movie.advanceToFrame", {"frame": min(t, 4253), "max_frames": 8000}): break
    written = collect_written(c, game_pc_only=True)
    hit = [[f"{s:#x}", f"{e:#x}"] for s, e in surv if any(s <= w < e for w in written)]
    json.dump({"state": "memcheck__flik_to_level01_boot", "source": "writewatch_memset",
               "candidate_free_written": hit},
              open(f"{ABL_DIR}/analysis/traces/ram_usage/memcheck__flik.json", "w"))
    call(c, "accessLog.clear")
    print(f"[memcheck] {len(hit)} survivor runs eliminated by write-watch (memset/same-value): {hit}")


def consolidate():
    """Fold analysis/traces/ram_usage/*.json (per-state, owner-local cache) into the
    committed analysis/traces/ram_usage_summary.json (deterministic; feeds the map)."""
    import glob, json
    root = ABL_DIR
    files = sorted(glob.glob(f"{root}/analysis/traces/ram_usage/*.json"))
    states, sources, written = [], {}, set()
    for f in files:
        d = json.load(open(f))
        if d.get("load_fail"):
            continue
        states.append(d["state"])
        sources[d.get("source", "?")] = sources.get(d.get("source", "?"), 0) + 1
        for s, e in d.get("candidate_free_written", []):
            written.add((int(s, 16), int(e, 16)))
    doc = {
        "generated_by": "tools/trace_ram_usage.py --consolidate",
        "coverage": {"pristine_states": len(states), "sources": dict(sorted(sources.items())),
                     "state_names": sorted(states)},
        "candidate_free_written": [[f"{s:#010x}", f"{e:#010x}"] for s, e in sorted(written)],
        "note": "PRISTINE states only (modded-disc saves excluded by an EXE-code content gate). "
                "Signal = value snapshot-diff (misses memset-of-zero) + boot->level movies. "
                "A candidate_free run here is written by game code in >=1 pristine state -> NOT a "
                "safe cave. Survivors are idle across the covered states, NOT proven-free.",
    }
    out = f"{root}/analysis/traces/ram_usage_summary.json"
    open(out, "w").write(json.dumps(doc, indent=1) + "\n")
    print(f"[consolidate] {len(states)} pristine states -> {len(written)} candidate_free runs "
          f"written; wrote {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--memcheck", action="store_true")
    ap.add_argument("--consolidate", action="store_true")
    a = ap.parse_args()
    if a.consolidate:
        consolidate()
        return 0
    c = connect()
    if a.validate:
        validate(c)
    if a.memcheck:
        memcheck(c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
