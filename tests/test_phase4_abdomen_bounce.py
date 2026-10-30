"""Falsification and retained-evidence guards for Phase-4 A05."""
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
import phase4_abdomen_bounce as abdomen  # noqa: E402
import phase4_common as common  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_abdomen_bounce.json"
ARTIFACT_SHA256 = "f7dec85ee70365cb98886ac749d8dd1e7b2ff4c749d0f4c5caf069349921dda1"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    boundary = doc["live"]["distance_boundary"]
    if (boundary["8192"]["after"]["fields"]["state"],
            boundary["8192"]["after"]["fields"]["slam_aux"]) != (3, 0):
        gaps.append("8192-unit near-floor boundary did not select state 3")
    if (boundary["8193"]["after"]["fields"]["state"],
            boundary["8193"]["after"]["fields"]["slam_aux"]) != (4, 9):
        gaps.append("8193-unit high-slam boundary did not select state 4/timer 9")

    breadth = doc["live"]["breadth"]["summary"]
    if breadth["anchors_compared"] != 19 or breadth["applicable_anchors"] != 18 or \
            len(breadth["high_slam_state_4_timer_9_labels"]) != 18:
        gaps.append("gameplay breadth is not 19 anchors / 18 ordinary high slams")
    if (breadth["exception_state"], breadth["exception_animation"],
            breadth["exception_slam_aux"]) != (0, 4, 0):
        gaps.append("Riverbed Flight exception changed")

    trace = doc["live"]["control_checked_trace"]
    if not all(trace["comparison"].get(key) is True for key in (
            "cycle_neutral", "same_cycle", "same_frame", "same_ram",
            "same_registers")):
        gaps.append("control-checked trace changed native execution")
    if len(trace["coverage"]) != 2 or any(
            row["coverage"]["truncated"] is not False
            for row in trace["coverage"]):
        gaps.append("decisive native coverage is absent or truncated")

    chain = doc["live"]["bonus1_five_stomp_chain"]
    if chain["checkpoints"]["128"]["player"]["bonus_streak"] != 1 or \
            chain["checkpoints"]["750"]["player"]["bonus_streak"] != 4:
        gaps.append("native consecutive-stomp chain did not reach streak 1 then 4")
    success = chain["checkpoints"]["1250"]["player"]
    if (success["scene"], success["bonus_streak"], success["bonus_latch"],
            success["bonus_flags"] & 2) != (0x10, 0, 6, 2):
        gaps.append("fifth native stomp did not unlock Bonus 1")
    response = chain["target_response"]
    if (response["before"]["response_state"],
            response["after"]["response_state"],
            response["after"]["response_54"],
            response["after"]["response_58"]) != (0, -20, 4096, 4096) or \
            response["player_health_before"] != response["player_health_after"]:
        gaps.append("accepted spider stomp target/player response changed")

    causal = doc["live"]["timer_counterfactual"]
    if not all((causal["pre_edit_fields_equal"], causal["pre_edit_block_equal"],
                causal["pre_edit_cycle_equal"])):
        gaps.append("timer counterfactual branches differ before the edit")
    control = causal["control_after"]["player"]
    edited = causal["edited_after"]["player"]
    if (control["bonus_streak"], control["fields"]["state"]) != (1, 4) or \
            (edited["bonus_streak"], edited["fields"]["state"],
             edited["fields"]["slam_aux"]) != (0, 5, 0) or \
            edited["fields"]["velocity_y"] >= 0:
        gaps.append("timer-zero causal branch did not rebound and reset")

    cold = doc["live"]["cold_boot"]
    if not all((cold["pre_edit_fields_equal"], cold["pre_edit_block_equal"],
                cold["pre_edit_cycle_equal"])) or \
            cold["control"]["samples"]["8384"]["player"]["fields"]["state"] != 4 or \
            cold["edited"]["after"]["fields"]["state"] != 2:
        gaps.append("cold-boot second-Cross counterfactual failed")

    pause = doc["live"]["pause_resume"]
    expected_frozen = ["x", "y", "z", "velocity_y", "state", "grounded",
                       "slam_aux", "animation"]
    if pause["frozen_fields"] != expected_frozen or \
            pause["paused"]["pause_flag"] != 1 or \
            pause["frozen"]["pause_flag"] != 1 or \
            pause["resumed"]["pause_flag"] != 0:
        gaps.append("pause did not freeze and resume high-slam state")

    death = doc["live"]["death_respawn"]
    if death["marked"]["fields"]["slam_aux"] != 7 or \
            death["respawn"]["fields"]["slam_aux"] != 0 or \
            death["fresh_double_cross"]["after"]["fields"]["state"] != 4 or \
            death["fresh_double_cross"]["after"]["fields"]["lives"] != \
            death["respawn"]["fields"]["lives"]:
        gaps.append("same-timeline respawn did not reset and re-enter A05")
    return gaps


