#!/usr/bin/env python3
"""Validate and bank the natural completed-Level-B FMV lifecycle receipt."""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_fmv_levelb_first_call.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_levelb_first_call.json"
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


def _spec(role: str) -> dict:
    return next(
        row for row in CONFIGURATION["external_receipts"]
        if row["role"] == role)


def _receipt(role: str) -> tuple[Path, dict]:
    spec = _spec(role)
    path = EXTERNAL_ROOT / spec["relative_path"]
    _require(
        path.is_file() and path.stat().st_size == spec["bytes"] and
        common.sha256(path) == spec["sha256"],
        f"{role} receipt identity drifted")
    return path, common.load_json(path)


def _event_matches(event: dict, expected: dict) -> bool:
    keys = ("address", "instruction_pc", "frame", "cycle", "width")
    return all(event.get(key) == expected[key] for key in keys) and \
        event.get("value") == expected["old"] and \
        event.get("new_value") == expected["new"]


def _entry_matches(event: dict, expected: dict) -> bool:
    return event.get("type") == "entry" and all(
        event.get(key) == expected[key]
        for key in ("function", "caller", "frame", "cycle"))


def _validate_identity(document: dict) -> None:
    debugger = CONFIGURATION["debugger"]
    capabilities = document.get("capabilities") or {}
    _require(
        (capabilities.get("api") or {}).get("version") ==
        debugger["api_version"] and
        (capabilities.get("api") or {}).get("schema_version") ==
        debugger["schema_version"] and
        (capabilities.get("binary") or {}).get("sha256") ==
        debugger["binary_sha256"] and
        (capabilities.get("source") or {}).get("revision") ==
        debugger["source_revision"] and
        (capabilities.get("source") or {}).get("dirty_state_hash") ==
        debugger["source_dirty_state_hash"],
        "debugger capability identity drifted")
    media = CONFIGURATION["media"]
    mounted = document.get("mounted_media") or {}
    _require(
        mounted.get("game_serial") == media["serial"] and
        mounted.get("verified_cue_sha256") == media["cue_sha256"] and
        mounted.get("verified_track_sha256") == media["bin_sha256"],
        "mounted pristine media identity drifted")
    fixture = document["fixtures"]["movie"]
    wanted_fixture = CONFIGURATION["fixture"]
    _require(
        fixture.get("sha256") == wanted_fixture["sha256"] and
        fixture.get("bytes") == wanted_fixture["bytes"],
        "movie fixture identity drifted")
    path = OPERATOR_ROOT / wanted_fixture["path"]
    _require(
        path.is_file() and path.stat().st_size == wanted_fixture["bytes"] and
        common.sha256(path) == wanted_fixture["sha256"],
        "centrally declared movie fixture drifted")
    isolated = document.get("isolated_instance") or {}
    profile = CONFIGURATION["profile"]
    _require(
        isolated.get("config_dir") == profile["config_dir"] and
        isolated.get("port") == profile["port"] and
        isolated.get("host") == "127.0.0.1" and
        isolated.get("profile_recreated") is True and
        isolated.get("token_retained") is False,
        "isolated debugger profile drifted")


def _validate_localization(document: dict) -> dict:
    expected = CONFIGURATION["expected"]["localization"]
    localization = document.get("localization") or {}
    queries = localization.get("queries") or []
    observed_targets = [
        [row.get("target_frame"), row.get("contains_call")]
        for row in queries]
    _require(
        localization.get("last_absent_target") ==
        expected["last_absent_target"] and
        localization.get("first_present_target") ==
        expected["first_present_target"] and
        observed_targets == expected["targets"],
        "binary localization boundary or query order drifted")
    for row in queries:
        trace = row.get("trace") or {}
        comparison = trace.get("comparison") or {}
        coverage = trace.get("coverage") or []
        movie = row.get("movie_status") or {}
        expected_hits = 1 if row["contains_call"] else 0
        _require(
            set(comparison) >= {
                "cycle_neutral", "same_cycle", "same_frame", "same_ram",
                "same_registers"} and all(comparison.values()) and
            len(coverage) == 1 and
            coverage[0].get("total_hits") == expected_hits and
            coverage[0].get("distinct_pc_count") == expected_hits and
            coverage[0].get("truncated") is False and
            movie.get("playback_index") == row["target_frame"] and
            movie.get("reproducible") is True and
            movie.get("truncated") is False,
            f"localization query {row.get('target_frame')} is not neutral")
    return {
        "query_count": len(queries),
        "last_absent_target": expected["last_absent_target"],
        "first_present_target": expected["first_present_target"],
        "all_internal_comparisons_cycle_neutral": True,
        "all_coverage_untruncated": True,
    }


