from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_menu_owner_coverage as menu  # noqa: E402


def _evidence(role: str) -> tuple[dict, dict, dict]:
    spec = next(
        row for row in menu.CONFIGURATION["receipts"]
        if row["role"] == role)
    receipt = json.loads(
        (menu.RUN_ROOT / spec["receipt"]["relative_path"]).read_text())
    batch = json.loads(
        (menu.RUN_ROOT / spec["batch_result"]["relative_path"]).read_text())
    return spec, receipt, batch


def test_rejected_control_is_banked_without_owner_exclusion():
    document = menu.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["observation"] == {
        "boot_positive_hits_per_movie": 3,
        "nonboot_candidate_hits_per_movie": 0,
        "all_traces_untruncated": True,
        "all_movie_status_reproducible": False,
        "precise_controls_admissible": False,
        "menu_v1_passive_control_admissible": True,
        "menu_v2_passive_control_admissible": False,
    }
    assert document["falsifier"]["outcome"] == "falsified"
    assert document["record_counts"] == {
        "closed_v2_receipts": 4,
        "atomic_jobs": 8,
        "replay_frames": 60620,
        "execution_events": 6,
        "endpoint_control_failures": 3,
        "owned_pids_stopped": 4,
    }
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["observed_nonboot_zero_promoted"] is False
    assert menu.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n")


@pytest.mark.parametrize(
    ("role", "mutator", "error"),
    [
        (
            "menu_v1_precise",
            lambda row: row["result"]["jobs"][1]["result"]["capture"][
                "traces"]["execution"]["watches"][0].update({"hit_count": 1}),
            "caller coverage",
        ),
        (
            "menu_v1_precise",
            lambda row: row["result"]["jobs"][1]["result"]["capture"].update(
                {"cycle": 4412410952}),
            "endpoint control classification",
        ),
        (
            "menu_v2_passive",
            lambda row: row["result"]["jobs"][1]["result"]["capture"].update(
                {"cycle": 4168377124}),
            "endpoint control classification",
        ),
        (
            "menu_v2_precise",
            lambda row: row["result"]["jobs"][0]["result"]["capture"][
                "traces"]["execution"].update({"truncated": True}),
            "endpoint or trace",
        ),
        (
            "menu_v1_precise",
            lambda row: row["expected_media"]["tracks"][0].update(
                {"sha256": "0" * 64}),
            "mounted pristine media",
        ),
    ],
)
def test_low_level_mutations_are_rejected(role, mutator, error):
    spec, receipt, batch = _evidence(role)
    mutated = copy.deepcopy(batch)
    mutator(mutated)
    with pytest.raises(ValueError, match=error):
        menu.validate_pair(spec, receipt, mutated)
