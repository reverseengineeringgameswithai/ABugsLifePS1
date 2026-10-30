"""Falsification guards for the generated E08 static class frontier."""

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_e08_class_frontier as frontier  # noqa: E402


def document() -> dict:
    return json.loads(frontier.OUTPUT.read_text())


def test_e08_class_frontier_recomputes_from_low_level_machine_layers():
    rebuilt = frontier.build()
    assert frontier.render(rebuilt) == frontier.OUTPUT.read_bytes()


def test_e08_class_frontier_is_exhaustive_joined_and_non_promoting():
    doc = document()
    assert doc["schema"] == "abl-phase4-e08-class-frontier/1"
    assert doc["valid"] is True and doc["errors"] == []
    assert doc["summary"] == {
        "behavior_classes": 54,
        "class_owners_promoted": 0,
        "controlled_unowned_classes": 19,
        "downstream_owned_classes": 7,
        "duplicate_type_words": 0,
        "missing_class_joins": 0,
        "moved_uncontrolled_classes": 0,
        "retained_absent_classes": 21,
        "retained_significant_classes": 5,
        "retained_timing_only_classes": 2,
        "selectors_outside_decoded_domain": 0,
        "uncontrolled_classes": 28,
        "unknown_callbacks": 0,
        "unowned_classes": 47,
    }
    rows = doc["frontier"]
    assert len(rows) == len({row["type_word"] for row in rows}) == 28
    assert all(row["program"]["decode_complete"] for row in rows)
    assert all(0 <= row["program_selector"] < 40 for row in rows)
    assert all(row["semantic_owner"] is None for row in rows)
    assert all(row["native_outcome_control"] is False for row in rows)
    assert doc["claim_boundary"]["complete_frontier_met"] is False
    assert doc["claim_boundary"]["coupled_rows_promoted"] == []


def test_e08_frontier_priority_is_derived_from_retained_evidence_and_interfaces():
    rows = document()["frontier"]
    assert [row["type_word"] for row in rows[:5]] == [
        "0x2528", "0x2629", "0x050d", "0x1b1f", "0x1e20"]
    assert [row["evidence_cohort"] for row in rows[:5]] == [
        "retained_significant"] * 5
    assert [row["type_word"] for row in rows[5:7]] == ["0x2223", "0x1f04"]
    assert [row["evidence_cohort"] for row in rows[5:7]] == [
        "retained_timing_only"] * 2
    assert all(row["evidence_cohort"] == "retained_absent" for row in rows[7:])
    assert rows[0]["program"]["id"] == "worm_section"
    assert rows[1]["program"]["id"] == "wall_worm_section"
    assert rows[2]["program"]["id"] == "bee"


def test_e08_frontier_pins_callback_bounds_sources_and_match_status():
    callbacks = document()["callback_census"]
    assert len(callbacks) == 10
    assert [row["start"] for row in callbacks] == sorted(
        row["start"] for row in callbacks)
    assert {row["match"] for row in callbacks} == {"asm", "c"}
    assert all(row["source_sha256"] != "0" * 64 for row in callbacks)
    assert all(row["source"].endswith((".c", ".s")) for row in callbacks)


def test_e08_frontier_falsifies_duplicate_or_missing_uncontrolled_class(
        monkeypatch):
    contacts = copy.deepcopy(frontier.common.load_json(frontier.CONTACTS_PATH))
    contacts["summary"]["remaining_uncontrolled_type_words"].append("0x050d")
    original = frontier.common.load_json
    monkeypatch.setattr(
        frontier.common, "load_json",
        lambda path: contacts if Path(path) == frontier.CONTACTS_PATH
        else original(path))
    with pytest.raises(ValueError, match="native-control class partition drifted"):
        frontier.build()


def test_e08_frontier_falsifies_selector_outside_decoded_domain(monkeypatch):
    props = copy.deepcopy(frontier.common.load_json(frontier.PROPS_PATH))
    row = next(
        item for item in props["live"]["source_actor_clusters"]["behavior_classes"]
        if item["type_word"].lower() == "0x050d")
    row["program_selector"] = 40
    original = frontier.common.load_json
    monkeypatch.setattr(
        frontier.common, "load_json",
        lambda path: props if Path(path) == frontier.PROPS_PATH else original(path))
    with pytest.raises(ValueError, match="selector outside decoded domain"):
        frontier.build()


def test_e08_frontier_falsifies_unknown_callback(monkeypatch):
    props = copy.deepcopy(frontier.common.load_json(frontier.PROPS_PATH))
    row = next(
        item for item in props["live"]["source_actor_clusters"]["behavior_classes"]
        if item["type_word"].lower() == "0x050d")
    row["callbacks"] = ["0x80040000"]
    original = frontier.common.load_json
    monkeypatch.setattr(
        frontier.common, "load_json",
        lambda path: props if Path(path) == frontier.PROPS_PATH else original(path))
    with pytest.raises(ValueError, match="resident callback census count drifted"):
        frontier.build()


def test_e08_frontier_falsifies_priority_evidence_drift(monkeypatch):
    offline = copy.deepcopy(frontier.common.load_json(frontier.OFFLINE_PATH))
    significant = offline["derived_findings"][
        "uncontrolled_type_words_with_significant_changes"]
    significant.remove("0x050d")
    original = frontier.common.load_json
    monkeypatch.setattr(
        frontier.common, "load_json",
        lambda path: offline if Path(path) == frontier.OFFLINE_PATH
        else original(path))
    with pytest.raises(ValueError, match="does not partition"):
        frontier.build()