def test_static_abdomen_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = abdomen.build_static_census()
    assert recomputed == retained
    assert abdomen.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["slam_branch"]["sha256"] == (
        "64e868b83ccc5206806df55d3d2facaea3e744931afa3df68c8dcf0a2fb460ef")
    assert recomputed["regions"]["stomp_branch"]["sha256"] == (
        "cbf87d52ea8149912d53027b12dca1b1f5339fc50fc8bfccf51a5d4de271927d")


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = abdomen.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["near_floor_distance_inclusive_max"] = 8191
    assert "near-floor maximum is not 8192" in abdomen.static_census_gaps(mutated)

    executable = bytearray(abdomen.EXE_PATH.read_bytes())
    executable[abdomen._va_offset(0x80048C8C)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        abdomen.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["timer_counterfactual"]["edited_after"]["player"][
        "bonus_streak"] = 1
    assert "timer-zero causal branch" in " ".join(evidence_gaps(mutated))
    mutated = copy.deepcopy(document)
    mutated["live"]["control_checked_trace"]["comparison"]["same_ram"] = False
    assert "control-checked trace" in " ".join(evidence_gaps(mutated))


def test_retained_abdomen_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []
    assert doc["live"]["operator_oracle"]["start"]["fields"]["state"] == 4
    assert doc["live"]["operator_oracle"]["start"]["fields"]["slam_aux"] == 1
    assert doc["live"]["timer_counterfactual"]["edited_after"]["player"][
        "fields"]["health"] == 3

    coverage = doc["live"]["control_checked_trace"]["coverage"]
    assert [(row["coverage"]["total_hits"],
             row["coverage"]["distinct_pc_count"])
            for row in coverage] == [(2532, 115), (54, 54)]
    controller_pcs = {row["pc"] for row in coverage[0]["coverage"]["counts_by_pc"]}
    contact_pcs = {row["pc"] for row in coverage[1]["coverage"]["counts_by_pc"]}
    assert {"0x80048c6c", "0x80048ca8", "0x80048cbc"} <= controller_pcs
    assert {"0x8004b2ac", "0x8004b31c", "0x8004b324",
            "0x8004b35c", "0x8004b3a8"} <= contact_pcs

    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_abdomen_bounce.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_completed_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "abdomen_bounce")
    finding = common.finding_index()["ordinary_abdomen_bounce"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_abdomen_schema_matches_static_and_live_boundaries():
    schema = yaml.safe_load(
        (ROOT / "config/phase4_abdomen_bounce.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-abdomen-bounce/1"
    assert int(schema["decoded_input"]["cross_mask"], 16) == \
        static["law"]["cross_mask"]
    assert schema["ordinary_controller"]["state_split"]["near_floor"].endswith(
        "state 3")
    assert schema["ordinary_controller"]["high_slam"]["slam_aux"]["arm"] == 10
    assert schema["resident_contact"]["target_response"]["state"] == -20
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
