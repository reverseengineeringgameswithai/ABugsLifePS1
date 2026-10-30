"""Gate for E16's Definition-of-Done scorecard.

A scorecard is a claim about how close a row is to solved, so the failure modes
worth catching are the flattering ones:

  * citing evidence that does not exist;
  * an item marked met without stating its scope, so a sub-area pass reads as a
    row-level one -- the overclaim this row has already retracted once;
  * drifting out of step with the roadmap, which is the actual standard.

The last is why this test parses the roadmap's own Definition-of-Done text rather
than trusting the tool's copy of it.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phase4_e16_dod_scorecard.py"
ART = ROOT / "analysis/phase4_e16_dod_scorecard.json"
ROADMAP = ROOT / "ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md"
VALID_STATES = {"met", "met_in_scope", "partial", "open"}


@pytest.fixture(scope="module")
def card():
    r = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    return json.loads(ART.read_text())


def test_every_cited_artifact_exists(card):
    """The tool checks this itself; the gate makes it fatal."""
    assert card["evidence_missing_from_disk"] == []
    assert not card["verdict"].startswith("BROKEN")


def test_it_scores_the_roadmap_s_nine_items_in_order(card):
    """Parsed from the roadmap, not from the tool's own list -- if the standard is
    edited, this fails instead of quietly scoring the wrong thing."""
    text = ROADMAP.read_text()
    start = text.index("## Definition of Done for a solved subsystem")
    # Bound the block at the next heading. A fixed character window overran into
    # the following numbered list and counted 11 items.
    nxt = text.find("\n## ", start + 1)
    block = text[start:nxt if nxt != -1 else len(text)]
    names = re.findall(r"^\d+\.\s+\*\*([^:]+):", block, re.M)
    assert len(names) == 9, f"roadmap DoD has {len(names)} items, not 9"
    slugs = [n.strip().lower().replace(" ", "_").replace("-", "_") for n in names]
    assert [i["id"] for i in card["items"]] == slugs
    assert [i["n"] for i in card["items"]] == list(range(1, 10))


def test_no_item_claims_more_than_it_shows(card):
    for item in card["items"]:
        assert item["state"] in VALID_STATES, item["state"]
        for field in ("requirement", "scope", "established", "missing", "next_experiment"):
            assert str(item.get(field) or "").strip(), f"{item['id']} missing {field}"
        if item["state"] in {"met", "met_in_scope"}:
            assert item["evidence"], f"{item['id']} claims met with no evidence"


def test_a_sub_area_pass_is_never_reported_as_row_level(card):
    """`met_in_scope` exists precisely so item 2 cannot read as 'E16's frontier is
    complete'. It is met for the three pointer tables; the streaming table,
    region A and the high heap are unmeasured, and the entry must say so."""
    frontier = [i for i in card["items"] if i["id"] == "complete_frontier"][0]
    assert frontier["state"] == "met_in_scope"
    assert "0x8009B5A8" in frontier["scope"]
    for token in ("0x8007EFE8", "region A", "high heap"):
        assert token in frontier["missing"], f"{token} must be named as out of scope"
    assert card["summary"]["met_in_scope"] >= 1
    assert card["scope_caveat"]


def test_the_row_is_not_reported_solved(card):
    """Six partial and one open. If this ever flips, it must be because the items
    moved -- not because the scorecard got generous."""
    s = card["summary"]
    assert s["row_is_solved"] is False
    assert s["partial"] + s["open"] > 0
    assert s["met"] + s["met_in_scope"] + s["partial"] + s["open"] == 9
    assert "NOT solved" in card["verdict"]


def test_it_names_the_standard_and_distinguishes_it_from_the_tool(card):
    """The drift that produced this scorecard: treating
    phase4_promotion_preflight.py as the bar. The artifact must record that the
    tool encodes the standard rather than being it."""
    assert "Definition of Done" in card["standard"]
    why = card["why_not_the_promotion_tool"]
    assert "1:1" in why and "judged by review" in why


def test_the_open_item_is_named_rather_than_buried(card):
    """The weakest item should be findable without reading all nine."""
    opens = [i for i in card["items"] if i["state"] == "open"]
    assert len(opens) == 1
    assert opens[0]["id"] == "cross_system_behavior"
    assert opens[0]["id"] in card["verdict"] or "cross-system" in card["verdict"]
