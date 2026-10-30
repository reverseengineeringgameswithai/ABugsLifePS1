from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_duckstation_two_pc_first_hit as adapter  # noqa: E402
import phase4_fmv_levelb_two_pc_first_hit as boundary  # noqa: E402


def _plan() -> dict:
    return copy.deepcopy(boundary.CONFIGURATION["first_hit_plan"])


def _run(rpc=None, plan=None, identity=None):
    first_hit_plan = plan or _plan()
    fake = rpc or boundary.SyntheticRpc(1)
    return adapter.execute_first_hit(
        fake,
        first_hit_plan,
        "synthetic-session-two-pc",
        identity or first_hit_plan["identity_join"],
        sleep=lambda _seconds: None,
    )


def test_two_pc_boundary_is_banked_without_live_or_dimension_claim():
    document = boundary.build()
    assert document == json.loads(boundary.OUTPUT.read_text())
    assert document["valid"] is True and document["errors"] == []
    assert document["static_transition_boundary"]["first_hit_set"] == [
        "0x8004FD74",
        "0x8005029C",
    ]
    assert document["debugger"]["required_methods_present"] is True
    assert document["debugger"]["temporary_breakpoints_used"] is False
    assert [
        row["first_hit"]["pc"]
        for row in document["synthetic_executions"]
    ] == ["0x8004FD74", "0x8005029C"]
    assert all(document["falsifier"]["checks"].values())
    assert document["falsifier"]["native_evaluation"] is False
    admission = document["v2_receipt_admission"]
    assert admission["live_receipt_schema"] == \
        "abl-phase4-live-run-receipt/2"
    assert admission["historical_observer_schema_unchanged"] is True
    assert admission["capture_window"] == {
        "clock": "emulator_frame",
        "start": 15792,
        "stop": 15856,
        "stop_inclusive": False,
    }
    assert [row["admitted"] for row in admission["synthetic_admissions"]] == [
        True,
        True,
    ]
    assert document["claim_boundary"]["live_executed"] is False
    assert document["claim_boundary"]["selected_natural_branch_claimed"] is False
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["next_lane"] == "live"
    assert document["record_counts"] == {
        "offline_queries_executed_this_iteration": 0,
        "live_receipts_executed_this_iteration": 0,
        "synthetic_transcripts_executed": 2,
        "native_first_hits_claimed": 0,
        "dma_events_claimed": 0,
        "promoted_dimensions": 0,
    }


@pytest.mark.parametrize(
    ("winner_index", "pc", "registers"),
    [
        (
            0,
            "0x8004FD74",
            {
                "pc": "0x8004FD74",
                "a0": "0x00000003",
                "a1": "0x00000000",
            },
        ),
        (
            1,
            "0x8005029C",
            {
                "pc": "0x8005029C",
                "a0": "0x00000006",
                "a1": "0x00000080",
            },
        ),
    ],
)
def test_both_first_hit_branches_are_closed_and_owned(
    winner_index: int,
    pc: str,
    registers: dict,
):
    rpc = boundary.SyntheticRpc(winner_index)
    result = _run(rpc=rpc)
    assert result["complete"] is True
    assert result["first_hit"] == {
        "pc": pc,
        "winner_breakpoint_id": f"bp_{41 + winner_index}",
        "registers": registers,
    }
    assert result["cleanup"] == {
        "owned_breakpoint_ids": ["bp_41", "bp_42"],
        "remaining_breakpoints": 0,
    }
    assert [
        method for _session, method, _params, _timeout in rpc.calls
    ] == [
        "debugger.status",
        "debugger.listBreakpoints",
        "debugger.addBreakpoint",
        "debugger.addBreakpoint",
        "debugger.listBreakpoints",
        "debugger.resume",
        "debugger.status",
        "debugger.getRegisters",
        "debugger.listBreakpoints",
        "debugger.removeBreakpoint",
        "debugger.removeBreakpoint",
        "debugger.listBreakpoints",
        "capture.atomic",
    ]
    assert result["execution"] == {
        "clock": "emulator_frame",
        "anchor_frame": 15792,
        "frame_ceiling": 15856,
        "first_hit_frame": 15796,
    }
    assert all(
        event["server_session_id"] == "synthetic-session-two-pc"
        and event["socket_timeout_ms"] == 5000
        and len(event["result_sha256"]) == 64
        and isinstance(event["result"], dict)
        for event in result["command_events"]["events"]
    )


