"""Offline validation of the Phase-2 gate-item artifacts: action windows/oracle,
lifecycle, presentation baseline, and soak."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = json.loads((ROOT / "analysis" / "phase2_action_windows.json").read_text())
ACTIONS = json.loads((ROOT / "analysis" / "phase2_action_oracle.json").read_text())
LIFECYCLE = json.loads((ROOT / "analysis" / "phase2_lifecycle_oracle.json").read_text())
PRESENTATION = json.loads((ROOT / "analysis" / "phase2_presentation_baseline.json").read_text())
SOAK = json.loads((ROOT / "analysis" / "phase2_soak.json").read_text())


def test_action_windows_cover_core_classes():
    t = WINDOWS["totals"]
    assert t["jump"]["in_stage"] >= 500
    assert t["square_action"]["in_stage"] >= 1000
    assert t["double_tap_cross"]["in_stage"] >= 50
    assert t["kick"]["total"] >= 5
    # movies never slow-walk or press circle — covered by synthetic probes instead
    assert t["slow_walk"]["total"] == 0
    assert t["circle_negative"]["total"] == 0
    assert len(WINDOWS["movies"]) == 18  # 16 go_to_end + 2 100% Runs


def test_action_oracle_samples_and_probes():
    samples = ACTIONS["movie_samples"]
    assert sum(len(v) for v in samples.values()) >= 15
    for cls in ("jump", "square_action", "triangle_action", "camera_look", "kick"):
        assert samples[cls], f"no native sample for {cls}"
    for e in (x for v in samples.values() for x in v):
        assert set(e["snapshots"]) == {"-15", "+2", "+12", "+32"}
    syn = ACTIONS["synthetic_probes"]
    ratio = syn["slow_walk"]["displacement_ratio_x"]
    assert 0.4 < ratio < 0.8, f"slow-walk ratio {ratio} outside plausible band"
    circle = syn["circle_negative"]
    # health is excluded: 0x800A7E2A is the HUD-ANIMATED display and may tick
    # during any window (lifecycle oracle finding) — not a Circle effect
    for f in ("lives", "grain", "equipped_berry", "power_word", "scene_id",
              "player_x", "player_z"):
        assert f in circle["null_delta_fields"], f"circle changed {f}"


def test_lifecycle_findings_and_passes():
    ex = LIFECYCLE["experiments"]
    assert ex["save_reload"]["deterministic"] is True
    assert set(ex["pause_freeze"]["player_fields_frozen_under_pause"]) >= \
        {"player_x", "player_y", "player_z"}
    assert ex["pause_freeze"]["resume_restores_motion"] is True
    assert ex["teleport_recovery"]["recovered_to_floor"] is True
    assert ex["teleport_recovery"]["no_death"] is True


def test_lifecycle_death_respawn_game_over():
    ex = LIFECYCLE["experiments"]
    death = ex["death_contact_respawn"]
    assert "0x800A6594" in death["true_health_address"]
    assert death["death_observed"] is True
    assert death["respawn_state"]["lives"] == death["before"]["lives"] - 1
    assert death["respawn_health"] == 4      # respawn restores 4, not full 7
    assert death["respawn_at_spawn_point"] is True
    go = ex["game_over_final_life"]
    assert go["before"]["lives"] == 0        # lives 0 = playable final life
    assert go["left_stage_scene"] is True    # final-life death leaves the stage
    assert 0 in go["scene_sequence_compressed"]


def test_presentation_baseline_deterministic_everywhere():
    anchors = PRESENTATION["anchors"]
    assert len(anchors) == 19
    for lbl, a in anchors.items():
        assert "error" not in a, f"{lbl}: {a.get('error')}"
        assert a["deterministic_double_capture"] is True, lbl
        assert len(a["frame_sha256"]) == 64, lbl
    # distinct stages must present distinct frames
    hashes = [a["frame_sha256"] for a in anchors.values()]
    assert len(set(hashes)) == len(hashes), "two anchors share a frame hash"


def test_soak_results():
    r = SOAK["results"]
    assert all(v["deterministic"] for v in r["reload_x3"].values())
    for sav, idle in r["idle_soak"].items():
        assert idle["guest_alive_in_scene"] is True, sav
        assert "scene_id" not in idle["drifting_fields"], sav
    pc = r["pause_cycle_x10"]
    assert pc["still_in_scene"] and pc["responds_to_input_after"]
