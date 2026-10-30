#!/usr/bin/env python3
"""Phase-4 E02/F01: DISC-SIDE region-code census for all 16 campaign scenes.

The runtime census (`tools/phase4_e02_region_code_census.py`) reads the codes out
of save-state RAM at 0x800A7E48 + i*0x30 + 0x2E. Its disc cross-check covered
**LEVEL01 only**, because `tools/edit_sector_region_code.py` hardcodes LEVEL01's
chunk-32 local offset 0x36570 -- pointed at any other level it walks the wrong
bytes and reports nothing. That silence was a tooling artifact, never evidence.

This tool removes the hardcode. Per scene it re-locates the authored sector
source array in its own container (the binding proved by E02's collision round
trip, `analysis/phase4_e02_collision_roundtrip.json`, 16/16 exact), reads the
authored region code at **src+0x2C** straight from the container bytes, and
diffs it against the runtime table's **+0x2E** for the same sector index.

Two container families, both live-derived (E02 2026-08-04): `.RAW` chunk data
(block base 8) and `.ALL` (block base 4). The array can span chunk 32 into 33,
so the `.RAW` stream is decompressed CONTIGUOUSLY and indexed globally; the
per-chunk (index, local offset) is reported afterwards for edit tooling.

Not circular: the array alignment is fixed by the sector ORIGINS (+0x08 words),
never by the region code at +0x2C. The code field is read only after the
alignment is settled, so agreement is a real check of the converter law
src+0x2C -> rt+0x2E rather than a restatement of it.

Scope: the 16 scenes reachable through the campaign progression table
0x80077FA0. Scene 16 (map/results, force-flag only) has no save anchor and is
NOT covered -- see `scene_universe` in the output.

Usage: python3 tools/phase4_e02_disc_region_code_census.py \
           [--out analysis/phase4_e02_disc_region_code_census.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from level_goal_trigger_catalog import extract_main_ram, u32  # committed parser
from phase4_e02_collision_roundtrip import chunk_segments      # committed codec walk

SECTOR_TABLE = 0x800A7E48
RT_STRIDE = 0x30
RT_CODE_OFF = 0x2E
SRC_STRIDE = 0x4C
SRC_CODE_OFF = 0x2C
SRC_ORIGIN_OFF = 0x08
COUNT_GLOBAL = 0x800822A0

# Valid scene ids are 1..17 (0x8003CF84: `addiu v1,s4,-1` / `sltiu v0,v1,17`).
# The campaign progression table 0x80077FA0 lists the 16 that are reachable in
# ordinal order; scene 16 is absent from it and is forced only by [0x8008225C].
SCENE_PROGRESSION = [17, 1, 3, 2, 6, 10, 11, 4, 5, 14, 7, 12, 13, 9, 8, 15]
SCENE_VALID_RANGE = list(range(1, 18))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_container(path: Path):
    """Return (contiguous stream, [(start, end)] per chunk). .ALL/.DAT/.BIN are flat."""
    if path.suffix == ".RAW":
        return chunk_segments(path.read_bytes())
    blob = path.read_bytes()
    return blob, [(0, len(blob))]


def locate_array(stream: bytes, table: bytes, count: int):
    """Find the authored source array by matching a reference sector's ORIGINS.

    Same needle as the committed round trip: runtime origin words are the source
    words << 5, stored at src+0x08. Returns the stream offset of record 0.
    """
    ref = next((i for i in range(count)
                if all(abs(struct.unpack_from("<i", table, i * RT_STRIDE + o)[0]) >= 64
                       for o in (0, 4, 8))), None)
    if ref is None:
        return None, None
    needle = struct.pack("<iii", *(struct.unpack_from("<i", table, ref * RT_STRIDE + o)[0] >> 5
                                   for o in (0, 4, 8)))
    p = stream.find(needle)
    while p != -1:
        arr = p - SRC_ORIGIN_OFF - ref * SRC_STRIDE
        if arr >= 0:
            ok = all(struct.unpack_from("<i", table, ref * RT_STRIDE + o)[0]
                     == struct.unpack_from("<i", stream, arr + ref * SRC_STRIDE
                                           + SRC_ORIGIN_OFF + oi * 4)[0] << 5
                     for oi, o in enumerate((0, 4, 8)))
            if ok:
                return arr, ref
        p = stream.find(needle, p + 1)
    return None, ref


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e02_disc_region_code_census.json"))
    args = ap.parse_args()

    runtime = json.loads((ROOT / "analysis/phase4_e02_region_code_census.json").read_text())
    roundtrip = json.loads((ROOT / "analysis/phase4_e02_collision_roundtrip.json").read_text())

    levels, disc_hist, failures, disagreements = {}, Counter(), [], []
    for label, rt_lv in runtime["levels"].items():
        loc = roundtrip["levels"][label]
        container = ROOT / "REBUILD/files" / loc["matched_raw"]
        authored = loc["match"]["authored_count"]

        meta, ram = extract_main_ram(ROOT / rt_lv["save"])
        count = u32(ram, COUNT_GLOBAL) & 0xFFFF
        table = ram[SECTOR_TABLE - 0x80000000: SECTOR_TABLE - 0x80000000 + count * RT_STRIDE]

        stream, segs = load_container(container)
        arr, ref = locate_array(stream, table, count)
        if arr is None:
            failures.append(label)
            levels[label] = {"scene": rt_lv["scene_word"], "container": loc["matched_raw"],
                             "located": False, "error": "source array not located"}
            continue

        chunk_idx = max(i for i, (a, b) in enumerate(segs) if a <= arr)
        local = arr - segs[chunk_idx][0]

        rows, hist, mism = [], Counter(), []
        for i in range(authored):
            code = struct.unpack_from("<i", stream, arr + i * SRC_STRIDE + SRC_CODE_OFF)[0]
            rt = struct.unpack_from("<h", table, i * RT_STRIDE + RT_CODE_OFF)[0]
            hist[code] += 1
            if code != rt:
                mism.append({"sector": i, "disc_code": code, "runtime_code": rt})
            if code != 0:
                off = arr + i * SRC_STRIDE + SRC_CODE_OFF
                ox, oy, oz = struct.unpack_from("<iii", stream, arr + i * SRC_STRIDE + SRC_ORIGIN_OFF)
                rows.append({
                    "sector": i, "code": code, "runtime_code": rt,
                    "runtime_origin": [ox << 5, oy << 5, oz << 5],
                    "stream_offset": off,
                    "chunk": chunk_idx, "chunk_local_offset": hex(off - segs[chunk_idx][0]),
                })
        disc_hist.update(hist)

        # Any nonzero runtime code at an index beyond the authored prefix would be
        # a code the disc census structurally cannot see. Enumerate, don't assume.
        beyond = [{"sector": r["sector"], "code": r["code"]}
                  for r in rt_lv["nonzero_sectors"] if r["sector"] >= authored]
        if mism or beyond:
            disagreements.append({"level": label, "mismatches": mism, "runtime_only": beyond})

        levels[label] = {
            "scene": rt_lv["scene_word"],
            "container": loc["matched_raw"],
            "container_sha256": sha256(container),
            "save": rt_lv["save"], "save_sha256": rt_lv["save_sha256"],
            "located": True,
            "array_stream_offset": arr,
            "array_chunk": chunk_idx,
            "array_chunk_local_offset": hex(local),
            "reference_sector": ref,
            "authored_sectors": authored,
            "runtime_sectors": count,
            "runtime_registered_tail": count - authored,
            "code_histogram": {str(k): v for k, v in sorted(hist.items())},
            "nonzero_sectors": rows,
            "disc_vs_runtime_mismatches": mism,
            "runtime_nonzero_beyond_authored": beyond,
        }
        print(f"{label:26s} scene={rt_lv['scene_word']:2d} {loc['matched_raw']:22s} "
              f"chunk={chunk_idx:2d} local={hex(local):>9s} authored={authored:4d} "
              f"nonzero={[(r['sector'], r['code']) for r in rows]}")

    out = {
        "_comment": "Phase-4 E02/F01 DISC-SIDE region-code census: authored src+0x2C read "
                    "straight from each scene's own container, diffed against the runtime "
                    "table's +0x2E. Removes edit_sector_region_code.py's hardcoded LEVEL01 "
                    "offset, under which every other level silently reported nothing. "
                    "Regenerate: tools/phase4_e02_disc_region_code_census.py",
        "generated": str(date.today()),
        "source_record": {"stride": SRC_STRIDE, "code_offset": SRC_CODE_OFF,
                          "origin_offset": SRC_ORIGIN_OFF},
        "runtime_record": {"base": f"0x{SECTOR_TABLE:08x}", "stride": RT_STRIDE,
                           "code_offset": RT_CODE_OFF, "count_global": f"0x{COUNT_GLOBAL:08x}"},
        "converter_law": "FUNC_80030F60 writers 0x80030F94 / 0x80031264: rt+0x2E <- src+0x2C",
        "scene_universe": {
            "valid_scene_ids": SCENE_VALID_RANGE,
            "campaign_progression_table": {"address": "0x80077FA0", "scenes": SCENE_PROGRESSION},
            "covered_scenes": sorted({lv["scene"] for lv in levels.values()}),
            "uncovered_scenes": sorted(set(SCENE_VALID_RANGE)
                                       - {lv["scene"] for lv in levels.values()}),
            "uncovered_note": "Scene 16 is absent from the progression table and is reached "
                              "only by the force flag [0x8008225C] (map/results); it has no "
                              "save anchor, so neither census covers it.",
        },
        "campaign_disc_histogram": {str(k): v for k, v in sorted(disc_hist.items())},
        "distinct_codes_disc": sorted(disc_hist),
        "distinct_codes_runtime": runtime["distinct_codes_campaign"],
        "agreement": {
            "levels_located": sum(1 for v in levels.values() if v.get("located")),
            "levels_total": len(levels),
            "levels_with_disagreement": [d["level"] for d in disagreements],
            "disagreements": disagreements,
            "authored_sectors_compared": sum(v.get("authored_sectors", 0) for v in levels.values()),
        },
        "levels": levels,
        "failures": failures,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")

    print(f"\ndisc histogram      : {dict(sorted(disc_hist.items()))}")
    print(f"distinct codes disc : {sorted(disc_hist)}")
    print(f"located             : {out['agreement']['levels_located']}/{len(levels)}")
    print(f"disagreements       : {len(disagreements)}")
    print(f"wrote {args.out}")
    return 0 if not failures and not disagreements else 1


if __name__ == "__main__":
    sys.exit(main())
