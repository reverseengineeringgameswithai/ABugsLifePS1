"""Phase-3 guard: the object render-descriptor table (0x80096B98).

The mod-relevant facts: the kind -> descriptor POINTERS are the same in every
level. Post-load descriptor values are scene-dependent, but this snapshot census
does not identify the writer. The guard pins every byte-level observation and
rejects both a false stability claim and invented loader causality."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "analysis" / "phase3_render_descriptors.json").read_text())


def test_table_enumerated_across_every_anchor():
    assert D["anchors_used"] >= 40
    assert D["kinds_with_a_descriptor"] == 50
    assert D["fixture_sha256"], "no fixture pins (DoF #1)"


def test_pointer_table_is_scene_invariant():
    """The kind -> descriptor mapping itself does NOT change per level."""
    assert D["pointer_table_is_scene_invariant"] is True


def test_scene_dependent_and_invariant_bytes_are_exactly_accounted():
    """Strict-pristine evidence excludes four changes introduced by ALLMODS."""
    b = D["descriptor_bytes"]
    for off in ("+0x04", "+0x06"):
        assert b[off]["invariant"] is False, off
        assert b[off]["kinds_whose_value_changes_between_levels"] == 50, off
    expected_varying = {
        "+0x04": 50, "+0x06": 50, "+0x07": 50, "+0x08": 3, "+0x0A": 3,
    }
    assert D["scene_dependent_bytes"] == list(expected_varying)
    assert D["invariant_bytes"] == [
        "+0x00", "+0x01", "+0x02", "+0x03", "+0x05", "+0x09", "+0x0B",
    ]
    assert {off: row["kinds_whose_value_changes_between_levels"]
            for off, row in b.items() if not row["invariant"]} == expected_varying
    assert all(row["varying_kind_ids"] for row in b.values() if not row["invariant"])
    assert all(not row["varying_kind_ids"] for row in b.values() if row["invariant"])


def test_writer_causality_is_not_invented_from_cross_anchor_variance():
    writer = D["writer_attribution"]
    assert writer["status"] == "unresolved"
    assert "cross-anchor variance is not a write trace" in writer["reason"]
    assert "write watch" in writer["next_experiment"]
    assert "does not identify the writer" in D["verdict"]
    assert "loader REWRITES" not in D["verdict"]


def test_every_save_was_inspected_before_load():
    anchor = D["run_provenance"]["anchor"]
    inspections = anchor["state_inspections"]
    assert len(inspections) == D["anchors_used"]
    assert all(row["exists"] and row["valid"] and row["serial"] == "SCUS-94288"
               for row in inspections)
