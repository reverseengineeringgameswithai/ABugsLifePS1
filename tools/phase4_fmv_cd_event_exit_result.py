#!/usr/bin/env python3
"""Bank the bounded E15 CD-event player-interface control without promotion."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

import phase4_common as common
import phase4_duckstation_batch as live


CONFIG_PATH = common.ROOT / "config/phase4_fmv_cd_event_exit_result.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_cd_event_exit_result.json"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIGURATION["run_root"]).resolve()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _artifact(
    spec: dict, label: str, *, run_root: Path | None = None
) -> tuple[Path, dict]:
    root = RUN_ROOT if run_root is None else run_root
    path = (root / spec["relative_path"]).resolve()
    _require(root in path.parents, f"{label} escapes retained run root")
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


def _stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def _validate_reference(
    reference: dict, label: str, *, run_root: Path | None = None
) -> Path:
    root = RUN_ROOT if run_root is None else run_root
    _require(
        set(reference) == {"scope", "path", "sha256"},
        f"{label} reference schema drifted",
    )
    if reference["scope"] == "run":
        path = (root / reference["path"]).resolve()
        _require(root in path.parents, f"{label} reference escapes run root")
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


def _validate_preservation(
    receipt: dict, role: str, *, run_root: Path | None = None
) -> None:
    paths = {
        key: _validate_reference(
            reference, f"{role} receipt {key}", run_root=run_root
        )
        for key, reference in receipt["evidence"].items()
    }
    preservation = common.load_json(paths["external_preservation_manifest"])
    _require(
        preservation.get("schema")
        == "abl-phase4-method-external-preservation/1"
        and preservation.get("complete") is True
        and preservation.get("errors") == [],
        f"{role} preservation manifest is not closed",
    )
    entries = {
        row["sha256"]: row for row in preservation.get("entries") or []
    }
    _require(
        len(entries) == len(preservation.get("entries") or []),
        f"{role} preservation manifest has duplicate identities",
    )
    for key, path in paths.items():
        if key == "external_preservation_manifest":
            continue
        reference = receipt["evidence"][key]
        row = entries.get(reference["sha256"])
        _require(
            row is not None
            and row.get("size") == path.stat().st_size
            and row.get("preservation_required") is True,
            f"{role} preservation manifest omits {key}",
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
    *,
    configuration: dict | None = None,
    run_root: Path | None = None,
) -> dict:
    config = CONFIGURATION if configuration is None else configuration
    role = spec["role"]
    media = config["media"]
    debugger = config["debugger"]
    _require(
        receipt.get("schema") == "abl-phase4-live-run-receipt/2"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("precise") is spec["precise"]
        and receipt.get("escalation_id") == config["escalation_id"]
        and receipt.get("missing_fact_id") == config["missing_fact_id"],
        f"{role} receipt closure identity drifted",
    )
    experiment = receipt["experiment"]
    expected_anchor = {
        "kind": "movie_start_state",
        "media_sha256": media["bin_sha256"],
        "movie_sha256": media["movie_sha256"],
        "settings_sha256": media["settings_sha256"],
        "start": {"clock": "movie_frame", "value": 0},
        "state_sha256": media["state_sha256"],
    }
    _require(
        experiment["anchor"] == expected_anchor
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
        and batch.get("row_ids") == [config["row_id"]]
        and batch.get("escalation_ids") == [config["escalation_id"]]
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
            result["media_verified"] is True
            and stage["start_playback_index"] == 0
            and stage["target_frame"]
            == stage["frames_advanced"]
            == spec["stage_stop"]
            and stage["movie"]["playback_index"] == spec["stage_stop"]
            and stage["movie"]["truncated"] is False
            and run["start_playback_index"] == spec["stage_stop"]
            and run["target_frame"] == spec["replay_stop"]
            and run["frames_advanced"]
            == spec["replay_stop"] - spec["stage_stop"]
            and result["capture"]["movie"]["playback_index"]
            == spec["replay_stop"]
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
            and row["instruction_start"] == row["instruction_stop"] == 0
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
        config_key = "cleanup" if key == "owned_pid_cleanup" else key
        _require(
            receipt["evidence"][key]["sha256"] == spec[config_key]["sha256"],
            f"{role} receipt evidence join drifted for {key}",
        )
    _validate_preservation(receipt, role, run_root=run_root)
    media_path = _validate_reference(
        receipt["evidence"]["media_capabilities"],
        f"{role} media/capabilities",
        run_root=run_root,
    )
    media_doc = common.load_json(media_path)
    _require(
        media_doc.get("schema") == "abl-phase4-live-media-capabilities/1"
        and media_doc.get("complete") is True
        and media_doc.get("errors") == []
        and media_doc.get("mounted_serial") == media["serial"]
        and media_doc.get("pristine_media_sha256") == media["bin_sha256"]
        and media_doc.get("duckstation_executable_sha256")
        == debugger["binary_sha256"]
        and media_doc.get("duckstation_executable_sha256")
        == experiment["duckstation_executable_sha256"]
        and media_doc.get("duckstation_source_sha256")
        == experiment["duckstation_source_sha256"]
        and media_doc.get("api_surface_sha256")
        == experiment["api_surface_sha256"],
        f"{role} normalized media/capability identity drifted",
    )
    if spec["precise"]:
        passive_sha256 = next(
            row["receipt"]["sha256"]
            for row in config["receipts"]
            if not row["precise"]
        )
        _require(
            receipt["prelude_receipt"]["sha256"] == passive_sha256,
            "precise receipt lost its passive-prelude join",
        )
        _validate_reference(
            receipt["prelude_receipt"],
            "precise passive-prelude",
            run_root=run_root,
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


def _memory(capture: dict, label: str) -> dict:
    rows = [
        row for row in capture.get("memory") or [] if row.get("label") == label
    ]
    _require(len(rows) == 1, f"capture lacks unique {label} dump")
    return rows[0]


def _positive_observation(result: dict, max_events: int) -> dict[str, Any]:
    _require(
        result["after_load"]
        == {
            "address": "0x800b7420",
            "after": "0x24020001",
            "before": "0x8c422484",
            "code_invalidated": True,
            "kind": "code_write",
            "original_word": "0x8c422484",
            "replacement_word": "0x24020001",
            "written": 4,
        },
        "positive one-word write/readback drifted",
    )
    functions = result["capture"]["traces"]["functions"]
    expected = [
        ("entry", "0x8006d8e8", "0x800b746c", 1),
        ("exit", "0x8006d8e8", "0x800b746c", 2),
        ("entry", "0x8007094c", "0x800b749c", 3),
        ("exit", "0x8007094c", "0x800b749c", 4),
        ("entry", "0x800709ac", "0x800b74a4", 5),
        ("exit", "0x800709ac", "0x800b74a4", 6),
    ]
    observed = [
        (row["type"], row["function"], row["caller"], row["index"])
        for row in functions[:6]
    ]
    indexes = [row["index"] for row in functions]
    _require(
        observed == expected
        and indexes == list(range(1, 13))
        and len(functions) == 12 < max_events
        and functions[0]["arguments"][0] == "0x0000000b"
        and all(
            functions[index]["cycle"] < functions[index + 1]["cycle"]
            for index in range(5)
        ),
        "positive ordered CD-event exit sequence drifted",
    )
    _require(
        result["capture"]["traces"]["access"]["truncated"] is False
        and result["capture"]["traces"]["execution"]["truncated"] is False,
        "positive trace reported truncation",
    )
    return {
        "one_word_write": result["after_load"],
        "ordered_exit_functions": observed,
        "cd_control_command": 11,
        "target_exit_events": 6,
        "total_function_events": len(functions),
        "configured_max_events": max_events,
        "headroom_events": max_events - len(functions),
        "first_event_cycle": functions[0]["cycle"],
        "last_target_event_cycle": functions[5]["cycle"],
        "exit_frame": functions[0]["frame"],
        "endpoint_pc": result["status"]["pc"],
        "scene_endpoint": _memory(result["capture"], "scene")["hex"],
        "fmv_running_latch_endpoint": _memory(
            result["capture"], "fmv_running_latch"
        )["hex"],
    }


def _negative_observation(result: dict) -> dict[str, Any]:
    _require(
        result.get("after_load") is None,
        "native negative gained a perturbation",
    )
    functions = result["capture"]["traces"]["functions"]
    _require(
        functions == []
        and result["capture"]["traces"]["access"]["truncated"] is False
        and result["capture"]["traces"]["execution"]["truncated"] is False,
        "native negative exit-sequence exclusion drifted",
    )
    return {
        "perturbations": 0,
        "retained_function_events": 0,
        "target_exit_events": 0,
        "endpoint_pc": result["status"]["pc"],
        "scene_endpoint": _memory(result["capture"], "scene")["hex"],
        "fmv_running_latch_endpoint": _memory(
            result["capture"], "fmv_running_latch"
        )["hex"],
    }


def _static_join() -> dict[str, Any]:
    spec = CONFIGURATION["static_source"]
    path = common.ROOT / spec["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["sha256"],
        "static lifecycle source identity drifted",
    )
    document = common.load_json(path)
    route = document["transient_player_continuations"][
        "native_cd_event_route"
    ]
    _require(
        route["registration"]["callback"] == "0x80045D5C"
        and route["registration"]["event_class"] == "0xF0000003"
        and route["registration"]["event_spec"] == "0x00008000"
        and route["callback"]["store"]
        == {
            "address": "0x80082484",
            "gp_offset": "0x000006EC",
            "pc": "0x80045D60",
            "type": "u32",
            "value": 1,
        }
        and route["player_consumer"]["load"]["pc"] == "0x800B7420"
        and route["player_consumer"]["exit_branch"]["pc"] == "0x800B7428"
        and route["player_consumer"]["exit_branch"]["target"] == "0x800B7464"
        and route["player_consumer"]["common_teardown"]["cd_control_call"]
        == "0x800B746C"
        and route["player_consumer"]["common_teardown"]["command"] == "0x0B"
        and route["unclassified_static_edges"] == 0
        and route["runtime_event_delivery_claimed"] is False,
        "static CD-event route contract drifted",
    )
    return {
        "artifact": spec["path"],
        "sha256": spec["sha256"],
        "registration_callback": route["registration"]["callback"],
        "event_class": route["registration"]["event_class"],
        "event_spec": route["registration"]["event_spec"],
        "field_address": route["callback"]["store"]["address"],
        "field_value": route["callback"]["store"]["value"],
        "consumer_pc": route["player_consumer"]["load"]["pc"],
        "branch_pc": route["player_consumer"]["exit_branch"]["pc"],
        "exit_target": route["player_consumer"]["exit_branch"]["target"],
        "cd_control_call": route["player_consumer"]["common_teardown"][
            "cd_control_call"
        ],
        "cd_control_command": route["player_consumer"]["common_teardown"][
            "command"
        ],
        "runtime_event_delivery_claimed": False,
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
        len(planned) == 1
        and planned[0].get("state") == "planned"
        and planned[0].get("missing_fact_id")
        == CONFIGURATION["missing_fact_id"],
        "immutable before ledger lacks the unique planned escalation",
    )
    static_join = _static_join()
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
        and first["run"]["status"] == second["run"]["status"]
        and first["capture"] == second["capture"],
        "passive same-anchor endpoints diverged",
    )
    max_events = next(
        row["function_max_events"]
        for row in CONFIGURATION["receipts"]
        if row["precise"]
    )
    positive_result = precise_jobs[0]["result"]
    negative_result = precise_jobs[1]["result"]
    positive = _positive_observation(positive_result, max_events)
    negative = _negative_observation(negative_result)
    _require(
        positive_result["staged_prelude"]["status"]
        == negative_result["staged_prelude"]["status"]
        and positive_result["capture"]["frame"]
        == negative_result["capture"]["frame"]
        == 4565
        and positive_result["capture"]["cycle"]
        == negative_result["capture"]["cycle"]
        == 2584138962,
        "precise same-anchor frame/cycle basis drifted",
    )
    return {
        "schema": "abl-phase4-fmv-cd-event-exit-result/1",
        "generated": _stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "missing_fact_id": CONFIGURATION["missing_fact_id"],
        "before_ledger_sha256": CONFIGURATION["before_ledger"]["sha256"],
        "static_join": static_join,
        "receipts": runs,
        "observation": {
            "passive_repeat_equal": True,
            "passive_movie_reproducible_flag": first["capture"]["movie"][
                "reproducible"
            ],
            "precise_endpoint_frame": positive_result["capture"]["frame"],
            "precise_endpoint_cycle": positive_result["capture"]["cycle"],
            "positive": positive,
            "native_negative": negative,
        },
        "falsifier": {
            "predicate": (
                "reject if the one-word positive misses or reorders the "
                "CdControl(0x0B), StClearRing and callback-teardown sequence, "
                "if the native branch records that sequence, or if either "
                "trace saturates, truncates, diverges from its typed bound or "
                "fails owned-PID cleanup"
            ),
            "outcome": "survived",
            "evidence": {
                "positive_target_exit_events": 6,
                "negative_target_exit_events": 0,
                "positive_total_function_events": 12,
                "configured_max_events": max_events,
                "headroom_events": max_events - 12,
                "passive_repeat_equal": True,
                "truncated": False,
                "owned_pids_stopped": 2,
            },
        },
        "record_counts": {
            "emulator_launches": 2,
            "completed_atomic_jobs": 4,
            "replay_frames": 1340,
            "observer_frames": 342,
            "exact_after_load_writes": 1,
            "positive_target_exit_events": 6,
            "positive_total_function_events": 12,
            "negative_target_exit_events": 0,
            "owned_pids_stopped": 2,
            "investigator_live_receipts": 2,
            "promotion_admissible_live_receipts": 0,
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "source_dependencies": {
            str(CONFIG_PATH.relative_to(common.ROOT)): common.sha256(CONFIG_PATH),
            CONFIGURATION["static_source"]["path"]: common.sha256(
                common.ROOT / CONFIGURATION["static_source"]["path"]
            ),
            "tools/phase4_fmv_cd_event_exit_result.py": common.sha256(
                Path(__file__)
            ),
            "tools/phase4_duckstation_batch.py": common.sha256(
                common.ROOT / "tools/phase4_duckstation_batch.py"
            ),
            "config/phase4_fmv_cd_event_exit_passive_batch.yaml": common.sha256(
                common.ROOT
                / "config/phase4_fmv_cd_event_exit_passive_batch.yaml"
            ),
            "config/phase4_fmv_cd_event_exit_control_batch.yaml": common.sha256(
                common.ROOT
                / "config/phase4_fmv_cd_event_exit_control_batch.yaml"
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
            raise SystemExit("phase4 FMV CD-event exit result is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: one-word CD-event player interface reaches ordered teardown; "
        "native control excludes it; no dimension promoted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
