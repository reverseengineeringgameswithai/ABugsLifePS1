#!/usr/bin/env python3
"""Phase-3 WP5xWP4: find the FUNCTION-POINTER FIELDS of the typed records.

The jalr pass proved 36 indirect calls go through a function pointer loaded from
a record at a fixed offset — but it could not say WHICH record. Static slicing
cannot answer that (the base register is just a pointer). Live data can:

  for every typed record, at every 4-byte offset, across every pristine anchor:
      does the value point at the ENTRY POINT of a censused code function?

A field that holds a real entry point in live instance after live instance, in
level after level, is a function-pointer field. A field that holds a code-looking
value once is noise, so a candidate must clear a hit-rate floor AND be seen in
several distinct instances.

The result is then cross-referenced with the offsets the jalr sites actually call
through, which turns "this record has a pointer here" into "this record has a
pointer here AND the game calls it".

Usage: python3 tools/phase3_fn_ptr_fields.py [--port 23473]
Output: analysis/phase3_fn_ptr_fields.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         inspect_state_before_load,
                                         select_pristine_save_anchors,
                                         verified_media_identity,
                                         write_live_evidence)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               inspect_state_before_load,
                                               select_pristine_save_anchors,
                                               verified_media_identity,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
sys.path.insert(0, str(ROOT / "tools"))

from phase3_jr_tables import find_function, load_functions, load_symbols  # noqa: E402

MIN_HITS = 8          # a candidate must hold an entry point this many times
MIN_RATE = 0.5        # ...in at least half the live instances it was seen in


def fixture_pin(*rels):
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(ap)
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient

    recs = yaml.safe_load((ROOT / "config" / "record_types.yaml").read_text())["records"]
    funcs = load_functions()
    syms = load_symbols()
    entry_points = {s: (f.get("name") or syms.get(s))
                    for s, _, f in funcs
                    if f.get("range_type") in ("code", "thunk")}

    jalr = json.loads(
        (ROOT / "analysis" / "phase3_jalr_callbacks.json").read_text())
    called_offsets = set(jalr["struct_field_offsets"])

    baseline = json.loads(
        (ROOT / "analysis" / "phase2_stage_baseline.json").read_text())
    anchors, anchor_selection = select_pristine_save_anchors(baseline)

    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)
    st = c.call("debugger.status", {})
    assert st.get("game_serial") == "SCUS-94288", st
    media_identity = verified_media_identity(c, st)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    # offset -> {"hits": n, "seen": n, "handlers": {name: count}}
    stats = {r["id"]: defaultdict(lambda: {"hits": 0, "seen": 0,
                                           "handlers": defaultdict(int)})
             for r in recs}
    used = []
    state_inspections = []
    for label, save in anchors:
        state_inspections.append(
            inspect_state_before_load(c, ROOT / save, media_identity))
        loaded = c.call("emulator.loadState",
                        {"path": str(ROOT / save),
                         "pause_after_load": True})
        assert loaded.get("loaded") and loaded.get("game_serial") == "SCUS-94288", loaded
        used.append(save)
        for rec in recs:
            rid, size, n = rec["id"], rec["size"], rec["instances"]
            buf = rd(rec["base"], size * n)
            for i in range(n):
                blob = buf[i * size:(i + 1) * size]
                if not any(blob):
                    continue                       # empty slot teaches nothing
                for off in range(0, size - 3, 4):
                    v = struct.unpack_from("<I", blob, off)[0]
                    s = stats[rid][off]
                    s["seen"] += 1
                    name = entry_points.get(v)
                    if name is not None or (v in entry_points):
                        s["hits"] += 1
                        s["handlers"][name or f"0x{v:08X}"] += 1

    out = {}
    for rec in recs:
        rid = rec["id"]
        fields = {}
        for off, s in sorted(stats[rid].items()):
            if s["hits"] >= MIN_HITS and s["seen"] and s["hits"] / s["seen"] >= MIN_RATE:
                key = f"+0x{off:02X}"
                fields[key] = {
                    "hit_rate": round(s["hits"] / s["seen"], 3),
                    "instances_seen": s["seen"],
                    "distinct_handlers": len(s["handlers"]),
                    "handlers": dict(sorted(s["handlers"].items(),
                                            key=lambda kv: -kv[1])[:6]),
                    "called_by_a_jalr_at_this_offset": key in called_offsets,
                }
        if fields:
            out[rid] = fields

    run_provenance = finish_run(
        args, generator="tools/phase3_fn_ptr_fields.py",
        anchor={"saves": used, "fixture_sha256": fixture_pin(*used),
                "selection": anchor_selection,
                "state_inspections": state_inspections,
                "media_identity": media_identity},
        timing={"anchors_loaded": len(used), "sampling": "one paused snapshot per anchor"},
    )
    doc = {
        "_comment": "Phase-3: FUNCTION-POINTER FIELDS of the typed records, found "
                    "empirically — a field that holds the ENTRY POINT of a censused "
                    "function in live instance after live instance, across levels. "
                    "Cross-referenced with the offsets the jalr sites actually call "
                    "through, which upgrades 'there is a pointer here' to 'and the "
                    "game calls it'. Regenerate: tools/phase3_fn_ptr_fields.py",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "media": {"serial": st.get("game_serial")},
        "media_identity_after_connect": media_identity,
        "anchor_selection": anchor_selection,
        "fixture_sha256": fixture_pin(*used),
        "anchors_used": len(used),
        "thresholds": {"min_hits": MIN_HITS, "min_hit_rate": MIN_RATE},
        "jalr_called_offsets": sorted(called_offsets),
        "records": out,
    }
    path = ROOT / "analysis" / "phase3_fn_ptr_fields.json"
    write_live_evidence(path, doc)
    print(f"[fnptr] {len(used)} strict-pristine anchors; "
          f"{anchor_selection['anchors_rejected']} non-pristine/uncertain refused")
    for rid, fields in out.items():
        for off, f in fields.items():
            mark = " <== a jalr calls this offset" if f["called_by_a_jalr_at_this_offset"] else ""
            print(f"  {rid:16s} {off}: rate {f['hit_rate']:.2f}, "
                  f"{f['distinct_handlers']} handlers{mark}")
            for h, n in list(f["handlers"].items())[:3]:
                print(f"        {h} x{n}")
    if not out:
        print("  no function-pointer fields cleared the thresholds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
