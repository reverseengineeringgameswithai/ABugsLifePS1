#!/usr/bin/env python3
"""Run one native phase-neutral nine-PC Menu-movie coverage experiment.

The atomic scenario jobs remain uninstrumented endpoint controls.  The direct
``movie.traceToFrame`` operation then performs its own same-anchor
uninstrumented/passive cached-interpreter pair and is retained as a typed
command event in the v2 receipt.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml

import phase4_duckstation_batch as batch
import phase4_common as common


ESCALATION_ID = "P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE"
MISSING_FACT_ID = "E15/menu-phase-neutral-owner-coverage"
BOOT_PCS = (0x8004FB5C, 0x8004FB68, 0x8004FB74)
NONBOOT_PCS = (
    0x8004FFD4, 0x800500D8, 0x80050284,
    0x8005031C, 0x8005036C, 0x8005B788,
)
TARGET_PCS = BOOT_PCS + NONBOOT_PCS


def _direct_operation(plan: dict[str, Any]) -> dict[str, Any] | None:
    operations = (plan.get("v2_receipt") or {}).get(
        "observer_plan", {}).get("operations") or []
    matches = [
        row for row in operations
        if isinstance(row, dict) and row.get("method") == "movie.traceToFrame"
    ]
    return matches[0] if len(matches) == 1 else None


def direct_rpc_params(plan: dict[str, Any]) -> dict[str, Any]:
    """Derive the exact closed RPC params from the typed observer plan."""
    operation = _direct_operation(plan)
    if operation is None:
        raise ValueError("plan lacks one direct movie.traceToFrame operation")
    args = operation["args"]
    return {
        "path": args["path"],
        "frame": args["frame"],
        "ranges": [
            {
                "start": row["start"],
                "end": row["end"],
                "label": f"pc_{row['start']:08x}",
                "max_pcs": 1,
            }
            for row in args["ranges"]
        ],
        "pc_min": args["filter"]["pc_min"],
        "pc_max": args["filter"]["pc_max"],
    }


def validate_plan(
        plan: dict[str, Any], *, allow_executed: bool = False,
) -> list[str]:
    errors = list(batch.validate_plan(plan, allow_executed=allow_executed))
    if plan.get("escalation_ids") != [ESCALATION_ID]:
        errors.append("phase-neutral Menu plan has the wrong escalation ID")
    receipt = plan.get("v2_receipt") or {}
    if receipt.get("missing_fact_id") != MISSING_FACT_ID:
        errors.append("phase-neutral Menu plan has the wrong missing-fact ID")
    jobs = plan.get("jobs") or []
    if len(jobs) != 2:
        errors.append("phase-neutral Menu plan requires two atomic controls")
    elif any(job.get("instrumentation") != [] for job in jobs):
        errors.append("phase-neutral Menu atomic controls must be uninstrumented")
    elif any(job.get("recipe") != "bootAndRun" for job in jobs):
        errors.append("phase-neutral Menu controls must use cold boot")

    operations = (receipt.get("observer_plan") or {}).get("operations") or []
    direct = [
        row for row in operations
        if isinstance(row, dict) and row.get("method") == "movie.traceToFrame"
    ]
    if receipt.get("precise") is True:
        if len(operations) != 1 or len(direct) != 1:
            errors.append(
                "precise phase-neutral plan requires one direct native observer")
        else:
            args = direct[0].get("args") or {}
            ranges = args.get("ranges") or []
            expected_ranges = [
                {"start": pc, "end": pc} for pc in TARGET_PCS
            ]
            if ranges != expected_ranges:
                errors.append(
                    "phase-neutral observer must cover the exact nine singleton PCs")
            if args.get("filter") != {
                    "pc_min": min(TARGET_PCS), "pc_max": max(TARGET_PCS)}:
                errors.append("phase-neutral observer PC filter drifted")
            movie_paths = {
                (job.get("movie") or {}).get("path") for job in jobs
            }
            movie_frames = {
                (job.get("run") or {}).get("movie_frame") for job in jobs
            }
            if movie_paths != {args.get("path")} or \
                    movie_frames != {args.get("frame")} or \
                    args.get("start") != 0 or args.get("end") != args.get("frame"):
                errors.append(
                    "direct observer differs from the full same-anchor movie span")
        assertion = receipt.get("assertion_plan") or {}
        if assertion.get("kind") != "phase_neutral_menu_owner_coverage" or \
                assertion.get("boot_positive_pcs") != list(BOOT_PCS) or \
                assertion.get("nonboot_falsifier_pcs") != list(NONBOOT_PCS):
            errors.append("phase-neutral Menu assertion set drifted")
    elif direct:
        errors.append("passive Menu prelude cannot contain a direct observer")
    return sorted(set(errors))


def validate_trace_result(
        result: dict[str, Any], expected_frame: int,
) -> dict[str, Any]:
    """Validate the native result and derive the predeclared falsifier."""
    comparison = result.get("comparison") or {}
    comparison_keys = {
        "cycle_neutral", "same_ram", "same_registers", "same_cycle",
        "same_frame",
    }
    if result.get("target_frame") != expected_frame or \
            result.get("trace_mode") != "passive_cached_block_coverage" or \
            comparison_keys - set(comparison) or \
            any(not isinstance(comparison[key], bool)
                for key in comparison_keys):
        raise RuntimeError("native Menu observer result is incomplete")
    control = result.get("control") or {}
    instrumented = result.get("instrumented") or {}
    endpoint_keys = {
        "cycle", "frame", "movie_frame", "pc", "ram_sha256",
        "registers_sha256", "sp",
    }
    if set(control) != endpoint_keys or set(instrumented) != endpoint_keys:
        raise RuntimeError("native Menu observer endpoints are incomplete")
    derived = {
        "same_ram": control.get("ram_sha256") == instrumented.get("ram_sha256"),
        "same_registers": (
            control.get("registers_sha256") ==
            instrumented.get("registers_sha256")),
        "same_cycle": control.get("cycle") == instrumented.get("cycle"),
        "same_frame": (
            control.get("frame") == instrumented.get("frame") and
            control.get("movie_frame") == instrumented.get("movie_frame")),
    }
    derived["cycle_neutral"] = all(derived.values())
    if comparison != derived:
        raise RuntimeError("native Menu observer endpoints contradict comparison")
    coverage = result.get("coverage")
    if not isinstance(coverage, list) or len(coverage) != len(TARGET_PCS):
        raise RuntimeError("native Menu observer returned incomplete coverage")
    counts: dict[int, int] = {}
    for pc, row in zip(TARGET_PCS, coverage, strict=True):
        expected = f"0x{pc:08x}"
        body = row.get("coverage") or {}
        pcs = body.get("pcs")
        count_rows = body.get("counts_by_pc")
        if row.get("label") != f"pc_{pc:08x}" or row.get("range") != {
                "start": expected, "end": expected} or \
                body.get("truncated") is not False or \
                not isinstance(body.get("total_hits"), int) or \
                body["total_hits"] < 0 or \
                not isinstance(pcs, list) or \
                not isinstance(count_rows, list) or \
                not all(isinstance(item, dict) for item in count_rows) or \
                body.get("distinct_pc_count") != len(pcs) or \
                body.get("distinct_pc_count") != len(
                    count_rows) or \
                sum(item.get("count", -1) for item in count_rows) != \
                body["total_hits"] or \
                any(item.get("pc") != expected or
                    not isinstance(item.get("count"), int) or
                    item["count"] < 1
                    for item in count_rows):
            raise RuntimeError(f"native Menu observer coverage drifted at {expected}")
        counts[pc] = body["total_hits"]
    missing_boot = [pc for pc in BOOT_PCS if counts[pc] == 0]
    nonboot_hits = {pc: counts[pc] for pc in NONBOOT_PCS if counts[pc] != 0}
    reasons = []
    if not derived["cycle_neutral"]:
        reasons.append("native_endpoint_divergence")
    if missing_boot:
        reasons.append("missing_boot_positive_control")
    if nonboot_hits:
        reasons.append("nonboot_owner_hit")
    return {
        "target_frame": expected_frame,
        "cycle_neutral": derived["cycle_neutral"],
        "boot_hits": {f"0x{pc:08x}": counts[pc] for pc in BOOT_PCS},
        "nonboot_hits": {f"0x{pc:08x}": counts[pc] for pc in NONBOOT_PCS},
        "truncated": False,
        "falsifier": {
            "outcome": "falsified" if reasons else "survived",
            "reasons": reasons,
        },
    }


def run_live(
        plan: dict[str, Any], port: int, token: str, output: Path,
        poll_seconds: float = 1.0,
) -> dict[str, Any]:
    document = batch.run_live(plan, port, token, output, poll_seconds)
    operation = _direct_operation(plan)
    if operation is None:
        return document
    methods = set(
        (document["identity_results"]["debugger.capabilities"].get(
            "methods") or {}).keys())
    if "movie.traceToFrame" not in methods:
        raise RuntimeError("running DuckStation lacks movie.traceToFrame")
    module = batch._load_client_module()
    client = module.DebuggerClient("127.0.0.1", port, "ws")
    client.authenticate(token)
    client.transport.sock.settimeout(300)
    params = direct_rpc_params(plan)
    result = client.call(
        "movie.traceToFrame", params,
        timeout=max(300.0, float(params["frame"])))
    summary = validate_trace_result(result, params["frame"])
    document["generator_sha256"] = batch.sha256(Path(__file__))
    document["direct_observer"] = {
        "method": "movie.traceToFrame",
        "params": params,
        "result": result,
        "validated_summary": summary,
    }
    batch.write_json(output, document)
    return document


def _rewrite_direct_receipt(
        plan: dict[str, Any], document: dict[str, Any], receipt_dir: Path,
        run_root: Path,
) -> Path:
    """Replace the generic adapter identity and retain the direct event."""
    receipt_path = receipt_dir / "receipt.json"
    receipt = common.load_json(receipt_path)
    settings_path = receipt_dir / "settings-snapshot.json"
    observer_path = receipt_dir / "observer-plan.json"
    perturbation_path = receipt_dir / "perturbation-plan.json"
    control_path = receipt_dir / "control-plan.json"
    events_path = receipt_dir / "command-events.json"
    pagination_path = receipt_dir / "pagination.json"
    preservation_path = receipt_dir / "preservation.json"
    adapter_path = Path(__file__).resolve()

    manifest = common.load_json(batch.RPC_MANIFEST)
    normalized = batch._normalized_capabilities(
        document["identity_results"]["debugger.capabilities"], manifest)
    experiment_without_control = {
        "anchor": receipt["experiment"]["anchor"],
        "execution": receipt["experiment"]["execution"],
        "domain": receipt["experiment"]["domain"],
        "observer_plan_sha256": batch.sha256(observer_path),
        "perturbation_plan_sha256": batch.sha256(perturbation_path),
        "duckstation_source_sha256": normalized["source_sha256"],
        "duckstation_executable_sha256": normalized["executable_sha256"],
        "api_surface_sha256": normalized["api_surface_sha256"],
        "adapter_source_sha256": batch.sha256(adapter_path),
    }
    control = {
        "schema": "abl-phase4-control-plan/1",
        "role": plan["v2_receipt"]["control_role"],
        "paired_run_basis_sha256": batch.sha256_bytes(
            batch.canonical_bytes(experiment_without_control)),
        "anchor_sha256": batch.sha256_bytes(
            batch.canonical_bytes(experiment_without_control["anchor"])),
        "only_difference_plan_sha256": batch.sha256(perturbation_path),
        "assertion_plan_sha256": batch.sha256_bytes(batch.canonical_bytes(
            plan["v2_receipt"]["assertion_plan"])),
    }
    batch.write_json(control_path, control)
    receipt["experiment"] = {
        "executor_role": "investigator",
        **experiment_without_control,
        "control_plan_sha256": batch.sha256(control_path),
    }
    atomic_plan_sha256 = batch.sha256_bytes(batch.canonical_bytes({
        "anchor": receipt["experiment"]["anchor"],
        "execution": receipt["experiment"]["execution"],
        "observer_plan_sha256": batch.sha256(observer_path),
        "perturbation_plan_sha256": batch.sha256(perturbation_path),
        "control_plan_sha256": batch.sha256(control_path),
    }))

    events = common.load_json(events_path)
    run_event = next(
        row for row in events["events"]
        if row["method"] == "scenario.runBatch")
    run_event["params"]["plan_sha256"] = atomic_plan_sha256
    direct = document["direct_observer"]
    direct_result = direct["result"]
    events["events"].append({
        "sequence": len(events["events"]),
        "server_session_id": run_event["server_session_id"],
        "method": direct["method"],
        "params": direct["params"],
        "result_sha256": batch.sha256_bytes(
            batch.canonical_bytes(direct_result)),
        "result": direct_result,
    })
    batch.write_json(events_path, events)

    coverage = direct_result["coverage"]
    record_count = sum(
        row["coverage"]["distinct_pc_count"] for row in coverage)
    batch.write_json(pagination_path, {
        "schema": "abl-phase4-live-pagination/1",
        "complete": True,
        "errors": [],
        "truncated": False,
        "pages_complete": True,
        "pages": [{"page": 0, "record_count": record_count}],
    })
    receipt["evidence"]["adapter_source"] = {
        "scope": "repo",
        "path": "tools/phase4_fmv_menu_phase_neutral_live.py",
        "sha256": batch.sha256(adapter_path),
    }
    receipt["evidence"]["control_plan"] = batch.artifact_ref(
        control_path, run_root)
    receipt["evidence"]["command_events"] = batch.artifact_ref(
        events_path, run_root)
    receipt["evidence"]["pagination"] = batch.artifact_ref(
        pagination_path, run_root)

    evidence_paths = [
        receipt_dir / "raw-results.json",
        pagination_path,
        receipt_dir / "media-capabilities.json",
        events_path,
        observer_path,
        perturbation_path,
        control_path,
        adapter_path,
        settings_path,
        receipt_dir / "owned-pid-cleanup.json",
        receipt_dir / "batch-result.json",
        receipt_dir / "owned-pid-cleanup-raw.json",
        Path(batch.__file__).resolve(),
    ]
    entries = []
    seen: set[str] = set()
    for path in evidence_paths:
        digest = batch.sha256(path)
        if digest in seen:
            continue
        seen.add(digest)
        entries.append({
            "sha256": digest,
            "size": path.stat().st_size,
            "media_class": (
                "tool_source" if path.suffix == ".py" else "runtime_receipt"),
            "preservation_required": True,
        })
    batch.write_json(preservation_path, {
        "schema": "abl-phase4-method-external-preservation/1",
        "complete": True,
        "errors": [],
        "entries": entries,
    })
    receipt["evidence"]["external_preservation_manifest"] = batch.artifact_ref(
        preservation_path, run_root)
    batch.write_json(receipt_path, receipt)
    return receipt_path


def emit_v2_receipt(
        plan: dict[str, Any], document: dict[str, Any], receipt_dir: Path,
        run_root: Path, cleanup: dict[str, Any], cleanup_raw: dict[str, Any],
        prelude_receipt: Path | None,
) -> Path:
    path = batch.emit_v2_receipt(
        plan, document, receipt_dir, run_root, cleanup, cleanup_raw,
        prelude_receipt)
    if _direct_operation(plan) is not None:
        path = _rewrite_direct_receipt(plan, document, receipt_dir, run_root)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--port", type=int)
    parser.add_argument("--token")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--receipt-dir", type=Path)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument("--owned-pid", type=int)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--prelude-receipt", type=Path)
    args = parser.parse_args()
    plan = yaml.safe_load(args.plan.read_text(encoding="utf-8"))
    errors = validate_plan(plan, allow_executed=args.validate_only)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.validate_only:
        kind = "native precise" if _direct_operation(plan) else "passive"
        print(f"PASS: {kind}; {len(plan['jobs'])} atomic controls")
        return 0
    if args.port is None or not args.token or args.output is None:
        parser.error("live execution requires --port, --token and --output")
    wants_receipt = args.receipt_dir is not None
    receipt_args = (
        args.run_root, args.config_dir, args.owned_pid, args.binary,
    )
    if not wants_receipt or any(value is None for value in receipt_args):
        parser.error(
            "live execution requires --receipt-dir, --run-root, --config-dir, "
            "--owned-pid and --binary")
    cleanup = None
    cleanup_raw = None
    try:
        document = run_live(
            plan, args.port, args.token, args.output, args.poll_seconds)
    finally:
        cleanup, cleanup_raw = batch.stop_owned_instance(
            args.config_dir.resolve(), args.binary.resolve(), args.owned_pid)
    if cleanup["complete"] is not True:
        raise RuntimeError("owned DuckStation cleanup did not close")
    receipt_path = emit_v2_receipt(
        plan, document, args.receipt_dir.resolve(), args.run_root.resolve(),
        cleanup, cleanup_raw,
        args.prelude_receipt.resolve()
        if args.prelude_receipt is not None else None)
    print(
        f"closed live receipt: {receipt_path} "
        f"sha256={batch.sha256(receipt_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
