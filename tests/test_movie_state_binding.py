#!/usr/bin/env python3
"""Guards for the movie<->state binding.

Before the 2026-08-05 backfill, all 123 state-anchored fixtures recorded
start_state.sha256 as null, so movie.loadAndArm -- which rejects a mismatch -- had
nothing to check and a drifting state replayed silently.

These guard the binding AND the honesty of the claim: the hashes give FORWARD
protection only. They cannot show a state still matches what its movie was recorded
against, because no recording-time hash ever existed.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "analysis/movie_state_hashes.json"


def man():
    return json.loads(MAN.read_text())


def test_every_anchored_movie_is_bound_to_a_state():
    d = man()
    assert d["movies"] >= 123
    assert d["movies_with_recorded_hash"] == d["movies"], "some fixture lost its hash"


def test_every_recorded_hash_matches_the_state_on_disk():
    """The check that fires when a .sav drifts."""
    d = man()
    assert d["movies_where_hash_matches_state"] == d["movies"], (
        "%d fixture(s) no longer match their state -- investigate before trusting any "
        "result derived from them"
        % (d["movies"] - d["movies_where_hash_matches_state"]))


def test_the_claim_is_scoped_to_forward_protection():
    """Overclaiming this as retroactive validation would certify an already-drifted
    fixture as good -- encoding an inference as a passing check."""
    p = man()["provenance"]
    assert "FUTURE drift" in p
    assert "Does NOT establish" in p


def test_shared_states_are_visible():
    """119 states back 123 movies; one drift can break several fixtures at once."""
    d = man()
    assert d["distinct_states"] < d["movies"]


def test_movies_stay_untracked():
    """860MB of captures on a 12GB repo; the manifest is the tracked evidence."""
    gi = (ROOT / ".gitignore").read_text()
    assert "*.movie.json" in gi or "movies/**" in gi
