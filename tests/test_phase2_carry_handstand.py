"""Offline validation of the seed-carry + handstand oracle (rows A09/A10)."""
import json

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "analysis" / "phase2_carry_handstand_oracle.json").read_text())


@pytest.mark.local_media
def test_fixture_pinned_and_deterministic():
    fx = DOC["fixture"]
    assert (ROOT / fx["movie"]).exists() and (ROOT / fx["anchor"]).exists()
    assert len(fx["movie_sha256"]) == 64 and len(fx["anchor_sha256"]) == 64
    assert DOC["deterministic_across_replays"] is True


def test_carry_identity_attachment():
    s = DOC["series"]
    assert DOC["laws"]["carry_attached_at_f660"] is True
    at = s["660"]
    assert at["player"][0] == at["rec0_xyz"][0]
    assert at["player"][2] == at["rec0_xyz"][2]
    # the untested-Y error caught by review: Y rides a FIXED 19200 overhead offset
    assert at["player"][1] - at["rec0_xyz"][1] == 19200
    assert DOC["laws"]["carry_y_offset"] == 19200
    assert at["rec0_id"] == 11          # movable seed class
    # before pickup the seed rests away from the player
    pre = s["290"]
    assert (abs(pre["player"][0] - pre["rec0_xyz"][0])
            + abs(pre["player"][2] - pre["rec0_xyz"][2])) > 8000
    # after the drop it detaches again
    post = s["700"]
    assert (abs(post["player"][0] - post["rec0_xyz"][0])
            + abs(post["player"][2] - post["rec0_xyz"][2])) > 8000


def test_handstand_signature():
    s = DOC["series"]
    assert DOC["laws"]["handstand_frozen"] is True
    for mf in ("1120", "1160", "1200"):
        assert s[mf]["grounded"] == 0, mf     # mounted = airborne-flagged
    assert s["1240"]["s80"] == 6              # dismount hop state
