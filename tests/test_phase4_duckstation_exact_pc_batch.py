from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_duckstation_exact_pc_batch as adapter  # noqa: E402
import phase4_fmv_levelb_region_b_dma_exact_pc_arm as arm  # noqa: E402


def _plan() -> dict:
    return copy.deepcopy(arm.CONFIGURATION["exact_pc_plan"])


def _run(rpc=None, plan=None, identity=None):
    exact_plan = plan or _plan()
    fake = rpc or arm.SyntheticRpc()
    return adapter.execute_exact_pc_window(
        fake,
        exact_plan,
        "synthetic-session-exact-pc",
        identity or exact_plan["identity_join"],
        sleep=lambda _seconds: None,
    )


def test_readiness_is_banked_without_live_dma_or_dimension_claim():
    document = arm.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"] == {
        "outcome": "survived_synthetic_mutations",
        "predicate": document["work_packet"]["falsifier"],
        "native_evaluation": False,
    }
    assert document["claim_boundary"]["adapter_preflight_complete"] is True
    assert document["claim_boundary"]["synthetic_transcript_only"] is True
    assert document["claim_boundary"]["live_executed"] is False
    assert document["claim_boundary"]["live_receipts"] == 0
    assert document["claim_boundary"]["dma_events_claimed"] == 0
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["next_lane"] == "static"
    assert document["record_counts"] == {
        "offline_queries_executed_this_iteration": 0,
        "live_receipts_executed_this_iteration": 0,
        "synthetic_transcripts_executed": 1,
        "dma_events_claimed": 0,
        "promoted_dimensions": 0,
    }


def test_exact_pc_sequence_is_closed_bounded_and_session_owned():
    rpc = arm.SyntheticRpc()
    result = _run(rpc=rpc)
    assert result["complete"] is True
    assert result["stops"] == {
        "start_pc": "0x80046078",
        "terminal_pc": "0x800460C4",
        "registers": {
            "pc": "0x80046078",
            "a0": "0x00000012",
            "a1": "0x800B5788",
        },
    }
    assert [method for _session, method, _params, _timeout in rpc.calls] == [
        "debugger.status",
        "debugger.runUntilAddress",
        "debugger.status",
        "debugger.getRegisters",
        "transferLog.clear",
        "transferLog.start",
        "debugger.runUntilAddress",
        "debugger.status",
        "transferLog.stop",
        "transferLog.get",
        "capture.atomic",
    ]
    assert all(
        event["server_session_id"] == "synthetic-session-exact-pc"
        and event["socket_timeout_ms"] == 5000
        and len(event["result_sha256"]) == 64
        for event in result["command_events"]["events"]
    )
    assert result["execution"] == {
        "clock": "emulator_frame",
        "anchor_frame": 15816,
        "frame_ceiling": 15880,
        "start_stop_frame": 15817,
        "terminal_stop_frame": 15817,
    }
    assert result["transfer"]["total"] == 2
    assert result["transfer"]["truncated"] is False
    assert result["transfer"]["indexes_contiguous"] is True


def test_adapter_cli_validates_the_tracked_outer_configuration():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/phase4_duckstation_exact_pc_batch.py"),
            "--plan",
            str(
                ROOT
                / "config/"
                "phase4_fmv_levelb_region_b_dma_exact_pc_arm.yaml"
            ),
            "--validate-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS: exact-PC stop/arm plan (9 required methods)" in result.stdout


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda config: config["exact_pc_plan"]["start_stop"].update(
                address=0x8004607C
            ),
            "start_stop address differs from required pc",
        ),
        (
            lambda config: config["exact_pc_plan"]["start_stop"][
                "required_registers"
            ].update(a0=17),
            "typed plan differs from the static exact-PC boundary",
        ),
        (
            lambda config: config["exact_pc_plan"]["terminal_stop"].update(
                address=0x800460C8
            ),
            "typed plan differs from the static exact-PC boundary",
        ),
        (
            lambda config: config["exact_pc_plan"].update(
                arm_sequence=list(
                    reversed(config["exact_pc_plan"]["arm_sequence"])
                )
            ),
            "arm_sequence must clear then start",
        ),
        (
            lambda config: config["exact_pc_plan"]["execution_limit"].update(
                max_frame_delta=0
            ),
            "max_frame_delta",
        ),
        (
            lambda config: config["exact_pc_plan"][
                "transfer_pagination"
            ].update(max_pages=1, page_size=10),
            "cannot retain max_records",
        ),
        (
            lambda config: config["exact_pc_plan"]["identity_join"].update(
                binary_sha256="0" * 64
            ),
            "identity differs from the RPC manifest",
        ),
        (
            lambda config: config["exact_pc_plan"]["identity_join"].update(
                media_sha256="0" * 64
            ),
            "media differs from the central pristine authority",
        ),
        (
            lambda config: config["exact_pc_plan"]["terminal_capture"][
                "params"
            ].update(trace_limit=10001),
            "trace_limit",
        ),
    ],
)
def test_plan_and_static_join_mutations_fail_closed(mutation, message):
    configuration = copy.deepcopy(arm.CONFIGURATION)
    mutation(configuration)
    with pytest.raises(ValueError, match=message):
        arm.build(configuration)


