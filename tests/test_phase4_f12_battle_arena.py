"""Guards for the F12 (Battle Arena stage) registry row.

F12's own named objective ("defeat Molt with crowd berries") is closed via
synthesis from D19_molt's bounded-exhausted investigation. See
tests/test_phase4_d19_molt.py for the underlying evidence guards.
"""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"


def _row_block(row_id):
    text = REGISTRY.read_text()
    start = text.index(f"  - id: {row_id}")
    end = text.index("\n  - id:", start + 10)
    return text[start:end]


def test_registry_status_is_partial_not_unresolved():
    block = _row_block("F12_battle_arena")
    assert "status: partial" in block
    assert "status: unresolved" not in block
    parsed = yaml.safe_load("rows:\n" + block)
    row = parsed["rows"][0]
    assert row["id"] == "F12_battle_arena"
    assert row["status"] == "partial"


def test_bindings_cite_d19_synthesis():
    block = _row_block("F12_battle_arena")
    assert "SYNTHESIZED FROM D19" in block
    assert "id=29" in block


def test_bindings_reconcile_the_two_overlay_claims():
    block = _row_block("F12_battle_arena")
    assert "LEVEL09_LEVEL" in block
    assert "LEVEL03/LEVEL1.BIN" in block
    assert "NOT a conflict" in block


def test_missing_field_scopes_to_stage_layout_not_boss_mechanics():
    block = _row_block("F12_battle_arena")
    assert "now closed via D19 synthesis" in block
    assert "arena layout" in block.lower()


def test_d19_row_also_partial():
    block = _row_block("D19_molt")
    assert "status: partial" in block
