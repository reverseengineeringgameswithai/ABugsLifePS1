#!/usr/bin/env python3
"""Bank the E15 managed two-PC first-hit boundary without a live claim."""
from __future__ import annotations

import argparse
import copy
from datetime import date
import json
from pathlib import Path
from typing import Any

import phase4_common as common
import phase4_duckstation_two_pc_first_hit as adapter
import phase4_fmv_levelb_two_pc_first_hit_live as live_emitter
import phase4_method_metrics as metrics


CONFIG_PATH = (
    common.ROOT / "config/phase4_fmv_levelb_two_pc_first_hit.yaml"
)
OUTPUT = common.ROOT / "analysis/phase4_fmv_levelb_two_pc_first_hit.json"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIGURATION["run_root"])
RUNTIME_PATH = (
    common.ROOT
    / "config/phase4_fmv_levelb_two_pc_first_hit_runtime.yaml"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def _pinned_json(
    spec: dict[str, Any],
    label: str,
    *,
    run: bool = False,
) -> tuple[Path, dict[str, Any]]:
    base = RUN_ROOT if run else common.ROOT
    relative = spec.get("relative_path") if run else spec.get("path")
    path = base / relative
    _require(
        path.is_file() and common.sha256(path) == spec["sha256"],
        f"{label} identity drifted",
    )
    return path, common.load_json(path)


def _work_packet() -> dict[str, Any]:
    path, packet = _pinned_json(
        CONFIGURATION["work_packet"], "iteration work packet", run=True
    )
    predicted = packet.get("predicted_authoritative_machine_layer")
    _require(
        path.stat().st_size == CONFIGURATION["work_packet"]["bytes"]
        and packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("iteration") == 1
        and packet.get("campaign_id") == CONFIGURATION["campaign_id"]
        and packet.get("row_ids") == [CONFIGURATION["row_id"]]
        and packet.get("first_unmet_dimension")
        == CONFIGURATION["dimension"]
        and packet.get("next_lane") == CONFIGURATION["lane"]
        and predicted
        == {
            "artifact": "analysis/phase4_fmv_levelb_two_pc_first_hit.json",
            "source": "src_re/fmv_levelb_transition_relocalization.c",
            "generator": "tools/phase4_fmv_levelb_two_pc_first_hit.py",
            "config": "config/phase4_fmv_levelb_two_pc_first_hit.yaml",
            "adapter": "tools/phase4_duckstation_two_pc_first_hit.py",
            "guard": "tests/test_phase4_fmv_levelb_two_pc_first_hit.py",
        },
        "iteration work packet no longer binds the two-PC claim",
    )
    _require(
        "both managed execute stops" in packet["exact_claim"]
        and "incomplete removal of either owned breakpoint"
        in packet["explicit_falsifier"]
        and packet["evidence_domain"]
        == "static_current_debugger_interface_and_synthetic_first_hit_transcript"
        and any(
            "No DuckStation process" in item
            for item in packet["non_claims"]
        ),
        "work packet first-hit semantic boundary drifted",
    )
    return {
        "sha256": CONFIGURATION["work_packet"]["sha256"],
        "exact_claim": packet["exact_claim"],
        "explicit_falsifier": packet["explicit_falsifier"],
        "evidence_domain": packet["evidence_domain"],
        "inventory": packet["inventory"],
    }


def _transition_boundary(
    plan: dict[str, Any],
) -> dict[str, Any]:
    _path, document = _pinned_json(
        CONFIGURATION["transition_relocalization"],
        "transition re-localization",
    )
    boundaries = document.get("earlier_transition_boundaries") or []
    expected = [
        {
            "pc": "0x8004FD74",
            "a0": 3,
            "a1": 0,
            "selection": "negative_pending_request",
        },
        {
            "pc": "0x8005029C",
            "a0": 6,
            "a1": 128,
            "selection": "nonnegative_pending_request",
        },
    ]
    observed = [
        {
            key: row[key]
            for key in ("pc", "a0", "a1", "selection")
        }
        for row in boundaries
    ]
    typed = [
        {
            "pc": f"0x{int(stop['params']['address']):08X}",
            "a0": stop["required_registers"]["a0"],
            "a1": stop["required_registers"]["a1"],
        }
        for stop in plan["breakpoint_sequence"]
    ]
    _require(
        document.get("schema")
        == "abl-phase4-fmv-levelb-transition-relocalization/1"
        and document.get("falsifier", {}).get("outcome") == "survived"
        and document.get("relocalization", {}).get("earlier_first_hit_set")
        == ["0x8004FD74", "0x8005029C"]
        and document["relocalization"]["first_hit_set_complete"] is True
        and document["relocalization"]["new_live_escalation_authorized"]
        is False
        and document["claim_boundary"]["dimension_promoted"] is False
        and observed == expected
        and typed
        == [
            {"pc": "0x8004FD74", "a0": 3, "a1": 0},
            {"pc": "0x8005029C", "a0": 6, "a1": 128},
        ],
        "typed first-hit plan differs from the static transition boundary",
    )
    source = "src_re/fmv_levelb_transition_relocalization.c"
    source_hash = document.get("source_dependencies", {}).get(source)
    source_path = common.ROOT / source
    _require(
        isinstance(source_hash, str)
        and source_path.is_file()
        and common.sha256(source_path) == source_hash,
        "transition semantic source identity drifted",
    )
    return {
        "sha256": CONFIGURATION["transition_relocalization"]["sha256"],
        "schema": document["schema"],
        "first_hit_set": document["relocalization"]["earlier_first_hit_set"],
        "boundaries": expected,
        "semantic_source": {
            "path": source,
            "sha256": source_hash,
            "status": "documentation_grade_non_matching",
        },
        "prior_exact_pc_outcome": "falsified_repeated",
        "new_live_escalation_authorized": False,
    }


def _debugger(plan: dict[str, Any]) -> dict[str, Any]:
    manifest_path, manifest = _pinned_json(
        CONFIGURATION["rpc_manifest"], "candidate-HEAD RPC manifest"
    )
    _capsule_path, capsule = _pinned_json(
        CONFIGURATION["capsule_index"], "central capsule authority"
    )
    source_root = Path(manifest["source"]["canonical_path"]).expanduser()
    identity = plan["identity_join"]
    media = [
        row
        for row in capsule.get("pristine_media") or []
        if row.get("path", "").endswith(".bin")
    ]
    _require(
        identity["rpc_manifest_sha256"] == common.sha256(manifest_path)
        and identity["source_revision"] == manifest["source"]["revision"]
        and identity["source_dirty_state_hash"]
        == manifest["source"]["dirty_state_hash"]
        and identity["dispatcher_sha256"]
        == manifest["source"]["dispatcher_sha256"]
        and identity["binary_sha256"]
        == manifest["binaries"]["build-release/bin/duckstation-qt"]["sha256"],
        "first-hit identity differs from the RPC manifest",
    )
    _require(
        capsule.get("complete") is True
        and len(media) == 1
        and identity["media_serial"] == "SCUS-94288"
        and identity["media_sha256"] == media[0]["sha256"],
        "first-hit media differs from pristine authority",
    )
    missing = sorted(
        set(adapter.REQUIRED_METHODS) - set(manifest["methods"]["current"])
    )
    _require(not missing, f"RPC manifest lacks required methods: {missing}")
    for relative, pin in manifest["source"]["files"].items():
        path = source_root / relative
        _require(
            path.is_file()
            and path.stat().st_size == pin["size"]
            and common.sha256(path) == pin["sha256"],
            f"RPC source dependency drifted: {relative}",
        )
    binary_relative = "build-release/bin/duckstation-qt"
    binary = source_root / binary_relative
    binary_pin = manifest["binaries"][binary_relative]
    _require(
        binary.is_file()
        and binary.stat().st_size == binary_pin["size"]
        and common.sha256(binary) == binary_pin["sha256"],
        "RPC running-binary candidate identity drifted",
    )
    dispatcher = (
        source_root / manifest["source"]["dispatcher_path"]
    ).read_text()
    docs = (source_root / "docs/external-debugger.md").read_text()
    _require(
        "HandleListBreakpoints" in dispatcher
        and "HandleAddBreakpoint" in dispatcher
        and "HandleRemoveBreakpoint" in dispatcher
        and "DebuggerControlService::Resume()" in dispatcher
        and "Use a normal" in docs
        and "breakpoint if you need to manage it" in docs
        and "Churn-safe" in docs
        and "debugger.listBreakpoints" in docs,
        "managed breakpoint semantics drifted",
    )
    return {
        "manifest_sha256": CONFIGURATION["rpc_manifest"]["sha256"],
        "capsule_index_sha256": CONFIGURATION["capsule_index"]["sha256"],
        "source_root": str(source_root),
        "source_revision": manifest["source"]["revision"],
        "source_dirty_state_hash": manifest["source"]["dirty_state_hash"],
        "dispatcher_sha256": manifest["source"]["dispatcher_sha256"],
        "binary_path": binary_relative,
        "binary_sha256": binary_pin["sha256"],
        "required_methods": list(adapter.REQUIRED_METHODS),
        "required_methods_present": True,
        "managed_breakpoint_boundary": "pre-instruction execute pause",
        "temporary_breakpoints_used": False,
    }


class SyntheticRpc:
    """Deterministic dual-branch transcript for adapter semantics."""

    def __init__(self, winner_index: int) -> None:
        self.winner_index = winner_index
        self.calls: list[tuple[str, str, dict[str, Any], int]] = []
        self.breakpoints: list[dict[str, Any]] = []
        self.resumed = False

    def __call__(
        self,
        server_session_id: str,
        method: str,
        params: dict[str, Any],
        socket_timeout_ms: int,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                server_session_id,
                method,
                copy.deepcopy(params),
                socket_timeout_ms,
            )
        )
        winner_pc = (0x8004FD74, 0x8005029C)[self.winner_index]
        if method == "debugger.status":
            if self.resumed:
                return {
                    "valid": True,
                    "paused": True,
                    "frame": 15796,
                    "pc": f"0x{winner_pc:08X}",
                }
            return {
                "valid": True,
                "paused": True,
                "frame": 15792,
                "pc": "0x80050324",
            }
        if method == "debugger.listBreakpoints":
            rows = copy.deepcopy(self.breakpoints)
            if self.resumed and len(rows) == 2:
                rows[self.winner_index]["hit_count"] = 1
                rows[self.winner_index]["trigger_count"] = 1
            return {"breakpoints": rows}
        if method == "debugger.addBreakpoint":
            number = 41 + len(self.breakpoints)
            row = {
                "id": f"bp_{number}",
                "number": number,
                "type": "execute",
                "address": f"0x{int(params['address']):08X}",
                "enabled": True,
                "temporary": False,
                "conditional": False,
                "condition": None,
                "hit_count": 0,
                "trigger_count": 0,
            }
            self.breakpoints.append(row)
            return {
                "id": row["id"],
                "number": number,
                "breakpoint": copy.deepcopy(row),
            }
        if method == "debugger.resume":
            self.resumed = True
            return {
                "valid": True,
                "paused": False,
                "running": True,
                "frame": 15792,
                "pc": "0x80050324",
            }
        if method == "debugger.getRegisters":
            values = (
                {"pc": 0x8004FD74, "a0": 3, "a1": 0},
                {"pc": 0x8005029C, "a0": 6, "a1": 128},
            )[self.winner_index]
            return {"registers": values}
        if method == "debugger.removeBreakpoint":
            identifier = params["id"]
            self.breakpoints = [
                row for row in self.breakpoints if row["id"] != identifier
            ]
            return {"id": identifier, "removed": True}
        if method == "capture.atomic":
            return {
                "atomic": True,
                "trigger": params["trigger"],
                "frame": 15796,
                "cycle": 8900000000 + self.winner_index,
                "cpu": {
                    "status": {
                        "valid": True,
                        "paused": True,
                        "frame": 15796,
                        "pc": f"0x{winner_pc:08X}",
                    },
                    "registers": {"pc": winner_pc},
                },
            }
        if method == "debugger.pause":
            return {
                "valid": True,
                "paused": True,
                "frame": 15796,
                "pc": f"0x{winner_pc:08X}",
            }
        raise AssertionError(f"unexpected synthetic method: {method}")


