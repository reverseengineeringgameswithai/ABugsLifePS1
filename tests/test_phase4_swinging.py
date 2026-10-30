"""Falsification and retained-evidence guards for Phase-4 A16."""
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
import phase4_swinging as swing  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_swinging.json"
ARTIFACT_SHA256 = "80aa3d28d1bd75e5cba6094870e1c7b2fdd4a09c8c707cd0db799bd20bc398fa"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    live_doc = doc["live"]
    natural = live_doc["natural_controls"]["summary"]
    if natural["negative_attachment_indices"] != [0, 0, 0] or \
            (natural["positive_attachment_index"], natural["positive_state"],
             natural["positive_grounded"], natural["positive_animation"]) != \
            (2, 5, 0, 4):
        gaps.append("natural Up+Cross boundary is incomplete")

    breadth = live_doc["breadth"]["summary"]
    if breadth["anchors_compared"] != 19 or \
            breadth["applicable_labels"] != [
                "bonus2_mushrooms", "stage01_anthill", "stage11_the_tree"] or \
            len(breadth["non_applicable_labels"]) != 16 or \
            not breadth["bonus2_reuses_stage01_layout"]:
        gaps.append("gameplay applicability breadth is incomplete")

    capacity = live_doc["direct_capacity"]["summary"]
    if capacity["declared_capacity"] != 8 or \
            capacity["distinct_active_slots_exercised"] != 10 or \
            not capacity["all_selected_target_slot"]:
        gaps.append("active record/capacity controls are incomplete")

    pendulum = live_doc["pendulum"]["summary"]
    if pendulum["samples"] != 13 or pendulum["attachment_indices"] != [2] or \
            pendulum["player_y_span"] <= 0 or \
            pendulum["record_velocity_equals_player_velocity_samples"] != 13:
        gaps.append("pendulum publication law is incomplete")

    trace = live_doc["writer_trace"]
    if trace["truncated"] or not {
            "0x800423c8", "0x800423dc", "0x800423f0"} <= set(
                trace["observed_instruction_pcs"]):
        gaps.append("pendulum writer attribution is incomplete")

    release = live_doc["release"]["summary"]
    if (release["idle_attachment_index"], release["release_attachment_index"],
            release["release_state"], release["release_animation"],
            release["record_claim_before"], release["native_minus_30_new_value"]) != \
            (2, 0, 1, 3, 1, 65506):
        gaps.append("native release boundary is incomplete")

    pause = live_doc["pause_resume"]
    if len(pause["frozen_fields"]) != 10 or not pause["pool_frozen"]:
        gaps.append("pause freeze is incomplete")
    if not live_doc["camera_dependency"]["camera_deltas_differ"]:
        gaps.append("camera attachment dependency is absent")

    transition = live_doc["transition_reset"]
    if transition["active_counts"] != [
            [16, 12, 16], [], [16, 22, 16, 22, 16, 16, 19], []] or \
            transition["attachment_indices"] != [2, 0, 0, 0]:
        gaps.append("scene initialization/reset evidence is incomplete")

    death = live_doc["death_respawn"]
    if death["before"]["fields"]["attachment_index"] != 2 or \
            death["fatal"]["fields"]["attachment_index"] != 0 or \
            death["respawn"]["fields"]["attachment_index"] != 0 or \
            death["respawn"]["fields"]["lives"] != \
            death["before"]["fields"]["lives"] - 1:
        gaps.append("native damage/respawn lifecycle is incomplete")
    return gaps


def test_static_swing_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = swing.build_static_census()
    assert recomputed == retained
    assert swing.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["acquire_and_pendulum"]["sha256"] == (
        "742395b7c8a0f04595bb6492d77bdd90d393708fd8be448aacf57282ee7187d2")
    assert recomputed["regions"]["detach_helper"]["sha256"] == (
        "5a7e215519cf6c29d5430158ab0efe9a947fd846ff005a20b2886d43af3adafd")


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = swing.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["pool_capacity"] = 9
    assert "swing pool capacity is not 8" in swing.static_census_gaps(mutated)

    executable = bytearray(swing.EXE_PATH.read_bytes())
    executable[swing._va_offset(0x80041F08)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        swing.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["natural_controls"]["summary"][
        "negative_attachment_indices"][0] = 2
    assert "natural Up+Cross boundary is incomplete" in evidence_gaps(mutated)
    mutated = copy.deepcopy(document)
    mutated["live"]["death_respawn"]["fatal"]["fields"][
        "attachment_index"] = 2
    assert "native damage/respawn lifecycle is incomplete" in evidence_gaps(mutated)


def test_retained_swing_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []

    cold = doc["live"]["cold_boot"]
    assert cold["checkpoint"] == 8000
    assert cold["player"]["scene"] == 1
    assert cold["pool"]["active_counts"] == [16, 12, 16]
    assert cold["pool"]["attachment_index"] == 0
    for key in ("started", "movie"):
        assert cold[key]["reproducible"] is True
        assert cold[key]["truncated"] is False

    release_events = doc["live"]["release"]["fresh_cross"]["trace"]["events"]
    decisive = {row["instruction_pc"]: row for row in release_events}
    assert decisive["0x80041ab4"]["new_value"] == 65506
    assert decisive["0x80041ab8"]["new_value"] == 0

    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_swinging.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_swing_schema_and_typed_records_match_the_live_boundary():
    schema = yaml.safe_load((ROOT / "config/phase4_swinging.yaml").read_text())
    records = yaml.safe_load((ROOT / "config/record_types.yaml").read_text())
    semantic = yaml.safe_load((ROOT / "config/semantic_state.yaml").read_text())
    assert schema["schema"] == "abl-phase4-swinging/1"
    assert schema["pool"]["capacity"] == 8
    assert int(schema["pool"]["stride"], 16) == 836
    assert int(schema["attachment"]["player_index"]["address"], 16) == \
        swing.ATTACHMENT_INDEX
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }

    record = next(row for row in records["records"]
                  if row["id"] == "swing_visual_record")
    assert (record["base"], record["size"], record["instances"]) == \
        (swing.POOL_BASE, swing.POOL_STRIDE, swing.POOL_CAPACITY)
    fields = {row["name"]: row for row in record["fields"]}
    assert fields["attachment_claim"]["offset"] == swing.CLAIM_OFFSET
    assert fields["dynamic_velocity_x"]["width"] == "s16"
    entries = {row["id"]: row for row in semantic["entries"]}
    assert entries["original.player_swing_attachment_index"]["address"] == \
        swing.ATTACHMENT_INDEX
    assert entries["original.swing_visual_pool"]["address"] == swing.POOL_BASE


def test_completed_swing_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "swing_attachment")
    finding = common.finding_index()["swing_attachment_controller"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)
