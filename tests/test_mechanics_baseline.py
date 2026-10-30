"""Phase-1 exit-gate ratchet: the mechanics baseline registry must stay complete.

Guards the registry shape (every row has status/evidence/fixture/next-experiment,
campaign matrix covers Training + 15 stages + 3 bonus rows, every manual enemy
family and boss has a row, referenced fixtures exist) so later phases cannot
silently drop a mechanic from the solve surface.
"""
import sys

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mechanics_baseline as mb  # noqa: E402


def test_registry_validates():
    doc = mb.load()
    errors = mb.validate(doc, require_fixtures=False)
    assert not errors, "mechanics baseline violations:\n" + "\n".join(errors)


@pytest.mark.local_media
def test_registry_fixtures_present_locally():
    doc = mb.load()
    errors = mb.validate(doc)
    assert not errors, "mechanics baseline violations:\n" + "\n".join(errors)


def test_registry_matches_source_note_scale():
    doc = mb.load()
    rows = doc["rows"]
    assert len(rows) >= 105
    # the strict-Solved rule: baseline says no gameplay row is Solved yet; a row
    # flipping to solved must come with a deliberate registry+note edit, not drift.
    assert not [r["id"] for r in rows if r["status"] == "solved"], \
        "a row claims Solved — confirm it meets the strict Definition of Done and update the note"


def test_every_row_names_a_next_experiment():
    doc = mb.load()
    for r in doc["rows"]:
        assert len(r["next"].strip()) > 20, f"{r['id']}: next-experiment too thin"
