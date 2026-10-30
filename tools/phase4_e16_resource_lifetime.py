#!/usr/bin/env python3
"""Phase-4 E16: resource OWNERSHIP and LIFETIME for the registered chunk tables.

E16's `missing` lists "resource ownership + lifetimes" as untouched. The
registered-chunk tables are the sharpest place to ask it, because they hold raw
RAM pointers into decompressed chunk storage with no refcount, no size, and no
owner field -- so their lifetime is entirely a property of who zeroes them and
when.

The question this answers: **when the game leaves the frontend for a gameplay
level, are the frontend's registered pointers cleared, or left dangling into
memory that the next load reuses?** A dangling pointer here would be a real
hazard for any mod that calls the upload path outside the frontend.

Method. Replay E02_FreshLoad_Clover (from-boot, Interpreter: boot -> memory-card
load -> level select -> Clover Forest, so it crosses a load boundary), with
readwrite watches on the three occupied table windows, AND snapshot the raw
table contents every N frames. Events give the writers and their frames;
snapshots give the occupancy timeline the events alone cannot (a slot that is
never touched again looks identical to one that was never populated).

Slot addressing is DISP_BASE + marker*4 on the RAW marker -- see
tools/phase4_e16_table_read_watch.py for why that matters.

Usage: python3 tools/phase4_e16_resource_lifetime.py [--port 23472]
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

TABLE_SPEC = [
    ("markers_0x28_0x2F", 0x8009C170, 0x28, 0x2F),
    ("markers_0x30_0x57", 0x8009B4E8, 0x30, 0x57),
    ("markers_0x58_0x5F", 0x800A6450, 0x58, 0x5F),
]
TABLES = [(nm, db + lo * 4, (hi - lo + 1) * 4) for nm, db, lo, hi in TABLE_SPEC]

DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
MOVIE = ROOT / "movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json"
SCENE = 0x80082504          # committed scene id (see gap0035 / B06 notes)


def read_u32s(c, addr, count):
    hx = c.call("debugger.readMemory",
                {"address": "0x%08x" % addr, "length": count * 4})["hex"]
    b = bytes.fromhex(hx)
    return list(struct.unpack("<%dI" % count, b))


def drain(c, sink, seen):
    off = 0
    trunc = False
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        ev = page.get("events", [])
        trunc |= page.get("truncated", False)
        if not ev:
            break
        for e in ev:
            k = (e.get("frame"), e.get("cycle"), e.get("pc"), e.get("address"), e.get("type"))
            if k not in seen:
                seen.add(k)
                sink.append(e)
        off += len(ev)
        if len(ev) < 10000:
            break
    return trunc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--frames", type=int, default=5562)
    ap.add_argument("--step", type=int, default=200)
    ap.add_argument("--config-dir", default="/tmp/dsrepro_e16life")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_resource_lifetime.json"))
    args = ap.parse_args()

    print(f"launching isolated instance on port {args.port} (Interpreter)...")
    subprocess.run([str(ROOT / "tools/launch_repro_playback.sh"),
                    "--config-dir", args.config_dir, "--port", str(args.port),
                    "--disc", str(DISC), "--execution-mode", "Interpreter"], check=True)

    out = {
        "_comment": "Phase-4 E16 resource ownership/lifetime: what happens to the "
                    "registered chunk pointers across a frontend -> gameplay load. "
                    "Regenerate: tools/phase4_e16_resource_lifetime.py",
        "generated": str(date.today()),
        "movie": str(MOVIE.relative_to(ROOT)),
        "tables": [{"name": n, "base": "0x%08x" % b, "slots": ln // 4} for n, b, ln in TABLES],
    }

    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate("debugger-1000")
    c.transport.sock.settimeout(30)

    timeline, events, seen = [], [], set()
    trunc = False
    try:
        c.call("accessLog.clear", {})
        for name, base, ln in TABLES:
            c.call("accessLog.addWatch", {"address": "0x%08x" % base, "length": ln,
                                          "type": "readwrite", "label": name,
                                          "max_events": 60000})
        c.call("movie.load", {"path": str(MOVIE)})
        c.call("movie.startPlayback", {"load_start_state": True})

        f = 0
        while f < args.frames:
            f = min(f + args.step, args.frames)
            c.call("movie.advanceToFrame", {"frame": f})
            trunc |= drain(c, events, seen)
            st = c.call("movie.status", {})
            snap = {"frame": st.get("playback_index")}
            try:
                snap["scene"] = read_u32s(c, SCENE, 1)[0]
            except Exception:                          # noqa: BLE001
                snap["scene"] = None
            for name, base, ln in TABLES:
                vals = read_u32s(c, base, ln // 4)
                snap[name] = {"nonzero": sum(1 for v in vals if v),
                              "distinct": len(set(v for v in vals if v))}
            timeline.append(snap)
            if not st.get("playing"):
                break
        trunc |= drain(c, events, seen)
        out["final_status"] = c.call("movie.status", {})

        # ---- is a surviving pointer still VALID? -------------------------
        # A slot that outlives its scene is only a hazard if the memory it
        # points at has been reused. The chunk's own subtype marker is a u32 at
        # its offset 0, so a surviving slot whose target still reads back the
        # marker it was registered under is stale-but-intact; one that does not
        # is genuinely dangling.
        survivors = []
        for name, base, ln, lo in [(n, b, l, sp[2]) for (n, b, l), sp
                                   in zip(TABLES, TABLE_SPEC)]:
            vals = read_u32s(c, base, ln // 4)
            for i, v in enumerate(vals):
                if not v:
                    continue
                marker_expected = lo + i
                target_ok, first = None, None
                if 0x80000000 <= v < 0x80200000:
                    try:
                        first = read_u32s(c, v, 1)[0]
                        target_ok = (first == marker_expected)
                    except Exception:                  # noqa: BLE001
                        target_ok = None
                survivors.append({
                    "table": name, "slot": i,
                    "marker_expected": "0x%02x" % marker_expected,
                    "pointer": "0x%08x" % v,
                    "target_first_u32": None if first is None else "0x%08x" % first,
                    "marker_intact": target_ok,
                })
        out["survivors_at_end_of_run"] = survivors
        intact = [x for x in survivors if x["marker_intact"] is True]
        broken = [x for x in survivors if x["marker_intact"] is False]
        out["survivor_validity"] = {
            "surviving_slots": len(survivors),
            "marker_intact": len(intact),
            "marker_overwritten": len(broken),
        }
    finally:
        try:
            c.call("accessLog.clear", {})
        except Exception:                              # noqa: BLE001
            pass
        subprocess.run([str(Path.home() / "duckstation/scripts/debugger-client/"
                             "launch_debugger_instance.sh"), "stop",
                        "--config-dir", args.config_dir], check=False)

    out["truncated"] = trunc
    out["timeline"] = timeline
    out["event_count"] = len(events)

    # writer census, with frames -- who populates and who clears
    writes = [e for e in events if e.get("type") == "write"]
    zeroing = [e for e in writes if e.get("new_value", e.get("value")) == 0]
    setting = [e for e in writes if e.get("new_value", e.get("value")) not in (0, None)]
    out["writers"] = {
        "all": dict(Counter(e["pc"] for e in writes)),
        "zeroing_pcs": dict(Counter(e["pc"] for e in zeroing)),
        "populating_pcs": dict(Counter(e["pc"] for e in setting)),
        "first_populate_frame": min((e["frame"] for e in setting), default=None),
        "last_populate_frame": max((e["frame"] for e in setting), default=None),
        "first_zero_frame": min((e["frame"] for e in zeroing), default=None),
        "last_zero_frame": max((e["frame"] for e in zeroing), default=None),
    }

    # the lifetime question
    occ = [(t["frame"], sum(t[n]["nonzero"] for n, _, _ in TABLES)) for t in timeline]
    out["occupancy_samples"] = occ
    peak = max((n for _, n in occ), default=0)
    final = occ[-1][1] if occ else 0
    scenes = [t.get("scene") for t in timeline]
    out["scene_samples"] = scenes
    out["peak_populated_slots"] = peak
    out["final_populated_slots"] = final
    if peak == 0:
        out["verdict"] = ("INCONCLUSIVE -- no slot was ever populated in this run, so "
                          "nothing can be said about their lifetime.")
    elif final == 0:
        out["verdict"] = ("CLEARED -- the tables are populated during the frontend and "
                          "hold %d pointers at peak, but end the run at 0. The "
                          "registrations do not outlive the frontend." % peak)
    else:
        v = out.get("survivor_validity", {})
        broken = v.get("marker_overwritten")
        intact = v.get("marker_intact")
        detail = ""
        if broken is not None:
            detail = (" Of the survivors, %d still read back their own marker and %d do "
                      "not." % (intact, broken))
            if broken == 0:
                detail += (" So they are STALE BUT INTACT: the gameplay load did not "
                           "reuse that memory, and the pointers remain usable.")
            elif intact == 0:
                detail += (" So they are GENUINELY DANGLING: the gameplay load reused "
                           "that memory and the upload path would read garbage.")
        out["verdict"] = ("POINTERS SURVIVE THE SCENE THAT REGISTERED THEM -- %d of %d "
                          "slots still hold a pointer at the end of the run, after the "
                          "game left the frontend for a gameplay level.%s"
                          % (final, peak, detail))

    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("\n" + out["verdict"])
    print(f"peak={peak} final={final} events={len(events)}  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
