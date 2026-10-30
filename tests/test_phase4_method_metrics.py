import copy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from tools import phase4_method_metrics as metrics
from tools import phase4_method_legacy_live_index as legacy
from tools import phase4_method_reports as reports
from tools import phase4_duckstation_exact_pc_batch as exact_pc_adapter
from tools import phase4_fmv_levelb_region_b_dma_exact_pc_arm as exact_pc_arm
from tools import phase4_duckstation_two_pc_first_hit as two_pc_adapter
from tools import phase4_fmv_levelb_two_pc_first_hit as two_pc_boundary


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_method_contract_constants_are_closed_and_ordered():
    assert metrics.SCHEMA == "abl-phase4-method-metrics/2"
    assert metrics.TRIAL_SCHEMA == "abl-phase4-method-trial-root/1"
    assert metrics.SEMANTIC_SOURCE == (
        "src/main/**", "src_re/**", "symbols/**", "asm/**",
        "config/record_types.yaml", "config/semantic_state.yaml",
        "config/phase4_*.yaml", "analysis/mechanics_baseline.yaml",
    )
    assert "tools/phase4_*.py" in metrics.GENERATOR_GUARD
    assert "analysis/phase4_closure_debt.json" in metrics.JOINED_ONLY
    metrics.self_check()


def test_report_producer_matches_independent_fixed_command_contract():
    produced = {
        schema: tuple(
            (tuple(command), tuple(sorted(accepted)))
            for command, accepted in checks
        )
        for schema, checks in reports.fixed_report_commands().items()
    }
    assert produced == metrics.EXPECTED_REPORT_COMMANDS


def test_legacy_projection_ignores_only_regenerated_current_audit():
    raw = {
        "id": "P4-OLD",
        "state": "executed",
        "execution_result": {"media": {"bin_sha256": "1" * 64}},
        "derived_post_run_audit": {
            "queue_source_hashes": {
                "live_escalation_source_sha256": "2" * 64,
            },
        },
    }
    refreshed = json.loads(json.dumps(raw))
    refreshed["derived_post_run_audit"]["queue_source_hashes"][
        "live_escalation_source_sha256"] = "3" * 64
    assert legacy.source_entry_sha256(raw) == \
        legacy.source_entry_sha256(refreshed)
    assert legacy.source_projection(raw) == \
        metrics._legacy_source_projection(raw)

    tampered = json.loads(json.dumps(raw))
    tampered["execution_result"]["media"]["bin_sha256"] = "4" * 64
    assert legacy.source_entry_sha256(raw) != \
        legacy.source_entry_sha256(tampered)


def test_legacy_index_creation_metadata_is_checkout_stable():
    retained = json.loads(legacy.OUTPUT.read_text())
    assert legacy.INDEX_CREATED == "2026-07-26"
    assert legacy.build()["generated"] == legacy.INDEX_CREATED
    assert retained == legacy.build()
    assert retained["generated"] == legacy.INDEX_CREATED
    assert "date.today" not in Path(legacy.__file__).read_text()


def test_levelb_legacy_observers_are_hash_derived_non_dma_normalizations():
    retained = json.loads(legacy.OUTPUT.read_text())
    normalized = [
        row for row in retained["entries"]
        if row["normalization"] == "normalized"
    ]
    assert {row["escalation_id"] for row in normalized} == \
        legacy.LEVELB_NORMALIZATION_IDS
    assert retained["counts"] == {
        "entries": 16,
        "normalized": 4,
        "conservative_deny": 12,
    }
    for row in normalized:
        assert row["domain"] == "interface"
        assert row["window"] is None
        assert row["observer_methods"]
        assert row["external_receipt_sha256s"]
        assert not any(
            method.startswith("transferLog.")
            for method in row["observer_methods"])


def test_legacy_banked_analysis_pins_retain_behavior_proofs():
    retained = json.loads(legacy.OUTPUT.read_text())
    source = json.loads(legacy.SOURCE.read_text())
    reconciliation = json.loads(
        (legacy.ROOT / "analysis" /
         "phase4_upstream_dependency_reconciliation.json").read_text())
    source_entries = {row["id"]: row for row in source["entries"]}
    joined_pins = {
        row["entry_id"]: row
        for row in reconciliation["joined_live_escalation_pins"]
    }
    artifact_proofs = {
        row["path"]: row for row in reconciliation["artifacts"]
    }
    expected_normalized_payloads = {
        "analysis/phase4_fmv_levelb_reachability.json":
            "4dddf2a59e69f44ff3dbbcdad8da0c1730142f0086cc11a1436815d899dbae35",
        "analysis/phase4_fmv_levelb_first_call.json":
            "6c09512114c192112a0cc53d69db54c08a420c28fc95f283adc1c111f22a9c4c",
        "analysis/phase4_fmv_finale_route_probe.json":
            "ef63cc98954b29b6b5df2b82cc6c94fabcb72d68971bf136738acf81dd663e42",
    }
    checked = 0
    for indexed in retained["entries"]:
        escalation_id = indexed["escalation_id"]
        live = source_entries[escalation_id]
        banked = (live.get("execution_result") or {}).get("banked_analysis")
        if not banked or escalation_id not in joined_pins:
            continue
        pin = joined_pins[escalation_id]
        proof = artifact_proofs[banked["path"]]
        assert indexed["source_entry_sha256"] == \
            legacy.source_entry_sha256(live)
        assert _sha(legacy.ROOT / banked["path"]) == banked["sha256"]
        assert pin["sha256_after"] == banked["sha256"]
        assert pin["behavioral_payload_preserved"] is True
        assert proof["artifact_sha256_after"] == banked["sha256"]
        assert proof[
            "only_dependency_metadata_or_joined_identity_changed"] is True
        assert proof["historical_run_provenance_preserved"] is True
        assert proof["normalized_runtime_payload_sha256"] == \
            expected_normalized_payloads[banked["path"]]
        checked += 1
    assert checked == 6


def test_exact_pc_result_tracks_the_current_legacy_index():
    retained = json.loads(legacy.OUTPUT.read_text())
    result = json.loads(
        (legacy.ROOT / "analysis" /
         "phase4_fmv_levelb_region_b_dma_exact_pc_result.json").read_text())
    assert result["source_dependencies"][
        "analysis/phase4_method_legacy_live_index.json"] == \
        _sha(legacy.OUTPUT)
    assert retained["counts"] == {
        "entries": 16,
        "normalized": 4,
        "conservative_deny": 12,
    }
    assert result["claim_boundary"]["dimension_promoted"] is False


def test_json_duplicate_keys_and_floats_are_rejected(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema":"x","schema":"y"}')
    with pytest.raises(metrics.MetricsError, match="duplicate JSON key"):
        metrics.load_json(duplicate)
    floating = tmp_path / "float.json"
    floating.write_text('{"value":1.5}')
    with pytest.raises(metrics.MetricsError, match="floating-point"):
        metrics.load_json(floating)


@pytest.mark.parametrize("unsafe", [
    "/tmp/evidence.json", "../evidence.json", "a/../evidence.json", "./x.json",
])
def test_artifact_reference_rejects_unsafe_paths(tmp_path, unsafe):
    run = tmp_path / "run"
    repo = tmp_path / "repo"
    run.mkdir(parents=True)
    repo.mkdir(parents=True)
    ref = {"scope": "run", "path": unsafe, "sha256": "0" * 64}
    with pytest.raises(metrics.MetricsError, match="unsafe|non-canonical"):
        metrics.resolve_ref(ref, run, repo, "fixture")


def test_artifact_reference_rejects_hash_drift_and_unknown_keys(tmp_path):
    run = tmp_path / "run"
    repo = tmp_path / "repo"
    run.mkdir()
    repo.mkdir()
    artifact = run / "value.json"
    artifact.write_text("{}\n")
    bad = {"scope": "run", "path": "value.json", "sha256": "0" * 64}
    with pytest.raises(metrics.MetricsError, match="SHA-256 mismatch"):
        metrics.resolve_ref(bad, run, repo, "fixture")
    good = {**bad, "sha256": _sha(artifact), "passes": True}
    with pytest.raises(metrics.MetricsError, match="key mismatch"):
        metrics.resolve_ref(good, run, repo, "fixture")


def test_artifact_reference_rejects_symlink_escape(tmp_path):
    run = tmp_path / "run"
    repo = tmp_path / "repo"
    outside = tmp_path / "outside.json"
    run.mkdir()
    repo.mkdir()
    outside.write_text("{}\n")
    (run / "escape.json").symlink_to(outside)
    ref = {
        "scope": "run", "path": "escape.json", "sha256": _sha(outside),
    }
    with pytest.raises(metrics.MetricsError, match="escaping|regular"):
        metrics.resolve_ref(ref, run, repo, "fixture")


def _clock_range(start=10, stop=20):
    return {
        "clock": "movie_frame", "start": start, "stop": stop,
        "stop_inclusive": False,
    }


def _live_receipt():
    h = "1" * 64
    return {
        "schema": "abl-phase4-live-run-receipt/2",
        "complete": True,
        "errors": [],
        "experiment": {
            "executor_role": "investigator",
            "anchor": {
                "kind": "movie_start_state",
                "media_sha256": h,
                "settings_sha256": "2" * 64,
                "movie_sha256": "3" * 64,
                "state_sha256": "4" * 64,
                "start": {"clock": "movie_frame", "value": 10},
            },
            "execution": {
                "bound": _clock_range(10, 30),
                "capture_window": _clock_range(12, 20),
            },
            "domain": "ram",
            "observer_plan_sha256": "5" * 64,
            "perturbation_plan_sha256": "6" * 64,
            "control_plan_sha256": "7" * 64,
            "duckstation_source_sha256": "8" * 64,
            "duckstation_executable_sha256": "9" * 64,
            "api_surface_sha256": "a" * 64,
            "adapter_source_sha256": "b" * 64,
        },
    }


def test_live_experiment_key_is_canonical_but_semantic_fields_matter():
    first = _live_receipt()
    reordered = json.loads(json.dumps(first, sort_keys=True))
    assert metrics._canonical_live_key(first) == metrics._canonical_live_key(reordered)
    changed = _live_receipt()
    changed["experiment"]["execution"]["capture_window"]["stop"] = 21
    assert metrics._canonical_live_key(first) != metrics._canonical_live_key(changed)


@pytest.mark.parametrize(
    "path",
    [
        "tools/phase4_duckstation_batch.py",
        "tools/phase4_duckstation_late_batch.py",
        "tools/phase4_duckstation_exact_pc_batch.py",
        "tools/phase4_test_live.py",
    ],
)
def test_live_adapter_allowlist_covers_tracked_phase4_runners(path):
    assert metrics.LIVE_ADAPTER_PATH.fullmatch(path)


@pytest.mark.parametrize(
    "path",
    [
        "tools/phase4_untracked_batch.py",
        "tools/phase4_duckstation_late_batch.py.bak",
        "tools/../phase4_duckstation_late_batch.py",
    ],
)
def test_live_adapter_allowlist_remains_closed(path):
    assert not metrics.LIVE_ADAPTER_PATH.fullmatch(path)


def test_semantic_live_key_cannot_be_salted_by_adapter_comments():
    first = _live_receipt()
    second = json.loads(json.dumps(first))
    second["experiment"]["adapter_source_sha256"] = "f" * 64
    control = {"role": "baseline"}
    observer = {"operations": [{"method": "debugger.readMemory"}]}
    perturbation = {"kind": "none", "operations": []}
    assert metrics._semantic_live_key(
        first, control, observer, perturbation) == \
        metrics._semantic_live_key(
            second, control, observer, perturbation)


def test_observer_and_execution_limits_are_closed_and_finite():
    with pytest.raises(metrics.MetricsError, match="method is not closed"):
        metrics._validate_observer_plan({
            "schema": "abl-phase4-observer-plan/1",
            "operations": [{
                "sequence": 0, "method": "scenario.runBatch",
                "args": {"jobs": "not-an-array"},
            }],
            "result_limits": {
                "max_records": 1, "max_bytes": 1, "max_pages": 1,
            },
        }, "observer")
    metrics._validate_observer_plan({
        "schema": "abl-phase4-observer-plan/1",
        "operations": [{
            "sequence": 0,
            "method": "transferLog.start",
            "args": {},
        }],
        "result_limits": {
            "max_records": 100000,
            "max_bytes": 268435456,
            "max_pages": 10000,
        },
    }, "observer")
    with pytest.raises(metrics.MetricsError, match="must be positive"):
        metrics._validate_observer_plan({
            "schema": "abl-phase4-observer-plan/1",
            "operations": [{
                "sequence": 0, "method": "debugger.getRegisters", "args": {},
            }],
            "result_limits": {
                "max_records": 10 ** 80, "max_bytes": 1, "max_pages": 1,
            },
        }, "observer")
    with pytest.raises(metrics.MetricsError, match="nonnegative integer"):
        metrics._typed_clock(
            {"clock": "cpu_cycle", "value": 10 ** 80},
            point=True, where="clock")


def _direct_exact_pc_components():
    plan = copy.deepcopy(exact_pc_arm.CONFIGURATION["exact_pc_plan"])
    direct_result = exact_pc_adapter.execute_exact_pc_window(
        exact_pc_arm.SyntheticRpc(),
        plan,
        "owned-exact-pc-session",
        plan["identity_join"],
        sleep=lambda _seconds: None,
    )
    observer = {
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
    }
    method_schemas = {
        method: hashlib.sha256(method.encode()).hexdigest()
        for method in (
            set(exact_pc_adapter.REQUIRED_METHODS) |
            metrics.REQUIRED_LIVE_COMMAND_METHODS |
            metrics.REQUIRED_ATOMIC_COMMAND_METHODS
        )
    }
    event_rows = [
        ("debugger.capabilities", {}, {"identity": "capabilities"}),
        ("debugger.status", {}, {"game_serial": "SCUS-94288"}),
        ("emulator.getMediaInfo", {}, {
            "serial": "SCUS-94288",
            "sha256": metrics.PRISTINE_MEDIA_SHA256,
        }),
        ("scenario.runBatch", {"plan_sha256": "1" * 64}, {
            "batch_id": "batch-exact", "job_ids": ["job-anchor"],
        }),
        ("scenario.getBatch", {
            "batch_id": "batch-exact", "include_results": True,
        }, {
            "batch_id": "batch-exact", "status": "completed",
            "job_ids": ["job-anchor"],
        }),
    ]
    atomic_events = [
        {
            "sequence": index,
            "server_session_id": "owned-exact-pc-session",
            "method": method,
            "params": params,
            "result": result,
            "result_sha256": hashlib.sha256(
                metrics.canonical_bytes(result)).hexdigest(),
        }
        for index, (method, params, result) in enumerate(event_rows)
    ]
    direct_events = [
        {**event, "sequence": len(atomic_events) + index}
        for index, event in enumerate(
            direct_result["command_events"]["events"])
    ]
    command_events = {
        "schema": "abl-phase4-live-command-events/1",
        "complete": True,
        "errors": [],
        "events": atomic_events + direct_events,
    }
    raw = {
        "schema": "abl-phase4-live-raw-results/1",
        "complete": True,
        "errors": [],
        "counters": {
            "server_session_id": "owned-exact-pc-session",
            "launches": 1,
            "atomic_jobs": 1,
            "replay_frames": 15816,
            "observer_frames": 0,
            "instructions": 0,
        },
        "sessions": [{
            "server_session_id": "owned-exact-pc-session",
            "launch_sequence": 0,
        }],
        "results": [{
            "job_id": "job-anchor",
            "server_session_id": "owned-exact-pc-session",
            "status": "completed",
            "replay_start": 0,
            "replay_stop": 15816,
            "observer_start": 15816,
            "observer_stop": 15816,
            "instruction_start": 0,
            "instruction_stop": 0,
        }],
    }
    pagination = {
        "schema": "abl-phase4-live-pagination/1",
        "complete": True,
        "errors": [],
        "truncated": False,
        "pages_complete": True,
        "pages": [
            {
                "page": index,
                "record_count": page["returned"],
            }
            for index, page in enumerate(
                direct_result["transfer"]["pages"])
        ],
    }
    experiment = {
        "anchor": {
            "media_sha256": metrics.PRISTINE_MEDIA_SHA256,
        },
        "execution": {
            "bound": {
                "clock": "emulator_frame",
                "start": 0,
                "stop": 15880,
                "stop_inclusive": False,
            },
            "capture_window": {
                "clock": "emulator_frame",
                "start": 15816,
                "stop": 15880,
                "stop_inclusive": False,
            },
        },
        "domain": "dma",
        "duckstation_executable_sha256": (
            plan["identity_join"]["binary_sha256"]),
    }
    media = {
        "capabilities": {
            "method_schemas": method_schemas,
        },
    }
    return (
        observer, command_events, raw, pagination, experiment, media,
        command_events["events"][4:5],
    )


def test_direct_exact_pc_receipt_stream_is_adapter_replayed_and_bounded():
    (
        observer, events, raw, pagination, experiment, media, terminal_gets,
    ) = _direct_exact_pc_components()
    metrics._validate_observer_plan(observer, "observer")
    metrics._validate_result_doc(
        events, "abl-phase4-live-command-events/1", "events")
    derived = metrics._validate_direct_exact_pc_stream(
        observer, events, raw, pagination, experiment, media,
        "tools/phase4_duckstation_exact_pc_batch.py",
        terminal_gets, metrics.ROOT, "direct")
    assert derived is not None
    assert derived["execution"] == {
        "clock": "emulator_frame",
        "anchor_frame": 15816,
        "frame_ceiling": 15880,
        "start_stop_frame": 15817,
        "terminal_stop_frame": 15817,
    }
    assert derived["stops"]["registers"] == {
        "pc": "0x80046078",
        "a0": "0x00000012",
        "a1": "0x800B5788",
    }
    assert derived["transfer"]["total"] == 2
    assert derived["transfer"]["truncated"] is False


class _EscapingExactPcRpc(exact_pc_arm.SyntheticRpc):
    def __call__(self, server_session_id, method, params, socket_timeout_ms):
        result = super().__call__(
            server_session_id, method, params, socket_timeout_ms)
        if method == "debugger.status" and self.status_count == 2:
            result.update(paused=False, frame=15881, pc="0x80050324")
        if method == "debugger.pause":
            result.update(frame=15881, pc="0x80050324")
        return result


def _falsified_direct_exact_pc_components():
    observer, events, raw, pagination, experiment, media, terminal_gets = \
        _direct_exact_pc_components()
    plan = observer["direct_command_plan"]
    rpc = _EscapingExactPcRpc()
    retained = []

    def recording_rpc(session_id, method, params, socket_timeout_ms):
        result = rpc(session_id, method, params, socket_timeout_ms)
        retained.append({
            "sequence": len(retained),
            "server_session_id": session_id,
            "method": method,
            "params": params,
            "socket_timeout_ms": socket_timeout_ms,
            "result": result,
            "result_sha256": hashlib.sha256(
                metrics.canonical_bytes(result)).hexdigest(),
        })
        return result

    with pytest.raises(
            exact_pc_adapter.ExactPcFalsifiedError,
            match="escaped the finite emulator-frame bound"):
        exact_pc_adapter.execute_exact_pc_window(
            recording_rpc, plan, "owned-exact-pc-session",
            plan["identity_join"], sleep=lambda _seconds: None)
    events["events"] = events["events"][:5] + [
        {**event, "sequence": 5 + index}
        for index, event in enumerate(retained)
    ]
    pagination["pages"] = []
    return (
        observer, events, raw, pagination, experiment, media, terminal_gets,
    )


def test_falsified_direct_exact_pc_receipt_is_adapter_replayed_and_closed():
    components = _falsified_direct_exact_pc_components()
    derived = metrics._validate_direct_exact_pc_stream(
        *components[:6],
        "tools/phase4_duckstation_exact_pc_batch.py",
        components[6], metrics.ROOT, "direct")
    assert derived == {
        "schema": exact_pc_adapter.RESULT_SCHEMA,
        "complete": True,
        "errors": [],
        "outcome": "falsified",
        "reason": "start_stop escaped the finite emulator-frame bound",
        "command_event_count": 4,
    }


def test_bounded_exact_pc_falsifier_requires_retained_pause():
    components = _falsified_direct_exact_pc_components()
    components[1]["events"].pop()
    with pytest.raises(metrics.MetricsError, match="lacks retained pause"):
        metrics._validate_direct_exact_pc_stream(
            *components[:6],
            "tools/phase4_duckstation_exact_pc_batch.py",
            components[6], metrics.ROOT, "direct")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda observer, events, _raw, _pages: events["events"][6][
                "params"].update(address="0x8004607C"),
            "differs from the typed adapter request",
        ),
        (
            lambda _observer, events, _raw, _pages: events["events"][8][
                "result"]["registers"].update(a1=0x800B5790),
            "falsified direct command stream has extras",
        ),
        (
            lambda observer, _events, _raw, _pages: observer[
                "direct_command_plan"]["execution_limit"].update(
                    max_frame_delta=63),
            "result limits|frame bound",
        ),
        (
            lambda _observer, _events, raw, _pages: raw["results"][0].update(
                observer_stop=15817),
            "paused capture anchor",
        ),
        (
            lambda _observer, _events, _raw, pages: pages["pages"][0].update(
                record_count=1),
            "pagination differs",
        ),
    ],
)
def test_direct_exact_pc_receipt_mutations_fail_closed(mutation, message):
    (
        observer, events, raw, pagination, experiment, media, terminal_gets,
    ) = _direct_exact_pc_components()
    mutation(observer, events, raw, pagination)
    for event in events["events"]:
        event["result_sha256"] = hashlib.sha256(
            metrics.canonical_bytes(event["result"])).hexdigest()
    with pytest.raises(metrics.MetricsError, match=message):
        metrics._validate_direct_exact_pc_stream(
            observer, events, raw, pagination, experiment, media,
            "tools/phase4_duckstation_exact_pc_batch.py",
            terminal_gets, metrics.ROOT, "direct")


