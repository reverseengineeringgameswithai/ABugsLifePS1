#!/usr/bin/env python3
"""Bank the E15 exact-PC stop/arm adapter without claiming live execution."""
from __future__ import annotations

import argparse
import copy
from datetime import date
import json
from pathlib import Path
from typing import Any

import phase4_common as common
import phase4_duckstation_exact_pc_batch as adapter


CONFIG_PATH = (
    common.ROOT
    / "config/phase4_fmv_levelb_region_b_dma_exact_pc_arm.yaml"
)
OUTPUT = (
    common.ROOT
    / "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_arm.json"
)
CONFIGURATION = common.load_yaml(CONFIG_PATH)


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


def _pinned_json(spec: dict[str, Any], label: str) -> tuple[Path, dict]:
    raw_path = Path(spec["path"])
    path = raw_path if raw_path.is_absolute() else common.ROOT / raw_path
    _require(
        path.is_file() and common.sha256(path) == spec["sha256"],
        f"{label} identity drifted",
    )
    return path, common.load_json(path)


def _validate_work_packet() -> dict[str, Any]:
    _path, packet = _pinned_json(
        CONFIGURATION["work_packet"], "iteration work packet"
    )
    predicted = packet.get("predicted_authoritative_machine_layer") or {}
    _require(
        packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("iteration") == 1
        and packet.get("campaign_id") == CONFIGURATION["campaign_id"]
        and packet.get("row_ids") == [CONFIGURATION["row_id"]]
        and packet.get("first_unmet_dimension")
        == CONFIGURATION["dimension"]
        and packet.get("next_lane") == CONFIGURATION["lane"]
        and predicted
        == {
            "adapter": "tools/phase4_duckstation_exact_pc_batch.py",
            "plan_configuration": (
                "config/"
                "phase4_fmv_levelb_region_b_dma_exact_pc_arm.yaml"
            ),
            "readiness_artifact": (
                "analysis/"
                "phase4_fmv_levelb_region_b_dma_exact_pc_arm.json"
            ),
            "guard": (
                "tests/test_phase4_duckstation_exact_pc_batch.py"
            ),
        },
        "iteration work packet no longer binds the selected adapter claim",
    )
    _require(
        "no live gameplay claim" in packet["evidence_domain"]
        and any(
            "No new live escalation is authorized" in item
            for item in packet["non_claims"]
        ),
        "work packet live boundary drifted",
    )
    return {
        "sha256": CONFIGURATION["work_packet"]["sha256"],
        "claim": packet["claim"],
        "falsifier": packet["falsifier"],
        "inventory": packet["inventory"],
        "selection": packet["selection"],
    }


def _validate_static_subwindow(
    plan: dict[str, Any],
) -> dict[str, Any]:
    _path, document = _pinned_json(
        CONFIGURATION["static_subwindow"], "static exact-PC subwindow"
    )
    subwindow = document.get("exact_pc_subwindow") or {}
    start = subwindow.get("start") or {}
    stop = subwindow.get("stop") or {}
    _require(
        document.get("schema")
        == "abl-phase4-fmv-levelb-region-b-dma-subwindow/1"
        and start.get("pc") == "0x80046078"
        and start.get("boundary") == "before_instruction"
        and start.get("register_assertions")
        == {"a0": 18, "a1": "0x800B5788"}
        and start.get("actions_after_stop_before_resume")
        == ["transferLog.clear", "transferLog.start"]
        and stop.get("pc") == "0x800460C4"
        and stop.get("boundary") == "before_instruction"
        and subwindow.get("cdread_submissions_between_stops") == 1
        and subwindow.get("transfer_log_capacity") == 100000
        and document["claim_boundary"]["dimension_promoted"] is False
        and document["claim_boundary"]["next_lane"] == "static",
        "static exact-PC boundary drifted",
    )
    _require(
        plan["start_stop"]
        == {
            "method": "debugger.runUntilAddress",
            "address": 0x80046078,
            "boundary": "before_instruction",
            "required_registers": {
                "pc": 0x80046078,
                "a0": 18,
                "a1": 0x800B5788,
            },
        }
        and plan["arm_sequence"]
        == [
            {
                "sequence": 0,
                "method": "transferLog.clear",
                "params": {},
            },
            {
                "sequence": 1,
                "method": "transferLog.start",
                "params": {},
            },
        ]
        and plan["terminal_stop"]
        == {
            "method": "debugger.runUntilAddress",
            "address": 0x800460C4,
            "boundary": "before_instruction",
        },
        "typed plan differs from the static exact-PC boundary",
    )
    return {
        "sha256": CONFIGURATION["static_subwindow"]["sha256"],
        "schema": document["schema"],
        "start": start,
        "stop": stop,
        "cdread_submissions_between_stops": 1,
        "transfer_log_capacity": 100000,
    }


