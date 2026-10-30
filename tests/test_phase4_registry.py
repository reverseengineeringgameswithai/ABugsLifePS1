"""Phase-4 registry, priority, inventory, and fixture guards."""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_inventory  # noqa: E402
import phase4_priority  # noqa: E402


def test_archive_tracking_excludes_provisioned_external_inputs(monkeypatch):
    def archive_run(command, *args, **kwargs):
        assert command[0] == "git"
        return subprocess.CompletedProcess(command, 128)

    monkeypatch.setattr(common.subprocess, "run", archive_run)
    assert common.git_tracked(
        "ObsidianVault/Canon/Systems/SYS_abdomen_bounce.md") is True
    assert common.git_tracked("level_14.sav") is False


def test_all_107_rows_have_one_primary_owner_across_twelve_families():
    registry = common.load_yaml(common.REGISTRY_PATH)
    mechanics = common.load_yaml(common.BASELINE_PATH)
    assert common.validate_registry(registry, mechanics) == []
    owners, duplicates = common.primary_owners(registry)
    assert duplicates == {}
    assert len(owners) == len(mechanics["rows"]) == 107
    assert set(owners) == {row["id"] for row in mechanics["rows"]}
    assert len(registry["families"]) == 12


def test_dependency_overlaps_never_change_primary_ownership():
    registry = common.load_yaml(common.REGISTRY_PATH)
    owners, _ = common.primary_owners(registry)
    dependency_mentions = {}
    for family in registry["families"]:
        for row_id in family["dependency_rows"]:
            dependency_mentions.setdefault(row_id, []).append(family["id"])
            assert owners[row_id] != family["id"]
    assert dependency_mentions, "cross-system dependencies were not inventoried"


def test_priority_is_derived_from_shared_surfaces_and_gaps():
    report = phase4_priority.build()
    assert report["registry_gaps"] == []
    assert report["work_package_1_met"] is True
    assert report["active_mod_demand_terms"] == []
    assert set(report["priority_order"][:7]) == common.CORE_FAMILIES
    assert all("shared_symbol_edges" in row and "coverage_gap_count" in row
               for row in report["families"])


def test_phase3_bounded_frontiers_are_not_promoted_by_scaffold():
    handoff = common.handoff_constraints()
    assert handoff["preserved"] is True
    assert all(handoff["checks"].values())


