#!/usr/bin/env python3
"""Phase-3 gate bullet 3: the overlay boundary map (facts joined, first time).

Dispatch is fully enumerated (234 sites). The other half of bullet 3 — overlay
boundaries — has its facts scattered across FOUR artifacts that were never joined:

  config/overlays.yml                  region bases + shared $gp
  tools/build_baselines.json           hash-pinned overlay sizes => RAM range
  analysis/functions.json              resident_overlay_entry_targets (every
                                       overlay entry VA + its resident callers)
                                       and per-function `overlay` tags
  analysis/phase3_scene_asset_graph.json  which SCENE loads which overlay

This joins them into one artifact: per overlay, its RAM range, function count,
entry points (with resident callers), and the scenes that load it.

THE BOUNDARY FACT A MOD NEEDS AND DOES NOT HAVE: overlays REUSE the same RAM
window (region A = per-level LEVEL*.BIN swap buffer @ 0x800B39A0, region B =
MEMORY.BIN @ 0x800B5788). So an address in that window is only meaningful GIVEN
which overlay is loaded — and mod/hook_caves.yaml is resident-EXE only, with no
overlay-aware bounds check. A cave that assumes a fixed meaning for an overlay-
window address is wrong the moment a different level loads.

Usage: python3 tools/phase3_overlay_map.py
Output: analysis/phase3_overlay_map.json
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def fixture_pin(*rels):
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def as_int(v):
    return int(v, 16) if isinstance(v, str) else v


def main() -> int:
    overlays_yml = yaml.safe_load((ROOT / "config" / "overlays.yml").read_text())
    baselines = json.loads((ROOT / "tools" / "build_baselines.json").read_text())
    census = json.loads((ROOT / "analysis" / "functions.json").read_text())
    scene_graph = json.loads(
        (ROOT / "analysis" / "phase3_scene_asset_graph.json").read_text())

    # Build the overlay-size map from the centrally pinned pristine staging
    # manifest.  The previous version silently depended on an ignored
    # extracted/re_baseline/overlays.json.  That file merely repeated these
    # sizes and made clean-checkout regeneration impossible.
    per_overlay = {}
    for rel, pin in baselines["staged_inputs"].items():
        match = re.fullmatch(r"LEVEL(\d{2})/(LEVEL1?)\.BIN", rel)
        if match:
            number, stem = match.groups()
            per_overlay[f"LEVEL{number}_{stem}.BIN"] = {
                "base": overlays_yml["region_a"],
                "size": pin["size"],
                "sha256": pin["sha256"],
            }
    memory = baselines["staged_inputs"]["BITS/MEMORY.BIN"]
    per_overlay["MEMORY.BIN"] = {
        "base": overlays_yml["region_b"],
        "size": memory["size"],
        "sha256": memory["sha256"],
    }
    if len(per_overlay) != 21:
        raise SystemExit(f"expected 21 pinned overlays including MEMORY.BIN, got {len(per_overlay)}")
    entry_targets = census["resident_overlay_entry_targets"]

    # census function tags: overlay -> function count (independent of overlays.json)
    census_counts = Counter(f.get("overlay") for f in census["functions"]
                            if f.get("space") == "overlay")

    # scene -> overlays it loads (from the decoded scene-asset table)
    overlay_to_scenes = defaultdict(list)
    for skey, srow in scene_graph["scenes"].items():
        for ovtag in srow.get("overlays", {}):
            overlay_to_scenes[ovtag].append(srow["scene_id"])

    # entry VAs, bucketed to the overlay whose RAM range contains them
    ranges = []
    for name, meta in per_overlay.items():
        base = as_int(meta["base"])
        size = meta.get("size", 0)
        ranges.append((base, base + size, name))

    def owning_overlay(va):
        for lo, hi, name in ranges:
            if lo <= va < hi:
                return name
        return None

    # region A is SHARED: every LEVEL*.BIN overlay maps to base 0x800B39A0, so an
    # entry VA in region A cannot be attributed to one specific overlay by address
    # — it belongs to whichever overlay is currently loaded. Only region B
    # (MEMORY.BIN, a distinct base) is unambiguous. Bucket accordingly and SAY SO,
    # rather than pretending every region-A entry belongs to LEVEL01.
    region_a_base = as_int(overlays_yml["region_a"])
    region_b_base = as_int(overlays_yml["region_b"])
    region_a_entries, region_b_entries = [], []
    for va_s, info in entry_targets.items():
        va = as_int(va_s)
        rec = {"entry": f"0x{va:08X}",
               "resident_call_sites": info.get("call_sites", [])[:8],
               "n_sites": info.get("n_sites")}
        (region_b_entries if va >= region_b_base else region_a_entries).append(rec)

    out = {}
    for name, meta in sorted(per_overlay.items()):
        if meta.get("size", 0) <= 4:              # LEVEL00 stub
            continue
        base = as_int(meta["base"])
        # the census tag uses the LEVELnn_LEVEL form, overlays.json uses
        # LEVELnn_LEVEL.BIN — normalise to the census tag for the scene join
        tag = name.replace(".BIN", "")
        out[name] = {
            "ram_range": [f"0x{base:08X}", f"0x{base + meta['size']:08X}"],
            "size": meta["size"],
            "staged_input_sha256": meta["sha256"],
            "functions_census": census_counts.get(tag, 0),
            "entry_points_note": ("region A is a SHARED swap buffer — its entry "
                                  "points are listed once under region_a_shared_"
                                  "entry_points, not per level, because the same VA "
                                  "belongs to whichever LEVEL*.BIN is loaded"
                                  if base < region_b_base else
                                  "region B (MEMORY.BIN) has a distinct base — its "
                                  "entries are unambiguous"),
            "entry_points": (region_b_entries if base >= region_b_base else []),
            "scenes_that_load_it": sorted(overlay_to_scenes.get(tag, [])),
        }

    region_a = as_int(overlays_yml["region_a"])
    region_b = as_int(overlays_yml["region_b"])
    doc = {
        "_comment": "Phase-3 overlay boundary map, JOINING four artifacts that were "
                    "never joined (overlays.yml bases, pinned staged-input sizes, the "
                    "census resident_overlay_entry_targets, and the scene-asset "
                    "graph). THE KEY FACT: overlays REUSE the same RAM window, so an "
                    "address there is only meaningful GIVEN the loaded overlay — and "
                    "mod/hook_caves.yaml is resident-only with no overlay-aware bounds "
                    "check. Regenerate: tools/phase3_overlay_map.py",
        "generated": date.today().isoformat(),
        "fixture_sha256": fixture_pin(
            "config/overlays.yml",
            "tools/build_baselines.json",
            "analysis/functions.json",
            "analysis/phase3_scene_asset_graph.json"),
        "regions": {
            "region_a": {"base": f"0x{region_a:08X}",
                         "role": "per-level LEVEL*.BIN swap buffer"},
            "region_b": {"base": f"0x{region_b:08X}",
                         "role": "MEMORY.BIN (front-end / shared)"},
            "shared_gp": f"0x{as_int(overlays_yml['gp']):08X}",
        },
        "region_a_shared_entry_points": region_a_entries,
        "overlays": len(out),
        "overlay_ram_window": ["0x800B39A4", "0x800BE5E8"],
        "mod_safety": "An address in the overlay RAM window has NO fixed meaning: "
                      "region A holds a DIFFERENT level's overlay each load. A cave "
                      "that reads/writes there must condition on which overlay is "
                      "resident (the scene id 0x80082504 selects it). hook_caves.yaml "
                      "does not model overlays at all — it is resident-EXE only.",
        "map": out,
    }
    path = ROOT / "analysis" / "phase3_overlay_map.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[overlays] {len(out)} overlays joined")
    for name, v in list(out.items())[:6]:
        print(f"  {name:18s} {v['ram_range'][0]}..{v['ram_range'][1]} "
              f"fns={v['functions_census']} entries={len(v['entry_points'])} "
              f"scenes={v['scenes_that_load_it']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
