#!/usr/bin/env python3
"""Guards for the Bonus-1 streak law (row F16).

Two things here are corrections, and both are the kind that quietly come back:

  * The row was named "consecutive spider bounces". Nothing in the streak logic
    looks at the enemy -- `s6` is the PLAYER struct. The operator flagged it; the
    name must not drift back to a species.
  * The berry reset is at the CONSTRUCTOR's entry and is unconditional, so it is the
    THROW that kills the chain, not the kill. "Berry kills reset it" is the natural
    thing to write down and is subtly wrong.

The resolved direct-site list is guarded without promoting it to domain closure.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools/phase4_f16_streak_law.c"
TRACER = ROOT / "tools/phase4_f16_streak_reset_trace.py"
LIVE = ROOT / "analysis/phase4_F16_streak_live.json"


def rows():
    d = yaml.safe_load((ROOT / "analysis/mechanics_baseline.yaml").read_text(
        encoding="utf-8"))
    for v in d.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return {x["id"]: x for x in v}
    raise AssertionError("no row list")


@pytest.fixture(scope="module")
def law(tmp_path_factory):
    exe = tmp_path_factory.mktemp("f16law") / "f16law"
    subprocess.run(["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-o", str(exe), str(TOOL)], check=True, cwd=ROOT)
    r = subprocess.run([str(exe)], cwd=ROOT, capture_output=True, text=True)
    return r


def test_law_tool_builds_and_every_pin_holds(law):
    assert law.returncode == 0, law.stdout[-3000:]
    assert "0 failed" in law.stdout
    assert "every pin holds against the pristine image" in law.stdout


def test_the_resolved_direct_counter_sites_remain_pinned(law):
    assert "scanner resolves ONE direct read" in law.stdout
    assert "scanner resolves SEVEN direct writes" in law.stdout
    assert "six resolved direct clears" in law.stdout
    assert "no fixed-form direct overlay hit" in law.stdout
    for pc in ("0x800470d8", "0x8004a6c4", "0x8004a854",
               "0x8004b1d4", "0x8004b350", "0x8004b3d0"):
        assert pc in law.stdout


def test_the_deciding_state_is_the_players(law):
    assert "s6 is never reassigned inside the actor loop" in law.stdout
    assert "0x8004ac78" in law.stdout


def test_the_three_way_class_test(law):
    """sltiu ...,2 is the whole 'some things reset, some don't' behaviour."""
    assert "sltiu v0,v0,2" in law.stdout
    assert "NEITHER counts NOR resets" in law.stdout


def test_the_berry_reset_is_proven_unconditional(law):
    """Both halves of the proof must be present: no branch before the store, AND
    nothing branching over it. Checking only the first is how this goes wrong."""
    assert "no branch between the function entry and the store" in law.stdout
    assert "nothing in the function branches over it" in law.stdout


def test_berry_reset_is_described_as_the_throw_not_the_kill():
    src = TOOL.read_text()
    assert "THROW, not the kill" in src or "THROW not the kill" in src


# ---------------------------------------------------------------------- row --

def test_row_name_is_no_longer_species_specific():
    """The operator's correction. 'Spiders' was the fixture, not the rule."""
    name = rows()["F16_bonus1_spiders"]["name"]
    assert "spider" not in name.lower()
    assert "butt-slam" in name.lower()


def test_row_records_the_three_way_class_test():
    b = " ".join(rows()["F16_bonus1_spiders"]["bindings"])
    assert "0x800A6584" in b
    assert "sltiu" in b
    assert "NEVER touched" in b or "never touched" in b


def test_row_records_the_complete_reset_list():
    b = " ".join(rows()["F16_bonus1_spiders"]["bindings"])
    for pc in ("0x800470D8", "0x8004B1D4", "0x8004B350", "0x8004A6C4",
               "0x8004A854", "0x8004B3D0"):
        assert pc in b, pc
    assert "THROW not the kill" in b or "THROW, not the kill" in b or "THROW" in b


def test_row_says_the_player_not_the_enemy_decides():
    b = " ".join(rows()["F16_bonus1_spiders"]["bindings"])
    assert "PLAYER" in b
    assert "fixture, not the rule" in b


# --------------------------------------------------------------------- live --

@pytest.mark.skipif(not LIVE.exists(), reason="live capture not present")
def test_live_run_found_no_writer_outside_the_resolved_set():
    d = json.loads(LIVE.read_text())
    assert d["writers_outside_resolved_set_in_this_run"] == []
    assert d["no_observed_writer_outside_resolved_set"] is True
    assert d["RETRACTED_domain_closed"] is True


