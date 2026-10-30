"""Falsification and retained-evidence guards for Phase-4 A02."""
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

import live_session_provenance as live  # noqa: E402
import phase4_common as common  # noqa: E402
import phase4_slow_walk as slow  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_slow_walk.json"
ARTIFACT_SHA256 = "adb3a0b219bdc7dc0e8d39cd191e423464e7c8a01167d78be8f6602eb96d062e"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    breadth = doc["live"]["breadth"]["summary"]
    if breadth["anchors_compared"] != 19:
        gaps.append("gameplay breadth is not exactly 19 anchors")
    if breadth["applicable_anchors"] != 18:
        gaps.append("ground-locomotion breadth is not exactly 18 anchors")
    for key in ("walk_animation_29_labels", "run_animation_not_29_labels",
                "r2_up_observed_labels"):
        if len(breadth[key]) != 18:
            gaps.append(f"breadth predicate is incomplete: {key}")
    if breadth["exception_outcome_differences"]:
        gaps.append("flight negative diverged")

    cold = doc["live"]["cold_boot"]
    if cold["pre_edit_field_differences"] or not all((
            cold["pre_edit_block_equal"], cold["pre_edit_cycle_equal"],
            cold["pre_edit_emulator_frame_equal"])):
        gaps.append("cold-boot branches differ before the edit window")
    if cold["control"]["after"]["fields"]["animation"] == slow.WALK_ANIMATION:
        gaps.append("cold-boot run control selected walk animation")
    if cold["edited"]["after"]["fields"]["animation"] != slow.WALK_ANIMATION:
        gaps.append("cold-boot edited branch did not select walk animation")

    trace = doc["live"]["writer_trace"]
    pcs = {str(row["instruction_pc"]).lower() for row in trace["events"]}
    if trace["truncated"] or not {
            "0x8004848c", "0x800494ac", "0x800566d0", "0x800566e8"} <= pcs:
        gaps.append("decisive input/speed/animation trace is absent or truncated")
    return gaps


def test_static_slow_walk_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = slow.build_static_census()
    assert recomputed == retained
    assert slow.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["player_update"]["sha256"] == (
        "cab9a859cd6284a25c2ec4d0ba5072a0261b826a0497004e1a528dc0ebc74024")
    assert recomputed["regions"]["animation_gate"]["sha256"] == (
        "e5e7326c0a2d582ec0700353f5aedf6af951d795677312795d4284880fd15c57")


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = slow.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["slow_component_cap"] = 769
    assert "slow movement component cap is not 768" in slow.static_census_gaps(mutated)

    executable = bytearray(slow.EXE_PATH.read_bytes())
    executable[slow._va_offset(0x80048494)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        slow.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["breadth"]["summary"]["walk_animation_29_labels"].pop()
    assert "breadth predicate is incomplete: walk_animation_29_labels" in \
        evidence_gaps(mutated)
    mutated = copy.deepcopy(document)
    mutated["live"]["cold_boot"]["pre_edit_cycle_equal"] = False
    assert "cold-boot branches differ before the edit window" in evidence_gaps(mutated)


def test_retained_slow_walk_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []

    controls = doc["live"]["controls"]
    assert controls["l2_r2_outcome_differences"] == []
    shoulder = controls["shoulder_without_direction"]
    assert (shoulder["displacement_x"], shoulder["displacement_z"]) == (0, 0)
    assert shoulder["after"]["fields"]["animation"] != slow.WALK_ANIMATION
    release = controls["release_and_reentry"]
    assert [release[key]["fields"]["animation"] for key in (
        "first_walk", "released_to_run", "second_walk")] == [29, 0, 29]

    pause = doc["live"]["pause_resume"]
    assert pause["frozen_fields"] == ["x", "y", "z", "horizontal_speed", "animation"]
    assert pause["paused_start"]["pause_flag"] == 1
    assert pause["paused_after_r2_up"]["pause_flag"] == 1
    assert pause["resumed_after_r2_up"]["pause_flag"] == 0
    assert pause["resumed_after_r2_up"]["fields"]["animation"] == 29

    death = doc["live"]["death_respawn"]
    assert death["respawn"]["fields"]["health"] == 4
    assert death["respawn"]["fields"]["lives"] == death["before"]["fields"]["lives"] - 1
    assert death["respawn"]["scene"] == death["before"]["scene"]
    assert death["respawn"]["fields"]["animation"] == 29
    assert death["post_respawn_walk"]["fields"]["animation"] == 29

    cold = doc["live"]["cold_boot"]
    assert cold["edit_recipe"]["edited_frame_count"] == 60
    for side in ("control", "edited"):
        for key in ("started", "before_movie", "after_movie"):
            assert cold[side][key]["reproducible"] is True
            assert cold[side][key]["truncated"] is False

    trace = doc["live"]["writer_trace"]
    decisive = {row["instruction_pc"]: row for row in trace["events"]}
    assert decisive["0x8004848c"]["value"] == slow.R2_MASK | slow.UP_MASK
    assert decisive["0x800566e8"]["new_value"] == slow.WALK_ANIMATION
    assert trace["total"] == 19

    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_slow_walk.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_completed_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "slow_walk_modifier")
    finding = common.finding_index()["slow_walk_modifier_law"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_slow_walk_schema_matches_static_and_live_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_slow_walk.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-slow-walk/1"
    assert int(schema["decoded_input"]["slow_mask"], 16) == static["law"]["shoulder_mask"]
    assert schema["movement"]["default_component_bound"] == 1792
    assert schema["movement"]["slow_component_bound"] == 768
    assert schema["animation"]["slow_animation"] == 29
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
