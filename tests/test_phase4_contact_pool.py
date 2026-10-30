"""Falsification and retained-evidence guards for Phase-4 E06."""
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
import phase4_contact_pool as contact  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_contact_pool.json"
ARTIFACT_SHA256 = "e83d95c784fc171257915aabea7bee791a0607766b9ac792c79d1c9cf7af52db"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    gaps.extend(contact.static_census_gaps(doc["static_census"]))
    breadth = doc["live"]["breadth"]["summary"]
    if breadth["anchors"] != 19 or len(breadth["distinct_type3f_hashes"]) != 19:
        gaps.append("all-stage live type3f breadth is incomplete")
    if breadth["authored_live_kinds"] != sorted(contact.SOURCE_KIND_ROLES):
        gaps.append("all authored source kinds were not observed live")
    if len(breadth["distinct_descriptor_table_hashes"]) != 1:
        gaps.append("descriptor pointer-table identity changed across scenes")
    if breadth["allocator_occupied_max"] != 4 or breadth["pool_headroom_min"] != 60:
        gaps.append("pristine allocator occupancy/headroom drifted")

    controls = doc["live"]["allocator_controls"]
    if controls["ordinary_free"]["record"]["slot"] != 8 or \
            controls["ordinary_free"]["record"]["action_id"] != 20 or \
            controls["ordinary_free"]["record"]["lifetime_ttl_or_active_gate"] != 200:
        gaps.append("ordinary allocator construction control failed")
    if controls["occupied_skip"]["record"]["slot"] != \
            controls["occupied_skip"]["expected_selected_slot"]:
        gaps.append("occupied-slot negative control did not skip")
    if controls["dead_residue_reuse"]["record"]["slot"] != \
            controls["dead_residue_reuse"]["expected_selected_slot"] or \
            controls["dead_residue_reuse"]["record"]["position"][0] == 0x12345678:
        gaps.append("dead residue was not reused and overwritten")
    if controls["wrap_63_to_0"]["record"]["slot"] != 0 or \
            controls["wrap_63_to_0"]["cursor_after"] != 0:
        gaps.append("allocator cursor did not wrap from 63 to 0")

    walker = doc["live"]["walker_controls"]
    if walker["far_negative"]["before"]["lifetime_ttl_or_active_gate"] != 200 or \
            walker["far_negative"]["after"]["lifetime_ttl_or_active_gate"] != 200:
        gaps.append("ordinary far walker negative control changed the record")
    if walker["near_positive"]["before"]["lifetime_ttl_or_active_gate"] != 200 or \
            walker["near_positive"]["after"]["lifetime_ttl_or_active_gate"] != 1 or \
            walker["near_positive"]["after"]["state"] != 16:
        gaps.append("near walker contact action did not reproduce")
    if walker["invalid_coordinate_overflow"]["after"][
            "lifetime_ttl_or_active_gate"] != 1:
        gaps.append("invalid-coordinate overflow exception was not retained")

    projectile = doc["live"]["projectile_retirement"]
    if len(projectile["samples"]) < 8 or \
            projectile["retired"]["record"]["lifetime_ttl"] != 0 or \
            projectile["retired"]["player"]["fields"]["berries_in_flight"] != 0:
        gaps.append("shared-pool projectile TTL retirement failed")
    pause = doc["live"]["pause_resume"]
    if pause["paused"]["record"]["record_sha256"] != \
            pause["frozen"]["record"]["record_sha256"] or \
            pause["resumed"]["record"]["record_sha256"] == \
            pause["frozen"]["record"]["record_sha256"]:
        gaps.append("pause/resume pool lifecycle failed")
    respawn = doc["live"]["death_respawn"]
    if respawn["respawn"]["fields"]["health"] != 4 or \
            respawn["respawn"]["fields"]["berries_in_flight"] != 0 or \
            respawn["respawn"]["fields"]["lives"] != \
            respawn["before"]["fields"]["lives"] - 1:
        gaps.append("death/respawn pool reset failed")
    reuse = doc["live"]["scene_reuse"]
    if not all(reuse[key] for key in (
            "level01_type3f_reloaded_equal", "level01_descriptor_reloaded_equal",
            "level01_level02_type3f_different", "level01_pool_reloaded_equal")):
        gaps.append("scene unload/reload ownership failed")
    full = doc["live"]["full_capacity_last"]
    if len(full["armed"]["allocator_occupied_slots"]) != 64 or \
            full["call_outcome"].get("code") != -32005 or \
            (full["call_outcome"].get("data") or {}).get("reason") != "timeout":
        gaps.append("full-pool no-escape behavior did not reproduce")
    cold = doc["live"]["cold_boot"]
    if cold["pre_edit_field_differences"] or not all((
            cold["pre_edit_block_equal"], cold["pre_edit_cycle_equal"],
            cold["pre_edit_emulator_frame_equal"])) or \
            cold["edited"]["execution"]["spawn_return"]["events"][0]["regs"]["s1"] != "0x00000002":
        gaps.append("cold-boot pool allocation counterfactual failed")
    return gaps


def test_static_contact_pool_census_recomputes_from_pinned_pristine_inputs():
    retained = load_artifact()["static_census"]
    recomputed = contact.build_static_census()
    assert recomputed == retained
    assert contact.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["source_catalog"]["entry_count"] == 1058
    assert recomputed["source_catalog"]["authored_kind_count"] == 16
    assert recomputed["allocator_call_census"]["resident_count"] == 76
    assert recomputed["allocator_call_census"]["overlay_encoded_hit_count"] == 15


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = contact.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["typed_contract"]["allocation"]["full_pool_escape"] = "overwrite oldest"
    assert "allocator capacity/failure contract drifted" in \
        contact.static_census_gaps(mutated)
    mutated = copy.deepcopy(census)
    mutated["source_catalog"]["classification_counts"][
        "descriptor_index_not_authored_as_type3f_source"] = 32
    assert "50 descriptor indices were not exhaustively classified" in \
        contact.static_census_gaps(mutated)

    executable = bytearray(contact.EXE_PATH.read_bytes())
    executable[contact._va_offset(0x80059E7C)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        contact.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["allocator_controls"]["occupied_skip"]["record"]["slot"] = 8
    assert "occupied-slot negative control did not skip" in evidence_gaps(mutated)
    mutated = copy.deepcopy(document)
    mutated["live"]["full_capacity_last"]["call_outcome"]["code"] = 0
    assert "full-pool no-escape behavior did not reproduce" in evidence_gaps(mutated)


def test_retained_contact_pool_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_contact_pool.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["rpc_manifest"]["source"]["method_count"] == 207
    assert doc["run_provenance"]["duckstation"]["revision"] == (
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5")
    assert doc["run_provenance"]["duckstation"]["binary_sha256"] == (
        "91cbe22b2c2e22ad83d695988ada36bbabb22c65366cb5ec9e8e30784de93af6")
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_completed_contact_pool_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "contact_object_pool")
    finding = common.finding_index()["contact_object_pool_contract"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_contact_pool_schema_matches_static_and_live_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_contact_pool.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-contact-pool/1"
    assert schema["pool"]["capacity"] == static["typed_contract"]["pool"]["capacity"]
    assert schema["pool"]["stride"] == static["typed_contract"]["pool"]["stride"]
    assert schema["authored_source_catalog"]["authored_kinds"] == \
        static["source_catalog"]["authored_kinds"]
    assert schema["pool"]["full_pool_failure"].startswith("no escape")
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