@pytest.mark.skipif(not LIVE.exists(), reason="live capture not present")
def test_live_run_replayed_as_recorded():
    """A v4 Interpreter movie that desyncs still reports success -- the five
    increments and the unlock are what prove it actually replayed."""
    d = json.loads(LIVE.read_text())
    assert d["movie_version"] == 4
    inc = [s for s in d["streak_timeline"] if s["pc"] == "0x8004b3a8"]
    assert [s["v"] for s in inc] == [1, 2, 3, 4, 5]


def test_tracer_uses_60hz_not_frame_stepping():
    """The movie is armed_while_paused, i.e. exactly the phase-sensitive case where
    advanceToFrame and 60 Hz playback disagree."""
    src = TRACER.read_text()
    assert "debugger.resume" in src
    # the docstring names advanceToFrame to warn against it; what matters is that
    # it is never CALLED
    assert 'movie.advanceToFrame"' not in src


def test_tracer_isolates_parallel_runs():
    """A shared config dir made two of three runs fail to bring the API up, which
    presents as an emulator fault rather than a harness bug."""
    assert "f16-reset-%d" in TRACER.read_text()


# ------------------------------------------------- the operator's reset test --

RESET = ROOT / "analysis/phase4_F16_reset_test.json"


@pytest.fixture(scope="module")
def reset():
    return json.loads(RESET.read_text())


def marker(d, label):
    return next(m for m in d["operator_markers"] if m["label"] == label)


def test_reset_test_used_movie_relative_frames(reset):
    """The recording is state-anchored. Comparing raw emulator frames against the
    operator's marks would line every event up against the wrong action."""
    assert reset["movie_anchor_frame"] == 10757


def test_berry_reset_happens_at_the_throw_not_the_kill(reset):
    """The whole point: the clear lands ~87 frames BEFORE the berry hits anything,
    so 'berry kills reset the chain' is the wrong causal model."""
    m = marker(reset, "berry kill")
    killed = m["destroyed_a_live_chain"]
    assert killed, "the berry event destroyed nothing"
    assert killed[0]["pc"] == "0x800470d8"
    assert killed[0]["mf"] < m["movie_frame"] - 50


def test_kick_kill_does_not_touch_the_counter(reset):
    m = marker(reset, "kick kill")
    assert m["streak_events_within_200_frames"] == []
    assert m["destroyed_a_live_chain"] == []


def test_thrown_seed_kill_does_not_touch_the_counter(reset):
    """Seeds are not the berry dispatch -- a thrown seed produced no counter event."""
    m = marker(reset, "seed kill (thrown)")
    assert m["streak_events_within_200_frames"] == []


def test_buttslide_and_landing_jump_kills_do_reset(reset):
    for label, pc in (("buttslide kill", "0x8004b1d4"),
                      ("landing-jump kill", "0x8004b350")):
        m = marker(reset, label)
        assert m["destroyed_a_live_chain"], label
        assert m["destroyed_a_live_chain"][0]["pc"] == pc, label


def test_damage_path_destroyed_live_chains(reset):
    hits = [r for r in reset["destructive_resets"] if r["pc"] == "0x8004a854"]
    assert len(hits) >= 2


def test_reset_test_found_no_writer_outside_the_resolved_set(reset):
    assert reset["no_observed_writer_outside_resolved_set"] is True
    assert reset["writers_outside_resolved_set_in_this_run"] == []
    assert reset["RETRACTED_domain_closed"] is True


def test_bonus1_canon_and_tools_do_not_restore_domain_closure():
    canon = (ROOT / "ObsidianVault/Canon/Systems/SYS_bonus1_streak_law.md").read_text()
    source = TOOL.read_text()
    tracer = TRACER.read_text()
    assert "## The counter's domain is closed" not in canon
    assert "So the list below is complete, not a sample." not in canon
    assert "THE COUNTER'S DOMAIN IS CLOSED" not in source
    assert "exactly ONE read of the counter in the whole game" not in source
    assert 'out["domain_closed"]' not in tracer
    assert "resolved direct set, not an absolute domain" in canon


def test_canon_records_the_slam_timer_not_a_class():
    t = " ".join((ROOT / "ObsidianVault/Canon/Systems/SYS_bonus1_streak_law.md")
                 .read_text().split())
    assert "butt-slam window timer" in t
    assert "sticks at 1" in t
    assert "0x80048CA8" in t


def test_canon_flags_the_misleading_census_name():
    t = " ".join((ROOT / "ObsidianVault/Canon/Systems/SYS_bonus1_streak_law.md")
                 .read_text().split())
    assert "hit/knockback" in t
    assert "not describing this block" in t
