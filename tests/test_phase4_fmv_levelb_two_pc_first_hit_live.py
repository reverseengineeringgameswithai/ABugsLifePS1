from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_two_pc_first_hit as boundary  # noqa: E402
import phase4_fmv_levelb_two_pc_first_hit_live as live  # noqa: E402
import phase4_duckstation_two_pc_first_hit as adapter  # noqa: E402
import phase4_method_metrics as metrics  # noqa: E402


RUNTIME = ROOT / "config/phase4_fmv_levelb_two_pc_first_hit_runtime.yaml"


def test_runtime_is_closed_and_matches_the_predeclared_64_frame_receipt():
    runtime = live.load_runtime(RUNTIME)
    plan = live.first_hit_plan(runtime)
    assert runtime["observer_plan"]["direct_command_plan"] == plan
    assert runtime["execution"]["capture_window"] == {
        "clock": "emulator_frame",
        "start": 15792,
        "stop": 15856,
        "stop_inclusive": False,
    }
    assert plan["execution_limit"]["max_frame_delta"] == 64
    assert runtime["observer_plan"]["result_limits"] == \
        adapter.observer_result_limits(plan)
    metrics._validate_observer_plan(runtime["observer_plan"], "observer")


def test_atomic_request_is_one_uninstrumented_cold_boot_anchor():
    runtime = live.load_runtime(RUNTIME)
    request = live._batch_request(runtime)
    assert request["continue_on_error"] is False
    [job] = request["jobs"]
    assert job["recipe"] == "bootAndRun"
    assert job["instrumentation"] == []
    assert job["run"] == {"frames": 15791}
    assert job["movie"] == {
        "path": str((ROOT / "movies/100% Runs/LEVEL01.movie.json").resolve()),
    }
    assert Path(job["movie"]["path"]).is_absolute()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda doc: doc["atomic_anchor"].update(target_frame=15791),
            "atomic anchor",
        ),
        (
            lambda doc: doc["execution"]["capture_window"].update(stop=15857),
            "64-frame window",
        ),
        (
            lambda doc: doc["observer_plan"]["operations"][1]["args"].update(
                address=0x800502A0),
            "observer plan",
        ),
        (
            lambda doc: doc["variant"].update(control_role="negative"),
            "variant",
        ),
    ],
)
def test_runtime_mutations_fail_closed(tmp_path, mutation, message):
    changed = copy.deepcopy(live.yaml.safe_load(RUNTIME.read_text()))
    mutation(changed)
    path = tmp_path / "runtime.yaml"
    path.write_text(live.yaml.safe_dump(changed, sort_keys=False))
    with pytest.raises(ValueError, match=message):
        live.load_runtime(path)


def test_emitter_retains_adapter_derived_command_bodies(tmp_path):
    runtime = live.load_runtime(RUNTIME)
    plan = live.first_hit_plan(runtime)
    session_id = "synthetic-owned-two-pc-session"
    direct = adapter.execute_first_hit(
        boundary.SyntheticRpc(0),
        plan,
        session_id,
        plan["identity_join"],
        sleep=lambda _seconds: None,
    )
    direct["outcome"] = "survived"
    methods = set(adapter.REQUIRED_METHODS) | \
        metrics.REQUIRED_LIVE_COMMAND_METHODS | \
        metrics.REQUIRED_ATOMIC_COMMAND_METHODS
    method_schemas = {
        method: hashlib.sha256(method.encode()).hexdigest()
        for method in methods
    }
    document = {
        "schema": live.RESULT_SCHEMA,
        "generated": "2026-07-29T00:00:00+00:00",
        "complete": True,
        "errors": [],
        "port": 31337,
        "owned_pid": 4242,
        "config_dir": str(tmp_path / "config"),
        "client_sha256": "1" * 64,
        "runner_sha256": "2" * 64,
        "runtime_sha256": None,
        "identity_results": {
            "debugger.capabilities": {"api": {"version": "2.1.0"}},
            "debugger.status": {"game_serial": "SCUS-94288"},
            "emulator.getMediaInfo": {"serial": "SCUS-94288"},
        },
        "normalized_identity": {
            "source_sha256": "3" * 64,
            "executable_sha256": plan["identity_join"]["binary_sha256"],
            "api_surface_sha256": "4" * 64,
            "method_schemas": method_schemas,
        },
        "batch_request": live._batch_request(runtime),
        "batch_id": "batch-two-pc",
        "batch_submission": {
            "batch_id": "batch-two-pc",
            "job_ids": ["levelb_two_pc_first_hit_anchor"],
        },
        "batch_polls": [{
            "state": "completed",
            "jobs": [{"id": "levelb_two_pc_first_hit_anchor"}],
        }],
        "result": {
            "jobs": [{
                "id": "levelb_two_pc_first_hit_anchor",
                "state": "completed",
                "result": {
                    "run": {"frames_advanced": 15791},
                    "status": {"frame": 15792},
                },
            }],
        },
        "server_session_id": session_id,
        "direct_result": direct,
    }
    cleanup = {
        "schema": "abl-phase4-owned-pid-cleanup/1",
        "complete": True,
        "errors": [],
        "owned_pid": 4242,
        "owned_pid_stopped": True,
        "config_dir": str(tmp_path / "config"),
        "actions": [
            {"sequence": 0, "kind": "stop_owned_pid", "pid": 4242},
            {"sequence": 1, "kind": "confirm_pid_stopped", "pid": 4242},
        ],
    }
    prelude = tmp_path / "prelude.json"
    prelude.write_text("{}\n")
    runtime_copy = tmp_path / RUNTIME.name
    runtime_copy.write_bytes(RUNTIME.read_bytes())
    receipt_path = live.emit_receipt(
        runtime,
        runtime_copy,
        document,
        tmp_path / "iteration-1-receipts" / "live" /
        runtime["variant"]["receipt_id"],
        tmp_path,
        cleanup,
        {"complete": True},
        prelude,
    )
    receipt = json.loads(receipt_path.read_text())
    assert receipt["schema"] == "abl-phase4-live-run-receipt/2"
    assert receipt["evidence"]["adapter_source"]["path"] == \
        "tools/phase4_duckstation_two_pc_first_hit.py"
    events_path = tmp_path / receipt["evidence"]["command_events"]["path"]
    events = json.loads(events_path.read_text())
    assert [row["method"] for row in events["events"][-13:]] == [
        row["method"] for row in direct["command_events"]["events"]
    ]
    metrics._validate_result_doc(
        events, "abl-phase4-live-command-events/1", "events")
    pages_path = tmp_path / receipt["evidence"]["pagination"]["path"]
    pages = json.loads(pages_path.read_text())
    assert pages["pages"] == [] and pages["pages_complete"] is True
