#!/usr/bin/env python3
"""Bank the E15 typed late-DMA arming method without claiming execution."""
from __future__ import annotations

import argparse
import copy
from datetime import date
import json
from pathlib import Path

import phase4_common as common
import phase4_duckstation_late_batch as live


CONFIG_PATH = (
    common.ROOT / "config/phase4_fmv_levelb_region_b_dma_late_arm.yaml"
)
OUTPUT = (
    common.ROOT / "analysis/phase4_fmv_levelb_region_b_dma_late_arm.json"
)
RPC_MANIFEST = (
    common.ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
)
ESCALATIONS = common.ROOT / "analysis/phase4_live_escalations.json"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIGURATION["run_root"]).resolve()


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


def _pinned_repo_artifact(spec: dict, label: str) -> tuple[Path, dict]:
    path = common.ROOT / spec["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["sha256"],
        f"{label} identity drifted",
    )
    return path, common.load_json(path)


def _pinned_run_artifact(spec: dict, label: str) -> tuple[Path, dict]:
    path = RUN_ROOT / spec["relative_path"]
    _require(
        path.is_file()
        and path.stat().st_size == spec["bytes"]
        and common.sha256(path) == spec["sha256"],
        f"{label} identity drifted",
    )
    return path, common.load_json(path)


def _validate_plan_document(role: str, spec: dict, plan: dict) -> dict:
    errors = live.validate_plan(plan)
    _require(not errors, f"{role} plan rejected: {'; '.join(errors)}")
    jobs = plan.get("jobs") or []
    _require(len(jobs) == 2, f"{role} plan must contain one paired replay")
    receipt = plan.get("v2_receipt") or {}
    execution = receipt.get("execution") or {}
    bound = execution.get("bound") or {}
    capture = execution.get("capture_window") or {}
    expected_target = spec["prelude_target"]
    expected_stop = spec["capture_stop"]
    _require(
        receipt.get("id") == spec["receipt_id"]
        and receipt.get("missing_fact_id")
        == CONFIGURATION["missing_fact_id"]
        and bound
        == {
            "clock": "emulator_frame",
            "start": 0,
            "stop": expected_stop,
            "stop_inclusive": False,
        }
        and capture
        == {
            "clock": "emulator_frame",
            "start": expected_target,
            "stop": expected_stop,
            "stop_inclusive": False,
        },
        f"{role} typed receipt range drifted",
    )
    provisioned_movie = (
        common.ROOT / "movies/100% Runs/LEVEL01.movie.json"
    ).resolve()
    for job in jobs:
        movie_path = Path(job["movie"]["path"])
        resolved_movie = (
            movie_path.resolve()
            if movie_path.is_absolute()
            else (common.ROOT / movie_path).resolve()
        )
        _require(
            job.get("recipe") == "bootAndRun"
            and resolved_movie == provisioned_movie
            and job.get("staged_prelude")
            == {
                "kind": "emulator_advance",
                "target_frame": expected_target,
                "max_frames": expected_target,
            }
            and job.get("run") == {"frames": spec["run_frames"]},
            f"{role} staged-prelude method drifted",
        )
    methods = [
        arm.get("method")
        for arm in (jobs[0].get("instrumentation") or [])
    ]
    _require(
        (role == "passive" and methods == [])
        or (role == "precise" and methods == ["transferLog.start"]),
        f"{role} observer arming drifted",
    )
    return {
        "sha256": spec["sha256"],
        "receipt_id": spec["receipt_id"],
        "precise": receipt["precise"],
        "recipe": "bootAndRun",
        "provisioned_movie": str(provisioned_movie.relative_to(common.ROOT)),
        "prelude": {
            "kind": "emulator_advance",
            "start": 1,
            "stop": expected_target,
        },
        "execution_bound": bound,
        "capture_window": capture,
        "post_prelude_frames": spec["run_frames"],
        "observer_methods": methods or ["debugger.getRegisters"],
        "jobs": len(jobs),
    }


def _validate_plan(role: str, spec: dict) -> dict:
    path = common.ROOT / spec["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["sha256"],
        f"{role} plan identity drifted",
    )
    return _validate_plan_document(role, spec, common.load_yaml(path))


def _validate_work_packet() -> dict:
    _, packet = _pinned_run_artifact(
        CONFIGURATION["work_packet"], "iteration work packet"
    )
    _require(
        packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("iteration") == 2
        and packet.get("campaign_id") == CONFIGURATION["campaign_id"]
        and packet.get("row_ids") == [CONFIGURATION["row_id"]]
        and packet.get("first_unmet_dimension") == CONFIGURATION["dimension"]
        and packet.get("next_lane") == CONFIGURATION["lane"]
        and packet.get("evidence_domain") == "dma"
        and packet.get("escalation_id") == CONFIGURATION["escalation_id"]
        and packet.get("missing_fact_id") == CONFIGURATION["missing_fact_id"],
        "iteration work packet no longer binds the selected claim",
    )
    predicted = packet.get("predicted_authoritative_machine_layer") or {}
    _require(
        predicted.get("artifact")
        == "analysis/phase4_fmv_levelb_region_b_dma_late_arm.json"
        and predicted.get("adapter") == "tools/phase4_duckstation_batch.py",
        "work packet predicted machine layer drifted",
    )
    return {
        "sha256": CONFIGURATION["work_packet"]["sha256"],
        "claim": packet["claim"],
        "falsifier": packet["falsifier"],
        "evidence_domain": packet["evidence_domain"],
        "inventory": packet["inventory"],
        "selection": packet["selection"],
    }


def _validate_prior_evidence() -> dict:
    prior = CONFIGURATION["prior_evidence"]
    _, attempt = _pinned_repo_artifact(
        prior["dma_attempt"], "prior DMA attempt"
    )
    _, ownership = _pinned_repo_artifact(
        prior["replacement_ownership"], "replacement ownership"
    )
    _, receipt = _pinned_run_artifact(
        prior["offline_receipt"], "offline receipt"
    )
    _, output = _pinned_run_artifact(
        prior["offline_output"], "offline output"
    )
    _require(
        attempt["claim_boundary"]["next_lane"] == "live_method"
        and attempt["claim_boundary"]["first_region_b_dma_identified"]
        is False
        and attempt["observation"]["precise"]["receipt_present"] is False,
        "prior failed-closed attempt boundary drifted",
    )
    _require(
        ownership["completed_level_b_replacement_policy"][
            "common_resource_policy"
        ]["destination"]
        == "0x800B5788"
        and ownership["ownership"]["replacement_byte_owner"]
        == "E16_streaming_overlays",
        "static request ownership drifted",
    )
    _require(
        receipt.get("schema") == "abl-phase4-offline-query/1"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt["external_inputs"][0]["sha256"]
        == prior["external_index_sha256"]
        and output.get("schema")
        == "abl-phase4-offline-json-search-result/1"
        and len(output.get("terms") or {}) == 10
        and all(
            row.get("count") == 0
            and row.get("paths") == []
            and row.get("paths_truncated") is False
            for row in output["terms"].values()
        ),
        "retained offline negative result drifted",
    )
    return {
        "dma_attempt_sha256": prior["dma_attempt"]["sha256"],
        "replacement_ownership_sha256":
            prior["replacement_ownership"]["sha256"],
        "offline_receipt_sha256": prior["offline_receipt"]["sha256"],
        "offline_output_sha256": prior["offline_output"]["sha256"],
        "external_index_sha256": prior["external_index_sha256"],
        "zero_result_terms": 10,
    }


def _validate_debugger() -> dict:
    expected = CONFIGURATION["debugger"]
    manifest = common.load_json(RPC_MANIFEST)
    source = manifest.get("source") or {}
    binary = (
        (manifest.get("binaries") or {}).get(
            "build-release/bin/duckstation-qt"
        )
        or {}
    )
    scenarios = (
        (source.get("files") or {}).get(
            "docs/external-debugger-scenarios.md"
        )
        or {}
    )
    _require(
        source.get("revision") == expected["source_revision"]
        and source.get("dirty_state_hash") == expected["dirty_state_hash"]
        and source.get("dispatcher_sha256")
        == expected["dispatcher_sha256"]
        and scenarios.get("sha256") == expected["scenarios_doc_sha256"]
        and binary.get("sha256") == expected["release_binary_sha256"],
        "current DuckStation manifest does not pin the staged-prelude build",
    )
    dispatcher = Path.home() / "duckstation" / source["dispatcher_path"]
    scenario_doc = (
        Path.home()
        / "duckstation/docs/external-debugger-scenarios.md"
    )
    _require(
        dispatcher.is_file()
        and common.sha256(dispatcher) == expected["dispatcher_sha256"]
        and scenario_doc.is_file()
        and common.sha256(scenario_doc)
        == expected["scenarios_doc_sha256"]
        and "emulator_advance" in dispatcher.read_text()
        and "emulator_advance" in scenario_doc.read_text(),
        "typed emulator_advance implementation or documentation drifted",
    )
    return {
        "manifest_sha256": common.sha256(RPC_MANIFEST),
        "source_revision": expected["source_revision"],
        "dirty_state_hash": expected["dirty_state_hash"],
        "dispatcher_sha256": expected["dispatcher_sha256"],
        "scenarios_doc_sha256": expected["scenarios_doc_sha256"],
        "release_binary_sha256": expected["release_binary_sha256"],
        "adapter_sha256": common.sha256(
            common.ROOT / "tools/phase4_duckstation_late_batch.py"
        ),
    }


