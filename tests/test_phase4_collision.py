"""Falsification and retained-evidence guards for Phase-4 E02."""
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
import phase4_collision as collision  # noqa: E402
import phase4_common as common  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_collision.json"
ARTIFACT_SHA256 = "d1987d886559928ba48ba8dae9c97157ad25fdec3c9233311b427fba8cdf9399"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def evidence_gaps(doc: dict) -> list[str]:
    gaps: list[str] = []
    static = doc["static_census"]
    gaps.extend(collision.static_census_gaps(static))
    breadth = doc["live"]["breadth"]["summary"]
    if breadth["anchors_compared"] != 19 or \
            breadth["applicable_candidate_anchors"] != 18:
        gaps.append("collision breadth is not exactly 19/18 anchors")
    if len(breadth["distinct_sector_table_hashes"]) != 19:
        gaps.append("all-stage runtime table census is not distinct and complete")
    if sorted(breadth["nonzero_region_codes"]) != [1, 2, 3, 4]:
        gaps.append("nonzero region-code domain is incomplete")
    if breadth["candidate_count_min"] <= 0 or \
            breadth["candidate_count_max"] >= collision.POINTER_STORAGE_SLOTS:
        gaps.append("candidate breadth is empty or exceeds pointer storage")
    if breadth["floor_or_slope_plane_samples"] <= 0 or \
            breadth["other_orientation_plane_samples"] <= 0:
        gaps.append("floor/slope and non-floor plane orientations were not both sampled")
    if len(breadth["movement_delta_labels"]) != 19:
        gaps.append("timing-matched movement branch did not differ in every context")
    if max(breadth["sector_counts"].values()) > collision.SECTOR_GRID_LIMIT:
        gaps.append("observed sector count exceeds the decoded grid limit")

    controls = doc["live"]["geometry_controls"]
    active = controls["active_sector_origin_shift"]
    planes = controls["current_sector_plane_ref_shift"]
    if active["player_y_delta_vs_baseline"] < 1500 or \
            active["floor_y_delta_vs_baseline"] < 1500 or \
            active["branch"]["after"]["fields"]["grounded"] == 0:
        gaps.append("active-sector origin causal control failed")
    if controls["distant_sector_origin_shift"]["post_fields_equal_baseline"] is not True:
        gaps.append("distant-sector negative control changed collision output")
    if planes["mutated_plane_count"] < 1 or \
            planes["player_y_delta_vs_baseline"] < 1500 or \
            planes["floor_y_delta_vs_baseline"] < 1500 or \
            planes["branch"]["after"]["fields"]["grounded"] == 0:
        gaps.append("plane-reference causal control failed")

    region = doc["live"]["region_exit"]
    if region["advance_until"]["reason"] != "condition" or \
            region["sector_177"]["index"] != 177 or \
            region["sector_177"]["region_code"] != 2 or \
            region["positive_query"]["v0"] != 2 or \
            region["negative_gate_query"]["v0"] != 0 or \
            region["after"]["transition_lever"] != 1:
        gaps.append("natural region-code exit or gate controls failed")

    trace = doc["live"]["resolver_trace"]
    required = ("player_integrator", "candidate_boundary", "swept_resolver",
                "resolved_y_commit", "region_code_query")
    if trace["execution"]["truncated"] or any(
            trace["by_label"][label]["truncated"] or
            not trace["by_label"][label]["events"] for label in required):
        gaps.append("resolver execution trace is absent or truncated")

    pause = doc["live"]["pause_resume"]
    if pause["frozen_fields"] != ["x", "y", "z", "floor_y", "grounded"]:
        gaps.append("pause did not freeze collision/player outputs")
    respawn = doc["live"]["death_respawn"]
    if respawn["respawn"]["fields"]["health"] != 4 or \
            respawn["respawn"]["fields"]["lives"] != \
            respawn["before"]["fields"]["lives"] - 1:
        gaps.append("native death/respawn lifecycle failed")
    reuse = doc["live"]["table_reuse"]
    if not reuse["level01_reloaded_equal"] or not reuse["level01_level02_different"]:
        gaps.append("scene table retirement/rebuild lifecycle failed")
    cold = doc["live"]["cold_boot"]
    if cold["pre_edit_field_differences"] or not all((
            cold["pre_edit_block_equal"], cold["pre_edit_cycle_equal"],
            cold["pre_edit_emulator_frame_equal"])):
        gaps.append("cold-boot branches diverged before the input edit window")
    return gaps


