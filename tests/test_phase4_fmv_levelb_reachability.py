from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_reachability as levelb  # noqa: E402


def test_current_levelb_reachability_summary_is_reproducible():
    document = levelb.build()
    assert document["record_counts"] == {
        "atomic_batches": 1,
        "atomic_jobs": 2,
        "atomic_caller_hits": 0,
        "atomic_typed_selected_limit_events": 7,
        "save_recipe_branches": 2,
        "save_recipe_caller_hits": 0,
        "save_recipe_function_events": 0,
        "phase_neutral_branches": 2,
        "phase_neutral_coverage_ranges": 12,
        "phase_neutral_completed_level_b_positive": 1,
        "phase_neutral_completed_level_b_neutral": 0,
    }
    assert document["attempts"]["phase_neutral_full_level_movie"][
        "original"]["observed"]["completed_level_b_call"] is True
    assert document["attempts"]["phase_neutral_full_level_movie"][
        "neutral"]["observed"]["completed_level_b_call"] is False
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert levelb.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n")


def test_legacy_nonreproducible_selector_sequence_cannot_be_rewritten(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    configuration = copy.deepcopy(levelb.CONFIGURATION)
    for spec in configuration["external_receipts"]:
        source = levelb.EXTERNAL_ROOT / spec["relative_path"]
        target = tmp_path / spec["relative_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    atomic_spec = next(
        row for row in configuration["external_receipts"]
        if row["role"] == "cold_boot_atomic")
    atomic_path = tmp_path / atomic_spec["relative_path"]
    document = json.loads(atomic_path.read_text())
    events = document["result"]["jobs"][0]["result"][
        "capture"]["traces"]["access"]["events"]
    event = next(
        row for row in events
        if row.get("instruction_pc") == "0x800b6dc0" and
        row.get("new_value") == 386)
    event["new_value"] = 485
    atomic_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    atomic_spec["bytes"] = atomic_path.stat().st_size
    atomic_spec["sha256"] = hashlib.sha256(atomic_path.read_bytes()).hexdigest()

    monkeypatch.setattr(levelb, "EXTERNAL_ROOT", tmp_path)
    monkeypatch.setattr(levelb, "CONFIGURATION", configuration)
    with pytest.raises(ValueError, match="legacy cold-boot receipt drifted"):
        levelb.build()


def test_phase_neutral_positive_is_recomputed_from_covered_pcs(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    configuration = copy.deepcopy(levelb.CONFIGURATION)
    for spec in configuration["external_receipts"]:
        source = levelb.EXTERNAL_ROOT / spec["relative_path"]
        target = tmp_path / spec["relative_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    result_spec = next(
        row for row in configuration["external_receipts"]
        if row["role"] == "phase_neutral_replay")
    result_path = tmp_path / result_spec["relative_path"]
    document = json.loads(result_path.read_text())
    document["original_movie"]["observed"][
        "completed_level_b_call"] = False
    result_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n")
    result_spec["bytes"] = result_path.stat().st_size
    result_spec["sha256"] = hashlib.sha256(
        result_path.read_bytes()).hexdigest()

    monkeypatch.setattr(levelb, "EXTERNAL_ROOT", tmp_path)
    monkeypatch.setattr(levelb, "CONFIGURATION", configuration)
    with pytest.raises(ValueError, match="observed PC set drifted"):
        levelb.build()
