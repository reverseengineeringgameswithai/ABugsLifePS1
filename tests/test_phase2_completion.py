"""Offline validation of the Phase-2 completion oracle artifact.

Guards analysis/phase2_completion_oracle.json: all 16 stages replayed from boot,
pristine-replay acceptance, scene timelines reach each stage's baseline scene id,
timeline/snapshot consistency, and completion-adjacent anchors present.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "analysis" / "phase2_completion_oracle.json").read_text())
BASELINE = json.loads((ROOT / "analysis" / "phase2_stage_baseline.json").read_text())

ALL_STAGES = ["training"] + [
    "stage01_anthill", "stage02_tunnels", "stage03_council_chamber",
    "stage04_cliffside_canyon", "stage05_riverbed_run", "stage06_birdnest",
    "stage07_city_entrance", "stage08_city_square", "stage09_bug_bar",
    "stage10_clover_forest", "stage11_the_tree", "stage12_battle_arena",
    "stage13_anthill_two", "stage14_riverbed_flight", "stage15_canyon_showdown",
]


def test_all_stages_replayed_and_accepted():
    stages = DOC["stages"]
    assert sorted(stages) == sorted(ALL_STAGES)
    for lbl, st in stages.items():
        assert "error" not in st, f"{lbl}: {st.get('error')}"
        assert st["pristine_replay_accepted"] is True, lbl
        assert st["movie_sha256"] and len(st["movie_sha256"]) == 64, lbl


def test_every_movie_reaches_its_stage():
    for lbl, st in DOC["stages"].items():
        assert st["entered_stage_frame"] is not None, f"{lbl}: never entered scene {st['target_scene']}"
        assert st["last_in_stage"], lbl
        assert st["last_in_stage"]["snapshot"]["scene_id"] == st["target_scene"], lbl


def test_target_scenes_match_baseline():
    for lbl, st in DOC["stages"].items():
        if lbl == "training":
            assert st["target_scene"] == 17  # in-level Training (start save is pre-load)
        else:
            assert st["target_scene"] == BASELINE["stages"][lbl]["anchor"]["scene_id"], lbl


def test_collected_counter_sentinels():
    """Missing-pickup sentinel: each run's end-state collected counters are pinned.
    A build with missing/moved tokens desyncs the run or changes these counts."""
    expected_grain = {
        "training": 35, "stage01_anthill": 5, "stage02_tunnels": 32,
        "stage03_council_chamber": 9, "stage04_cliffside_canyon": 20,
        "stage05_riverbed_run": 27, "stage06_birdnest": 15,
        "stage07_city_entrance": 31, "stage08_city_square": 11,
        "stage09_bug_bar": 35, "stage10_clover_forest": 30,
        "stage11_the_tree": 32, "stage12_battle_arena": 30,
        "stage13_anthill_two": 22, "stage14_riverbed_flight": 40,
        "stage15_canyon_showdown": 13,
    }
    for lbl, grain in expected_grain.items():
        end = DOC["stages"][lbl]["movie_end_snapshot"]
        assert end["grain"] == grain, f"{lbl}: grain {end['grain']} != pinned {grain}"


def test_timelines_consistent():
    for lbl, st in DOC["stages"].items():
        tl = st["scene_timeline"]
        assert tl, lbl
        for seg in tl:
            assert seg["first"] <= seg["last"], f"{lbl}: {seg}"
        for a, b in zip(tl, tl[1:]):
            assert a["last"] < b["first"], f"{lbl}: overlapping segments"
            assert a["scene"] != b["scene"], f"{lbl}: uncompressed timeline"
        stage_frames = [seg for seg in tl if seg["scene"] == st["target_scene"]]
        assert stage_frames, lbl
        assert st["entered_stage_frame"] == stage_frames[0]["first"], lbl
        end_scene = st["movie_end_snapshot"]["scene_id"]
        assert st["stage_exited_by_movie_end"] == (end_scene != st["target_scene"]), lbl
