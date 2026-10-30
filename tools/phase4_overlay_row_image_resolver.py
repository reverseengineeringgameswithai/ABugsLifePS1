#!/usr/bin/env python3
"""Resolve ambiguous overlay-address citations to an IMAGE, per citing row.

After `phase4_overlay_keying_repair`, the ownership graph honestly reports that an overlay
address is inside a real function in many images at once. Enumerating the ambiguity was the
repair; this tool RESOLVES it where an independent axis forces the answer.

THE AXIS. The graph is per-row, and a row's own stage determines which overlay is resident
while that row's mechanic runs. Stage -> scene comes from the game's own progression table
at 0x80077FA0, read out of SCUS_942.88; scene -> blob follows the disc law
(dir = scene if scene <= 10 else scene - 10; file = LEVEL.BIN if scene <= 10 else
LEVEL1.BIN). Neither input is the artifact under review, so this is a check rather than a
restatement.

WHY IT IS TRUSTED. Six resolutions were already established INDEPENDENTLY -- by a compiled-C
byte probe, a 100.0% code-window match, a disc-side census, and a writer-set constraint.
All six are asserted as a gate below and the tool refuses to run if any stops reproducing.

WHAT IT REFUSES TO DO. A row whose stage is "all", "multiple", a range, or prose naming
more than one scene gets NO answer and is reported with its reason. Guessing an owner is
the defect this whole line of work exists to remove.

Usage: python3 tools/phase4_overlay_row_image_resolver.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TABLE_VA = 0x80077FA0

# Each entry was established by a route that never consulted the progression table.
# If any stops reproducing, the chain is wrong and this tool must not emit.
KNOWN_POSITIVES = {
    "F00_training": ("LEVEL07_LEVEL1",
                     "writer-set constraint: both stores exist in exactly 1 of 20 images "
                     "(analysis/phase4_f00_state_owner_probe.json)"),
    "F02_tunnels": ("LEVEL03_LEVEL",
                    "disc-side pin: the overlay address belonged to LEVEL03, not LEVEL02"),
    "F09_bug_bar": ("LEVEL04_LEVEL1",
                    "compiled-C probe over 21 pinned images (tools/phase4_f09_overlay_pin.c)"),
    "D18_thud": ("LEVEL04_LEVEL1", "D18's own overlay pin"),
    "F10_clover_forest": ("LEVEL07_LEVEL", "row states scene 7 (disc level07)"),
    "F11_the_tree": ("LEVEL02_LEVEL1", "100.0% code-window match to LEVEL02/LEVEL1.BIN"),
}

# Bonus stages are NOT in the progression table (it holds the 16 main stages). Their scene
# is a separately banked finding, carried here with its provenance rather than derived.
DECLARED_SCENES = {
    "bonus": (0x10, "banked F16/F17/F18: bonus scene 0x10 == LEVEL06/LEVEL1.BIN, "
                    "455 words fully accounted"),
    "training": (None, None),  # resolved through the table at ordinal 0
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def progression_table() -> list[int]:
    """The 16 stage->scene entries, read from the shipped EXE. Never hand-typed."""
    exe = ROOT / "SCUS_942.88"
    blob = exe.read_bytes()
    t_addr = struct.unpack_from("<I", blob, 0x18)[0]
    off = TABLE_VA - t_addr + 0x800
    table = [struct.unpack_from("<i", blob, off + i * 4)[0] for i in range(16)]
    if len(table) != 16 or any(v < 0 for v in table) or len(set(table)) != 16:
        raise SystemExit(f"progression table read back implausible: {table}")
    return table


def scene_to_image(scene: int) -> str:
    d = scene if scene <= 10 else scene - 10
    return f"LEVEL{d:02d}_LEVEL" + ("" if scene <= 10 else "1")


def enumerate_scenes(stages, table) -> tuple[list[int] | None, str]:
    """A row spanning SEVERAL overlays still bounds them, when its scope is enumerable.

    'stages 13-15' and prose naming two scenes cannot yield one image, but they do narrow
    19 candidates to 3 and 2. That is a real bound, not an answer, and it is reported
    separately from `resolved` so the two are never confused. Open-ended scope
    ('all', '+ others') stays unbounded.
    """
    if stages is None:
        return None, "no stage"
    low = str(stages).strip().lower()
    # ⚠️ Match open-ended scope as a WHOLE-STRING scope word or an explicit "+ others",
    # never as a bare substring. D17's prose says "confirmed for all 3 Birdnest fixtures"
    # -- that "all" is a fixture count, not scope, and a substring test wrongly discarded
    # a perfectly enumerable two-scene row.
    if low in {"all", "multiple", "frontend", "various", "any"}:
        return None, f"open-ended scope ({low!r})"
    if any(m in low for m in ("+ others", "and others", " others")):
        return None, "scope explicitly extends beyond the named stages"
    m = re.search(r"stages?\s+(\d+)\s*[-–]\s*(\d+)", low)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if 0 <= lo <= hi < 16:
            return [table[i] for i in range(lo, hi + 1)], f"stage range {lo}-{hi}"
        return None, f"stage range {lo}-{hi} outside the 16-entry table"
    scenes = sorted({int(x) for x in re.findall(r"scene\s+(\d+)", low)})
    if len(scenes) > 1:
        return scenes, f"prose enumerating {len(scenes)} scenes"
    return None, "scope not enumerable"


def parse_stage(stages) -> tuple[int | None, int | None, str]:
    """(ordinal, scene, reason). Conservative: only a SINGLE unambiguous stage resolves."""
    if stages is None:
        return None, None, "row declares no stage"
    s = str(stages).strip()
    low = s.lower()
    if low == "training":
        return 0, None, "training == progression ordinal 0"
    if low == "bonus":
        return None, DECLARED_SCENES["bonus"][0], DECLARED_SCENES["bonus"][1]
    if re.fullmatch(r"\d+", s):
        return int(s), None, "bare stage ordinal"
    m = re.fullmatch(r"stages?\s+(\d+)", low)
    if m:
        return int(m.group(1)), None, "single 'stage N'"
    # Prose: accept only when exactly ONE distinct scene number is named and no marker
    # signals extra scope. The DISTINCT-COUNT does the real work -- D17 names scenes 11
    # and 6 and is rejected by the count alone. An earlier version also rejected any
    # prose containing " and ", which threw away F10's legitimate single-scene note
    # ("= 7, and the Phase-3 scene graph labels..."); the known-positive gate caught it.
    scenes = {int(x) for x in re.findall(r"scene\s+(\d+)", low)}
    extra = [m for m in ("+ others", "others", "multiple", "and others") if m in low]
    if len(scenes) == 1 and not extra:
        return None, scenes.pop(), "prose naming exactly one scene"
    if len(scenes) == 1 and extra:
        return None, None, f"prose names one scene but signals wider scope ({extra[0]!r})"
    if len(scenes) > 1:
        return None, None, f"prose names {len(scenes)} scenes -- row spans several overlays"
    if re.search(r"stages?\s+\d+\s*[-–]\s*\d+", low):
        return None, None, "stage RANGE -- row spans several overlays"
    return None, None, f"stage scope not a single overlay ({s[:60]!r})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_overlay_row_image_resolution.json"))
    args = ap.parse_args()

    table = progression_table()
    pins = [{"path": "SCUS_942.88", "sha256": sha256_file(ROOT / "SCUS_942.88")}]

    def resolve_row(rid, stages):
        ordinal, scene, reason = parse_stage(stages)
        if ordinal is not None:
            if not 0 <= ordinal < 16:
                return None, None, None, f"ordinal {ordinal} outside the 16-entry table"
            scene = table[ordinal]
        if scene is None:
            return None, None, None, reason
        return ordinal, scene, scene_to_image(scene), reason

    # --- gate: every independently established answer must reproduce -------------
    reg_path = ROOT / "analysis/mechanics_baseline.yaml"
    pins.append({"path": "analysis/mechanics_baseline.yaml", "sha256": sha256_file(reg_path)})
    reg = {r["id"]: r for r in yaml.safe_load(reg_path.read_text())["rows"]}
    gate = []
    for rid, (expect, how) in sorted(KNOWN_POSITIVES.items()):
        _o, _s, got, why = resolve_row(rid, reg[rid].get("stages"))
        gate.append({"row": rid, "expected": expect, "derived": got,
                     "reproduces": got == expect, "independent_basis": how, "route": why})
        if got != expect:
            raise SystemExit(
                f"KNOWN-POSITIVE GATE FAILED: {rid} derives {got!r}, but {expect!r} was "
                f"established independently ({how}). The stage->scene->image chain is "
                "wrong; refusing to emit resolutions built on it.")

    # --- image extents + census attribution --------------------------------------
    d3p = ROOT / "analysis/phase4_d3_contract.json"
    pins.append({"path": "analysis/phase4_d3_contract.json", "sha256": sha256_file(d3p)})
    extents = {i["image"]: (int(i["file_va_base"], 16), i["size"])
               for i in json.loads(d3p.read_text())["inputs"]["image_identities"]}

    fnp = ROOT / "analysis/functions.json"
    pins.append({"path": "analysis/functions.json", "sha256": sha256_file(fnp)})
    census = []
    for f in json.loads(fnp.read_text())["functions"]:
        if f.get("space") != "resident" and isinstance(f.get("overlay"), str):
            census.append((int(f["start"], 16), int(f["end"], 16), f["overlay"], f.get("name")))

    ogp = ROOT / "analysis/phase3_ownership_graph.json"
    pins.append({"path": "analysis/phase3_ownership_graph.json", "sha256": sha256_file(ogp)})
    og = json.loads(ogp.read_text())

    resolved, unresolved, falsified, narrowed = [], [], [], []
    for rid, row in og["rows"].items():
        for f in row["functions"]:
            if not f.get("overlay_ambiguous"):
                continue
            a = int(f["address"], 16)
            cands = f["overlay_candidates"]
            ordinal, scene, image, reason = resolve_row(rid, reg[rid].get("stages"))
            rec = {"row": rid, "address": f["address"], "candidates": len(cands),
                   "stage_scope": reg[rid].get("stages"), "route": reason}
            if image is None:
                # no single answer -- can the scope at least BOUND the image set?
                scenes, why = enumerate_scenes(reg[rid].get("stages"), table)
                if scenes:
                    imgs = sorted({scene_to_image(sc) for sc in scenes})
                    fits = [im for im in imgs
                            if im in extents
                            and extents[im][0] <= a <= extents[im][0] + extents[im][1] - 4]
                    # ⚠️ Do NOT compare `census_candidates` with `bounded_image_count`:
                    # the first counts images with CENSUSED CODE at this address, the
                    # second counts images the stage scope allows that PHYSICALLY span it.
                    # Different bases -- treating one as a reduction of the other is the
                    # same category error that briefly produced 10 false "falsifications".
                    rec |= {"scenes": scenes, "images_from_stage_scope": imgs,
                            "bounded_images": fits,
                            "census_candidates": len(cands),
                            "bounded_image_count": len(fits),
                            "bound_route": why}
                    narrowed.append(rec)
                else:
                    unresolved.append(rec)
                continue
            rec |= {"stage_ordinal": ordinal, "scene": scene, "image": image}
            # HARD CHECK -- physical containment in the pinned blob. If the derived image
            # does not span the address, the stage mapping contradicts the bytes and the
            # resolution is rejected.
            base, size = extents.get(image, (None, None))
            rec["contained_in_blob"] = base is not None and base <= a <= base + size - 4
            if not rec["contained_in_blob"]:
                rec["failure"] = (f"derived image {image} does not physically span "
                                  f"{f['address']} -- stage mapping contradicts the bytes")
                rec["candidates_list"] = cands
                falsified.append(rec)
                continue
            # SOFT CHECK -- does the function census attribute a function here to that
            # image? ⚠️ `overlay_candidates` is built from the CENSUS, which covers only
            # 192 functions across 20 images, so its absence means "no censused code
            # there", NOT "wrong image". An earlier version treated that absence as a
            # falsification and flagged 10 resolutions -- including F00's 0x800B4A3C ->
            # LEVEL07_LEVEL1, which is byte-proved by a writer-set constraint. All 10 were
            # physically contained. Census coverage is corroboration, never refutation.
            hit = next((n for s, e, img, n in census if img == image and s <= a < e), None)
            rec["census_function_in_this_image"] = hit
            rec["corroborated_by_census"] = hit is not None
            rec["in_census_candidate_list"] = image in cands
            resolved.append(rec)

    hist = Counter(r["row"] for r in resolved)
    doc = {
        "_comment": "Ambiguous overlay-address citations resolved to an IMAGE per citing "
                    "row, via the game's own progression table (0x80077FA0) and the disc "
                    "scene->blob law. Rows whose stage scope spans several overlays get NO "
                    "answer and are listed with the reason. Regenerate: "
                    "tools/phase4_overlay_row_image_resolver.py",
        "schema": "abl-phase4-overlay-row-image-resolution/1",
        "generated": date.today().isoformat(),
        "authority": {"promotes_row_or_dimension": False, "edits_knowledge_bases": False,
                      "requires_fresh_verifier": True},
        "method": {
            "axis": "row stage -> scene (progression table, read from SCUS_942.88) -> blob",
            "scene_to_blob_law": "dir = scene if scene<=10 else scene-10; "
                                 "file = LEVEL.BIN if scene<=10 else LEVEL1.BIN",
            "progression_table": table,
            "independent_of": "analysis/phase3_ownership_graph.json (the artifact resolved)",
        },
        "known_positive_gate": gate,
        "evidence_pins": pins,
        "summary": {
            "ambiguous_citations": len(resolved) + len(unresolved) + len(falsified) + len(narrowed),
            "resolved": len(resolved),
            "falsified": len(falsified),
            "narrowed_to_a_bounded_image_set": len(narrowed),
            "unresolved_open_ended_scope": len(unresolved),
            "resolved_corroborated_by_census": sum(1 for r in resolved
                                                   if r["corroborated_by_census"]),
            "resolved_contained_in_blob": sum(1 for r in resolved if r["contained_in_blob"]),
            "resolved_without_censused_code_there": sum(1 for r in resolved
                                                        if not r["corroborated_by_census"]),
            "distinct_images_used": len({r["image"] for r in resolved}),
            "by_row": dict(sorted(hist.items())),
        },
        "resolved": resolved,
        "narrowed": narrowed,
        "falsified": falsified,
        "unresolved": unresolved,
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    s = doc["summary"]
    print(f"[row-image] known-positive gate: {len(gate)}/{len(gate)} reproduce")
    print(f"  ambiguous citations : {s['ambiguous_citations']}")
    print(f"  RESOLVED            : {s['resolved']}  "
          f"(all {s['resolved_contained_in_blob']} physically contained; "
          f"{s['resolved_corroborated_by_census']} also corroborated by the function "
          f"census, {s['resolved_without_censused_code_there']} with no censused code there)")
    print(f"  NARROWED (bounded set, not one answer) : {s['narrowed_to_a_bounded_image_set']}")
    print(f"  FALSIFIED           : {s['falsified']}")
    print(f"  unresolved (open-ended scope) : {s['unresolved_open_ended_scope']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
