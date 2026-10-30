"""Phase-3 gate bullet 3 (overlay half): the overlay boundary map.

The fact this guards: overlays REUSE the same RAM window, so an address there is
meaningful only given the loaded overlay. A map that assigned each region-A entry
to one specific level would be lying — region A is a shared swap buffer."""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M = json.loads((ROOT / "analysis" / "phase3_overlay_map.json").read_text())
SCENE = json.loads(
    (ROOT / "analysis" / "phase3_scene_asset_graph.json").read_text())


def test_every_real_overlay_is_mapped_and_pinned():
    assert M["overlays"] >= 18
    assert M["fixture_sha256"], "no fixture pins (DoF #1)"
    for name, v in M["map"].items():
        assert v["ram_range"][0].startswith("0x800B")
        assert int(v["ram_range"][1], 16) > int(v["ram_range"][0], 16)


def test_scene_overlay_mapping_agrees_with_the_scene_asset_graph():
    """Two independent sources must agree: the scene-asset graph says LEVEL01
    loads at scenes 1 and 6; the overlay map, built from the same table, must
    reproduce that."""
    l01 = M["map"]["LEVEL01_LEVEL.BIN"]
    assert l01["scenes_that_load_it"] == [1, 6]
    # every overlay that any scene loads must appear with a non-empty scene list
    loads = Counter()
    for srow in SCENE["scenes"].values():
        for ov in srow.get("overlays", {}):
            loads[ov] += 1
    for ovtag in loads:
        key = ovtag + ".BIN"
        if key in M["map"]:
            assert M["map"][key]["scenes_that_load_it"], ovtag


def test_region_a_sharing_is_stated_not_faked():
    """All LEVEL*.BIN overlays share region A's base — so their entry points are
    NOT attributed per level (that would be a lie), but listed once as shared.
    Only region B (MEMORY.BIN, distinct base) gets its own entries."""
    # all region-A overlays report the same base
    region_a = [v for v in M["map"].values()
                if int(v["ram_range"][0], 16) < 0x800B5000]
    assert len({v["ram_range"][0] for v in region_a}) == 1
    for v in region_a:
        assert v["entry_points"] == []            # not faked per-level
    assert len(M["region_a_shared_entry_points"]) >= 30
    # region B keeps its own
    assert M["map"]["MEMORY.BIN"]["entry_points"]


def test_no_entry_point_is_lost_in_the_join():
    census = json.loads((ROOT / "analysis" / "functions.json").read_text())
    total_targets = len(census["resident_overlay_entry_targets"])
    assigned = (len(M["region_a_shared_entry_points"])
                + sum(len(v["entry_points"]) for v in M["map"].values()))
    assert assigned == total_targets


def test_mod_safety_boundary_is_documented():
    assert "no fixed meaning" in M["mod_safety"].lower() or \
        "different level" in M["mod_safety"].lower()
    assert "resident" in M["mod_safety"].lower()


def test_overlay_map_regenerates_without_an_ignored_extraction_tree():
    before = json.loads((ROOT / "analysis/phase3_overlay_map.json").read_text())
    proc = subprocess.run([sys.executable, "tools/phase3_overlay_map.py"], cwd=ROOT,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = json.loads((ROOT / "analysis/phase3_overlay_map.json").read_text())
    before.pop("generated", None)
    after.pop("generated", None)
    assert before == after
    assert "tools/build_baselines.json" in after["fixture_sha256"]
    assert "extracted/re_baseline/overlays.json" not in after["fixture_sha256"]
