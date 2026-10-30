"""Guards for Phase-4 upstream dependency-identity reconciliation."""

import hashlib
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_reconcile_upstream_dependencies as reconcile  # noqa: E402


def test_reconciliation_is_bounded_current_and_provenance_preserving():
    report = json.loads(reconcile.OUTPUT.read_text())
    assert report["schema"] == "abl-phase4-upstream-dependency-reconciliation/1"
    assert report["valid"] is True and report["errors"] == []
    assert len(report["artifacts"]) == 36
    assert all(row["only_reconciled_metadata_or_joined_identity_changed"]
               for row in report["artifacts"])
    promoted = next(row for row in report["artifacts"]
                    if row["path"] == "analysis/phase4_c16_bonus_death.json")
    assert promoted["only_dependency_metadata_or_joined_identity_changed"] is False
    assert promoted["current_fixture_metadata"] == {
        "fixture": "movies/Bonus_Level_03.movie.json",
        "field": "fixture_census.movie.media_class",
        "before": "pristine_serial",
        "after": "pristine",
    }
    assert all(
        row["only_dependency_metadata_or_joined_identity_changed"] is True
        for row in report["artifacts"] if row is not promoted)
    assert all(row["historical_run_provenance_preserved"]
               for row in report["artifacts"])
    assert report["joined_live_escalation_config"] == \
        "config/phase4_live_escalations.yaml"
    assert report["joined_live_escalation_only_sha_leaves_changed"] is True
    assert len(report["joined_live_escalation_pins"]) == 21
    assert {row["path"] for row in report["joined_live_escalation_pins"]} == {
        "analysis/phase4_offline_seed_actions_batch.json",
        "analysis/phase4_offline_bonus_objectives_batch.json",
        "analysis/phase4_fmv_levelb_first_call.json",
        "analysis/phase4_fmv_menu_owner_coverage.json",
        "analysis/phase4_fmv_menu_phase_neutral_live.json",
        "analysis/phase4_fmv_levelb_reachability.json",
        "analysis/phase4_fmv_c16_selector_control_result.json",
        "analysis/phase4_fmv_decoded_record_control_result.json",
        "analysis/phase4_fmv_decoded_record_retention_result.json",
        "analysis/phase4_fmv_finale_route_probe.json",
        "analysis/phase4_fmv_cd_event_exit_result.json",
        "analysis/phase4_fmv_present_rect_height_function_trace_result.json",
        "analysis/phase4_fmv_levelb_region_b_dma_attempt.json",
    }
    assert all(row["behavioral_payload_preserved"] is True
               for row in report["joined_live_escalation_pins"])
    controlled_ids = {
        entry["id"] for entry in reconcile.common.load_yaml(
            ROOT / "config/phase4_live_escalations.yaml")["entries"]
        if (entry.get("execution_result") or {}).get("execution_kind") in {
            "atomic_batch_control", "phase_neutral_movie_control",
            "v2_receipt_set"}
    }
    assert "P4-ITER88-E15-LEVELB-PHASE-NEUTRAL-REVALIDATION" in controlled_ids
    controlled_pins = [
        row for row in report["joined_live_escalation_pins"]
        if row["pin_kind"] == "controlled_banked_analysis"]
    assert {row["entry_id"] for row in controlled_pins} == {
        "P4-ITER86-E15-LEVELB-LIFECYCLE-CONTROL",
        "P4-ITER87-E15-LEVELB-SAVE-ANCHOR-CONTROL",
        "P4-ITER88-E15-LEVELB-PHASE-NEUTRAL-REVALIDATION",
        "P4-ITER89-E15-LEVELB-FIRST-CALL-LIFECYCLE",
        "P4-ITER90-E15-FINALE-SEQUENCE-LIFECYCLE",
        "P4-ITER91-E15-FINALE-ENDPOINT-CORRECTION",
        "P4-ITER92-E15-MENU-NONBOOT-OWNER-COVERAGE",
        "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE",
        "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL",
        "P4-ITER99-E15-C16-STAGED-SELECTOR-LIFECYCLE-CONTROL",
        "P4-ITER102-E15-DECODED-RECORD-ABSENCE-CONTROL",
        "P4-ITER104-E15-DECODED-RECORD-RETENTION-CONTROL",
        "P4-ITER107-E15-CD-EVENT-EXIT-CONTROL",
        "P4-ITER114-E15-PRESENT-RECT-FUNCTION-CARDINALITY",
        "P4-R6-ITER2-E15-LEVELB-REGIONB-DMA-PROVENANCE",
    }
    assert all(row["pin_kind"] == "capsule_offline_analysis"
               for row in report["joined_live_escalation_pins"]
               if row not in controlled_pins)
    assert all(row["sha256_after"] == reconcile.file_sha(ROOT / row["path"])
               for row in report["joined_live_escalation_pins"])
    fmv = next(row for row in report["artifacts"]
               if row["path"] == "analysis/phase4_offline_fmv_batch.json")
    assert fmv["allowed_dependencies"] == [
        "analysis/phase4_trace_capsule_set.json", "config/phase4_fmv.yaml"]
    assert fmv["only_dependency_metadata_or_joined_identity_changed"] is True
    offline_paths = {
        f"analysis/phase4_offline_{name}_batch.json"
        for name in (
            "bonus_objectives", "collectibles", "contact", "e08", "fmv",
            "plant_power", "plant_weapon", "seed_actions", "seed_lifecycle",
            "traversal_plants",
        )
    }
    offline_rows = [
        row for row in report["artifacts"] if row["path"] in offline_paths]
    assert len(offline_rows) == len(offline_paths)
    assert all("analysis/phase4_trace_capsule_set.json"
               in row["allowed_dependencies"] for row in offline_rows)
    offline_e08 = next(
        row for row in offline_rows
        if row["path"] == "analysis/phase4_offline_e08_batch.json")
    assert "analysis/phase4_e08_hazard_outcomes.json" in \
        offline_e08["allowed_dependencies"]
    legacy_fmv = next(row for row in report["artifacts"]
                      if row["path"] == "analysis/phase4_fmv.json")
    assert legacy_fmv["allowed_dependencies"] == [
        "src_re/fmv_player_streaming.c"]
    assert legacy_fmv["only_dependency_metadata_or_joined_identity_changed"] is True
    assert legacy_fmv["historical_run_provenance_preserved"] is True
    reconciled_menu = {
        row["path"]: row for row in report["artifacts"]
        if row["path"] in {
            "analysis/phase4_fmv_menu_owner_coverage.json",
            "analysis/phase4_fmv_menu_phase_neutral_live.json",
        }
    }
    assert set(reconciled_menu) == {
        "analysis/phase4_fmv_menu_owner_coverage.json",
        "analysis/phase4_fmv_menu_phase_neutral_live.json",
    }
    assert all(row["allowed_dependencies"] == [
        "tools/phase4_duckstation_batch.py"]
        for row in reconciled_menu.values())
    dma_attempt = next(
        row for row in report["artifacts"]
        if row["path"] == "analysis/phase4_fmv_levelb_region_b_dma_attempt.json")
    assert dma_attempt["allowed_dependencies"] == [
        "analysis/phase3_duckstation_rpc_manifest.json",
        "tools/phase4_duckstation_batch.py",
    ]
    assert dma_attempt["historical_run_provenance_preserved"] is True
    for row in report["artifacts"]:
        assert set(row["dependency_sha256_after"]) == set(row["allowed_dependencies"])
        assert all(
            digest == reconcile.file_sha(ROOT / relative)
            for relative, digest in row["dependency_sha256_after"].items())


