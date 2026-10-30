#!/usr/bin/env python3
"""Bank the rejected E15 menu-owner coverage control without overclaiming it."""

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


CONFIG_PATH = common.ROOT / "config/phase4_fmv_menu_owner_coverage.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_menu_owner_coverage.json"
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
        path == RUN_ROOT or RUN_ROOT in path.parents,
        f"{label} escapes the retained run root")
    _require(
        path.is_file() and path.stat().st_size == spec["bytes"] and
        common.sha256(path) == spec["sha256"],
        f"{label} identity drifted")
    return path, common.load_json(path)


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


def _validate_identity(receipt: dict, batch: dict, spec: dict) -> None:
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
        experiment["adapter_source_sha256"] ==
        CONFIGURATION["debugger"]["adapter_sha256"],
        f"{spec['role']} receipt anchor/adapter drifted")
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


def _capture_summary(capture: dict) -> dict:
    execution = capture["traces"]["execution"]
    return {
        "frame": capture["frame"],
        "cycle": capture["cycle"],
        "movie_reproducible": capture["movie"]["reproducible"],
        "domain_sha256": {key: _digest(capture[key]) for key in DOMAINS},
        "execution_events": execution["total"],
        "execution_truncated": execution["truncated"],
        "watch_hits": {
            row["label"]: row["hit_count"] for row in execution["watches"]},
    }


def validate_pair(spec: dict, receipt: dict, batch: dict) -> dict:
    _validate_identity(receipt, batch, spec)
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
            len(execution["events"]) == execution["total"],
            f"{spec['role']} endpoint or trace is incomplete")
    summaries = [_capture_summary(row) for row in captures]
    endpoint_equal = {
        "frame": captures[0]["frame"] == captures[1]["frame"],
        "cycle": captures[0]["cycle"] == captures[1]["cycle"],
        **{key: captures[0][key] == captures[1][key] for key in DOMAINS},
    }
    _require(
        endpoint_equal == spec["expected_endpoint_equal"],
        f"{spec['role']} endpoint control classification drifted")
    if spec["precise"]:
        _require(
            [row["id"] for row in jobs] ==
            ["boot_positive_callers", "nonboot_negative_callers"],
            f"{spec['role']} precise job roles drifted")
        positive = summaries[0]
        negative = summaries[1]
        expected_positive = {
            key: value["hits"]
            for key, value in CONFIGURATION["boot_positive"].items()}
        expected_negative = {
            key: value["hits"]
            for key, value in CONFIGURATION["nonboot_falsifiers"].items()}
        _require(
            positive["watch_hits"] == expected_positive and
            negative["watch_hits"] == expected_negative and
            positive["execution_events"] == sum(expected_positive.values()) and
            negative["execution_events"] == 0,
            f"{spec['role']} caller coverage drifted")
        observed_events = positive["execution_events"]
        for event in captures[0]["traces"]["execution"]["events"]:
            label = next(
                key for key, value in CONFIGURATION["boot_positive"].items()
                if value["pc"] == event["pc"])
            _require(
                event["frame"] == spec["expected_boot_event_frames"][label],
                f"{spec['role']} boot event frame drifted")
    else:
        _require(
            all(row["execution_events"] == 0 and not row["watch_hits"]
                for row in summaries),
            f"{spec['role']} passive prelude contains instrumentation")
        observed_events = 0
    return {
        "role": spec["role"],
        "receipt_sha256": spec["receipt"]["sha256"],
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "movie_sha256": spec["movie_sha256"],
        "precise": spec["precise"],
        "endpoint_equal": endpoint_equal,
        "jobs": summaries,
        "observed_execution_events": observed_events,
        "replay_frames": sum(
            capture["frame"] -
            receipt["experiment"]["anchor"]["start"]["value"]
            for capture in captures),
        "control_admissible": all(endpoint_equal.values()),
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
        pairs.append(validate_pair(spec, receipt, batch))
    precise = [row for row in pairs if row["precise"]]
    passive = [row for row in pairs if not row["precise"]]
    _require(
        all(row["observed_execution_events"] == 3 for row in precise) and
        all(not row["control_admissible"] for row in precise) and
        any(not row["control_admissible"] for row in passive),
        "rejected method classification drifted")
    return {
        "schema": "abl-phase4-fmv-menu-owner-coverage/1",
        "generated": stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "missing_fact_id": CONFIGURATION["missing_fact_id"],
        "receipts": pairs,
        "observation": {
            "boot_positive_hits_per_movie": 3,
            "nonboot_candidate_hits_per_movie": 0,
            "all_traces_untruncated": True,
            "all_movie_status_reproducible": False,
            "precise_controls_admissible": False,
            "menu_v1_passive_control_admissible":
                passive[0]["control_admissible"],
            "menu_v2_passive_control_admissible":
                passive[1]["control_admissible"],
        },
        "record_counts": {
            "closed_v2_receipts": len(pairs),
            "atomic_jobs": sum(len(row["jobs"]) for row in pairs),
            "replay_frames": sum(row["replay_frames"] for row in pairs),
            "execution_events": sum(
                row["observed_execution_events"] for row in pairs),
            "endpoint_control_failures": sum(
                not row["control_admissible"] for row in pairs),
            "owned_pids_stopped": len(pairs),
        },
        "falsifier": {
            "predicate":
                "every passive and precise same-anchor endpoint is equal",
            "outcome": "falsified",
            "failing_receipts": [
                row["receipt_sha256"] for row in pairs
                if not row["control_admissible"]],
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "source_dependencies": {
            "tools/phase4_fmv_menu_owner_coverage.py":
                common.sha256(Path(__file__)),
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
            raise SystemExit("phase4 menu-owner coverage artifact is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: menu-owner zero-hit observations rejected by endpoint control; "
        "no lifecycle claim promoted", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
