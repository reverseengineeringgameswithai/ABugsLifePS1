"""Falsification and retained-evidence guards for Phase-4 A20."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import live_session_provenance as live  # noqa: E402
import phase4_circle_absence as circle  # noqa: E402
import phase4_common as common  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_circle_absence.json"
ARTIFACT_SHA256 = "c96af4d2cbfe5089c5157ddbdff10c856bbbf53e71958a35b27d45c3ea490076"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_static_decoder_census_recomputes_from_pinned_pristine_bytes():
    retained = load_artifact()["static_census"]
    recomputed = circle.build_static_census()
    assert recomputed == retained
    assert circle.static_census_gaps(recomputed) == []
    assert recomputed["executable"]["sha256"] == (
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20")
    assert recomputed["decoder"]["sha256"] == (
        "5262593728a0d339c1de205d247609b6bdbbed17425bd88e896d91b0a4533029")
    assert recomputed["profile_table"]["sha256"] == (
        "d0f4b1031cdd5f3e29bcca36482bb46210b13fa72dc02627e568f8c87af9a9f4")


def test_decoder_or_profile_mutation_turns_the_static_proof_red():
    census = circle.build_static_census()
    mutated = copy.deepcopy(census)
    mutated["default_profile"]["circle_action_bits"] = 0x8000
    assert "default profile maps raw Circle to an action bit" in \
        circle.static_census_gaps(mutated)

    mutated = copy.deepcopy(census)
    mutated["remap_boundary"]["circle_action_bits"] = 0
    assert "profile 1 no longer maps raw Circle to Square action" in \
        circle.static_census_gaps(mutated)

    executable = bytearray(circle.EXE_PATH.read_bytes())
    executable[circle._va_offset(circle.PROFILE_TABLE + 2)] ^= 0x20
    with pytest.raises(SystemExit, match="PRISTINE-INPUT GUARD"):
        circle.build_static_census(bytes(executable))


def test_retained_circle_evidence_recomputes_low_level_predicates():
    doc = load_artifact()
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == ARTIFACT_SHA256
    summary = doc["live"]["summary"]
    assert summary["anchors_requested"] == 42
    assert summary["anchors_compared"] == 42
    assert summary["phase_matched_equal_anchors"] == 42
    assert summary["raw_circle_observed_anchors"] == 42
    assert summary["decoded_equivalent_anchors"] == 42
    assert summary["profile_zero_anchors"] == 42
    assert summary["differing_labels"] == []
    assert summary["raw_circle_missing_labels"] == []
    assert summary["decoded_difference_labels"] == []
    assert all(row["outcome_differences"] == []
               for row in doc["live"]["anchor_results"].values())

    negative = doc["live"]["negative_control"]
    positive = doc["live"]["positive_control"]
    assert (negative["raw_pad"] & circle.RAW_CIRCLE) == circle.RAW_CIRCLE
    assert negative["decoded_action_bits"] == 0
    assert negative["truncated"] is False
    assert negative["decoder_write_events"][0]["instruction_pc"] == "0x800512d0"
    assert (positive["raw_pad"] & circle.RAW_CIRCLE) == circle.RAW_CIRCLE
    assert positive["decoded_action_bits"] == 0x8000
    assert positive["truncated"] is False
    assert positive["decoder_write_events"][-1]["instruction_pc"] == "0x80051318"

    run = doc["run_provenance"]
    assert run["generator_sha256"] == hashlib.sha256(
        (ROOT / "tools/phase4_circle_absence.py").read_bytes()).hexdigest()
    assert run["rpc_manifest"]["source"]["method_count"] == 203
    assert run["cleanup"]["owned_pid_stopped"] is True
    assert live.retained_pristine_save_gaps(doc, require_selection=True) == []


def test_reviewed_absence_and_reusable_finding_are_audited_not_self_certified():
    registry = common.load_yaml(common.REGISTRY_PATH)
    proof = next(row for row in registry["reviewed_absence"]
                 if row["row_id"] == "A20_circle_noop")
    assert common.audit_absence(proof) == []
    finding = common.finding_index()["circle_default_input_absence"]
    assert common.audit_finding(finding) == []
    assert all(not ({part.lower() for part in assertion["json_path"].split(".")}
                    & common.SELF_CERTIFYING_KEYS)
               for assertion in proof["evidence"].values()
               for assertion in assertion)


def test_input_action_schema_matches_static_and_live_boundaries():
    schema = yaml.safe_load(
        (ROOT / "config/phase4_input_actions.yaml").read_text())
    static = load_artifact()["static_census"]
    assert schema["schema"] == "abl-phase4-input-actions/1"
    assert int(schema["raw_input"]["circle"]["raw_mask"], 16) == circle.RAW_CIRCLE
    assert int(schema["profiles"]["proven_boundaries"]
               ["default_profile_0"]["circle_action_bits"], 16) == \
        static["default_profile"]["circle_action_bits"]
    assert int(schema["profiles"]["proven_boundaries"]
               ["native_profile_1_positive_control"]["circle_action_bits"], 16) == \
        static["remap_boundary"]["circle_action_bits"]
    assert schema["profiles"]["table"]["sha256"] == \
        static["profile_table"]["sha256"]
    assert set(schema["mod_contract"]) == {
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    }


def test_declared_scenario_runner_validates_the_existing_stage_oracle():
    proc = subprocess.run([
        sys.executable, "tools/run_ps1_scenario.py",
        "tools/scenarios/duckstation/stage_identity_stage01_anthill.yaml",
        "--validate-only",
    ], cwd=ROOT, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "stage_identity_stage01_anthill" in proc.stdout
