"""Guards for C16 (lives, game over, continue).

See ObsidianVault/Experiments/EXP_2026-08-04_phase4_c16_lives_gameover.md.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis" / "phase4_c16_lives_gameover.json"
TOOL = ROOT / "tools" / "phase4_c16_lives_gameover.c"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def load():
    return json.loads(ARTIFACT.read_text())


def test_lifecycle_claim_is_exhaustive_not_a_grep():
    s = load()["LIVES_LIFECYCLE_EXHAUSTIVE_2026-08-04"]
    assert "EVERY retail file" in s["method"]
    assert "r2's function listings" in s["method"]
    assert "23 accesses / 10 stores" in s["method"]
    assert "zero hits" in s["overlays_are_clean"]


def test_the_ten_stores_are_accounted_for():
    st = load()["LIVES_LIFECYCLE_EXHAUSTIVE_2026-08-04"]["ten_stores"]
    assert "CAP IS 9" in st["eight_grants"].upper()
    assert "0x80055550" in st["one_restore"]


def test_the_named_decrement_was_corrected_by_the_movie():
    """The live run proved 0x80050210 never executes; the real one is in the
    respawn transition handler. The wrong claim must stay visible as history."""
    c = load()["CORRECTION_2026-08-04_the_decrement_i_named_is_not_the_one_that_runs"]
    assert "0x8005B34C" in c["what_the_movie_shows"]
    assert "never executed" in c["what_the_movie_shows"]
    assert "0x8005B334" in c["the_real_death_decrement"]
    assert "respawn_transition_state_handler" in c["the_real_death_decrement"]
    # the meta-failure must be named, not softened
    assert "passing structural check" in c["why_my_heuristic_missed_it"]
    assert "GAME-OVER CHECK" in c["what_0x80050210_actually_is"]
    assert "0x800A6590" in c["bonus_finding"] and "0x20" in c["bonus_finding"]


def test_tool_no_longer_asserts_the_false_classification():
    src = TOOL.read_text()
    assert "acc != 23 || stores != 10)" in src
    assert "dec != 1" not in src


def test_game_over_path_and_fmv_id():
    s = load()["DECREMENT_AND_GAME_OVER_2026-08-04"]
    assert "0x800500D4" in s["the_branch"]
    assert "FMV id 46" in s["game_over_path"]
    assert "scene_setup_and_load(5, 0x40)" in s["game_over_path"]
    assert "41" in s["fmv_id_cross_reference"]


def test_game_over_args_captured_live_with_ra_proving_the_call_site():
    g = load()["GAME_OVER_ARGS_CAPTURED_2026-08-04"]
    assert "0x2E" in g["fmv_call"] and "0x800500E0" in g["fmv_call"]
    assert "a0 = 5" in g["scene_call"] and "0x800500EC" in g["scene_call"]
    # the method gotcha must be recorded, it cost a whole run
    assert "PC EQUALITY" in g["closes"]
    assert "paused" in g["closes"]


def test_scene_tension_resolved_as_a_category_error_not_papered_over():
    g = load()["GAME_OVER_ARGS_CAPTURED_2026-08-04"]
    r = g["scene_tension_RESOLVED_as_a_category_error"]
    assert "DIFFERENT THINGS" in r
    assert "0x8008245C" in r and "4 throughout" in r
    # and the residual honesty: 'scene 0' is bounded, not proven either way
    assert "neither confirmed nor refuted" in g["what_is_still_unverified"]


def test_scene_tension_is_flagged_not_resolved():
    """The row's own binding says scene 0; the code says 5. Still open even after
    the movie -- the execTrace capture returned no a0/a1."""
    g = load()["DECREMENT_AND_GAME_OVER_2026-08-04"]
    s = g["TENSION_FLAGGED_NOT_RESOLVED"]
    assert "scene 0" in s and "a0 = 5" in s
    assert "Not resolved" in g["scene_tension_still_open"]
    assert "SUPERSEDED_2026-08-04" in g


def test_new_game_defaults_confirm_the_save_schema():
    s = load()["NEW_GAME_DEFAULTS_2026-08-04"]
    assert "INITIAL LIVES" in s["layout"] and "buf[0] = 5" in s["layout"]
    assert "19 bytes" in s["layout"]
    assert "0x80055478" in s["layout"] and "0x80055538" in s["layout"]
    # naming restraint after three census corrections this session
    assert "NOT renamed" in s["function"] or "not changed" in s["function"]


def test_row_not_claimed_exhausted_and_fixture_offer_recorded():
    d = load()
    assert "NOT exhausted" in d["status"]
    assert "continue" in d["STILL_OPEN"]
    assert "FALSIFIED" in d["fixture_note"]
    assert "C16_lives_gameover.movie.json" in d["fixture_note"]


def test_tool_pins_and_recounts():
    fd, out = tempfile.mkstemp()
    os.close(fd)
    try:
        b = subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(TOOL), "-o", out], capture_output=True, text=True)
        assert b.returncode == 0, b.stderr
        r = subprocess.run([out, str(EXE)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-2000:] + r.stderr
        assert "19/19 pins OK" in r.stdout
        assert "23 accesses, 10 stores" in r.stdout
        assert "does NOT find the real death decrement" in r.stdout
        assert "entirely RESIDENT" in r.stdout
    finally:
        os.remove(out)


def test_registry_row_updated():
    text = REGISTRY.read_text()
    s = text.index("  - id: C16_lives_gameover")
    e = text.index("\n  - id:", s + 10)
    block = text[s:e]
    for needle in ("LIVES LIFECYCLE EXHAUSTIVE 2026-08-04",
                   "DECREMENT IS THE GAME-OVER BRANCH 2026-08-04",
                   "NEW-GAME DEFAULTS 2026-08-04"):
        assert needle in block, needle
    row = yaml.safe_load("rows:\n" + block)["rows"][0]
    assert row["status"] == "partial"
    assert "NOT exhausted" in row["next"]


def test_continue_path_and_scene0_confirmation():
    c = load()["CONTINUE_PATH_CLOSED_2026-08-04_v2_movie"]
    # the new movie must be a NEW file, not an overwrite
    assert "NEW file" in c["fixture"] and "_v2" in c["fixture"]
    assert "still reproduces" in c["fixture"]
    # lives restore route
    assert "0x80055554" in c["lives_are_restored_by_the_SAVE_DESERIALIZER"]
    assert "not by calling the new-game initializer" in c["lives_are_restored_by_the_SAVE_DESERIALIZER"]
    # BIOS write reported, not interpreted
    assert "BIOS" in c["two_further_writes_at_level_entry"]
    assert "not interpreted" in c["two_further_writes_at_level_entry"]


def test_my_scene0_hedge_was_resolved_in_the_registrys_favour():
    """I hedged 'neither is scene 0'; v2 shows 0x8008245C does reach 0. The
    reversal must be explicit, and the surviving narrower point kept."""
    c = load()["CONTINUE_PATH_CLOSED_2026-08-04_v2_movie"]["SCENE_0_CONFIRMED_correcting_my_own_hedge"]
    assert "IS CONFIRMED" in c
    assert "REGISTRY'S FAVOUR" in c.upper()
    assert "a0 = 5" in c and "NOT the value written" in c
    # and the timing nuance must not be smoothed away
    n = load()["CONTINUE_PATH_CLOSED_2026-08-04_v2_movie"]["timing_nuance"]
    assert "NOT at the game-over instant" in n