def test_iteration58_scorecard_adds_pause_without_promoting_phase_completion():
    coverage = phase4_coverage.build()
    assert coverage["counts"] == {
        "baseline_rows": 107,
        "campaign_complete": 15,
        "reviewed_absent": 1,
        "complete_total": 16,
        "open": 91,
    }
    assert coverage["families"]["input_player_actions"]["derived_status"] == "complete"
    assert coverage["families"]["input_player_actions"]["completed_rows"] == 11
    assert coverage["families"]["movement_world_physics"]["derived_status"] == "complete"
    assert coverage["families"]["movement_world_physics"]["completed_rows"] == 1
    assert coverage["families"]["objects_events_hazards"]["derived_status"] == "active"
    assert coverage["families"]["objects_events_hazards"]["completed_rows"] == 3
    assert coverage["families"]["audio_cinematics"]["derived_status"] == "active"
    assert coverage["families"]["audio_cinematics"]["completed_rows"] == 0
    assert coverage["families"]["audio_cinematics"]["open_rows"] == [
        "E12_audio", "E15_fmv"]
    assert coverage["families"]["player_lifecycle"]["derived_status"] == "active"
    assert coverage["families"]["player_lifecycle"]["completed_rows"] == 0
    assert coverage["families"]["player_lifecycle"]["open_rows"] == [
        "C15_respawn_anchor", "C16_lives_gameover"]
    assert coverage["families"]["hud_frontend_persistence"][
        "derived_status"] == "active"
    assert coverage["families"]["hud_frontend_persistence"][
        "completed_rows"] == 1
    assert coverage["families"]["hud_frontend_persistence"]["open_rows"] == [
        "A19_status_display", "C17_movie_viewer", "E13_hud_results",
        "E14_frontend_save"]
    assert coverage["families"]["bosses_special_objectives"][
        "derived_status"] == "active"
    assert coverage["families"]["bosses_special_objectives"][
        "completed_rows"] == 0
    assert {"D18_thud", "F09_bug_bar"}.issubset(
        coverage["families"]["bosses_special_objectives"]["open_rows"])
    assert coverage["families"]["collectibles_equipment_rewards"][
        "derived_status"] == "active"
    assert coverage["families"]["collectibles_equipment_rewards"][
        "completed_rows"] == 0
    assert {"C01_grain_pickup", "C02_fifty_grain_reward",
            "C13_grain_harvester"}.issubset(
        coverage["families"]["collectibles_equipment_rewards"]["open_rows"])
    assert all(row["derived_status"] == "pending" for family, row in
               coverage["families"].items()
               if family not in ("input_player_actions", "movement_world_physics",
                                 "objects_events_hazards", "audio_cinematics",
                                 "player_lifecycle", "bosses_special_objectives",
                                 "hud_frontend_persistence",
                                 "collectibles_equipment_rewards"))
    assert coverage["rows"]["A01_move_run"]["state"] == "campaign_complete"
    assert coverage["rows"]["A02_slow_walk"]["state"] == "campaign_complete"
    assert coverage["rows"]["A03_jump"]["state"] == "campaign_complete"
    assert coverage["rows"]["A04_kick"]["state"] == "campaign_complete"
    assert coverage["rows"]["A05_abdomen_bounce"]["state"] == "campaign_complete"
    assert coverage["rows"]["A06_downhill_slide"]["state"] == "campaign_complete"
    assert coverage["rows"]["A07_spin"]["state"] == "campaign_complete"
    assert coverage["rows"]["A08_berry_throw"]["state"] == "campaign_complete"
    assert coverage["rows"]["A16_swinging"]["state"] == "campaign_complete"
    assert coverage["rows"]["A17_camera_controls"]["state"] == "campaign_complete"
    assert coverage["rows"]["A18_pause"]["state"] == "campaign_complete"
    assert coverage["rows"]["A20_circle_noop"]["state"] == "reviewed_absent"
    assert coverage["rows"]["E02_collision"]["state"] == "campaign_complete"
    assert coverage["rows"]["E06_contact_object_pool"]["state"] == "campaign_complete"
    assert coverage["rows"]["E07_event_vm"]["state"] == "campaign_complete"
    assert coverage["rows"]["E09_grain_gates"]["state"] == "campaign_complete"
    assert coverage["rows"]["E15_fmv"]["state"] == "open"
    assert coverage["work_packages"]["WP1"]["met"] is True
    assert coverage["work_packages"]["WP6"]["met"] is True
    assert all(not coverage["work_packages"][name]["met"]
               for name in ("WP2", "WP3", "WP4", "WP5"))
    assert coverage["overall_met"] is False


def test_generator_artifact_test_and_schema_discovery_has_no_omissions():
    inventory = phase4_inventory.build_campaign_inventory()
    for key in (
        "missing_generator_declarations", "stale_generator_declarations",
        "orphan_artifacts", "missing_declared_outputs",
        "missing_test_declarations", "stale_test_declarations",
        "missing_schema_declarations", "stale_schema_declarations",
        "source_surface_mismatches", "registry",
    ):
        assert inventory["gaps"][key] == [], f"{key}: {inventory['gaps'][key]}"


def test_retained_artifact_source_dependencies_are_recomputed_and_visible():
    inventory = phase4_inventory.build_campaign_inventory()
    gaps = inventory["gaps"]["artifact_source_dependency_mismatches"]
    assert gaps == []
    assert inventory["structural_ready"] is True
    assert inventory["artifact_source_dependencies_fresh"] is True
    assert inventory["closure_ready"] is True


def test_inventory_breaks_generated_consumer_hash_cycles_semantically():
    inventory = phase4_inventory.build_campaign_inventory()
    outputs = {
        output["path"]: output
        for generator in inventory["generators"].values()
        for output in generator["outputs"]
    }
    for path in (
        "analysis/phase4_offline_opportunity_queue.json",
        "analysis/phase4_live_escalations.json",
    ):
        assert outputs[path]["comparison"] == "semantic_recompute"
        assert outputs[path]["sha256"] is None


@pytest.mark.local_media
def test_all_fixture_bytes_match_central_pins_after_provisioning():
    audit = phase4_inventory.build_fixture_audit()
    assert audit["structural_ready"] is True, audit["structural_gaps"]
    assert audit["counts"]["baseline_rows"] == 107
    assert audit["counts"]["rows_with_phase2_pristine_trigger"] == 80
    assert audit["counts"]["rows_with_phase2_blocker"] == 27
