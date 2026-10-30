import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "analysis" / "phase4_e12_audio.json"
STATIC_GUARD = ROOT / "tools" / "phase4_e12_audio_static.c"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="ascii"))


def test_e12_is_bounded_and_does_not_require_a_movie():
    evidence = load_evidence()
    assert evidence["row"] == "E12_audio"
    assert evidence["status"] == "substantiated_partial"
    assert evidence["closure"] == "bounded_exhausted_move_on"
    assert evidence["additional_interpreter_movie_required"] is False
    assert evidence["method"]["live_replay_reason"] is None


def test_music_map_is_complete_and_derived_from_packed_ids():
    music = load_evidence()["observations"]["music_selection"]
    levels = music["levels"]
    assert [entry["level"] for entry in levels] == list(range(1, 16))
    assert [entry["channel"] for entry in levels[:8]] == list(range(8))
    assert {entry["file"] for entry in levels[:8]} == {"AUDIO1.XA"}
    assert [entry["channel"] for entry in levels[8:]] == list(range(7))
    assert {entry["file"] for entry in levels[8:]} == {"AUDIO2.XA"}
    assert music["special_override"] == {
        "packed_id": "0x15",
        "decimal": 21,
        "file": "AUDIO3.XA",
        "channel": 5,
    }


def test_sfx_frontier_and_dynamic_boundary_are_explicit():
    evidence = load_evidence()
    frontier = evidence["observations"]["sfx_call_frontier"]
    assert frontier["total_dispatch_calls"] == 31
    assert frontier["total_play_sound_calls"] == 109
    assert frontier["total_dispatch_dynamic_sites"] == 4
    assert frontier["total_play_sound_dynamic_sites"] == 4
    residuals = " ".join(evidence["bounded_residuals"])
    assert "dynamic direct-dispatch" in residuals
    assert "audible/semantic label" in residuals


def test_voice_pause_and_capsule_limits_are_preserved():
    evidence = load_evidence()
    voice = evidence["observations"]["voice_ownership"]
    pause = evidence["observations"]["pause_and_reset"]
    capsules = evidence["capsule_audit"]
    assert "Eight entries" in voice["primary_pool"]
    assert "all 24 SPU key states" in voice["lifecycle_tick"]
    assert "keys off all 24 voices" in voice["hard_reset"]
    assert "stops while paused" in pause["pause"]
    assert capsules["relevant_e12_capsule_found"] is False
    assert "per-voice SPU register" in capsules["missing_domain"]


def test_static_guard_pins_pristine_asm_and_media_inventories():
    source = STATIC_GUARD.read_text(encoding="ascii")
    for token in (
        "0x8005bb90u",
        "0x80044c70u",
        "0x800432ecu",
        "0x800434dcu",
        "AUDIO%u.XA",
        "g_totals.vh_files != 21",
        "resident_dispatch != 22",
        "g_totals.dispatch_calls != 9",
    ):
        assert token in source
