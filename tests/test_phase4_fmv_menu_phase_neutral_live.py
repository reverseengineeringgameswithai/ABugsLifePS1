from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_menu_phase_neutral_live as live  # noqa: E402
import phase4_method_metrics as metrics  # noqa: E402


PLAN_NAMES = (
    "phase4_fmv_menu_v1_phase_neutral_passive_batch.yaml",
    "phase4_fmv_menu_v1_phase_neutral_owner_batch.yaml",
    "phase4_fmv_menu_v2_phase_neutral_passive_batch.yaml",
    "phase4_fmv_menu_v2_phase_neutral_owner_batch.yaml",
)


def _plans() -> dict[str, dict]:
    return {
        name: yaml.safe_load((ROOT / "config" / name).read_text())
        for name in PLAN_NAMES
    }


def _trace_result(plan: dict) -> dict:
    params = live.direct_rpc_params(plan)
    coverage = []
    for index, row in enumerate(params["ranges"]):
        hits = 1 if row["start"] in live.BOOT_PCS else 0
        pc = f"0x{row['start']:08x}"
        coverage.append({
            "range": {"start": pc, "end": pc},
            "label": row["label"],
            "coverage": {
                "watch_id": index + 1,
                "total_hits": hits,
                "distinct_pc_count": hits,
                "truncated": False,
                "pcs": [pc] if hits else [],
                "counts_by_pc": (
                    [{"pc": pc, "count": hits}] if hits else []),
            },
        })
    return {
        "target_frame": params["frame"],
        "trace_mode": "passive_cached_block_coverage",
        "configured_execution_mode": "Interpreter",
        "comparison_execution_mode": "CachedInterpreter",
        "control": {
            "cycle": 1234,
            "frame": params["frame"] + 1,
            "movie_frame": 0,
            "pc": "0x8004fea4",
            "ram_sha256": "a" * 64,
            "registers_sha256": "b" * 64,
            "sp": "0x801fffd0",
        },
        "instrumented": {
            "cycle": 1234,
            "frame": params["frame"] + 1,
            "movie_frame": 0,
            "pc": "0x8004fea4",
            "ram_sha256": "a" * 64,
            "registers_sha256": "b" * 64,
            "sp": "0x801fffd0",
        },
        "comparison": {
            "cycle_neutral": True,
            "same_ram": True,
            "same_registers": True,
            "same_cycle": True,
            "same_frame": True,
        },
        "coverage": coverage,
        "status": {"frame": params["frame"]},
    }


def test_four_plans_are_atomic_full_span_and_strictly_preluded():
    plans = _plans()
    assert all(
        live.validate_plan(plan, allow_executed=True) == []
        for plan in plans.values())
    for version, frame in (("v1", 7793), ("v2", 7362)):
        passive = plans[
            f"phase4_fmv_menu_{version}_phase_neutral_passive_batch.yaml"]
        precise = plans[
            f"phase4_fmv_menu_{version}_phase_neutral_owner_batch.yaml"]
        prior = passive["v2_receipt"]
        current = precise["v2_receipt"]
        assert prior["anchor"] == current["anchor"]
        assert prior["execution"]["capture_window"]["stop"] == frame + 2
        assert current["execution"]["capture_window"]["stop"] == frame + 1
        assert all(job["instrumentation"] == [] for job in precise["jobs"])
        params = live.direct_rpc_params(precise)
        assert params["frame"] == frame
        assert [row["start"] for row in params["ranges"]] == \
            list(live.TARGET_PCS)
        assert all(row["start"] == row["end"] for row in params["ranges"])


def test_plan_mutations_reject_split_observer_and_candidate_drift():
    plan = _plans()[
        "phase4_fmv_menu_v1_phase_neutral_owner_batch.yaml"]
    split = copy.deepcopy(plan)
    split["jobs"][0]["instrumentation"] = [{
        "method": "execTrace.addWatch", "params": {"pc": live.BOOT_PCS[0]},
    }]
    assert any(
        "must be uninstrumented" in error
        for error in live.validate_plan(split, allow_executed=True))

    missing = copy.deepcopy(plan)
    operation = missing["v2_receipt"]["observer_plan"]["operations"][0]
    operation["args"]["ranges"].pop()
    assert any(
        "exact nine singleton PCs" in error
        for error in live.validate_plan(missing, allow_executed=True))

    short = copy.deepcopy(plan)
    short["v2_receipt"]["observer_plan"]["operations"][0]["args"][
        "frame"] -= 1
    assert any(
        "full same-anchor movie span" in error
        for error in live.validate_plan(short, allow_executed=True))