def test_reconciliation_rebuilds_identically():
    updates, report = reconcile.build()
    projected_hashes = {
        row["path"]: row["artifact_sha256_after"]
        for row in report["artifacts"]
    }
    config_bytes, _rows = reconcile.reconciled_live_escalation_config(
        report, artifact_hashes=projected_hashes)
    assert reconcile.report_rendered(report) == reconcile.OUTPUT.read_bytes()
    assert all(path.read_bytes() == reconcile.artifact_rendered(document)
               for path, document in updates)
    assert config_bytes == reconcile.LIVE_ESCALATION_CONFIG.read_bytes()
    assert hashlib.sha256(config_bytes).hexdigest() == \
        report["joined_live_escalation_config_sha256_after"]


def test_reconciliation_preserves_c16_producer_rendering():
    c16 = json.loads(
        (ROOT / "analysis/phase4_fmv_c16_selector_control_result.json").read_text())
    assert reconcile.artifact_rendered(c16) == (
        json.dumps(c16, indent=2, sort_keys=True) + "\n").encode()


def test_reconciliation_ignores_predeclared_unexecuted_escalations(
        tmp_path, monkeypatch):
    source = reconcile.common.load_yaml(reconcile.LIVE_ESCALATION_CONFIG)
    executed = next(
        entry for entry in source["entries"]
        if entry["id"] == "P4-ITER89-E15-LEVELB-FIRST-CALL-LIFECYCLE")
    planned = dict(executed)
    planned["id"] = "P4-TEST-PLANNED-ESCALATION"
    planned["state"] = "planned"
    planned.pop("execution_result")
    source["entries"].append(planned)
    assert planned["state"] == "planned"
    assert "execution_result" not in planned
    temporary = tmp_path / "phase4_live_escalations.yaml"
    temporary.write_text(yaml.safe_dump(source, sort_keys=False))
    monkeypatch.setattr(reconcile, "LIVE_ESCALATION_CONFIG", temporary)

    rendered, rows = reconcile.reconciled_live_escalation_config()

    rendered_source = yaml.safe_load(rendered)
    rendered_planned = next(
        entry for entry in rendered_source["entries"]
        if entry["id"] == planned["id"])
    assert rendered_planned == planned
    assert planned["id"] not in {row["entry_id"] for row in rows}