def test_adapter_cli_validates_tracked_configuration():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/phase4_duckstation_two_pc_first_hit.py"),
            "--plan",
            str(ROOT / "config/phase4_fmv_levelb_two_pc_first_hit.yaml"),
            "--validate-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS: two-PC first-hit plan (8 required methods)" in result.stdout


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda config: config["first_hit_plan"]["breakpoint_sequence"][
                0
            ]["params"].update(address=0x8004FD78),
            "address differs from its required pc",
        ),
        (
            lambda config: config["first_hit_plan"]["breakpoint_sequence"][
                0
            ]["params"].update(temporary=True),
            "managed enabled execute stops",
        ),
        (
            lambda config: config["first_hit_plan"].update(
                breakpoint_sequence=[
                    config["first_hit_plan"]["breakpoint_sequence"][0]
                ]
            ),
            "exactly two stops",
        ),
        (
            lambda config: config["first_hit_plan"]["breakpoint_sequence"][
                1
            ]["required_registers"].update(a1=127),
            "differs from the static transition boundary",
        ),
        (
            lambda config: config["first_hit_plan"]["execution_limit"].update(
                max_status_polls=0
            ),
            "max_status_polls",
        ),
        (
            lambda config: config["first_hit_plan"]["execution_limit"].update(
                max_frame_delta=65
            ),
            "tracked v2 emitter differs",
        ),
        (
            lambda config: config["first_hit_plan"].update(
                cleanup={
                    "method": "debugger.removeBreakpoint",
                    "remove_all_owned": False,
                    "require_empty_after": True,
                }
            ),
            "cleanup must remove",
        ),
        (
            lambda config: config["first_hit_plan"]["identity_join"].update(
                binary_sha256="0" * 64
            ),
            "identity differs from the RPC manifest",
        ),
    ],
)
def test_plan_static_and_identity_mutations_fail_closed(mutation, message):
    configuration = copy.deepcopy(boundary.CONFIGURATION)
    mutation(configuration)
    with pytest.raises(ValueError, match=message):
        boundary.build(configuration)


class MutatingRpc(boundary.SyntheticRpc):
    def __init__(self, mutation: str) -> None:
        super().__init__(1)
        self.mutation = mutation
        self.list_count = 0

    def __call__(self, server_session_id, method, params, socket_timeout_ms):
        result = super().__call__(
            server_session_id, method, params, socket_timeout_ms
        )
        if method == "debugger.listBreakpoints":
            self.list_count += 1
            if self.mutation == "preexisting" and self.list_count == 1:
                result["breakpoints"] = [
                    {
                        "id": "bp_99",
                        "address": "0x80010000",
                        "type": "execute",
                    }
                ]
            if self.mutation == "loser_hit" and self.list_count == 3:
                result["breakpoints"][0]["hit_count"] = 1
                result["breakpoints"][0]["trigger_count"] = 1
            if self.mutation == "winner_twice" and self.list_count == 3:
                result["breakpoints"][1]["hit_count"] = 2
                result["breakpoints"][1]["trigger_count"] = 2
        if (
            self.mutation == "unexpected_pc"
            and method == "debugger.status"
            and self.resumed
        ):
            result["pc"] = "0x800500D8"
        if self.mutation == "register" and method == "debugger.getRegisters":
            result["registers"]["a1"] = 127
        if self.mutation == "remove" and method == "debugger.removeBreakpoint":
            result["removed"] = False
        if self.mutation == "capture" and method == "capture.atomic":
            result["atomic"] = False
        return result


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("preexisting", "pre-existing breakpoints"),
        ("unexpected_pc", "unexpected PC 0x800500D8"),
        ("register", "register identity differs"),
        ("loser_hit", "non-winning breakpoint fired"),
        ("winner_twice", "exactly one first hit"),
        ("remove", "did not confirm owned cleanup"),
        ("capture", "incomplete first-hit identity"),
    ],
)
def test_synthetic_transcript_mutations_fail_closed(mutation, message):
    with pytest.raises(adapter.FirstHitFalsifiedError, match=message):
        _run(rpc=MutatingRpc(mutation))


class NonPausingRpc(boundary.SyntheticRpc):
    def __init__(self) -> None:
        super().__init__(1)

    def __call__(self, server_session_id, method, params, socket_timeout_ms):
        if method == "debugger.status" and self.resumed:
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
                "frame": 15793,
                "pc": "0x80050324",
            }
        return super().__call__(
            server_session_id, method, params, socket_timeout_ms
        )


def test_poll_bound_pauses_removes_owned_breakpoints_and_fails_closed():
    plan = _plan()
    plan["execution_limit"]["max_status_polls"] = 1
    rpc = NonPausingRpc()
    with pytest.raises(
        adapter.FirstHitFalsifiedError,
        match="finite status-poll bound",
    ):
        _run(rpc=rpc, plan=plan)
    methods = [method for _s, method, _p, _t in rpc.calls]
    assert "debugger.pause" in methods
    assert methods[-3:] == [
        "debugger.removeBreakpoint",
        "debugger.removeBreakpoint",
        "debugger.listBreakpoints",
    ]
    assert rpc.breakpoints == []


def test_verified_identity_is_required_before_any_rpc_command():
    rpc = boundary.SyntheticRpc(1)
    changed = copy.deepcopy(_plan()["identity_join"])
    changed["media_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="verified identity context differs"):
        _run(rpc=rpc, identity=changed)
    assert rpc.calls == []
