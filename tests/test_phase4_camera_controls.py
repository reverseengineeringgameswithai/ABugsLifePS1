"""Falsification and retained-evidence guards for Phase-4 A17."""
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
import phase4_camera_controls as camera  # noqa: E402
import phase3_semantic_lifetime as lifetime  # noqa: E402
import phase4_common as common  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_camera_controls.json"
ARTIFACT_SHA256 = "b46154304f59454d96739ceeac0876815a5272d28ff4a61d7b2fc6b80af47ccf"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    controls = doc["live"]["controls"]["summary"]
    if controls["neutral"]["held_modes"] != [0] or \
            controls["neutral"]["camera_changed"] is not False:
        gaps.append("neutral camera control is incomplete")
    if controls["l1"]["final_mode"] != 2 or \
            abs(controls["l1"]["final_distance"] - 600) > 32 or \
            controls["l1"]["camera_changed"] is not True:
        gaps.append("L1 manual camera law is incomplete")
    if controls["r1"]["final_mode"] != 3 or \
            abs(controls["r1"]["final_distance"] - 1400) > 32 or \
            controls["r1"]["final_vertical_target"] != 24576:
        gaps.append("R1 lock camera law is incomplete")
    if controls["l1_up"]["final_vertical_target"] != 32768 or \
            controls["l1_down"]["final_vertical_target"] != 4096 or \
            abs(controls["l1_down"]["final_orbit_bias"] - 12288) > 2304 or \
            controls["l1_left"]["final_pitch_step"] <= 0 or \
            controls["l1_right"]["final_pitch_step"] >= 0:
        gaps.append("L1 directional controls are incomplete")
    if controls["l1_r1"]["final_mode"] != 2:
        gaps.append("L1/R1 precedence is incomplete")
    for name in ("l1", "r1", "l1_up", "l1_down", "l1_left",
                 "l1_right", "l1_r1"):
        row = controls[name]
        if (row["release_mode"], row["release_distance"],
                row["release_vertical_target"], row["release_orbit_bias"],
                row["release_suppression_timer"]) != (0, 900, 12288, 0, 0):
            gaps.append(f"{name} release/reset is incomplete")

    breadth = doc["live"]["breadth"]["summary"]
    if breadth["anchors_compared"] != 19 or \
            len(breadth["standard_manual_labels"]) != 17 or \
            breadth["l1_only_labels"] != ["stage09_bug_bar"] or \
            breadth["manual_disabled_labels"] != ["stage14_riverbed_flight"] or \
            breadth["r1_mode_without_16_frame_output_change_labels"] != \
            ["bonus2_mushrooms"] or \
            (breadth["l1_camera_changed_anchors"],
             breadth["r1_camera_changed_anchors"]) != (18, 16):
        gaps.append("gameplay applicability breadth is incomplete")

    pause = doc["live"]["pause_resume"]
    if pause["camera_frozen"] is not True or \
            (pause["paused_after_l1"]["mode"],
             pause["resumed_after_l1"]["mode"]) != (0, 2):
        gaps.append("pause/resume camera lifecycle is incomplete")
    death = doc["live"]["death_respawn"]
    if death["armed"]["mode"] != 2 or death["respawn"]["mode"] != 0 or \
            death["respawn"]["fields"]["distance"] != 900 or \
            death["l1_reentry"]["mode"] != 2:
        gaps.append("death/respawn camera reset is incomplete")

    trace = doc["live"]["writer_trace"]
    l1_pcs = set(trace["l1"]["observed_instruction_pcs"])
    r1_pcs = set(trace["r1"]["observed_instruction_pcs"])
    if trace["l1"]["truncated"] or not {
            "0x8004dfd4", "0x8004dff0", "0x8004e01c",
            "0x8004e4c0", "0x800527f4", "0x80052a40"} <= l1_pcs:
        gaps.append("L1 writer/HUD attribution is incomplete")
    if trace["r1"]["truncated"] or not {
            "0x8004dfd4", "0x8004e070", "0x8004e1cc",
            "0x8004e490", "0x80052a40"} <= r1_pcs:
        gaps.append("R1 writer/HUD attribution is incomplete")
    cold = doc["live"]["cold_boot"]
    if cold["branches"]["l1"]["pre_edit_camera_equal"] is not True or \
            cold["branches"]["r1"]["pre_edit_camera_equal"] is not True or \
            (cold["branches"]["l1"]["after"]["mode"],
             cold["branches"]["r1"]["after"]["mode"]) != (2, 3):
        gaps.append("cold-boot L1/R1 control is incomplete")
    return gaps


