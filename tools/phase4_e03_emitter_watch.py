#!/usr/bin/env python3
"""Phase-4 E03: OT emitter roster via a primitive-cursor write-watch.

Every OT packet allocator bumps the primitive cursor [0x8008249C] (batch-wise:
one store per emitter batch), and frame_present re-inits it plus the depth-
bucket base [0x80082230] per rendered frame. Watching those two words for a few
frames therefore enumerates EVERY packet emitter with its exact store site --
a 4-byte watch instead of a 28 KB region trace.

Usage: python3 tools/phase4_e03_emitter_watch.py --port 23701 \
           [--out analysis/phase4_e03_emitter_roster.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
sys.path.insert(0, str(ROOT / "tools"))

from live_session_provenance import (inspect_state_before_load,
                                     verified_media_identity)

PRIM_CURSOR = 0x8008249C
BUCKET_BASE = 0x80082230

SAVES = [
    ("normal_gameplay", "level02.sav"),
    ("boss_showdown", "level_15.sav"),
    ("training", "phase3_pristine_training_gameplay_i5.sav"),
]


def load_symbols():
    syms = {}
    for line in (ROOT / "symbols/re_symbols.sym").read_text().splitlines():
        m = re.match(r"([0-9A-Fa-f]{8})\s+(\S+)", line)
        if m:
            syms[int(m.group(1), 16)] = m.group(2)
    keys = sorted(syms)
    def owner(pc):
        import bisect
        i = bisect.bisect_right(keys, pc) - 1
        return {"symbol": syms[keys[i]], "symbol_addr": f"0x{keys[i]:08x}"} if i >= 0 else {}
    return owner


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=23701)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--frames", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e03_emitter_roster.json"))
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(60)

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)
    owner = load_symbols()

    scenes = {}
    for label, sav in SAVES:
        path = ROOT / sav
        inspect_state_before_load(c, path, media_identity)
        r = c.call("emulator.loadState", {"path": str(path), "pause_after_load": True})
        assert r.get("loaded"), r
        c.call("emulator.advanceFrames", {"frames": 30})
        # watches are cleared by loadState -- arm after
        c.call("accessLog.addWatch", {"address": f"0x{PRIM_CURSOR:08x}", "length": 4,
                                      "type": "write", "label": "prim_cursor",
                                      "max_events": 20000})
        c.call("accessLog.addWatch", {"address": f"0x{BUCKET_BASE:08x}", "length": 4,
                                      "type": "write", "label": "bucket_base",
                                      "max_events": 2000})
        c.call("emulator.advanceFrames", {"frames": args.frames})
        log = c.call("accessLog.get", {"limit": 4096})
        c.call("accessLog.clear", {})

        sites = Counter()
        for e in log["events"]:
            sites[(e["instruction_pc"], e["address"], e["instruction"])] += 1
        rows = []
        for (pc, addr, ins), n in sorted(sites.items(), key=lambda kv: -kv[1]):
            rows.append({"store_pc": pc, "target": addr, "instruction": ins,
                         "batches": n, **owner(int(pc, 16))})
        scenes[label] = {
            "save": sav,
            "save_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "vsync_frames_watched": args.frames,
            "events_total": log["total"], "truncated": log["truncated"],
            "sites": rows,
        }
        print(f"{label}: {log['total']} events, {len(rows)} distinct store sites")

    out = {
        "_comment": "Phase-4 E03 OT emitter roster: every writer of the primitive "
                    "cursor [0x8008249C] and depth-bucket base [0x80082230] over a "
                    "few frames, per scene class, symbol-joined. Counts are BATCHES "
                    "(one cursor store per emitter batch), not primitives. "
                    "Regenerate: tools/phase4_e03_emitter_watch.py",
        "generated": str(date.today()),
        "media_identity": media_identity,
        "prim_cursor": f"0x{PRIM_CURSOR:08x}",
        "bucket_base": f"0x{BUCKET_BASE:08x}",
        "scenes": scenes,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
