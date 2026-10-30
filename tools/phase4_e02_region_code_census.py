#!/usr/bin/env python3
"""Phase-4 E02: UNFILTERED region-code census across all level saves.

The committed RCG-003 catalog (tools/level_goal_trigger_catalog.py) proved the
mechanism and scanned save-state RAM for codes 1..4 under plausibility rules.
This census removes the filter: per save, it reads the sector COUNT from the
loader's own global [gp+0x508] = 0x800822A0 (collision_source_converter canon,
LEVEL01 N=223) and dumps EVERY sector's region-code halfword at
0x800A7E48 + i*0x30 + 0x2E for i in [0, count) -- no value filter, no
plausibility heuristics. Save-state RAM extraction is reused from the
committed catalog tool (import).

Cross-check: for LEVEL01 (the level with a proven disc<->runtime mapping),
the nonzero (sector, code) pairs must contain the disc-side rows reported by
tools/edit_sector_region_code.py --list over the chunk-32-resident prefix.

Usage: python3 tools/phase4_e02_region_code_census.py \
           [--out analysis/phase4_e02_region_code_census.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from level_goal_trigger_catalog import extract_main_ram, u16, u32  # committed parser

SECTOR_TABLE = 0x800A7E48
SECTOR_STRIDE = 0x30
CODE_OFF = 0x2E
COUNT_GLOBAL = 0x800822A0          # [gp+0x508], set by FUNC_80030F60 at load
RAM_BASE = 0x80000000

SAVES = [
    ("training", "phase3_pristine_training_gameplay_i5.sav"),
    ("stage01_anthill", "level01.sav"),
    ("stage02_tunnels", "level02.sav"),
    ("stage03_council_chamber", "level03.sav"),
    ("stage04_cliffside_canyon", "level04.sav"),
    ("stage05_riverbed_run", "level05.sav"),
    ("stage06_birdnest", "level_06.sav"),
    ("stage07_city_entrance", "level_07.sav"),
    ("stage08_city_square", "level_08.sav"),
    ("stage09_bug_bar", "level_09.sav"),
    ("stage10_clover_forest", "level_10.sav"),
    ("stage11_the_tree", "level_11.sav"),
    ("stage12_battle_arena", "level_12.sav"),
    ("stage13_anthill_two", "level_13.sav"),
    ("stage14_riverbed_flight", "level_14.sav"),
    ("stage15_canyon_showdown", "level_15.sav"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e02_region_code_census.json"))
    args = ap.parse_args()

    levels, all_codes = {}, Counter()
    for label, sav in SAVES:
        path = ROOT / sav
        meta, ram = extract_main_ram(path)
        count = u16(ram, COUNT_GLOBAL)
        rows, hist = [], Counter()
        for i in range(count):
            code = u16(ram, SECTOR_TABLE + i * SECTOR_STRIDE + CODE_OFF)
            if code >= 0x8000:
                code -= 0x10000
            hist[code] += 1
            if code != 0:
                ox = u32(ram, SECTOR_TABLE + i * SECTOR_STRIDE)
                rows.append({"sector": i, "code": code,
                             "origin_x": ox - 0x100000000 if ox >= 0x80000000 else ox})
        all_codes.update(hist)
        levels[label] = {
            "save": sav,
            "save_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "scene_word": u32(ram, 0x80082504),
            "sector_count": count,
            "code_histogram": {str(k): v for k, v in sorted(hist.items())},
            "nonzero_sectors": rows,
        }
        print(f"{label}: count={count} nonzero={[(r['sector'], r['code']) for r in rows]}")

    # disc-side cross-check for LEVEL01 (proven scene->file mapping)
    disc = subprocess.run([sys.executable, str(ROOT / "tools/edit_sector_region_code.py"),
                           "--list", str(ROOT / "REBUILD/files/LEVEL01/LEVEL.RAW")],
                          capture_output=True, text=True)
    disc_rows = [(int(m.group(1)), int(m.group(2)))
                 for m in re.finditer(r"sec\s+(\d+): code=(\d+)", disc.stdout)]
    runtime_rows = [(r["sector"], r["code"]) for r in levels["stage01_anthill"]["nonzero_sectors"]]
    cross_ok = all(dr in runtime_rows for dr in disc_rows)

    out = {
        "_comment": "Phase-4 E02 unfiltered region-code census: every sector's code "
                    "halfword for the loader-declared count [0x800822A0], per level "
                    "save, offline via the committed save-state parser. Regenerate: "
                    "tools/phase4_e02_region_code_census.py",
        "generated": str(date.today()),
        "table": {"base": f"0x{SECTOR_TABLE:08x}", "stride": SECTOR_STRIDE,
                  "code_offset": CODE_OFF, "count_global": f"0x{COUNT_GLOBAL:08x}"},
        "campaign_code_histogram": {str(k): v for k, v in sorted(all_codes.items())},
        "distinct_codes_campaign": sorted(all_codes),
        "levels": levels,
        "disc_crosscheck_level01": {"disc_rows": disc_rows,
                                    "runtime_contains_all_disc_rows": cross_ok},
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"distinct codes campaign-wide: {sorted(all_codes)}")
    print(f"LEVEL01 disc crosscheck: {'OK' if cross_ok else 'MISMATCH'}")
    print(f"wrote {args.out}")
    return 0 if cross_ok else 1


if __name__ == "__main__":
    sys.exit(main())
