#!/usr/bin/env python3
"""Phase-4 E02b driver: all-level collision round trip + plane census.

Per level save: extracts main RAM offline (committed catalog parser), dumps the
runtime sector table (count from [0x800822A0]) and derives the collision
staging base from sector 0's block pointer (runtime +0x10 == staging+8).
Then sweeps EVERY LEVEL*.RAW on the tree: decompresses per-chunk (committed
byte-exact codec), needle-searches the stream for a reference sector's origins
(no chunk-index or local-offset assumption), and runs the compiled C
round-trip/census tool (tools/phase4_e02_collision_roundtrip.c) on hits. A
zero-mismatch round trip PROVES the scene->file binding empirically. Scenes
with no match anywhere (city_square, bug_bar, clover_forest, the_tree) have
runtime-BUILT collision tables -- a bounded finding, not an error.

Usage: python3 tools/phase4_e02_collision_roundtrip.py \
           [--out analysis/phase4_e02_collision_roundtrip.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from level_goal_trigger_catalog import extract_main_ram, u32
import decode_level_raw

SECTOR_TABLE = 0x800A7E48
COUNT_GLOBAL = 0x800822A0


def chunk_segments(raw: bytes):
    """Decompress per chunk, returning [(start, end)] in the output stream."""
    out = bytearray()
    segs, off = [], 0
    while off + 8 <= len(raw):
        w0 = struct.unpack_from(">I", raw, off)[0]
        w1 = struct.unpack_from(">I", raw, off + 4)[0]
        if w0 == 0xFFFFFFFF:
            break
        a = len(out)
        decode_level_raw.decompress_chunk(raw[off:off + 0xE + w1], out)
        segs.append((a, len(out)))
        off += 0xE + w1
    return bytes(out), segs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e02_collision_roundtrip.json"))
    ap.add_argument("--tool", default="")
    args = ap.parse_args()

    tool = args.tool
    tmp = Path(tempfile.mkdtemp(prefix="e02rt_"))
    if not tool:
        tool = str(tmp / "e02rt")
        subprocess.run(["cc", "-O2", "-Werror", "-o", tool,
                        str(ROOT / "tools/phase4_e02_collision_roundtrip.c")], check=True)

    census = json.loads((ROOT / "analysis/phase4_e02_region_code_census.json").read_text())
    levels, failures = {}, []
    raw_cache = {}
    for label, lv in census["levels"].items():
        scene = lv["scene_word"]
        save = ROOT / lv["save"]
        meta, ram = extract_main_ram(save)
        count = u32(ram, COUNT_GLOBAL) & 0xFFFF
        table = ram[SECTOR_TABLE - 0x80000000: SECTOR_TABLE - 0x80000000 + count * 0x30]
        sec0_blk = u32(ram, SECTOR_TABLE + 0x10)
        rt_path = tmp / f"{label}_rt.bin"
        rt_path.write_bytes(struct.pack("<I", count) + table)

        # No naming-rule guess and NO container-type guess: sweep every level
        # container -- compressed .RAW (decompressed per chunk) AND uncompressed
        # .ALL/.DAT/.BIN. Restricting this to .RAW was the 2026-08-04 scope error
        # that produced a false "runtime-built" claim for four scenes.
        cands = sorted(set(
            list((ROOT / "REBUILD/files").glob("LEVEL*/*.RAW"))
            + list((ROOT / "REBUILD/files").glob("LEVEL*/*.ALL"))
            + list((ROOT / "REBUILD/files").glob("LEVEL*/*.DAT"))
            + list((ROOT / "REBUILD/files").glob("LEVEL*/*.BIN"))))
        matched, results = None, {}
        for cand in cands:
            key = str(cand)
            if key not in raw_cache:
                try:
                    if cand.suffix == ".RAW":
                        raw_cache[key] = chunk_segments(cand.read_bytes())
                    else:
                        blob = cand.read_bytes()          # uncompressed container
                        raw_cache[key] = (blob, [(0, len(blob))])
                except Exception as e:
                    raw_cache[key] = (None, str(e))
            stream, segs = raw_cache[key]
            if stream is None:
                results[cand.parent.name+"/"+cand.name] = {"error": f"decompress: {segs}"}
                continue
            # locate the source sector array by NEEDLE SEARCH: a reference
            # runtime sector's origins (>>5) must appear at rec+0x08 -- no
            # fixed chunk index or local-offset assumption.
            ref = next((i for i in range(count)
                        if all(abs(struct.unpack_from("<i", table, i * 0x30 + o)[0]) >= 64
                               for o in (0, 4, 8))), None)
            if ref is None:
                results[cand.parent.name+"/"+cand.name] = {"error": "no reference sector"}
                continue
            needle = struct.pack("<iii", *(struct.unpack_from("<i", table, ref * 0x30 + o)[0] >> 5
                                           for o in (0, 4, 8)))
            arr = None
            p = stream.find(needle)
            while p != -1:
                cand_arr = p - 8 - ref * 0x4C
                if cand_arr >= 0:
                    # Validate the REFERENCE record only: the authored prefix
                    # can be a single record (Bug Bar authors 1 of 46; the rest
                    # are runtime-registered). Candidate quality is settled by
                    # the C tool + ranking, not by this pre-filter.
                    ok = all(struct.unpack_from("<i", table, ref * 0x30 + o)[0]
                             == struct.unpack_from("<i", stream, cand_arr + ref * 0x4C + 8 + oi * 4)[0] << 5
                             for oi, o in enumerate((0, 4, 8)))
                    if ok:
                        arr = cand_arr
                        break
                p = stream.find(needle, p + 1)
            if arr is None:
                continue
            seg_start = max(a for a, b in segs if a <= arr)
            blob_path = tmp / f"{label}_{cand.parent.name}_{cand.name}.bin"
            blob_path.write_bytes(stream[seg_start:])
            # block base is container-dependent (8 = RAW chunk-32, 4 = .ALL,
            # both live-derived). Try each; keep the cleanest walk.
            best = None
            for bb in (8, 4):
                # staging = container base in RAM = sector0.blockptr - block_base
                staging_bb = (sec0_blk - bb) & 0xFFFFFFFF
                r = subprocess.run([tool, str(blob_path), str(rt_path), hex(staging_bb),
                                    str(arr - seg_start), str(bb)],
                                   capture_output=True, text=True)
                try:
                    res = json.loads(r.stdout)
                except Exception:
                    continue
                if not res.get("located"):
                    continue
                cs = res.get("census", {})
                key = (res.get("roundtrip_mismatches", 1) == 0,
                       cs.get("bad_blocks", 1) == 0,
                       cs.get("planes", 0), res.get("authored_count", 0))
                if best is None or key > best[0]:
                    best = (key, res)
            if best is None:
                continue
            results[cand.parent.name+"/"+cand.name] = best[1]
        # rank candidates: clean round trip, clean walk, most planes, most authored
        def rank(kv):
            res = kv[1]
            cs = res.get("census", {})
            return (res.get("roundtrip_mismatches", 1) == 0,
                    cs.get("bad_blocks", 1) == 0,
                    cs.get("planes", 0), res.get("authored_count", 0))
        clean = {k: v for k, v in results.items()
                 if v.get("roundtrip_mismatches") == 0
                 and v.get("census", {}).get("bad_blocks") == 0
                 and v.get("census", {}).get("planes", 0) > 0}
        if clean:
            matched = max(clean.items(), key=rank)[0]
        row = {
            "save": lv["save"], "scene": scene,
            "sector_count": count, "sector0_block_ptr": hex(sec0_blk),
            "matched_raw": matched,
            "match": results.get(matched) if matched else None,
            "candidates_tried": sorted(results),
            "all_clean_candidates": sorted(clean),
        }
        if not matched:
            failures.append(label)
            row["all_results"] = results
        levels[label] = row
        m = results.get(matched, {}) if matched else {}
        c = m.get("census", {})
        print(f"{label}: scene={scene} count={count} matched={matched} "
              f"planes={c.get('planes')} floors={c.get('floors')} "
              f"walls={c.get('walls_vertical')} ceil={c.get('ceilings')}")

    tot = {"planes": 0, "floors": 0, "walls_vertical": 0, "ceilings": 0,
           "groups": 0, "normal_len_off": 0, "bad_blocks": 0}
    f2c = {"eq_src14": 0, "nonzero": 0, "total_sectors": 0,
           "authored": 0, "runtime_extra": 0}
    for row in levels.values():
        if row["match"]:
            for k in tot:
                tot[k] += row["match"]["census"].get(k, 0)
            f2c["eq_src14"] += row["match"]["flag2c"]["eq_src14"]
            f2c["nonzero"] += row["match"]["flag2c"]["nonzero"]
            f2c["total_sectors"] += row["match"]["sector_count"]
            f2c["authored"] += row["match"]["authored_count"]
            f2c["runtime_extra"] += row["match"]["runtime_extra"]

    out = {
        "_comment": "Phase-4 E02b: all-level collision source->runtime round trip "
                    "(independent C reimplementation of FUNC_80030F60 diffed against "
                    "actual save RAM) + campaign plane census. Regenerate: "
                    "tools/phase4_e02_collision_roundtrip.py",
        "generated": str(date.today()),
        "campaign_totals": tot,
        "flag2c_summary": f2c,
        "levels": levels,
        "failing_levels": failures,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"campaign: {tot} | failing: {failures or 'none'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
