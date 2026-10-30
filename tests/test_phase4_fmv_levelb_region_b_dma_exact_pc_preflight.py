from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_region_b_dma_exact_pc_preflight as preflight  # noqa: E402


def _configuration() -> dict:
    return copy.deepcopy(preflight.CONFIGURATION)


def test_preflight_banks_one_planned_escalation_without_live_claim():
    document = preflight.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["generated_escalation"]["state"] == "planned"
    assert document["generated_escalation"]["receipt_ids"] == [
        "e15-levelb-region-b-dma-exact-pc-native",
        "e15-levelb-region-b-dma-exact-pc-passive-prelude",
        "e15-levelb-region-b-dma-exact-pc-repeat",
    ]
    assert document["immutable_before_ledger"][
        "contains_fresh_escalation"
    ] is True
    assert document["immutable_before_ledger"]["planned_entries"] == 1
    assert document["receipt_admission"]["state"] == "implemented"
    assert document["claim_boundary"]["before_ledger_authorized"] is True
    assert document["claim_boundary"]["receipt_admission_complete"] is True
    assert document["claim_boundary"]["live_executed"] is False
    assert document["claim_boundary"]["live_receipts"] == 0
    assert document["claim_boundary"]["dma_events_claimed"] == 0
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["next_lane"] == "live"
    assert document["record_counts"] == {
        "offline_queries_executed_this_iteration": 0,
        "offline_queries_reused": 1,
        "live_receipts_executed_this_iteration": 0,
        "synthetic_receipt_admissions": 1,
        "dma_events_claimed": 0,
        "promoted_dimensions": 0,
    }


def test_offline_static_and_adapter_basis_is_exact_and_non_native():
    document = preflight.build()
    assert document["offline_basis"]["result_complete"] is True
    assert document["offline_basis"]["result_truncated"] is False
    assert document["offline_basis"]["matching_paths"] == 0
    assert document["offline_basis"]["external_index"][
        "media_class"
    ] == "derived_pristine_evidence"
    assert document["static_boundary"] == {
        "subwindow_sha256": (
            "c7d3696ea7fbd0276b57f64f0790b57351932bb10a84e68cf6e80985d5120f07"
        ),
        "start_pc": "0x80046078",
        "stop_pc": "0x800460C4",
        "required_registers": {"a0": 18, "a1": "0x800B5788"},
        "cdread_submissions_between_stops": 1,
    }
    assert document["adapter_readiness"]["synthetic_command_events"] == 11
    assert document["adapter_readiness"]["native_execution"] is False
    assert document["falsifier"]["outcome"] == (
        "survived_receipt_admission_mutations"
    )
    assert document["falsifier"]["native_evaluation"] is False


def test_passive_capture_is_strictly_wider_on_both_exact_pc_sides():
    plans = preflight.build()["typed_plans"]
    passive = plans["passive_capture_window"]
    precise = plans["precise_capture_window"]
    assert passive == {
        "clock": "emulator_frame",
        "start": 15800,
        "stop": 15896,
        "stop_inclusive": False,
    }
    assert precise == {
        "clock": "emulator_frame",
        "start": 15816,
        "stop": 15880,
        "stop_inclusive": False,
    }
    assert passive["start"] < precise["start"]
    assert passive["stop"] > precise["stop"]
    assert plans["passive_strictly_wider_on_both_sides"] is True
    assert plans["atomic_anchor_method"] == "scenario.runBatch"
    assert plans["precise_observer_method"] == "transferLog.start"


def test_direct_command_receipt_admission_replays_and_rejects_mutations():
    admission = preflight.build()["receipt_admission"]
    assert admission["state"] == "implemented"
    assert admission["observer_plan_schema"] == "abl-phase4-observer-plan/2"
    assert admission["atomic_anchor_jobs"] == 1
    assert admission["direct_command_events"] == 11
    assert admission["mutation_rejections"] == 3
    assert admission["historical_observer_schema_retained"] is True
    assert admission["execution_forbidden_this_iteration"] is True
    assert admission["next_lane"] == "live"
    assert len(admission["guard_nodes"]) == 8


def test_tracked_passive_plan_validates_against_generated_ledger():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/phase4_duckstation_late_batch.py"),
            "--plan",
            str(
                ROOT
                / "config/"
                "phase4_fmv_levelb_region_b_dma_exact_pc_passive_batch.yaml"
            ),
            "--validate-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS:" in result.stdout


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda config: config["work_packet"].update(sha256="0" * 64),
            "iteration work packet identity drifted",
        ),
        (
            lambda config: config["immutable_before_ledger"].update(
                sha256="0" * 64
            ),
            "immutable iteration-before ledger identity drifted",
        ),
        (
            lambda config: config["generated_live_ledger"].update(
                sha256="0" * 64
            ),
            "generated live escalation ledger identity drifted",
        ),
        (
            lambda config: config["offline_basis"]["external_index"].update(
                sha256="0" * 64
            ),
            "work packet offline basis drifted",
        ),
        (
            lambda config: config["static_basis"]["subwindow"].update(
                sha256="0" * 64
            ),
            "static exact-PC subwindow identity drifted",
        ),
        (
            lambda config: config["passive_plan"]["capture_window"].update(
                start=15816
            ),
            "passive receipt differs",
        ),
        (
            lambda config: config["precise_plan"]["direct_observer"][
                "start_stop"
            ].update(pc=0x8004607C),
            "precise live contract differs",
        ),
        (
            lambda config: config["precise_plan"]["direct_observer"][
                "required_registers"
            ].update(a0=17),
            "precise live contract differs",
        ),
        (
            lambda config: config["precise_plan"]["atomic_anchor"].update(
                method="debugger.runUntilAddress"
            ),
            "precise live contract differs",
        ),
        (
            lambda config: config["precise_plan"]["direct_observer"].update(
                max_status_polls_per_stop=0
            ),
            "precise live limits differ",
        ),
        (
            lambda config: config["receipt_admission"].update(
                state="not_implemented"
            ),
            "receipt admission boundary drifted",
        ),
        (
            lambda config: config["claim_boundary"].update(
                live_executed=True
            ),
            "claim boundary drifted",
        ),
    ],
)
def test_identity_plan_bound_and_claim_mutations_fail_closed(
    mutation, message
):
    configuration = _configuration()
    mutation(configuration)
    with pytest.raises(ValueError, match=message):
        preflight.build(configuration)


def test_generated_artifact_is_fresh_and_pins_all_machine_layers():
    document = preflight.build()
    assert set(document["inputs"]) == {
        "config_sha256",
        "work_packet_sha256",
        "before_ledger_sha256",
        "generated_live_ledger_sha256",
        "offline_receipt_sha256",
        "offline_index_sha256",
        "static_subwindow_sha256",
        "adapter_readiness_sha256",
        "exact_pc_adapter_sha256",
        "passive_plan_sha256",
        "receipt_validator_sha256",
    }
    assert preflight.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )
