"""Falsification and retained-evidence guards for the active Phase-4 E15 campaign."""
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
import phase4_coverage  # noqa: E402
import phase4_fmv as fmv  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_fmv.json"
ARTIFACT_SHA256 = "19070548afd0f0182917c9905a926fefcc7c7ce4375db68017fe1994fe8716ce"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_retained_e15_control_recomputes_exact_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    assert doc["campaign_state"] == "active_partial"
    assert fmv.evidence_gaps(doc) == []
    assert doc["run_provenance"]["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_fmv.py").read_bytes()).hexdigest()
    assert doc["run_provenance"]["rpc_manifest"]["source"]["method_count"] == 203
    assert doc["run_provenance"]["duckstation"]["revision"] == (
        "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5")
    assert doc["run_provenance"]["duckstation"]["binary_sha256"] == (
        "c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec")
    assert doc["run_provenance"]["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=False) == []


def test_input_residency_and_trace_mutations_turn_the_e15_proof_red():
    doc = load_artifact()
    mutated = copy.deepcopy(doc)
    mutated["live"]["start_removed_control"]["pre_trigger"][
        "cycle_neutral_trace"]["control"]["ram_sha256"] = "00" * 32
    assert "pre-trigger ram_sha256 diverged" in " ".join(fmv.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["natural_start_skip"]["post_trigger"]["snapshot"][
        "status"]["pc"] = "0x800b98f0"
    assert "post-input PCs changed" in " ".join(fmv.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["natural_start_skip"]["final"]["snapshot"][
        "region_b"]["overlay_resident"] = True
    assert "overlay residency divergence changed" in " ".join(
        fmv.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["start_removed_control"]["final"][
        "cycle_neutral_trace"]["coverage"][0]["total_hits"] = 0
    assert "cycle-neutral and complete" in " ".join(fmv.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["cold_boot_natural_completion"]["points"][
        "title_reset"]["snapshot"]["region_b"]["resident_fields"][
            "selected_frame_limit"] = 440
    assert "typed boundary title_reset changed" in " ".join(
        fmv.evidence_gaps(mutated))

    mutated = copy.deepcopy(doc)
    mutated["live"]["cold_boot_natural_completion"]["points"][
        "intro_completed"]["cycle_neutral_trace"]["control"][
            "ram_sha256"] = "00" * 32
    gaps = " ".join(fmv.evidence_gaps(mutated))
    assert "control/instrumented signatures diverged" in gaps
    assert "retained signature changed" in gaps

    mutated = copy.deepcopy(doc)
    mutated["live"]["cold_boot_natural_completion"]["points"][
        "frontend_transition"]["cycle_neutral_trace"]["coverage"][4][
            "total_hits"] = 0
    assert "zero-coverage frontier" in " ".join(fmv.evidence_gaps(mutated))


@pytest.mark.local_media
def test_static_manifest_and_external_fixture_census_recompute_from_pins():
    doc = load_artifact()
    assert fmv.build_static_census() == doc["static_census"]
    assert fmv.build_fixture_census() == doc["fixture_census"]
    rows = doc["static_census"]["manifest_and_frame_table"]["entries"]
    assert len(rows) == 40
    assert all(int(row["instruction_word"], 16) ==
               0x24050000 | row["frame_count"] for row in rows)
    assert rows[3]["path"] == "BUGSFMV1/LEV1A.STR"
    assert rows[3]["frame_count"] == 386
    cold = doc["fixture_census"]["cold_boot_movie"]
    assert cold == {
        "path": "movies/go_to_end/LEVEL01.movie.json",
        "sha256": "bfedc0d0f4828998fc598257b35ad090180ad6cb01ea317bc40229f977dc40fb",
        "size": 7631156,
        "media_class": "pristine_serial",
        "version": 3,
        "frames": 10348,
        "initial_frame": 1,
        "from_boot": True,
        "non_neutral_frame_count": 7429,
        "first_non_neutral_frame": 1758,
        "last_non_neutral_frame": 10347,
        "non_neutral_frames_sha256": (
            "59c6cc2d2375fdfe91b25e8c84de36a6560ca5617f4f3a162022b1e1d212c77c"),
    }


def test_natural_boot_completion_reuse_and_frontend_handoff_are_exact():
    doc = load_artifact()
    cold = doc["live"]["cold_boot_natural_completion"]
    assert cold["neutral_input_recipe"]["changed_frame_count"] == 7429
    points = cold["points"]
    assert [(name, points[name]["snapshot"]["region_b"]["resident_fields"])
            for name in ("dlogo_completed", "title_completed", "intro_completed")] == [
        ("dlogo_completed", {"completion_request": 1, "selected_frame_limit": 156}),
        ("title_completed", {"completion_request": 1, "selected_frame_limit": 440}),
        ("intro_completed", {"completion_request": 1, "selected_frame_limit": 1750}),
    ]
    assert points["title_reset"]["snapshot"]["region_b"]["resident_fields"] == {
        "completion_request": 0, "selected_frame_limit": 0}
    assert points["intro_reset"]["snapshot"]["region_b"]["resident_fields"] == {
        "completion_request": 0, "selected_frame_limit": 0}
    assert points["overlay_retired"]["snapshot"]["region_b"]["overlay_resident"] is False
    assert points["frontend_transition"]["snapshot"]["resident"]["scene"] == 1
    assert points["frontend_transition"]["snapshot"]["resident"]["shell_substate"] == 1
    for point in points.values():
        assert point["cycle_neutral_trace"]["comparison"]["cycle_neutral"] is True
        assert not any(row["truncated"] for row in
                       point["cycle_neutral_trace"]["coverage"])


def test_e15_registry_assertions_are_low_level_but_campaign_stays_open():
    registry = common.load_yaml(common.REGISTRY_PATH)
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "fmv_playback")
    assert campaign["status"] == "active"
    for assertions in campaign["evidence"].values():
        for assertion in assertions:
            assert common.audit_assertion(assertion) == []
    assert common.audit_campaign(campaign, registry, common.finding_index()) == [
        "fmv_playback: status is not completed"]
    coverage = phase4_coverage.build()
    assert coverage["rows"]["E15_fmv"]["state"] == "open"
    assert coverage["families"]["audio_cinematics"]["derived_status"] == "active"
    assert coverage["counts"]["complete_total"] == 16
    assert coverage["counts"]["open"] == 91


def test_fmv_schema_preserves_region_b_and_mod_safety_boundaries():
    schema = yaml.safe_load((ROOT / "config/phase4_fmv.yaml").read_text())
    assert schema["schema"] == "abl-phase4-fmv/11"
    assert schema["campaign_state"] == "active_partial"
    assert schema["pristine_frontier"]["manifest"]["entries"] == 40
    assert schema["reproduced_control"]["selected_movie"] == \
        "BUGSFMV1/LEV1A.STR"
    assert schema["reproduced_control"]["selected_frame_limit"] == 386
    boundary = schema["typed_state"]["player_boundary"]
    assert boundary["region_b_address_rows"] == 30
    assert boundary["structures"]["double_buffer"]["size"] == 12
    assert boundary["structures"]["rect_bank"]["slots"] == 2
    assert schema["interface_frontier"]["resident_consumers"][
        "direct_call_count"] == 9
    cold = schema["cold_boot_control"]
    assert [row["frame_limit"] for row in cold["natural_sequence"]] == \
        [156, 440, 1750]
    assert cold["retirement"]["movie_frame"] == 8500
    assert cold["frontend_transition"] == {
        "movie_frame": 9400, "scene": 1, "shell_substate": 1,
        "overlay_resident": False}
    assert schema["reproduced_control"]["final_boundary"] == {
        "movie_frame": 541,
        "start_overlay_resident": False,
        "start_str_backloc": 73,
        "start_removed_overlay_resident": True,
        "start_removed_str_backloc": 163,
    }
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }
