#!/usr/bin/env python3
"""Bank the E15 exact-PC live preflight without executing DuckStation."""
from __future__ import annotations

import argparse
import copy
from datetime import date
import json
from pathlib import Path
from typing import Any

import phase4_common as common
import phase4_duckstation_exact_pc_batch as exact_adapter
import phase4_duckstation_late_batch as late_adapter
import phase4_fmv_levelb_region_b_dma_exact_pc_arm as exact_arm
import phase4_method_metrics as method_metrics


CONFIG_PATH = (
    common.ROOT
    / "config/phase4_fmv_levelb_region_b_dma_exact_pc_live.yaml"
)
OUTPUT = (
    common.ROOT
    / "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_preflight.json"
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


def _pinned_path(spec: dict[str, Any], label: str) -> Path:
    raw = Path(spec["path"])
    path = raw if raw.is_absolute() else common.ROOT / raw
    _require(path.is_file(), f"{label} is missing")
    _require(
        common.sha256(path) == spec["sha256"],
        f"{label} identity drifted",
    )
    expected_bytes = spec.get("bytes")
    if expected_bytes is not None:
        _require(
            path.stat().st_size == expected_bytes,
            f"{label} size drifted",
        )
    return path


def _pinned_json(spec: dict[str, Any], label: str) -> tuple[Path, dict]:
    path = _pinned_path(spec, label)
    return path, common.load_json(path)


def _validate_work_packet(configuration: dict[str, Any]) -> dict[str, Any]:
    _path, packet = _pinned_json(
        configuration["work_packet"], "iteration work packet"
    )
    expected_layers = {
        "receipt_validator": "tools/phase4_method_metrics.py",
        "receipt_guard": "tests/test_phase4_method_metrics.py",
        "exact_pc_adapter": "tools/phase4_duckstation_exact_pc_batch.py",
        "adapter_guard": "tests/test_phase4_duckstation_exact_pc_batch.py",
        "preflight_artifact": (
            "analysis/"
            "phase4_fmv_levelb_region_b_dma_exact_pc_preflight.json"
        ),
        "closure_debt": "analysis/phase4_closure_debt.json",
    }
    _require(
        packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("iteration") == 2
        and packet.get("campaign_id") == configuration["campaign_id"]
        and packet.get("row_ids") == [configuration["row_id"]]
        and packet.get("first_unmet_dimension")
        == configuration["dimension"]
        and packet.get("next_lane") == configuration["lane"]
        and packet.get("predicted_authoritative_machine_layer")
        == expected_layers,
        "iteration work packet no longer binds this exact-PC preflight",
    )
    _require(
        packet["retained_offline_basis"]["receipt_sha256"]
        == configuration["offline_basis"]["receipt"]["sha256"]
        and packet["retained_offline_basis"]["index_sha256"]
        == configuration["offline_basis"]["external_index"]["sha256"],
        "work packet offline basis drifted",
    )
    _require(
        any(
            "work packet remains deliberately static" in item
            for item in packet["non_claims"]
        ),
        "work packet live boundary drifted",
    )
    return {
        "sha256": configuration["work_packet"]["sha256"],
        "claim": packet["claim"],
        "falsifier": packet["falsifier"],
        "evidence_domain": packet["evidence_domain"],
        "inventory": packet["inventory"],
        "selection": packet["selection"],
    }


def _validate_before_ledger(configuration: dict[str, Any]) -> dict[str, Any]:
    spec = configuration["immutable_before_ledger"]
    _path, ledger = _pinned_json(spec, "immutable iteration-before ledger")
    entries = ledger.get("entries") or []
    escalation_id = configuration["escalation_id"]
    _require(
        ledger.get("schema") == "abl-phase4-live-escalations/1"
        and ledger.get("valid") is True,
        "immutable iteration-before ledger is invalid",
    )
    matching = [
        entry
        for entry in entries
        if entry.get("id") == escalation_id
        and entry.get("state") == "planned"
        and entry.get("target_row") == configuration["row_id"]
        and entry.get("missing_fact_id") == configuration["missing_fact_id"]
    ]
    _require(
        len(matching) == 1,
        "immutable iteration-before ledger does not admit the exact escalation",
    )
    _require(
        len([
            entry
            for entry in entries
            if entry.get("state", "planned") == "planned"
        ]) == 1,
        "immutable iteration-before ledger has an ambiguous planned set",
    )
    return {
        "absolute_path": str(Path(spec["path"])),
        "sha256": spec["sha256"],
        "bytes": spec["bytes"],
        "entries": len(entries),
        "planned_entries": 1,
        "contains_fresh_escalation": True,
    }


def _validate_offline_basis(
    configuration: dict[str, Any],
) -> dict[str, Any]:
    basis = configuration["offline_basis"]
    receipt_path, receipt = _pinned_json(
        basis["receipt"], "retained offline receipt"
    )
    index_path = _pinned_path(
        basis["external_index"], "retained derived-pristine index"
    )
    outputs = receipt.get("outputs") or []
    output_path = receipt_path.parent / outputs[0]["path"].split(
        "iteration-1-receipts/", 1
    )[-1]
    _require(
        receipt.get("schema") == "abl-phase4-offline-query/1"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("execution")
        == {
            "exit_code": 0,
            "stdout": "PASS: offline query\n",
            "stdout_sha256": (
                "bf6d15363b59d2dd48e0d3cc4ff9a4e4577ce43de049899bcdde9416a6c6057c"
            ),
        },
        "retained offline receipt is not closed",
    )
    _require(
        len(receipt.get("external_inputs") or []) == 1
        and receipt["external_inputs"][0]["sha256"]
        == basis["external_index"]["sha256"]
        and len(outputs) == 1
        and outputs[0]["sha256"] == basis["result_sha256"],
        "retained offline input/output join drifted",
    )
    _require(
        output_path.is_file()
        and common.sha256(output_path) == basis["result_sha256"],
        "retained offline result bytes drifted",
    )
    result = common.load_json(output_path)
    terms = result.get("terms") or {}
    _require(
        result.get("schema")
        == "abl-phase4-offline-json-search-result/1"
        and result.get("source")
        == {
            "bytes": basis["external_index"]["bytes"],
            "sha256": basis["external_index"]["sha256"],
        }
        and len(terms) == 10
        and all(
            row == {
                "count": 0,
                "paths": [],
                "paths_truncated": False,
            }
            for row in terms.values()
        ),
        "retained offline result no longer supplies the exact negative",
    )
    return {
        "receipt_sha256": basis["receipt"]["sha256"],
        "external_index": {
            "absolute_path": str(index_path),
            "sha256": basis["external_index"]["sha256"],
            "bytes": basis["external_index"]["bytes"],
            "media_class": "derived_pristine_evidence",
        },
        "result_sha256": basis["result_sha256"],
        "result_complete": True,
        "result_truncated": False,
        "matching_paths": 0,
        "reused": True,
    }


def _validate_static_and_adapter(
    configuration: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    static_basis = configuration["static_basis"]
    _subwindow_path, subwindow = _pinned_json(
        static_basis["subwindow"], "static exact-PC subwindow"
    )
    _readiness_path, readiness = _pinned_json(
        static_basis["adapter_readiness"], "exact-PC adapter readiness"
    )
    exact_plan_path = _pinned_path(
        static_basis["exact_pc_plan"], "exact-PC plan"
    )
    _pinned_path(
        static_basis["exact_pc_adapter"], "exact-PC adapter source"
    )
    plan_config = common.load_yaml(exact_plan_path)
    plan = plan_config["exact_pc_plan"]
    errors = exact_adapter.validate_plan(plan)
    _require(not errors, f"exact-PC plan rejected: {'; '.join(errors)}")
    exact = subwindow.get("exact_pc_subwindow") or {}
    _require(
        subwindow.get("schema")
        == "abl-phase4-fmv-levelb-region-b-dma-subwindow/1"
        and exact.get("start", {}).get("pc") == "0x80046078"
        and exact.get("start", {}).get("register_assertions")
        == {"a0": 18, "a1": "0x800B5788"}
        and exact.get("stop", {}).get("pc") == "0x800460C4"
        and exact.get("cdread_submissions_between_stops") == 1,
        "static exact-PC single-submission boundary drifted",
    )
    _require(
        readiness.get("valid") is True
        and readiness.get("falsifier", {}).get("outcome")
        == "survived_synthetic_mutations"
        and readiness.get("claim_boundary", {}).get("live_executed")
        is False
        and readiness.get("synthetic_execution", {}).get(
            "command_event_count"
        )
        == 11,
        "exact-PC adapter readiness drifted",
    )
    precise = configuration["precise_plan"]
    observer = precise["direct_observer"]
    _require(
        precise["atomic_anchor"]
        == {
            "method": "scenario.runBatch",
            "recipe": "bootAndRun",
            "target_frame": 15816,
            "max_frames": 15816,
            "jobs_per_receipt": 1,
            "require_paused": True,
            "require_atomic_result": True,
        }
        and observer["start_stop"]
        == {
            "method": "debugger.runUntilAddress",
            "pc": 0x80046078,
            "boundary": "before_instruction",
        }
        and observer["required_registers"]
        == {"pc": 0x80046078, "a0": 18, "a1": 0x800B5788}
        and observer["arm_sequence"]
        == ["transferLog.clear", "transferLog.start"]
        and observer["terminal_stop"]
        == {
            "method": "debugger.runUntilAddress",
            "pc": 0x800460C4,
            "boundary": "before_instruction",
        },
        "precise live contract differs from the static/adapter boundary",
    )
    _require(
        observer["max_status_polls_per_stop"]
        == plan["execution_limit"]["max_status_polls_per_stop"]
        and observer["max_pages"]
        == plan["transfer_pagination"]["max_pages"]
        and observer["max_records"]
        == plan["transfer_pagination"]["max_records"]
        and observer["max_bytes"]
        == plan["transfer_pagination"]["max_bytes"]
        and observer["require_contiguous_indexes"] is True
        and observer["require_truncated"] is False,
        "precise live limits differ from the guarded exact-PC adapter",
    )
    return (
        {
            "subwindow_sha256": static_basis["subwindow"]["sha256"],
            "start_pc": "0x80046078",
            "stop_pc": "0x800460C4",
            "required_registers": {
                "a0": 18,
                "a1": "0x800B5788",
            },
            "cdread_submissions_between_stops": 1,
        },
        {
            "readiness_sha256": static_basis[
                "adapter_readiness"
            ]["sha256"],
            "adapter_sha256": static_basis[
                "exact_pc_adapter"
            ]["sha256"],
            "plan_sha256": static_basis["exact_pc_plan"]["sha256"],
            "required_methods": readiness["debugger"][
                "required_methods"
            ],
            "synthetic_command_events": 11,
            "native_execution": False,
        },
    )


def _validate_plans_and_ledger(
    configuration: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    ledger_path, ledger = _pinned_json(
        configuration["generated_live_ledger"],
        "generated live escalation ledger",
    )
    _require(
        ledger.get("schema") == "abl-phase4-live-escalations/1"
        and ledger.get("valid") is True,
        "generated live escalation ledger is invalid",
    )
    entries = [
        row
        for row in ledger.get("entries") or []
        if row.get("id") == configuration["escalation_id"]
    ]
    _require(
        len(entries) == 1
        and entries[0].get("state") == "planned"
        and entries[0].get("target_row") == configuration["row_id"]
        and entries[0].get("missing_fact_id")
        == configuration["missing_fact_id"],
        "fresh generated escalation is absent, duplicated or not planned",
    )
    entry = entries[0]
    receipts = {
        row["id"]: row
        for row in entry.get("receipt_plan", {}).get("receipts", [])
    }
    passive_spec = configuration["passive_plan"]
    precise_spec = configuration["precise_plan"]
    expected_ids = {
        passive_spec["receipt_id"],
        *precise_spec["receipt_ids"],
    }
    _require(
        set(receipts) == expected_ids,
        "generated escalation receipt set drifted",
    )
    passive_path = _pinned_path(passive_spec, "passive exact-PC plan")
    passive = common.load_yaml(passive_path)
    passive_errors = late_adapter.validate_plan(
        passive,
        operator_root=Path("~/Downloads/ABL"),
        escalation_doc=ledger,
    )
    _require(
        not passive_errors,
        f"passive exact-PC plan rejected: {'; '.join(passive_errors)}",
    )
    passive_row = receipts[passive_spec["receipt_id"]]
    precise_rows = [receipts[row_id] for row_id in precise_spec["receipt_ids"]]
    _require(
        passive_row["capture_window"] == passive_spec["capture_window"]
        and passive_row["execution_bound"] == passive_spec["execution_bound"]
        and passive_row["observer_method"] == "debugger.getRegisters"
        and passive_row["precise"] is False,
        "passive receipt differs from its generated escalation",
    )
    expected_precise_capture = precise_spec["direct_observer"][
        "capture_window"
    ]
    expected_precise_bound = precise_spec["direct_observer"][
        "execution_bound"
    ]
    for row in precise_rows:
        _require(
            row["capture_window"] == expected_precise_capture
            and row["execution_bound"] == expected_precise_bound
            and row["observer_method"] == "transferLog.start"
            and row["atomic_method"] == "scenario.runBatch"
            and row["precise"] is True
            and row["prelude_receipt_id"] == passive_spec["receipt_id"],
            "precise receipt differs from the exact-PC plan",
        )
    passive_window = passive_row["capture_window"]
    precise_window = precise_rows[0]["capture_window"]
    _require(
        passive_window["clock"] == precise_window["clock"]
        and passive_window["start"] < precise_window["start"]
        and passive_window["stop"] > precise_window["stop"],
        "passive capture is not strictly wider on both exact-PC sides",
    )
    _require(
        entry.get("derived_pre_run_audit", {}).get(
            "higher_priority_offline_ready_rows"
        )
        == []
        and entry.get("derived_pre_run_audit", {}).get(
            "target_classification"
        )
        == "offline_partial"
        and entry.get("derived_pre_run_audit", {}).get(
            "target_queue_rank"
        )
        == 5,
        "generated escalation priority audit drifted",
    )
    return (
        {
            "sha256": common.sha256(ledger_path),
            "entry_id": configuration["escalation_id"],
            "state": "planned",
            "receipt_ids": sorted(receipts),
            "higher_priority_offline_ready_rows": [],
        },
        {
            "passive_plan_sha256": passive_spec["sha256"],
            "passive_capture_window": passive_window,
            "precise_capture_window": precise_window,
            "passive_strictly_wider_on_both_sides": True,
            "atomic_anchor_method": "scenario.runBatch",
            "precise_observer_method": "transferLog.start",
            "same_anchor_movie_sha256": precise_spec["anchor"][
                "movie_sha256"
            ],
            "media_sha256": precise_spec["anchor"]["media_sha256"],
            "precise_receipts": precise_spec["receipt_ids"],
        },
    )


def _validate_receipt_admission(
    configuration: dict[str, Any],
) -> dict[str, Any]:
    admission = configuration["receipt_admission"]
    boundary = configuration["claim_boundary"]
    validator_path = _pinned_path(
        admission["validator"], "method-metrics receipt validator")
    _require(
        admission.get("schema")
        == "abl-phase4-exact-pc-receipt-admission/1"
        and admission.get("state") == "implemented"
        and admission.get("observer_plan_schema")
        == "abl-phase4-observer-plan/2"
        and admission.get("guard_nodes")
        == [
            (
                "tests/test_phase4_method_metrics.py::"
                "test_full_direct_exact_pc_receipt_is_admitted_by_outer_validator"
            ),
            (
                "tests/test_phase4_method_metrics.py::"
                "test_direct_exact_pc_receipt_mutations_fail_closed"
            ),
            (
                "tests/test_phase4_method_metrics.py::"
                "test_falsified_direct_exact_pc_receipt_is_adapter_replayed_and_closed"
            ),
            (
                "tests/test_phase4_method_metrics.py::"
                "test_bounded_exact_pc_falsifier_requires_retained_pause"
            ),
            (
                "tests/test_phase4_method_metrics.py::"
                "test_historical_observer_schema_cannot_admit_direct_command_events"
            ),
            (
                "tests/test_phase4_method_metrics.py::"
                "test_strict_live_receipt_recomputes_plans_media_cleanup_and_counters"
            ),
            (
                "tests/test_phase4_method_metrics.py::"
                "test_levelb_legacy_observers_are_hash_derived_non_dma_normalizations"
            ),
            (
                "tests/test_phase4_method_metrics.py::"
                "test_normalized_legacy_interface_observer_does_not_block_new_dma"
            ),
        ]
        and len(admission.get("required_before_execution") or []) == 5
        and len(admission.get("forbidden") or []) == 4,
        "exact-PC direct-command receipt admission boundary drifted",
    )
    _require(
        boundary.get("escalation_predeclared") is True
        and boundary.get("passive_plan_predeclared") is True
        and boundary.get("exact_native_and_repeat_receipts_predeclared")
        is True
        and boundary.get("before_ledger_authorized") is True
        and boundary.get("receipt_admission_complete") is True
        and boundary.get("live_executed") is False
        and boundary.get("live_receipts") == 0
        and boundary.get("dma_events_claimed") == 0
        and boundary.get("dimension_promoted") is False
        and boundary.get("next_lane") == "live",
        "non-executed exact-PC claim boundary drifted",
    )

    plan_path = _pinned_path(
        configuration["static_basis"]["exact_pc_plan"], "exact-PC plan")
    plan = common.load_yaml(plan_path)["exact_pc_plan"]
    direct = exact_adapter.execute_exact_pc_window(
        exact_arm.SyntheticRpc(),
        plan,
        "synthetic-receipt-admission-session",
        plan["identity_join"],
        sleep=lambda _seconds: None,
    )
    observer = {
        "schema": admission["observer_plan_schema"],
        "operations": [{
            "sequence": 0,
            "method": "transferLog.start",
            "args": {},
        }],
        "result_limits": {
            "max_records": plan["transfer_pagination"]["max_records"],
            "max_bytes": plan["transfer_pagination"]["max_bytes"],
            "max_pages": plan["transfer_pagination"]["max_pages"],
        },
        "direct_command_plan": plan,
    }
    method_metrics._validate_observer_plan(
        observer, "exact-PC receipt admission observer")

    def event(
        sequence: int,
        method: str,
        params: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "sequence": sequence,
            "server_session_id": "synthetic-receipt-admission-session",
            "method": method,
            "params": params,
            "result": result,
            "result_sha256": exact_adapter.sha256_bytes(
                exact_adapter.canonical_bytes(result)),
        }

    atomic_rows = [
        (
            "debugger.capabilities",
            {},
            {"identity": "synthetic-admission-capabilities"},
        ),
        ("debugger.status", {}, {"game_serial": "SCUS-94288"}),
        (
            "emulator.getMediaInfo",
            {},
            {
                "serial": "SCUS-94288",
                "sha256": method_metrics.PRISTINE_MEDIA_SHA256,
            },
        ),
        (
            "scenario.runBatch",
            {"plan_sha256": "1" * 64},
            {"batch_id": "synthetic-anchor", "job_ids": ["anchor-job"]},
        ),
        (
            "scenario.getBatch",
            {"batch_id": "synthetic-anchor", "include_results": True},
            {
                "batch_id": "synthetic-anchor",
                "status": "completed",
                "job_ids": ["anchor-job"],
            },
        ),
    ]
    atomic_events = [
        event(index, method, params, result)
        for index, (method, params, result) in enumerate(atomic_rows)
    ]
    direct_events = [
        {**row, "sequence": len(atomic_events) + index}
        for index, row in enumerate(direct["command_events"]["events"])
    ]
    command_events = {
        "schema": "abl-phase4-live-command-events/1",
        "complete": True,
        "errors": [],
        "events": atomic_events + direct_events,
    }
    method_metrics._validate_result_doc(
        command_events,
        "abl-phase4-live-command-events/1",
        "exact-PC receipt admission events",
    )
    raw = {
        "schema": "abl-phase4-live-raw-results/1",
        "complete": True,
        "errors": [],
        "counters": {
            "server_session_id": "synthetic-receipt-admission-session",
            "launches": 1,
            "atomic_jobs": 1,
            "replay_frames": 15816,
            "observer_frames": 0,
            "instructions": 0,
        },
        "sessions": [{
            "server_session_id": "synthetic-receipt-admission-session",
            "launch_sequence": 0,
        }],
        "results": [{
            "job_id": "anchor-job",
            "server_session_id": "synthetic-receipt-admission-session",
            "status": "completed",
            "replay_start": 0,
            "replay_stop": 15816,
            "observer_start": 15816,
            "observer_stop": 15816,
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
        "pages": [
            {"page": index, "record_count": page["returned"]}
            for index, page in enumerate(direct["transfer"]["pages"])
        ],
    }
    experiment = {
        "anchor": {
            "media_sha256": method_metrics.PRISTINE_MEDIA_SHA256,
        },
        "execution": {
            "bound": {
                "clock": "emulator_frame",
                "start": 0,
                "stop": 15880,
                "stop_inclusive": False,
            },
            "capture_window": {
                "clock": "emulator_frame",
                "start": 15816,
                "stop": 15880,
                "stop_inclusive": False,
            },
        },
        "domain": "dma",
        "duckstation_executable_sha256": (
            plan["identity_join"]["binary_sha256"]
        ),
    }
    methods = (
        set(exact_adapter.REQUIRED_METHODS)
        | method_metrics.REQUIRED_LIVE_COMMAND_METHODS
        | method_metrics.REQUIRED_ATOMIC_COMMAND_METHODS
    )
    media = {
        "capabilities": {
            "method_schemas": {
                method: exact_adapter.sha256_bytes(method.encode())
                for method in methods
            },
        },
    }
    terminal_gets = [atomic_events[-1]]
    derived = method_metrics._validate_direct_exact_pc_stream(
        observer,
        command_events,
        raw,
        pagination,
        experiment,
        media,
        "tools/phase4_duckstation_exact_pc_batch.py",
        terminal_gets,
        common.ROOT,
        "exact-PC receipt admission",
    )
    _require(
        derived is not None
        and derived["execution"]["anchor_frame"] == 15816
        and derived["execution"]["frame_ceiling"] == 15880
        and derived["stops"]["start_pc"] == "0x80046078"
        and derived["stops"]["terminal_pc"] == "0x800460C4"
        and derived["transfer"]["truncated"] is False,
        "exact-PC direct-command admission result drifted",
    )

    mutation_rejections = 0
    mutations: list[
        tuple[
            dict[str, Any],
            dict[str, Any],
            dict[str, Any],
        ]
    ] = []
    wrong_command = copy.deepcopy(command_events)
    wrong_command["events"][6]["params"]["address"] = "0x8004607C"
    wrong_command["events"][6]["result_sha256"] = \
        exact_adapter.sha256_bytes(
            exact_adapter.canonical_bytes(
                wrong_command["events"][6]["result"]))
    mutations.append((wrong_command, raw, pagination))
    wrong_anchor = copy.deepcopy(raw)
    wrong_anchor["results"][0]["observer_stop"] = 15817
    mutations.append((command_events, wrong_anchor, pagination))
    wrong_page = copy.deepcopy(pagination)
    wrong_page["pages"][0]["record_count"] = 1
    mutations.append((command_events, raw, wrong_page))
    for mutated_events, mutated_raw, mutated_pages in mutations:
        try:
            method_metrics._validate_direct_exact_pc_stream(
                observer,
                mutated_events,
                mutated_raw,
                mutated_pages,
                experiment,
                media,
                "tools/phase4_duckstation_exact_pc_batch.py",
                [mutated_events["events"][4]],
                common.ROOT,
                "mutated exact-PC receipt admission",
            )
        except method_metrics.MetricsError:
            mutation_rejections += 1
    _require(
        mutation_rejections == len(mutations),
        "exact-PC receipt admission did not reject every mutation",
    )
    historical = {
        "schema": "abl-phase4-observer-plan/1",
        "operations": [{
            "sequence": 0,
            "method": "debugger.getRegisters",
            "args": {},
        }],
        "result_limits": {
            "max_records": 1,
            "max_bytes": 1,
            "max_pages": 1,
        },
    }
    method_metrics._validate_observer_plan(
        historical, "historical observer regression")
    return {
        "state": "implemented",
        "validator_path": admission["validator"]["path"],
        "validator_sha256": common.sha256(validator_path),
        "observer_plan_schema": observer["schema"],
        "direct_plan_sha256": exact_adapter.sha256_bytes(
            exact_adapter.canonical_bytes(plan)),
        "atomic_anchor_jobs": 1,
        "direct_command_events": len(direct_events),
        "mutation_rejections": mutation_rejections,
        "historical_observer_schema_retained": True,
        "guard_nodes": copy.deepcopy(admission["guard_nodes"]),
        "required_before_execution": copy.deepcopy(
            admission["required_before_execution"]
        ),
        "execution_forbidden_this_iteration": True,
        "next_lane": "live",
    }


def build(configuration: dict[str, Any] | None = None) -> dict[str, Any]:
    configuration = copy.deepcopy(configuration or CONFIGURATION)
    work_packet = _validate_work_packet(configuration)
    before = _validate_before_ledger(configuration)
    offline = _validate_offline_basis(configuration)
    static, adapter = _validate_static_and_adapter(configuration)
    ledger, plans = _validate_plans_and_ledger(configuration)
    admission = _validate_receipt_admission(configuration)
    return {
        "_comment": (
            "Static receipt admission only. Synthetic replay proves the v2 "
            "direct-command boundary; no DuckStation launch, live receipt, "
            "native DMA event or dimension promotion is admitted."
        ),
        "schema": (
            "abl-phase4-fmv-levelb-region-b-dma-exact-pc-preflight/1"
        ),
        "generated": _stable_generated(),
        "campaign_id": configuration["campaign_id"],
        "row_id": configuration["row_id"],
        "dimension": configuration["dimension"],
        "lane": configuration["lane"],
        "inputs": {
            "config_sha256": common.sha256(CONFIG_PATH),
            "work_packet_sha256": work_packet["sha256"],
            "before_ledger_sha256": before["sha256"],
            "generated_live_ledger_sha256": ledger["sha256"],
            "offline_receipt_sha256": offline["receipt_sha256"],
            "offline_index_sha256": offline["external_index"]["sha256"],
            "static_subwindow_sha256": static["subwindow_sha256"],
            "adapter_readiness_sha256": adapter["readiness_sha256"],
            "exact_pc_adapter_sha256": adapter["adapter_sha256"],
            "passive_plan_sha256": plans["passive_plan_sha256"],
            "receipt_validator_sha256": admission["validator_sha256"],
        },
        "work_packet": work_packet,
        "immutable_before_ledger": before,
        "offline_basis": offline,
        "static_boundary": static,
        "adapter_readiness": adapter,
        "generated_escalation": ledger,
        "typed_plans": plans,
        "receipt_admission": admission,
        "falsifier": {
            "outcome": "survived_receipt_admission_mutations",
            "predicate": work_packet["falsifier"],
            "native_evaluation": False,
        },
        "claim_boundary": copy.deepcopy(
            configuration["claim_boundary"]
        ),
        "record_counts": {
            "offline_queries_executed_this_iteration": 0,
            "offline_queries_reused": 1,
            "live_receipts_executed_this_iteration": 0,
            "synthetic_receipt_admissions": 1,
            "dma_events_claimed": 0,
            "promoted_dimensions": 0,
        },
        "errors": [],
        "valid": True,
    }


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
            raise SystemExit("phase4 E15 exact-PC live preflight is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: E15 exact-PC receipt admission "
        "(offline reused=1, planned receipts=3, synthetic admissions=1, "
        "live receipts=0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
