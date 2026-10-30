"""Phase-3 WP6 guards: scene-transition reset/ownership laws, ALL 16 stages.

LEVEL01 alone could not show whether these laws generalise — so the sweep runs
every stage, and the exceptions it found are asserted here rather than smoothed
over (Bug Bar has no actor roster at all; health is written later than the roster
in four stages)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = json.loads((ROOT / "analysis" / "phase3_transition_reset.json").read_text())
STAGES = T["stages"]
LAWS = T["laws"]

# Bug Bar carries NO chunk-31 actor roster — the same structural negative Phase 2
# documented when its death probe found an empty actor table.
NO_ROSTER = {"stage09_bug_bar"}


def test_every_stage_measured_with_both_transitions():
    assert T["stages_measured"] == 16, T["stages_measured"]
    assert not T["skipped"], T["skipped"]
    for name, r in STAGES.items():
        assert set(r["transitions"]) == {"entry_load", "exit_to_shell"}, name


def test_scene_id_flips_long_before_the_world_exists_in_every_stage():
    """THE load law: the scene id changes when the transition STARTS, but the
    world only exists when the disc read finishes. A mod hooking 'scene changed'
    runs inside an EMPTY world — for 450 frames at best, 1170 at worst."""
    gaps = LAWS["load_gap_frames"]
    assert len(gaps["per_stage"]) == 16
    assert gaps["min"] >= 120, gaps
    for stage, g in gaps["per_stage"].items():
        assert g >= 120, (stage, g)          # never "ready immediately"


def test_load_populates_the_world():
    for name, r in STAGES.items():
        e = r["transitions"]["entry_load"]["records"]
        a = e["actor_record"]
        assert a["live_before"] == 0, name
        if name in NO_ROSTER:
            assert a["live_after"] == 0, f"{name} unexpectedly grew a roster"
        else:
            assert a["live_after"] > 0, name
        # the player is always dead-zero before the load lands
        assert e["player_block"]["fields"]["health_true"]["before"] == 0, name


def test_player_spawns_with_health_4_where_health_is_written_by_world_ready():
    """hp := 4 at spawn (NOT 7). In four stages health is written a few ticks
    AFTER the actor roster, so at the world-ready sample it is still 0 — that is
    a timing fact, not a different spawn rule."""
    spawned = {name: r["transitions"]["entry_load"]["records"]["player_block"]
               ["fields"]["health_true"]["after"] for name, r in STAGES.items()}
    nonzero = {k: v for k, v in spawned.items() if v}
    assert len(nonzero) >= 12, spawned
    assert set(nonzero.values()) == {4}, nonzero      # always 4, never 7


def test_progression_is_session_owned_in_every_stage():
    """These survive the level exit in ALL 16 stages, so they belong to the
    SESSION, not the scene. A mod that reinitialises them on load silently wipes
    the player's progress."""
    common = set(LAWS["session_owned_everywhere"])
    for field in ("health_true", "lives", "grain_count",
                  "enemy_permanence_quota"):
        assert field in common, field
    for name, r in STAGES.items():
        carried = set(r["transitions"]["exit_to_shell"]["records"]
                      ["player_block"]["carried_over"])
        assert common <= carried, name


def test_exit_never_reclaims_the_world():
    """The exit frees NOTHING, in every stage: actor/plant/contact data stays
    resident and stale until the next load overwrites it. Anything reading those
    tables in the shell is reading the PREVIOUS level."""
    assert LAWS["exit_reclaims_world"] is False
    for name, r in STAGES.items():
        a = r["transitions"]["exit_to_shell"]["records"]["actor_record"]
        assert a["live_after"] == a["live_before"], name


def test_actor_table_runs_completely_full_in_some_stages():
    """MOD-SAFETY: the actor table is a FIXED 40-slot roster and several stages
    fill it COMPLETELY — zero free slots. A mod adding an actor there has nowhere
    to put it. If this stops holding, the rosters changed and the guidance must."""
    full = {name for name, r in STAGES.items()
            if r["transitions"]["exit_to_shell"]["records"]["actor_record"]
            ["live_before"] == 40}
    assert {"stage02_tunnels", "stage05_riverbed_run", "stage11_the_tree",
            "stage14_riverbed_flight"} <= full, full
