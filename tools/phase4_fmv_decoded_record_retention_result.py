#!/usr/bin/env python3
"""Bank the bounded E15 decoded-record retention control without promotion."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

import phase4_common as common
import phase4_duckstation_batch as live


CONFIG_PATH = (
    common.ROOT / "config/phase4_fmv_decoded_record_retention_result.yaml"
)
OUTPUT = (
    common.ROOT / "analysis/phase4_fmv_decoded_record_retention_result.json"
)
CONFIGURATION = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIGURATION["run_root"]).resolve()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _artifact(spec: dict, label: str) -> tuple[Path, dict]:
    path = (RUN_ROOT / spec["relative_path"]).resolve()
    _require(RUN_ROOT in path.parents, f"{label} escapes retained run root")
    _require(
        path.is_file()
        and path.stat().st_size == spec["bytes"]
        and common.sha256(path) == spec["sha256"],
        f"{label} identity drifted",
    )
    return path, common.load_json(path)


def _plan(spec: dict) -> dict:
    path = common.ROOT / spec["plan"]["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["plan"]["sha256"],
        f"{spec['role']} plan identity drifted",
    )
    plan = common.load_yaml(path)
    _require(
        live.validate_plan(plan, allow_executed=True) == [],
        f"{spec['role']} plan no longer validates",
    )
    return plan


def _memory(capture: dict, label: str) -> dict:
    rows = [
        row
        for row in capture.get("memory") or []
        if row.get("label") == label
    ]
    _require(len(rows) == 1, f"capture lacks unique {label} dump")
    return rows[0]


def _stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def _validate_reference(reference: dict, label: str) -> Path:
    _require(
        set(reference) == {"scope", "path", "sha256"},
        f"{label} reference schema drifted",
    )
    if reference["scope"] == "run":
        path = (RUN_ROOT / reference["path"]).resolve()
        _require(RUN_ROOT in path.parents, f"{label} reference escapes run root")
    elif reference["scope"] == "repo":
        path = (common.ROOT / reference["path"]).resolve()
        _require(
            common.ROOT == path or common.ROOT in path.parents,
            f"{label} reference escapes repository",
        )
    else:
        raise ValueError(f"{label} reference scope drifted")
    _require(
        path.is_file() and common.sha256(path) == reference["sha256"],
        f"{label} reference identity drifted",
    )
    return path


def _validate_command_events(events: dict, batch: dict, raw: dict) -> None:
    rows = events.get("events") or []
    methods = [row.get("method") for row in rows]
    _require(
        events.get("schema") == "abl-phase4-live-command-events/1"
        and events.get("complete") is True
        and events.get("errors") == []
        and methods[:4]
        == [
            "debugger.capabilities",
            "debugger.status",
            "emulator.getMediaInfo",
            "scenario.runBatch",
        ]
        and len(rows) >= 5
        and all(method == "scenario.getBatch" for method in methods[4:]),
        "command stream ordering drifted",
    )
    _require(
        [row.get("sequence") for row in rows] == list(range(len(rows)))
        and len({row.get("server_session_id") for row in rows}) == 1
        and rows[0].get("server_session_id")
        == raw["counters"]["server_session_id"],
        "command stream session/sequence drifted",
    )
    for row in rows:
        expected = hashlib.sha256(
            live.canonical_bytes(row.get("result"))
        ).hexdigest()
        _require(
            row.get("result_sha256") == expected,
            "command result body/hash drifted",
        )
    job_ids = [row["job_id"] for row in raw["results"]]
    _require(
        rows[3]["result"].get("batch_id") == batch["batch_id"]
        and rows[3]["result"].get("job_ids") == job_ids
        and all(
            row["params"].get("batch_id") == batch["batch_id"]
            and row["params"].get("include_results") is True
            for row in rows[4:]
        )
        and rows[-1]["result"].get("status") == "completed"
        and rows[-1]["result"].get("job_ids") == job_ids,
        "atomic batch command/job join drifted",
    )


def validate_run(
    spec: dict,
    receipt: dict,
    batch: dict,
    raw: dict,
    cleanup: dict,
    pagination: dict,
    command_events: dict,
    plan: dict,
) -> dict:
    role = spec["role"]
    media = CONFIGURATION["media"]
    debugger = CONFIGURATION["debugger"]
    _require(
        receipt.get("schema") == "abl-phase4-live-run-receipt/2"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("precise") is spec["precise"]
        and receipt.get("escalation_id") == CONFIGURATION["escalation_id"]
        and receipt.get("missing_fact_id") == CONFIGURATION["missing_fact_id"],
        f"{role} receipt closure identity drifted",
    )
    experiment = receipt["experiment"]
    _require(
        experiment["anchor"]
        == {
            "kind": "movie_start_state",
            "media_sha256": media["bin_sha256"],
            "movie_sha256": media["movie_sha256"],
            "settings_sha256": media["settings_sha256"],
            "start": {"clock": "movie_frame", "value": 0},
            "state_sha256": media["state_sha256"],
        }
        and experiment["execution"]["bound"]
        == {
            "clock": "movie_frame",
            "start": 0,
            "stop": spec["replay_stop"],
            "stop_inclusive": False,
        }
        and experiment["execution"]["capture_window"]
        == {
            "clock": "movie_frame",
            "start": spec["observer_start"],
            "stop": spec["replay_stop"],
            "stop_inclusive": False,
        }
        and experiment["adapter_source_sha256"]
        == debugger["adapter_sha256_at_execution"]
        and experiment["duckstation_executable_sha256"]
        == debugger["binary_sha256"],
        f"{role} typed experiment identity drifted",
    )
    _require(
        batch.get("schema") == "abl-phase4-duckstation-batch-result/1"
        and batch.get("row_ids") == [CONFIGURATION["row_id"]]
        and batch.get("escalation_ids") == [CONFIGURATION["escalation_id"]]
        and batch["result"]["state"] == "completed"
        and batch["expected_media"]["sha256"] == media["cue_sha256"]
        and batch["expected_media"]["tracks"][0]["sha256"]
        == media["bin_sha256"]
        and batch["mounted_media"]["game_serial"] == media["serial"]
        and batch["expected_debugger"]["binary_sha256"]
        == debugger["binary_sha256"]
        and batch["plan_sha256"]
        == live.sha256_bytes(live.plan_bytes(plan)),
        f"{role} batch/media/debugger/plan identity drifted",
    )
    jobs = batch["result"]["jobs"]
    _require(
        len(jobs) == 2
        and [row["id"] for row in jobs]
        == [row["id"] for row in plan["jobs"]]
        and all(row["state"] == "completed" for row in jobs),
        f"{role} atomic jobs are incomplete or reordered",
    )
    for job in jobs:
        result = job["result"]
        stage = result["staged_prelude"]
        run = result["run"]
        _require(
            stage["start_playback_index"] == 0
            and stage["target_frame"]
            == stage["frames_advanced"]
            == spec["stage_stop"]
            and stage["movie"]["playback_index"] == spec["stage_stop"]
            and stage["movie"]["truncated"] is False
            and run["start_playback_index"] == spec["stage_stop"]
            and run["target_frame"] == spec["replay_stop"]
            and run["frames_advanced"]
            == spec["replay_stop"] - spec["stage_stop"]
            and result["capture"]["movie"]["truncated"] is False,
            f"{role} staged playback span drifted",
        )
    expected_replay_frames = 2 * spec["replay_stop"]
    expected_observer_frames = 2 * (
        spec["replay_stop"] - spec["observer_start"]
    )
    _require(
        raw.get("schema") == "abl-phase4-live-raw-results/1"
        and raw.get("complete") is True
        and raw.get("errors") == []
        and raw["counters"]["atomic_jobs"] == 2
        and raw["counters"]["launches"] == 1
        and raw["counters"]["replay_frames"] == expected_replay_frames
        and raw["counters"]["observer_frames"] == expected_observer_frames
        and [row["job_id"] for row in raw["results"]]
        == [row["id"] for row in jobs]
        and all(
            row["replay_start"] == 0
            and row["replay_stop"] == spec["replay_stop"]
            and row["observer_start"] == spec["observer_start"]
            and row["observer_stop"] == spec["replay_stop"]
            and row["status"] == "completed"
            for row in raw["results"]
        ),
        f"{role} raw counters drifted",
    )
    _require(
        cleanup.get("schema") == "abl-phase4-owned-pid-cleanup/1"
        and cleanup.get("complete") is True
        and cleanup.get("errors") == []
        and cleanup.get("owned_pid_stopped") is True
        and str(cleanup.get("config_dir") or "").startswith("/var/tmp/")
        and [row.get("kind") for row in cleanup.get("actions") or []]
        == ["stop_owned_pid", "confirm_pid_stopped"],
        f"{role} owned-PID cleanup drifted",
    )
    _require(
        pagination.get("schema") == "abl-phase4-live-pagination/1"
        and pagination.get("complete") is True
        and pagination.get("errors") == []
        and pagination.get("pages_complete") is True
        and pagination.get("truncated") is False,
        f"{role} pagination drifted",
    )
    _validate_command_events(command_events, batch, raw)
    for key in (
        "raw_results",
        "owned_pid_cleanup",
        "pagination",
        "command_events",
    ):
        config_key = (
            "cleanup" if key == "owned_pid_cleanup" else key
        )
        _require(
            receipt["evidence"][key]["sha256"] == spec[config_key]["sha256"],
            f"{role} receipt evidence join drifted for {key}",
        )
    for key, reference in receipt["evidence"].items():
        _validate_reference(reference, f"{role} receipt {key}")
    if spec["precise"]:
        passive_sha256 = next(
            row["receipt"]["sha256"]
            for row in CONFIGURATION["receipts"]
            if not row["precise"]
        )
        _require(
            receipt["prelude_receipt"]["sha256"] == passive_sha256,
            "precise receipt lost its passive-prelude join",
        )
        _validate_reference(
            receipt["prelude_receipt"], "precise passive-prelude"
        )
    else:
        _require(
            receipt["prelude_receipt"] is None,
            "passive receipt unexpectedly cites a prelude",
        )
    return {
        "role": role,
        "precise": spec["precise"],
        "receipt_sha256": spec["receipt"]["sha256"],
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "raw_results_sha256": spec["raw_results"]["sha256"],
        "cleanup_sha256": spec["cleanup"]["sha256"],
        "pagination_sha256": spec["pagination"]["sha256"],
        "command_events_sha256": spec["command_events"]["sha256"],
        "stage_start": 0,
        "stage_stop": spec["stage_stop"],
        "observer_start": spec["observer_start"],
        "replay_stop": spec["replay_stop"],
        "jobs": jobs,
    }


def _positive_observation(result: dict, max_events: int) -> dict:
    _require(
        result["after_load"]
        == {
            "address": "0x800b6c40",
            "after": "0x1000000e",
            "before": "0x1220000e",
            "code_invalidated": True,
            "kind": "code_write",
            "original_word": "0x1220000e",
            "replacement_word": "0x1000000e",
            "written": 4,
        },
        "positive after-load write/readback drifted",
    )
    access = result["capture"]["traces"]["access"]
    _require(
        access["total"] == 1
        and access["truncated"] is False
        and len(access["events"]) == 1,
        "positive latch access cardinality drifted",
    )
    event = access["events"][0]
    expected = {
        "address": "0x800b9a54",
        "cycle": 150531213774,
        "frame": 265861,
        "instruction": "sb v0, -0x65ac(at)",
        "instruction_pc": "0x800b6c84",
        "instruction_word": "0xa0229a54",
        "new_value": 1,
        "pc": "0x800b6c88",
        "reported_pc": "0x800b6c88",
        "type": "write",
        "value": 0,
        "width": 1,
    }
    _require(
        {key: event[key] for key in expected} == expected,
        "positive instruction-attributed latch write drifted",
    )
    functions = result["capture"]["traces"]["functions"]
    expected_order = [
        ("entry", "0x800b6c24", "0x800b7280", 1),
        ("exit", "0x800b6c24", "0x800b7280", 2),
        ("entry", "0x8007094c", "0x800b749c", 3),
        ("exit", "0x8007094c", "0x800b749c", 4),
        ("entry", "0x800709ac", "0x800b74a4", 5),
        ("exit", "0x800709ac", "0x800b74a4", 6),
    ]
    observed_order = [
        (row["type"], row["function"], row["caller"], row["index"])
        for row in functions
    ]
    _require(
        observed_order == expected_order
        and len(functions) < max_events
        and all(row["frame"] == 265861 for row in functions),
        "positive ordered decode/teardown trace drifted",
    )
    return {
        "predicate_write": result["after_load"],
        "latch_write": expected,
        "ordered_functions": observed_order,
        "retained_function_events": len(functions),
        "configured_max_events": max_events,
        "reached_capacity": False,
        "latch_endpoint": _memory(
            result["capture"], "decode_stop_latch"
        )["hex"],
    }


def _negative_observation(result: dict, max_events: int) -> dict:
    _require(
        result.get("after_load") is None,
        "native negative gained a perturbation",
    )
    access = result["capture"]["traces"]["access"]
    _require(
        access["events"] == []
        and access["total"] == 0
        and access["truncated"] is False,
        "native negative latch access exclusion drifted",
    )
    functions = result["capture"]["traces"]["functions"]
    indexes = [row["index"] for row in functions]
    _require(
        len(functions) == 90
        and indexes == list(range(1, 91))
        and len(functions) < max_events,
        "native function-trace retention signature drifted",
    )
    _require(
        all(
            row["function"] == "0x800b6c24"
            and row["caller"] == "0x800b7280"
            and row["type"] == ("entry" if row["index"] % 2 else "exit")
            for row in functions
        ),
        "native complete helper sequence drifted",
    )
    return {
        "access_events": 0,
        "access_truncated": False,
        "configured_max_events": max_events,
        "retained_events": len(functions),
        "first_retained_index": indexes[0],
        "last_retained_index": indexes[-1],
        "discarded_prefix_events": 0,
        "helper_calls": len(functions) // 2,
        "helper_function": "0x800b6c24",
        "helper_caller": "0x800b7280",
        "teardown_events": 0,
        "reached_capacity": False,
        "latch_endpoint": _memory(
            result["capture"], "decode_stop_latch"
        )["hex"],
        "scene_endpoint": _memory(result["capture"], "scene")["hex"],
    }


def build() -> dict:
    _before_path, before = _artifact(
        CONFIGURATION["before_ledger"], "immutable before ledger"
    )
    planned = [
        row
        for row in before.get("entries") or []
        if row.get("id") == CONFIGURATION["escalation_id"]
    ]
    _require(
        len(planned) == 1 and planned[0].get("state") == "planned",
        "immutable before ledger lacks the unique planned escalation",
    )
    prior_spec = CONFIGURATION["retention_source"]
    prior_path = common.ROOT / prior_spec["path"]
    _require(
        prior_path.is_file()
        and common.sha256(prior_path) == prior_spec["sha256"],
        "retention source artifact identity drifted",
    )
    prior = common.load_json(prior_path)
    _require(
        prior["falsifier"]["outcome"] == "falsified"
        and prior["falsifier"]["evidence"]
        == {
            "configured_max_events": prior_spec["prior_max_events"],
            "retained_events": prior_spec["prior_max_events"],
            "first_retained_index": prior_spec[
                "prior_first_retained_index"
            ],
            "last_retained_index": prior_spec["prior_last_retained_index"],
            "discarded_prefix_events": prior_spec[
                "prior_discarded_prefix_events"
            ],
        }
        and prior["retention_decomposition"][
            "observed_same_anchor_rate"
        ]["total_function_events"]
        == prior_spec["prior_total_events"],
        "retention source saturation contract drifted",
    )

    runs = []
    for spec in CONFIGURATION["receipts"]:
        _receipt_path, receipt = _artifact(
            spec["receipt"], f"{spec['role']} receipt"
        )
        _batch_path, batch = _artifact(
            spec["batch_result"], f"{spec['role']} batch"
        )
        _raw_path, raw = _artifact(
            spec["raw_results"], f"{spec['role']} raw result"
        )
        _cleanup_path, cleanup = _artifact(
            spec["cleanup"], f"{spec['role']} cleanup"
        )
        _pagination_path, pagination = _artifact(
            spec["pagination"], f"{spec['role']} pagination"
        )
        _events_path, events = _artifact(
            spec["command_events"], f"{spec['role']} command events"
        )
        runs.append(
            validate_run(
                spec,
                receipt,
                batch,
                raw,
                cleanup,
                pagination,
                events,
                _plan(spec),
            )
        )

    passive = next(row for row in runs if row["role"] == "passive")
    precise = next(row for row in runs if row["role"] == "precise")
    passive_jobs = passive.pop("jobs")
    precise_jobs = precise.pop("jobs")
    first = passive_jobs[0]["result"]
    second = passive_jobs[1]["result"]
    _require(
        first["staged_prelude"]["status"]
        == second["staged_prelude"]["status"]
        and first["capture"] == second["capture"],
        "passive same-anchor endpoints diverged",
    )
    max_events = next(
        row["function_max_events"]
        for row in CONFIGURATION["receipts"]
        if row["precise"]
    )
    positive = _positive_observation(precise_jobs[0]["result"], max_events)
    negative = _negative_observation(precise_jobs[1]["result"], max_events)
    _require(
        precise_jobs[0]["result"]["capture"]["frame"]
        == precise_jobs[1]["result"]["capture"]["frame"]
        and precise_jobs[0]["result"]["capture"]["cycle"]
        == precise_jobs[1]["result"]["capture"]["cycle"],
        "precise branch frame/cycle endpoints diverged",
    )
    headroom = max_events - negative["retained_events"]
    _require(
        headroom == 38
        and negative["first_retained_index"] == 1
        and negative["last_retained_index"] == 90,
        "successor headroom/contiguity falsifier fired",
    )
    return {
        "schema": "abl-phase4-fmv-decoded-record-retention-result/1",
        "generated": _stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "missing_fact_id": CONFIGURATION["missing_fact_id"],
        "before_ledger_sha256": CONFIGURATION["before_ledger"]["sha256"],
        "retention_source": {
            "artifact": prior_spec["path"],
            "sha256": prior_spec["sha256"],
            "prior_max_events": prior_spec["prior_max_events"],
            "prior_total_events": prior_spec["prior_total_events"],
            "prior_first_retained_index": prior_spec[
                "prior_first_retained_index"
            ],
            "prior_discarded_prefix_events": prior_spec[
                "prior_discarded_prefix_events"
            ],
        },
        "receipts": runs,
        "observation": {
            "passive_repeat_equal": True,
            "passive_movie_reproducible_flag": False,
            "precise_endpoint_frame": precise_jobs[0]["result"][
                "capture"
            ]["frame"],
            "precise_endpoint_cycle": precise_jobs[0]["result"][
                "capture"
            ]["cycle"],
            "positive": positive,
            "native_negative": negative,
        },
        "falsifier": {
            "predicate": (
                "reject unless the native branch retains contiguous function "
                "indexes 1..90, returns no more than 90 events, stays below "
                "the 128-event limit and preserves the latch-write exclusion"
            ),
            "outcome": "survived",
            "evidence": {
                "configured_max_events": max_events,
                "retained_events": negative["retained_events"],
                "first_retained_index": negative["first_retained_index"],
                "last_retained_index": negative["last_retained_index"],
                "discarded_prefix_events": 0,
                "headroom_events": headroom,
                "truncated": False,
                "native_latch_writes": 0,
            },
        },
        "record_counts": {
            "emulator_launches": 2,
            "completed_atomic_jobs": 4,
            "replay_frames": 3500,
            "observer_frames": 902,
            "exact_after_load_writes": 1,
            "positive_latch_writes": 1,
            "native_latch_writes": 0,
            "positive_retained_function_events": 6,
            "native_retained_function_events": 90,
            "native_discarded_function_events": 0,
            "owned_pids_stopped": 2,
            "investigator_live_receipts": 2,
            "promotion_admissible_live_receipts": 0,
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "source_dependencies": {
            str(CONFIG_PATH.relative_to(common.ROOT)): common.sha256(
                CONFIG_PATH
            ),
            "analysis/phase4_fmv_decoded_record_control_result.json":
                common.sha256(prior_path),
            "tools/phase4_fmv_decoded_record_retention_result.py":
                common.sha256(Path(__file__)),
            "tools/phase4_duckstation_batch.py": common.sha256(
                common.ROOT / "tools/phase4_duckstation_batch.py"
            ),
            "config/phase4_fmv_decoded_record_retention_passive_batch.yaml":
                common.sha256(
                    common.ROOT
                    / "config/phase4_fmv_decoded_record_retention_passive_batch.yaml"
                ),
            "config/phase4_fmv_decoded_record_retention_control_batch.yaml":
                common.sha256(
                    common.ROOT
                    / "config/phase4_fmv_decoded_record_retention_control_batch.yaml"
                ),
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
            raise SystemExit(
                "phase4 decoded-record retention result is stale"
            )
    else:
        print(rendered, end="")
    print(
        "PASS: native function indexes 1..90 retained below 128; "
        "decoded-record observer-retention fact closed; no dimension promoted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