def test_static_camera_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = camera.build_static_census()
    assert recomputed == retained
    assert camera.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["regions"]["camera_follow_update"]["sha256"] == (
        "121e043eba504843e57ee8df295fa4e88607bc5fe75cc800c55409476e8c66ca")
    assert recomputed["regions"]["camera_reset"]["sha256"] == (
        "44ea612d99d94718a92fdadbda47b9f60225cc3e65d4fd744d699145b09943ce")


def test_camera_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = camera.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["law"]["mode_domain"]["r1_lock"] = 4
    assert "manual camera mode domain is incomplete" in \
        camera.static_census_gaps(mutated)
    executable = bytearray(camera.EXE_PATH.read_bytes())
    executable[camera._va_offset(0x8004E070)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        camera.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["controls"]["summary"]["l1_r1"]["final_mode"] = 3
    assert "L1/R1 precedence is incomplete" in evidence_gaps(mutated)
    mutated = copy.deepcopy(document)
    mutated["live"]["breadth"]["summary"]["manual_disabled_labels"] = []
    assert "gameplay applicability breadth is incomplete" in evidence_gaps(mutated)
    mutated = copy.deepcopy(document)
    mutated["live"]["death_respawn"]["respawn"]["mode"] = 2
    assert "death/respawn camera reset is incomplete" in evidence_gaps(mutated)


def test_retained_camera_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []
    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_camera_controls.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_camera_schema_and_typed_state_match_live_boundary():
    schema = yaml.safe_load((ROOT / "config/phase4_camera_controls.yaml").read_text())
    records = yaml.safe_load((ROOT / "config/record_types.yaml").read_text())
    semantic = yaml.safe_load((ROOT / "config/semantic_state.yaml").read_text())
    assert schema["schema"] == "abl-phase4-camera-controls/1"
    assert schema["selector"]["mode_domain"] == {
        "neutral": 0, "l1_manual": 2, "r1_lock": 3}
    assert schema["l1"]["distance_target"] == 600
    assert schema["r1"]["distance_target"] == 1400
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
    camera_record = next(row for row in records["records"]
                         if row["id"] == "camera_record")
    fields = {row["name"]: row for row in camera_record["fields"]}
    assert fields["follow_distance"]["offset"] == 0x1E
    assert fields["profile_and_suppression_timer"]["width"] == "u16"
    entries = {row["id"]: row for row in semantic["entries"]}
    assert entries["original.manual_camera_mode"]["address"] == camera.MODE_WORD
    assert entries["original.camera_orbit_bias"]["address"] == camera.ORBIT_BIAS
    assert entries["original.camera_vertical_target"]["address"] == \
        camera.VERTICAL_TARGET
    assert entries["original.camera_pitch_step"]["width"] == "s16"


def test_camera_lifecycle_promotion_requires_independent_nonzero_reset_evidence():
    evidence = lifetime.camera_lifecycle_evidence()
    assert evidence["sha256"] == ARTIFACT_SHA256
    assert all(evidence["guards"].values())
    retained = json.loads(
        (ROOT / "analysis/phase3_semantic_lifetime.json").read_text())
    assert retained["camera_lifecycle_evidence"] == evidence
    rows = retained["entries"]
    assert rows["original.manual_camera_mode"]["reset"] == "reset_to_zero"
    assert rows["original.camera_orbit_bias"]["reset"] == "reset_to_zero"
    assert rows["original.camera_vertical_target"]["reset"] == "reloaded"
    assert rows["original.camera_pitch_step"]["reset"] == "reset_to_zero"
    for identifier in (
            "original.manual_camera_mode", "original.camera_orbit_bias",
            "original.camera_vertical_target", "original.camera_pitch_step"):
        assert ARTIFACT_SHA256 in rows[identifier]["corroborated_by"]


def test_completed_camera_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "manual_camera_controls")
    finding = common.finding_index()["manual_camera_controller"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)
