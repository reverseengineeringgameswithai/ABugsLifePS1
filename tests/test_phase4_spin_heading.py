"""Falsification and retained-evidence guards for Phase-4 A07."""
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
import phase4_spin_heading as spin  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_spin_heading.json"
ARTIFACT_SHA256 = "ce6a28f37ade07f8959d240bac48847b5fe7f49574bbeb63c1c8e7293a26e61a"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    controls = doc["live"]["controls"]["summary"]
    expected = ["stage01_ant_hill", "training_completion", "training_entry"]
    if sorted(controls["anchor_labels"]) != expected or \
            controls["anchors_with_opposite_signed_turn"] != expected or \
            controls["anchors_with_zero_special_fields"] != expected:
        gaps.append("exact source/reverse controls are incomplete")
    for row in doc["live"]["controls"]["anchors"].values():
        source = row["left_up_right_down"]["metrics"]
        reverse = row["left_down_right_up"]["metrics"]
        if source["post_left_signed_turn"] <= 0 or \
                reverse["post_left_signed_turn"] >= 0 or \
                max(source["max_bounded_turn_step"],
                    reverse["max_bounded_turn_step"]) > 256 or \
                source["direction_masks"] != [0, 16, 32, 64, 128] or \
                reverse["direction_masks"] != [0, 16, 32, 64, 128]:
            gaps.append("direction/heading trajectory law is incomplete")

    breadth = doc["live"]["breadth"]["summary"]
    if breadth["anchors_compared"] != 19 or \
            len(breadth["heading_responsive_labels"]) != 19 or \
            breadth["heading_disabled_labels"] != [] or \
            len(breadth["source_matches_neutral_special_field_labels"]) != 19:
        gaps.append("gameplay breadth is incomplete")

    trace = doc["live"]["writer_trace"]
    pcs = trace["observed_instruction_pcs"]
    if pcs["current_action_reads"] != ["0x80047f6c"] or \
            pcs["input_heading_writes"] != ["0x80048044"] or \
            not {"0x800491a4", "0x80049298", "0x800492a8"} <= \
            set(pcs["heading_writes"]):
        gaps.append("current-input/heading attribution is incomplete")
    for log in trace["logs"].values():
        if log["truncated"] or log["watch_cap_saturated"] or \
                log["returned"] != log["total"]:
            gaps.append("writer trace is incomplete")

    pause = doc["live"]["pause_resume"]
    if pause["player_block_frozen"] is not True or \
            pause["paused_metrics"]["heading_change_count"] != 0 or \
            pause["resumed_metrics"]["heading_change_count"] < 4:
        gaps.append("pause/resume lifecycle is incomplete")
    reset = doc["live"]["reload_reset"]
    if reset["heading_restored"] is not True or \
            reset["input_heading_restored"] is not True:
        gaps.append("reload reset is incomplete")
    respawn = doc["live"]["death_respawn"]
    if (respawn["respawn"]["health"], respawn["respawn"]["lives"]) != (4, 4) or \
            respawn["reentry_metrics"]["heading_change_count"] < 4:
        gaps.append("native respawn/re-entry is incomplete")
    cold = doc["live"]["cold_boot"]
    if not all(cold[key] for key in (
            "pre_edit_player_block_equal", "pre_edit_cycle_equal",
            "post_edit_heading_differs", "post_edit_position_differs")) or \
            any(cold["source"]["after"][key] != cold["neutral"]["after"][key]
                for key in ("state", "timer", "aux")):
        gaps.append("cold-boot causal control is incomplete")
    return gaps


def test_static_spin_heading_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = spin.build_static_census()
    assert recomputed == retained
    assert spin.static_census_gaps(recomputed) == []
    assert recomputed["regions"]["current_direction_helper"]["sha256"] == \
        "b807dab2754834cc14bd9d870cbafbe4921b8594d69229f88e502a03063b5d08"
    assert recomputed["law"]["input_history_storage"] is None
    assert recomputed["heading_xrefs"]["render_facing_reader"] is True


def test_spin_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = spin.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["input_history_storage"] = "0x80000000"
    assert "current-direction helper unexpectedly claims history storage" in \
        spin.static_census_gaps(mutated)
    executable = bytearray(spin.EXE_PATH.read_bytes())
    executable[spin._va_offset(0x80048044)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        spin.build_static_census(bytes(executable))

    doc = load_artifact()
    mutated_doc = copy.deepcopy(doc)
    mutated_doc["live"]["breadth"]["summary"]["heading_responsive_labels"] = []
    assert "gameplay breadth is incomplete" in evidence_gaps(mutated_doc)
    mutated_doc = copy.deepcopy(doc)
    mutated_doc["live"]["cold_boot"]["pre_edit_cycle_equal"] = False
    assert "cold-boot causal control is incomplete" in evidence_gaps(mutated_doc)


def test_retained_spin_heading_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []
    assert doc["classification"] == "positive_directional_heading_behavior"
    assert doc["secondary_lead"]["role"] == "non-authoritative trigger lead only"
    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_spin_heading.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_spin_schema_reuses_typed_heading_state_without_inventing_a_mode():
    schema = yaml.safe_load((ROOT / "config/phase4_spin_heading.yaml").read_text())
    records = yaml.safe_load((ROOT / "config/record_types.yaml").read_text())
    semantic = {row["id"]: row for row in yaml.safe_load(
        (ROOT / "config/semantic_state.yaml").read_text())["entries"]}
    assert schema["schema"] == "abl-phase4-spin-heading/1"
    assert schema["input_sequence"]["source_order"] == list(spin.SOURCE_ORDER)
    assert schema["controller"]["history_storage"] is None
    assert schema["applicability"]["responsive_anchors"] == 19
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions"}
    player = next(row for row in records["records"] if row["id"] == "player_block")
    fields = {row["name"]: row for row in player["fields"]}
    assert fields["heading"]["offset"] == 0x20
    assert fields["input_heading"]["offset"] == 0x28
    assert semantic["original.player_heading"]["address"] == spin.PLAYER_BASE + 0x20
    assert semantic["original.player_input_heading"]["address"] == spin.PLAYER_BASE + 0x28


def test_phase3_negative_remains_bounded_while_a07_positive_behavior_is_solved():
    old = json.loads((ROOT / "analysis/phase3_spin_functional.json").read_text())
    assert old["classification"] == "bounded_negative"
    assert old["disproven"] is False
    baseline = {row["id"]: row for row in yaml.safe_load(
        (ROOT / "analysis/mechanics_baseline.yaml").read_text())["rows"]}
    assert baseline["A07_spin"]["status"] == "solved"
    assert "phase4_spin_heading.json" in " ".join(
        str(value) for value in baseline["A07_spin"]["bindings"])


def test_completed_spin_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "directional_spin_heading")
    finding = common.finding_index()["directional_spin_heading_controller"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)
