#!/usr/bin/env python3
"""Guards for the rebuild guard.

It exists to be believed on the day something really moved, so its own failure modes
matter more than most. Two have already occurred:

  * it asserted a summary FIELD NAME (`domain_closed`) that was later renamed when
    that overclaim was retracted, and reported DID NOT REPRODUCE against a run that
    had reproduced perfectly;
  * it derived the emulator's method surface by REGEXING the emulator's C++, counting
    202 where the fork dispatches 221 -- leaving 19 methods invisible to the one check
    whose job is noticing a method disappeared.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools/rebuild_guard.py"
BASE = ROOT / "analysis/duckstation_prechange_baseline.json"
HIST = ROOT / "analysis/duckstation_prechange_baseline_2026-08-04.json"


def base():
    return json.loads(BASE.read_text())


def test_method_surface_comes_from_the_emulator_not_its_source():
    assert base()["rpc_methods_source"] == "live_capabilities"
    assert "MUST COME FROM THE EMULATOR" in TOOL.read_text()


def test_every_method_our_tools_call_still_exists():
    d = base()
    missing = set(d["methods_used_by_our_tools"]) - set(d["rpc_methods"])
    assert not missing, missing


def test_oracles_assert_values_not_field_names():
    """The check must survive us renaming our own output fields, because we do that
    whenever we correct an overclaim.

    Forbidding the STRING `domain_closed` here was too strict -- the block explains
    the past failure by naming it. What must be absent is the DEPENDENCY: no code
    path may key on it. Absence of a mention and absence of a use are different
    assertions, and conflating them is how this same test class keeps misfiring."""
    src = TOOL.read_text()
    oracles = src.split("ORACLES")[1]
    assert "SUBSTANTIVE evidence, not a summary flag" in src
    for use in ('d["domain_closed"]', "d['domain_closed']", 'd.get("domain_closed")'):
        assert use not in oracles, use


def test_diff_refuses_to_compare_incomparable_surfaces():
    """A live-derived list against a regex-derived one differs by construction; the
    delta would be reported as methods appearing or vanishing that did neither."""
    assert "NOT COMPARABLE" in TOOL.read_text()


def test_the_prechange_snapshot_was_preserved_not_overwritten():
    """The pre-upgrade binary identity and SAVE_STATE_VERSION cannot be re-derived
    once the old binary is gone."""
    assert HIST.exists()
    h = json.loads(HIST.read_text())
    assert h["save_state_version"] == 84
    assert "HISTORICAL" in h["_note"]
    assert h["rpc_method_count"] < base()["rpc_method_count"]


def test_the_unhashed_fixture_hazard_is_still_recorded():
    """123 state-anchored movies with start_state.sha256 null. Until that closes, a
    state drift is silent and these two oracles stand in for all of them."""
    d = base()
    assert d["state_anchored_count"] >= 100
    assert d["movies_without_state_hash"] == d["state_anchored_count"]
