#!/usr/bin/env python3
"""F02 Tunnels: who spawns the contact objects? Trace the allocator's callers.

WHY NOT RAM DIFFING
-------------------
tools/phase4_f02_debris_capture.py sampled the contact pool across the any%
Tunnels run and found all 64 slots churning with balanced up/down Y motion and
~2 million units of travel each. That is not 64 falling objects -- it is the
ROUND-ROBIN CURSOR (0x8008234C) recycling slots, so a slot is not an object and
per-slot tracking is meaningless. Diffing the pool cannot identify a spawner.

The allocator can. Canon names `contact_alloc` at 0x80059E44 and the explicit
constructor path at 0x8005A0E0; both pre-increment the cursor and wrap modulo 64.
Watching them with `ra` captured gives the CALLER of every contact spawn in the
stage -- which is the "bind them to their spawner" half of the row item, directly.

Replay is 60 Hz (debugger.resume + poll), never movie.advanceToFrame.

Usage: python3 tools/phase4_f02_spawner_trace.py
"""
from __future__ import annotations

import argparse, json, subprocess, sys, time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
ALLOC = {0x80059E44: "contact_alloc", 0x8005A0E0: "explicit_constructor"}
# Canon: contact_walker 0x800586B0 scans all 64 slots; its action dispatcher at
# 0x8001B570 has 117 actions. Which actions fire in Tunnels IS the damage-class
# half of the row item, so it is armed in the same pass -- non-halting
# instrumentation is free on an Interpreter-recorded movie (CLAUDE.md).
DISPATCH = {0x8001B570: "contact_action_dispatch", 0x800586B0: "contact_walker"}
CAPTURE = ["ra", "a0", "a1", "a2", "a3"]
PLAYER = 0x800A6500


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--movie", default="movies/Phase4/Interpreter/Any% Runs/LEVEL02_Tunnels.movie.json")
    ap.add_argument("--port", type=int, default=23495)
    ap.add_argument("--config-dir", default="/tmp/dsrepro_f02e")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_f02_spawner_trace.json"))
    args = ap.parse_args()

    subprocess.run([str(ROOT / "tools/launch_repro_playback.sh"),
                    "--config-dir", args.config_dir, "--port", str(args.port),
                    "--disc", str(DISC), "--execution-mode", "Interpreter"], check=True)
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate("debugger-1000")
    c.transport.sock.settimeout(900)

    events, ids = [], {}
    try:
        c.call("movie.load", {"path": str(ROOT / args.movie)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        frames = st.get("frame_count") or 0
        c.call("execTrace.clear", {})
        for pc, label in {**ALLOC, **DISPATCH}.items():
            r = c.call("execTrace.addWatch",
                       {"pc": "0x%08x" % pc, "label": label,
                        "capture": CAPTURE, "max_events": 60000})
            ids[r.get("watch_id")] = label
        p0 = c.call("debugger.readMemory", {"address": "0x%08x" % PLAYER, "length": 16})["hex"]
        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        while time.time() - began < 90 + frames / 30.0:
            time.sleep(1.5)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception:                                   # noqa: BLE001
                idx = last
            if idx == last:
                stalls += 1
                if stalls >= 8:
                    break
            else:
                stalls = 0
            last = idx
        p1 = c.call("debugger.readMemory", {"address": "0x%08x" % PLAYER, "length": 16})["hex"]
        for wid, label in ids.items():
            try:
                w = c.call("execTrace.get", {"watch_id": wid})
                for e in (w.get("events") or []):
                    e["_watch"] = label
                    events.append(e)
            except Exception as ex:                             # noqa: BLE001
                print("  query failed", label, str(ex)[:60])
    finally:
        try:
            c.call("execTrace.clear", {})
        except Exception:                                       # noqa: BLE001
            pass
        subprocess.run([str(Path.home() / "duckstation/scripts/debugger-client/"
                             "launch_debugger_instance.sh"), "stop",
                        "--config-dir", args.config_dir], check=False)

    guest_live = p0 != p1
    by_watch = Counter(e["_watch"] for e in events)
    truncated = {w: n for w, n in by_watch.items() if n >= 60000}
    callers = Counter()
    # The register block is "regs" -- not "registers", not "capture". Guessing the
    # key produced 4,466 captured calls and 0 callers, and the verdict still said
    # "CAPTURED ... from 0 distinct callers", which is incoherent. The guard below
    # now requires callers before claiming a capture.
    for e in events:
        regs = e.get("regs") or {}
        ra = regs.get("ra") if isinstance(regs, dict) else None
        if ra:
            callers[str(ra)] += 1

    out = {
        "_comment": "F02 Tunnels: callers of the contact allocator during the any% run. "
                    "Regenerate: tools/phase4_f02_spawner_trace.py",
        "generated": str(date.today()),
        "row_id": "F02_tunnels",
        "movie": args.movie,
        "watched": {"0x%08X" % k: v for k, v in ALLOC.items()},
        "control_guest_live": guest_live,
        "events": len(events),
        "events_by_watch": dict(by_watch),
        "watches_at_cap": truncated,
        "distinct_callers": len(callers),
        "caller_histogram": dict(callers.most_common(30)),
        "why_not_ram_diffing": ("The contact pool is round-robin recycled by the cursor at "
                                "0x8008234C, so a slot is not an object: sampling the pool "
                                "showed all 64 slots churning with balanced up/down motion. "
                                "The allocator's callers identify spawners; slot diffs cannot."),
        "caller_by_watch": {w: dict(Counter(
            (e.get("regs") or {}).get("ra") for e in events
            if e["_watch"] == w and (e.get("regs") or {}).get("ra")).most_common(12))
            for w in by_watch},
        # PERSIST EVERY CALL SIGNATURE, not a sample. The previous version kept 20 of
        # 4,466 events, so the arguments needed to split the callers were not on
        # disk and the next step looked like it needed another movie. It did not.
        "call_signatures": [
            {"watch": w, "ra": ra, "a0": a0, "a1": a1, "a2": a2, "a3": a3, "count": n}
            for (w, ra, a0, a1, a2, a3), n in Counter(
                (e["_watch"],
                 (e.get("regs") or {}).get("ra"), (e.get("regs") or {}).get("a0"),
                 (e.get("regs") or {}).get("a1"), (e.get("regs") or {}).get("a2"),
                 (e.get("regs") or {}).get("a3"))
                for e in events).most_common()],
        "per_caller_arg_domains": {
            ra: {
                "calls": n,
                "watches": sorted({e["_watch"] for e in events
                                   if (e.get("regs") or {}).get("ra") == ra}),
                "distinct_a0": len({(e.get("regs") or {}).get("a0") for e in events
                                    if (e.get("regs") or {}).get("ra") == ra}),
                "distinct_a1": len({(e.get("regs") or {}).get("a1") for e in events
                                    if (e.get("regs") or {}).get("ra") == ra}),
                "a3_values": sorted({(e.get("regs") or {}).get("a3") for e in events
                                     if (e.get("regs") or {}).get("ra") == ra})[:8],
            } for ra, n in callers.most_common(40)},
        "sample_events": events[:20],
        "verdict": None,
    }
    if not guest_live:
        out["verdict"] = "INCONCLUSIVE -- player block never changed; the replay did not run."
    elif events and not callers:
        out["verdict"] = ("BROKEN CAPTURE -- %d allocator calls recorded but no `ra` was "
                          "extracted, so no spawner can be named. Check the register key in "
                          "the event payload." % len(events))
    elif not events:
        out["verdict"] = ("NO ALLOCATOR CALLS -- the guest ran but neither 0x80059E44 nor "
                          "0x8005A0E0 fired. Stage-2 contact objects are therefore NOT "
                          "created through the runtime allocator during play; they are "
                          "placed at load. That is a finding, not a failure.")
    else:
        out["verdict"] = ("CAPTURED -- %d allocator calls from %d distinct callers during the "
                          "Tunnels run. Each caller is a spawner candidate for the row's "
                          "'bind them to their spawner' item."
                          % (len(events), len(callers)))
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"guest live {guest_live}  events {len(events)}  by watch {dict(by_watch)}")
    print(f"distinct callers: {len(callers)}")
    for ra, n in callers.most_common(12):
        print("   ra %s x%d" % (ra, n))
    print("\n" + out["verdict"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
