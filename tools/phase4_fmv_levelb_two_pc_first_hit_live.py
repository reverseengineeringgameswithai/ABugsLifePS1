#!/usr/bin/env python3
"""Run and retain the predeclared E15 managed two-PC first-hit experiment.

The atomic scenario establishes an uninstrumented paused cold-boot anchor.
The tracked two-PC adapter then owns both execute breakpoints and emits every
normalized direct command/result body needed by the strict v2 live receipt.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

import yaml

import phase4_common as common
import phase4_duckstation_batch as batch
import phase4_duckstation_two_pc_first_hit as first_hit


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SCHEMA = "abl-phase4-fmv-levelb-two-pc-first-hit-runtime/1"
RESULT_SCHEMA = "abl-phase4-fmv-levelb-two-pc-first-hit-live-result/1"
PRISTINE_TRACK_SHA256 = (
    "2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566"
)
DIRECT_ADAPTER = ROOT / "tools/phase4_duckstation_two_pc_first_hit.py"
RPC_MANIFEST = ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
TERMINAL_BATCH_STATES = {"completed", "failed", "cancelled"}


def _exact_keys(value: object, expected: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{where} keys differ from the closed schema")
    return value


def first_hit_plan(runtime: dict[str, Any]) -> dict[str, Any]:
    plan_doc = yaml.safe_load(
        (ROOT / runtime["first_hit_plan"]["path"]).read_text())
    return plan_doc["first_hit_plan"]


def load_runtime(path: Path) -> dict[str, Any]:
    runtime = yaml.safe_load(path.read_text())
    _exact_keys(
        runtime,
        {
            "schema", "campaign_id", "row_ids", "escalation_id",
            "missing_fact_id", "expected_media", "expected_debugger",
            "movie", "atomic_anchor", "first_hit_plan", "execution",
            "domain", "observer_plan", "perturbation_plan",
            "settings_snapshot", "assertion_plan", "variant",
        },
        "runtime",
    )
    if runtime["schema"] != RUNTIME_SCHEMA or \
            runtime["campaign_id"] != "fmv_playback" or \
            runtime["row_ids"] != ["E15_fmv"]:
        raise ValueError("runtime schema/campaign/row selection drifted")
    if runtime["escalation_id"] != \
            "P4-R10-ITER1-E15-LEVELB-TWO-PC-FIRST-HIT" or \
            runtime["missing_fact_id"] != \
            "E15/completed-level-b-natural-scene-setup-first-hit":
        raise ValueError("runtime escalation identity drifted")
    if runtime["domain"] != "interface":
        raise ValueError("runtime domain must be interface")

    media = _exact_keys(
        runtime["expected_media"],
        {"path", "serial", "title", "sha256", "tracks"},
        "expected_media",
    )
    if media["serial"] != "SCUS-94288" or \
            not isinstance(media["tracks"], list) or \
            len(media["tracks"]) != 1 or \
            media["tracks"][0].get("sha256") != PRISTINE_TRACK_SHA256:
        raise ValueError("runtime media is not pinned pristine authority")
    movie = _exact_keys(runtime["movie"], {"path", "sha256"}, "movie")
    movie_path = ROOT / movie["path"]
    if not movie_path.is_file() or common.sha256(movie_path) != movie["sha256"]:
        raise ValueError("centrally provisioned first-hit movie identity drifted")

    anchor = _exact_keys(
        runtime["atomic_anchor"],
        {
            "job_id", "target_frame", "max_frames", "run_frames",
            "capture_trigger", "trace_limit", "memory_dumps",
        },
        "atomic_anchor",
    )
    if anchor["target_frame"] != 15792 or anchor["max_frames"] != 15792 or \
            anchor["run_frames"] != 15791 or anchor["memory_dumps"] != []:
        raise ValueError("atomic anchor must stop paused at emulator frame 15792")
    expected_execution = {
        "bound": {
            "clock": "emulator_frame", "start": 0, "stop": 15856,
            "stop_inclusive": False,
        },
        "capture_window": {
            "clock": "emulator_frame", "start": 15792, "stop": 15856,
            "stop_inclusive": False,
        },
    }
    if runtime["execution"] != expected_execution:
        raise ValueError("runtime execution is not the exact 64-frame window")

    plan_ref = _exact_keys(
        runtime["first_hit_plan"], {"path", "sha256"}, "first_hit_plan")
    plan_path = ROOT / plan_ref["path"]
    if not plan_path.is_file() or common.sha256(plan_path) != plan_ref["sha256"]:
        raise ValueError("two-PC first-hit plan identity drifted")
    plan = first_hit_plan(runtime)
    errors = first_hit.validate_plan(plan)
    if errors:
        raise ValueError(f"two-PC first-hit plan is invalid: {'; '.join(errors)}")
    if plan["execution_limit"]["max_frame_delta"] != 64:
        raise ValueError("two-PC first-hit plan lost its exact 64-frame ceiling")
    expected_observer = {
        "schema": "abl-phase4-observer-plan/2",
        "operations": [
            {
                "sequence": index,
                "method": "debugger.addBreakpoint",
                "args": stop["params"],
            }
            for index, stop in enumerate(plan["breakpoint_sequence"])
        ],
        "result_limits": first_hit.observer_result_limits(plan),
        "direct_command_plan": plan,
    }
    if runtime["observer_plan"] != expected_observer:
        raise ValueError(
            "runtime observer plan differs from the guarded two-PC plan")
    if runtime["perturbation_plan"] != {
        "schema": "abl-phase4-perturbation-plan/1",
        "kind": "none",
        "operations": [],
    }:
        raise ValueError("runtime perturbation must be none")
    if runtime["variant"] != {
        "name": "native",
        "receipt_id": "e15-levelb-two-pc-first-hit-native",
        "control_role": "positive",
    }:
        raise ValueError("runtime variant differs from the predeclared receipt")
    return runtime


def _verify_authority(
    runtime: dict[str, Any],
    capabilities: dict[str, Any],
    status: dict[str, Any],
    media: dict[str, Any],
) -> dict[str, Any]:
    expected_debugger = runtime["expected_debugger"]
    observed_debugger = {
        "api_version": (capabilities.get("api") or {}).get("version"),
        "schema_version": (capabilities.get("api") or {}).get("schema_version"),
        "binary_sha256": (capabilities.get("binary") or {}).get("sha256"),
        "source_revision": (capabilities.get("source") or {}).get("revision"),
        "source_dirty": (capabilities.get("source") or {}).get("dirty"),
        "dirty_state_hash": (capabilities.get("source") or {}).get(
            "dirty_state_hash"),
    }
    if observed_debugger != expected_debugger:
        raise RuntimeError(
            f"running DuckStation identity differs from runtime: "
            f"{observed_debugger}")
    methods = set((capabilities.get("methods") or {}).keys())
    required = set(first_hit.REQUIRED_METHODS) | batch.REQUIRED_METHODS | {
        "scenario.runBatch", "scenario.getBatch",
    }
    missing = sorted(required - methods)
    if missing:
        raise RuntimeError(f"running DuckStation lacks methods: {missing}")

    expected_media = runtime["expected_media"]
    media_path = Path(str(media.get("path") or ""))
    serial = media.get("serial") or media.get("game_serial")
    if status.get("game_serial") != expected_media["serial"] or \
            serial != expected_media["serial"] or \
            not media_path.is_file() or \
            media_path.resolve() != Path(expected_media["path"]).resolve() or \
            common.sha256(media_path) != expected_media["sha256"]:
        raise RuntimeError("mounted media identity differs from runtime")
    for track in expected_media["tracks"]:
        track_path = Path(track["path"])
        if not track_path.is_file() or common.sha256(track_path) != track["sha256"]:
            raise RuntimeError(f"pristine companion track drifted: {track_path}")

    manifest = common.load_json(RPC_MANIFEST)
    normalized = batch._normalized_capabilities(capabilities, manifest)
    identity = first_hit_plan(runtime)["identity_join"]
    source = manifest["source"]
    binary = manifest["binaries"]["build-release/bin/duckstation-qt"]
    expected_identity = {
        "rpc_manifest_sha256": common.sha256(RPC_MANIFEST),
        "source_revision": source["revision"],
        "source_dirty_state_hash": source["dirty_state_hash"],
        "dispatcher_sha256": source["dispatcher_sha256"],
        "binary_sha256": binary["sha256"],
        "media_serial": expected_media["serial"],
        "media_sha256": PRISTINE_TRACK_SHA256,
    }
    if identity != expected_identity or \
            normalized["executable_sha256"] != identity["binary_sha256"]:
        raise RuntimeError(
            "two-PC first-hit identity differs from current authority")
    return normalized


def _batch_request(runtime: dict[str, Any]) -> dict[str, Any]:
    expected = runtime["expected_media"]
    anchor = runtime["atomic_anchor"]
    return {
        "continue_on_error": False,
        "jobs": [{
            "id": anchor["job_id"],
            "recipe": "bootAndRun",
            "media_path": expected["path"],
            "fast_boot": True,
            "force": True,
            "expected_media": {
                "path": expected["path"],
                "serial": expected["serial"],
                "title": expected["title"],
                "sha256": expected["sha256"],
                "tracks": expected["tracks"],
            },
            "movie": {
                "path": str((ROOT / runtime["movie"]["path"]).resolve()),
            },
            "instrumentation": [],
            "run": {"frames": anchor["run_frames"]},
            "capture": {
                "trigger": anchor["capture_trigger"],
                "include_registers": True,
                "trace_limit": anchor["trace_limit"],
                "memory_dumps": anchor["memory_dumps"],
            },
        }],
    }


def run_live(
    runtime: dict[str, Any],
    port: int,
    token: str,
    config_dir: Path,
    owned_pid: int,
    poll_seconds: float,
) -> dict[str, Any]:
    module = batch._load_client_module()
    client = module.DebuggerClient("127.0.0.1", port, "ws")
    client.authenticate(token)
    client.transport.sock.settimeout(300)
    capabilities = client.call("debugger.capabilities", {})
    status = client.call("debugger.status", {})
    media = client.call("emulator.getMediaInfo", {})
    normalized = _verify_authority(runtime, capabilities, status, media)

    request = _batch_request(runtime)
    submitted = client.call("scenario.runBatch", request)
    batch_id = submitted.get("batch_id")
    if not batch_id:
        raise RuntimeError(f"scenario.runBatch returned no batch ID: {submitted}")
    polls: list[dict[str, Any]] = []
    while True:
        polled = client.call(
            "scenario.getBatch",
            {"batch_id": batch_id, "include_results": True},
        )
        polls.append(polled)
        state = str(polled.get("state") or polled.get("status") or "")
        if state in TERMINAL_BATCH_STATES:
            break
        time.sleep(max(0.1, min(poll_seconds, 5.0)))
    if state != "completed":
        raise RuntimeError(f"atomic anchor batch ended {state}: {polled}")
    jobs = polled.get("jobs") or []
    if len(jobs) != 1 or \
            jobs[0].get("id") != runtime["atomic_anchor"]["job_id"] or \
            jobs[0].get("state") != "completed":
        raise RuntimeError("atomic anchor batch result is incomplete")
    result = jobs[0].get("result") or {}
    advanced = (result.get("run") or {}).get("frames_advanced")
    frame = (result.get("status") or {}).get("frame")
    if advanced != runtime["atomic_anchor"]["run_frames"] or \
            frame != runtime["atomic_anchor"]["target_frame"]:
        raise RuntimeError(
            f"atomic anchor did not stop at frame 15792: "
            f"advanced={advanced}, frame={frame}")

    session_id = batch.sha256_bytes(batch.canonical_bytes({
        "config_dir": str(config_dir.resolve()),
        "owned_pid": owned_pid,
        "port": port,
        "batch_id": batch_id,
        "executable_sha256": normalized["executable_sha256"],
    }))
    retained_events: list[dict[str, Any]] = []

    def rpc_call(
        observed_session: str,
        method: str,
        params: dict[str, Any],
        socket_timeout_ms: int,
    ) -> dict[str, Any]:
        if observed_session != session_id:
            raise RuntimeError("direct command escaped the owned server session")
        client.transport.sock.settimeout(socket_timeout_ms / 1000.0)
        result_body = client.call(method, params)
        retained_events.append({
            "sequence": len(retained_events),
            "server_session_id": session_id,
            "method": method,
            "params": params,
            "socket_timeout_ms": socket_timeout_ms,
            "result_sha256": batch.sha256_bytes(
                batch.canonical_bytes(result_body)),
            "result": result_body,
        })
        return result_body

    plan = first_hit_plan(runtime)
    try:
        direct = first_hit.execute_first_hit(
            rpc_call, plan, session_id, plan["identity_join"])
        direct["outcome"] = "survived"
    except first_hit.FirstHitFalsifiedError as exc:
        status_events = [
            event["result"] for event in retained_events
            if event["method"] == "debugger.status"
        ]
        if not status_events or \
                retained_events[-1]["method"] != "debugger.listBreakpoints" or \
                retained_events[-1]["result"].get("breakpoints") != []:
            raise RuntimeError(
                "two-PC falsifier lacked retained status or complete "
                "breakpoint cleanup") from exc
        direct = {
            "schema": first_hit.RESULT_SCHEMA,
            "complete": True,
            "errors": [],
            "outcome": "falsified",
            "falsifier": {
                "code": "TWO_PC_FIRST_HIT_TYPED_PREDICATE_FALSE",
                "reason": str(exc),
            },
            "server_session_id": session_id,
            "verified_identity": plan["identity_join"],
            "plan_sha256": batch.sha256_bytes(batch.canonical_bytes(plan)),
            "execution": {
                "clock": "emulator_frame",
                "anchor_frame": status_events[0].get("frame"),
                "frame_ceiling": (
                    status_events[0].get("frame")
                    + plan["execution_limit"]["max_frame_delta"]
                ),
                "failure_frame": status_events[-1].get("frame"),
            },
            "cleanup": {"remaining_breakpoints": 0},
            "command_events": {
                "complete": True,
                "errors": [],
                "events": retained_events,
            },
        }
    return {
        "schema": RESULT_SCHEMA,
        "generated": datetime.now(timezone.utc).isoformat(),
        "complete": True,
        "errors": [],
        "port": port,
        "owned_pid": owned_pid,
        "config_dir": str(config_dir.resolve()),
        "client_sha256": common.sha256(Path(module.__file__)),
        "runner_sha256": common.sha256(Path(__file__)),
        "runtime_sha256": None,
        "identity_results": {
            "debugger.capabilities": capabilities,
            "debugger.status": status,
            "emulator.getMediaInfo": media,
        },
        "normalized_identity": normalized,
        "batch_request": request,
        "batch_id": batch_id,
        "batch_submission": submitted,
        "batch_polls": polls,
        "result": polled,
        "server_session_id": session_id,
        "direct_result": direct,
    }


def _artifact_ref(path: Path, run_root: Path) -> dict[str, Any]:
    return {
        "scope": "run",
        "path": path.resolve().relative_to(run_root.resolve()).as_posix(),
        "sha256": common.sha256(path),
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def emit_receipt(
    runtime: dict[str, Any],
    runtime_path: Path,
    document: dict[str, Any],
    receipt_dir: Path,
    run_root: Path,
    cleanup: dict[str, Any],
    cleanup_raw: dict[str, Any],
    prelude_receipt: Path,
) -> Path:
    receipt_path = receipt_dir / "receipt.json"
    if receipt_path.exists():
        raise FileExistsError(f"refusing to overwrite live receipt: {receipt_path}")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        name: receipt_dir / filename
        for name, filename in {
            "settings": "settings-snapshot.json",
            "observer": "observer-plan.json",
            "perturbation": "perturbation-plan.json",
            "control": "control-plan.json",
            "raw": "raw-results.json",
            "pagination": "pagination.json",
            "media": "media-capabilities.json",
            "events": "command-events.json",
            "cleanup": "owned-pid-cleanup.json",
            "cleanup_raw": "owned-pid-cleanup-raw.json",
            "batch": "batch-result.json",
            "direct": "two-pc-first-hit-result.json",
            "preservation": "preservation.json",
        }.items()
    }
    document["runtime_sha256"] = common.sha256(runtime_path)
    for key, value in {
        "batch": document,
        "direct": document["direct_result"],
        "settings": runtime["settings_snapshot"],
        "observer": runtime["observer_plan"],
        "perturbation": runtime["perturbation_plan"],
        "cleanup": cleanup,
        "cleanup_raw": cleanup_raw,
    }.items():
        _write_json(paths[key], value)

    normalized = document["normalized_identity"]
    experiment_without_control = {
        "anchor": {
            "kind": "cold_boot_movie",
            "media_sha256": PRISTINE_TRACK_SHA256,
            "settings_sha256": common.sha256(paths["settings"]),
            "movie_sha256": runtime["movie"]["sha256"],
            "state_sha256": None,
            "start": {"clock": "emulator_frame", "value": 0},
        },
        "execution": runtime["execution"],
        "domain": runtime["domain"],
        "observer_plan_sha256": common.sha256(paths["observer"]),
        "perturbation_plan_sha256": common.sha256(paths["perturbation"]),
        "duckstation_source_sha256": normalized["source_sha256"],
        "duckstation_executable_sha256": normalized["executable_sha256"],
        "api_surface_sha256": normalized["api_surface_sha256"],
        "adapter_source_sha256": common.sha256(DIRECT_ADAPTER),
    }
    control = {
        "schema": "abl-phase4-control-plan/1",
        "role": runtime["variant"]["control_role"],
        "paired_run_basis_sha256": batch.sha256_bytes(
            batch.canonical_bytes(experiment_without_control)),
        "anchor_sha256": batch.sha256_bytes(
            batch.canonical_bytes(experiment_without_control["anchor"])),
        "only_difference_plan_sha256": common.sha256(paths["perturbation"]),
        "assertion_plan_sha256": batch.sha256_bytes(
            batch.canonical_bytes(runtime["assertion_plan"])),
    }
    _write_json(paths["control"], control)
    experiment = {
        "executor_role": "investigator",
        **experiment_without_control,
        "control_plan_sha256": common.sha256(paths["control"]),
    }
    atomic_plan_sha256 = batch.sha256_bytes(batch.canonical_bytes({
        "anchor": experiment["anchor"],
        "execution": experiment["execution"],
        "observer_plan_sha256": experiment["observer_plan_sha256"],
        "perturbation_plan_sha256": experiment["perturbation_plan_sha256"],
        "control_plan_sha256": experiment["control_plan_sha256"],
    }))

    job = document["result"]["jobs"][0]
    advanced = job["result"]["run"]["frames_advanced"]
    frame = job["result"]["status"]["frame"]
    session_id = document["server_session_id"]
    _write_json(paths["raw"], {
        "schema": "abl-phase4-live-raw-results/1",
        "complete": True,
        "errors": [],
        "sessions": [{
            "server_session_id": session_id,
            "launch_sequence": 0,
        }],
        "counters": {
            "server_session_id": session_id,
            "launches": 1,
            "atomic_jobs": 1,
            "replay_frames": advanced,
            "observer_frames": 0,
            "instructions": 0,
        },
        "results": [{
            "job_id": job["id"],
            "server_session_id": session_id,
            "status": job["state"],
            "replay_start": frame - advanced,
            "replay_stop": frame,
            "observer_start": frame,
            "observer_stop": frame,
            "instruction_start": 0,
            "instruction_stop": 0,
        }],
    })
    _write_json(paths["pagination"], {
        "schema": "abl-phase4-live-pagination/1",
        "complete": True,
        "errors": [],
        "truncated": False,
        "pages_complete": True,
        "pages": [],
    })
    _write_json(paths["media"], {
        "schema": "abl-phase4-live-media-capabilities/1",
        "complete": True,
        "errors": [],
        "mounted_serial": "SCUS-94288",
        "pristine_media_sha256": PRISTINE_TRACK_SHA256,
        "duckstation_source_sha256": normalized["source_sha256"],
        "duckstation_executable_sha256": normalized["executable_sha256"],
        "api_surface_sha256": normalized["api_surface_sha256"],
        "capabilities": {
            "api_version": document["identity_results"][
                "debugger.capabilities"]["api"]["version"],
            "method_schemas": normalized["method_schemas"],
        },
    })

    normalized_events: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
        ("debugger.capabilities", {}, normalized),
        ("debugger.status", {}, {
            "game_serial": document["identity_results"][
                "debugger.status"].get("game_serial"),
        }),
        ("emulator.getMediaInfo", {}, {
            "serial": "SCUS-94288",
            "sha256": PRISTINE_TRACK_SHA256,
        }),
        ("scenario.runBatch", {"plan_sha256": atomic_plan_sha256}, {
            "batch_id": document["batch_id"],
            "job_ids": [job["id"]],
        }),
    ]
    for poll in document["batch_polls"]:
        normalized_events.append((
            "scenario.getBatch",
            {"batch_id": document["batch_id"], "include_results": True},
            {
                "batch_id": document["batch_id"],
                "status": poll.get("state") or poll.get("status"),
                "job_ids": [
                    row.get("id") for row in poll.get("jobs") or []
                    if row.get("id")
                ] or [job["id"]],
            },
        ))
    events = [
        {
            "sequence": sequence,
            "server_session_id": session_id,
            "method": method,
            "params": params,
            "result_sha256": batch.sha256_bytes(batch.canonical_bytes(result)),
            "result": result,
        }
        for sequence, (method, params, result) in enumerate(normalized_events)
    ]
    offset = len(events)
    events.extend(
        {**event, "sequence": offset + index}
        for index, event in enumerate(
            document["direct_result"]["command_events"]["events"])
    )
    _write_json(paths["events"], {
        "schema": "abl-phase4-live-command-events/1",
        "complete": True,
        "errors": [],
        "events": events,
    })

    receipt = {
        "schema": "abl-phase4-live-run-receipt/2",
        "complete": True,
        "errors": [],
        "escalation_id": runtime["escalation_id"],
        "missing_fact_id": runtime["missing_fact_id"],
        "precise": True,
        "prelude_receipt": _artifact_ref(prelude_receipt, run_root),
        "experiment": experiment,
        "evidence": {
            "raw_results": _artifact_ref(paths["raw"], run_root),
            "pagination": _artifact_ref(paths["pagination"], run_root),
            "media_capabilities": _artifact_ref(paths["media"], run_root),
            "command_events": _artifact_ref(paths["events"], run_root),
            "observer_plan": _artifact_ref(paths["observer"], run_root),
            "perturbation_plan": _artifact_ref(
                paths["perturbation"], run_root),
            "control_plan": _artifact_ref(paths["control"], run_root),
            "adapter_source": {
                "scope": "repo",
                "path": "tools/phase4_duckstation_two_pc_first_hit.py",
                "sha256": common.sha256(DIRECT_ADAPTER),
            },
            "settings_snapshot": _artifact_ref(paths["settings"], run_root),
            "owned_pid_cleanup": _artifact_ref(paths["cleanup"], run_root),
            "external_preservation_manifest": {},
        },
    }
    retained = [
        paths["raw"], paths["pagination"], paths["media"], paths["events"],
        paths["observer"], paths["perturbation"], paths["control"],
        DIRECT_ADAPTER, paths["settings"], paths["cleanup"], paths["batch"],
        paths["direct"], paths["cleanup_raw"], Path(__file__), runtime_path,
    ]
    unique: dict[str, dict[str, Any]] = {}
    for retained_path in retained:
        digest = common.sha256(retained_path)
        unique[digest] = {
            "sha256": digest,
            "size": retained_path.stat().st_size,
            "media_class": (
                "tool_source"
                if retained_path.resolve() in {
                    Path(__file__).resolve(),
                    DIRECT_ADAPTER.resolve(),
                    runtime_path.resolve(),
                }
                else "runtime_receipt"
            ),
            "preservation_required": True,
        }
    _write_json(paths["preservation"], {
        "schema": "abl-phase4-method-external-preservation/1",
        "complete": True,
        "errors": [],
        "entries": list(unique.values()),
    })
    receipt["evidence"]["external_preservation_manifest"] = _artifact_ref(
        paths["preservation"], run_root)
    _write_json(receipt_path, receipt)
    return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
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

    runtime_path = args.runtime.resolve()
    runtime = load_runtime(runtime_path)
    if args.validate_only:
        print(
            f"PASS: {runtime['variant']['receipt_id']} two-PC runtime; "
            f"{len(first_hit.REQUIRED_METHODS)} direct methods; "
            "64 observer frames")
        return 0
    required = {
        "--port": args.port,
        "--token": args.token,
        "--output": args.output,
        "--receipt-dir": args.receipt_dir,
        "--run-root": args.run_root,
        "--config-dir": args.config_dir,
        "--owned-pid": args.owned_pid,
        "--binary": args.binary,
        "--prelude-receipt": args.prelude_receipt,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error(f"live execution lacks: {', '.join(missing)}")
    output = args.output.resolve()
    if ROOT == output or ROOT in output.parents:
        parser.error("live output must remain outside the Git worktree")
    expected_receipt_dir = (
        args.run_root.resolve() / "iteration-1-receipts" / "live" /
        runtime["variant"]["receipt_id"]
    )
    if args.receipt_dir.resolve() != expected_receipt_dir:
        parser.error("receipt directory differs from the predeclared receipt ID")
    if not args.prelude_receipt.is_file():
        parser.error("the required wider passive receipt is absent")

    cleanup = None
    cleanup_raw = None
    document = None
    try:
        document = run_live(
            runtime, args.port, args.token, args.config_dir.resolve(),
            args.owned_pid, args.poll_seconds)
        _write_json(output, document)
    finally:
        cleanup, cleanup_raw = batch.stop_owned_instance(
            args.config_dir.resolve(), args.binary.resolve(), args.owned_pid)
    if cleanup["complete"] is not True:
        raise RuntimeError("owned DuckStation cleanup did not close")
    if document is None:
        raise RuntimeError("two-PC live execution did not produce a result")
    receipt = emit_receipt(
        runtime, runtime_path, document, args.receipt_dir.resolve(),
        args.run_root.resolve(), cleanup, cleanup_raw,
        args.prelude_receipt.resolve())
    print(f"closed live receipt: {receipt} sha256={common.sha256(receipt)}")
    direct = document["direct_result"]
    if direct["outcome"] == "survived":
        detail = (
            f"first_hit={direct['first_hit']['pc']} "
            f"frame={direct['execution']['first_hit_frame']}")
    else:
        detail = (
            f"falsified={direct['falsifier']['reason']} "
            f"failure_frame={direct['execution']['failure_frame']}")
    print(detail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