def _validate_trace_counts(branch: dict, role: str) -> dict:
    traces = branch.get("traces") or {}
    expected = CONFIGURATION["expected"]["trace_counts"][role]
    observed = {
        "functions": (traces.get("functions") or {}).get("total"),
        "execution": (traces.get("execution") or {}).get("total"),
    }
    _require(
        (traces.get("functions") or {}).get("truncated") is False and
        (traces.get("execution") or {}).get("truncated") is False,
        f"{role} function/execution trace truncated")
    for label, access in (traces.get("access") or {}).items():
        observed[label] = access.get("total")
        _require(
            access.get("truncated") is False and
            len(access.get("events") or []) == access.get("total"),
            f"{role} {label} access trace truncated or inconsistent")
    _require(observed == expected, f"{role} trace counts drifted")
    movie = branch.get("movie_status") or {}
    _require(
        movie.get("game_serial") == CONFIGURATION["media"]["serial"] and
        movie.get("playback_index") == 16181 and
        movie.get("reproducible") is True and
        movie.get("truncated") is False and
        (movie.get("start_state") or {}).get("from_boot") is True,
        f"{role} movie endpoint drifted")
    return observed


def _validate_cleanup(document: dict) -> dict:
    for scope in (document, document["positive"], document["neutral"]):
        _require(
            len(scope.get("cleanup") or []) == 10 and
            all(row.get("ok") is True for row in scope["cleanup"]),
            "debugger instrumentation cleanup drifted")
    result_path = EXTERNAL_ROOT / _spec("result")["relative_path"]
    _path, cleanup = _receipt("cleanup")
    profile = CONFIGURATION["profile"]
    _require(
        cleanup.get("schema") == "abl-phase4-owned-pid-cleanup/1" and
        cleanup.get("config_dir") == profile["config_dir"] and
        cleanup.get("port") == profile["port"] and
        cleanup.get("pid") == profile["owned_pid"] and
        cleanup.get("owned_pid_stopped") is True and
        cleanup.get("token_retained_in_result") is False and
        cleanup.get("result_path") == str(result_path) and
        cleanup.get("result_sha256") == common.sha256(result_path) and
        cleanup.get("result_bytes") == result_path.stat().st_size,
        "owned-PID cleanup receipt drifted")
    return {
        "debugger_cleanup_actions": 30,
        "owned_pid": profile["owned_pid"],
        "owned_pid_stopped": True,
        "token_retained_in_result": False,
    }


