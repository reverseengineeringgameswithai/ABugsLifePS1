from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_menu_phase_neutral_result as result  # noqa: E402


def _evidence(role: str) -> tuple[dict, dict, dict, dict]:
    spec = next(
        row for row in result.CONFIGURATION["receipts"]
        if row["role"] == role)
    receipt = json.loads(
        (result.RUN_ROOT / spec["receipt"]["relative_path"]).read_text())
    batch = json.loads(
        (result.RUN_ROOT / spec["batch_result"]["relative_path"]).read_text())
    plan = result.common.load_yaml(ROOT / spec["plan"]["path"])
    return spec, receipt, batch, plan


def test_falsified_native_control_is_banked_without_owner_claim():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["observation"] == {
        "native_control_falsified_for_both_movies": True,
        "native_endpoint_diverged_for_both_movies": True,
        "nonboot_hits_present_for_both_movies": True,
        "all_native_traces_untruncated": True,
        "all_movie_status_reproducible": False,
        "shared_nonboot_hit_counts": {
            "0x8004ffd4": 0,
            "0x800500d8": 326,
            "0x80050284": 326,
            "0x8005031c": 0,
            "0x8005036c": 0,
            "0x8005b788": 0,
        },
    }
    assert document["record_counts"] == {
        "closed_v2_receipts": 4,
        "atomic_jobs": 8,
        "atomic_replay_frames": 60620,
        "native_observer_replay_frames": 15155,
        "native_coverage_hits": 3266,
        "native_control_failures": 2,
        "owned_pids_stopped": 4,
    }
    assert document["falsifier"]["outcome"] == "falsified"
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["natural_owner_calls_promoted"] is False
    assert document["claim_boundary"]["next_lane"] == "static"
    assert result.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n")


@pytest.mark.parametrize(
    ("role", "mutator", "error"),
    [
        (
            "menu_v1_precise",
            lambda row: row["direct_observer"]["result"]["comparison"].update(
                {"same_ram": True}),
            "endpoints contradict comparison",
        ),
        (
            "menu_v2_precise",
            lambda row: row["direct_observer"]["result"]["coverage"][4][
                "coverage"].update({"truncated": True}),
            "coverage drifted",
        ),
        (
            "menu_v1_precise",
            lambda row: row["direct_observer"]["params"].update(
                {"frame": 7792}),
            "direct observer plan",
        ),
        (
            "menu_v2_passive",
            lambda row: row["result"]["jobs"][1]["result"]["capture"].update(
                {"cycle": 4168377124}),
            "atomic endpoint classification",
        ),
        (
            "menu_v1_passive",
            lambda row: row["expected_media"]["tracks"][0].update(
                {"sha256": "0" * 64}),
            "mounted pristine media",
        ),
    ],
)
def test_low_level_mutations_are_rejected(role, mutator, error):
    spec, receipt, batch, plan = _evidence(role)
    mutated = copy.deepcopy(batch)
    mutator(mutated)
    with pytest.raises((ValueError, RuntimeError), match=error):
        result.validate_pair(spec, receipt, mutated, plan)
