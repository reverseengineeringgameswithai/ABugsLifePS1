#!/usr/bin/env python3
"""Run and retain one predeclared E15 exact-PC DMA experiment.

The generic Phase-4 batch runner cannot arm a direct observer between two
pre-instruction stops.  This runner establishes one paused, cold-boot atomic
anchor, retains the three authority identities and the batch command/result
stream, delegates the narrowed window to
``phase4_duckstation_exact_pc_batch``, and emits the strict v2 receipt admitted
by ``phase4_method_metrics``.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

import yaml

import phase4_common as common
import phase4_duckstation_batch as batch
import phase4_duckstation_exact_pc_batch as exact_pc


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SCHEMA = "abl-phase4-fmv-levelb-region-b-dma-exact-pc-runtime/1"
RESULT_SCHEMA = "abl-phase4-fmv-levelb-region-b-dma-exact-pc-live-result/1"
PRISTINE_TRACK_SHA256 = (
    "2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566"
)
EXACT_ADAPTER = ROOT / "tools/phase4_duckstation_exact_pc_batch.py"
RPC_MANIFEST = ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
TERMINAL_BATCH_STATES = {"completed", "failed", "cancelled"}


def _exact_keys(value: object, expected: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{where} keys differ from the closed schema")
    return value


def load_runtime(path: Path) -> dict[str, Any]:
    runtime = yaml.safe_load(path.read_text())
    _exact_keys(
        runtime,
        {
            "schema", "campaign_id", "row_ids", "escalation_id",
            "missing_fact_id", "expected_media", "expected_debugger",
            "movie", "atomic_anchor", "exact_pc_plan", "execution",
            "domain", "observer_plan", "perturbation_plan",
            "settings_snapshot", "assertion_plan", "variants",
        },
        "runtime",
    )
    if runtime["schema"] != RUNTIME_SCHEMA:
        raise ValueError("runtime schema is invalid")
    if runtime["campaign_id"] != "fmv_playback" or \
            runtime["row_ids"] != ["E15_fmv"]:
        raise ValueError("runtime campaign/row selection drifted")
    if runtime["domain"] != "dma":
        raise ValueError("runtime domain must be DMA")
    expected_media = _exact_keys(
        runtime["expected_media"],
        {"path", "serial", "title", "sha256", "tracks"},
        "expected_media",
    )
    if expected_media["serial"] != "SCUS-94288":
        raise ValueError("runtime media serial is not pristine SCUS-94288")
    tracks = expected_media["tracks"]
    if not isinstance(tracks, list) or len(tracks) != 1 or \
            tracks[0].get("sha256") != PRISTINE_TRACK_SHA256:
        raise ValueError("runtime media track is not the pristine authority pin")
    movie = _exact_keys(runtime["movie"], {"path", "sha256"}, "movie")
    movie_path = ROOT / movie["path"]
    if not movie_path.is_file() or common.sha256(movie_path) != movie["sha256"]:
        raise ValueError("centrally provisioned exact-PC movie identity drifted")
    anchor = _exact_keys(
        runtime["atomic_anchor"],
        {
            "job_id", "target_frame", "max_frames", "run_frames",
            "capture_trigger", "trace_limit", "memory_dumps",
        },
        "atomic_anchor",
    )
    if anchor["target_frame"] != 15816 or anchor["max_frames"] != 15816 or \
            anchor["run_frames"] != 15815:
        raise ValueError("atomic anchor must stop at emulator frame 15816")
    execution = runtime["execution"]
    if execution != {
        "bound": {
            "clock": "emulator_frame", "start": 0, "stop": 15880,
            "stop_inclusive": False,
        },
        "capture_window": {
            "clock": "emulator_frame", "start": 15816, "stop": 15880,
            "stop_inclusive": False,
        },
    }:
        raise ValueError("runtime execution window differs from the predeclared bound")
    plan_ref = _exact_keys(
        runtime["exact_pc_plan"], {"path", "sha256"}, "exact_pc_plan")
    plan_path = ROOT / plan_ref["path"]
    if not plan_path.is_file() or common.sha256(plan_path) != plan_ref["sha256"]:
        raise ValueError("exact-PC plan identity drifted")
    plan_doc = yaml.safe_load(plan_path.read_text())
    plan = plan_doc["exact_pc_plan"]
    plan_errors = exact_pc.validate_plan(plan)
    if plan_errors:
        raise ValueError(f"exact-PC plan is invalid: {'; '.join(plan_errors)}")
    observer = runtime["observer_plan"]
    if observer != {
        "schema": "abl-phase4-observer-plan/2",
        "operations": [{
            "sequence": 0, "method": "transferLog.start", "args": {},
        }],
        "result_limits": {
            "max_records": plan["transfer_pagination"]["max_records"],
            "max_bytes": plan["transfer_pagination"]["max_bytes"],
            "max_pages": plan["transfer_pagination"]["max_pages"],
        },
        "direct_command_plan": plan,
    }:
        raise ValueError("runtime observer plan differs from the guarded exact-PC plan")
    if runtime["perturbation_plan"] != {
        "schema": "abl-phase4-perturbation-plan/1",
        "kind": "none",
        "operations": [],
    }:
        raise ValueError("runtime perturbation must be none")
    variants = runtime["variants"]
    if variants != [
        {
            "name": "native",
            "receipt_id": "e15-levelb-region-b-dma-exact-pc-native",
            "control_role": "positive",
        },
        {
            "name": "repeat",
            "receipt_id": "e15-levelb-region-b-dma-exact-pc-repeat",
            "control_role": "negative",
        },
    ]:
        raise ValueError("runtime variants differ from the predeclared receipts")
    return runtime


def exact_plan(runtime: dict[str, Any]) -> dict[str, Any]:
    return yaml.safe_load(
        (ROOT / runtime["exact_pc_plan"]["path"]).read_text()
    )["exact_pc_plan"]


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
    required = (
        set(exact_pc.REQUIRED_METHODS)
        | batch.REQUIRED_METHODS
        | {"scenario.runBatch", "scenario.getBatch"}
    )
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
        raise RuntimeError(
            f"mounted media identity differs from runtime: status={status}, "
            f"media={media}")
    for track in expected_media["tracks"]:
        track_path = Path(track["path"])
        if not track_path.is_file() or \
                common.sha256(track_path) != track["sha256"]:
            raise RuntimeError(f"pristine companion track drifted: {track_path}")
    manifest = common.load_json(RPC_MANIFEST)
    normalized = batch._normalized_capabilities(capabilities, manifest)
    identity = exact_plan(runtime)["identity_join"]
    manifest_source = manifest["source"]
    manifest_binary = manifest["binaries"][
        "build-release/bin/duckstation-qt"]
    expected_identity = {
        "rpc_manifest_sha256": common.sha256(RPC_MANIFEST),
        "source_revision": manifest_source["revision"],
        "source_dirty_state_hash": manifest_source["dirty_state_hash"],
        "dispatcher_sha256": manifest_source["dispatcher_sha256"],
        "binary_sha256": manifest_binary["sha256"],
        "media_serial": expected_media["serial"],
        "media_sha256": PRISTINE_TRACK_SHA256,
    }
    if identity != expected_identity or \
            normalized["executable_sha256"] != identity["binary_sha256"]:
        raise RuntimeError("exact-PC identity join differs from current authority")
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
            # bootAndRun reports frame 1 before executing its first finite
            # frame; 15,815 advances therefore establish paused frame 15,816.
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
    variant: dict[str, Any],
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
    if len(jobs) != 1 or jobs[0].get("id") != \
            runtime["atomic_anchor"]["job_id"] or \
            jobs[0].get("state") != "completed":
        raise RuntimeError("atomic anchor batch result is incomplete")
    result = jobs[0].get("result") or {}
    advanced = (result.get("run") or {}).get("frames_advanced")
    frame = (result.get("status") or {}).get("frame")
    if advanced != runtime["atomic_anchor"]["run_frames"] or \
            frame != runtime["atomic_anchor"]["target_frame"]:
        raise RuntimeError(
            f"atomic anchor did not stop at frame 15816: "
            f"advanced={advanced}, frame={frame}")

    session_id = batch.sha256_bytes(batch.canonical_bytes({
        "config_dir": str(config_dir.resolve()),
        "owned_pid": owned_pid,
        "port": port,
        "batch_id": batch_id,
        "executable_sha256": normalized["executable_sha256"],
    }))
    observed_direct_events: list[dict[str, Any]] = []

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
        observed_direct_events.append({
            "sequence": len(observed_direct_events),
            "server_session_id": session_id,
            "method": method,
            "params": params,
            "socket_timeout_ms": socket_timeout_ms,
            "result_sha256": batch.sha256_bytes(
                batch.canonical_bytes(result_body)),
            "result": result_body,
        })
        return result_body

    direct_plan = exact_plan(runtime)
    try:
        direct = exact_pc.execute_exact_pc_window(
            rpc_call,
            direct_plan,
            session_id,
            direct_plan["identity_join"],
        )
        direct["outcome"] = "survived"
    except exact_pc.ExactPcFalsifiedError as exc:
        status_events = [
            event["result"] for event in observed_direct_events
            if event["method"] == "debugger.status"
        ]
        if not status_events:
            raise RuntimeError(
                "exact-PC falsifier lacked a retained status result") from exc
        direct = {
            "schema": exact_pc.RESULT_SCHEMA,
            "complete": True,
            "errors": [],
            "outcome": "falsified",
            "falsifier": {
                "code": "EXACT_PC_TYPED_PREDICATE_FALSE",
                "reason": str(exc),
            },
            "server_session_id": session_id,
            "verified_identity": direct_plan["identity_join"],
            "plan_sha256": batch.sha256_bytes(
                batch.canonical_bytes(direct_plan)),
            "execution": {
                "clock": "emulator_frame",
                "anchor_frame": status_events[0].get("frame"),
                "frame_ceiling": (
                    status_events[0].get("frame")
                    + direct_plan["execution_limit"]["max_frame_delta"]
                ),
                "failure_frame": status_events[-1].get("frame"),
            },
            "transfer": {
                "total": 0,
                "truncated": False,
                "pages": [],
                "indexes_contiguous": True,
                "retained_bytes": 2,
            },
            "command_events": {
                "complete": True,
                "errors": [],
                "events": observed_direct_events,
            },
        }
    return {
        "schema": RESULT_SCHEMA,
        "generated": datetime.now(timezone.utc).isoformat(),
        "complete": True,
        "errors": [],
        "variant": variant["name"],
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
    variant: dict[str, Any],
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
        "settings": receipt_dir / "settings-snapshot.json",
        "observer": receipt_dir / "observer-plan.json",
        "perturbation": receipt_dir / "perturbation-plan.json",
        "control": receipt_dir / "control-plan.json",
        "raw": receipt_dir / "raw-results.json",
        "pagination": receipt_dir / "pagination.json",
        "media": receipt_dir / "media-capabilities.json",
        "events": receipt_dir / "command-events.json",
        "cleanup": receipt_dir / "owned-pid-cleanup.json",
        "cleanup_raw": receipt_dir / "owned-pid-cleanup-raw.json",
        "batch": receipt_dir / "batch-result.json",
        "direct": receipt_dir / "exact-pc-result.json",
        "preservation": receipt_dir / "preservation.json",
    }
    document["runtime_sha256"] = common.sha256(runtime_path)
    _write_json(paths["batch"], document)
    _write_json(paths["direct"], document["direct_result"])
    _write_json(paths["settings"], runtime["settings_snapshot"])
    _write_json(paths["observer"], runtime["observer_plan"])
    _write_json(paths["perturbation"], runtime["perturbation_plan"])
    _write_json(paths["cleanup"], cleanup)
    _write_json(paths["cleanup_raw"], cleanup_raw)

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
        "adapter_source_sha256": common.sha256(EXACT_ADAPTER),
    }
    control = {
        "schema": "abl-phase4-control-plan/1",
        "role": variant["control_role"],
        "paired_run_basis_sha256": batch.sha256_bytes(batch.canonical_bytes(
            experiment_without_control)),
        "anchor_sha256": batch.sha256_bytes(batch.canonical_bytes(
            experiment_without_control["anchor"])),
        "only_difference_plan_sha256": common.sha256(paths["perturbation"]),
        "assertion_plan_sha256": batch.sha256_bytes(batch.canonical_bytes(
            runtime["assertion_plan"])),
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
    raw = {
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
    }
    _write_json(paths["raw"], raw)

    direct = document["direct_result"]
    pagination = {
        "schema": "abl-phase4-live-pagination/1",
        "complete": True,
        "errors": [],
        "truncated": direct["transfer"]["truncated"],
        "pages_complete": True,
        "pages": [
            {"page": index, "record_count": page["returned"]}
            for index, page in enumerate(direct["transfer"]["pages"])
        ],
    }
    _write_json(paths["pagination"], pagination)
    media = {
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
    }
    _write_json(paths["media"], media)

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
            {
                "batch_id": document["batch_id"],
                "include_results": True,
            },
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
        for index, event in enumerate(direct["command_events"]["events"])
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
                "path": "tools/phase4_duckstation_exact_pc_batch.py",
                "sha256": common.sha256(EXACT_ADAPTER),
            },
            "settings_snapshot": _artifact_ref(paths["settings"], run_root),
            "owned_pid_cleanup": _artifact_ref(paths["cleanup"], run_root),
            "external_preservation_manifest": {},
        },
    }
    retained = [
        paths["raw"], paths["pagination"], paths["media"], paths["events"],
        paths["observer"], paths["perturbation"], paths["control"],
        EXACT_ADAPTER, paths["settings"], paths["cleanup"], paths["batch"],
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
                if retained_path.suffix in {".py", ".yaml"}
                and retained_path.resolve() in {
                    Path(__file__).resolve(),
                    EXACT_ADAPTER.resolve(),
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
    parser.add_argument("--variant", choices=("native", "repeat"), required=True)
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
    variant = next(
        row for row in runtime["variants"] if row["name"] == args.variant)
    if args.validate_only:
        print(
            f"PASS: {variant['receipt_id']} exact-PC runtime; "
            f"{len(exact_pc.REQUIRED_METHODS)} direct methods")
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
    if args.receipt_dir.resolve() != \
            args.run_root.resolve() / "iteration-1-receipts" / "live" / \
            variant["receipt_id"]:
        parser.error("receipt directory differs from the predeclared variant ID")
    if not args.prelude_receipt.is_file():
        parser.error("the required wider passive receipt is absent")

    cleanup = None
    cleanup_raw = None
    document = None
    try:
        document = run_live(
            runtime, variant, args.port, args.token,
            args.config_dir.resolve(), args.owned_pid, args.poll_seconds)
        _write_json(output, document)
    finally:
        cleanup, cleanup_raw = batch.stop_owned_instance(
            args.config_dir.resolve(), args.binary.resolve(), args.owned_pid)
    if cleanup["complete"] is not True:
        raise RuntimeError("owned DuckStation cleanup did not close")
    if document is None:
        raise RuntimeError("exact-PC live execution did not produce a result")
    receipt = emit_receipt(
        runtime, runtime_path, variant, document, args.receipt_dir.resolve(),
        args.run_root.resolve(), cleanup, cleanup_raw,
        args.prelude_receipt.resolve())
    print(f"closed live receipt: {receipt} sha256={common.sha256(receipt)}")
    direct = document["direct_result"]
    if direct["outcome"] == "survived":
        detail = (
            f"transfers={direct['transfer']['total']} "
            f"terminal_frame={direct['execution']['terminal_stop_frame']}")
    else:
        detail = (
            f"falsified={direct['falsifier']['reason']} "
            f"failure_frame={direct['execution']['failure_frame']}")
    print(f"{variant['name']}: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