def validate_result(document: dict, *, verify_identity: bool = True) -> dict:
    _require(
        document.get("schema") ==
        "abl-phase4-fmv-levelb-first-call-live/1",
        "live receipt schema drifted")
    if verify_identity:
        _validate_identity(document)
    for scope in (document, document["positive"], document["neutral"]):
        _require(
            len(scope.get("cleanup") or []) == 10 and
            all(row.get("ok") is True for row in scope["cleanup"]),
            "debugger instrumentation cleanup drifted")
    localization = _validate_localization(document)
    positive = document.get("positive") or {}
    neutral = document.get("neutral") or {}
    positive_counts = _validate_trace_counts(positive, "positive")
    neutral_counts = _validate_trace_counts(neutral, "neutral")

    first_expected = CONFIGURATION["expected"]["first_call"]
    first = positive.get("first_call") or {}
    first_status = first.get("status") or {}
    first_regs = first.get("registers") or {}
    _require(
        first_status.get("frame") == first_expected["frame"] and
        first_status.get("cycle") == first_expected["cycle"] and
        first_status.get("pc") == first_expected["pc"] and
        all(first_regs.get(key) == first_expected[key]
            for key in ("a0", "a1", "s0", "ra", "sp")),
        "exact pre-delay completed-Level-B call drifted")

    loader_expected = CONFIGURATION["expected"]["loader_entry"]
    loader = positive.get("loader_entry") or {}
    loader_status = loader.get("status") or {}
    loader_regs = loader.get("registers") or {}
    _require(
        loader_status.get("frame") == loader_expected["frame"] and
        loader_status.get("cycle") == loader_expected["cycle"] and
        loader_status.get("pc") == loader_expected["pc"] and
        loader_regs.get("a0") == loader_expected["selector"] and
        loader_regs.get("a1") == loader_expected["mode"] and
        loader_regs.get("ra") == loader_expected["ra"] and
        loader_regs.get("sp") == loader_expected["sp"],
        "exact post-delay loader interface drifted")

    positive_access = positive["traces"]["access"]
    selected_expected = CONFIGURATION["expected"]["selected_limit"]
    completion_expected = CONFIGURATION["expected"]["completion"]
    selected_events = [
        row for row in positive_access["selected_frame_limit"]["events"]
        if _event_matches(row, selected_expected)]
    completion_events = [
        row for row in positive_access["completion_request"]["events"]
        if _event_matches(row, completion_expected)]
    limit_completion_events = [
        row for row in positive_access["completion_request"]["events"]
        if row.get("instruction_pc") ==
        completion_expected["unobserved_limit_writer"] and
        row.get("new_value") == 1]
    decoded_game_writes = [
        row for row in positive_access["decode_stop_latch"]["events"]
        if str(row.get("instruction_pc") or "").startswith("0x800b")]
    _require(
        len(selected_events) == 1 and len(completion_events) == 1 and
        not limit_completion_events and not decoded_game_writes,
        "Level-B limit/completion/stop-latch attribution drifted")

    functions = positive["traces"]["functions"]["events"]
    common = CONFIGURATION["expected"]["common_exit"]
    st_clear = [row for row in functions
                if _entry_matches(row, common["st_clear_ring"])]
    teardown = [row for row in functions
                if _entry_matches(row, common["callback_teardown"])]
    _require(
        len(st_clear) == len(teardown) == 1 and
        teardown[0].get("synthetic_unwind") is
        common["callback_teardown"]["synthetic_unwind"] and
        positive.get("elapsed_frames_to_common_callback") ==
        common["elapsed_frames_from_first_call"] and
        selected_events[0]["cycle"] < completion_events[0]["cycle"] <
        st_clear[0]["cycle"] < teardown[0]["cycle"],
        "ordered Level-B completion/teardown chain drifted")

    positive_exec = positive["traces"]["execution"]["events"]
    positive_loader_entries = [
        row for row in functions if row.get("type") == "entry" and
        row.get("function") == loader_expected["pc"] and
        row.get("caller") == first_expected["pc"]]
    neutral_functions = neutral["traces"]["functions"]["events"]
    neutral_loader_entries = [
        row for row in neutral_functions if row.get("type") == "entry" and
        row.get("function") == loader_expected["pc"]]
    neutral_levelb_entries = [
        row for row in neutral_loader_entries
        if row.get("caller") == first_expected["pc"]]
    neutral_limit = [
        row for row in
        neutral["traces"]["access"]["selected_frame_limit"]["events"]
        if row.get("instruction_pc") == selected_expected["instruction_pc"] and
        row.get("new_value") == selected_expected["new"]]
    expected_generic = CONFIGURATION["expected"][
        "neutral_generic_loader_entries"]
    observed_generic = [{
        "caller": row["caller"], "frame": row["frame"],
        "cycle": row["cycle"], "arguments": row["arguments"],
    } for row in neutral_loader_entries]
    _require(
        len(positive_exec) == 1 and
        positive_exec[0].get("pc") == first_expected["pc"] and
        len(positive_loader_entries) == 1 and
        not neutral["traces"]["execution"]["events"] and
        not neutral_levelb_entries and not neutral_limit and
        observed_generic == expected_generic,
        "same-window neutral Level-B control drifted")

    for derivative_name in ("original_derivative", "neutral_derivative"):
        derivative = document.get(derivative_name) or {}
        _require(
            derivative.get("transient_storage") ==
            "temporary /var/tmp directory removed before collector exit" and
            derivative.get("anchor") == "from_boot" and
            derivative.get("derived_frame_count") == 18230,
            f"{derivative_name} preservation boundary drifted")

    return {
        "localization": localization,
        "first_call": {
            "frame": first_expected["frame"],
            "cycle": first_expected["cycle"],
            "pc": first_expected["pc"],
            "pre_delay_arguments": {
                "a0": first_expected["a0"], "a1": first_expected["a1"],
                "progress_id_s0": first_expected["s0"],
            },
        },
        "loader_entry": {
            "frame": loader_expected["frame"],
            "cycle": loader_expected["cycle"],
            "pc": loader_expected["pc"],
            "selector": 11,
            "mode_signed": -1,
        },
        "selected_limit": dict(selected_expected),
        "completion": {
            **completion_expected,
            "limit_writer_observed": False,
        },
        "common_exit": {
            "st_clear_ring": dict(common["st_clear_ring"]),
            "callback_teardown": dict(common["callback_teardown"]),
            "elapsed_frames_from_first_call":
                common["elapsed_frames_from_first_call"],
            "ordered": True,
        },
        "positive_trace_counts": positive_counts,
        "neutral_trace_counts": neutral_counts,
        "neutral_control": {
            "completed_level_b_caller_events": 0,
            "completed_level_b_loader_entries": 0,
            "selected_limit_485_events": 0,
            "generic_loader_entries": observed_generic,
        },
        "decoded_stop_latch_game_writes": 0,
    }