def test_historical_observer_schema_cannot_admit_direct_command_events():
    observer, events, raw, pages, experiment, media, terminal_gets = \
        _direct_exact_pc_components()
    observer.pop("direct_command_plan")
    observer["schema"] = "abl-phase4-observer-plan/1"
    with pytest.raises(metrics.MetricsError, match="historical observer"):
        metrics._validate_direct_exact_pc_stream(
            observer, events, raw, pages, experiment, media,
            "tools/phase4_duckstation_exact_pc_batch.py",
            terminal_gets, metrics.ROOT, "direct")


def _direct_two_pc_components():
    plan = copy.deepcopy(two_pc_boundary.CONFIGURATION["first_hit_plan"])
    direct_result = two_pc_adapter.execute_first_hit(
        two_pc_boundary.SyntheticRpc(1),
        plan,
        "owned-two-pc-session",
        plan["identity_join"],
        sleep=lambda _seconds: None,
    )
    observer = {
        "schema": "abl-phase4-observer-plan/2",
        "operations": [
            {
                "sequence": index,
                "method": "debugger.addBreakpoint",
                "args": copy.deepcopy(stop["params"]),
            }
            for index, stop in enumerate(plan["breakpoint_sequence"])
        ],
        "result_limits": two_pc_adapter.observer_result_limits(plan),
        "direct_command_plan": plan,
    }
    method_schemas = {
        method: hashlib.sha256(method.encode()).hexdigest()
        for method in (
            set(two_pc_adapter.REQUIRED_METHODS) |
            metrics.REQUIRED_LIVE_COMMAND_METHODS |
            metrics.REQUIRED_ATOMIC_COMMAND_METHODS
        )
    }
    atomic_rows = [
        ("debugger.capabilities", {}, {"identity": "capabilities"}),
        ("debugger.status", {}, {"game_serial": "SCUS-94288"}),
        ("emulator.getMediaInfo", {}, {
            "serial": "SCUS-94288",
            "sha256": metrics.PRISTINE_MEDIA_SHA256,
        }),
        ("scenario.runBatch", {"plan_sha256": "2" * 64}, {
            "batch_id": "batch-first-hit", "job_ids": ["job-anchor"],
        }),
        ("scenario.getBatch", {
            "batch_id": "batch-first-hit", "include_results": True,
        }, {
            "batch_id": "batch-first-hit", "status": "completed",
            "job_ids": ["job-anchor"],
        }),
    ]
    atomic_events = [
        {
            "sequence": index,
            "server_session_id": "owned-two-pc-session",
            "method": method,
            "params": params,
            "result": result,
            "result_sha256": hashlib.sha256(
                metrics.canonical_bytes(result)).hexdigest(),
        }
        for index, (method, params, result) in enumerate(atomic_rows)
    ]
    direct_events = [
        {**event, "sequence": len(atomic_events) + index}
        for index, event in enumerate(
            direct_result["command_events"]["events"])
    ]
    command_events = {
        "schema": "abl-phase4-live-command-events/1",
        "complete": True,
        "errors": [],
        "events": atomic_events + direct_events,
    }
    raw = {
        "schema": "abl-phase4-live-raw-results/1",
        "complete": True,
        "errors": [],
        "counters": {
            "server_session_id": "owned-two-pc-session",
            "launches": 1,
            "atomic_jobs": 1,
            "replay_frames": 15792,
            "observer_frames": 0,
            "instructions": 0,
        },
        "sessions": [{
            "server_session_id": "owned-two-pc-session",
            "launch_sequence": 0,
        }],
        "results": [{
            "job_id": "job-anchor",
            "server_session_id": "owned-two-pc-session",
            "status": "completed",
            "replay_start": 0,
            "replay_stop": 15792,
            "observer_start": 15792,
            "observer_stop": 15792,
            "instruction_start": 0,
            "instruction_stop": 0,
        }],
    }
    pagination = {
        "schema": "abl-phase4-live-pagination/1",
        "complete": True,
        "errors": [],
        "truncated": False,
        "pages_complete": True,
        "pages": [],
    }
    experiment = {
        "anchor": {"media_sha256": metrics.PRISTINE_MEDIA_SHA256},
        "execution": {
            "bound": {
                "clock": "emulator_frame",
                "start": 0,
                "stop": 15856,
                "stop_inclusive": False,
            },
            "capture_window": {
                "clock": "emulator_frame",
                "start": 15792,
                "stop": 15856,
                "stop_inclusive": False,
            },
        },
        "domain": "interface",
        "duckstation_executable_sha256": (
            plan["identity_join"]["binary_sha256"]),
    }
    media = {"capabilities": {"method_schemas": method_schemas}}
    return (
        observer, command_events, raw, pagination, experiment, media,
        command_events["events"][4:5],
    )


def test_direct_two_pc_receipt_stream_is_adapter_replayed_and_bounded():
    components = _direct_two_pc_components()
    metrics._validate_observer_plan(components[0], "observer")
    metrics._validate_result_doc(
        components[1], "abl-phase4-live-command-events/1", "events")
    derived = metrics._validate_direct_two_pc_first_hit_stream(
        *components[:6],
        "tools/phase4_duckstation_two_pc_first_hit.py",
        components[6],
        metrics.ROOT,
        "direct",
    )
    assert derived is not None
    assert derived["execution"] == {
        "clock": "emulator_frame",
        "anchor_frame": 15792,
        "frame_ceiling": 15856,
        "first_hit_frame": 15796,
    }
    assert derived["first_hit"]["pc"] == "0x8005029C"
    assert derived["cleanup"]["remaining_breakpoints"] == 0


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda observer, _events, _raw, _pages: observer[
                "direct_command_plan"]["execution_limit"].update(
                    max_frame_delta=65),
            "64-frame predeclaration",
        ),
        (
            lambda _observer, events, _raw, _pages: events["events"][7][
                "result"].update(id="bp_99"),
            "adapter-derived|extras",
        ),
        (
            lambda _observer, events, _raw, _pages: events["events"][-3][
                "result"].update(removed=False),
            "extras|cleanup",
        ),
        (
            lambda _observer, events, _raw, _pages:
            events["events"][-2].__setitem__(
                "server_session_id", "other-session"),
            "typed adapter request",
        ),
        (
            lambda _observer, _events, _raw, pages: pages.update(
                pages=[{"page": 0, "record_count": 1}]),
            "closed empty pagination",
        ),
    ],
)
def test_direct_two_pc_receipt_mutations_fail_closed(mutation, message):
    components = list(_direct_two_pc_components())
    mutation(components[0], components[1], components[2], components[3])
    for event in components[1]["events"]:
        event["result_sha256"] = hashlib.sha256(
            metrics.canonical_bytes(event["result"])).hexdigest()
    with pytest.raises(metrics.MetricsError, match=message):
        metrics._validate_direct_two_pc_first_hit_stream(
            *components[:6],
            "tools/phase4_duckstation_two_pc_first_hit.py",
            components[6],
            metrics.ROOT,
            "direct",
        )


def test_live_schema_rejects_prose_windows_and_wrong_anchor_combinations():
    receipt = _live_receipt()
    receipt["experiment"]["execution"]["capture_window"] = "[12,20]"
    with pytest.raises(metrics.MetricsError, match="not an object"):
        metrics._canonical_live_key(receipt)
    receipt = _live_receipt()
    receipt["experiment"]["anchor"]["kind"] = "cold_boot"
    with pytest.raises(metrics.MetricsError, match="kind/hash combination"):
        metrics._canonical_live_key(receipt)


def test_controller_events_require_contiguous_closed_stream(tmp_path):
    path = tmp_path / "events.json"
    path.write_text(json.dumps({
        "schema": "abl-phase4-controller-events/1",
        "iteration": 1,
        "events": [
                {
                    "sequence": 0, "at": "2026-07-26T00:00:00Z",
                    "type": "iteration_started",
                    "payload": {"base_commit": "1" * 40},
                },
                {
                    "sequence": 2, "at": "2026-07-26T00:01:00Z",
                    "type": "iteration_completed",
                    "payload": {"tested_commit": "2" * 40},
                },
        ],
    }))
    with pytest.raises(metrics.MetricsError, match="not contiguous"):
        metrics._event_document(path)


def test_main_manifest_shape_cannot_grow_authored_pass_fields():
    assert "passes" not in metrics.MANIFEST_KEYS
    assert "counts" not in metrics.MANIFEST_KEYS
    assert "classification" not in metrics.MANIFEST_KEYS
    assert metrics.EVIDENCE_KEYS == {
        "debt_before", "debt_after", "progress_receipt",
        "offline_query_receipts", "live_run_receipts",
        "escalation_ledger_before", "escalation_ledger_after",
        "verifier_decision", "controller_events", "command_log",
        "validation_report", "knowledge_report", "vault_report",
        "clean_checkout_report",
    }


def _write_json(path: Path, doc):
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _ref(path: Path, run: Path):
    return {
        "scope": "run",
        "path": path.relative_to(run).as_posix(),
        "sha256": _sha(path),
    }


