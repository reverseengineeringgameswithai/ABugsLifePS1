from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_c16_selector_control_result as result  # noqa: E402


def _staged_evidence(
        role: str) -> tuple[dict, dict, dict, dict, dict, dict, dict]:
    source = result.CONFIGURATION["staged_successor"]
    run_root = Path(source["run_root"])
    spec = next(row for row in source["receipts"] if row["role"] == role)
    receipt = json.loads(
        (run_root / spec["receipt"]["relative_path"]).read_text())
    batch = json.loads(
        (run_root / spec["batch_result"]["relative_path"]).read_text())
    raw = json.loads(
        (run_root / spec["raw_results"]["relative_path"]).read_text())
    cleanup = json.loads(
        (run_root / spec["cleanup"]["relative_path"]).read_text())
    plan = result.common.load_yaml(ROOT / spec["plan"]["path"])
    return source, spec, receipt, batch, raw, cleanup, plan


def _mutate_access_pc(
        batch: dict, address: str, pc: str, new_value: int | None = None) -> None:
    event = next(
        row
        for job in batch["result"]["jobs"]
        for row in job["result"]["capture"]["traces"]["access"]["events"]
        if row["address"] == address and
        (new_value is None or row["new_value"] == new_value))
    event["pc"] = pc


def test_staged_selector_interface_is_banked_without_dimension_promotion():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["schema"].endswith("/3")
    assert document["historical_unstaged_attempt"]["falsifier"][
        "outcome"] == "falsified"
    assert all(
        not row["receipt_admissible"]
        for row in document["historical_unstaged_attempt"]["receipts"])
    assert document["falsifier"]["outcome"] == "survived"
    assert document["observation"]["same_anchor_loader_interface"] == {
        "function": "0x8003e7c0",
        "caller": "0x800500d8",
        "return_address": "0x800500e0",
        "frame": 265655,
        "cycle": 150414500686,
        "positive_selector": 40,
        "negative_selector": 46,
    }
    assert document["observation"]["same_frame_initial_limit_interface"] == {
        "instruction_pc": "0x800b6dc0",
        "reported_pc": "0x800b6dc4",
        "address": "0x80131eee",
        "frame": 265826,
        "positive_limit": 3162,
        "negative_limit": 281,
    }
    assert document["observation"]["negative_native_completion_request"] == {
        "instruction_pc": "0x800b6b48",
        "reported_pc": "0x800b6b4c",
        "address": "0x800cac10",
        "new_value": 1,
        "frame": 266492,
    }
    assert document["record_counts"] == {
        "emulator_launches": 2,
        "completed_atomic_jobs": 4,
        "replay_frames": 16024,
        "observer_frames": 14826,
        "exact_after_load_writes": 1,
        "owned_pids_stopped": 2,
        "intrinsically_valid_live_receipts": 2,
        "method_trial_admissible_live_receipts": 0,
    }
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["lifecycle_promoted"] is False
    assert all(row["intrinsic_v2_valid"] for row in document["receipts"])
    assert not any(
        row["method_trial_admissible"] for row in document["receipts"])
    assert document["method_admission"]["status"] == \
        "rejected_conservative_pre_v2_overlap"
    assert document["method_admission"][
        "method_trial_receipts_admissible"] == 0
    assert result.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n")


@pytest.mark.parametrize(
    ("role", "target", "mutator", "error"),
    [
        (
            "staged_precise", "batch",
            lambda row: row["result"]["jobs"][0]["result"][
                "after_load"].update({"code_invalidated": False}),
            "staged after-load write/readback",
        ),
        (
            "staged_precise", "batch",
            lambda row: row["result"]["jobs"][0]["result"][
                "staged_prelude"].update({"frames_advanced": 299}),
            "staged playback span",
        ),
        (
            "staged_passive", "raw",
            lambda row: row["results"][0].update({"replay_start": 1}),
            "staged raw counters",
        ),
        (
            "staged_passive", "cleanup",
            lambda row: row.update({"owned_pid_stopped": False}),
            "staged owned-PID cleanup",
        ),
        (
            "staged_precise", "batch",
            lambda row: row["expected_media"]["tracks"][0].update(
                {"sha256": "0" * 64}),
            "staged batch/media/debugger identity",
        ),
        (
            "staged_precise", "batch",
            lambda row: _mutate_access_pc(
                row, "0x80131eee", "0x800b6dc0"),
            "staged selector limit interface",
        ),
        (
            "staged_precise", "batch",
            lambda row: _mutate_access_pc(
                row, "0x800cac10", "0x800b6b48", 1),
            "bounded completion-request observation",
        ),
    ],
)
def test_staged_low_level_mutations_are_rejected(
        role, target, mutator, error):
    source, spec, receipt, batch, raw, cleanup, plan = _staged_evidence(role)
    values = {
        "receipt": copy.deepcopy(receipt),
        "batch": copy.deepcopy(batch),
        "raw": copy.deepcopy(raw),
        "cleanup": copy.deepcopy(cleanup),
    }
    mutator(values[target])
    with pytest.raises(ValueError, match=error):
        result.validate_staged_run(
            source, spec, values["receipt"], values["batch"],
            values["raw"], values["cleanup"], plan)