def build() -> dict:
    result_path, document = _receipt("result")
    observation = validate_result(document)
    cleanup = _validate_cleanup(document)
    fixture = dict(CONFIGURATION["fixture"])
    receipt_rows = []
    for role in ("result", "cleanup"):
        spec = _spec(role)
        receipt_rows.append({
            "role": role,
            "absolute_path": str(EXTERNAL_ROOT / spec["relative_path"]),
            "sha256": spec["sha256"],
            "bytes": spec["bytes"],
        })
    record_counts = {
        "localization_queries": observation["localization"]["query_count"],
        "localization_coverage_ranges":
            observation["localization"]["query_count"],
        "positive_function_events":
            observation["positive_trace_counts"]["functions"],
        "positive_execution_events":
            observation["positive_trace_counts"]["execution"],
        "positive_access_events": sum(
            value for key, value in
            observation["positive_trace_counts"].items()
            if key not in {"functions", "execution"}),
        "neutral_function_events":
            observation["neutral_trace_counts"]["functions"],
        "neutral_execution_events":
            observation["neutral_trace_counts"]["execution"],
        "neutral_access_events": sum(
            value for key, value in
            observation["neutral_trace_counts"].items()
            if key not in {"functions", "execution"}),
        "debugger_cleanup_actions": cleanup["debugger_cleanup_actions"],
    }
    return {
        "_comment": (
            "Tracked Level-B lifecycle summary only. Raw receipts, fixture, "
            "transient derivative and disc bytes remain external."),
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "external_receipts": receipt_rows,
        "fixture": fixture,
        "media": dict(CONFIGURATION["media"]),
        "debugger": dict(CONFIGURATION["debugger"]),
        "profile": {**CONFIGURATION["profile"],
                    "token_retained_in_result": False},
        "method": {
            "offline_source": "fmv-lifecycle-v2 index lacks this movie",
            "static_narrowing":
                "0x8005031C caller, level-B table and player xrefs",
            "live_fallback": document["method"]["fallback_reason"],
            "localization":
                "12 internally controlled passive exact-PC coverage queries",
            "causal_window":
                "last-absent reset plus 1,800 bounded instrumented frames",
        },
        "observation": observation,
        "record_counts": record_counts,
        "falsified_hypotheses": [
            (
                "The natural selector-11 stream completes through selected-"
                "limit writer 0x800B6B48. It instead publishes completion "
                "through frame-order-regression writer 0x800B6B24."),
            (
                "The timing-matched all-neutral branch executes no generic "
                "fmv_bin_load call. It executes two frontend/attract loader "
                "uses, while still excluding the completed-Level-B route."),
        ],
        "retained_low_level_facts": [
            (
                "The first cumulative passive target containing 0x8005031C is "
                "movie frame 14382; all 12 internal comparisons are RAM, "
                "register, cycle and frame neutral and untruncated."),
            (
                "The pre-delay caller has progress ID one and a0/a1 zero; 14 "
                "cycles later the exact loader boundary has selector 11 and "
                "mode -1. Limit 485, completion request, StClearRing and "
                "balanced callback teardown then occur in strict order."),
            (
                "The same-window all-neutral derivative has no completed-"
                "Level-B caller, caller-owned loader entry or limit-485 "
                "publication; its two different generic loader entries are "
                "retained as divergent frontend behavior."),
        ],
        "claim_boundary": {
            "classification":
                "natural_level_b_interface_and_lifecycle_control",
            "dimension_promoted": False,
            "debt_reduced": [
                "exact first completed-Level-B caller boundary",
                "selector-11/mode-minus-one loader interface",
                "limit-485 publication and completion writer choice",
                "common balanced teardown for one natural Level-B stream",
            ],
            "not_claimed": [
                "other Level-B IDs or level transitions",
                "alternate, advert or movie-viewer playback",
                "pause, repeat, decode or CD-failure behavior",
                "campaign breadth or subsystem-wide lifecycle closure",
            ],
            "next_method": (
                "Reuse the static selector/manifest frontier to select one "
                "existing alternate, advert or viewer recording before any "
                "new live replay; keep pause/error policy separate."),
        },
        "source_dependencies": {
            "tools/phase4_fmv_levelb_first_call.py":
                common.sha256(Path(__file__)),
            "tools/phase4_fmv_levelb_first_call_live.py":
                common.sha256(
                    common.ROOT /
                    "tools/phase4_fmv_levelb_first_call_live.py"),
            str(CONFIG_PATH.relative_to(common.ROOT)):
                common.sha256(CONFIG_PATH),
            "analysis/phase4_fmv_static_owners.json":
                common.sha256(
                    common.ROOT / "analysis/phase4_fmv_static_owners.json"),
            "analysis/phase4_fmv_levelb_reachability.json":
                common.sha256(
                    common.ROOT /
                    "analysis/phase4_fmv_levelb_reachability.json"),
        },
        "valid": True,
        "errors": [],
        "raw_external_bytes_committed": False,
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
            raise SystemExit("phase4 Level-B first-call artifact is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: natural Level-B caller/selector/completion/teardown banked; "
        "no dimension promoted", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
