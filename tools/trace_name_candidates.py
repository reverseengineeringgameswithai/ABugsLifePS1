#!/usr/bin/env python3
"""u3-1 runtime-naming driver: gather execTrace evidence for unnamed resident fns.

For each `dynamic:true` candidate in analysis/naming_priority.json (grouped by its
`levels` field), load a PRISTINE level save (the MSM content-gated list —
analysis/traces/ram_usage_summary.json), arm execTrace watches on candidate entry
PCs (capture a0..a3 + ra), run frames, and aggregate per-fn evidence:
  - callers: unique `ra` values resolved to the CONTAINING NAMED function
  - args: a0..a3 classified (pointer into a named global/struct region, small int, VA)
  - hits per save
Output: analysis/traces/u3_evidence.json (resumable; one entry per candidate).

Constraints honored: throwaway instance only (never operator port 2346); watches
re-armed after every loadState; pristine saves only.

  python3 tools/trace_name_candidates.py --port 23460 --levels 1,2,3
  python3 tools/trace_name_candidates.py --port 23460            # all level buckets
"""
from __future__ import annotations
import argparse
import bisect
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / "analysis" / "naming_priority.json"
CENSUS = ROOT / "analysis" / "functions.json"
SUMMARY = ROOT / "analysis" / "traces" / "ram_usage_summary.json"
OUT = ROOT / "analysis" / "traces" / "u3_evidence.json"
SYM = ROOT / "symbols" / "re_symbols.sym"
MEMMAP = ROOT / "analysis" / "memory_map.json"

WATCHES_PER_RUN = 14          # conservative execTrace watch budget
FRAMES_PER_RUN = 900
MAX_EVENTS = 60


def load_ctx():
    fj = json.loads(CENSUS.read_text())
    spans, names = [], {}
    for f in fj["functions"]:
        if f["space"] == "resident" and f.get("range_type") in ("code", "thunk"):
            s, e = int(f["start"], 16), int(f["end"], 16)
            spans.append((s, e, f.get("name") or f["start"]))
    spans.sort()
    starts = [s for s, _, _ in spans]
    # named data regions for arg classification
    data = {}
    for ln in SYM.read_text().splitlines():
        m = re.match(r"([0-9A-Fa-f]{8})\s+(\S+)", ln)
        if m:
            data[int(m.group(1), 16)] = m.group(2)
    mm = json.loads(MEMMAP.read_text())
    for g in mm.get("bss_named_globals", []):
        data[int(g["addr"], 16)] = g["name"]
    dkeys = sorted(data)
    return spans, starts, data, dkeys


def owner_fn(va, spans, starts):
    i = bisect.bisect_right(starts, va) - 1
    if i >= 0 and spans[i][0] <= va < spans[i][1]:
        return spans[i][2]
    return None


def classify_arg(v, data, dkeys):
    if v is None:
        return None
    if isinstance(v, str):
        v = int(v, 16)
    if 0x80010000 <= v < 0x80200000:
        i = bisect.bisect_right(dkeys, v) - 1
        if i >= 0 and v - dkeys[i] <= 0x100:
            off = v - dkeys[i]
            return f"{data[dkeys[i]]}+{off:#x}" if off else data[dkeys[i]]
        return f"ptr:{v:#x}"
    if v < 0x10000:
        return f"int:{v}"
    return f"{v:#x}"


