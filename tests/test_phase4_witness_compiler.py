"""Matched-origin, perturbation, assertion, and authority tests for witnesses."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_witness_compiler as witness  # noqa: E402


def fixture():
    arm = {
        "receipt_sha256": "1" * 64,
        "input_sha256": "2" * 64,
        "start_state_sha256": "3" * 64,
        "start_fingerprint": "4" * 64,
        "end_fingerprint": "5" * 64,
        "perturbations": {"power_slot": 400},
        "observations": {
            "power_slot": 399, "health": 3,
            "position": {"x": 100, "y": 20},
        },
        "control_checks": {"media_verified": True, "instrumentation_armed": True,
                           "owned_cleanup": True},
        "errors": [], "truncated": False,
    }
    control = copy.deepcopy(arm)
    control.update(receipt_sha256="6" * 64, input_sha256="7" * 64,
                   end_fingerprint="8" * 64)
    control["perturbations"]["power_slot"] = 0
    control["observations"]["power_slot"] = 0
    return {
        "schema": witness.SCHEMA,
        "identity": {
            "row_id": "B06_invincibility", "dimension": "original_oracle",
            "scope": "one matched timer boundary", "media_sha256": "9" * 64,
            "executable_sha256": "a" * 64, "overlay_sha256": None,
            "fixture_sha256": "b" * 64, "anchor_class": "validated_save_state",
            "execution_mode": "Interpreter", "debugger_binary_sha256": "c" * 64,
            "debugger_source_revision": "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5",
        },
        "claim": {"id": "B06/timer-consumption", "statement": "A positive timer decrements once.",
                  "observation_scope": "matched next native iteration"},
        "arms": {"positive": arm, "control": control},
        "expected_perturbation_keys": ["power_slot"],
        "assertions": [
            {"id": "slot-differs", "path": "power_slot", "op": "eq",
             "positive_expected": 399, "control_expected": 0, "delta_expected": None},
            {"id": "health-stable", "path": "health", "op": "unchanged",
             "positive_expected": None, "control_expected": None, "delta_expected": None},
            {"id": "x-stable", "path": "position.x", "op": "unchanged",
             "positive_expected": None, "control_expected": None, "delta_expected": None},
            {"id": "y-stable", "path": "position.y", "op": "unchanged",
             "positive_expected": None, "control_expected": None, "delta_expected": None},
        ],
        "authority": copy.deepcopy(witness.AUTHORITY),
    }


def test_matched_witness_derives_every_difference_and_is_nonpromoting():
    report = witness.compile_witness(fixture())
    assert report["schema"] == witness.OUTPUT_SCHEMA
    assert report["verdict"] == "witness_ready_for_fresh_verifier"
    assert report["matched_origin"] is True
    assert report["perturbations"] == {
        "changed_keys": ["power_slot"], "expected_keys": ["power_slot"]}
    assert report["observations"] == {
        "differing_leaf_paths": ["power_slot"], "unasserted_differing_paths": []}
    assert all(row["passed"] for row in report["assertions"])
    assert report["authority"]["promotes_row_or_dimension"] is False


def test_unmatched_origin_and_perturbation_drift_are_not_ready():
    document = fixture()
    document["arms"]["control"]["start_fingerprint"] = "d" * 64
    document["arms"]["positive"]["perturbations"]["health"] = 4
    report = witness.compile_witness(document)
    assert report["verdict"] == "not_ready"
    assert "START_FINGERPRINT_MISMATCH" in report["errors"]
    assert "PERTURBATION_UNIVERSE_DRIFT" in report["errors"]


def test_equal_or_one_sided_extra_perturbations_cannot_hide_in_the_universe():
    document = fixture()
    document["arms"]["positive"]["perturbations"]["hidden"] = 1
    document["arms"]["control"]["perturbations"]["hidden"] = 1
    assert "PERTURBATION_UNIVERSE_DRIFT" in witness.compile_witness(document)["errors"]

    document = fixture()
    document["arms"]["positive"]["perturbations"]["hidden"] = None
    assert "PERTURBATION_UNIVERSE_DRIFT" in witness.compile_witness(document)["errors"]


def test_every_observed_difference_requires_an_assertion():
    document = fixture()
    document["arms"]["positive"]["observations"]["position"]["z"] = 9
    document["arms"]["control"]["observations"]["position"]["z"] = 8
    report = witness.compile_witness(document)
    assert report["verdict"] == "not_ready"
    assert report["observations"]["unasserted_differing_paths"] == ["position.z"]
    assert "UNASSERTED_OBSERVATION_DIFFERENCE" in report["errors"]


def test_assertion_failures_report_stable_ids_and_delta_is_strict_numeric():
    document = fixture()
    document["assertions"][0]["positive_expected"] = 398
    report = witness.compile_witness(document)
    assert "ASSERTION_FAILED:slot-differs" in report["errors"]
    changed = fixture()
    changed["assertions"][0].update(op="delta_eq", delta_expected=True)
    with pytest.raises(witness.WitnessError, match="must be numeric"):
        witness.validate(changed)


@pytest.mark.parametrize("mutate,match", [
    (lambda row: row.update(schema="abl-phase4-differential-witness/2"), "must use"),
    (lambda row: row["identity"].update(execution_mode="CachedInterpreter"),
     "must be Interpreter"),
    (lambda row: row["identity"].update(media_sha256="bad"), "SHA-256"),
    (lambda row: row["arms"]["positive"].update(errors=["capture failed"]),
     "errors must be exactly"),
    (lambda row: row["arms"]["positive"].update(truncated=0), "truncated"),
    (lambda row: row["arms"]["positive"]["control_checks"].update(
        media_verified=1), "control_checks"),
    (lambda row: row["authority"].update(runtime_silence_proves_absence=True),
     "authority"),
    (lambda row: row["assertions"][0].update(op="approximately"), "op is invalid"),
])
def test_schema_identity_control_and_authority_mutations_fail_closed(mutate, match):
    document = fixture()
    mutate(document)
    with pytest.raises(witness.WitnessError, match=match):
        witness.validate(document)


def test_anchor_class_binds_start_state_presence():
    document = fixture()
    document["identity"]["anchor_class"] = "cold_boot"
    with pytest.raises(witness.WitnessError, match="may not name a start state"):
        witness.validate(document)
    document["arms"]["positive"]["start_state_sha256"] = None
    document["arms"]["control"]["start_state_sha256"] = None
    witness.validate(document)
    document["identity"]["anchor_class"] = "validated_save_state"
    with pytest.raises(witness.WitnessError, match="must be hash-bound"):
        witness.validate(document)


def test_cli_check_detects_stale_retained_witness(tmp_path):
    source = tmp_path / "witness.json"
    source.write_text(json.dumps(fixture()), encoding="utf-8")
    output = ROOT / "analysis/phase4_witness_compiler_test.tmp.json"
    try:
        command = [sys.executable, str(ROOT / "tools/phase4_witness_compiler.py"),
                   str(source), "--output", str(output)]
        first = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                               check=False)
        assert first.returncode == 0, first.stderr
        fresh = subprocess.run(command + ["--check"], cwd=ROOT, text=True,
                               capture_output=True, check=False)
        assert fresh.returncode == 0, fresh.stderr
        output.write_text("{}\n", encoding="utf-8")
        stale = subprocess.run(command + ["--check"], cwd=ROOT, text=True,
                               capture_output=True, check=False)
        assert stale.returncode != 0 and "stale" in stale.stderr
    finally:
        output.unlink(missing_ok=True)
