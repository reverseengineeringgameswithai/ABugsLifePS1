"""Gate for B09's launch-plant reachability closure.

This closes a row item as a NEGATIVE, so the tests guard the two ways a negative
goes wrong: a chain link quietly changing, and the negative being broader than
the evidence supports.
"""
from __future__ import annotations

import json, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_b09_launch_plant_reachability.py"
ART = ROOT / "analysis/phase4_b09_launch_plant_reachability.json"
CENSUS = ROOT / "analysis/phase4_e08_object_census.json"


@pytest.fixture(scope="module")
def a():
    r = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    return json.loads(ART.read_text())


def test_the_negative_is_exactly_dandelion_and_cannon(a):
    """Not 'launch plants' generally -- mushroom and propeller ARE reachable, and
    stating the negative too broadly would be the overclaim."""
    assert a["co_occurrence"]["dandelion"] == []
    assert a["co_occurrence"]["cannon"] == []
    assert a["co_occurrence"]["mushroom"], "mushroom must remain reachable"
    assert a["co_occurrence"]["propeller"], "propeller must remain reachable"


def test_only_three_stage_files_can_grant_super_jump(a):
    sj = a["stages_where_super_jump_is_possible"]
    assert len(sj) == 3
    assert set(sj) == {"LEVEL01/LEVEL1.DAT", "LEVEL05/LEVEL.DAT", "LEVEL09/LEVEL.DAT"}


def test_no_super_jump_stage_carries_enough_orange_tokens(a):
    """The whole argument: dandelion needs 2 orange, cannon 3."""
    for s in a["stages"]:
        if s["super_jump_possible"]:
            assert s["orange_tokens"] <= 1
            assert s["max_brown_tier"] <= 2


def test_the_counts_come_from_the_census_per_FILE(a):
    """Per-directory aggregation merges stages (LEVEL01/ holds stage 1 and 6) and
    produced a table that contradicted the operator's play experience."""
    lv = json.loads(CENSUS.read_text())["levels"]
    for s in a["stages"]:
        h = lv[s["file"]]["type3f_kind_histogram"]
        assert h.get("0x2a", 0) == s["blue_tokens"]
        assert h.get("0x29", 0) == s["orange_tokens"]


def test_every_chain_link_is_recorded(a):
    c = a["chain"]
    assert "0x80046BEC" in c["fresh_level_lanes"]
    assert "(old+1)" in c["token_upgrade"]
    assert c["brown_tiers"]["3"] == "dandelion" or c["brown_tiers"][3] == "dandelion"
    assert "directory != stage" in c["granularity"]


def test_the_prediction_was_confirmed_by_measurement(a):
    """The bird level predicted brown max 1 and measured 1/1."""
    assert "measured 1" in a["confirmation"]
    assert "B08_SuperJump_EOL" in a["confirmation"]


def test_it_claims_a_reviewed_negative_not_a_deferral(a):
    assert "REVIEWED NEGATIVE" in a["verdict"]
    assert "not present in the pristine" in a["verdict"]
