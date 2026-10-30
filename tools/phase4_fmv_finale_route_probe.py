#!/usr/bin/env python3
"""Validate and bank the rejected LEVEL15 finale-route fixture lead."""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_fmv_finale_route_probe.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_finale_route_probe.json"
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
        (capabilities.get("source") or {}).get("dirty") is True and
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
    wanted = CONFIGURATION["fixture"]
    _require(
        fixture.get("sha256") == wanted["sha256"] and
        fixture.get("bytes") == wanted["bytes"] and
        fixture.get("frame_count") == wanted["frame_count"] and
        fixture.get("anchor") == wanted["anchor"],
        "movie fixture identity drifted")
    path = OPERATOR_ROOT / wanted["path"]
    _require(
        path.is_file() and path.stat().st_size == wanted["bytes"] and
        common.sha256(path) == wanted["sha256"],
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


def _validate_trace(document: dict, name: str, endpoint: dict) -> dict:
    expected = CONFIGURATION["expected"]["checks"][name]
    row = document.get(name) or {}
    trace = row.get("trace") or {}
    comparison = trace.get("comparison") or {}
    coverage_rows = trace.get("coverage") or []
    _require(
        row.get("target_frame") == expected["target_frame"] and
        row.get("complete_consumption") is
        expected["complete_consumption"] and
        row.get("register_filter") == expected["register_filter"],
        f"{name}: target/consumption/filter drifted")
    _require(
        set(comparison) >= {
            "cycle_neutral", "same_cycle", "same_frame", "same_ram",
            "same_registers"} and all(comparison.values()),
        f"{name}: cycle-neutral comparison drifted")
    _require(
        len(coverage_rows) == 1,
        f"{name}: coverage range count drifted")
    coverage = coverage_rows[0].get("coverage") or {}
    pcs = coverage.get("pcs") or []
    _require(
        coverage.get("total_hits") == expected["total_hits"] and
        coverage.get("truncated") is False and
        (pcs[0] if pcs else None) == expected["pc"] and
        coverage.get("distinct_pc_count") == (1 if pcs else 0),
        f"{name}: coverage result drifted")
    _require(
        trace.get("instrumented") == endpoint and
        trace.get("control") == endpoint,
        f"{name}: endpoint signature drifted")
    movie = row.get("movie_status") or {}
    movie_identity_valid = (
        movie.get("truncated") is False and
        movie.get("frame_count") == CONFIGURATION["fixture"]["frame_count"] and
        (movie.get("start_state") or {}).get("from_boot") is True)
    if expected["complete_consumption"]:
        _require(
            expected["target_frame"] ==
            CONFIGURATION["fixture"]["frame_count"] and
            row.get("target_frame") == movie.get("frame_count") and
            movie_identity_valid and
            movie.get("playing") is False and
            movie.get("playback_index") == 0 and
            movie.get("reproducible") is False and
            trace.get("target_frame") == movie.get("frame_count") and
            (trace.get("control") or {}).get("movie_frame") == 0 and
            (trace.get("instrumented") or {}).get("movie_frame") == 0,
            f"{name}: complete movie consumption drifted")
    else:
        _require(
            movie_identity_valid and
            movie.get("playing") is True and
            movie.get("reproducible") is True and
            movie.get("playback_index") == expected["target_frame"],
            f"{name}: recorded boot anchor drifted")
    return {
        "target_frame": expected["target_frame"],
        "complete_consumption": expected["complete_consumption"],
        "register_filter": expected["register_filter"],
        "total_hits": expected["total_hits"],
        "pc": expected["pc"],
        "cycle_neutral": True,
        "untruncated": True,
    }


def _validate_cleanup(document: dict) -> dict:
    cleanup = document.get("cleanup") or []
    _require(
        len(cleanup) == 10 and
        all(row.get("ok") is True for row in cleanup),
        "debugger instrumentation cleanup drifted")
    result_path = EXTERNAL_ROOT / _spec("result")["relative_path"]
    _path, receipt = _receipt("cleanup")
    profile = CONFIGURATION["profile"]
    evidence = receipt.get("evidence_result") or {}
    _require(
        receipt.get("schema") == "abl-phase4-owned-pid-cleanup/1" and
        receipt.get("config_dir") == profile["config_dir"] and
        receipt.get("owned_pid") == profile["owned_pid"] and
        receipt.get("instance_pid_absent_after_stop") is True and
        receipt.get("owned_pid_alive_after_stop") is False and
        receipt.get("runtime_executable_sha256") ==
        CONFIGURATION["debugger"]["binary_sha256"] and
        receipt.get("credentials_retained") is False and
        evidence.get("absolute_path") == str(result_path) and
        evidence.get("sha256") == common.sha256(result_path) and
        evidence.get("bytes") == result_path.stat().st_size,
        "owned-PID cleanup receipt drifted")
    return {
        "debugger_cleanup_actions": len(cleanup),
        "owned_pid": profile["owned_pid"],
        "owned_pid_stopped": True,
        "credentials_retained": False,
    }


def validate_result(document: dict, *, verify_identity: bool = True) -> dict:
    _require(
        document.get("schema") ==
        "abl-phase4-fmv-finale-route-probe-live/1",
        "live receipt schema drifted")
    if verify_identity:
        _validate_identity(document)
    early_endpoint = CONFIGURATION["expected"]["early_endpoint"]
    final_endpoint = CONFIGURATION["expected"]["final_endpoint"]
    checks = {
        "early_bare_pc_alias": _validate_trace(
            document, "early_bare_pc_alias", early_endpoint),
        "early_selector_filtered_control": _validate_trace(
            document, "early_selector_filtered_control", early_endpoint),
        "full_finale_c_selector_filtered": _validate_trace(
            document, "full_finale_c_selector_filtered", final_endpoint),
        "full_finale_d_bare_pc": _validate_trace(
            document, "full_finale_d_bare_pc", final_endpoint),
    }
    _require(
        checks["early_bare_pc_alias"]["total_hits"] > 0 and
        checks["early_selector_filtered_control"]["total_hits"] == 0,
        "bare-PC alias control no longer excludes the resident selector")
    _require(
        checks["full_finale_c_selector_filtered"]["total_hits"] == 0 and
        checks["full_finale_d_bare_pc"]["total_hits"] == 0,
        "LEVEL15 recording now reaches a resident finale route")
    return {
        "checks": checks,
        "early_endpoint": dict(early_endpoint),
        "final_endpoint": dict(final_endpoint),
        "complete_consumption": True,
        "consumed_frame_count": CONFIGURATION["fixture"]["frame_count"],
        "final_consumed_input_index":
            CONFIGURATION["fixture"]["frame_count"] - 1,
        "bare_pc_alias_hits": 326,
        "resident_finale_c_hits": 0,
        "resident_finale_d_hits": 0,
    }


def build() -> dict:
    _result_path, document = _receipt("result")
    observation = validate_result(document)
    cleanup = _validate_cleanup(document)
    receipts = [{
        "role": role,
        "absolute_path": str(EXTERNAL_ROOT / _spec(role)["relative_path"]),
        "sha256": _spec(role)["sha256"],
        "bytes": _spec(role)["bytes"],
    } for role in ("result", "cleanup")]
    return {
        "_comment": (
            "Tracked negative fixture classification only. Raw receipt, "
            "recording and retail media remain external."),
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "external_receipts": receipts,
        "fixture": dict(CONFIGURATION["fixture"]),
        "media": dict(CONFIGURATION["media"]),
        "debugger": dict(CONFIGURATION["debugger"]),
        "profile": {
            **CONFIGURATION["profile"],
            "owned_pid_stopped": True,
            "token_retained_in_result": False,
        },
        "method": dict(document["method"]),
        "observation": observation,
        "record_counts": {
            "cycle_neutral_queries": 4,
            "coverage_ranges": 4,
            "complete_consumption_queries": 2,
            "bare_pc_alias_hits": observation["bare_pc_alias_hits"],
            "resident_finale_route_hits": 0,
            "debugger_cleanup_actions":
                cleanup["debugger_cleanup_actions"],
        },
        "falsified_hypotheses": [
            (
                "The filename and retained scene-15-to-frontend timeline "
                "identify a natural LEV15C/LEV15D finale replay. Exact "
                "resident-owner coverage through complete consumption of all "
                "33,268 samples proves that neither caller executes."),
            (
                "Bare cumulative coverage at 0x80050284 is sufficient during "
                "a from-boot replay. It records 326 address-reuse hits before "
                "frame 1000, all excluded by the required a0=40 predicate."),
        ],
        "claim_boundary": {
            "classification": "rejected_finale_recording_lead",
            "dimension_promoted": False,
            "debt_reduced": [
                "rejected one incorrect alternate/finale recording lead",
                "added an exact owner-register guard for cold-boot PC reuse",
            ],
            "not_claimed": [
                "LEV15C or LEV15D reachability",
                "alternate, advert or movie-viewer playback",
                "any selector limit, completion or teardown event",
                "lifecycle, breadth or original-interface promotion",
            ],
            "next_method": (
                "Change fixture-selection method: exhaust centrally declared "
                "boss/menu leads by declared anchor and faithful input span; "
                "if none reaches an exact owner, predeclare a bounded "
                "synthetic selector lifecycle control without treating it as "
                "natural route ownership."),
        },
        "source_dependencies": {
            "tools/phase4_fmv_finale_route_probe.py":
                common.sha256(Path(__file__)),
            "tools/phase4_fmv_finale_route_probe_live.py":
                common.sha256(
                    common.ROOT /
                    "tools/phase4_fmv_finale_route_probe_live.py"),
            str(CONFIG_PATH.relative_to(common.ROOT)):
                common.sha256(CONFIG_PATH),
            "analysis/phase4_fmv_static_owners.json":
                common.sha256(
                    common.ROOT / "analysis/phase4_fmv_static_owners.json"),
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
            raise SystemExit("phase4 finale-route probe artifact is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: LEVEL15 rejected as a finale-route fixture; "
        "no dimension promoted", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
