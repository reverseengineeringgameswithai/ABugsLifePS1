#!/usr/bin/env python3
"""Phase-4 E16 driver: campaign-wide LEVEL.RAW chunk-role census.

Decompresses every chunk of every LEVEL*.RAW with the committed byte-exact
codec, then classifies each chunk by its own subtype marker via the compiled C
classifier (tools/phase4_e16_chunk_classify.c). Establishes:

  * whether the marker space is CLOSED campaign-wide (no unknown markers),
  * whether the committed LEVEL01 census's 46 "likely" guesses are structurally
    correct when read from the bytes rather than inferred from load order,
  * whether every 0x101 mesh definition pairs with a 0x102 payload of the same
    object id.

Usage: python3 tools/phase4_e16_chunk_census.py [--out analysis/phase4_e16_chunk_census.json]
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import decode_level_raw as DEC


def chunks_of(raw: bytes):
    out = bytearray(); segs = []; off = 0
    while off + 8 <= len(raw):
        w0 = struct.unpack_from(">I", raw, off)[0]
        w1 = struct.unpack_from(">I", raw, off + 4)[0]
        if w0 == 0xFFFFFFFF:
            break
        a = len(out)
        DEC.decompress_chunk(raw[off:off + 0xE + w1], out)
        segs.append((a, len(out)))
        off += 0xE + w1
    return bytes(out), segs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_chunk_census.json"))
    ap.add_argument("--tool", default="")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="e16_"))
    tool = args.tool
    if not tool:
        tool = str(tmp / "e16")
        subprocess.run(["cc", "-O2", "-Werror", "-o", tool,
                        str(ROOT / "tools/phase4_e16_chunk_classify.c")], check=True)

    files = {}
    fam_hist = Counter()
    marker_hist = Counter()
    unknown = []
    pair_problems = []
    for p in sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.RAW")):
        key = f"{p.parent.name}/{p.name}"
        try:
            stream, segs = chunks_of(p.read_bytes())
        except Exception as e:
            files[key] = {"error": str(e)}; continue
        rows = []
        defs, pays = {}, {}
        for cid, (a, b) in enumerate(segs):
            blob = stream[a:b]
            cf = tmp / "c.bin"; cf.write_bytes(blob)
            r = subprocess.run([tool, str(cf), str(cid)], capture_output=True, text=True)
            try:
                res = json.loads(r.stdout)
            except Exception:
                res = {"chunk_id": cid, "ok": False}
            rows.append(res)
            if not res.get("ok"):
                continue
            fam_hist[res["family"]] += 1
            marker_hist[res["marker"]] += 1
            if res["family"] == "UNKNOWN":
                unknown.append({"file": key, **res})
            if res["family"] == "mesh_definition":
                defs.setdefault(res["second_word"], []).append(cid)
            if res["family"] == "mesh_payload":
                pays.setdefault(res["second_word"], []).append(cid)
        unmatched_defs = sorted(set(defs) - set(pays))
        unmatched_pays = sorted(set(pays) - set(defs))
        if unmatched_defs or unmatched_pays:
            pair_problems.append({"file": key, "defs_without_payload": unmatched_defs,
                                  "payloads_without_def": unmatched_pays})
        files[key] = {"chunks": len(segs), "rows": rows,
                      "mesh_object_ids": sorted(set(defs) | set(pays)),
                      "defs_without_payload": unmatched_defs,
                      "payloads_without_def": unmatched_pays}
        print(f"{key:24s} chunks={len(segs):3d} "
              f"fams={ {k: v for k, v in Counter(x.get('family') for x in rows if x.get('ok')).most_common()} }")

    out = {
        "_comment": "Phase-4 E16 campaign-wide chunk-role census. Each chunk is classified "
                    "by its OWN subtype marker (u32 at decompressed offset 0), read from the "
                    "bytes rather than inferred from load order, across every LEVEL*.RAW. "
                    "Regenerate: tools/phase4_e16_chunk_census.py",
        "generated": str(date.today()),
        "marker_space": {
            "0x0000-0x001f": "texture/VRAM page", "0x0022": "sprite/animation strip container",
            "0x0023": "seed table", "0x0024": "backdrop panorama + sky palette",
            "0x0101": "mesh definition (+4 object id, +0x0A sub-mesh count)",
            "0x0102": "mesh payload (+4 object id)",
            "0x0103": "collision planes + sky table",
            "0x0104": "collision sector-source table",
        },
        "family_histogram": dict(fam_hist),
        "marker_histogram": dict(sorted(marker_hist.items())),
        "unknown_markers": unknown,
        "mesh_pairing_problems": pair_problems,
        "files": files,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"\nfamilies: {dict(fam_hist)}")
    print(f"unknown markers: {len(unknown)} | mesh pairing problems: {len(pair_problems)}")
    print(f"wrote {args.out}")
    return 0 if not unknown else 1


if __name__ == "__main__":
    sys.exit(main())