def test_static_collision_census_recomputes_from_pinned_pristine_inputs():
    retained = load_artifact()["static_census"]
    recomputed = collision.build_static_census()
    assert recomputed == retained
    assert collision.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert len(recomputed["regions"]) == 13
    assert recomputed["assets"]["classified_assets"] == 24
    assert recomputed["assets"]["collision_chunks_roundtripped"] == 28


def test_static_and_retained_leaf_mutations_turn_the_proof_red():
    census = collision.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["typed_contract"]["candidate_list"]["writer_has_bounds_check"] = True
    assert "collision capacity/failure contract drifted" in \
        collision.static_census_gaps(mutated)

    executable = bytearray(collision.EXE_PATH.read_bytes())
    executable[collision._va_offset(0x80036CEC)] ^= 1
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        collision.build_static_census(bytes(executable))

    document = load_artifact()
    mutated = copy.deepcopy(document)
    mutated["live"]["geometry_controls"]["active_sector_origin_shift"][
        "player_y_delta_vs_baseline"] = 0
    assert "active-sector origin causal control failed" in evidence_gaps(mutated)
    mutated = copy.deepcopy(document)
    mutated["live"]["region_exit"]["negative_gate_query"]["v0"] = 2
    assert "natural region-code exit or gate controls failed" in evidence_gaps(mutated)


def test_retained_collision_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert evidence_gaps(doc) == []

    breadth = doc["live"]["breadth"]
    for label, row in breadth["anchors"].items():
        assert 0 < row["sector_table"]["count"] <= collision.SECTOR_GRID_LIMIT
        assert len(row["sector_table"]["rows"]) == row["sector_table"]["count"]
        if label != collision.FLIGHT_LABEL:
            candidate = row["candidate_boundary"]
            assert 0 < candidate["count"] < collision.POINTER_STORAGE_SLOTS
            assert candidate["count"] == len(candidate["pointers"])
            assert candidate["count"] == len(candidate["sectors"])

    controls = doc["live"]["geometry_controls"]
    assert controls["active_sector_origin_shift"]["world_delta"] == 2048
    assert controls["current_sector_plane_ref_shift"]["local_ref_y_delta"] == 64
    assert controls["active_sector_origin_shift"]["player_y_delta_vs_baseline"] == 2070
    assert controls["current_sector_plane_ref_shift"]["player_y_delta_vs_baseline"] == 2070

    region = doc["live"]["region_exit"]
    assert region["advance_until"]["frames_advanced"] == 54
    assert region["sector_177"]["origin_x"] == -163008
    assert region["sector_177"]["origin_y"] == -169888
    assert region["sector_177"]["origin_z"] == -124832

    provenance = doc["run_provenance"]
    assert provenance["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_collision.py").read_bytes()).hexdigest()
    assert provenance["rpc_manifest"]["source"]["method_count"] == 203
    assert provenance["duckstation"]["revision"] == (
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5")
    assert provenance["duckstation"]["binary_sha256"] == (
        "c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec")
    assert provenance["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_completed_collision_campaign_and_finding_are_low_level_audited():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "collision_floor_planes")
    finding = common.finding_index()["collision_floor_plane_resolver"]
    assert common.audit_finding(finding) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertions in campaign["evidence"].values()
               for assertion in assertions)


def test_collision_schema_matches_static_and_live_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_collision.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-collision/1"
    assert schema["runtime_sector_table"]["stride"] == \
        static["typed_contract"]["sector_table"]["stride"]
    assert schema["runtime_sector_table"]["grid_scan_limit"] == \
        static["typed_contract"]["grid_sector_scan_limit"]
    assert schema["player_candidate_list"]["pointer_storage_slots"] == 400
    assert schema["player_candidate_list"]["append_has_bounds_check"] is False
    assert schema["plane_record"]["size"] == 0x20
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
