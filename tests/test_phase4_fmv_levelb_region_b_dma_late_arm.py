from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_region_b_dma_late_arm as late_arm  # noqa: E402
import phase4_duckstation_late_batch as batch  # noqa: E402
import phase4_method_metrics as metrics  # noqa: E402


def _plan(role: str) -> tuple[dict, dict]:
    spec = late_arm.CONFIGURATION["plans"][role]
    return spec, late_arm.common.load_yaml(ROOT / spec["path"])


def test_late_arm_preflight_is_banked_without_live_or_dimension_claim():
    document = late_arm.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["escalation"]["state"] == "planned"
    assert document["escalation"]["higher_priority_offline_ready_rows"] == []
    assert document["falsifier"]["outcome"] == "not_evaluated"
    assert document["claim_boundary"]["method_preflight_complete"] is True
    assert document["claim_boundary"]["live_executed"] is False
    assert document["claim_boundary"]["first_region_b_dma_identified"] is False
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["next_lane"] == "live"
    assert document["record_counts"] == {
        "offline_queries_executed_this_iteration": 0,
        "offline_receipts_reused": 1,
        "live_receipts_executed_this_iteration": 0,
        "planned_live_receipts": 2,
        "promoted_dimensions": 0,
    }
    assert late_arm.common.sha256(
        ROOT / "tools/phase4_duckstation_batch.py"
    ) == "e94ec290a489484587b50fe72a472dbfa8578a7f17dcaf32f57af2efcf8bb375"
    assert document["inputs"]["adapter_sha256"] == late_arm.common.sha256(
        ROOT / "tools/phase4_duckstation_late_batch.py"
    )
    ledger = late_arm.common.load_json(late_arm.ESCALATIONS)
    [entry] = [
        row for row in ledger["entries"]
        if row["id"] == late_arm.CONFIGURATION["escalation_id"]
    ]
    assert "tools/phase4_duckstation_late_batch.py" in (
        entry["live_experiment"]
    )
    assert late_arm.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


def test_plans_use_provisioned_movie_and_exact_finite_windows():
    document = late_arm.build()
    passive = document["plans"]["passive"]
    precise = document["plans"]["precise"]
    assert passive["provisioned_movie"] == "movies/100% Runs/LEVEL01.movie.json"
    assert passive["prelude"] == {
        "kind": "emulator_advance", "start": 1, "stop": 15720,
    }
    assert passive["capture_window"] == {
        "clock": "emulator_frame", "start": 15720, "stop": 16120,
        "stop_inclusive": False,
    }
    assert precise["prelude"] == {
        "kind": "emulator_advance", "start": 1, "stop": 15740,
    }
    assert precise["capture_window"] == {
        "clock": "emulator_frame", "start": 15740, "stop": 16080,
        "stop_inclusive": False,
    }
    assert precise["observer_methods"] == ["transferLog.start"]
    for role in ("passive", "precise"):
        _spec, plan = _plan(role)
        assert {
            job["movie"]["path"] for job in plan["jobs"]
        } == {"movies/100% Runs/LEVEL01.movie.json"}
        execution = batch._execution_plan(plan)
        assert {
            Path(job["movie"]["path"]) for job in execution["jobs"]
        } == {ROOT / "movies/100% Runs/LEVEL01.movie.json"}


def test_late_transfer_plan_retains_complete_atomic_pagination_and_identity():
    _, passive = _plan("passive")
    _, precise = _plan("precise")
    assert batch.validate_plan(passive) == []
    assert batch.validate_plan(precise) == []
    assert all(
        job["capture"]["transfer_pagination"]
        == {"page_size": 10000, "max_pages": 10}
        for job in precise["jobs"]
    )

    stale = copy.deepcopy(precise)
    stale["expected_debugger"]["binary_sha256"] = "0" * 64
    errors = batch.validate_plan(stale)
    assert any(
        "differs from the candidate-HEAD RPC manifest" in error
        for error in errors
    )
    assert any(
        "settings binary differs from expected debugger" in error
        for error in errors
    )
    assert metrics.LIVE_ADAPTER_PATH.fullmatch(
        "tools/phase4_duckstation_late_batch.py"
    )


@pytest.mark.parametrize("role", ["passive", "precise"])
def test_late_adapter_cli_validates_each_plan_without_recursive_monkeypatch(role):
    spec, _plan_document = _plan(role)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/phase4_duckstation_late_batch.py"),
            "--plan",
            str(ROOT / spec["path"]),
            "--validate-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS: 2 atomic jobs and 1 controls" in result.stdout


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda plan: plan["jobs"][0].pop("staged_prelude"),
            "nonzero cold-boot capture requires",
        ),
        (
            lambda plan: plan["jobs"][0]["staged_prelude"].update(
                kind="movie_advance"
            ),
            "only for loadStateAndRun",
        ),
        (
            lambda plan: plan["jobs"][0]["staged_prelude"].update(
                target_frame=15739
            ),
            "capture start differs",
        ),
        (
            lambda plan: plan["jobs"][0]["run"].update(frames=339),
            "do not exactly cover",
        ),
    ],
)
def test_precise_plan_mutations_fail_closed(mutation, message):
    spec, plan = _plan("precise")
    mutation(plan)
    with pytest.raises(ValueError, match=message):
        late_arm._validate_plan_document("precise", spec, plan)


def test_emulator_prelude_raw_counters_join_full_replay_to_late_observer():
    document = {
        "result": {
            "state": "completed",
            "jobs": [{
                "id": "native",
                "state": "completed",
                "result": {
                    "staged_prelude": {
                        "frames_advanced": 15739,
                        "start_frame": 1,
                        "target_frame": 15740,
                        "status": {"frame": 15740},
                    },
                    "run": {"frames_advanced": 340},
                    "status": {"frame": 16080},
                },
            }],
        },
    }
    execution = {
        "bound": {
            "clock": "emulator_frame", "start": 0, "stop": 16080,
            "stop_inclusive": False,
        },
        "capture_window": {
            "clock": "emulator_frame", "start": 15740, "stop": 16080,
            "stop_inclusive": False,
        },
    }
    raw = batch._raw_result_document(document, "owned-session", execution)
    assert raw["results"][0]["replay_start"] == 1
    assert raw["results"][0]["observer_start"] == 15740
    assert raw["results"][0]["observer_stop"] == 16080
    assert raw["counters"]["replay_frames"] == 16079
    assert raw["counters"]["observer_frames"] == 340

    changed = copy.deepcopy(document)
    changed["result"]["jobs"][0]["result"]["staged_prelude"][
        "target_frame"
    ] = 15739
    with pytest.raises(RuntimeError, match="not contiguous"):
        batch._raw_result_document(
            changed, "owned-session", execution
        )


def test_adapter_accepts_only_hash_pinned_provisioned_fixture_alias():
    entries = late_arm.common.load_json(
        late_arm.common.FIXTURE_SET_PATH
    )["entries"]
    provisioned = ROOT / "movies/100% Runs/LEVEL01.movie.json"
    rel, pin = batch._central_fixture(
        str(provisioned), entries, Path.home() / "Downloads/ABL"
    )
    assert rel == "movies/100% Runs/LEVEL01.movie.json"
    assert pin["sha256"] == (
        "ece62d4e6f92b887b0500dd8ac3bec48f3638ad5d9858cda7d5b0afb3a8d2602"
    )
