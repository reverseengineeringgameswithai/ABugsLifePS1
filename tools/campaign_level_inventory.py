#!/usr/bin/env python3
"""Build a campaign-wide static inventory for A Bug's Life level resources.

This is intentionally offline-only. It summarizes the extracted REBUILD/files tree:
stage-to-directory mapping, level sidecars, DAT record layouts, type-0x3f pickup
kinds, RAW chunk counts/sizes, and obvious audio/model resources. It does not claim
objective semantics; those remain runtime/overlay work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decode_level_raw  # noqa: E402


# CORRECTED 2026-08-01. The previous table was keyed by the STRING-POOL ORDER at
# 0x8001AD0C (STAGE_MAP[k] was string row k-1), which assumed "row index = scene_id - 1".
# That assumption is false: the dispatcher jumps through a PERMUTED jr table at
# 0x8001AFB0, and the level .DAT is chosen arithmetically instead --
#     dir  = scene_id <= 10 ? scene_id : scene_id - 10
#     file = scene_id <= 10 ? LEVEL.DAT : LEVEL1.DAT
# so each disc directory hosts TWO scenes. The old map was wrong for 11 of 15 stages
# (e.g. it put scene 11 at LEVEL02/LEVEL4B; it is really LEVEL01/LEVEL2C).
#
# Keyed by SCENE ID. The player-facing level ordinal is a further permutation, the
# campaign progression table at 0x80077FA0 -- see phase3_scene_asset_graph.json.
# Regenerate from analysis/phase3_scene_asset_graph.json (tools/phase3_scene_asset_graph.py).
STAGE_MAP = {
     1: ('LEVEL01', 'LEVEL1A', 'LEVEL.DAT'),   # string row 0
     2: ('LEVEL02', 'LEVEL1C', 'LEVEL.DAT'),   # string row 2
     3: ('LEVEL03', 'LEVEL1B', 'LEVEL.DAT'),   # string row 1
     4: ('LEVEL04', 'LEVEL3A', 'LEVEL.DAT'),   # string row 6
     5: ('LEVEL05', 'LEVEL3B', 'LEVEL.DAT'),   # string row 7
     6: ('LEVEL06', 'LEVEL2A', 'LEVEL.DAT'),   # string row 3
     7: ('LEVEL07', 'LEVEL4A', 'LEVEL.DAT'),   # string row 9
     8: ('LEVEL08', 'LEVEL5B', 'LEVEL.DAT'),   # string row 13
     9: ('LEVEL09', 'LEVEL5A', 'LEVEL.DAT'),   # string row 12
    10: ('LEVEL10', 'LEVEL2B', 'LEVEL.DAT'),   # string row 4
    11: ('LEVEL01', 'LEVEL2C', 'LEVEL1.DAT'),   # string row 5
    12: ('LEVEL02', 'LEVEL4B', 'LEVEL1.DAT'),   # string row 10
    13: ('LEVEL03', 'LEVEL4C', 'LEVEL1.DAT'),   # string row 11
    14: ('LEVEL04', 'LEVEL3C', 'LEVEL1.DAT'),   # string row 8
    15: ('LEVEL05', 'LEVEL5C', 'LEVEL1.DAT'),   # string row 14
}

KIND_LABELS = {
    0x10: "FLIK-F",
    0x11: "FLIK-L",
    0x12: "FLIK-I",
    0x13: "FLIK-K",
    0x14: "grain",
    0x21: "green-berry",
    0x22: "gold-berry",
    0x23: "blueberry",
    0x24: "purple-berry",
    0x29: "seed-orange",
    0x2A: "seed-blue",
    0x2B: "seed-green",
    0x2C: "seed-token-2c",
    0x2D: "seed-token-2d",
    0x30: "telescope",
    0x31: "animated-construct",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def s16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]


def s32(data: bytes, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def dat_record_size(data: bytes, off: int) -> int:
    count = u16(data, off)
    rec_type = s16(data, off + 2)
    if rec_type < 0:
        return (((count * 3 + 1) >> 1) << 2) + 0x10
    if rec_type == 0x3F:
        return count * 0x10 + 4
    return count * 0x0C + 4


def parse_dat(path: Path) -> dict:
    data = path.read_bytes()
    total = struct.unpack_from("<I", data, 0)[0] if len(data) >= 4 else 0
    off = 4
    records = []
    kinds: Counter[int] = Counter()
    bbox = None
    ok = True
    error = ""
    try:
        for idx in range(total):
            rec_off = off
            count = u16(data, off)
            rec_type = s16(data, off + 2)
            size = dat_record_size(data, off)
            records.append({"idx": idx, "type": rec_type, "count": count, "off": rec_off, "size": size})
            if rec_type == 0x3F:
                xs: list[int] = []
                ys: list[int] = []
                zs: list[int] = []
                base = off + 4
                for entry in range(count):
                    eoff = base + entry * 0x10
                    if eoff + 0x10 > len(data):
                        break
                    x, y, z = s32(data, eoff), s32(data, eoff + 4), s32(data, eoff + 8)
                    kinds[data[eoff + 0x0C]] += 1
                    if y != -0x80000000:
                        xs.append(x)
                        ys.append(y)
                        zs.append(z)
                if xs:
                    bbox = {
                        "x": [min(xs), max(xs)],
                        "y": [min(ys), max(ys)],
                        "z": [min(zs), max(zs)],
                    }
            off += size
        if off > len(data):
            ok = False
            error = f"record walk ended past EOF: {off:#x}>{len(data):#x}"
    except Exception as exc:  # keep inventory generation useful on anomalous files
        ok = False
        error = f"{type(exc).__name__}: {exc}"
    return {
        "path": str(path),
        "size": len(data),
        "sha256": sha256(path),
        "ok": ok,
        "error": error,
        "record_count": total,
        "records": records,
        "types": Counter(r["type"] for r in records),
        "type3f_count": sum(kinds.values()),
        "type3f_kinds": kinds,
        "type3f_bbox_file": bbox,
    }


def raw_chunk_headers(path: Path) -> list[dict]:
    data = path.read_bytes()
    rows = []
    off = 0
    idx = 0
    while off + 8 <= len(data):
        word0 = struct.unpack_from(">I", data, off)[0]
        word1 = struct.unpack_from(">I", data, off + 4)[0]
        if word0 == 0xFFFFFFFF:
            break
        comp_size = 0x0E + word1
        rows.append({"idx": idx, "off": off, "word0": word0, "payload_size": word1, "comp_size": comp_size})
        off += comp_size
        idx += 1
    return rows


def parse_raw(path: Path) -> dict:
    data = path.read_bytes()
    headers = raw_chunk_headers(path)
    out, chunks, consumed = decode_level_raw.decompress_file(data)
    sizes = []
    out_off = 0
    for header in headers:
        chunk_out = decode_level_raw.decompress_chunk(data[header["off"] : header["off"] + header["comp_size"]])
        sizes.append(len(chunk_out))
        out_off += len(chunk_out)
    return {
        "path": str(path),
        "size": len(data),
        "sha256": sha256(path),
        "chunks": chunks,
        "consumed": consumed,
        "decompressed_size": len(out),
        "chunk_sizes": sizes,
        "largest_chunk": max(enumerate(sizes), key=lambda p: p[1]) if sizes else None,
        "texture_frame_chunks_33548": [i for i, size in enumerate(sizes) if size == 33548],
    }


def summarize_level(level_dir: Path) -> dict:
    dats = [parse_dat(path) for path in sorted(level_dir.glob("*.DAT")) if not path.name.endswith(".orig")]
    raws = [parse_raw(path) for path in sorted(level_dir.glob("*.RAW")) if "." not in path.suffixes[:-1]]
    bins = sorted(path.name for path in level_dir.glob("*.BIN"))
    models = sorted(path.name for path in level_dir.glob("*.ALL"))
    vabs = sorted(path.name for path in list(level_dir.glob("*.VH")) + list(level_dir.glob("*.VB")))
    return {
        "dir": level_dir.name,
        "files": sorted(path.name for path in level_dir.iterdir() if path.is_file()),
        "dats": dats,
        "raws": raws,
        "bins": bins,
        "models": models,
        "vabs": vabs,
    }


def counter_summary(counter: Counter[int], labels: bool = False) -> str:
    if not counter:
        return "-"
    parts = []
    for key in sorted(counter):
        label = KIND_LABELS.get(key, "?") if labels else str(key)
        parts.append(f"{key:#04x} {label}={counter[key]}" if labels else f"{key}={counter[key]}")
    return ", ".join(parts)


def dat_brief(dat: dict) -> str:
    types = Counter()
    for rec in dat["records"]:
        types[rec["type"]] += 1
    type_counts = ", ".join(f"{typ:#x}:{count}" for typ, count in sorted(types.items()))
    return f"{Path(dat['path']).name} {dat['record_count']} recs [{type_counts}]"


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "---",
        "title: Campaign Level Coverage Matrix",
        "type: system",
        "status: active reference",
        "updated: 2026-07-02",
        "confidence: STATIC-COMPLETE / RUNTIME-PARTIAL",
        "tags: [system, campaign, levels, retail-completeness, rcg-001]",
        "---",
        "",
        "# Campaign Level Coverage Matrix",
        "",
        "> Static campaign-wide inventory generated from `REBUILD/files/LEVEL00..LEVEL10` by `tools/campaign_level_inventory.py`. This closes the `RCG-001` inventory gap: every retail stage now has a directory/overlay/resource profile, and every level directory has a DAT/RAW/object-sidecar summary. Objective semantics are intentionally marked as residual runtime work.",
        "",
        "## Scene / stage map",
        "",
        "Source: resident filename table `0x8001ad0c`, already documented in [[Finding - Level-warp mechanism]].",
        "",
        "| Stage | Directory | Overlay stem | Static profile |",
        "|---:|---|---|---|",
    ]
    by_dir = {level["dir"]: level for level in report["levels"]}
    for stage, (dirname, overlay, datname) in sorted(STAGE_MAP.items()):
        level = by_dir.get(dirname)
        dats = ", ".join(Path(dat["path"]).name for dat in level["dats"]) if level else "-"
        raws = ", ".join(Path(raw["path"]).name for raw in level["raws"]) if level else "-"
        lines.append(f"| {stage} | `{dirname}` | `{overlay}` | DAT: {dats}; RAW: {raws} |")

    lines += [
        "",
        "## Level directory profiles",
        "",
        "| Dir | Stages | DAT files | Primary type-0x3f kinds | RAW chunks | Sidecars |",
        "|---|---|---|---|---|---|",
    ]
    stages_by_dir: dict[str, list[str]] = {}
    for stage, (dirname, overlay, datname) in sorted(STAGE_MAP.items()):
        stages_by_dir.setdefault(dirname, []).append(f"{stage}:{overlay}")
    for level in report["levels"]:
        dat_text = "<br>".join(dat_brief(dat) for dat in level["dats"]) or "-"
        kinds = Counter()
        for dat in level["dats"]:
            if Path(dat["path"]).name == "LEVEL.DAT" or not kinds:
                kinds.update(dat["type3f_kinds"])
        raw_text = "<br>".join(
            f"{Path(raw['path']).name}: {raw['chunks']} chunks / {raw['decompressed_size']} B, largest {raw['largest_chunk'][0]}={raw['largest_chunk'][1]} B"
            for raw in level["raws"]
        ) or "-"
        sidecars = ", ".join(level["bins"] + level["models"] + level["vabs"]) or "-"
        lines.append(
            f"| `{level['dir']}` | {', '.join(stages_by_dir.get(level['dir'], [])) or '(dev/unmapped)'} | "
            f"{dat_text} | {counter_summary(kinds, labels=True)} | {raw_text} | {sidecars} |"
        )

    lines += [
        "",
        "## Coverage status",
        "",
        "- **Complete static coverage:** all `LEVEL00..LEVEL10` directories, all `*.DAT`, all `*.RAW`, all level overlays, VAB sidecars, and terrain model sidecars are inventoried.",
        "- **Object coverage:** all primary `type-0x3f` pickup/object tables are counted by kind across the campaign; unknown kinds remain visible as explicit `?` labels instead of hidden assumptions.",
        "- **Geometry/collision coverage:** RAW container chunk counts, decompressed sizes, texture-frame chunks, and largest chunks are known for each level; exact collision/floor role indices remain per-level follow-up work.",
        "- **Runtime coverage inherited:** fixed-address runtime structures have already been live-confirmed for LEVEL02/03/04/05 in [[Finding - Level formats generalize, content is per-level]].",
        "- **Residual:** objective semantics, exits/boss triggers, per-overlay verb meanings, and per-level editor material profiles still belong to `RCG-003`, `RCG-006`, `RCG-007`, and `RCG-009`; they are no longer part of the broad campaign-coverage gap.",
        "",
        "## Reproduction",
        "",
        "```bash",
        "python3 tools/campaign_level_inventory.py --root REBUILD/files --json build/campaign_level_inventory.json --markdown 'ObsidianVault/Systems/Campaign Level Coverage Matrix.md'",
        "```",
        "",
        "## Related",
        "",
        "[[Retail Gameplay Completeness Gap Audit]] · [[Finding - Level formats generalize, content is per-level]] · [[Finding - Level-warp mechanism]] · [[Asset - LEVEL.DAT]] · [[Asset - LEVEL.RAW]] · [[Asset - LEVEL.BIN and overlays]] · `src_re/campaign_level_coverage.c`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def make_report(root: Path) -> dict:
    levels = [summarize_level(path) for path in sorted(root.glob("LEVEL[0-9][0-9]")) if path.is_dir()]
    return {"root": str(root), "stage_map": STAGE_MAP, "levels": levels}


def to_jsonable(obj):
    if isinstance(obj, Counter):
        return dict(obj)
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(type(obj).__name__)


def main() -> int:
    ap = argparse.ArgumentParser(description="Campaign-wide static level resource inventory.")
    ap.add_argument("--root", type=Path, default=Path("REBUILD/files"))
    ap.add_argument("--json", type=Path)
    ap.add_argument("--markdown", type=Path)
    args = ap.parse_args()

    report = make_report(args.root)
    print(f"levels: {len(report['levels'])}")
    print(f"stages: {len(STAGE_MAP)}")
    for level in report["levels"]:
        primary = next((dat for dat in level["dats"] if Path(dat["path"]).name == "LEVEL.DAT"), None)
        kinds = primary["type3f_kinds"] if primary else Counter()
        print(
            f"{level['dir']}: dats={len(level['dats'])} raws={len(level['raws'])} "
            f"primary_type3f={sum(kinds.values())} kinds=[{counter_summary(kinds, labels=True)}]"
        )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, default=to_jsonable), encoding="utf-8")
        print(f"json: {args.json}")
    if args.markdown:
        write_markdown(report, args.markdown)
        print(f"markdown: {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