def save_for_level(lvl: int):
    """Pick a pristine per-level save for a level number."""
    cands = [f"level{lvl:02d}.sav", f"level_{lvl:02d}.sav", f"level_{lvl}.sav",
             f"LEVEL{lvl:02d}_1.sav", f"level{lvl:02d}_end_of_stage.sav"]
    pristine = {n[5:] for n in json.loads(SUMMARY.read_text())["coverage"]["state_names"]
                if n.startswith("sav__")}
    for c in cands:
        if (ROOT / c).exists() and c[:-4] in pristine:
            return ROOT / c
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=23460)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--levels", help="comma list, e.g. 1,2,3 (default: all with candidates)")
    ap.add_argument("--frames", type=int, default=FRAMES_PER_RUN)
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    sys.path.insert(0, str(Path.home() / "duckstation" / "scripts" / "debugger-client"))
    from duckstation_debug_client import DebuggerClient  # noqa: E402
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(args.timeout)

    def call(m, p=None):
        try:
            return c.call(m, p or {})
        except Exception as e:                             # noqa: BLE001
            return {"_err": str(e)[:140]}

    spans, starts, data, dkeys = load_ctx()
    prior = json.loads(PRIOR.read_text())["candidates"]
    cands = [r for r in prior if r.get("dynamic")]
    by_level = {}
    for r in cands:
        for lvl in (r.get("levels") or []):
            # levels entries look like "LEVEL01", "LEVEL00-Training"
            m = re.search(r"LEVEL(\d+)", str(lvl))
            if m:
                by_level.setdefault(int(m.group(1)), []).append(r)

    want = ([int(x) for x in args.levels.split(",")] if args.levels
            else sorted(by_level))
    evidence = json.loads(OUT.read_text()) if OUT.exists() else {}

    for lvl in want:
        rows = [r for r in by_level.get(lvl, []) if r["address"] not in evidence]
        save = save_for_level(lvl)
        if not rows or not save:
            print(f"[u3] level {lvl}: {'no candidates left' if not rows else 'NO pristine save'}")
            continue
        print(f"[u3] level {lvl}: {len(rows)} candidates via {save.name}")
        for i in range(0, len(rows), WATCHES_PER_RUN):
            batch = rows[i:i + WATCHES_PER_RUN]
            r = call("emulator.loadState", {"path": str(save)})
            if r.get("_err"):
                print("   loadState err:", r["_err"]); break
            call("emulator.setTurbo", {"enabled": True})
            call("execTrace.clear")   # server has no clearWatches; clear removes
                                      # watches+events+breakpoints (verified in the
                                      # fork's HandleExecTraceClear) so batches don't
                                      # accumulate past the watch budget
            for cand in batch:                              # re-arm AFTER loadState
                call("execTrace.addWatch", {"pc": cand["address"],
                                            "capture": ["a0", "a1", "a2", "a3", "ra"],
                                            "max_events": MAX_EVENTS})
            call("emulator.advanceFrames", {"frames": args.frames})
            evs = call("execTrace.get", {"limit": 4000}).get("events", [])
            per = {}
            for e in evs:
                pc = e.get("pc")
                regs = e.get("regs", {})
                d = per.setdefault(pc, {"hits": 0, "callers": set(), "args": []})
                d["hits"] += 1
                ra = regs.get("ra")
                if ra:
                    fn = owner_fn(int(ra, 16) if isinstance(ra, str) else ra, spans, starts)
                    if fn:
                        d["callers"].add(fn)
                if len(d["args"]) < 6:
                    d["args"].append([classify_arg(regs.get(k), data, dkeys)
                                      for k in ("a0", "a1", "a2", "a3")])
            for cand in batch:
                pc = cand["address"]
                got = per.get(pc) or per.get(pc.lower()) or per.get(pc.upper())
                evidence[pc] = {
                    "save": save.name, "level": lvl,
                    "hits": got["hits"] if got else 0,
                    "callers": sorted(got["callers"]) if got else [],
                    "args": got["args"] if got else [],
                    "size": cand["size"], "n_callers_static": cand["n_callers"],
                }
            hit = sum(1 for cand in batch if evidence[cand['address']]['hits'])
            print(f"   batch {i//WATCHES_PER_RUN}: {hit}/{len(batch)} fired")
        OUT.write_text(json.dumps(evidence, indent=1) + "\n")
    fired = sum(1 for v in evidence.values() if v["hits"])
    print(f"[u3] evidence rows: {len(evidence)} ({fired} fired) -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
