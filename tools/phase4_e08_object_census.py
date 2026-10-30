#!/usr/bin/env python3
"""Phase-4 E08 driver: per-level object census across every LEVEL*.DAT.

Runs the compiled C walker (tools/phase4_e08_object_census.c) over every DAT on
the tree, aggregates the placement tables (type-0x3F contact objects, pass-1
prop instances, pass-2 mesh/scale registration, pass-3 cull anchors), and
cross-checks the result against independently committed facts:

  * LEVEL01 pass-1 base 0x1504 / pass-3 base 0x3AEC / 484 records
    (src_re/prop_decor_catalog.c, tools/edit_pass1_records.py)
  * LEVEL01 type-0x3F kinds: 50 grain (0x14), 3 telescopes (0x30),
    4 FLIK letters (0x10..0x13), 4 berries (0x21..0x24)
    (tools/catalog_type3f.py identities; SYS grain/telescope canon)
  * non-empty pass-2 occurs only in the scenes E11 named
    (analysis-side check, reported not asserted)

Usage: python3 tools/phase4_e08_object_census.py [--out analysis/phase4_e08_object_census.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KIND_NAMES = {
    0x10: "FLIK letter F", 0x11: "FLIK letter L", 0x12: "FLIK letter I",
    0x13: "FLIK letter K", 0x14: "grain", 0x21: "green/homing berry",
    0x22: "gold berry", 0x23: "blue/super berry", 0x24: "purple/mega berry",
    0x29: "orange/red seed token", 0x2A: "blue seed token",
    0x2B: "green seed token", 0x2C: "seed token (2C)", 0x2D: "seed token (2D)",
    0x30: "telescope / hint gem", 0x31: "animated construct (31)",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e08_object_census.json"))
    ap.add_argument("--tool", default="")
    args = ap.parse_args()

    tool = args.tool
    if not tool:
        tmp = Path(tempfile.mkdtemp(prefix="e08_"))
        tool = str(tmp / "e08")
        subprocess.run(["cc", "-O2", "-Werror", "-o", tool,
                        str(ROOT / "tools/phase4_e08_object_census.c")], check=True)

    dats = sorted(p for p in (ROOT / "REBUILD/files").glob("LEVEL*/*.DAT")
                  if not any(s in p.name for s in (".orig", ".prechaser")))
    levels, failed = {}, []
    tot = Counter()
    kinds = Counter()
    for p in dats:
        r = subprocess.run([tool, str(p)], capture_output=True, text=True)
        try:
            res = json.loads(r.stdout)
        except Exception:
            failed.append(str(p.relative_to(ROOT))); continue
        if res.get("ok") is False:
            failed.append(str(p.relative_to(ROOT))); levels[f"{p.parent.name}/{p.name}"] = res; continue
        res["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        key = f"{p.parent.name}/{p.name}"
        levels[key] = res
        for f in ("type3f_entries", "pass1_records", "pass3_records"):
            tot[f] += res[f]
        tot["pass2_nonempty"] += 1 if res["pass2_entries"] > 0 else 0
        for k, v in res["type3f_kind_histogram"].items():
            kinds[k] += v
        print(f"{key:26s} t3f={res['type3f_entries']:4d} pass1={res['pass1_records']:5d} "
              f"pass2={res['pass2_entries']:4d} pass3={res['pass3_records']:4d}")

    # ---- cross-checks against independently committed facts ----
    l01 = levels.get("LEVEL01/LEVEL.DAT", {})
    h = l01.get("type3f_kind_histogram", {})
    checks = {
        "level01_pass1_base_0x1504": l01.get("pass1_base") == "0x1504",
        "level01_pass3_base_0x3aec": l01.get("pass3_base") == "0x3aec",
        "level01_pass1_records_484": l01.get("pass1_records") == 484,
        "level01_grain_50": h.get("0x14") == 50,
        "level01_telescopes_3": h.get("0x30") == 3,
        "level01_flik_letters_4": sum(h.get(f"0x{k:02x}", 0) for k in range(0x10, 0x14)) == 4,
        "level01_berry_types_4": sum(h.get(f"0x{k:02x}", 0) for k in range(0x21, 0x25)) == 4,
        "every_dat_parsed": not failed,
    }
    nonempty_p2 = sorted(k for k, v in levels.items() if v.get("pass2_entries", 0) > 0)

    out = {
        "_comment": "Phase-4 E08 per-level object census. Every placement table is walked "
                    "exactly as the retail parser does, with each table's base DERIVED per "
                    "file (no LEVEL01 constants assumed). Regenerate: "
                    "tools/phase4_e08_object_census.py",
        "generated": str(date.today()),
        "kind_names": {f"0x{k:02x}": v for k, v in KIND_NAMES.items()},
        "campaign_totals": dict(tot),
        "campaign_kind_histogram": dict(sorted(kinds.items())),
        "unknown_kinds": sorted(k for k in kinds if int(k, 16) not in KIND_NAMES),
        "pass2_nonempty_files": nonempty_p2,
        "crosschecks": checks,
        "levels": levels,
        "failed": failed,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"\ncampaign: {dict(tot)}")
    print(f"crosschecks: {checks}")
    print(f"unknown kinds: {out['unknown_kinds']}")
    print(f"wrote {args.out}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
