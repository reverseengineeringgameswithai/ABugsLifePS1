"""Falsification guards for the natural C16 LOSE lifecycle."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_lose_lifecycle as lose  # noqa: E402


def document() -> dict:
    return json.loads(lose.OUTPUT.read_text())


def receipt(role: str) -> dict:
    return lose._receipt(role)[1]


def test_summary_rebuilds_from_four_external_receipts():
    assert lose.render(lose.build()) == lose.OUTPUT.read_bytes()
    doc = document()
    assert doc["valid"] is True and doc["errors"] == []
    assert len(doc["external_receipts"]) == 4
    assert doc["record_counts"] == {
        "atomic_batches": 1,
        "jobs": 2,
        "failed_positive_function_events": 0,
        "cached_control_pairs": 1,
        "staged_exact_stops": 8,
        "staged_access_events": 3,
    }
    assert doc["raw_external_bytes_committed"] is False


def test_failed_positive_is_retained_as_observer_desync():
    attempt = document()["observations"]["frame_zero_attempt"]
    positive = attempt["gameover_movie_positive"]
    negative = attempt["gameover_no_input_control"]
    assert positive["movie_playback_index"] == 1600
    assert positive["movie_reproducible"] is False
    assert negative["movie_reproducible"] is True
    assert positive["function_events"] == negative["function_events"] == 0
    assert positive["scene"] == negative["scene"] == 9


def test_staged_positive_binds_loader_completion_and_teardown():
    natural = document()["observations"]["natural_lose"]
    assert natural["cached_stage"]["comparison"]["cycle_neutral"] is True
    assert natural["loader"]["entry"]["caller"] == "0x800500d8"
    assert natural["loader"]["entry"]["arguments"][0:2] == [
        "0x0000002e", "0x00000000"]
    assert natural["access_events"][0]["new_value"] == 281
    assert natural["access_events"][-1] == {
        "label": "completion_request",
        "frame": 266492,
        "cycle": 150888266123,
        "instruction_pc": "0x800b6b48",
        "old_value": 0,
        "new_value": 1,
    }
    assert natural["ring_calls"][-1]["caller"] == "0x800b749c"
    assert natural["callback_teardown"]["caller"] == "0x800b74a4"
    assert natural["endpoint"]["selected_frame_limit"] == 281
    assert natural["endpoint"]["movie_reproducible"] is True


def test_staged_guard_rejects_loader_selector_drift():
    mutated = receipt("staged_positive")
    mutated["observations"]["loader"]["entry"]["arguments"][0] = "0x0000002d"
    with pytest.raises(ValueError, match="LOSE loader entry/return"):
        lose.validate_staged(mutated)


def test_staged_guard_rejects_completion_writer_and_truncation():
    mutated = receipt("staged_positive")
    access = mutated["observations"][
        "atomic_after_loader_return"]["traces"]["access"]
    access["events"][-1]["instruction_pc"] = "0x800b6b24"
    with pytest.raises(ValueError, match="selected-limit/completion"):
        lose.validate_staged(mutated)
    mutated = receipt("staged_positive")
    mutated["observations"][
        "atomic_after_loader_return"]["traces"]["access"]["truncated"] = True
    with pytest.raises(ValueError, match="selected-limit/completion"):
        lose.validate_staged(mutated)


def test_failed_attempt_cannot_be_reclassified_as_reproducible():
    mutated = receipt("frame_zero_atomic_attempt")
    positive = next(
        row for row in mutated["result"]["jobs"]
        if row["id"] == "gameover_movie_positive")
    positive["result"]["movie"]["reproducible"] = True
    with pytest.raises(ValueError, match="observer-desync"):
        lose.validate_atomic_attempt(mutated)


def test_residuals_keep_all_partial_dimensions_open():
    doc = document()
    assert len(doc["residuals"]) == 3
    assert "does not promote lifecycle" in doc["residuals"][-1]
