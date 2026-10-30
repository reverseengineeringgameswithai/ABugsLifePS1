"""Phase-3 WP7 guard: the scene -> asset -> overlay graph is consistent with
the INDEPENDENT Phase-2 replay evidence (a decode that agreed with itself but
not with the movies would be worthless)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GRAPH = json.loads((ROOT / "analysis" / "phase3_scene_asset_graph.json").read_text())
ORACLE = json.loads(
    (ROOT / "analysis" / "phase2_completion_oracle.json").read_text())


def test_fifteen_scenes_decoded_and_shaped():
    scenes = GRAPH["scenes"]
    assert len(scenes) == 15
    for key, r in scenes.items():
        assert r["asset_entry"].startswith("level")
        assert "\\" in r["asset_entry"]
        assert r["loading_screen"].startswith("gfx\\")
        assert r["overlays"], key           # every scene resolves an overlay


def test_every_campaign_scene_matches_a_phase2_movie():
    """Cross-evidence: the EXE table's row index = scene_id - 1 must reproduce
    the scene ids the Phase-2 go_to_end movies actually reached."""
    observed = {st["target_scene"]: label
                for label, st in ORACLE["stages"].items()
                if isinstance(st.get("target_scene"), int)}
    for r in GRAPH["scenes"].values():
        sid = r["scene_id"]
        if sid in observed:
            assert r["phase2_stage_labels"] == [observed[sid]], sid
    campaign = {r["scene_id"] for r in GRAPH["scenes"].values()}
    assert campaign == set(range(1, 16))
    # All 15 campaign stages cross-verified; Training is an explicit exceptional route.
    verified = [r for r in GRAPH["scenes"].values() if r["phase2_stage_labels"]]
    assert len(verified) == 15
    assert GRAPH["gaps"] == []
    training = [r for r in GRAPH["exceptional_routes"] if r["scene"] == 17]
    assert len(training) == 1
    route = training[0]["route"]
    assert route["resource_dispatch_table"] == "0x8001AFB0"
    assert route["resource_dispatch_index"] == 16
    assert route["resource_dispatch_target"] == "0x8003CFC4"
    assert route["disc_directory"] == "LEVEL00"
    assert "not a Region-A code overlay" in route["overlay_semantics"]
    assert GRAPH["unload_graph"]["observed_exit_reclaims_world"] is False


def test_disc_dirs_do_not_track_scene_ids():
    """The load law: the disc DIRECTORY selects the overlay, the asset PREFIX
    selects the sub-level — so dir numbers deliberately differ from scene ids
    (scene 11 -> level02). Guards against a 'simplification' regression."""
    scenes = GRAPH["scenes"]
    mismatched = [r for r in scenes.values()
                  if int(r["disc_dir"].removeprefix("level")) != r["scene_id"]]
    assert len(mismatched) >= 8
    s11 = scenes["scene_11"]
    assert s11["disc_dir"] == "level02" and s11["asset_prefix"] == "level4b"


@pytest.mark.local_media
def test_graph_is_fresh_regeneration():
    before = json.loads(
        (ROOT / "analysis" / "phase3_scene_asset_graph.json").read_text())
    proc = subprocess.run([sys.executable, "tools/phase3_scene_asset_graph.py"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    after = json.loads(
        (ROOT / "analysis" / "phase3_scene_asset_graph.json").read_text())
    before.pop("generated"), after.pop("generated")
    assert before == after, "committed scene graph is stale"