class MutatingRpc(arm.SyntheticRpc):
    def __init__(self, mutation: str) -> None:
        super().__init__()
        self.mutation = mutation

    def __call__(self, server_session_id, method, params, socket_timeout_ms):
        result = super().__call__(
            server_session_id, method, params, socket_timeout_ms
        )
        if self.mutation == "register" and method == "debugger.getRegisters":
            result["registers"]["a1"] = 0x800B5790
        if (
            self.mutation == "terminal_pc"
            and method == "debugger.status"
            and self.status_count == 3
        ):
            result["pc"] = "0x800460C8"
        if self.mutation == "truncated" and method == "transferLog.get":
            result["truncated"] = True
        if self.mutation == "indexes" and method == "transferLog.get":
            result["events"][1]["index"] = 3
        if self.mutation == "clear" and method == "transferLog.clear":
            result["cleared"] = False
        if self.mutation == "capture" and method == "capture.atomic":
            result["atomic"] = False
        return result


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("register", "register identity differs"),
        ("terminal_pc", "paused at 0x800460C8"),
        ("truncated", "incomplete or truncated"),
        ("indexes", "indexes are not complete and contiguous"),
        ("clear", "did not confirm clearing"),
        ("capture", "incomplete terminal identity"),
    ],
)
def test_synthetic_result_mutations_fail_closed(mutation, message):
    with pytest.raises(adapter.ExactPcFalsifiedError, match=message):
        _run(rpc=MutatingRpc(mutation))


class NonPausingRpc(arm.SyntheticRpc):
    def __call__(self, server_session_id, method, params, socket_timeout_ms):
        if method == "debugger.status" and self.status_count:
            self.status_count += 1
            self.calls.append(
                (
                    server_session_id,
                    method,
                    copy.deepcopy(params),
                    socket_timeout_ms,
                )
            )
            return {
                "valid": True,
                "paused": False,
                "frame": 15817,
                "pc": "0x80050324",
            }
        return super().__call__(
            server_session_id, method, params, socket_timeout_ms
        )


def test_poll_bound_pauses_and_fails_closed():
    plan = _plan()
    plan["execution_limit"]["max_status_polls_per_stop"] = 1
    rpc = NonPausingRpc()
    with pytest.raises(
            adapter.ExactPcFalsifiedError,
            match="finite status-poll bound"):
        _run(rpc=rpc, plan=plan)
    assert rpc.calls[-1] == (
        "synthetic-session-exact-pc",
        "debugger.pause",
        {},
        5000,
    )


def test_verified_identity_is_required_before_any_rpc_command():
    rpc = arm.SyntheticRpc()
    changed = copy.deepcopy(_plan()["identity_join"])
    changed["media_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="verified identity context differs"):
        _run(rpc=rpc, identity=changed)
    assert rpc.calls == []


def test_generated_artifact_and_debugger_dependencies_are_fresh():
    document = arm.build()
    assert set(document["debugger"]["required_methods"]) == set(
        adapter.REQUIRED_METHODS
    )
    assert document["debugger"]["required_methods_present"] is True
    assert document["debugger"]["run_until_boundary"] == (
        "temporary pre-instruction breakpoint"
    )
    assert arm.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )
