from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_first_call as levelb  # noqa: E402


def _raw() -> dict:
    return json.loads(
        (levelb.EXTERNAL_ROOT /
         levelb._spec("result")["relative_path"]).read_text())


def test_summary_rebuilds_from_hash_pinned_low_level_events():
    document = levelb.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["record_counts"] == {
        "localization_queries": 12,
        "localization_coverage_ranges": 12,
        "positive_function_events": 8,
        "positive_execution_events": 1,
        "positive_access_events": 228,
        "neutral_function_events": 14,
        "neutral_execution_events": 0,
        "neutral_access_events": 231,
        "debugger_cleanup_actions": 30,
    }
    assert document["observation"]["loader_entry"]["selector"] == 11
    assert document["observation"]["completion"]["instruction_pc"] == \
        "0x800b6b24"
    assert document["observation"]["neutral_control"][
        "completed_level_b_loader_entries"] == 0
    assert len(document["observation"]["neutral_control"][
        "generic_loader_entries"]) == 2
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert levelb.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n")


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (lambda row: row["localization"]["queries"][7]["trace"][
            "comparison"].update({"same_ram": False}),
         "localization query"),
        (lambda row: row["positive"]["first_call"]["registers"].update(
            {"s0": "0x00000002"}),
         "pre-delay"),
        (lambda row: row["positive"]["loader_entry"]["registers"].update(
            {"a0": "0x0000000a"}),
         "post-delay"),
        (lambda row: row["positive"]["traces"]["access"][
            "selected_frame_limit"]["events"][0].update({"new_value": 484}),
         "limit/completion"),
        (lambda row: next(
            event for event in row["positive"]["traces"]["access"][
                "completion_request"]["events"]
            if event.get("instruction_pc") == "0x800b6b24").update(
                {"instruction_pc": "0x800b6b48"}),
         "limit/completion"),
        (lambda row: next(
            event for event in row["positive"]["traces"]["functions"]["events"]
            if event.get("caller") == "0x800b74a4" and
            event.get("type") == "entry").update({"synthetic_unwind": True}),
         "completion/teardown"),
        (lambda row: row["neutral"]["traces"]["execution"]["events"].append(
            {"pc": "0x8005031c"}),
         "neutral Level-B"),
        (lambda row: row["neutral"]["traces"]["functions"]["events"][4].update(
            {"caller": "0x8005031c"}),
         "neutral Level-B"),
        (lambda row: row["neutral"]["traces"]["functions"].update(
            {"truncated": True}),
         "trace truncated"),
        (lambda row: row["positive"]["cleanup"][0].update({"ok": False}),
         "instrumentation cleanup"),
    ],
)
def test_low_level_mutations_are_rejected(mutator, error):
    document = copy.deepcopy(_raw())
    mutator(document)
    with pytest.raises(ValueError, match=error):
        levelb.validate_result(document, verify_identity=False)