def _validate_debugger(plan: dict[str, Any]) -> dict[str, Any]:
    manifest_path, manifest = _pinned_json(
        CONFIGURATION["rpc_manifest"], "candidate-HEAD RPC manifest"
    )
    source_root = Path(manifest["source"]["canonical_path"]).expanduser()
    identity = plan["identity_join"]
    _capsule_path, capsule_index = _pinned_json(
        CONFIGURATION["capsule_index"], "central capsule authority"
    )
    pristine_bins = [
        row
        for row in capsule_index.get("pristine_media") or []
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
        == manifest["binaries"][
            "build-release/bin/duckstation-qt"
        ]["sha256"],
        "typed plan identity differs from the RPC manifest",
    )
    _require(
        capsule_index.get("complete") is True
        and capsule_index.get("authority")
        == (
            "hash-verified pristine SCUS-94288 retail media; "
            "ALLMODS is not an input"
        )
        and len(pristine_bins) == 1
        and identity["media_serial"] == "SCUS-94288"
        and identity["media_sha256"] == pristine_bins[0]["sha256"],
        "typed plan media differs from the central pristine authority",
    )
    current_methods = set(manifest["methods"]["current"])
    missing = sorted(set(adapter.REQUIRED_METHODS) - current_methods)
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
    documentation = (
        source_root / "docs/external-debugger.md"
    ).read_text()
    _require(
        "HandleRunUntilAddress" in dispatcher
        and "DebuggerControlService::RunUntilAddress(address)" in dispatcher
        and "set a temporary breakpoint and run" in documentation
        and "auto-clear" in documentation
        and "transferLog.clear" in documentation,
        "exact-stop or transfer-log documented semantics drifted",
    )
    return {
        "manifest_sha256": CONFIGURATION["rpc_manifest"]["sha256"],
        "capsule_index_sha256": CONFIGURATION["capsule_index"]["sha256"],
        "source_root": str(source_root),
        "source_revision": manifest["source"]["revision"],
        "source_dirty_state_hash": manifest["source"][
            "dirty_state_hash"
        ],
        "dispatcher_sha256": manifest["source"]["dispatcher_sha256"],
        "binary_path": binary_relative,
        "binary_sha256": binary_pin["sha256"],
        "required_methods": list(adapter.REQUIRED_METHODS),
        "required_methods_present": True,
        "run_until_boundary": "temporary pre-instruction breakpoint",
    }