def _strict_live_fixture(tmp_path: Path):
    run = tmp_path / "run"
    repo = tmp_path / "repo"
    run.mkdir(parents=True)
    repo.mkdir(parents=True)
    (repo / "analysis").mkdir()
    (repo / "tools").mkdir()
    h = metrics.PRISTINE_MEDIA_SHA256
    methods = {
        "committed": [
            "debugger.readMemory", "debugger.capabilities",
            "debugger.status", "emulator.getMediaInfo",
            "scenario.runBatch", "scenario.getBatch",
        ],
        "dirty_only": [],
    }
    source_declaration = {"status_sha256": "8" * 64}
    source_hash = hashlib.sha256(
        metrics.canonical_bytes(source_declaration)).hexdigest()
    executable_hash = "9" * 64
    api_hash = hashlib.sha256(metrics.canonical_bytes(methods)).hexdigest()
    _write_json(repo / "analysis" / "phase3_duckstation_rpc_manifest.json", {
        "source": source_declaration,
        "binaries": {"build/bin/duckstation-qt": {
            "sha256": executable_hash,
        }},
        "methods": methods,
    })
    docs = {
        "observer.json": {
            "schema": "abl-phase4-observer-plan/1",
            "operations": [
                {"sequence": 0, "method": "debugger.readMemory",
                 "args": {"address": 0x800A6500, "size": 4}},
            ],
            "result_limits": {
                "max_records": 1, "max_bytes": 4, "max_pages": 1,
            },
        },
        "perturbation.json": {
            "schema": "abl-phase4-perturbation-plan/1",
            "kind": "none", "operations": [],
        },
        "control.json": {
            "schema": "abl-phase4-control-plan/1",
            "role": "baseline",
            "paired_run_basis_sha256": "2" * 64,
            "anchor_sha256": "3" * 64,
            "only_difference_plan_sha256": "4" * 64,
            "assertion_plan_sha256": "5" * 64,
        },
        "raw.json": {
            "schema": "abl-phase4-live-raw-results/1",
            "complete": True, "errors": [],
            "sessions": [{
                "server_session_id": "owned-session", "launch_sequence": 0,
            }],
            "counters": {
                "server_session_id": "owned-session",
                "launches": 1, "atomic_jobs": 1, "replay_frames": 40,
                "observer_frames": 8, "instructions": 12,
            },
            "results": [{
                "job_id": "job-0", "server_session_id": "owned-session",
                "status": "completed", "replay_start": 0, "replay_stop": 40,
                "observer_start": 8, "observer_stop": 16,
                "instruction_start": 100, "instruction_stop": 112,
            }],
        },
        "pages.json": {
            "schema": "abl-phase4-live-pagination/1",
            "complete": True, "errors": [], "truncated": False,
            "pages_complete": True,
            "pages": [{"page": 0, "record_count": 1}],
        },
        "media.json": {
            "schema": "abl-phase4-live-media-capabilities/1",
            "complete": True, "errors": [], "mounted_serial": "SCUS-94288",
            "pristine_media_sha256": h,
            "duckstation_source_sha256": source_hash,
            "duckstation_executable_sha256": executable_hash,
            "api_surface_sha256": api_hash,
            "capabilities": {
                "api_version": "1",
                "method_schemas": {
                    "debugger.readMemory": "1" * 64,
                    "debugger.capabilities": "2" * 64,
                    "debugger.status": "3" * 64,
                    "emulator.getMediaInfo": "4" * 64,
                    "scenario.runBatch": "5" * 64,
                    "scenario.getBatch": "6" * 64,
                },
            },
        },
        "events.json": {
            "schema": "abl-phase4-live-command-events/1",
            "complete": True, "errors": [],
            "events": [],
        },
        "settings.json": {
            "renderer": "software", "cpu_mode": "cached_interpreter",
        },
        "cleanup.json": {
            "schema": "abl-phase4-owned-pid-cleanup/1",
            "complete": True, "errors": [], "owned_pid": 123,
            "owned_pid_stopped": True, "config_dir": "/tmp/owned-config",
            "actions": [
                {"sequence": 0, "kind": "stop_owned_pid", "pid": 123},
                {"sequence": 1, "kind": "confirm_pid_stopped", "pid": 123},
            ],
        },
    }
    paths = {}
    for name, doc in docs.items():
        paths[name] = run / name
        _write_json(paths[name], doc)
    adapter = repo / "tools" / "phase4_test_live.py"
    adapter.write_text("# pinned adapter\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "add", "tools/phase4_test_live.py"], cwd=repo, check=True)
    paths["adapter.py"] = adapter
    preservation = run / "preservation.json"
    entries = [
        {
            "sha256": _sha(path), "size": path.stat().st_size,
            "media_class": (
                "tool_source" if path.suffix == ".py" else "runtime_receipt"),
            "preservation_required": True,
        }
        for path in paths.values()
    ]
    _write_json(preservation, {
        "schema": "abl-phase4-method-external-preservation/1",
        "complete": True, "errors": [], "entries": entries,
    })
    observer_sha = _sha(paths["observer.json"])
    perturbation_sha = _sha(paths["perturbation.json"])
    control_sha = _sha(paths["control.json"])
    settings_sha = _sha(paths["settings.json"])
    receipt = {
        "schema": "abl-phase4-live-run-receipt/2",
        "complete": True, "errors": [],
        "escalation_id": "P4-V2-TEST",
        "missing_fact_id": "E15/test-bound",
        "precise": False,
        "prelude_receipt": None,
        "experiment": {
            "executor_role": "investigator",
            "anchor": {
                "kind": "cold_boot", "media_sha256": h,
                "settings_sha256": settings_sha,
                "movie_sha256": None, "state_sha256": None,
                "start": {"clock": "emulator_frame", "value": 0},
            },
            "execution": {
                "bound": {
                    "clock": "emulator_frame", "start": 0, "stop": 40,
                    "stop_inclusive": False,
                },
                "capture_window": {
                    "clock": "emulator_frame", "start": 8, "stop": 16,
                    "stop_inclusive": False,
                },
            },
            "domain": "ram",
            "observer_plan_sha256": observer_sha,
            "perturbation_plan_sha256": perturbation_sha,
            "control_plan_sha256": control_sha,
            "duckstation_source_sha256": source_hash,
            "duckstation_executable_sha256": executable_hash,
            "api_surface_sha256": api_hash,
            "adapter_source_sha256": _sha(adapter),
        },
        "evidence": {
            "raw_results": _ref(paths["raw.json"], run),
            "pagination": _ref(paths["pages.json"], run),
            "media_capabilities": _ref(paths["media.json"], run),
            "command_events": _ref(paths["events.json"], run),
            "observer_plan": _ref(paths["observer.json"], run),
            "perturbation_plan": _ref(paths["perturbation.json"], run),
            "control_plan": _ref(paths["control.json"], run),
            "adapter_source": {
                "scope": "repo", "path": "tools/phase4_test_live.py",
                "sha256": _sha(adapter),
            },
            "settings_snapshot": _ref(paths["settings.json"], run),
            "owned_pid_cleanup": _ref(paths["cleanup.json"], run),
            "external_preservation_manifest": _ref(preservation, run),
        },
    }
    control = json.loads(paths["control.json"].read_text(encoding="utf-8"))
    control["anchor_sha256"] = hashlib.sha256(
        metrics.canonical_bytes(receipt["experiment"]["anchor"])).hexdigest()
    control["only_difference_plan_sha256"] = perturbation_sha
    control["paired_run_basis_sha256"] = hashlib.sha256(
        metrics.canonical_bytes({
            key: value for key, value in receipt["experiment"].items()
            if key not in {"executor_role", "control_plan_sha256"}
        })).hexdigest()
    _write_json(paths["control.json"], control)
    old_control_sha = receipt["evidence"]["control_plan"]["sha256"]
    new_control_sha = _sha(paths["control.json"])
    receipt["evidence"]["control_plan"]["sha256"] = new_control_sha
    receipt["experiment"]["control_plan_sha256"] = new_control_sha
    atomic_plan_sha256 = hashlib.sha256(metrics.canonical_bytes({
        "anchor": receipt["experiment"]["anchor"],
        "execution": receipt["experiment"]["execution"],
        "observer_plan_sha256": observer_sha,
        "perturbation_plan_sha256": perturbation_sha,
        "control_plan_sha256": new_control_sha,
    })).hexdigest()
    event_results = [
        ("debugger.capabilities", {}, {
            "source_sha256": source_hash,
            "executable_sha256": executable_hash,
            "api_surface_sha256": api_hash,
            "method_schemas": docs["media.json"]["capabilities"]["method_schemas"],
        }),
        ("debugger.status", {}, {"game_serial": "SCUS-94288"}),
        ("emulator.getMediaInfo", {}, {
            "serial": "SCUS-94288", "sha256": h,
        }),
        ("scenario.runBatch", {"plan_sha256": atomic_plan_sha256}, {
            "batch_id": "batch-0", "job_ids": ["job-0"],
        }),
        ("scenario.getBatch", {
            "batch_id": "batch-0", "include_results": True,
        }, {
            "batch_id": "batch-0", "status": "completed",
            "job_ids": ["job-0"],
        }),
    ]
    old_events_sha = _sha(paths["events.json"])
    events = json.loads(paths["events.json"].read_text(encoding="utf-8"))
    events["events"] = [
        {
            "sequence": index, "server_session_id": "owned-session",
            "method": method, "params": params, "result": result,
            "result_sha256": hashlib.sha256(
                metrics.canonical_bytes(result)).hexdigest(),
        }
        for index, (method, params, result) in enumerate(event_results)
    ]
    _write_json(paths["events.json"], events)
    receipt["evidence"]["command_events"]["sha256"] = _sha(paths["events.json"])
    preservation_doc = json.loads(preservation.read_text(encoding="utf-8"))
    for entry in preservation_doc["entries"]:
        if entry["sha256"] == old_control_sha:
            entry["sha256"] = new_control_sha
            entry["size"] = paths["control.json"].stat().st_size
        elif entry["sha256"] == old_events_sha:
            entry["sha256"] = _sha(paths["events.json"])
            entry["size"] = paths["events.json"].stat().st_size
    _write_json(preservation, preservation_doc)
    receipt["evidence"]["external_preservation_manifest"]["sha256"] = _sha(
        preservation)
    receipt_path = run / "receipt.json"
    _write_json(receipt_path, receipt)
    ledger = {
        "schema": "abl-phase4-live-escalations/1",
        "entries": [{
            "id": "P4-V2-TEST", "state": "planned",
            "missing_fact_id": "E15/test-bound", "target_row": "E15_fmv",
        }],
    }
    legacy = {"entries": []}
    after_ledger = {
        "schema": "abl-phase4-live-escalations/1",
        "entries": [{**ledger["entries"][0], "state": "executed"}],
    }
    return run, repo, receipt_path, receipt, ledger, after_ledger, legacy


def _full_direct_exact_pc_fixture(tmp_path: Path):
    run, _repo, receipt_path, receipt, ledger, after_ledger, legacy_index = \
        _strict_live_fixture(tmp_path)
    manifest = json.loads(
        (metrics.ROOT / "analysis/phase3_duckstation_rpc_manifest.json").read_text())
    source_hash = hashlib.sha256(
        metrics.canonical_bytes(manifest["source"])).hexdigest()
    executable_hash = manifest["binaries"][
        "build-release/bin/duckstation-qt"]["sha256"]
    api_hash = hashlib.sha256(
        metrics.canonical_bytes(manifest["methods"])).hexdigest()
    plan = copy.deepcopy(exact_pc_arm.CONFIGURATION["exact_pc_plan"])
    session_id = "owned-exact-pc-session"
    direct = exact_pc_adapter.execute_exact_pc_window(
        exact_pc_arm.SyntheticRpc(), plan, session_id,
        plan["identity_join"], sleep=lambda _seconds: None)
    methods = set(exact_pc_adapter.REQUIRED_METHODS) | \
        metrics.REQUIRED_LIVE_COMMAND_METHODS | \
        metrics.REQUIRED_ATOMIC_COMMAND_METHODS
    method_schemas = {
        method: hashlib.sha256(method.encode()).hexdigest()
        for method in methods
    }

    paths = {
        name: run / name
        for name in (
            "observer.json", "perturbation.json", "control.json", "raw.json",
            "pages.json", "media.json", "events.json", "settings.json",
            "cleanup.json",
        )
    }
    observer = {
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
    }
    _write_json(paths["observer.json"], observer)
    observer_sha = _sha(paths["observer.json"])
    perturbation_sha = _sha(paths["perturbation.json"])
    settings_sha = _sha(paths["settings.json"])
    anchor = {
        "kind": "cold_boot_movie",
        "media_sha256": metrics.PRISTINE_MEDIA_SHA256,
        "settings_sha256": settings_sha,
        "movie_sha256": (
            "ece62d4e6f92b887b0500dd8ac3bec48f3638ad5d9858cda7d5b0afb3a8d2602"
        ),
        "state_sha256": None,
        "start": {"clock": "emulator_frame", "value": 0},
    }
    receipt["precise"] = True
    receipt["experiment"].update({
        "anchor": anchor,
        "execution": {
            "bound": {
                "clock": "emulator_frame", "start": 0, "stop": 15880,
                "stop_inclusive": False,
            },
            "capture_window": {
                "clock": "emulator_frame", "start": 15816, "stop": 15880,
                "stop_inclusive": False,
            },
        },
        "domain": "dma",
        "observer_plan_sha256": observer_sha,
        "perturbation_plan_sha256": perturbation_sha,
        "duckstation_source_sha256": source_hash,
        "duckstation_executable_sha256": executable_hash,
        "api_surface_sha256": api_hash,
        "adapter_source_sha256": _sha(
            metrics.ROOT / "tools/phase4_duckstation_exact_pc_batch.py"),
    })
    control = json.loads(paths["control.json"].read_text())
    control["anchor_sha256"] = hashlib.sha256(
        metrics.canonical_bytes(anchor)).hexdigest()
    control["only_difference_plan_sha256"] = perturbation_sha
    control["paired_run_basis_sha256"] = hashlib.sha256(
        metrics.canonical_bytes({
            key: value for key, value in receipt["experiment"].items()
            if key not in {"executor_role", "control_plan_sha256"}
        })).hexdigest()
    _write_json(paths["control.json"], control)
    control_sha = _sha(paths["control.json"])
    receipt["experiment"]["control_plan_sha256"] = control_sha

    _write_json(paths["raw.json"], {
        "schema": "abl-phase4-live-raw-results/1",
        "complete": True,
        "errors": [],
        "sessions": [{
            "server_session_id": session_id, "launch_sequence": 0,
        }],
        "counters": {
            "server_session_id": session_id,
            "launches": 1, "atomic_jobs": 1, "replay_frames": 15816,
            "observer_frames": 0, "instructions": 0,
        },
        "results": [{
            "job_id": "job-anchor", "server_session_id": session_id,
            "status": "completed", "replay_start": 0, "replay_stop": 15816,
            "observer_start": 15816, "observer_stop": 15816,
            "instruction_start": 0, "instruction_stop": 0,
        }],
    })
    pages = [
        {"page": index, "record_count": page["returned"]}
        for index, page in enumerate(direct["transfer"]["pages"])
    ]
    _write_json(paths["pages.json"], {
        "schema": "abl-phase4-live-pagination/1",
        "complete": True, "errors": [], "truncated": False,
        "pages_complete": True, "pages": pages,
    })
    _write_json(paths["media.json"], {
        "schema": "abl-phase4-live-media-capabilities/1",
        "complete": True, "errors": [], "mounted_serial": "SCUS-94288",
        "pristine_media_sha256": metrics.PRISTINE_MEDIA_SHA256,
        "duckstation_source_sha256": source_hash,
        "duckstation_executable_sha256": executable_hash,
        "api_surface_sha256": api_hash,
        "capabilities": {
            "api_version": "1", "method_schemas": method_schemas,
        },
    })
    atomic_plan_sha256 = hashlib.sha256(metrics.canonical_bytes({
        "anchor": anchor,
        "execution": receipt["experiment"]["execution"],
        "observer_plan_sha256": observer_sha,
        "perturbation_plan_sha256": perturbation_sha,
        "control_plan_sha256": control_sha,
    })).hexdigest()
    identity_results = [
        ("debugger.capabilities", {}, {
            "source_sha256": source_hash,
            "executable_sha256": executable_hash,
            "api_surface_sha256": api_hash,
            "method_schemas": method_schemas,
        }),
        ("debugger.status", {}, {"game_serial": "SCUS-94288"}),
        ("emulator.getMediaInfo", {}, {
            "serial": "SCUS-94288",
            "sha256": metrics.PRISTINE_MEDIA_SHA256,
        }),
        ("scenario.runBatch", {"plan_sha256": atomic_plan_sha256}, {
            "batch_id": "batch-exact", "job_ids": ["job-anchor"],
        }),
        ("scenario.getBatch", {
            "batch_id": "batch-exact", "include_results": True,
        }, {
            "batch_id": "batch-exact", "status": "completed",
            "job_ids": ["job-anchor"],
        }),
    ]
    events = [
        {
            "sequence": index, "server_session_id": session_id,
            "method": method, "params": params, "result": result,
            "result_sha256": hashlib.sha256(
                metrics.canonical_bytes(result)).hexdigest(),
        }
        for index, (method, params, result) in enumerate(identity_results)
    ]
    event_count = len(events)
    events.extend(
        {**event, "sequence": event_count + index}
        for index, event in enumerate(direct["command_events"]["events"])
    )
    _write_json(paths["events.json"], {
        "schema": "abl-phase4-live-command-events/1",
        "complete": True, "errors": [], "events": events,
    })
    prelude_path = run / "prelude.json"
    prelude_experiment = copy.deepcopy(receipt["experiment"])
    prelude_experiment["execution"] = {
        "bound": {
            "clock": "emulator_frame", "start": 0, "stop": 15896,
            "stop_inclusive": False,
        },
        "capture_window": {
            "clock": "emulator_frame", "start": 15800,
            "stop": 15896, "stop_inclusive": False,
        },
    }
    _write_json(prelude_path, {
        "schema": "abl-phase4-live-run-receipt/2",
        "precise": False,
        "experiment": prelude_experiment,
    })
    receipt["prelude_receipt"] = _ref(prelude_path, run)
    receipt["evidence"] = {
        "raw_results": _ref(paths["raw.json"], run),
        "pagination": _ref(paths["pages.json"], run),
        "media_capabilities": _ref(paths["media.json"], run),
        "command_events": _ref(paths["events.json"], run),
        "observer_plan": _ref(paths["observer.json"], run),
        "perturbation_plan": _ref(paths["perturbation.json"], run),
        "control_plan": _ref(paths["control.json"], run),
        "adapter_source": {
            "scope": "repo",
            "path": "tools/phase4_duckstation_exact_pc_batch.py",
            "sha256": receipt["experiment"]["adapter_source_sha256"],
        },
        "settings_snapshot": _ref(paths["settings.json"], run),
        "owned_pid_cleanup": _ref(paths["cleanup.json"], run),
    }
    preservation = run / "preservation.json"
    preserved_paths = list(paths.values()) + [
        metrics.ROOT / "tools/phase4_duckstation_exact_pc_batch.py",
    ]
    entries = {}
    for preserved in preserved_paths:
        digest = _sha(preserved)
        entries[digest] = {
            "sha256": digest,
            "size": preserved.stat().st_size,
            "media_class": (
                "tool_source" if preserved.suffix == ".py"
                else "runtime_receipt"
            ),
            "preservation_required": True,
        }
    _write_json(preservation, {
        "schema": "abl-phase4-method-external-preservation/1",
        "complete": True, "errors": [], "entries": list(entries.values()),
    })
    receipt["evidence"]["external_preservation_manifest"] = _ref(
        preservation, run)
    _write_json(receipt_path, receipt)
    return run, receipt_path, receipt, ledger, after_ledger, legacy_index


def _full_direct_two_pc_fixture(tmp_path: Path):
    run, receipt_path, receipt, ledger, after_ledger, legacy_index = \
        _full_direct_exact_pc_fixture(tmp_path)
    plan = copy.deepcopy(two_pc_boundary.CONFIGURATION["first_hit_plan"])
    session_id = "owned-two-pc-session"
    direct = two_pc_adapter.execute_first_hit(
        two_pc_boundary.SyntheticRpc(0), plan, session_id,
        plan["identity_join"], sleep=lambda _seconds: None)
    paths = {
        name: run / name
        for name in (
            "observer.json", "perturbation.json", "control.json", "raw.json",
            "pages.json", "media.json", "events.json", "settings.json",
            "cleanup.json",
        )
    }
    observer = {
        "schema": "abl-phase4-observer-plan/2",
        "operations": [
            {
                "sequence": row["sequence"],
                "method": row["method"],
                "args": row["params"],
            }
            for row in plan["breakpoint_sequence"]
        ],
        "result_limits": two_pc_adapter.observer_result_limits(plan),
        "direct_command_plan": plan,
    }
    _write_json(paths["observer.json"], observer)
    observer_sha = _sha(paths["observer.json"])
    perturbation_sha = _sha(paths["perturbation.json"])
    receipt["experiment"].update({
        "execution": {
            "bound": {
                "clock": "emulator_frame", "start": 0, "stop": 15856,
                "stop_inclusive": False,
            },
            "capture_window": {
                "clock": "emulator_frame", "start": 15792, "stop": 15856,
                "stop_inclusive": False,
            },
        },
        "domain": "interface",
        "observer_plan_sha256": observer_sha,
        "perturbation_plan_sha256": perturbation_sha,
        "adapter_source_sha256": _sha(
            metrics.ROOT / "tools/phase4_duckstation_two_pc_first_hit.py"),
    })
    control = json.loads(paths["control.json"].read_text())
    control["only_difference_plan_sha256"] = perturbation_sha
    control["paired_run_basis_sha256"] = hashlib.sha256(
        metrics.canonical_bytes({
            key: value for key, value in receipt["experiment"].items()
            if key not in {"executor_role", "control_plan_sha256"}
        })).hexdigest()
    _write_json(paths["control.json"], control)
    control_sha = _sha(paths["control.json"])
    receipt["experiment"]["control_plan_sha256"] = control_sha

    raw = json.loads(paths["raw.json"].read_text())
    raw["sessions"][0]["server_session_id"] = session_id
    raw["counters"].update({
        "server_session_id": session_id,
        "replay_frames": 15792,
    })
    raw["results"][0].update({
        "server_session_id": session_id,
        "replay_stop": 15792,
        "observer_start": 15792,
        "observer_stop": 15792,
    })
    _write_json(paths["raw.json"], raw)
    _write_json(paths["pages.json"], {
        "schema": "abl-phase4-live-pagination/1",
        "complete": True, "errors": [], "truncated": False,
        "pages_complete": True, "pages": [],
    })
    media = json.loads(paths["media.json"].read_text())
    for method in two_pc_adapter.REQUIRED_METHODS:
        media["capabilities"]["method_schemas"].setdefault(
            method, hashlib.sha256(method.encode()).hexdigest())
    _write_json(paths["media.json"], media)

    anchor = receipt["experiment"]["anchor"]
    atomic_plan_sha256 = hashlib.sha256(metrics.canonical_bytes({
        "anchor": anchor,
        "execution": receipt["experiment"]["execution"],
        "observer_plan_sha256": observer_sha,
        "perturbation_plan_sha256": perturbation_sha,
        "control_plan_sha256": control_sha,
    })).hexdigest()
    old_events = json.loads(paths["events.json"].read_text())["events"]
    identity_events = copy.deepcopy(old_events[:5])
    for event in identity_events:
        event["server_session_id"] = session_id
    identity_events[0]["result"]["method_schemas"] = \
        media["capabilities"]["method_schemas"]
    identity_events[0]["result_sha256"] = hashlib.sha256(
        metrics.canonical_bytes(identity_events[0]["result"])).hexdigest()
    identity_events[3]["params"]["plan_sha256"] = atomic_plan_sha256
    identity_events[3]["result_sha256"] = hashlib.sha256(
        metrics.canonical_bytes(identity_events[3]["result"])).hexdigest()
    events = [
        {**event, "sequence": index}
        for index, event in enumerate(identity_events)
    ]
    event_count = len(events)
    events.extend(
        {**event, "sequence": event_count + index}
        for index, event in enumerate(direct["command_events"]["events"])
    )
    _write_json(paths["events.json"], {
        "schema": "abl-phase4-live-command-events/1",
        "complete": True, "errors": [], "events": events,
    })

    prelude_path = run / "prelude.json"
    prelude = json.loads(prelude_path.read_text())
    prelude["experiment"]["domain"] = "interface"
    prelude["experiment"]["execution"] = {
        "bound": {
            "clock": "emulator_frame", "start": 0, "stop": 15872,
            "stop_inclusive": False,
        },
        "capture_window": {
            "clock": "emulator_frame", "start": 15776,
            "stop": 15872, "stop_inclusive": False,
        },
    }
    _write_json(prelude_path, prelude)
    receipt["prelude_receipt"] = _ref(prelude_path, run)
    receipt["evidence"].update({
        "raw_results": _ref(paths["raw.json"], run),
        "pagination": _ref(paths["pages.json"], run),
        "media_capabilities": _ref(paths["media.json"], run),
        "command_events": _ref(paths["events.json"], run),
        "observer_plan": _ref(paths["observer.json"], run),
        "control_plan": _ref(paths["control.json"], run),
        "adapter_source": {
            "scope": "repo",
            "path": "tools/phase4_duckstation_two_pc_first_hit.py",
            "sha256": receipt["experiment"]["adapter_source_sha256"],
        },
    })
    preservation = run / "preservation.json"
    preserved_paths = list(paths.values()) + [
        metrics.ROOT / "tools/phase4_duckstation_two_pc_first_hit.py",
    ]
    entries = {}
    for preserved in preserved_paths:
        digest = _sha(preserved)
        entries[digest] = {
            "sha256": digest,
            "size": preserved.stat().st_size,
            "media_class": (
                "tool_source" if preserved.suffix == ".py"
                else "runtime_receipt"
            ),
            "preservation_required": True,
        }
    _write_json(preservation, {
        "schema": "abl-phase4-method-external-preservation/1",
        "complete": True, "errors": [], "entries": list(entries.values()),
    })
    receipt["evidence"]["external_preservation_manifest"] = _ref(
        preservation, run)
    _write_json(receipt_path, receipt)
    return run, receipt_path, receipt, ledger, after_ledger, legacy_index


def test_full_direct_exact_pc_receipt_is_admitted_by_outer_validator(tmp_path):
    run, path, receipt, ledger, after_ledger, legacy_index = \
        _full_direct_exact_pc_fixture(tmp_path)
    verifier = {
        "verified_live_receipt_sha256s": [_sha(path)],
        "method_exceptions": [],
    }
    result = metrics._validate_live_receipt(
        path, receipt, run, metrics.ROOT, ledger, after_ledger,
        ["E15_fmv"], verifier, legacy_index, "live")
    assert result["precise"] is True


def test_full_direct_two_pc_receipt_is_admitted_by_outer_validator(tmp_path):
    run, path, receipt, ledger, after_ledger, legacy_index = \
        _full_direct_two_pc_fixture(tmp_path)
    verifier = {
        "verified_live_receipt_sha256s": [_sha(path)],
        "method_exceptions": [],
    }
    result = metrics._validate_live_receipt(
        path, receipt, run, metrics.ROOT, ledger, after_ledger,
        ["E15_fmv"], verifier, legacy_index, "live")
    assert result["precise"] is True
    assert result["counters"]["replay_frames"] == 15792


def test_normalized_legacy_interface_observer_does_not_block_new_dma(
        tmp_path):
    run, path, receipt, ledger, after_ledger, _legacy_index = \
        _full_direct_exact_pc_fixture(tmp_path)
    normalized = {
        "escalation_id": "P4-OLD-INTERFACE",
        "target_row": "E15_fmv",
        "media_sha256": metrics.PRISTINE_MEDIA_SHA256,
        "movie_sha256": receipt["experiment"]["anchor"]["movie_sha256"],
        "state_sha256": None,
        "normalization": "normalized",
        "domain": "interface",
    }
    verifier = {
        "verified_live_receipt_sha256s": [_sha(path)],
        "method_exceptions": [],
    }
    result = metrics._validate_live_receipt(
        path, receipt, run, metrics.ROOT, ledger, after_ledger,
        ["E15_fmv"], verifier, {"entries": [normalized]}, "live")
    assert result["precise"] is True
    blocked = {**normalized, "domain": "dma"}
    with pytest.raises(metrics.MetricsError, match="conservative pre-v2 deny"):
        metrics._validate_live_receipt(
            path, receipt, run, metrics.ROOT, ledger, after_ledger,
            ["E15_fmv"], verifier, {"entries": [blocked]}, "live")
    assert result["counters"] == {
        "server_session_id": "owned-exact-pc-session",
        "launches": 1,
        "atomic_jobs": 1,
        "replay_frames": 15816,
        "observer_frames": 0,
        "instructions": 0,
    }


def test_strict_live_receipt_recomputes_plans_media_cleanup_and_counters(tmp_path):
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(tmp_path)
    verifier = {
        "verified_live_receipt_sha256s": [_sha(path)],
        "method_exceptions": [],
    }
    result = metrics._validate_live_receipt(
        path, receipt, run, repo, ledger, after_ledger,
        ["E15_fmv"], verifier, legacy, "live")
    assert result["counters"]["launches"] == 1
    assert result["external_bytes"] > 0


def test_one_predeclared_escalation_admits_distinct_same_iteration_receipts():
    receipts = [
        {
            "executor_role": "investigator",
            "semantic_key": "menu-v1-prelude",
            "escalation_id": "P4-MENU-COVERAGE",
        },
        {
            "executor_role": "investigator",
            "semantic_key": "menu-v1-precise",
            "escalation_id": "P4-MENU-COVERAGE",
        },
        {
            "executor_role": "investigator",
            "semantic_key": "menu-v2-precise",
            "escalation_id": "P4-MENU-COVERAGE",
        },
    ]
    seen_keys: set[str] = set()
    seen_escalations: set[str] = set()
    duplicates = metrics._admit_iteration_live_receipts(
        receipts, seen_keys, seen_escalations)
    assert duplicates == []
    assert seen_keys == {
        "menu-v1-prelude", "menu-v1-precise", "menu-v2-precise",
    }
    assert seen_escalations == {"P4-MENU-COVERAGE"}

    with pytest.raises(
            metrics.MetricsError, match="investigator escalation was reused"):
        metrics._admit_iteration_live_receipts(
            [{
                "executor_role": "investigator",
                "semantic_key": "later-iteration",
                "escalation_id": "P4-MENU-COVERAGE",
            }],
            seen_keys, seen_escalations)


def test_same_iteration_live_receipts_still_reject_semantic_duplicates():
    with pytest.raises(
            metrics.MetricsError,
            match="duplicate investigator live experiments"):
        metrics._admit_iteration_live_receipts(
            [
                {
                    "executor_role": "investigator",
                    "semantic_key": "same-experiment",
                    "escalation_id": "P4-FIRST",
                },
                {
                    "executor_role": "investigator",
                    "semantic_key": "same-experiment",
                    "escalation_id": "P4-SECOND",
                },
            ],
            set(), set())


def test_live_receipt_requires_atomic_command_job_join(tmp_path):
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(
        tmp_path)
    events_path = run / "events.json"
    events = json.loads(events_path.read_text(encoding="utf-8"))
    events["events"] = [
        item for item in events["events"]
        if item["method"] not in {"scenario.runBatch", "scenario.getBatch"}
    ]
    for sequence, event in enumerate(events["events"]):
        event["sequence"] = sequence
    _write_json(events_path, events)
    receipt["evidence"]["command_events"]["sha256"] = _sha(events_path)
    with pytest.raises(metrics.MetricsError, match="atomic execution events missing"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")


def test_live_receipt_rejects_batch_order_duplicate_identity_and_unbounded_counters(
        tmp_path):
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(
        tmp_path)
    events = json.loads((run / "events.json").read_text(encoding="utf-8"))
    run_index = next(
        index for index, item in enumerate(events["events"])
        if item["method"] == "scenario.runBatch")
    get_index = next(
        index for index, item in enumerate(events["events"])
        if item["method"] == "scenario.getBatch")
    events["events"][run_index], events["events"][get_index] = \
        events["events"][get_index], events["events"][run_index]
    for sequence, event in enumerate(events["events"]):
        event["sequence"] = sequence
    _write_json(run / "events.json", events)
    receipt["evidence"]["command_events"]["sha256"] = _sha(run / "events.json")
    with pytest.raises(metrics.MetricsError, match="getBatch precedes"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")

    run, _repo, _path, _receipt, _ledger, _after, _legacy = \
        _strict_live_fixture(tmp_path / "duplicate-identity")
    events = json.loads((run / "events.json").read_text(encoding="utf-8"))
    duplicate = dict(events["events"][1])
    duplicate["sequence"] = len(events["events"])
    duplicate["result"] = {"game_serial": "WRONG"}
    duplicate["result_sha256"] = hashlib.sha256(
        metrics.canonical_bytes(duplicate["result"])).hexdigest()
    events["events"].append(duplicate)
    with pytest.raises(metrics.MetricsError, match="exactly once"):
        metrics._validate_result_doc(
            events, "abl-phase4-live-command-events/1", "events")

    run, _repo, _path, _receipt, _ledger, _after, _legacy = \
        _strict_live_fixture(tmp_path / "unbounded")
    raw = json.loads((run / "raw.json").read_text(encoding="utf-8"))
    raw["results"][0]["replay_stop"] = metrics.MAX_CLOCK_VALUE + 1
    with pytest.raises(metrics.MetricsError, match="typed clock bound"):
        metrics._validate_result_doc(
            raw, "abl-phase4-live-raw-results/1", "raw")

    with pytest.raises(metrics.MetricsError, match="central anchor fixture manifest"):
        metrics._validate_anchor_fixtures({
            "movie_sha256": "e" * 64, "state_sha256": None,
        }, tmp_path / "no-fixtures", "anchor")

    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(
        tmp_path / "settings")
    receipt["experiment"]["anchor"]["settings_sha256"] = "f" * 64
    with pytest.raises(metrics.MetricsError, match="settings snapshot"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")


def test_live_receipt_without_preplanned_missing_fact_is_rejected(tmp_path):
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(tmp_path)
    ledger["entries"][0]["state"] = "executed"
    with pytest.raises(metrics.MetricsError, match="pre-planned"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")


def test_live_receipt_overlapping_legacy_deny_is_rejected(tmp_path):
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(tmp_path)
    legacy["entries"] = [{
        "escalation_id": "OLD", "target_row": "E15_fmv",
        "media_sha256": metrics.PRISTINE_MEDIA_SHA256, "movie_sha256": None,
        "state_sha256": None,
    }]
    with pytest.raises(metrics.MetricsError, match="pre-v2 deny"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")


def test_live_receipt_rejects_fake_method_out_of_bound_capture_and_overflow(tmp_path):
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(
        tmp_path)
    observer_path = run / "observer.json"
    observer = json.loads(observer_path.read_text(encoding="utf-8"))
    observer["operations"][0]["method"] = "debugger.FakeMethod"
    _write_json(observer_path, observer)
    receipt["evidence"]["observer_plan"]["sha256"] = _sha(observer_path)
    receipt["experiment"]["observer_plan_sha256"] = _sha(observer_path)
    with pytest.raises(metrics.MetricsError, match="method is not closed"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")

    bounds = tmp_path / "bounds"
    bounds.mkdir()
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(
        bounds)
    receipt["experiment"]["execution"]["capture_window"]["stop"] = 41
    with pytest.raises(metrics.MetricsError, match="outside"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")

    perturb = {"schema": "abl-phase4-perturbation-plan/1",
               "kind": "operations", "operations": [{
                   "sequence": 0, "kind": "memory_write", "address": 1,
                   "width_bits": 8, "before": 256, "after": 0,
               }]}
    with pytest.raises(metrics.MetricsError, match="exceeds its width"):
        metrics._validate_perturbation_plan(perturb, "perturb")


def test_live_receipt_rejects_authored_counters_and_normal_profile(tmp_path):
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(
        tmp_path)
    raw_path = run / "raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["counters"]["launches"] = 99
    _write_json(raw_path, raw)
    receipt["evidence"]["raw_results"]["sha256"] = _sha(raw_path)
    with pytest.raises(metrics.MetricsError, match="not derived|preservation"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")


def test_live_receipt_rejects_fabricated_authority_and_duplicate_jobs(tmp_path):
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(
        tmp_path)
    media_path = run / "media.json"
    media = json.loads(media_path.read_text(encoding="utf-8"))
    media["duckstation_source_sha256"] = "f" * 64
    _write_json(media_path, media)
    receipt["evidence"]["media_capabilities"]["sha256"] = _sha(media_path)
    with pytest.raises(metrics.MetricsError, match="source identity"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")

    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(
        tmp_path / "duplicate")
    raw_path = run / "raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["results"].append(dict(raw["results"][0]))
    raw["counters"]["atomic_jobs"] = 2
    raw["counters"]["replay_frames"] = 80
    raw["counters"]["observer_frames"] = 16
    raw["counters"]["instructions"] = 24
    _write_json(raw_path, raw)
    receipt["evidence"]["raw_results"]["sha256"] = _sha(raw_path)
    with pytest.raises(metrics.MetricsError, match="duplicate raw job"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")

    profile = tmp_path / "profile"
    profile.mkdir()
    run, repo, path, receipt, ledger, after_ledger, legacy = _strict_live_fixture(
        profile)
    cleanup_path = run / "cleanup.json"
    cleanup = json.loads(cleanup_path.read_text(encoding="utf-8"))
    cleanup["config_dir"] = str(Path.home() / ".config" / "duckstation")
    _write_json(cleanup_path, cleanup)
    receipt["evidence"]["owned_pid_cleanup"]["sha256"] = _sha(cleanup_path)
    with pytest.raises(metrics.MetricsError, match="profile is forbidden"):
        metrics._validate_live_receipt(
            path, receipt, run, repo, ledger, after_ledger,
            ["E15_fmv"], None, legacy, "live")


def test_gap_free_verifier_requires_substantive_independent_evidence():
    commit = "1" * 40
    decision = {
        "phase": 4, "status": "open_autonomous", "summary": "",
        "gaps": [], "gap_codes": [],
        "falsifier_results": [
            {"id": "one", "outcome": "survived", "evidence": ""},
        ],
        "verified_live_receipt_sha256s": [], "method_exceptions": [],
        "evidence": [], "validation": [], "required_input": "",
        "candidate_commit": commit,
    }
    with pytest.raises(metrics.MetricsError, match="falsifier|summary|gap-free"):
        metrics._validate_verifier_decision(decision, commit, "verifier")

    decision.update({
        "summary": "adverse prose pretending to be evidence",
        "falsifier_results": [
            {"id": "one", "outcome": "survived", "evidence": "not run"},
            {"id": "two", "outcome": "survived", "evidence": "missing"},
        ],
        "evidence": ["all evidence missing"],
        "validation": ["pytest exit 1"],
    })
    with pytest.raises(metrics.MetricsError, match="without roots"):
        metrics._validate_verifier_decision(decision, commit, "verifier")


def test_offline_receipt_requires_tracked_reader_command_inputs_and_outputs(
        tmp_path):
    repo = tmp_path / "repo"
    run = tmp_path / "run"
    (repo / "tools").mkdir(parents=True)
    run.mkdir()
    reader = repo / "tools" / "phase4_test_query.py"
    reader.write_text(
        "import argparse, pathlib\n"
        "ap=argparse.ArgumentParser()\n"
        "ap.add_argument('--input', required=True)\n"
        "ap.add_argument('--output', required=True)\n"
        "ap.add_argument('--query-json', required=True)\n"
        "a=ap.parse_args()\n"
        "assert pathlib.Path(a.input).read_bytes() == b'pinned input'\n"
        "assert a.query_json\n"
        "pathlib.Path(a.output).write_text('{\"result\":1}\\n')\n"
        "print('PASS: offline query')\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "tools/phase4_test_query.py"],
                   cwd=repo, check=True)
    external = run / "capsule.index"
    output = run / "result.json"
    external.write_bytes(b"pinned input")
    output.write_text('{"result":1}\n')
    preservation = run / "preservation.json"
    entries = [
        {
            "sha256": _sha(item), "size": item.stat().st_size,
            "media_class": "derived_pristine_evidence",
            "preservation_required": True,
        }
        for item in (external, output)
    ]
    _write_json(preservation, {
        "schema": "abl-phase4-method-external-preservation/1",
        "complete": True, "errors": [], "entries": entries,
    })
    ref = lambda path: {"scope": "run", "path": path.name, "sha256": _sha(path)}
    receipt = {
        "schema": "abl-phase4-offline-query/1",
        "complete": True, "errors": [],
        "reader": {
            "scope": "repo", "path": "tools/phase4_test_query.py",
            "sha256": _sha(reader),
        },
        "command": [
            "python3", "tools/phase4_test_query.py",
            "--input", "@run/capsule.index",
            "--output", "@run/result.json",
            "--query-json", "@query",
        ],
        "execution": {
            "exit_code": 0,
            "stdout": "PASS: offline query\n",
            "stdout_sha256": hashlib.sha256(
                b"PASS: offline query\n").hexdigest(),
        },
        "query": {"row": "E15_fmv", "window": [10, 20]},
        "external_inputs": [ref(external)],
        "outputs": [ref(output)],
        "external_preservation_manifest": ref(preservation),
    }
    result = metrics._validate_offline_receipt(receipt, run, repo, "offline")
    assert result["external_bytes"] == external.stat().st_size
    assert result["external_inputs"] == {_sha(external): external.stat().st_size}

    receipt["external_inputs"] = []
    with pytest.raises(metrics.MetricsError, match="external_inputs"):
        metrics._validate_offline_receipt(receipt, run, repo, "offline")

    receipt["external_inputs"] = [ref(external)]
    receipt["command"][1] = "tools/phase4_other.py"
    with pytest.raises(metrics.MetricsError, match="pinned reader"):
        metrics._validate_offline_receipt(receipt, run, repo, "offline")

    receipt["command"][1] = "tools/phase4_test_query.py"
    receipt["command"].extend(["--scan-root", "/"])
    with pytest.raises(metrics.MetricsError, match="unbounded path"):
        metrics._validate_offline_receipt(receipt, run, repo, "offline")

    receipt["command"] = receipt["command"][:-2]
    preservation_doc = json.loads(preservation.read_text(encoding="utf-8"))
    preservation_doc["entries"][0]["media_class"] = "non_pristine"
    _write_json(preservation, preservation_doc)
    receipt["external_preservation_manifest"] = ref(preservation)
    with pytest.raises(metrics.MetricsError, match="not pristine-authority"):
        metrics._validate_offline_receipt(receipt, run, repo, "offline")


def test_fixed_report_output_rejects_reproducible_adverse_text():
    with pytest.raises(metrics.MetricsError, match="reports failure"):
        metrics._validate_fixed_check_output(
            [metrics.sys.executable, "tools/validate_vault.py", "--check"],
            "FAIL: injected semantic validation failure\n", 0, "vault")
    with pytest.raises(metrics.MetricsError, match="reports failure"):
        metrics._validate_fixed_check_output(
            [metrics.sys.executable, "tools/validate_vault.py", "--check"],
            "ObsidianVault consistency report\n1 failed, 7 passed\n", 0,
            "vault")


def test_fixed_report_output_canonicalizes_both_pytest_duration_formats():
    first = "62 passed in 74.77s (0:01:14)\n"
    second = "62 passed in 75.25s (0:01:15)\n"
    assert metrics._canonical_check_output(first) == \
        metrics._canonical_check_output(second)
    assert "62 passed" in metrics._canonical_check_output(first)
    assert metrics._canonical_check_output("61 passed in 74.77s (0:01:14)\n") != \
        metrics._canonical_check_output(first)


def test_promotion_rejects_trivial_guard_and_unrelated_schema(tmp_path):
    repo = tmp_path / "repo"
    files = {
        "tools/phase4_fake_gen.py": "# output: analysis/artifact.json\n",
        "tests/test_fake_guard.py": "def test_fake():\n    assert True\n",
        "config/unrelated.yaml": "unrelated: true\n",
        "ObsidianVault/Canon/c.md": "canon\n",
        "ObsidianVault/Experiments/e.md": "experiment\n",
        "ObsidianVault/Mods/m.md": "mods\n",
    }
    for rel, body in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    source_sha = _sha(repo / "config/unrelated.yaml")
    (repo / "analysis").mkdir(parents=True, exist_ok=True)
    _write_json(repo / "analysis/artifact.json", {
        "value": 1, "source_sha": source_sha,
    })
    files["analysis/artifact.json"] = ""
    _write_json(repo / "analysis/phase4_campaign_inventory.json", {
        "generators": {"tools/phase4_fake_gen.py": {
            "tracked": True, "sha256": _sha(repo / "tools/phase4_fake_gen.py"),
            "outputs": [{"path": "analysis/artifact.json"}],
        }},
        "tests": ["tests/test_fake_guard.py"],
    })
    claim = {
        "claim": "met",
        "evidence": [{
            "artifact": "analysis/artifact.json",
            "sha256": _sha(repo / "analysis/artifact.json"),
            "json_path": "value", "op": "eq", "expected": 1,
        }],
        "authoritative_paths": list(files),
        "knowledge_bindings": [{
            "artifact": "analysis/artifact.json",
            "producer": "tools/phase4_fake_gen.py",
            "semantic_sources": [{
                "path": "config/unrelated.yaml",
                "sha256": source_sha,
                "artifact_json_path": "source_sha",
            }],
            "guard_nodes": ["tests/test_fake_guard.py::test_fake"],
        }],
        "residuals": [],
    }
    (repo / "config/phase4_campaigns.yaml").write_text(yaml.safe_dump({
        "child_campaigns": [{
            "id": "salted", "rows": ["R"],
            "note": "ObsidianVault/Canon/c.md",
            "mods_disposition": "applicable",
            "dimension_claims": {"behavior": claim},
        }],
    }))
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    after = {
        "schema": "abl-phase4-closure-debt/1", "valid": True, "errors": [],
        "rows": [{"row_id": "R"}] + [
            {"row_id": f"D{index}"} for index in range(106)
        ],
    }
    with pytest.raises(
            metrics.MetricsError,
            match="does not reject artifact drift"):
        metrics._derive_knowledge_join(
            repo, "salted", {
                "rows": [],
                "dimensions": [["R", "behavior", "partial", "met"]],
                "demotions": [],
            }, after, {"joined": True}, {"complete": True})


def test_controller_event_stream_requires_exact_monotonic_lifecycle(tmp_path):
    path = tmp_path / "events.json"
    base = "1" * 40
    tested = "2" * 40
    events = [
        {"sequence": 0, "at": "2026-07-26T00:00:00Z",
         "type": "iteration_started", "payload": {"base_commit": base}},
        {"sequence": 1, "at": "2026-07-26T00:00:01Z",
         "type": "executor_finished",
         "payload": {"status": "open_autonomous",
                     "candidate_commit": tested}},
        {"sequence": 2, "at": "2026-07-26T00:00:02Z",
         "type": "iteration_reports_started",
         "payload": {"tested_commit": tested}},
        {"sequence": 3, "at": "2026-07-26T00:00:03Z",
         "type": "iteration_completed",
         "payload": {"tested_commit": tested}},
    ]
    _write_json(path, {
        "schema": "abl-phase4-controller-events/1",
        "iteration": 1, "events": events,
    })
    parsed, _, _ = metrics._event_document(path, 1, base, tested)
    assert [item["type"] for item in parsed] == [
        "iteration_started", "executor_finished",
        "iteration_reports_started", "iteration_completed",
    ]

    events.pop(1)
    for index, event in enumerate(events):
        event["sequence"] = index
    _write_json(path, {
        "schema": "abl-phase4-controller-events/1",
        "iteration": 1, "events": events,
    })
    with pytest.raises(metrics.MetricsError, match="lifecycle"):
        metrics._event_document(path, 1, base, tested)


def test_infrastructure_event_requires_expected_iteration_code_and_cleanup(tmp_path):
    path = tmp_path / "events.json"
    _write_json(path, {
        "schema": "abl-phase4-controller-events/1", "iteration": 999,
        "events": [
            {"sequence": 0, "at": "2026-07-26T00:00:00Z",
             "type": "iteration_started",
             "payload": {"base_commit": "1" * 40}},
            {"sequence": 1, "at": "2026-07-26T00:00:01Z",
             "type": "infrastructure_failure", "payload": {}},
        ],
    })
    with pytest.raises(metrics.MetricsError, match="iteration disagrees"):
        metrics._event_document(path, 1)
    with pytest.raises(metrics.MetricsError, match="key mismatch"):
        metrics._event_document(path, 999)


def test_report_completeness_is_recomputed_from_exit_and_output(tmp_path):
    output = "ok\n"
    report = tmp_path / "report.json"
    doc = {
        "schema": "abl-phase4-validation-report/1",
        "tested_commit": "0" * 40,
        "generated_at": "2026-07-26T00:00:00Z",
        "complete": True, "errors": [],
        "checks": [{
            "command": ["true"],
            "started_at": "2026-07-26T00:00:00Z",
            "finished_at": "2026-07-26T00:00:01Z",
            "exit_code": 1, "accepted_exit_codes": [0], "ok": True,
            "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
            "output": output, "output_tail": output,
        }],
    }
    _write_json(report, doc)
    with pytest.raises(metrics.MetricsError, match="fixed contract|authored ok"):
        metrics._closed_report(
            report, "abl-phase4-validation-report/1",
            "0" * 40, tmp_path, tmp_path)


def test_movie_ready_scheduler_handoff_requires_rotation_without_debt_drift():
    def snapshot(campaign, rows):
        return {
            "schema": "abl-phase4-closure-debt/1",
            "valid": True,
            "errors": [],
            "rows": [{"row_id": "stable", "counts": {"remaining": 1}}],
            "scheduler": {"selected_campaigns": [{
                "campaign_id": campaign, "rows": rows,
            }]},
        }

    old = snapshot("movie-ready:E08+E10", ["E08", "E10"])
    new = snapshot("movie-ready:D11", ["D11"])
    progress = {
        "campaign_id": "movie-ready:E08+E10",
        "row_ids": ["E08", "E10"],
        "row_transitions": [],
        "dimension_transitions": [],
        "demotions": [],
    }
    assert metrics._movie_ready_scheduler_handoff(old, new, progress)

    overlapping = snapshot("movie-ready:E10+D11", ["E10", "D11"])
    assert not metrics._movie_ready_scheduler_handoff(
        old, overlapping, progress)
    drifted = copy.deepcopy(new)
    drifted["rows"][0]["counts"]["remaining"] = 0
    assert not metrics._movie_ready_scheduler_handoff(old, drifted, progress)
