#!/usr/bin/env python3
"""Validate and summarize the external E15 callback-lifecycle control receipts."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_fmv_callback_lifecycle.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_callback_lifecycle.json"
BATCH_PLAN = common.ROOT / "config/phase4_fmv_callback_lifecycle_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
EXTERNAL_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()
OPERATOR_ROOT = Path(os.environ.get(
    "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads" / "ABL"))).resolve()

SHARED_EVENTS = [
    {
        "type": "entry", "function": "0x8007094c", "caller": "0x8006d3bc",
        "return_address": "0x8006d3c4", "frame": 4443, "cycle": 2515397349,
        "sp": "0x801ff638", "synthetic_unwind": False,
        "arguments": ["0x801217c0", "0x00000020", "0x00000001", "0x00000000"],
    },
    {
        "type": "exit", "function": "0x8007094c", "caller": "0x8006d3bc",
        "return_address": "0x8006d3c4", "frame": 4443, "cycle": 2515399779,
        "sp": "0x801ff638", "synthetic_unwind": False,
        "v0": "0x00000000", "v1": "0x80121ba0",
    },
]

PLAYER_EXIT_EVENTS = [
    {
        "type": "entry", "function": "0x8007094c", "caller": "0x800b749c",
        "return_address": "0x800b74a4", "frame": 4671, "cycle": 2644271877,
        "sp": "0x801ff650", "synthetic_unwind": False,
        "arguments": ["0x801fff08", "0x00000000", "0x00000000", "0x00000000"],
    },
    {
        "type": "exit", "function": "0x8007094c", "caller": "0x800b749c",
        "return_address": "0x800b74a4", "frame": 4671, "cycle": 2644274307,
        "sp": "0x801ff650", "synthetic_unwind": False,
        "v0": "0x00000000", "v1": "0x80121ba0",
    },
    {
        "type": "entry", "function": "0x800709ac", "caller": "0x800b74a4",
        "return_address": "0x800b74ac", "frame": 4671, "cycle": 2644274321,
        "sp": "0x801ff650", "synthetic_unwind": False,
        "arguments": ["0x00000000", "0x00000020", "0x00000020", "0x00000000"],
    },
    {
        "type": "exit", "function": "0x800709ac", "caller": "0x800b74a4",
        "return_address": "0x800b74ac", "frame": 4671, "cycle": 2644284120,
        "sp": "0x80080d70", "synthetic_unwind": True,
        "v0": "0x00000001", "v1": "0x0000863c",
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


def _event_subset(event: dict, expected: dict) -> bool:
    return all(event.get(key) == value for key, value in expected.items())


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
             plan.get("row_ids") == ["E15_fmv"],
             "batch plan selection drifted")
    _require(len(plan.get("jobs") or []) == 2 and
             len(plan.get("control_pairs") or []) == 1,
             "batch plan control shape drifted")
    for job in plan["jobs"]:
        _require(job.get("auto_select_disc") is False,
                 "batch plan no longer retains the verified mounted disc")
        _require(job.get("run", {}).get("frames") == 541,
                 "batch plan movie-end bound drifted")
        arm = (job.get("instrumentation") or [None])[0] or {}
        params = arm.get("params") or {}
        _require(arm.get("method") == "functionTrace.start" and
                 params.get("functions") == [0x8007094C, 0x800709AC] and
                 params.get("max_events") == 16,
                 "batch plan function trace contract drifted")
        _require(job.get("capture", {}).get("trace_limit") == 16,
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


def validate_receipt(document: dict, spec: dict, *, verify_identity: bool = True,
                     path: Path | None = None) -> dict:
    if verify_identity:
        _require(path is not None and path.is_file(), f"{spec['id']}: receipt is absent")
        _require(path.stat().st_size == spec["bytes"],
                 f"{spec['id']}: receipt size drifted")
        _require(common.sha256(path) == spec["sha256"],
                 f"{spec['id']}: receipt hash drifted")
    _require(document.get("schema") == "abl-phase4-duckstation-batch-result/1",
             f"{spec['id']}: receipt schema drifted")
    _require(document.get("plan_sha256") == spec["plan_sha256"],
             f"{spec['id']}: plan identity drifted")
    debugger = CONFIGURATION["debugger"]
    capabilities = document.get("capabilities") or {}
    _require(document.get("generator_sha256") == debugger["batch_generator_sha256"] and
             document.get("client_sha256") == debugger["client_sha256"],
             f"{spec['id']}: batch tool identity drifted")
    _require(capabilities.get("api", {}).get("version") == debugger["api_version"] and
             capabilities.get("api", {}).get("schema_version") == debugger["schema_version"],
             f"{spec['id']}: debugger API drifted")
    _require(capabilities.get("binary", {}).get("sha256") == debugger["binary_sha256"] and
             capabilities.get("source", {}).get("revision") == debugger["source_revision"] and
             capabilities.get("source", {}).get("dirty_state_hash") ==
             debugger["source_dirty_state_hash"],
             f"{spec['id']}: debugger build identity drifted")
    required_methods = set(capabilities.get("required_methods") or [])
    _require({"scenario.runBatch", "scenario.loadStateAndRun",
              "provenanceLog.start", "capture.atomic"} <= required_methods,
             f"{spec['id']}: required debugger surface drifted")
    media = CONFIGURATION["media"]
    mounted = document.get("mounted_media") or {}
    _require(mounted.get("game_serial") == media["serial"] and
             Path(str(mounted.get("path") or "")).name ==
             "Disney-Pixar A Bug's Life (v1.0).cue",
             f"{spec['id']}: mounted media identity drifted")
    inspections = document.get("state_inspections") or []
    _require(len(inspections) == 1, f"{spec['id']}: state inspection count drifted")
    state_info = inspections[0].get("state_info") or {}
    _require(state_info.get("valid") is True and
             state_info.get("serial") == media["serial"] and
             state_info.get("file_size") == CONFIGURATION["fixture"]["state_bytes"],
             f"{spec['id']}: inspected state identity drifted")
    result = document.get("result") or {}
    _require(result.get("state") == "completed" and result.get("total_jobs") == 2 and
             result.get("processed_jobs") == 2 and result.get("succeeded_jobs") == 2 and
             result.get("failed_jobs") == 0,
             f"{spec['id']}: atomic batch completion drifted")
    jobs = {row["id"]: row for row in result.get("jobs") or []}
    _require(set(jobs) == {"start_skip_positive", "neutral_negative"},
             f"{spec['id']}: control jobs drifted")
    expected_head = CONFIGURATION["expected_fmv_head_sha256"]
    summaries = {}
    for job_id, job in jobs.items():
        payload = job.get("result") or {}
        capture = payload.get("capture") or {}
        _require(job.get("state") == "completed" and job.get("attempts") == 1 and
                 job.get("recipe") == "loadStateAndRun",
                 f"{spec['id']}/{job_id}: job completion drifted")
        expected_cycle = spec.get("negative_cycle", spec["cycle"]) \
            if job_id == "neutral_negative" else spec["cycle"]
        _require(payload.get("run", {}).get("frames_advanced") == spec["frames"] and
                 capture.get("frame") == spec["emulator_frame"] and
                 capture.get("cycle") == expected_cycle and
                 capture.get("trigger") == spec["trigger"] and
                 capture.get("atomic") is True,
                 f"{spec['id']}/{job_id}: execution bound drifted")
        _require(payload.get("media_verified") is True and
                 payload.get("media", {}).get("sha256") == media["cue_sha256"] and
                 payload.get("media", {}).get("game_serial") == media["serial"],
                 f"{spec['id']}/{job_id}: post-load media proof drifted")
        events = capture.get("traces", {}).get("functions") or []
        expected_count = spec[
            "expected_positive_events" if job_id == "start_skip_positive"
            else "expected_negative_events"]
        _require(len(events) == expected_count and len(events) < 16,
                 f"{spec['id']}/{job_id}: function event count drifted or saturated")
        expected_events = SHARED_EVENTS
        if spec["id"] == "frame_541_causal_control" and \
                job_id == "start_skip_positive":
            expected_events = SHARED_EVENTS + PLAYER_EXIT_EVENTS
        _require(len(events) == len(expected_events) and
                 all(_event_subset(event, expected)
                     for event, expected in zip(events, expected_events)),
                 f"{spec['id']}/{job_id}: function caller/order/cycle drifted")
        memory = _memory(job)
        head_sha = hashlib.sha256(bytes.fromhex(memory["fmv_bin_head"]["hex"])).hexdigest()
        resident = head_sha == expected_head
        expected_resident = True if job_id == "neutral_negative" else \
            bool(spec["positive_overlay_resident"])
        _require(resident is expected_resident,
                 f"{spec['id']}/{job_id}: FMV.BIN residency drifted")
        _require(memory["callback_backend_flags"]["hex"] ==
                 CONFIGURATION["expected_callback_words_hex"],
                 f"{spec['id']}/{job_id}: fixed callback words drifted")
        summaries[job_id] = {
            "function_events": events,
            "event_count": len(events),
            "trace_ring_limit": 16,
            "trace_ring_saturated": False,
            "fmv_head_sha256": head_sha,
            "fmv_bin_resident": resident,
            "callback_words_hex": memory["callback_backend_flags"]["hex"],
            "str_backloc": int.from_bytes(
                bytes.fromhex(memory["str_backloc"]["hex"]), "little"),
        }
    return {
        "id": spec["id"],
        "frames_advanced": spec["frames"],
        "emulator_frame": spec["emulator_frame"],
        "cycle": spec["cycle"],
        "jobs": summaries,
    }


def build() -> dict:
    _require(CONFIGURATION.get("schema") ==
             "abl-phase4-fmv-callback-lifecycle-source/1",
             "callback lifecycle source schema drifted")
    validate_plan()
    fixtures = validate_external_fixtures()
    receipts = []
    preservation = []
    for spec in CONFIGURATION["external_receipts"]:
        path = EXTERNAL_ROOT / spec["relative_path"]
        document = json.loads(path.read_text())
        receipts.append(validate_receipt(document, spec, path=path))
        preservation.append({
            "id": spec["id"],
            "absolute_path": str(path),
            "sha256": spec["sha256"],
            "bytes": spec["bytes"],
            "media_class": "external game-derived evidence; never commit",
            "preservation_required": True,
        })
    for profile in CONFIGURATION["profiles"]:
        config_dir = Path(profile["config_dir"])
        _require(config_dir.is_dir() and not (config_dir / "instance.pid").exists() and
                 profile.get("owned_pid_stopped") is True,
                 f"isolated profile cleanup receipt drifted: {config_dir}")
    final = receipts[-1]["jobs"]
    positive_events = final["start_skip_positive"]["function_events"]
    teardown_entry = positive_events[4]
    teardown_exit = positive_events[5]
    return {
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(),
        "valid": True,
        "errors": [],
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "fixtures": fixtures,
        "external_receipts": preservation,
        "profiles": CONFIGURATION["profiles"],
        "observations": {
            "shared_initialization": {
                "present_in_both_controls": True,
                "function": "StClearRing",
                "address": "0x8007094c",
                "caller": "0x8006d3bc",
                "return_address": "0x8006d3c4",
                "emulator_frame": 4443,
                "entry_cycle": 2515397349,
                "exit_cycle": 2515399779,
            },
            "positive_common_exit": {
                "negative_control_absent": True,
                "emulator_frame": 4671,
                "st_clear_ring": {
                    "caller": "0x800b749c",
                    "return_address": "0x800b74a4",
                    "entry_cycle": 2644271877,
                    "exit_cycle": 2644274307,
                },
                "callback_teardown": {
                    "address": teardown_entry["function"],
                    "caller": teardown_entry["caller"],
                    "return_address": teardown_entry["return_address"],
                    "entry_cycle": teardown_entry["cycle"],
                    "exit_cycle": teardown_exit["cycle"],
                    "exit_is_synthetic_unwind": teardown_exit["synthetic_unwind"],
                    "exit_v0": teardown_exit["v0"],
                },
                "entry_gap_after_st_clear_ring_exit_cycles":
                    teardown_entry["cycle"] - positive_events[3]["cycle"],
            },
            "movie_end_residency_control": {
                "positive_fmv_bin_resident":
                    final["start_skip_positive"]["fmv_bin_resident"],
                "negative_fmv_bin_resident":
                    final["neutral_negative"]["fmv_bin_resident"],
                "negative_fmv_head_sha256":
                    final["neutral_negative"]["fmv_head_sha256"],
            },
            "fixed_callback_words": {
                "positive": final["start_skip_positive"]["callback_words_hex"],
                "negative": final["neutral_negative"]["callback_words_hex"],
                "equal_after_capture": True,
            },
        },
        "falsified_hypotheses": [
            "Passive frame-362 block starts prove a positive-only teardown call.",
            "The passive capsule's 416-to-417 FMV.BIN retirement is an exact live function-trace trigger.",
            "callback_teardown clears the four captured fixed callback words before the movie-end capture.",
        ],
        "causal_conclusion": (
            "At the inspected pristine E15 save anchor, Start-only input is sufficient "
            "for the player common exit to call StClearRing and then callback_teardown; "
            "the same 541-frame no-input control calls neither exit interface and "
            "retains exact FMV.BIN."
        ),
        "residuals": [
            "The callback_teardown exit is a synthetic unwind, not a conventional balanced return.",
            "The four captured fixed callback words remain equal across controls after capture.",
            "Function tracing shifts the live positive retirement later than the passive capsule boundary; capsule block starts remain correlation only.",
            "This one same-anchor control does not close pause, repeat, error, alternate-route or platform lifecycle breadth.",
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
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != payload:
            print(f"ERROR: stale {OUTPUT.relative_to(common.ROOT)}")
            return 1
    if not args.write and not args.check:
        print(json.dumps(document, indent=2, sort_keys=True))
    else:
        print("PASS: 3 E15 callback receipts, 1 causal control, 3 falsified hypotheses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
