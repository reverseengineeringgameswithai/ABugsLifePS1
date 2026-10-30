"""Phase-3 generator/artifact/fixture inventory guard."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase3_evidence_inventory as inventory  # noqa: E402


def _without_date(doc):
    clean = dict(doc)
    clean.pop("generated", None)
    return clean


def test_inventory_is_fresh_and_no_generator_or_artifact_is_silently_omitted():
    retained = json.loads((ROOT / "analysis/phase3_evidence_inventory.json").read_text())
    computed = inventory.build_inventory()
    assert _without_date(retained) == _without_date(computed)
    summary = computed["summary"]
    assert summary["missing_generator_declarations"] == []
    assert summary["stale_generator_declarations"] == []
    assert summary["orphan_artifacts"] == []
    assert summary["missing_outputs"] == []


def test_reciprocal_audit_edges_use_semantic_freshness_not_impossible_hash_cycles():
    doc = inventory.build_inventory()
    for tool in ("tools/phase3_contradictions.py",
                 "tools/phase3_evidence_inventory.py",
                 "tools/phase3_gate_audit.py"):
        outputs = doc["generators"][tool]["outputs"]
        assert outputs and all(row["sha256"] is None for row in outputs)


def test_every_generator_mode_has_an_explicit_static_local_or_live_class():
    doc = inventory.build_inventory()
    allowed = {"static", "local_media", "live"}
    for generator, row in doc["generators"].items():
        assert row["modes"], generator
        assert {mode["classification"] for mode in row["modes"]} <= allowed
        assert all(mode["command"] for mode in row["modes"])


def test_live_provenance_and_isolation_are_complete_and_low_level_verifiable():
    doc = inventory.build_inventory()
    summary = doc["summary"]
    assert doc["closure_ready"] is True
    assert summary["live_artifacts_without_run_provenance"] == []
    assert summary["live_save_artifacts_without_preload_state_inspection"] == []
    assert summary["live_save_artifacts_with_non_pristine_origin"] == []
    assert summary["live_tools_with_hardcoded_default_token"] == []
    assert summary["live_tools_without_config_dir_argument"] == []
    assert summary["live_mode_environment_declaration_gaps"] == []
    assert summary["live_artifact_environment_mismatches"] == []
    assert summary["live_artifact_source_dependency_mismatches"] == []
    assert summary["live_artifact_reproduction_guard_failures"] == []
    assert summary["current_live_toolchain_gaps"] == []
    assert summary["tracked_input_mutations"] == []
    for tool, row in doc["generators"].items():
        live_modes = [m for m in row["modes"] if m["classification"] == "live"]
        for mode in live_modes:
            assert "--config-dir" in mode["command"], tool
            assert "--instance-state" in mode["command"], tool
            assert "--port" in mode["command"] and "--token" in mode["command"], tool
            reproduction = mode["reproduction"]
            assert all(flag in reproduction["launcher_command"]
                       for flag in ("--config-dir", "--port", "--token",
                                    "--binary", "--disc")), tool
            assert all(flag in reproduction["settings_command"]
                       for flag in ("--config-dir", "--port", "--binary",
                                    "--binary-sha256", "--profile")), tool
            assert reproduction["media"]["pin_source"] == "tools/build_baselines.json"
            assert len(reproduction["binary"]["sha256"]) == 64
        for retained in row["live_artifact_provenance"]:
            artifact = json.loads((ROOT / retained["artifact"]).read_text())
            provenance = artifact["run_provenance"]
            assert provenance["generator_sha256"] == row["tool_sha256"], tool
            assert provenance["provenance_helper_sha256"] == \
                row["shared_dependencies"][0]["sha256"], tool
            if any(inventory.LIVE_LAUNCHER_HELPER in
                   mode["reproduction"]["launcher_command"]
                   for mode in live_modes):
                assert provenance["launcher_helper_sha256"] == \
                    inventory.current_launcher_helper_sha256(), tool
            assert retained["source_dependency_gaps"] == [], tool
            assert retained["declared_environment_gaps"] == [], tool
            if not any(mode["reproduction"].get("immutable_snapshot_required")
                       for mode in live_modes):
                rpc = provenance["rpc_manifest"]
                assert rpc["semantic_sha256"] == \
                    inventory.rpc_manifest_semantic_sha256()
                assert rpc["source"]["status_sha256"] == \
                    inventory.CURRENT_RPC_MANIFEST["source"]["status_sha256"]
            assert provenance["debugger"]["recreated"] is True, tool
            assert provenance["cleanup"]["owned_pid_stopped"] is True, tool
            save_anchors = retained["save_anchors"]
            if save_anchors:
                assert retained["state_inspections_complete"] is True, tool
                assert retained["pristine_save_origin_gaps"] == [], tool
                inspections = provenance["anchor"]["state_inspections"]
                assert all(row["exists"] and row["valid"]
                           and row["serial"] == "SCUS-94288"
                           for row in inspections), tool
            media = provenance["anchor"]["media_identity"]
            assert media["rpc_before_hash"]["has_media"] is True, tool
            assert media["rpc_after_hash"]["has_media"] is True, tool
            assert media["rpc_before_hash"]["game_serial"] == media["game_serial"], tool
            assert media["rpc_after_hash"]["game_serial"] == media["game_serial"], tool
            assert media["hash_verification"]["pristine_verified"] is True, tool
            assert all(f["matches_pin"] for f in
                       media["hash_verification"]["files"].values()), tool


def test_inventory_rejects_stale_shared_helper_and_missing_state_media_provenance():
    """A helper-only guard change must reopen every stale retained live artifact."""
    artifact = ROOT / "analysis/phase3_camera_record.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        run = doc["run_provenance"]
        run["provenance_helper_sha256"] = "0" * 64
        inspection = run["anchor"]["state_inspections"][0]
        inspection.pop("fixture_declaration", None)
        inspection.pop("state_media_hash_verification", None)
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        computed = inventory.build_inventory()
        row = computed["generators"]["tools/phase3_camera_record.py"]
        retained = row["live_artifact_provenance"][0]
        assert computed["closure_ready"] is False
        assert retained["source_dependency_gaps"]
        assert any("fixture declaration" in gap
                   for gap in retained["pristine_save_origin_gaps"])
        assert any("embedded media hash verification" in gap
                   for gap in retained["pristine_save_origin_gaps"])
        assert computed["summary"]["live_artifact_source_dependency_mismatches"]
        assert "analysis/phase3_camera_record.json" in \
            computed["summary"]["live_save_artifacts_with_non_pristine_origin"]
    finally:
        artifact.write_text(original)


def test_transition_inventory_pins_the_operator_owned_card_seed_argument():
    row = inventory.build_inventory()["generators"]["tools/phase3_transition_reset.py"]
    live = next(m for m in row["modes"] if m["classification"] == "live")
    assert "--card-seed ~/.cache/abl/abl_card_seed.mcd" in live["command"]
    assert "tools/launch_repro_playback.sh" in live["reproduction"]["launcher_command"]
    assert "--card-seed ~/.cache/abl/abl_card_seed.mcd" in \
        live["reproduction"]["launcher_command"]
    assert live["reproduction"]["settings_profile"] == "movie-replay-v1"


def test_live_declarations_follow_the_current_rpc_manifest_not_historical_hashes():
    manifest = inventory.CURRENT_RPC_MANIFEST
    assert inventory.BINARY_PROFILES["normal"]["sha256"] == \
        manifest["binaries"]["build/bin/duckstation-qt"]["sha256"]
    assert inventory.BINARY_PROFILES["release"]["sha256"] == \
        manifest["binaries"]["build-release/bin/duckstation-qt"]["sha256"]
    assert inventory.BINARY_PROFILES["release_current"] == \
        inventory.BINARY_PROFILES["release"]


def test_generic_live_declarations_use_the_race_safe_owned_launcher():
    doc = inventory.build_inventory()
    for tool, row in doc["generators"].items():
        for mode in row["modes"]:
            reproduction = mode.get("reproduction") or {}
            if reproduction.get("settings_profile") != "isolated-defaults-v1":
                continue
            command = reproduction["launcher_command"]
            assert inventory.LIVE_LAUNCHER_HELPER in command, tool
            assert "--fork-launcher" in command and "--client" in command, tool


def test_inventory_rejects_training_fixture_without_exact_regeneration_evidence():
    artifact = ROOT / "analysis/phase3_training_anchor_fixture.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        doc["playback_generation"] = None
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        computed = inventory.build_inventory()
        failures = computed["summary"][
            "live_artifact_reproduction_guard_failures"]
        assert computed["closure_ready"] is False
        assert any("playback_generation is absent" in gap for gap in failures)
    finally:
        artifact.write_text(original)


def test_inventory_rejects_training_fixture_without_a_fresh_candidate():
    artifact = ROOT / "analysis/phase3_training_anchor_fixture.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        doc["playback_generation"]["candidate_generated_in_this_run"] = False
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        computed = inventory.build_inventory()
        failures = computed["summary"][
            "live_artifact_reproduction_guard_failures"]
        assert computed["closure_ready"] is False
        assert any("candidate_generated_in_this_run" in gap for gap in failures)
    finally:
        artifact.write_text(original)


def test_inventory_rejects_retained_live_source_identity_drift():
    artifact = ROOT / "analysis/phase3_camera_record.json"
    original = artifact.read_text()
    try:
        doc = json.loads(original)
        doc["run_provenance"]["rpc_manifest"]["source"]["status_sha256"] = "0" * 64
        artifact.write_text(json.dumps(doc, indent=1) + "\n")
        computed = inventory.build_inventory()
        mismatches = computed["summary"]["live_artifact_environment_mismatches"]
        assert computed["closure_ready"] is False
        assert any("phase3_camera_record.json" in gap
                   and "RPC source identity" in gap for gap in mismatches)
    finally:
        artifact.write_text(original)


def test_strict_pristine_aggregates_declare_the_retained_normal_binary():
    doc = inventory.build_inventory()
    for tool in ("tools/phase3_record_types.py", "tools/phase3_fn_ptr_fields.py",
                 "tools/phase3_render_descriptors.py"):
        live = next(mode for mode in doc["generators"][tool]["modes"]
                    if mode["classification"] == "live")
        assert live["reproduction"]["binary"] == inventory.BINARY_PROFILES["normal"]
        assert "build/bin/duckstation-qt" in live["reproduction"]["launcher_command"]


@pytest.mark.local_media
def test_jalr_static_refresh_preserves_banked_live_evidence_byte_for_byte():
    artifact = ROOT / "analysis/phase3_jalr_callbacks.json"
    before = artifact.read_bytes()
    proc = subprocess.run(
        [sys.executable, "tools/phase3_jalr_callbacks.py", "--no-live"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert artifact.read_bytes() == before
    retained = json.loads(before)
    assert retained["run_provenance"]
    assert set(retained["installed_handlers"]) == set(retained["global_callback_slots"])