def _synthetic(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for winner_index in range(2):
        rpc = SyntheticRpc(winner_index)
        result = adapter.execute_first_hit(
            rpc,
            plan,
            f"synthetic-session-first-hit-{winner_index}",
            plan["identity_join"],
            sleep=lambda _seconds: None,
        )
        methods = [
            method for _session, method, _params, _timeout in rpc.calls
        ]
        _require(
            result["complete"] is True
            and result["first_hit"]["pc"]
            == ("0x8004FD74", "0x8005029C")[winner_index]
            and result["cleanup"]["remaining_breakpoints"] == 0
            and result["cleanup"]["owned_breakpoint_ids"]
            == ["bp_41", "bp_42"]
            and methods
            == [
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
            and all(
                event["server_session_id"]
                == f"synthetic-session-first-hit-{winner_index}"
                and event["socket_timeout_ms"] == 5000
                and len(event["result_sha256"]) == 64
                for event in result["command_events"]["events"]
            ),
            "synthetic two-PC command/result transcript drifted",
        )
        rows.append(
            {
                "synthetic": True,
                "complete": result["complete"],
                "server_session_id": result["server_session_id"],
                "plan_sha256": result["plan_sha256"],
                "method_sequence": methods,
                "first_hit": result["first_hit"],
                "execution": result["execution"],
                "cleanup": result["cleanup"],
                "command_event_count": len(
                    result["command_events"]["events"]
                ),
                "command_result_hashes": [
                    event["result_sha256"]
                    for event in result["command_events"]["events"]
                ],
            }
        )
    return rows


def _receipt_admission(plan: dict[str, Any]) -> dict[str, Any]:
    runtime = live_emitter.load_runtime(RUNTIME_PATH)
    _require(
        runtime["observer_plan"]["direct_command_plan"] == plan
        and runtime["execution"]["capture_window"]
        == {
            "clock": "emulator_frame",
            "start": 15792,
            "stop": 15856,
            "stop_inclusive": False,
        },
        "tracked v2 emitter differs from the selected two-PC plan",
    )
    method_schemas = {
        method: adapter.sha256_bytes(method.encode())
        for method in (
            set(adapter.REQUIRED_METHODS)
            | metrics.REQUIRED_LIVE_COMMAND_METHODS
            | metrics.REQUIRED_ATOMIC_COMMAND_METHODS
        )
    }
    admissions = []
    for winner_index in range(2):
        session_id = f"synthetic-v2-first-hit-{winner_index}"
        direct = adapter.execute_first_hit(
            SyntheticRpc(winner_index),
            plan,
            session_id,
            plan["identity_join"],
            sleep=lambda _seconds: None,
        )
        atomic_events = [
            {
                "sequence": index,
                "server_session_id": session_id,
                "method": method,
                "params": params,
                "result_sha256": adapter.sha256_bytes(
                    metrics.canonical_bytes(result)),
                "result": result,
            }
            for index, (method, params, result) in enumerate([
                ("debugger.capabilities", {}, {"identity": "synthetic"}),
                ("debugger.status", {}, {"game_serial": "SCUS-94288"}),
                ("emulator.getMediaInfo", {}, {
                    "serial": "SCUS-94288",
                    "sha256": metrics.PRISTINE_MEDIA_SHA256,
                }),
                ("scenario.runBatch", {"plan_sha256": "2" * 64}, {
                    "batch_id": f"batch-first-hit-{winner_index}",
                    "job_ids": ["job-anchor"],
                }),
                ("scenario.getBatch", {
                    "batch_id": f"batch-first-hit-{winner_index}",
                    "include_results": True,
                }, {
                    "batch_id": f"batch-first-hit-{winner_index}",
                    "status": "completed",
                    "job_ids": ["job-anchor"],
                }),
            ])
        ]
        events = {
            "schema": "abl-phase4-live-command-events/1",
            "complete": True,
            "errors": [],
            "events": atomic_events + [
                {**event, "sequence": len(atomic_events) + index}
                for index, event in enumerate(
                    direct["command_events"]["events"])
            ],
        }
        raw = {
            "schema": "abl-phase4-live-raw-results/1",
            "complete": True,
            "errors": [],
            "counters": {
                "server_session_id": session_id,
                "launches": 1,
                "atomic_jobs": 1,
                "replay_frames": 15792,
                "observer_frames": 0,
                "instructions": 0,
            },
            "sessions": [{
                "server_session_id": session_id,
                "launch_sequence": 0,
            }],
            "results": [{
                "job_id": "job-anchor",
                "server_session_id": session_id,
                "status": "completed",
                "replay_start": 0,
                "replay_stop": 15792,
                "observer_start": 15792,
                "observer_stop": 15792,
                "instruction_start": 0,
                "instruction_stop": 0,
            }],
        }
        pagination = {
            "schema": "abl-phase4-live-pagination/1",
            "complete": True,
            "errors": [],
            "truncated": False,
            "pages_complete": True,
            "pages": [],
        }
        experiment = {
            "anchor": {"media_sha256": metrics.PRISTINE_MEDIA_SHA256},
            "execution": runtime["execution"],
            "domain": runtime["domain"],
            "duckstation_executable_sha256":
                plan["identity_join"]["binary_sha256"],
        }
        media = {"capabilities": {"method_schemas": method_schemas}}
        metrics._validate_observer_plan(
            runtime["observer_plan"], "synthetic observer")
        metrics._validate_result_doc(
            events,
            "abl-phase4-live-command-events/1",
            "synthetic command events",
        )
        derived = metrics._validate_direct_two_pc_first_hit_stream(
            runtime["observer_plan"],
            events,
            raw,
            pagination,
            experiment,
            media,
            "tools/phase4_duckstation_two_pc_first_hit.py",
            events["events"][4:5],
            common.ROOT,
            "synthetic direct first-hit",
        )
        _require(
            derived is not None
            and derived["first_hit"]["pc"]
            == ("0x8004FD74", "0x8005029C")[winner_index]
            and derived["execution"]["frame_ceiling"] == 15856
            and derived["cleanup"]["remaining_breakpoints"] == 0,
            "method-metrics admission did not reproduce both first-hit branches",
        )
        admissions.append({
            "winner_pc": derived["first_hit"]["pc"],
            "command_event_count": len(direct["command_events"]["events"]),
            "frame_ceiling": derived["execution"]["frame_ceiling"],
            "remaining_breakpoints": derived["cleanup"][
                "remaining_breakpoints"],
            "admitted": True,
        })
    return {
        "live_receipt_schema": metrics.LIVE_SCHEMA,
        "observer_plan_schema": runtime["observer_plan"]["schema"],
        "adapter_path": "tools/phase4_duckstation_two_pc_first_hit.py",
        "adapter_sha256": common.sha256(
            common.ROOT / "tools/phase4_duckstation_two_pc_first_hit.py"),
        "emitter_path":
            "tools/phase4_fmv_levelb_two_pc_first_hit_live.py",
        "emitter_sha256": common.sha256(
            common.ROOT
            / "tools/phase4_fmv_levelb_two_pc_first_hit_live.py"),
        "runtime_path":
            "config/phase4_fmv_levelb_two_pc_first_hit_runtime.yaml",
        "runtime_sha256": common.sha256(RUNTIME_PATH),
        "metrics_validator_path": "tools/phase4_method_metrics.py",
        "metrics_validator_sha256": common.sha256(
            common.ROOT / "tools/phase4_method_metrics.py"),
        "capture_window": runtime["execution"]["capture_window"],
        "result_limits": runtime["observer_plan"]["result_limits"],
        "synthetic_admissions": admissions,
        "historical_observer_schema_unchanged": True,
        "live_receipts_emitted": 0,
    }


def build(
    configuration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    global CONFIGURATION, RUN_ROOT
    original = CONFIGURATION
    original_run = RUN_ROOT
    if configuration is not None:
        CONFIGURATION = copy.deepcopy(configuration)
        RUN_ROOT = Path(CONFIGURATION["run_root"])
    try:
        packet = _work_packet()
        plan = CONFIGURATION["first_hit_plan"]
        errors = adapter.validate_plan(plan)
        _require(
            not errors,
            f"two-PC first-hit plan rejected: {'; '.join(errors)}",
        )
        transition = _transition_boundary(plan)
        debugger = _debugger(plan)
        synthetic = _synthetic(plan)
        admission = _receipt_admission(plan)
        return {
            "_comment": (
                "Static v2 emitter/validator readiness only. All retained "
                "first-hit executions are synthetic; no native branch, DMA "
                "event or dimension is admitted."
            ),
            "schema": "abl-phase4-fmv-levelb-two-pc-first-hit/1",
            "generated": _stable_generated(),
            "campaign_id": CONFIGURATION["campaign_id"],
            "row_id": CONFIGURATION["row_id"],
            "dimension": CONFIGURATION["dimension"],
            "lane": CONFIGURATION["lane"],
            "inputs": {
                "config_sha256": common.sha256(CONFIG_PATH),
                "adapter_sha256": common.sha256(
                    common.ROOT
                    / "tools/phase4_duckstation_two_pc_first_hit.py"
                ),
                "rpc_manifest_sha256": debugger["manifest_sha256"],
                "capsule_index_sha256": debugger[
                    "capsule_index_sha256"
                ],
                "transition_relocalization_sha256": transition["sha256"],
                "work_packet_sha256": packet["sha256"],
                "semantic_source_sha256": transition[
                    "semantic_source"
                ]["sha256"],
                "live_emitter_sha256": admission["emitter_sha256"],
                "runtime_sha256": admission["runtime_sha256"],
                "method_metrics_sha256": admission[
                    "metrics_validator_sha256"],
            },
            "work_packet": packet,
            "static_transition_boundary": transition,
            "debugger": debugger,
            "plan": copy.deepcopy(plan),
            "synthetic_executions": synthetic,
            "v2_receipt_admission": admission,
            "falsifier": {
                "outcome": "survived_dual_branch_preflight",
                "predicate": packet["explicit_falsifier"],
                "native_evaluation": False,
                "checks": {
                    "exact_two_managed_stops": True,
                    "both_listed_before_resume": True,
                    "target_specific_registers": True,
                    "winner_counter_exactly_one": True,
                    "loser_counter_zero": True,
                    "both_owned_ids_removed": True,
                    "post_cleanup_breakpoint_set_empty": True,
                    "finite_frame_and_poll_bounds": True,
                    "exact_64_frame_receipt_bound": True,
                    "normalized_result_bodies_retained": True,
                    "single_server_session_per_transcript": True,
                    "tracked_v2_receipt_emitter": True,
                    "dual_branch_method_metrics_admission": True,
                    "historical_observer_schema_unchanged": True,
                    "current_debugger_identity_joined": True,
                    "static_transition_identity_joined": True,
                    "retired_exact_pc_not_promoted": True,
                    "live_execution_absent": True,
                    "dimension_promotion_absent": True,
                },
            },
            "claim_boundary": copy.deepcopy(
                CONFIGURATION["claim_boundary"]
            ),
            "record_counts": {
                "offline_queries_executed_this_iteration": 0,
                "live_receipts_executed_this_iteration": 0,
                "synthetic_transcripts_executed": 2,
                "native_first_hits_claimed": 0,
                "dma_events_claimed": 0,
                "promoted_dimensions": 0,
            },
            "errors": [],
            "valid": True,
        }
    finally:
        CONFIGURATION = original
        RUN_ROOT = original_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            raise SystemExit("phase4 E15 two-PC first-hit artifact is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: E15 two-PC first-hit preflight "
        "(synthetic transcripts=2, live receipts=0, promoted dimensions=0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
