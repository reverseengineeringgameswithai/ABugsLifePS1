"""Offline validation of the Phase-2 gate-residuals artifact (audio oracle,
in-motion presentation, camera-lock samples, death matrix, long soak)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "analysis" / "phase2_gate_residuals.json").read_text())


def test_audio_baseline_all_anchors_deterministic():
    audio = DOC["audio_baseline"]
    assert len(audio) == 19
    for lbl, a in audio.items():
        assert a["deterministic_double_capture"] is True, lbl
        assert len(a["voices"]) == 24, lbl
        # the high-pitch sentinel: every active voice pins its exact pitch
        for idx in a["voices_on"]:
            assert str(idx) in a["voice_pitches_on"], f"{lbl} voice {idx}"
            assert 0 < a["voice_pitches_on"][str(idx)] <= 0x4000, f"{lbl} voice {idx}"


def test_audio_event_signatures_present():
    # quiet anchors (menu-adjacent saves, silent rooms) can be event-free for
    # 120 frames; 13/19 emitted events on the pristine baseline run
    with_events = [l for l, a in DOC["audio_baseline"].items()
                   if a["events_120f"]["counts"]]
    assert len(with_events) >= 12, "SPU event flow collapsed vs the pristine baseline"


def test_motion_presentation_deterministic():
    m = DOC["motion_presentation"]
    assert m["deterministic_across_replays"] is True
    assert m["distinct_frames"] == len(m["frames"])
    assert m["replay1"] == m["replay2"]


def test_camera_lock_native_samples():
    samples = DOC["camera_lock_samples"]
    assert len(samples) == 2
    for s in samples:
        assert s["snapshots"], s["movie"]


def test_death_matrix_stage_classes():
    dm = DOC["death_matrix"]
    for cls in ("stage03_boss_arena", "stage07_city"):
        d = dm[cls]
        assert d["lives_decremented"] is True, cls
        assert d["respawn_health"] == 4, cls   # respawn law holds across classes
    # tree class: no hostile contact from first records — documented, not silent
    assert "note" in dm["stage11_tree"]


def test_long_soak_including_natural_game_over():
    soak = DOC["long_soak"]
    l1 = soak["level01.sav"]
    assert l1["guest_alive_in_scene"] is True
    assert l1["emulated_minutes"] >= 3.0
    # Bug Bar: the idle player is killed by the arena — a NATURAL game-over,
    # corroborating the lifecycle laws (hp -1, lives 0, game-over scene 0)
    l9 = soak["level_09.sav"]["final"]
    assert l9["health_true"] == -1 and l9["lives"] == 0 and l9["scene_id"] == 0