def test_result_requires_three_boot_controls_six_zeros_and_native_neutrality():
    plan = _plans()[
        "phase4_fmv_menu_v1_phase_neutral_owner_batch.yaml"]
    result = _trace_result(plan)
    summary = live.validate_trace_result(result, 7793)
    assert all(summary["boot_hits"].values())
    assert set(summary["nonboot_hits"].values()) == {0}
    assert summary["cycle_neutral"] is True
    assert summary["falsifier"] == {"outcome": "survived", "reasons": []}

    nonboot = copy.deepcopy(result)
    nonboot["coverage"][3]["coverage"].update({
        "total_hits": 1,
        "distinct_pc_count": 1,
        "pcs": ["0x8004ffd4"],
        "counts_by_pc": [{"pc": "0x8004ffd4", "count": 1}],
    })
    summary = live.validate_trace_result(nonboot, 7793)
    assert summary["falsifier"] == {
        "outcome": "falsified",
        "reasons": ["nonboot_owner_hit"],
    }

    divergent = copy.deepcopy(result)
    divergent["instrumented"]["cycle"] += 1
    divergent["comparison"]["same_cycle"] = False
    divergent["comparison"]["cycle_neutral"] = False
    summary = live.validate_trace_result(divergent, 7793)
    assert summary["falsifier"] == {
        "outcome": "falsified",
        "reasons": ["native_endpoint_divergence"],
    }

    truncated = copy.deepcopy(result)
    truncated["coverage"][0]["coverage"]["truncated"] = True
    with pytest.raises(RuntimeError, match="coverage drifted"):
        live.validate_trace_result(truncated, 7793)


def test_receipt_command_schema_retains_closed_direct_observer_event():
    plan = _plans()[
        "phase4_fmv_menu_v1_phase_neutral_owner_batch.yaml"]
    result = _trace_result(plan)
    params = live.direct_rpc_params(plan)
    rows = [
        ("debugger.capabilities", {}, {"identity": "capabilities"}),
        ("debugger.status", {}, {"game_serial": "SCUS-94288"}),
        ("emulator.getMediaInfo", {}, {
            "serial": "SCUS-94288", "sha256": "1" * 64}),
        ("scenario.runBatch", {"plan_sha256": "2" * 64}, {
            "batch_id": "batch", "job_ids": ["a", "b"]}),
        ("scenario.getBatch", {
            "batch_id": "batch", "include_results": True}, {
            "batch_id": "batch", "status": "completed",
            "job_ids": ["a", "b"]}),
        ("movie.traceToFrame", params, result),
    ]
    document = {
        "schema": "abl-phase4-live-command-events/1",
        "complete": True,
        "errors": [],
        "events": [
            {
                "sequence": index,
                "server_session_id": "owned-session",
                "method": method,
                "params": method_params,
                "result": method_result,
                "result_sha256": hashlib.sha256(
                    metrics.canonical_bytes(method_result)).hexdigest(),
            }
            for index, (method, method_params, method_result) in enumerate(rows)
        ],
    }
    metrics._validate_result_doc(
        document, "abl-phase4-live-command-events/1", "events")

    mutated = copy.deepcopy(document)
    mutated["events"][-1]["result"]["comparison"]["same_ram"] = False
    mutated["events"][-1]["result_sha256"] = hashlib.sha256(
        metrics.canonical_bytes(mutated["events"][-1]["result"])).hexdigest()
    with pytest.raises(metrics.MetricsError, match="contradicts retained endpoints"):
        metrics._validate_result_doc(
            mutated, "abl-phase4-live-command-events/1", "events")

    coherent_divergence = copy.deepcopy(document)
    observed = coherent_divergence["events"][-1]["result"]
    observed["instrumented"]["cycle"] += 1
    observed["comparison"]["same_cycle"] = False
    observed["comparison"]["cycle_neutral"] = False
    coherent_divergence["events"][-1]["result_sha256"] = hashlib.sha256(
        metrics.canonical_bytes(observed)).hexdigest()
    metrics._validate_result_doc(
        coherent_divergence, "abl-phase4-live-command-events/1", "events")
