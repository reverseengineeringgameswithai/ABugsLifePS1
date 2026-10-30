#!/usr/bin/env python3
"""Bank the falsified E15 native phase-neutral Menu-owner control."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import phase4_common as common
import phase4_fmv_menu_phase_neutral_live as live


CONFIG_PATH = common.ROOT / "config/phase4_fmv_menu_phase_neutral_result.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_menu_phase_neutral_live.json"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(os.environ.get(
    "ABL_PHASE4_RUN_ROOT", CONFIGURATION["run_root"])).resolve()
DOMAINS = ("cpu", "memory", "gpu", "spu", "movie")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _artifact(spec: dict, label: str) -> tuple[Path, dict]:
    path = (RUN_ROOT / spec["relative_path"]).resolve()
    _require(
        RUN_ROOT in path.parents,
        f"{label} escapes the retained run root")
    _require(
        path.is_file() and path.stat().st_size == spec["bytes"] and
        common.sha256(path) == spec["sha256"],
        f"{label} identity drifted")
    return path, common.load_json(path)


def _repo_artifact(spec: dict, label: str) -> tuple[Path, dict]:
    path = (common.ROOT / spec["path"]).resolve()
    _require(
        common.ROOT in path.parents and path.is_file() and
        common.sha256(path) == spec["sha256"],
        f"{label} identity drifted")
    return path, common.load_yaml(path)


def _preservation_contains(receipt: dict, batch_spec: dict) -> None:
    ref = receipt["evidence"]["external_preservation_manifest"]
    _require(ref.get("scope") == "run", "preservation is not run-owned")
    path = (RUN_ROOT / ref["path"]).resolve()
    _require(
        path.is_file() and common.sha256(path) == ref["sha256"],
        "preservation manifest identity drifted")
    preservation = common.load_json(path)
    expected = {
        "sha256": batch_spec["sha256"],
        "size": batch_spec["bytes"],
        "media_class": "runtime_receipt",
        "preservation_required": True,
    }
    _require(
        preservation.get("complete") is True and
        preservation.get("errors") == [] and
        expected in preservation.get("entries", []),
        "full result is absent from external preservation")


def _validate_identity(
        receipt: dict, batch: dict, plan: dict, spec: dict,
) -> dict:
    adapter = (
        CONFIGURATION["debugger"]["precise_adapter_sha256"]
        if spec["precise"]
        else CONFIGURATION["debugger"]["passive_adapter_sha256"])
    _require(
        receipt.get("schema") == "abl-phase4-live-run-receipt/2" and
        receipt.get("complete") is True and receipt.get("errors") == [] and
        receipt.get("precise") is spec["precise"] and
        receipt.get("escalation_id") == CONFIGURATION["escalation_id"] and
        receipt.get("missing_fact_id") == CONFIGURATION["missing_fact_id"],
        f"{spec['role']} live receipt is not closed or typed")
    experiment = receipt["experiment"]
    _require(
        experiment["anchor"]["media_sha256"] ==
        CONFIGURATION["media"]["bin_sha256"] and
        experiment["anchor"]["movie_sha256"] == spec["movie_sha256"] and
        experiment["adapter_source_sha256"] == adapter,
        f"{spec['role']} receipt anchor/adapter drifted")
    expected_prelude = spec.get("prelude_receipt")
    observed_prelude = receipt.get("prelude_receipt")
    if expected_prelude is None:
        _require(observed_prelude is None, f"{spec['role']} has an opaque prelude")
    else:
        _require(
            observed_prelude == {
                "scope": "run",
                "path": expected_prelude["relative_path"],
                "sha256": expected_prelude["sha256"],
            },
            f"{spec['role']} passive prelude join drifted")
    _require(
        live.validate_plan(plan, allow_executed=True) == [],
        f"{spec['role']} plan no longer validates")
    _require(
        batch.get("schema") == "abl-phase4-duckstation-batch-result/1" and
        batch["result"]["state"] == "completed" and
        batch["row_ids"] == [CONFIGURATION["row_id"]] and
        batch["escalation_ids"] == [CONFIGURATION["escalation_id"]],
        f"{spec['role']} batch is not the completed selected-row run")
    debugger = CONFIGURATION["debugger"]
    observed_debugger = batch["expected_debugger"]
    _require(
        observed_debugger["api_version"] == debugger["api_version"] and
        observed_debugger["schema_version"] == debugger["schema_version"] and
        observed_debugger["binary_sha256"] == debugger["binary_sha256"] and
        observed_debugger["source_revision"] == debugger["source_revision"] and
        observed_debugger["dirty_state_hash"] ==
        debugger["source_dirty_state_hash"],
        f"{spec['role']} debugger identity drifted")
    media = batch["expected_media"]
    _require(
        media["serial"] == CONFIGURATION["media"]["serial"] and
        media["sha256"] == CONFIGURATION["media"]["cue_sha256"] and
        media["tracks"][0]["sha256"] == CONFIGURATION["media"]["bin_sha256"] and
        batch["mounted_media"]["game_serial"] ==
        CONFIGURATION["media"]["serial"],
        f"{spec['role']} mounted pristine media drifted")
    cleanup_ref = receipt["evidence"]["owned_pid_cleanup"]
    cleanup_path = (RUN_ROOT / cleanup_ref["path"]).resolve()
    _require(
        cleanup_path.is_file() and
        common.sha256(cleanup_path) == cleanup_ref["sha256"] and
        common.load_json(cleanup_path).get("owned_pid_stopped") is True,
        f"{spec['role']} owned-PID cleanup drifted")
    raw_ref = receipt["evidence"]["raw_results"]
    raw_path = (RUN_ROOT / raw_ref["path"]).resolve()
    _require(
        raw_path.is_file() and common.sha256(raw_path) == raw_ref["sha256"],
        f"{spec['role']} raw result identity drifted")
    raw = common.load_json(raw_path)
    _require(
        raw.get("complete") is True and raw.get("errors") == [] and
        raw["counters"]["atomic_jobs"] == 2 and
        raw["counters"]["instructions"] == 0 and
        len(raw["sessions"]) == 1 and len(raw["results"]) == 2,
        f"{spec['role']} raw result counters drifted")
    return raw


def _capture_summary(capture: dict) -> dict:
    execution = capture["traces"]["execution"]
    return {
        "frame": capture["frame"],
        "cycle": capture["cycle"],
        "movie_reproducible": capture["movie"]["reproducible"],
        "domain_sha256": {key: _digest(capture[key]) for key in DOMAINS},
        "execution_events": execution["total"],
        "execution_truncated": execution["truncated"],
    }


def validate_pair(spec: dict, receipt: dict, batch: dict, plan: dict) -> dict:
    raw = _validate_identity(receipt, batch, plan, spec)
    _preservation_contains(receipt, spec["batch_result"])
    jobs = batch["result"]["jobs"]
    _require(
        len(jobs) == 2 and all(row["state"] == "completed" for row in jobs),
        f"{spec['role']} atomic jobs are incomplete")
    captures = [row["result"]["capture"] for row in jobs]
    for capture in captures:
        movie = capture["movie"]
        execution = capture["traces"]["execution"]
        _require(
            capture["frame"] == spec["endpoint_frame"] and
            movie["truncated"] is False and
            movie["reproducible"] is False and
            movie["start_state"]["from_boot"] is True and
            execution["truncated"] is False and
            len(execution["events"]) == execution["total"] == 0,
            f"{spec['role']} atomic endpoint is incomplete")
    endpoint_equal = {
        "frame": captures[0]["frame"] == captures[1]["frame"],
        "cycle": captures[0]["cycle"] == captures[1]["cycle"],
        **{key: captures[0][key] == captures[1][key] for key in DOMAINS},
    }
    _require(
        endpoint_equal == spec["expected_endpoint_equal"],
        f"{spec['role']} atomic endpoint classification drifted")
    direct_summary = None
    direct_comparison = None
    if spec["precise"]:
        direct = batch.get("direct_observer") or {}
        _require(
            direct.get("method") == "movie.traceToFrame" and
            direct.get("params") == live.direct_rpc_params(plan),
            f"{spec['role']} direct observer plan drifted")
        direct_summary = live.validate_trace_result(
            direct.get("result") or {}, spec["target_frame"])
        _require(
            direct_summary == direct.get("validated_summary") and
            direct_summary["boot_hits"] == CONFIGURATION["boot_positive"] and
            direct_summary["nonboot_hits"] ==
            CONFIGURATION["nonboot_falsifiers"] and
            direct_summary["falsifier"] == {
                "outcome": "falsified",
                "reasons": [
                    "native_endpoint_divergence", "nonboot_owner_hit"],
            },
            f"{spec['role']} direct falsifier classification drifted")
        direct_comparison = direct["result"]["comparison"]
    else:
        _require(
            "direct_observer" not in batch,
            f"{spec['role']} passive prelude contains a direct observer")
    return {
        "role": spec["role"],
        "receipt_sha256": spec["receipt"]["sha256"],
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "plan_sha256": spec["plan"]["sha256"],
        "movie_sha256": spec["movie_sha256"],
        "precise": spec["precise"],
        "atomic_endpoint_equal": endpoint_equal,
        "atomic_jobs": [_capture_summary(capture) for capture in captures],
        "atomic_replay_frames": raw["counters"]["replay_frames"],
        "direct_observer": direct_summary,
        "direct_comparison": direct_comparison,
        "control_admissible": (
            direct_summary is not None and
            direct_summary["falsifier"]["outcome"] == "survived"),
    }


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def build() -> dict:
    pairs = []
    for spec in CONFIGURATION["receipts"]:
        _receipt_path, receipt = _artifact(
            spec["receipt"], f"{spec['role']} receipt")
        _batch_path, batch = _artifact(
            spec["batch_result"], f"{spec['role']} batch result")
        _plan_path, plan = _repo_artifact(
            spec["plan"], f"{spec['role']} plan")
        pairs.append(validate_pair(spec, receipt, batch, plan))
    precise = [row for row in pairs if row["precise"]]
    passive = [row for row in pairs if not row["precise"]]
    _require(
        len(precise) == len(passive) == 2 and
        all(not row["control_admissible"] for row in precise),
        "falsified native method classification drifted")
    return {
        "schema": "abl-phase4-fmv-menu-phase-neutral-live/1",
        "generated": stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "missing_fact_id": CONFIGURATION["missing_fact_id"],
        "receipts": pairs,
        "observation": {
            "native_control_falsified_for_both_movies": True,
            "native_endpoint_diverged_for_both_movies": True,
            "nonboot_hits_present_for_both_movies": True,
            "all_native_traces_untruncated": True,
            "all_movie_status_reproducible": False,
            "shared_nonboot_hit_counts":
                CONFIGURATION["nonboot_falsifiers"],
        },
        "record_counts": {
            "closed_v2_receipts": len(pairs),
            "atomic_jobs": sum(len(row["atomic_jobs"]) for row in pairs),
            "atomic_replay_frames": sum(
                row["atomic_replay_frames"] for row in pairs),
            "native_observer_replay_frames": sum(
                row["direct_observer"]["target_frame"] for row in precise),
            "native_coverage_hits": sum(
                sum(row["direct_observer"]["boot_hits"].values()) +
                sum(row["direct_observer"]["nonboot_hits"].values())
                for row in precise),
            "native_control_failures": sum(
                not row["control_admissible"] for row in precise),
            "owned_pids_stopped": len(pairs),
        },
        "falsifier": {
            "predicate": (
                "each native observer is endpoint-neutral, hits all three "
                "boot controls and hits no non-boot candidate"),
            "outcome": "falsified",
            "failing_receipts": [
                row["receipt_sha256"] for row in precise],
            "reasons": [
                "native_endpoint_divergence", "nonboot_owner_hit"],
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "source_dependencies": {
            "tools/phase4_fmv_menu_phase_neutral_result.py":
                common.sha256(Path(__file__)),
            "tools/phase4_fmv_menu_phase_neutral_live.py":
                common.sha256(
                    common.ROOT /
                    "tools/phase4_fmv_menu_phase_neutral_live.py"),
            "tools/phase4_duckstation_batch.py":
                common.sha256(
                    common.ROOT / "tools/phase4_duckstation_batch.py"),
            str(CONFIG_PATH.relative_to(common.ROOT)):
                common.sha256(CONFIG_PATH),
        },
        "raw_external_bytes_committed": False,
        "valid": True,
        "errors": [],
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
            raise SystemExit("phase4 native Menu result artifact is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: both native Menu observers falsified; "
        "no owner or lifecycle claim promoted", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
