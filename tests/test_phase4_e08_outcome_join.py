"""Guards for the deterministic E08 actor/source native-outcome join."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_e08_outcome_join as outcome_join  # noqa: E402


ARTIFACT = ROOT / "analysis/phase4_e08_outcome_join.json"
ARTIFACT_SHA256 = "bd731ed8e9bb5b4d40ee64bce3bf1cb859d95d22d45fc91593d690f85a3e1906"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_e08_outcome_join_recomputes_byte_semantically_from_retained_trials():
    retained = load_artifact()
    assert outcome_join.build() == retained
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    for name, row in retained["inputs"].items():
        path = ROOT / row["path"]
        assert name in outcome_join.INPUTS
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_exact_native_contact_partition_is_derived_from_raw_outcomes():
    doc = load_artifact()
    assert doc["summary"] == {
        "contact_controlled_type_words": 22,
        "exact_actor_source_joins": 28,
        "joined_representatives": 28,
        "missing_actor_source_joins": 0,
        "outcome_class_representatives": {
            "ordinary_contact_suppressed_0x800": 3,
            "ordinary_damage_kick_response": 20,
            "response_only_0x80": 3,
            "separate_actor_path_0x20": 2,
        },
        "unclassified_type_words_total": 47,
        "unclassified_type_words_with_native_contact_controls": 18,
        "unclassified_type_words_without_native_contact_control": 29,
    }
    controlled = set(doc["unclassified_type_words_with_native_contact_controls"])
    without = set(doc["unclassified_type_words_without_native_contact_control"])
    assert len(controlled) == 18
    assert len(without) == 29
    assert controlled.isdisjoint(without)
    assert len(controlled | without) == 47
    assert len(doc["type_words"]) == 22
    assert len(doc["representatives"]) == 28
    assert all(
        row["native_controls"][branch]["call"]["address"].lower()
        == "0x8004abf4"
        for row in doc["representatives"]
        for branch in ("neutral", "kick", "timer_12_slide")
    )


def test_natural_type_0109_control_retains_matched_accept_and_expire_outcomes():
    row = load_artifact()["natural_abdomen_control"]
    assert row["type_word"] == "0x0109"
    assert row["movie_frames"] == [124, 128]
    assert row["matched_before"]["slam_aux"] == 1
    assert row["accepted_bounce"] == {
        "actor_response_54": 4096,
        "actor_response_58": 4096,
        "actor_response_state": -20,
        "bonus_streak": 1,
        "cycle": 5287761987,
        "frame": 9340,
        "health": 4,
    }
    assert row["expired_contact"] == {
        "actor_response_state": 15,
        "bonus_streak": 0,
        "cycle": 5287761987,
        "edit": "at movie frame 124 write player+0x84 u16 1 -> 0",
        "frame": 9340,
        "health": 3,
    }


def test_low_level_mutations_break_the_join_instead_of_trusting_summaries():
    kick = json.loads((ROOT / "analysis/phase4_kick.json").read_text())
    trial = copy.deepcopy(
        kick["live"]["contact_matrix"]["trials"]["10:4002"])
    trial["kick"]["after"]["actor"]["state"] = 15
    with pytest.raises(SystemExit, match="raw outcomes contradict"):
        outcome_join._validate_kick_pair("mutated", trial)

    props = json.loads((ROOT / "analysis/phase4_props_movers.json").read_text())
    props["live"]["source_actor_clusters"]["summary"][
        "all_actor_source_ids_match"] = False
    with pytest.raises(SystemExit, match="low-level breadth"):
        outcome_join._actor_index(props)


def test_e08_schema_and_campaign_keep_the_new_evidence_honestly_open():
    schema = yaml.safe_load((ROOT / "config/phase4_props_movers.yaml").read_text())
    assert schema["schema"] == "abl-phase4-props-movers/5"
    assert schema["campaign_state"] == "active_partial"
    frontier = schema["native_contact_outcome_frontier"]
    assert {key: frontier[key] for key in (
        "artifact", "joined_representatives", "contact_controlled_type_words",
        "unclassified_with_native_contact_controls",
        "unclassified_without_native_contact_control",
        "natural_type_0x0109_control") } == {
        "artifact": "analysis/phase4_e08_outcome_join.json",
        "joined_representatives": 28,
        "contact_controlled_type_words": 22,
        "unclassified_with_native_contact_controls": 18,
        "unclassified_without_native_contact_control": 29,
        "natural_type_0x0109_control": "accepted abdomen bounce versus expired damaging contact",
    }
    assert frontier["aggregate_unclassified_with_native_outcome_controls"] == 19
    assert frontier["aggregate_unclassified_without_native_outcome_control"] == 28
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "props_movers_gates")
    assert campaign["status"] == "active"
    assert common.audit_campaign(campaign, registry, common.finding_index()) == [
        "props_movers_gates: status is not completed"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["E08_props_movers_gates"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91
