#!/usr/bin/env python3
"""Validate the external E15 level-A no-input common-exit reachability control."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path

import yaml

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_fmv_natural_completion.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_natural_completion.json"
BATCH_PLAN = common.ROOT / "config/phase4_fmv_natural_completion_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
EXTERNAL_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()
OPERATOR_ROOT = Path(os.environ.get(
    "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads" / "ABL"))).resolve()

SHARED_INITIALIZATION = [
    {
        "type": "entry", "function": "0x8007094c", "caller": "0x8006d3bc",
        "return_address": "0x8006d3c4", "frame": 4443, "cycle": 2515397349,
        "sp": "0x801ff638", "synthetic_unwind": False,
    },
    {
        "type": "exit", "function": "0x8007094c", "caller": "0x8006d3bc",
        "return_address": "0x8006d3c4", "frame": 4443, "cycle": 2515399779,
        "sp": "0x801ff638", "synthetic_unwind": False,
        "v0": "0x00000000", "v1": "0x80121ba0",
    },
]
EXIT_SHAPE = [
    {
        "type": "entry", "function": "0x8007094c", "caller": "0x800b749c",
        "return_address": "0x800b74a4",
    },
    {
        "type": "exit", "function": "0x8007094c", "caller": "0x800b749c",
        "return_address": "0x800b74a4",
    },
    {
        "type": "entry", "function": "0x800709ac", "caller": "0x800b74a4",
        "return_address": "0x800b74ac",
    },
    {
        "type": "exit", "function": "0x800709ac", "caller": "0x800b74a4",
        "return_address": "0x800b74ac",
    },
]


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = json.loads(OUTPUT.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def canonical_plan_sha256(plan: dict) -> str:
    payload = (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _subset(observed: dict, expected: dict) -> bool:
    return all(observed.get(key) == value for key, value in expected.items())


def _memory(job: dict) -> dict[str, dict]:
    rows = job["result"]["capture"]["memory"]
    result = {row["label"]: row for row in rows}
    _require(len(result) == len(rows) == 8, "atomic memory capture shape drifted")
    return result


def validate_plan() -> dict:
    plan = yaml.safe_load(BATCH_PLAN.read_text())
    expected = CONFIGURATION["batch_plan"]
    _require(BATCH_PLAN.relative_to(common.ROOT).as_posix() == expected["path"],
             "batch plan path drifted")
    _require(canonical_plan_sha256(plan) == expected["canonical_sha256"],
             "executed batch plan canonical hash drifted")
    _require(plan.get("campaign_id") == "fmv_playback" and
             plan.get("row_ids") == ["E15_fmv"] and
             plan.get("escalation_ids") == [CONFIGURATION["escalation_id"]],
             "batch plan selection drifted")
    _require([row.get("id") for row in plan.get("jobs") or []] ==
             ["start_skip_positive", "natural_completion_control"] and
             len(plan.get("control_pairs") or []) == 1,
             "batch plan control shape drifted")
    for job in plan["jobs"]:
        _require(job.get("auto_select_disc") is False,
                 "batch plan no longer retains the verified mounted disc")
        _require(job.get("run", {}).get("frames") == CONFIGURATION["run"]["frames"],
                 "batch plan completion bound drifted")
        arm = (job.get("instrumentation") or [None])[0] or {}
        params = arm.get("params") or {}
        _require(arm.get("method") == "functionTrace.start" and
                 params.get("functions") == [0x8007094C, 0x800709AC] and
                 params.get("max_events") == CONFIGURATION["run"]["trace_limit"],
                 "batch plan function trace contract drifted")
        _require(job.get("capture", {}).get("trace_limit") ==
                 CONFIGURATION["run"]["trace_limit"],
                 "batch plan trace capture limit drifted")
    return plan


def validate_external_fixtures() -> dict:
    fixture = CONFIGURATION["fixture"]
    rows = {}
    for kind in ("movie", "state"):
        path = OPERATOR_ROOT / fixture[f"{kind}_path"]
        _require(path.is_file(), f"E15 {kind} fixture is absent")
        _require(common.sha256(path) == fixture[f"{kind}_sha256"],
                 f"E15 {kind} fixture hash drifted")
        rows[kind] = {
            "path": fixture[f"{kind}_path"],
            "sha256": fixture[f"{kind}_sha256"],
            "bytes": path.stat().st_size,
            "media_class": "pristine_serial" if kind == "movie" else "pristine",
        }
    _require(rows["state"]["bytes"] == fixture["state_bytes"],
             "E15 state fixture size drifted")
    return rows


def validate_cleanup_receipt() -> tuple[Path, dict]:
    spec = CONFIGURATION["cleanup_receipt"]
    path = EXTERNAL_ROOT / spec["relative_path"]
    _require(path.is_file() and path.stat().st_size == spec["bytes"] and
             common.sha256(path) == spec["sha256"],
             "owned-PID cleanup receipt identity drifted")
    receipt = common.load_json(path)
    profile = CONFIGURATION["profile"]
    _require(receipt.get("schema") == "abl-phase4-owned-pid-cleanup/1" and
             receipt.get("config_dir") == profile["config_dir"] and
             receipt.get("owned_pid") == profile["owned_pid"] and
             receipt.get("instance_pid_absent_after_stop") is True and
             receipt.get("owned_pid_alive_after_stop") is False and
             receipt.get("credentials_retained") is False and
             receipt.get("runtime_executable_sha256") ==
             CONFIGURATION["debugger"]["binary_sha256"],
             "owned-PID cleanup receipt payload drifted")
    return path, receipt


def validate_prior_boundary() -> dict:
    spec = CONFIGURATION["prior_boundary"]
    path = common.ROOT / spec["artifact"]
    _require(path.is_file() and common.sha256(path) == spec["sha256"],
             "prior 541-frame boundary artifact identity drifted")
    document = common.load_json(path)
    control = document["observations"]["movie_end_residency_control"]
    _require(control["negative_fmv_bin_resident"] is spec["fmv_bin_resident"],
             "prior no-input FMV residency drifted")
    receipt = document["external_receipts"][-1]
    _require(receipt["id"] == "frame_541_causal_control",
             "prior boundary receipt selection drifted")
    external = common.load_json(Path(receipt["absolute_path"]))
    negative = next(row for row in external["result"]["jobs"]
                    if row["id"] == "neutral_negative")
    memory = _memory(negative)
    backloc = int.from_bytes(bytes.fromhex(memory["str_backloc"]["hex"]), "little")
    limit = int.from_bytes(
        bytes.fromhex(memory["selected_frame_limit"]["hex"]), "little")
    _require(backloc == spec["no_input_str_backloc"] and
             limit == spec["selected_frame_limit"] and
             negative["result"]["capture"]["frame"] == spec["no_input_emulator_frame"],
             "prior no-input stream boundary drifted")
    return {
        "artifact": spec["artifact"],
        "sha256": spec["sha256"],
        "frames_advanced": spec["no_input_frames"],
        "emulator_frame": spec["no_input_emulator_frame"],
        "str_backloc": backloc,
        "selected_frame_limit": limit,
        "fmv_bin_resident": control["negative_fmv_bin_resident"],
    }


def _validate_events(job_id: str, events: list[dict]) -> dict:
    expected = CONFIGURATION["expected"][
        "start_skip" if job_id == "start_skip_positive" else "natural_completion"]
    _require(len(events) == 6 and len(events) < CONFIGURATION["run"]["trace_limit"],
             f"{job_id}: function event count drifted or saturated")
    _require(all(_subset(observed, wanted)
                 for observed, wanted in zip(events[:2], SHARED_INITIALIZATION)),
             f"{job_id}: shared initialization event drifted")
    exit_events = events[2:]
    _require(all(_subset(observed, wanted)
                 for observed, wanted in zip(exit_events, EXIT_SHAPE)),
             f"{job_id}: player common-exit call shape drifted")
    _require([row["frame"] for row in exit_events] == [expected["frame"]] * 4 and
             [row["cycle"] for row in exit_events] == expected["cycles"],
             f"{job_id}: player common-exit frame/cycle drifted")
    _require(exit_events[0]["synthetic_unwind"] is False and
             exit_events[1]["synthetic_unwind"] is False and
             exit_events[2]["synthetic_unwind"] is False and
             exit_events[3]["synthetic_unwind"] is
             expected["teardown_exit_synthetic_unwind"],
             f"{job_id}: teardown unwind classification drifted")
    return {
        "frame": expected["frame"],
        "st_clear_ring": {
            "address": exit_events[0]["function"],
            "caller": exit_events[0]["caller"],
            "return_address": exit_events[0]["return_address"],
            "entry_cycle": exit_events[0]["cycle"],
            "exit_cycle": exit_events[1]["cycle"],
        },
        "callback_teardown": {
            "address": exit_events[2]["function"],
            "caller": exit_events[2]["caller"],
            "return_address": exit_events[2]["return_address"],
            "entry_cycle": exit_events[2]["cycle"],
            "exit_cycle": exit_events[3]["cycle"],
            "exit_is_synthetic_unwind": exit_events[3]["synthetic_unwind"],
        },
        "entry_gap_after_st_clear_ring_exit_cycles":
            exit_events[2]["cycle"] - exit_events[1]["cycle"],
        "trace_ring_limit": CONFIGURATION["run"]["trace_limit"],
        "trace_ring_saturated": False,
    }


def validate_receipt(document: dict, *, verify_identity: bool = True,
                     path: Path | None = None) -> dict:
    spec = CONFIGURATION["external_receipt"]
    if verify_identity:
        _require(path is not None and path.is_file(), "natural-completion receipt is absent")
        _require(path.stat().st_size == spec["bytes"] and
                 common.sha256(path) == spec["sha256"],
                 "natural-completion receipt identity drifted")
    _require(document.get("schema") == "abl-phase4-duckstation-batch-result/1" and
             document.get("plan_sha256") == CONFIGURATION["batch_plan"]["canonical_sha256"],
             "natural-completion receipt plan identity drifted")
    debugger = CONFIGURATION["debugger"]
    capabilities = document.get("capabilities") or {}
    _require(document.get("generator_sha256") == debugger["batch_generator_sha256"] and
             document.get("client_sha256") == debugger["client_sha256"],
             "batch tool identity drifted")
    _require(capabilities.get("api", {}).get("version") == debugger["api_version"] and
             capabilities.get("api", {}).get("schema_version") == debugger["schema_version"] and
             capabilities.get("binary", {}).get("sha256") == debugger["binary_sha256"] and
             capabilities.get("source", {}).get("revision") == debugger["source_revision"] and
             capabilities.get("source", {}).get("dirty_state_hash") ==
             debugger["source_dirty_state_hash"],
             "debugger capability identity drifted")
    _require({"debugger.capabilities", "scenario.runBatch",
              "scenario.loadStateAndRun", "provenanceLog.start",
              "capture.atomic"} <= set(capabilities.get("required_methods") or []),
             "required debugger surface drifted")
    media = CONFIGURATION["media"]
    mounted = document.get("mounted_media") or {}
    _require(mounted.get("game_serial") == media["serial"] and
             Path(str(mounted.get("path") or "")).name ==
             "Disney-Pixar A Bug's Life (v1.0).cue",
             "mounted media identity drifted")
    inspections = document.get("state_inspections") or []
    state_info = (inspections[0].get("state_info") or {}) if len(inspections) == 1 else {}
    _require(state_info.get("valid") is True and
             state_info.get("serial") == media["serial"] and
             state_info.get("file_size") == CONFIGURATION["fixture"]["state_bytes"],
             "inspected state identity drifted")
    result = document.get("result") or {}
    _require(result.get("state") == "completed" and result.get("total_jobs") == 2 and
             result.get("processed_jobs") == 2 and result.get("succeeded_jobs") == 2 and
             result.get("failed_jobs") == 0,
             "atomic batch completion drifted")
    jobs = {row["id"]: row for row in result.get("jobs") or []}
    _require(set(jobs) == {"start_skip_positive", "natural_completion_control"},
             "natural-completion control jobs drifted")
    summaries = {}
    for job_id, job in jobs.items():
        payload = job.get("result") or {}
        capture = payload.get("capture") or {}
        _require(job.get("state") == "completed" and job.get("attempts") == 1 and
                 job.get("recipe") == "loadStateAndRun",
                 f"{job_id}: job completion drifted")
        run = CONFIGURATION["run"]
        _require(payload.get("run", {}).get("frames_advanced") == run["frames"] and
                 capture.get("frame") == run["endpoint_emulator_frame"] and
                 capture.get("cycle") == run["endpoint_cycle"] and
                 capture.get("trigger") == run["trigger"] and
                 capture.get("atomic") is True,
                 f"{job_id}: execution bound drifted")
        _require(payload.get("media_verified") is True and
                 payload.get("media", {}).get("sha256") == media["cue_sha256"] and
                 payload.get("media", {}).get("game_serial") == media["serial"],
                 f"{job_id}: post-load media proof drifted")
        events = capture.get("traces", {}).get("functions") or []
        common_exit = _validate_events(job_id, events)
        memory = _memory(job)
        expected = CONFIGURATION["expected"][
            "start_skip" if job_id == "start_skip_positive" else "natural_completion"]
        head_sha = hashlib.sha256(
            bytes.fromhex(memory["fmv_bin_head"]["hex"])).hexdigest()
        _require(head_sha == expected["endpoint_head_sha256"] and
                 head_sha != CONFIGURATION["expected"]["fmv_bin_head_sha256"],
                 f"{job_id}: endpoint Region-B retirement drifted")
        _require(memory["callback_backend_flags"]["hex"] ==
                 CONFIGURATION["expected"]["mmio_pointer_words_hex"],
                 f"{job_id}: MMIO pointer words drifted")
        summaries[job_id] = {
            "common_exit": common_exit,
            "function_event_count": len(events),
            "endpoint_fmv_head_sha256": head_sha,
            "endpoint_fmv_bin_resident": False,
            "mmio_pointer_words_hex": memory["callback_backend_flags"]["hex"],
        }
    return summaries


def build() -> dict:
    _require(CONFIGURATION.get("schema") ==
             "abl-phase4-fmv-natural-completion-source/1",
             "natural-completion source schema drifted")
    validate_plan()
    fixtures = validate_external_fixtures()
    prior = validate_prior_boundary()
    receipt_path = EXTERNAL_ROOT / CONFIGURATION["external_receipt"]["relative_path"]
    jobs = validate_receipt(common.load_json(receipt_path), path=receipt_path)
    cleanup_path, _cleanup = validate_cleanup_receipt()
    profile = CONFIGURATION["profile"]
    _require(profile.get("owned_pid_stopped") is True,
             "isolated profile cleanup declaration drifted")
    start = jobs["start_skip_positive"]["common_exit"]
    natural = jobs["natural_completion_control"]["common_exit"]
    return {
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(),
        "valid": True,
        "errors": [],
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "fixtures": fixtures,
        "external_receipts": [
            {
                "absolute_path": str(receipt_path),
                "sha256": CONFIGURATION["external_receipt"]["sha256"],
                "bytes": CONFIGURATION["external_receipt"]["bytes"],
                "role": "atomic_batch_result",
                "media_class": "external game-derived evidence; never commit",
                "preservation_required": True,
            },
            {
                "absolute_path": str(cleanup_path),
                "sha256": CONFIGURATION["cleanup_receipt"]["sha256"],
                "bytes": CONFIGURATION["cleanup_receipt"]["bytes"],
                "role": "owned_pid_cleanup",
                "media_class": "external non-game cleanup evidence; never commit",
                "preservation_required": True,
            },
        ],
        "profiles": [profile],
        "prior_no_input_boundary": prior,
        "observations": {
            "shared_initialization": {
                "present_in_both_controls": True,
                "function": "StClearRing",
                "address": "0x8007094c",
                **CONFIGURATION["expected"]["initialization"],
            },
            "start_skip": jobs["start_skip_positive"],
            "natural_completion": jobs["natural_completion_control"],
            "common_interface": {
                "same_static_callers_and_returns": True,
                "start_exit_frame": start["frame"],
                "natural_exit_frame": natural["frame"],
                "natural_after_start_frames": natural["frame"] - start["frame"],
                "natural_after_prior_boundary_frames":
                    natural["frame"] - prior["emulator_frame"],
                "start_teardown_synthetic_unwind":
                    start["callback_teardown"]["exit_is_synthetic_unwind"],
                "natural_teardown_synthetic_unwind":
                    natural["callback_teardown"]["exit_is_synthetic_unwind"],
            },
            "endpoint": {
                "frames_advanced": CONFIGURATION["run"]["frames"],
                "emulator_frame": CONFIGURATION["run"]["endpoint_emulator_frame"],
                "cycle": CONFIGURATION["run"]["endpoint_cycle"],
                "both_fmv_bin_retired": True,
                "region_b_typed_fields_valid": False,
            },
        },
        "record_counts": {
            "atomic_batches": 1,
            "jobs": 2,
            "function_events": sum(row["function_event_count"] for row in jobs.values()),
        },
        "bounded_conclusion": (
            "At the inspected pristine LEV1A save anchor, no input reaches "
            "the same player common-exit StClearRing and callback_teardown "
            "call sites as Start-skip, 634 emulator frames later. This receipt "
            "proves common-exit reachability only; it does not identify which "
            "completion, stop, or failure writer caused the converging exit. "
            "Natural callback_teardown returns normally; the Start trace "
            "retains its synthetic-unwind observer event."
        ),
        "residuals": [
            "This receipt proves one level-A no-input common-exit reachability fact, not its cause; event-aligned completion, backloc, selected-limit and stop-latch provenance is required.",
            "Pause, stop, repeated playback, scene unload/reload, decode timeout, CD failure and malformed-stream outcomes remain open.",
            "E12 audio, C17 viewer selection/unlocks, E14 persistence and E16 generic overlay loading retain separate interfaces.",
            "Endpoint Region-B memory is untyped after FMV.BIN retirement; only its failed identity guard is asserted.",
        ],
        "raw_external_bytes_committed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    payload = render(document)
    if args.write:
        OUTPUT.write_bytes(payload)
    if args.check and (not OUTPUT.is_file() or OUTPUT.read_bytes() != payload):
        print(f"ERROR: stale {OUTPUT.relative_to(common.ROOT)}")
        return 1
    if not args.write and not args.check:
        print(json.dumps(document, indent=2, sort_keys=True))
    else:
        print("PASS: 2 E15 jobs; no-input common exit is 634 frames after Start")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