class SyntheticRpc:
    """Deterministic method transcript used only to guard adapter semantics."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any], int]] = []
        self.status_count = 0

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
        if method == "debugger.status":
            self.status_count += 1
            statuses = (
                {
                    "valid": True,
                    "paused": True,
                    "frame": 15816,
                    "pc": "0x80050324",
                },
                {
                    "valid": True,
                    "paused": True,
                    "frame": 15817,
                    "pc": "0x80046078",
                },
                {
                    "valid": True,
                    "paused": True,
                    "frame": 15817,
                    "pc": "0x800460C4",
                },
            )
            return copy.deepcopy(statuses[self.status_count - 1])
        if method == "debugger.runUntilAddress":
            return {
                "valid": True,
                "running": True,
                "paused": False,
                "frame": 15816,
                "pc": "0x80050324",
            }
        if method == "debugger.getRegisters":
            return {
                "registers": {
                    "pc": 0x80046078,
                    "a0": 18,
                    "a1": 0x800B5788,
                }
            }
        if method == "transferLog.clear":
            return {"cleared": True}
        if method == "transferLog.start":
            return {"started": True}
        if method == "transferLog.stop":
            return {"stopped": True}
        if method == "transferLog.get":
            return {
                "events": [
                    {"index": 1, "kind": "synthetic_fixture"},
                    {"index": 2, "kind": "synthetic_fixture"},
                ],
                "total": 2,
                "truncated": False,
                "enabled": False,
            }
        if method == "capture.atomic":
            return {
                "atomic": True,
                "trigger": params["trigger"],
                "frame": 15817,
                "cycle": 9000000000,
                "cpu": {
                    "status": {
                        "valid": True,
                        "paused": True,
                        "frame": 15817,
                        "pc": "0x800460C4",
                    },
                    "registers": {"pc": 0x800460C4},
                },
                "memory": [
                    {
                        "label": "region_b_head",
                        "address": "0x800B5788",
                        "length": 256,
                    }
                ],
            }
        if method == "debugger.pause":
            return {
                "valid": True,
                "paused": True,
                "frame": 15817,
                "pc": "0x800460C4",
            }
        raise AssertionError(f"unexpected synthetic method: {method}")


def _validate_synthetic_execution(
    plan: dict[str, Any],
) -> dict[str, Any]:
    rpc = SyntheticRpc()
    result = adapter.execute_exact_pc_window(
        rpc,
        plan,
        "synthetic-session-exact-pc",
        plan["identity_join"],
        sleep=lambda _seconds: None,
    )
    methods = [method for _session, method, _params, _timeout in rpc.calls]
    expected_methods = [
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
    _require(
        methods == expected_methods
        and result["complete"] is True
        and result["stops"]["start_pc"] == "0x80046078"
        and result["stops"]["terminal_pc"] == "0x800460C4"
        and result["stops"]["registers"]
        == {
            "pc": "0x80046078",
            "a0": "0x00000012",
            "a1": "0x800B5788",
        }
        and result["transfer"]["total"] == 2
        and result["transfer"]["truncated"] is False
        and result["transfer"]["indexes_contiguous"] is True
        and all(
            event["socket_timeout_ms"] == 5000
            and event["server_session_id"] == "synthetic-session-exact-pc"
            for event in result["command_events"]["events"]
        ),
        "synthetic exact-PC command/result transcript drifted",
    )
    return {
        "synthetic": True,
        "complete": result["complete"],
        "server_session_id": result["server_session_id"],
        "plan_sha256": result["plan_sha256"],
        "method_sequence": methods,
        "stops": result["stops"],
        "execution": result["execution"],
        "transfer": {
            "total": result["transfer"]["total"],
            "truncated": result["transfer"]["truncated"],
            "indexes_contiguous": result["transfer"][
                "indexes_contiguous"
            ],
        },
        "command_event_count": len(result["command_events"]["events"]),
        "command_result_hashes": [
            event["result_sha256"]
            for event in result["command_events"]["events"]
        ],
    }


def build(configuration: dict[str, Any] | None = None) -> dict[str, Any]:
    global CONFIGURATION
    original = CONFIGURATION
    if configuration is not None:
        CONFIGURATION = copy.deepcopy(configuration)
    try:
        work_packet = _validate_work_packet()
        plan = CONFIGURATION["exact_pc_plan"]
        errors = adapter.validate_plan(plan)
        _require(not errors, f"exact-PC plan rejected: {'; '.join(errors)}")
        static = _validate_static_subwindow(plan)
        debugger = _validate_debugger(plan)
        synthetic = _validate_synthetic_execution(plan)
        return {
            "_comment": (
                "Adapter readiness only. The transcript is synthetic; no "
                "native execution, DMA event or dimension is admitted."
            ),
            "schema": (
                "abl-phase4-fmv-levelb-region-b-dma-exact-pc-arm/1"
            ),
            "generated": _stable_generated(),
            "campaign_id": CONFIGURATION["campaign_id"],
            "row_id": CONFIGURATION["row_id"],
            "dimension": CONFIGURATION["dimension"],
            "lane": CONFIGURATION["lane"],
            "inputs": {
                "config_sha256": common.sha256(CONFIG_PATH),
                "adapter_sha256": common.sha256(
                    common.ROOT
                    / "tools/phase4_duckstation_exact_pc_batch.py"
                ),
                "rpc_manifest_sha256": debugger["manifest_sha256"],
                "capsule_index_sha256": debugger[
                    "capsule_index_sha256"
                ],
                "static_subwindow_sha256": static["sha256"],
                "work_packet_sha256": work_packet["sha256"],
            },
            "work_packet": work_packet,
            "static_subwindow": static,
            "debugger": debugger,
            "plan": copy.deepcopy(plan),
            "synthetic_execution": synthetic,
            "falsifier": {
                "outcome": "survived_synthetic_mutations",
                "predicate": work_packet["falsifier"],
                "native_evaluation": False,
            },
            "claim_boundary": copy.deepcopy(
                CONFIGURATION["claim_boundary"]
            ),
            "record_counts": {
                "offline_queries_executed_this_iteration": 0,
                "live_receipts_executed_this_iteration": 0,
                "synthetic_transcripts_executed": 1,
                "dma_events_claimed": 0,
                "promoted_dimensions": 0,
            },
            "errors": [],
            "valid": True,
        }
    finally:
        CONFIGURATION = original


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
            raise SystemExit("phase4 E15 exact-PC arm artifact is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: E15 exact-PC adapter preflight "
        "(synthetic transcripts=1, live receipts=0, promoted dimensions=0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
