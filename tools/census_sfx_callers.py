#!/usr/bin/env python3
"""Resolve the sound id at every caller of the audio entry points.

WHY THIS EXISTS
---------------
"The B08 grant plays sound X" is only meaningful once you know whether X is *its* sound
or a shared one. The bubble grant calls `sfx_dispatch(-3)`, and negative ids index a
variant/round-robin pool -- so the id alone cannot tell you whether the sound belongs to
the bubble or to every collectible in the game. That needs a caller census.

Most call sites put a literal in the delay slot (`addiu a0, zero, 65`), but a
substantial minority compute the id, so a grep for the literal form silently
under-reports. This runs the same alias-aware value analysis as tools/census_address.py
and resolves `a0` at every call site, computed or not.

METHOD
------
`census_address.analyse(..., call_targets=..., calls_out=...)` snapshots a0..a3 AFTER the
delay slot at each `jal` to a named callee -- the same interprocedural argument machinery
the address census already needs. Unresolved arguments are reported as null rather than
omitted, so the residual is visible.

USAGE
    tools/census_sfx_callers.py --json analysis/sfx_caller_census.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "census_address", Path(__file__).with_name("census_address.py"))
_ca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ca)

# The two audio entry points, per ObsidianVault/Canon/Systems/SYS_sfx_system.md.
ENTRIES = {
    0x80050994: "sfx_dispatch",   # a0 = sound id; >=0 real pool, <0 variant pool
    0x8005044C: "play_sound",     # higher-level effect+cue spawner (id + context ptr)
}

# Sites this campaign cares about, so the report says what they are rather than
# leaving the reader to cross-reference.
OF_INTEREST = {
    "0x800588C0": "B06 invincibility grant -- sfx 65",
    "0x80058998": "B08 bubble grant -- sfx -3",
    "0x8004A820": "shared: every intercepted contact -- sfx 14",
    "0x800588D4": "B09 super jump grant -- sfx 75",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", type=Path, default=ROOT / "REBUILD" / "files" / "SCUS_942.88")
    ap.add_argument("--functions", type=Path, default=ROOT / "analysis/functions.json")
    ap.add_argument("--json", type=Path, default=ROOT / "analysis/sfx_caller_census.json")
    args = ap.parse_args()

    img = _ca.Image(args.exe, args.functions)
    calls: list = []
    # targets={} -> no address hits wanted; we only want the call-argument capture
    _ca.analyse(img, set(), call_targets=set(ENTRIES), calls_out=calls)

    seen, by_entry = {}, defaultdict(list)
    for c in calls:
        seen.setdefault(c["pc"], c)
    for c in sorted(seen.values(), key=lambda x: x["pc"]):
        callee = int(c["callee"], 16)
        a0 = c["args"].get("a0")
        rec = {"pc": c["pc"], "function": c["function"],
               "sound_id": (a0[0] if a0 and len(a0) == 1 else a0),
               "resolved": a0 is not None}
        if c["pc"] in OF_INTEREST:
            rec["note"] = OF_INTEREST[c["pc"]]
        by_entry[ENTRIES[callee]].append(rec)

    out = {
        "_comment": (
            "Sound id resolved at every caller of sfx_dispatch / play_sound, by the "
            "alias-aware value analysis in tools/census_address.py (arguments snapshotted "
            "AFTER the delay slot). `resolved: false` means the id is not derivable from "
            "the instruction stream -- reported, not omitted. Regenerate: "
            "tools/census_sfx_callers.py"),
        "entries": {hex(k): v for k, v in ENTRIES.items()},
    }
    for name, recs in by_entry.items():
        ids = Counter(r["sound_id"] for r in recs
                      if r["resolved"] and isinstance(r["sound_id"], int))
        shared = {str(i): [r["pc"] for r in recs if r["sound_id"] == i]
                  for i, n in ids.items() if n > 1}
        unique = sorted(str(i) for i, n in ids.items() if n == 1)
        out[name] = {
            "call_sites": len(recs),
            "resolved": sum(1 for r in recs if r["resolved"]),
            "unresolved": sum(1 for r in recs if not r["resolved"]),
            "ids_by_frequency": {str(i): n for i, n in ids.most_common()},
            "shared_ids": shared,
            "unique_to_one_site": unique,
            "sites": recs,
        }
        print("%s: %d sites, %d resolved, %d unresolved" %
              (name, len(recs), out[name]["resolved"], out[name]["unresolved"]))
        for i, n in ids.most_common():
            tag = " SHARED" if n > 1 else ""
            print("   id %-6s x%d%s" % (i, n, tag))

    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