def _validate_escalation(passive: dict, precise: dict) -> dict:
    ledger = common.load_json(ESCALATIONS)
    matches = [
        row for row in ledger.get("entries") or []
        if row.get("id") == CONFIGURATION["escalation_id"]
    ]
    _require(
        ledger.get("valid") is True
        and ledger.get("errors") == []
        and len(matches) == 1
        and matches[0].get("state") == "planned"
        and matches[0].get("target_row") == CONFIGURATION["row_id"]
        and matches[0].get("missing_fact_id")
        == CONFIGURATION["missing_fact_id"],
        "generated ledger does not retain the planned late-arm escalation",
    )
    receipts = matches[0]["receipt_plan"]["receipts"]
    _require(
        [row["id"] for row in receipts]
        == [passive["receipt_id"], precise["receipt_id"]]
        and receipts[1]["prelude_receipt_id"] == passive["receipt_id"],
        "planned receipt linkage drifted",
    )
    return {
        "source_sha256": ledger["inputs"]["source_sha256"],
        "state": "planned",
        "receipt_ids": [row["id"] for row in receipts],
        "higher_priority_offline_ready_rows":
            matches[0]["derived_pre_run_audit"][
                "higher_priority_offline_ready_rows"
            ],
        "target_queue_rank":
            matches[0]["derived_pre_run_audit"]["target_queue_rank"],
    }


def build(configuration: dict | None = None) -> dict:
    global CONFIGURATION
    original = CONFIGURATION
    if configuration is not None:
        CONFIGURATION = copy.deepcopy(configuration)
    try:
        work_packet = _validate_work_packet()
        prior = _validate_prior_evidence()
        debugger = _validate_debugger()
        passive = _validate_plan("passive", CONFIGURATION["plans"]["passive"])
        precise = _validate_plan("precise", CONFIGURATION["plans"]["precise"])
        _require(
            passive["capture_window"]["start"]
            < precise["capture_window"]["start"]
            and passive["capture_window"]["stop"]
            > precise["capture_window"]["stop"],
            "precise observer lacks a strictly wider passive prelude",
        )
        escalation = _validate_escalation(passive, precise)
        return {
            "_comment": (
                "Method preflight only: no live receipt or DMA event is "
                "admitted by this artifact."
            ),
            "schema": "abl-phase4-fmv-levelb-region-b-dma-late-arm/1",
            "generated": _stable_generated(),
            "campaign_id": CONFIGURATION["campaign_id"],
            "row_id": CONFIGURATION["row_id"],
            "dimension": CONFIGURATION["dimension"],
            "lane": CONFIGURATION["lane"],
            "inputs": {
                "source_sha256": common.sha256(CONFIG_PATH),
                "adapter_sha256": debugger["adapter_sha256"],
                "rpc_manifest_sha256": debugger["manifest_sha256"],
                "work_packet_sha256": work_packet["sha256"],
            },
            "work_packet": work_packet,
            "prior_evidence": prior,
            "debugger": debugger,
            "plans": {"passive": passive, "precise": precise},
            "escalation": escalation,
            "falsifier": {
                "outcome": "not_evaluated",
                "reason": "live_experiment_not_executed",
                "predicate": work_packet["falsifier"],
            },
            "claim_boundary": copy.deepcopy(
                CONFIGURATION["claim_boundary"]
            ),
            "record_counts": {
                "offline_queries_executed_this_iteration": 0,
                "offline_receipts_reused": 1,
                "live_receipts_executed_this_iteration": 0,
                "planned_live_receipts": 2,
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
            raise SystemExit("phase4 E15 DMA late-arm artifact is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: E15 typed emulator-frame late-arm preflight "
        "(live receipts=0, promoted dimensions=0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
