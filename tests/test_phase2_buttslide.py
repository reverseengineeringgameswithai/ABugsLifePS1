"""Offline validation of the buttslide (A06) oracle artifact."""
import json

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "analysis" / "phase2_buttslide_oracle.json").read_text())


@pytest.mark.local_media
def test_fixture_pinned_and_deterministic():
    fx = DOC["fixture"]
    assert (ROOT / fx["movie"]).exists()
    assert (ROOT / fx["anchor"]).exists()
    assert len(fx["movie_sha256"]) == 64 and len(fx["anchor_sha256"]) == 64
    assert DOC["deterministic_across_replays"] is True


def test_slide_state_machine():
    s = DOC["series"]
    # walk baseline -> jump -> slam/dive (state 4, airborne) -> ground slide (5)
    assert s["300"]["state80"] == 0 and s["300"]["grounded"] == 1
    assert s["360"]["state80"] == 1 and s["360"]["grounded"] == 0
    assert s["380"]["state80"] == 4 and s["380"]["grounded"] == 0
    assert (s["400"]["anim_a"], s["400"]["anim_b"]) == (11, 12)
    assert s["400"]["state80"] == 4
    assert s["430"]["state80"] == 5 and s["430"]["grounded"] == 1


def test_slide_displacement_is_fast():
    s = DOC["series"]
    # ground-slide covers large distance between f460 and f500
    dx = s["500"]["pos"][0] - s["460"]["pos"][0]
    dz = s["500"]["pos"][2] - s["460"]["pos"][2]
    assert abs(dx) + abs(dz) > 30000
