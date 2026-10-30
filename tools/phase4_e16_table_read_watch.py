#!/usr/bin/env python3
"""Phase-4 E16: does ANY shipped code read the three chunk pointer tables?

The LEVEL.RAW loader registers 46 chunks by pointer into three range-indexed
tables and never interprets the chunks themselves, so their formats belong to
whoever READS the tables:

    0x8009B4E8  markers 0x30..0x57  (40 slots)   <- 38 chunks live in LEVEL00
    0x8009C170  markers 0x28..0x2F  ( 8 slots)
    0x800A6450  markers 0x58..0x5F  ( 8 slots)

A complete static scan (tools/phase4_e16_table_consumers.c, plus a widened
displacement-window sweep over the resident EXE and all 30 .BIN files) finds
three stores and ZERO reads. Static absence is only as good as the search,
though, so this settles it empirically: watch all three windows for READS while
replaying a real boot -> frontend -> Clover Forest run.

WHY THIS MOVIE. 38 of the 46 registered chunks live in LEVEL00/LEVEL.RAW -- the
frontend. E02_FreshLoad_Clover is a from-boot Interpreter recording that walks
boot -> memory-card load -> level select -> Clover Forest, so it loads the
frontend chunks, uses the menus they would belong to, and then leaves for a
gameplay level. If anything reads these tables in normal play, this run is where
it happens.

POSITIVE CONTROL, NOT JUST A NEGATIVE. The watches are armed `readwrite`, so the
loader's own stores must appear. Writes present + reads absent is evidence; both
absent means the watch (or the load) never engaged and the run proves nothing --
the tool says so rather than reporting a clean negative.

Interpreter-recorded movie, so arming at frame 0 is free (no CPU mode change).
Isolated instance, pristine disc, no writes to the guest.

Usage: python3 tools/phase4_e16_table_read_watch.py [--port 23471] [--frames 5562]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

# The registration store is `lui at,0x800A; addu at,at,marker*4; sw s3,DISP(at)`, so
# the slot for marker M is DISP_BASE + M*4 -- indexed by the RAW marker, NOT by
# (M - marker_lo). The `addiu s4,-0x30` just ahead of it is only the bounds check.
# Getting this wrong once already cost a run: watching DISP_BASE..+160 watches 160
# bytes ENTIRELY BELOW the real table, so the loader's own stores never fire and the
# window reports whatever unrelated global happens to live there.
TABLE_SPEC = [
    ("markers_0x30_0x57", 0x8009B4E8, 0x30, 0x57),
    ("markers_0x28_0x2F", 0x8009C170, 0x28, 0x2F),
    ("markers_0x58_0x5F", 0x800A6450, 0x58, 0x5F),
]
TABLES = [("%s_at_0x%08x" % (nm, dispbase + lo * 4), dispbase + lo * 4, (hi - lo + 1) * 4)
          for nm, dispbase, lo, hi in TABLE_SPEC]
# The three registration stores found statically -- the expected writers.
LOADER_STORES = {"0x8003b9cc", "0x8003bc54", "0x8003bf48"}

DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
MOVIE = ROOT / "movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json"


def drain(c, sink, seen):
    """Page the access log dry, appending new events to `sink`."""
    off = 0
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        ev = page.get("events", [])
        if not ev:
            break
        for e in ev:
            key = (e.get("frame"), e.get("cycle"), e.get("pc"),
                   e.get("address"), e.get("type"))
            if key not in seen:
                seen.add(key)
                sink.append(e)
        off += len(ev)
        if len(ev) < 10000:
            break
    return page.get("truncated", False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=23471)
    ap.add_argument("--frames", type=int, default=5562)
    ap.add_argument("--step", type=int, default=400)
    ap.add_argument("--config-dir", default="/tmp/dsrepro_e16")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_table_read_watch.json"))
    args = ap.parse_args()

    launcher = ROOT / "tools/launch_repro_playback.sh"
    print(f"launching isolated instance on port {args.port} (Interpreter)...")
    subprocess.run([str(launcher), "--config-dir", args.config_dir,
                    "--port", str(args.port), "--disc", str(DISC),
                    "--execution-mode", "Interpreter"], check=True)

    out = {
        "_comment": "Phase-4 E16: live read-watch on the three LEVEL.RAW chunk pointer "
                    "tables during a boot -> frontend -> Clover Forest replay. Answers "
                    "'who reads these tables', which is what defines the 46 registered "
                    "chunk formats. Regenerate: tools/phase4_e16_table_read_watch.py",
        "generated": str(date.today()),
        "movie": str(MOVIE.relative_to(ROOT)),
        "tables": [{"name": n, "base": "0x%08x" % b, "length": ln} for n, b, ln in TABLES],
        "slot_addressing": {
            "formula": "slot(marker) = DISP_BASE + marker*4  (RAW marker, not marker-lo)",
            "evidence": "lui at,0x800A; addu at,at,(s4<<2); sw s3,DISP(at) at "
                        "0x8003bf48 / 0x8003b9cc / 0x8003bc54; the addiu s4,-lo just "
                        "before is only the sltiu bounds check "
                        "(tools/mips_ea_window.c on the pristine EXE)",
            "spec": [{"markers": "0x%02x..0x%02x" % (lo, hi), "disp_base": "0x%08x" % db,
                      "true_window": "0x%08x..0x%08x" % (db + lo * 4, db + hi * 4 + 3)}
                     for nm, db, lo, hi in TABLE_SPEC],
        },
        "expected_writers_from_static_scan": sorted(LOADER_STORES),
    }

    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate("debugger-1000")
    c.transport.sock.settimeout(30)

    try:
        c.call("accessLog.clear", {})
        wids = []
        for name, base, ln in TABLES:
            r = c.call("accessLog.addWatch", {
                "address": "0x%08x" % base, "length": ln, "type": "readwrite",
                "label": name, "max_events": 60000})
            wids.append({"table": name, "id": r.get("id"), "watch": r})
        out["watches"] = wids
        print("armed:", json.dumps(wids)[:300])

        # movie.startPlayback plays whatever is LOADED; it takes no path. Passing the
        # path there fails with "No movie has been recorded or loaded."
        out["movie_load"] = c.call("movie.load", {"path": str(MOVIE)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        out["playback_start"] = st
        print("playback:", json.dumps(st)[:300])

        events, seen = [], set()
        truncated = False
        f = 0
        while f < args.frames:
            f = min(f + args.step, args.frames)
            c.call("movie.advanceToFrame", {"frame": f})
            truncated |= drain(c, events, seen)
            status = c.call("movie.status", {})
            print(f"  frame {status.get('playback_index')}/{args.frames} "
                  f"events={len(events)} playing={status.get('playing')}")
            if not status.get("playing"):
                out["playback_ended_early_at"] = status.get("playback_index")
                break
        truncated |= drain(c, events, seen)
        out["final_movie_status"] = c.call("movie.status", {})
        out["truncated"] = truncated
    finally:
        try:
            c.call("accessLog.clear", {})
        except Exception:
            pass
        subprocess.run([str(Path.home() / "duckstation/scripts/debugger-client/"
                             "launch_debugger_instance.sh"), "stop",
                        "--config-dir", args.config_dir], check=False)

    # ---- classify -------------------------------------------------------
    def table_of(addr):
        a = int(str(addr), 16) if isinstance(addr, str) else addr
        for n, b, ln in TABLES:
            if b <= a < b + ln:
                return n, (a - b) // 4
        return None, None

    # Event schema: {"address": hex, "type": "read"|"write", "pc", "instruction", ...}
    reads = [e for e in events if e.get("type") == "read"]
    writes = [e for e in events if e.get("type") == "write"]
    out["event_count"] = len(events)
    out["read_count"] = len(reads)
    out["write_count"] = len(writes)
    out["write_pcs"] = dict(Counter(e["pc"] for e in writes))
    out["read_pcs"] = dict(Counter(e["pc"] for e in reads))

    per = {}
    for n, b, ln in TABLES:
        w = [e for e in writes if table_of(e["address"])[0] == n]
        r = [e for e in reads if table_of(e["address"])[0] == n]
        per[n] = {
            "writes": len(w), "reads": len(r),
            "slots_written": sorted({table_of(e["address"])[1] for e in w}),
            "write_pcs": sorted({e["pc"] for e in w}),
            "write_instructions": sorted({e.get("instruction", "") for e in w}),
            "read_pcs": sorted({e["pc"] for e in r}),
            "read_instructions": sorted({e.get("instruction", "") for e in r}),
        }
    out["per_table"] = per

    unexpected_readers = sorted({e["pc"] for e in reads} - LOADER_STORES)
    out["unexpected_readers"] = unexpected_readers

    control_ok = len(writes) > 0
    out["positive_control_ok"] = control_ok
    if not control_ok:
        out["verdict"] = ("INCONCLUSIVE -- no WRITES were observed either, so the watch "
                          "or the chunk load never engaged during this run. A clean "
                          "'no reads' cannot be claimed from it.")
    elif not reads:
        out["verdict"] = ("CONFIRMED WRITE-ONLY -- the loader's registration stores fired "
                          "(positive control) and NOTHING read any of the three tables "
                          "across the whole boot -> frontend -> level-select -> Clover "
                          "Forest run. The 46 pointer-registered chunks have no consumer.")
    else:
        out["verdict"] = ("READERS FOUND -- %d reads from %s. The tables ARE consumed; "
                          "the static scan missed them."
                          % (len(reads), unexpected_readers))

    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("\n" + out["verdict"])
    print(f"writes={len(writes)} reads={len(reads)}  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
