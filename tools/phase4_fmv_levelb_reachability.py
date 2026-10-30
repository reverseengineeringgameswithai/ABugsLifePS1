#!/usr/bin/env python3
"""Validate the corrected natural LEVEL01-B reachability evidence."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_fmv_levelb_reachability.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_levelb_reachability.json"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
EXTERNAL_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()
OPERATOR_ROOT = Path(os.environ.get(
    "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads" / "ABL"))).resolve()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def _receipt(role: str) -> tuple[Path, dict]:
    spec = next(
        row for row in CONFIGURATION["external_receipts"]
        if row["role"] == role)
    path = EXTERNAL_ROOT / spec["relative_path"]
    _require(
        path.is_file() and path.stat().st_size == spec["bytes"] and
        common.sha256(path) == spec["sha256"],
        f"{role} receipt identity drifted")
    return path, common.load_json(path)


def _validate_capabilities(document: dict) -> None:
    wanted = CONFIGURATION["debugger"]
    capabilities = document.get("capabilities") or {}
    _require(
        (capabilities.get("api") or {}).get("version") ==
        wanted["api_version"] and
        (capabilities.get("api") or {}).get("schema_version") ==
        wanted["schema_version"] and
        (capabilities.get("binary") or {}).get("sha256") ==
        wanted["binary_sha256"] and
        (capabilities.get("source") or {}).get("revision") ==
        wanted["source_revision"] and
        (capabilities.get("source") or {}).get("dirty_state_hash") ==
        wanted["source_dirty_state_hash"],
        "debugger capability identity drifted")


def _validate_cleanup(role: str, profile: dict, result_role: str) -> dict:
    _path, receipt = _receipt(role)
    result_path, _result = _receipt(result_role)
    evidence = receipt.get("evidence_result") or {}
    _require(
        receipt.get("schema") == "abl-phase4-owned-pid-cleanup/1" and
        receipt.get("config_dir") == profile["config_dir"] and
        receipt.get("owned_pid") == profile["owned_pid"] and
        receipt.get("instance_pid_absent_after_stop") is True and
        receipt.get("owned_pid_alive_after_stop") is False and
        receipt.get("credentials_retained") is False and
        receipt.get("runtime_executable_sha256") ==
        CONFIGURATION["debugger"]["binary_sha256"] and
        evidence.get("absolute_path") == str(result_path) and
        evidence.get("sha256") == common.sha256(result_path) and
        evidence.get("bytes") == result_path.stat().st_size,
        f"{role} cleanup payload drifted")
    return receipt


def _little(memory: list[dict], label: str) -> int:
    row = next(item for item in memory if item["label"] == label)
    return int.from_bytes(bytes.fromhex(row["hex"]), "little")


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _typed_limits(capture: dict) -> list[int]:
    return [
        row["new_value"]
        for row in capture["traces"]["access"]["events"]
        if row.get("instruction_pc") == "0x800b6dc0" and
        row.get("address") == "0x80131eee" and row.get("width") == 2
    ]


def validate_fixtures() -> dict:
    rows = {}
    for role, spec in CONFIGURATION["fixtures"].items():
        path = OPERATOR_ROOT / spec["path"]
        _require(
            path.is_file() and path.stat().st_size == spec["bytes"] and
            common.sha256(path) == spec["sha256"],
            f"{role} fixture identity drifted")
        rows[role] = dict(spec)
    return rows


def validate_cold_boot(document: dict) -> dict:
    expected = CONFIGURATION["expected"]["cold_boot"]
    plan = CONFIGURATION["batch_plan"]
    _require(
        document.get("schema") ==
        "abl-phase4-duckstation-batch-result/1" and
        document.get("plan_sha256") == plan["canonical_sha256"] and
        common.sha256(common.ROOT / plan["path"]) == plan["file_sha256"],
        "cold-boot plan or result identity drifted")
    _validate_capabilities(document)
    mounted = document.get("mounted_media") or {}
    _require(
        mounted.get("game_serial") == CONFIGURATION["media"]["serial"] and
        document["expected_media"]["sha256"] ==
        CONFIGURATION["media"]["cue_sha256"] and
        document["expected_media"]["tracks"][0]["sha256"] ==
        CONFIGURATION["media"]["bin_sha256"],
        "cold-boot mounted media drifted")
    result = document.get("result") or {}
    _require(
        result.get("state") == "completed" and
        result.get("total_jobs") == result.get("processed_jobs") ==
        result.get("succeeded_jobs") == 2 and
        result.get("failed_jobs") == 0,
        "cold-boot batch completion drifted")
    jobs = {row["id"]: row for row in result["jobs"]}
    _require(
        set(jobs) == {
            "level1b_full_movie_positive", "cold_boot_no_input_control"},
        "cold-boot job set drifted")
    summaries = {}
    for job_id, wanted_limits in (
            ("level1b_full_movie_positive",
             expected["positive_selected_limits"]),
            ("cold_boot_no_input_control",
             expected["neutral_selected_limits"])):
        payload = jobs[job_id]["result"]
        capture = payload["capture"]
        traces = capture["traces"]
        execution = traces["execution"]
        summary = {
            "endpoint_frame": capture["frame"],
            "endpoint_cycle": capture["cycle"],
            "frames_advanced": payload["run"]["frames_advanced"],
            "caller_hits": execution["total"],
            "caller_trace_truncated": execution["truncated"],
            "function_events": len(traces["functions"]),
            "selected_limits_from_fmv_writer": _typed_limits(capture),
            "access_ring_truncated": traces["access"]["truncated"],
        }
        _require(
            summary["endpoint_frame"] == expected["endpoint_frame"] and
            summary["endpoint_cycle"] == expected["endpoint_cycle"] and
            summary["frames_advanced"] == 18000 and
            summary["caller_hits"] == expected["caller_hits"] and
            summary["caller_trace_truncated"] is False and
            summary["function_events"] == expected["function_events"] and
            summary["selected_limits_from_fmv_writer"] == wanted_limits and
            summary["access_ring_truncated"] is False and
            expected["level_b_limit"] not in wanted_limits,
            f"{job_id}: legacy cold-boot receipt drifted")
        summaries[job_id] = summary
    positive_access = jobs[
        "level1b_full_movie_positive"]["result"]["capture"]["traces"]["access"]
    movie_started = jobs[
        "level1b_full_movie_positive"]["result"]["movie_started"]
    _require(
        movie_started.get("reproducible") is
        expected["movie_reproducible"] is False and
        movie_started.get("truncated") is False and
        (movie_started.get("start_state") or {}).get("from_boot") is True,
        "legacy cold-boot movie observer status drifted")
    summaries["level1b_full_movie_positive"]["movie_reproducible"] = False
    completion = next(
        row for row in positive_access["watches"]
        if row["label"] == "completion_request")
    _require(
        completion["hit_count"] ==
        expected["positive_completion_watch_hits"] ==
        completion["max_events"] ==
        expected["positive_completion_watch_max_events"],
        "cold-boot positive completion watch saturation drifted")
    summaries["observer_limits"] = {
        "positive_completion_watch_saturated": True,
        "movie_reproducible": False,
        "consequence": (
            "The fixed completion address was reused before FMV.BIN ownership; "
            "it cannot exclude a later completion write. More importantly, "
            "the precise frame-zero observers made movie playback "
            "non-reproducible, so none of this receipt's zero-hit results is "
            "accepted as route-exclusion authority."),
    }
    return summaries


def validate_save_recipe(document: dict) -> dict:
    expected = CONFIGURATION["expected"]["save_recipe"]
    _require(
        document.get("schema") ==
        "abl-phase4-fmv-levelb-staged-live/1",
        "save-recipe receipt schema drifted")
    _validate_capabilities(document)
    fixture = document["fixtures"]["state"]
    _require(
        fixture["sha256"] ==
        CONFIGURATION["fixtures"]["state"]["sha256"] and
        document["state_inspection"]["valid"] is True and
        document["state_inspection"]["serial"] ==
        CONFIGURATION["media"]["serial"] and
        document["mounted_media"]["game_serial"] ==
        CONFIGURATION["media"]["serial"],
        "save-recipe state/media identity drifted")
    positive = document["positive"]
    neutral = document["neutral_control"]
    positive_anchor = {
        key: positive["anchor"][key]
        for key in ("frame", "cycle", "pc", "sp", "scene")}
    neutral_anchor = {
        key: neutral["anchor"][key]
        for key in ("frame", "cycle", "pc", "sp", "scene")}
    _require(
        positive_anchor == neutral_anchor == expected["anchor"] and
        document["method"]["neutral_control_frames"] ==
        expected["neutral_control_frames"],
        "save-recipe anchors or duration drifted")
    summaries = {}
    for role, branch, scene in (
            ("native_recipe", positive, expected["positive_scene"]),
            ("neutral_control", neutral, expected["neutral_scene"])):
        capture = branch["capture"]
        execution = capture["traces"]["execution"]
        summary = {
            "endpoint_frame": capture["frame"],
            "endpoint_cycle": capture["cycle"],
            "scene": _little(capture["memory"], "scene"),
            "caller_hits": execution["total"],
            "caller_trace_truncated": execution["truncated"],
            "function_events": len(capture["traces"]["functions"]),
            "access_ring_truncated":
                capture["traces"]["access"]["truncated"],
            "cleanup_methods": len(branch["cleanup"]),
            "cleanup_failures": [
                row["method"] for row in branch["cleanup"]
                if row["ok"] is not True],
        }
        _require(
            summary["endpoint_frame"] ==
            expected["endpoint"]["frame"] and
            summary["endpoint_cycle"] ==
            expected["endpoint"]["cycle"] and
            summary["scene"] == scene and
            summary["caller_hits"] == expected["caller_hits"] and
            summary["caller_trace_truncated"] is False and
            summary["function_events"] == expected["function_events"] and
            summary["access_ring_truncated"] is False and
            not summary["cleanup_failures"],
            f"{role}: save-recipe exclusion drifted")
        summaries[role] = summary
    _require(
        len(positive["actions"]) == 9 and
        sum(row["frames"] for row in positive["actions"]) ==
        expected["neutral_control_frames"],
        "native action recipe drifted")
    summaries["observer_limits"] = {
        "fixed_fmv_addresses_typed_before_use": False,
        "provenance_log_enabled_at_endpoint":
            document["provenance"]["enabled"],
        "consequence": (
            "Only the post-load exact caller/function traces and scene outcome "
            "are exclusion authority; fixed FMV-overlay addresses are not "
            "typed while the loader was never entered."),
    }
    return summaries


def validate_phase_neutral(document: dict) -> dict:
    expected = CONFIGURATION["expected"]["phase_neutral"]
    _require(
        document.get("schema") ==
        "abl-phase4-fmv-levelb-phase-neutral-live/1",
        "phase-neutral receipt schema drifted")
    _validate_capabilities(document)
    mounted = document.get("mounted_media") or {}
    _require(
        mounted.get("has_media") is True and
        mounted.get("game_serial") == CONFIGURATION["media"]["serial"] and
        mounted.get("verified_cue_sha256") ==
        CONFIGURATION["media"]["cue_sha256"] and
        mounted.get("verified_track_sha256") ==
        CONFIGURATION["media"]["bin_sha256"],
        "phase-neutral mounted media drifted")
    movie_fixture = document["fixtures"]["movie"]
    _require(
        movie_fixture["sha256"] ==
        CONFIGURATION["fixtures"]["movie"]["sha256"] and
        movie_fixture["bytes"] ==
        CONFIGURATION["fixtures"]["movie"]["bytes"],
        "phase-neutral movie fixture drifted")
    method = document.get("method") or {}
    _require(
        method.get("rpc") == "movie.traceToFrame" and
        method.get("trace_mode") == "passive_cached_block_coverage" and
        method.get("source_frame_count") == expected["source_frames"] and
        method.get("derived_frame_count") == expected["derived_frames"] and
        method.get("target_frame") == expected["target_frame"],
        "phase-neutral replay method drifted")
    original_recipe = document["original_replay_derivative"]
    neutral_recipe = document["neutral_derivative"]
    _require(
        original_recipe["source_sha256"] == movie_fixture["sha256"] and
        original_recipe["source_frame_count"] == expected["source_frames"] and
        original_recipe["derived_frame_count"] == expected["derived_frames"] and
        original_recipe["appended_unexecuted_padding_frames"] == 1 and
        original_recipe["changed_frame_count"] == 0 and
        original_recipe["source_prefix_semantically_identical"] is True and
        original_recipe["source_prefix_sha256"] ==
        original_recipe["derived_prefix_sha256"] and
        neutral_recipe["source_sha256"] == movie_fixture["sha256"] and
        neutral_recipe["source_frame_count"] == expected["source_frames"] and
        neutral_recipe["derived_frame_count"] == expected["derived_frames"] and
        neutral_recipe["appended_unexecuted_padding_frames"] == 1 and
        neutral_recipe["changed_frame_count"] ==
        expected["changed_neutral_frames"] and
        neutral_recipe["first_changed_frame"] ==
        expected["first_changed_frame"] and
        neutral_recipe["last_changed_frame"] ==
        expected["last_changed_frame"] and
        neutral_recipe["source_prefix_semantically_identical"] is False and
        neutral_recipe["source_prefix_sha256"] ==
        original_recipe["source_prefix_sha256"],
        "phase-neutral derivative recipe drifted")

    summaries = {}
    for role, branch_key, endpoint_key, observed_key in (
            ("original", "original_movie", "original_endpoint",
             "original_observed"),
            ("neutral", "neutral_movie", "neutral_endpoint",
             "neutral_observed")):
        branch = document[branch_key]
        status = branch["movie_status"]
        trace = branch["cycle_neutral_trace"]
        comparison = trace["comparison"]
        control = trace["control"]
        instrumented = trace["instrumented"]
        wanted_endpoint = expected[endpoint_key]
        _require(
            status.get("reproducible") is True and
            status.get("truncated") is False and
            status.get("playback_index") == expected["target_frame"] and
            status.get("frame_count") == expected["derived_frames"] and
            (status.get("start_state") or {}).get("from_boot") is True and
            trace.get("target_frame") == expected["target_frame"] and
            trace.get("trace_mode") ==
            "passive_cached_block_coverage" and
            comparison.get("cycle_neutral") is True and
            all(comparison.get(key) is True for key in (
                "same_ram", "same_registers", "same_cycle", "same_frame")) and
            control == instrumented == wanted_endpoint,
            f"{role}: phase-neutral endpoint drifted")
        coverage = {row["label"]: row for row in trace["coverage"]}
        wanted_coverage = expected["coverage"][role]
        _require(
            set(coverage) == set(wanted_coverage),
            f"{role}: phase-neutral coverage labels drifted")
        compact_coverage = {}
        for label, wanted in wanted_coverage.items():
            row = coverage[label]
            pcs = row.get("pcs") or []
            recomputed_hash = _canonical_sha256(pcs)
            _require(
                row.get("truncated") is False and
                row.get("total_hits") == wanted["total_hits"] and
                row.get("distinct_pc_count") ==
                wanted["distinct_pc_count"] == len(pcs) and
                row.get("pcs_sha256") == recomputed_hash ==
                wanted["pcs_sha256"],
                f"{role}/{label}: phase-neutral coverage drifted")
            compact_coverage[label] = {
                "total_hits": row["total_hits"],
                "distinct_pc_count": row["distinct_pc_count"],
                "pcs_sha256": recomputed_hash,
                "truncated": False,
            }
        observed = {
            "completed_level_b_call":
                "0x8005031c" in coverage["resident_fmv_sequence"]["pcs"],
            "level_a_reset_call":
                "0x8005b788" in coverage["level_a_reset_owner"]["pcs"],
            "selected_limit_writer":
                "0x800b6dc0" in coverage["fmv_player"]["pcs"],
        }
        _require(
            observed == branch["observed"] == expected[observed_key],
            f"{role}: phase-neutral observed PC set drifted")
        summaries[role] = {
            "movie_reproducible": True,
            "movie_truncated": False,
            "comparison": dict(comparison),
            "endpoint": dict(control),
            "observed": observed,
            "coverage": compact_coverage,
        }
    cleanup_failures = [
        row["method"] for row in document.get("cleanup") or []
        if row.get("ok") is not True]
    profile = CONFIGURATION["profiles"][2]
    instance = document.get("isolated_instance") or {}
    _require(
        instance.get("config_dir") == profile["config_dir"] and
        instance.get("port") == profile["port"] and
        instance.get("profile_recreated") is True and
        instance.get("token_retained") is False and
        not cleanup_failures,
        "phase-neutral isolated-profile cleanup drifted")
    summaries["control_design"] = {
        "source_prefix_frames": expected["source_frames"],
        "appended_unexecuted_padding_frames": 1,
        "neutralized_input_frames": expected["changed_neutral_frames"],
        "cleanup_failures": cleanup_failures,
    }
    return summaries


def build() -> dict:
    fixtures = validate_fixtures()
    receipt_paths = {}
    receipts = {}
    for role in (
            "cold_boot_atomic", "cold_boot_cleanup",
            "save_recipe", "save_recipe_cleanup",
            "phase_neutral_replay", "phase_neutral_cleanup"):
        path, document = _receipt(role)
        receipt_paths[role] = path
        receipts[role] = document
    cold_boot = validate_cold_boot(receipts["cold_boot_atomic"])
    save_recipe = validate_save_recipe(receipts["save_recipe"])
    phase_neutral = validate_phase_neutral(
        receipts["phase_neutral_replay"])
    _validate_cleanup(
        "cold_boot_cleanup", CONFIGURATION["profiles"][0],
        "cold_boot_atomic")
    _validate_cleanup(
        "save_recipe_cleanup", CONFIGURATION["profiles"][1],
        "save_recipe")
    _validate_cleanup(
        "phase_neutral_cleanup", CONFIGURATION["profiles"][2],
        "phase_neutral_replay")
    external_receipts = [{
        "role": role,
        "absolute_path": str(path),
        "sha256": common.sha256(path),
        "bytes": path.stat().st_size,
    } for role, path in receipt_paths.items()]
    record_counts = {
        "atomic_batches": 1,
        "atomic_jobs": 2,
        "atomic_caller_hits": sum(
            cold_boot[role]["caller_hits"]
            for role in (
                "level1b_full_movie_positive",
                "cold_boot_no_input_control")),
        "atomic_typed_selected_limit_events": sum(
            len(cold_boot[role]["selected_limits_from_fmv_writer"])
            for role in (
                "level1b_full_movie_positive",
                "cold_boot_no_input_control")),
        "save_recipe_branches": 2,
        "save_recipe_caller_hits": sum(
            save_recipe[role]["caller_hits"]
            for role in ("native_recipe", "neutral_control")),
        "save_recipe_function_events": sum(
            save_recipe[role]["function_events"]
            for role in ("native_recipe", "neutral_control")),
        "phase_neutral_branches": 2,
        "phase_neutral_coverage_ranges": sum(
            len(phase_neutral[role]["coverage"])
            for role in ("original", "neutral")),
        "phase_neutral_completed_level_b_positive": int(
            phase_neutral["original"]["observed"]
            ["completed_level_b_call"]),
        "phase_neutral_completed_level_b_neutral": int(
            phase_neutral["neutral"]["observed"]
            ["completed_level_b_call"]),
    }
    return {
        "_comment": (
            "Tracked corrected reachability summary only. Raw receipts, "
            "fixture bytes, disc bytes and tokens remain external."),
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_ids": CONFIGURATION["escalation_ids"],
        "external_receipts": external_receipts,
        "fixtures": fixtures,
        "attempts": {
            "superseded_nonreproducible_cold_boot": cold_boot,
            "phase_neutral_full_level_movie": phase_neutral,
            "save_anchor_native_recipe": save_recipe,
        },
        "record_counts": record_counts,
        "falsified_hypotheses": [
            (
                "The centrally pinned 15,230-frame from-boot LEVEL01 movie "
                "does not execute completed-level-B caller 0x8005031C during "
                "its recorded input prefix."),
            (
                "The centrally pinned level01_end_of_stage state plus its "
                "previously reproduced 5,140-frame native completion/save "
                "recipe reaches the completed-level-B caller."),
        ],
        "retained_low_level_facts": [
            (
                "Recorded-anchor passive coverage is reproducible, untruncated "
                "and RAM/register/cycle/frame neutral. The original input "
                "executes both level-A handoff 0x8005B788 and completed-level-B "
                "call 0x8005031C; the all-neutral control executes neither."),
            (
                "The save branches start at identical frame/cycle/PC/SP/scene "
                "and end at identical frame/cycle; native input changes scene "
                "1 to 0 while neutral remains scene 1, but both retain zero "
                "0x8005031C and FMV function events."),
        ],
        "claim_boundary": {
            "classification": "positive_reachability_with_bounded_save_exclusion",
            "dimension_promoted": False,
            "not_claimed": [
                "the exact first completed-level-B frame/cycle and arguments",
                "selector 11, limit 485, completion and teardown on this route",
                "natural level-B reachability from another fixture",
                "movie-viewer or alternate-stream policy",
                "campaign breadth",
            ],
            "next_method": (
                "Use the phase-neutral positive to localize the first "
                "0x8005031C frame, then run one bounded instruction-attributed "
                "same-anchor control for its selector/limit/completion/teardown "
                "chain before evaluating lifecycle or breadth promotion."),
        },
        "source_dependencies": {
            "tools/phase4_fmv_levelb_reachability.py":
                common.sha256(Path(__file__)),
            str(CONFIG_PATH.relative_to(common.ROOT)):
                common.sha256(CONFIG_PATH),
            CONFIGURATION["batch_plan"]["path"]:
                common.sha256(common.ROOT / CONFIGURATION["batch_plan"]["path"]),
            "analysis/phase4_fmv_static_owners.json":
                common.sha256(
                    common.ROOT / "analysis/phase4_fmv_static_owners.json"),
            "analysis/phase4_fmv_interface_frontier.json":
                common.sha256(
                    common.ROOT / "analysis/phase4_fmv_interface_frontier.json"),
            "tools/phase4_fmv_levelb_phase_neutral_live.py":
                common.sha256(
                    common.ROOT /
                    "tools/phase4_fmv_levelb_phase_neutral_live.py"),
        },
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
            raise SystemExit("phase4 level-B reachability artifact is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: phase-neutral level-B reachability corrected; no dimension promoted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
