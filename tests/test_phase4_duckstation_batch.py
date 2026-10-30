import copy
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_duckstation_batch as batch


def sample_plan() -> tuple[dict, dict, dict]:
    debt = json.loads(batch.DEBT.read_text())
    capsules = json.loads(batch.CAPSULE_SET.read_text())
    media = capsules["pristine_media"][0]
    tracks = [row for row in capsules["pristine_media"] if row is not media]
    fixture = capsules["capsules"][0]
    operator_root = Path.home() / "Downloads" / "ABL"
    escalations = copy.deepcopy(json.loads(batch.ESCALATIONS.read_text()))
    escalation = escalations["entries"][0]
    escalation["state"] = "planned"
    target = escalation["target_row"]
    target_row = next(row for row in debt["rows"] if row["row_id"] == target)
    selected = {
        "campaign_id": target_row["campaign_id"] or "test-campaign",
        "rows": [target],
    }
    debt = copy.deepcopy(debt)
    next(row for row in debt["rows"] if row["row_id"] == target)[
        "campaign_id"] = selected["campaign_id"]
    debt["scheduler"]["selected_campaigns"] = [selected]
    rpc_manifest = json.loads(batch.RPC_MANIFEST.read_text())
    rpc_source = rpc_manifest["source"]
    release_binary = rpc_manifest["binaries"][
        "build-release/bin/duckstation-qt"]
    plan = {
        "schema": "abl-phase4-duckstation-batch/1",
        "campaign_id": selected["campaign_id"],
        "row_ids": selected["rows"],
        "escalation_ids": [escalation["id"]],
        "expected_media": {
            "path": media["absolute_path"],
            "serial": "SCUS-94288",
            "sha256": media["sha256"],
            "tracks": [{"path": row["absolute_path"], "sha256": row["sha256"]}
                       for row in tracks],
        },
        "expected_debugger": {
            "api_version": "2.1.0",
            "schema_version": "2026-07-18",
            "binary_sha256": release_binary["sha256"],
            "source_revision": rpc_source["revision"],
            "source_dirty": rpc_source["dirty"],
            "dirty_state_hash": rpc_source["dirty_state_hash"],
        },
        "continue_on_error": True,
        "jobs": [
            {
                "id": "positive",
                "recipe": "loadStateAndRun",
                "state_path": str(operator_root / fixture["start_state"]["path"]),
                "auto_select_disc": False,
                "expected_media": {"serial": "SCUS-94288", "sha256": media["sha256"]},
                "movie": {"path": str(operator_root / fixture["movie"])},
                "instrumentation": [
                    {"method": "provenanceLog.start", "params": {"clear": True}}
                ],
                "run": {"frames": 1},
                "capture": {"include_registers": True},
            },
            {
                "id": "negative",
                "recipe": "loadStateAndRun",
                "state_path": str(operator_root / fixture["start_state"]["path"]),
                "auto_select_disc": False,
                "expected_media": {"serial": "SCUS-94288", "sha256": media["sha256"]},
                "instrumentation": [
                    {"method": "provenanceLog.start", "params": {"clear": True}}
                ],
                "run": {"frames": 1},
                "capture": {"include_registers": True},
            },
        ],
        "control_pairs": [{
            "positive_job": "positive", "negative_job": "negative",
            "assertion": "The named positive and negative outcomes must differ only at the declared boundary.",
        }],
    }
    for job in plan["jobs"]:
        job["expected_media"] = plan["expected_media"]
    return plan, debt, escalations


def add_after_load_receipt(plan: dict, escalations: dict) -> dict:
    operation = {
        "kind": "code_write",
        "address": 0x800500D4,
        "original_word": 0x2404002E,
        "replacement_word": 0x24040028,
    }
    plan["jobs"][0]["after_load"] = operation
    plan["v2_receipt"] = {
        "id": "typed-after-load-code-write",
        "missing_fact_id": escalations["entries"][0].get("missing_fact_id"),
        "precise": False,
        "anchor": {
            "kind": "movie_start_state",
            "media_sha256": batch.PRISTINE_TRACK_SHA256,
            "movie_sha256": "1" * 64,
            "state_sha256": "2" * 64,
            "start": {"clock": "emulator_frame", "value": 1},
        },
        "execution": {
            "bound": {
                "clock": "emulator_frame", "start": 1, "stop": 3,
                "stop_inclusive": False,
            },
            "capture_window": {
                "clock": "emulator_frame", "start": 1, "stop": 3,
                "stop_inclusive": False,
            },
        },
        "domain": "native_control",
        "observer_plan": {
            "schema": "abl-phase4-observer-plan/1",
            "operations": [{
                "sequence": 0, "method": "debugger.getRegisters", "args": {},
            }],
            "result_limits": {
                "max_records": 2, "max_bytes": 4096, "max_pages": 1,
            },
        },
        "perturbation_plan": {
            "schema": "abl-phase4-perturbation-plan/1",
            "kind": "operations",
            "operations": [{"sequence": 0, **operation}],
        },
        "control_role": "positive",
        "assertion_plan": {
            "kind": "typed_after_load_code_write",
            "expected_original_word": operation["original_word"],
            "expected_replacement_word": operation["replacement_word"],
        },
        "settings_snapshot": {
            "schema": "abl-duckstation-settings-snapshot/1",
            "profile": "fresh-isolated-defaults-v1",
            "binary_sha256": plan["expected_debugger"]["binary_sha256"],
        },
    }
    return operation


def test_plan_requires_selected_campaign_pristine_media_and_control_pair():
    plan, debt, escalations = sample_plan()
    assert batch.validate_plan(plan, debt_doc=debt,
                               escalation_doc=escalations) == []
    request = batch.make_request(plan)
    assert len(request["jobs"]) == 2
    assert request["continue_on_error"] is True
    expected_after_state_load = batch._scenario_media_identity(plan["expected_media"])
    expected_after_state_load.pop("path")
    assert all(job["expected_media"] == expected_after_state_load
               for job in request["jobs"])
    assert plan["expected_media"]["path"] not in {
        value for job in request["jobs"] for value in job["expected_media"].values()}


def test_plan_rejects_wrong_media_and_unpaired_live_probe():
    plan, debt, escalations = sample_plan()
    plan["expected_media"] = {
        "path": "/missing/pristine.cue", "serial": "WRONG",
        "sha256": "0" * 64, "tracks": [],
    }
    plan["jobs"][0]["expected_media"] = plan["expected_media"]
    plan["jobs"][1]["expected_media"] = plan["expected_media"]
    plan["control_pairs"] = []
    errors = batch.validate_plan(plan, debt_doc=debt,
                                 escalation_doc=escalations)
    assert any("serial must be SCUS-94288" in error for error in errors)
    assert any("not a pinned pristine retail input" in error for error in errors)
    assert any("control pair" in error for error in errors)


def test_plan_rejects_non_atomic_or_unbounded_jobs():
    plan, debt, escalations = sample_plan()
    plan["jobs"][0]["recipe"] = "manualReplay"
    plan["jobs"][0]["run"] = {"frames": 1, "movie_frame": 2}
    plan["jobs"][0]["instrumentation"] = [
        {"method": "debugger.writeU32", "params": {}}
    ]
    errors = batch.validate_plan(plan, debt_doc=debt,
                                 escalation_doc=escalations)
    assert any("unsupported recipe" in error for error in errors)
    assert any("exactly one execution bound" in error for error in errors)
    assert any("non-arming instrumentation" in error for error in errors)


def test_plan_accepts_runtime_recipe_access_watch_and_rejects_trace_gate():
    plan, debt, escalations = sample_plan()
    plan["jobs"][0]["instrumentation"] = [{
        "method": "accessLog.addWatch",
        "params": {
            "address": "0x800cac10", "length": 4, "type": "write",
            "max_events": 32,
        },
    }]
    assert batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations) == []

    plan["jobs"][0]["instrumentation"][0]["method"] = "trace.armWhen"
    errors = batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations)
    assert any("non-arming instrumentation" in error for error in errors)


def test_control_pair_requires_same_anchor_and_run_bound():
    plan, debt, escalations = sample_plan()
    plan["jobs"][1]["run"] = {"frames": 2}
    errors = batch.validate_plan(plan, debt_doc=debt,
                                 escalation_doc=escalations)
    assert any("same anchor and run bound" in error for error in errors)


def test_load_state_jobs_must_retain_the_verified_mounted_disc():
    plan, debt, escalations = sample_plan()
    plan["jobs"][0]["auto_select_disc"] = True
    errors = batch.validate_plan(plan, debt_doc=debt,
                                 escalation_doc=escalations)
    assert any("retain the verified mounted disc" in error for error in errors)
    assert any("same anchor and run bound" in error for error in errors)


def test_typed_after_load_code_write_is_single_paired_and_receipt_bound():
    plan, debt, escalations = sample_plan()
    operation = add_after_load_receipt(plan, escalations)
    assert batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations) == []
    request = batch.make_request(plan)
    assert request["jobs"][0]["after_load"] == operation
    assert "after_load" not in request["jobs"][1]

    plan["v2_receipt"]["perturbation_plan"]["operations"][0][
        "replacement_word"] = 0x2404002D
    errors = batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations)
    assert any("does not exactly match" in error for error in errors)


def test_typed_after_load_code_write_rejects_unsafe_shapes_and_boot_recipe():
    plan, debt, escalations = sample_plan()
    operation = add_after_load_receipt(plan, escalations)
    plan["jobs"][0]["after_load"] = {**operation, "invalidate_code": False}
    errors = batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations)
    assert any("must contain exactly" in error for error in errors)

    plan, debt, escalations = sample_plan()
    add_after_load_receipt(plan, escalations)
    plan["jobs"][0]["after_load"]["replacement_word"] = 0x2404002E
    plan["v2_receipt"]["perturbation_plan"]["operations"][0][
        "replacement_word"] = 0x2404002E
    errors = batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations)
    assert any("code words must differ" in error for error in errors)

    plan, debt, escalations = sample_plan()
    add_after_load_receipt(plan, escalations)
    plan["jobs"][0]["recipe"] = "bootAndRun"
    plan["jobs"][0]["media_path"] = plan["expected_media"]["path"]
    errors = batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations)
    assert any("valid only for loadStateAndRun" in error for error in errors)


def test_e15_c16_selector_plans_are_retired_until_atomic_staging_exists():
    passive = yaml.safe_load((
        ROOT / "config/phase4_fmv_c16_selector_passive_batch.yaml").read_text())
    precise = yaml.safe_load((
        ROOT / "config/phase4_fmv_c16_selector_control_batch.yaml").read_text())
    staging_error = "nonzero movie-frame capture requires one atomic staged_prelude"
    assert any(staging_error in error for error in batch.validate_plan(
        passive, allow_executed=True))
    assert any(staging_error in error for error in batch.validate_plan(
        precise, allow_executed=True))
    assert passive["escalation_ids"] == precise["escalation_ids"] == [
        "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL",
    ]
    assert passive["expected_debugger"] == precise["expected_debugger"]
    assert passive["expected_debugger"]["binary_sha256"] == \
        "3735016cd206e1915a49d980016e064d40efc83aa8253eac8f60338906c712de"
    operation = {
        "kind": "code_write",
        "address": 0x800500D4,
        "original_word": 0x2404002E,
        "replacement_word": 0x24040028,
    }
    assert precise["jobs"][0]["after_load"] == operation
    assert "after_load" not in precise["jobs"][1]
    assert precise["v2_receipt"]["perturbation_plan"]["operations"] == [
        {"sequence": 0, **operation},
    ]
    prior = passive["v2_receipt"]["execution"]["capture_window"]
    current = precise["v2_receipt"]["execution"]["capture_window"]
    assert prior["clock"] == current["clock"] == "movie_frame"
    assert prior["start"] < current["start"]
    assert prior["stop"] == current["stop"]

    mutated = copy.deepcopy(precise)
    mutated["jobs"][1]["after_load"] = operation
    errors = batch.validate_plan(mutated, allow_executed=True)
    assert any("after_load must be the sole difference" in error
               for error in errors)


def test_atomic_staged_prelude_admits_nonzero_movie_capture_and_stays_paired():
    precise = yaml.safe_load((
        ROOT / "config/phase4_fmv_c16_selector_control_batch.yaml").read_text())
    for job in precise["jobs"]:
        job["staged_prelude"] = {
            "kind": "movie_advance",
            "target_frame": 300,
            "max_frames": 300,
        }
    execution = precise["v2_receipt"]["execution"]
    execution["bound"]["start"] = 0
    execution["capture_window"]["start"] = 300
    errors = batch.validate_plan(precise, allow_executed=True)
    assert not any("staged_prelude" in error for error in errors)
    assert batch.make_request(precise)["jobs"][0]["staged_prelude"] == {
        "kind": "movie_advance",
        "target_frame": 300,
        "max_frames": 300,
    }

    changed = copy.deepcopy(precise)
    changed["jobs"][1]["staged_prelude"]["target_frame"] = 299
    errors = batch.validate_plan(changed, allow_executed=True)
    assert any("capture start differs" in error for error in errors)
    assert any("same anchor and run bound" in error for error in errors)

    changed = copy.deepcopy(precise)
    changed["jobs"][0]["staged_prelude"]["max_frames"] = 299
    errors = batch.validate_plan(changed, allow_executed=True)
    assert any("cannot reach target_frame" in error for error in errors)

    changed = copy.deepcopy(precise)
    changed["jobs"][0]["staged_prelude"]["max_frames"] = 100001
    errors = batch.validate_plan(changed, allow_executed=True)
    assert any("exceeds the debugger recipe limit" in error for error in errors)


def test_fresh_e15_staged_selector_plans_are_predeclared_and_valid():
    passive = yaml.safe_load((
        ROOT / "config/phase4_fmv_c16_staged_selector_passive_batch.yaml"
    ).read_text())
    precise = yaml.safe_load((
        ROOT / "config/phase4_fmv_c16_staged_selector_control_batch.yaml"
    ).read_text())
    expected = [
        "P4-ITER99-E15-C16-STAGED-SELECTOR-LIFECYCLE-CONTROL",
    ]
    assert passive["escalation_ids"] == precise["escalation_ids"] == expected
    # The plans are retained after execution, so the normal guard must reject
    # retrospective reuse while the audit path accepts their exact bytes.
    assert any(
        "requires a current planned escalation" in error
        for error in batch.validate_plan(passive))
    assert any(
        "requires a current planned escalation" in error
        for error in batch.validate_plan(precise))
    assert batch.validate_plan(passive, allow_executed=True) == []
    assert batch.validate_plan(precise, allow_executed=True) == []
    assert {
        job["staged_prelude"]["target_frame"] for job in passive["jobs"]
    } == {299}
    assert {
        job["staged_prelude"]["target_frame"] for job in precise["jobs"]
    } == {300}
    assert passive["v2_receipt"]["execution"] == {
        "bound": {
            "clock": "movie_frame", "start": 0, "stop": 4006,
            "stop_inclusive": False,
        },
        "capture_window": {
            "clock": "movie_frame", "start": 299, "stop": 4006,
            "stop_inclusive": False,
        },
    }
    assert precise["v2_receipt"]["execution"]["bound"]["start"] == 0
    assert precise["v2_receipt"]["execution"]["capture_window"]["start"] == 300
    assert precise["jobs"][0]["after_load"] == {
        "kind": "code_write",
        "address": 0x800500D4,
        "original_word": 0x2404002E,
        "replacement_word": 0x24040028,
    }
    assert "after_load" not in precise["jobs"][1]


def test_e15_decoded_record_control_is_planned_narrow_and_fail_closed():
    passive = yaml.safe_load((
        ROOT / "config/phase4_fmv_decoded_record_passive_batch.yaml"
    ).read_text())
    precise = yaml.safe_load((
        ROOT / "config/phase4_fmv_decoded_record_control_batch.yaml"
    ).read_text())
    expected = [
        "P4-ITER102-E15-DECODED-RECORD-ABSENCE-CONTROL",
    ]
    assert passive["escalation_ids"] == precise["escalation_ids"] == expected
    assert batch.validate_plan(passive, allow_executed=True) == []
    assert batch.validate_plan(precise, allow_executed=True) == []
    assert {
        job["staged_prelude"]["target_frame"] for job in passive["jobs"]
    } == {649}
    assert {
        job["staged_prelude"]["target_frame"] for job in precise["jobs"]
    } == {650}
    prior = passive["v2_receipt"]["execution"]["capture_window"]
    current = precise["v2_receipt"]["execution"]["capture_window"]
    assert prior["clock"] == current["clock"] == "movie_frame"
    assert prior["start"] < current["start"]
    assert current["stop"] < prior["stop"]
    operation = {
        "kind": "code_write",
        "address": 0x800B6C40,
        "original_word": 0x1220000E,
        "replacement_word": 0x1000000E,
    }
    assert precise["jobs"][0]["after_load"] == operation
    assert "after_load" not in precise["jobs"][1]
    assert precise["v2_receipt"]["perturbation_plan"]["operations"] == [
        {"sequence": 0, **operation},
    ]
    assert precise["v2_receipt"]["observer_plan"]["operations"][0]["args"] == {
        "address": 0x800B9A54,
        "length": 1,
        "type": "write",
        "label": "decode_stop_latch",
        "max_events": 32,
        "stop_on_hit": False,
    }

    changed = copy.deepcopy(precise)
    changed["v2_receipt"]["perturbation_plan"]["operations"][0][
        "replacement_word"] = 0x1000000D
    errors = batch.validate_plan(changed)
    assert any("does not exactly match" in error for error in errors)

    changed = copy.deepcopy(precise)
    changed["jobs"][1]["after_load"] = operation
    errors = batch.validate_plan(changed)
    assert any("after_load must be the sole difference" in error
               for error in errors)


def test_e15_completed_retention_successor_is_guarded_against_replay():
    passive = yaml.safe_load((
        ROOT /
        "config/phase4_fmv_decoded_record_retention_passive_batch.yaml"
    ).read_text())
    precise = yaml.safe_load((
        ROOT /
        "config/phase4_fmv_decoded_record_retention_control_batch.yaml"
    ).read_text())
    expected = [
        "P4-ITER104-E15-DECODED-RECORD-RETENTION-CONTROL",
    ]
    assert passive["escalation_ids"] == precise["escalation_ids"] == expected
    replay_error = [
        "P4-ITER104-E15-DECODED-RECORD-RETENTION-CONTROL: "
        "live batch requires a current planned escalation",
    ]
    assert batch.validate_plan(passive) == replay_error
    assert batch.validate_plan(precise) == replay_error
    prior = passive["v2_receipt"]["execution"]["capture_window"]
    current = precise["v2_receipt"]["execution"]["capture_window"]
    assert prior == {
        "clock": "movie_frame", "start": 649, "stop": 900,
        "stop_inclusive": False,
    }
    assert current == {
        "clock": "movie_frame", "start": 650, "stop": 850,
        "stop_inclusive": False,
    }
    assert prior["start"] < current["start"]
    assert current["stop"] < prior["stop"]
    function_operation = precise["v2_receipt"][
        "observer_plan"]["operations"][1]
    assert function_operation["method"] == "functionTrace.start"
    assert function_operation["args"]["max_events"] == 128
    assertion = precise["v2_receipt"]["assertion_plan"]
    assert assertion["retention_source_receipt_sha256"] == \
        "7156595a5e9822afa871075802ccfe0fd7b4f5ef60fc46aa89fe00f72f329b1b"
    assert assertion["prior_emitted_function_events"] == 90
    assert assertion["function_max_events"] == 128
    assert assertion["required_first_function_index"] == 1
    assert assertion["required_last_function_index_lte"] == 90
    assert assertion["required_function_events_lte"] == 90
    assert assertion["require_function_events_lt_max"] is True

    changed = copy.deepcopy(precise)
    changed["jobs"][0]["instrumentation"][1]["params"]["max_events"] = 127
    errors = batch.validate_plan(changed)
    assert any("does not exactly match" in error for error in errors)


def test_e15_executed_function_cardinality_plan_is_finite_and_not_replayable():
    passive = yaml.safe_load((
        ROOT /
        "config/phase4_fmv_present_rect_height_function_passive_batch.yaml"
    ).read_text())
    precise = yaml.safe_load((
        ROOT /
        "config/phase4_fmv_present_rect_height_function_trace_batch.yaml"
    ).read_text())
    expected = [
        "P4-ITER114-E15-PRESENT-RECT-FUNCTION-CARDINALITY",
    ]
    assert passive["escalation_ids"] == precise["escalation_ids"] == expected
    expected_closed_error = [
        "P4-ITER114-E15-PRESENT-RECT-FUNCTION-CARDINALITY: "
        "live batch requires a current planned escalation"
    ]
    assert batch.validate_plan(passive) == expected_closed_error
    assert batch.validate_plan(precise) == expected_closed_error

    prior = passive["v2_receipt"]["execution"]["capture_window"]
    current = precise["v2_receipt"]["execution"]["capture_window"]
    assert prior == {
        "clock": "movie_frame", "start": 150, "stop": 270,
        "stop_inclusive": False,
    }
    assert current == {
        "clock": "movie_frame", "start": 160, "stop": 260,
        "stop_inclusive": False,
    }
    assert prior["start"] < current["start"]
    assert current["stop"] < prior["stop"]

    expected_trace = {
        "functions": [0x800B6A7C],
        "all_symbols": False,
        "capture_memory": False,
        "max_events": 32,
    }
    observer = precise["v2_receipt"]["observer_plan"]["operations"]
    assert observer == [{
        "sequence": 0,
        "method": "functionTrace.start",
        "args": expected_trace,
    }]
    assert all(
        job["instrumentation"] == [{
            "method": "functionTrace.start",
            "params": expected_trace,
        }]
        for job in precise["jobs"]
    )
    assertion = precise["v2_receipt"]["assertion_plan"]
    assert assertion["traced_function"] == 0x800B6A7C
    assert assertion["required_caller"] == 0x800B6C24
    assert assertion["expected_complete_calls"] == 3
    assert assertion["expected_function_events"] == 6
    assert assertion["function_max_events"] == 32
    assert precise["v2_receipt"]["perturbation_plan"] == {
        "schema": "abl-phase4-perturbation-plan/1",
        "kind": "none",
        "operations": [],
    }

    def assert_observer_matches_job_instrumentation(candidate):
        typed_observer = [
            {
                "method": operation["method"],
                "params": operation["args"],
            }
            for operation in candidate["v2_receipt"][
                "observer_plan"]["operations"]
        ]
        assert all(
            job["instrumentation"] == typed_observer
            for job in candidate["jobs"]
        )

    assert_observer_matches_job_instrumentation(precise)
    changed = copy.deepcopy(precise)
    changed["jobs"][0]["instrumentation"][0]["params"]["max_events"] = 31
    with pytest.raises(AssertionError):
        assert_observer_matches_job_instrumentation(changed)


def test_e15_cd_event_exit_control_is_executed_and_one_word_bounded():
    passive = yaml.safe_load((
        ROOT / "config/phase4_fmv_cd_event_exit_passive_batch.yaml"
    ).read_text())
    precise = yaml.safe_load((
        ROOT / "config/phase4_fmv_cd_event_exit_control_batch.yaml"
    ).read_text())
    expected = ["P4-ITER107-E15-CD-EVENT-EXIT-CONTROL"]
    assert passive["escalation_ids"] == precise["escalation_ids"] == expected
    assert batch.validate_plan(passive, allow_executed=True) == []
    assert batch.validate_plan(precise, allow_executed=True) == []
    prior = passive["v2_receipt"]["execution"]["capture_window"]
    current = precise["v2_receipt"]["execution"]["capture_window"]
    assert prior == {
        "clock": "movie_frame", "start": 249, "stop": 340,
        "stop_inclusive": False,
    }
    assert current == {
        "clock": "movie_frame", "start": 250, "stop": 330,
        "stop_inclusive": False,
    }
    assert prior["start"] < current["start"]
    assert current["stop"] < prior["stop"]
    operation = {
        "kind": "code_write",
        "address": 0x800B7420,
        "original_word": 0x8C422484,
        "replacement_word": 0x24020001,
    }
    assert precise["jobs"][0]["after_load"] == operation
    assert "after_load" not in precise["jobs"][1]
    assert precise["v2_receipt"]["perturbation_plan"]["operations"] == [
        {"sequence": 0, **operation},
    ]
    assertion = precise["v2_receipt"]["assertion_plan"]
    assert assertion["excluded_movie_input_before"] == 334
    assert assertion["required_exit_functions"] == [
        0x8006D8E8, 0x8007094C, 0x800709AC]
    assert assertion["expected_negative_exit_sequences"] == 0

    changed = copy.deepcopy(precise)
    changed["jobs"][0]["after_load"]["replacement_word"] = 0x24020002
    errors = batch.validate_plan(changed, allow_executed=True)
    assert any("does not exactly match" in error for error in errors)


def test_boot_jobs_reuse_the_plan_pinned_pristine_media():
    plan, debt, escalations = sample_plan()
    for job in plan["jobs"]:
        job["recipe"] = "bootAndRun"
        job["media_path"] = plan["expected_media"]["path"]
        job["fast_boot"] = True
        job.pop("state_path")
        job.pop("auto_select_disc")

    assert batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations) == []

    plan["jobs"][0]["media_path"] = plan["expected_media"]["tracks"][0]["path"]
    errors = batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations)
    assert any("differs from the plan's pinned pristine media" in error
               for error in errors)


def test_plan_pins_running_debugger_identity():
    plan, debt, escalations = sample_plan()
    plan["expected_debugger"]["binary_sha256"] = "not-a-hash"
    errors = batch.validate_plan(plan, debt_doc=debt,
                                 escalation_doc=escalations)
    assert any("binary_sha256 is invalid" in error for error in errors)


def test_batch_cannot_reuse_a_retrospective_executed_escalation():
    plan, debt, escalations = sample_plan()
    escalations["entries"][0]["state"] = "executed"
    errors = batch.validate_plan(plan, debt_doc=debt,
                                 escalation_doc=escalations)
    assert any("requires a current planned escalation" in error for error in errors)
    assert batch.validate_plan(
        plan, debt_doc=debt, escalation_doc=escalations,
        allow_executed=True) == []


def test_required_runtime_methods_include_batch_atomic_and_provenance():
    assert {
        "scenario.runBatch", "scenario.getBatch", "scenario.loadStateAndRun",
        "scenario.bootAndRun", "capture.atomic", "provenanceLog.start",
        "debugger.capabilities",
    } <= batch.REQUIRED_METHODS
    assert "accessLog.addWatch" in batch.RECIPE_INSTRUMENTATION_METHODS
    assert "trace.armWhen" not in batch.RECIPE_INSTRUMENTATION_METHODS
    assert "completed_with_errors" in batch.TERMINAL_BATCH_STATES


def test_menu_owner_receipt_batches_are_atomic_and_strictly_preluded():
    names = (
        "phase4_fmv_menu_v1_passive_batch.yaml",
        "phase4_fmv_menu_v1_owner_batch.yaml",
        "phase4_fmv_menu_v2_passive_batch.yaml",
        "phase4_fmv_menu_v2_owner_batch.yaml",
    )
    plans = {
        name: yaml.safe_load((ROOT / "config" / name).read_text())
        for name in names
    }
    assert all(
        batch.validate_plan(plan, allow_executed=True) == []
        for plan in plans.values())
    for version in ("v1", "v2"):
        passive = plans[f"phase4_fmv_menu_{version}_passive_batch.yaml"]
        precise = plans[f"phase4_fmv_menu_{version}_owner_batch.yaml"]
        prior = passive["v2_receipt"]
        current = precise["v2_receipt"]
        assert prior["precise"] is False
        assert current["precise"] is True
        assert prior["anchor"] == current["anchor"]
        assert prior["domain"] == current["domain"] == "interface"
        prior_window = prior["execution"]["capture_window"]
        current_window = current["execution"]["capture_window"]
        assert current_window["start"] >= prior_window["start"]
        assert current_window["stop"] < prior_window["stop"]
        assert all(
            arm["method"] == "execTrace.addWatch"
            for job in precise["jobs"]
            for arm in job["instrumentation"]
        )
        assert passive["jobs"][0]["movie"] == precise["jobs"][0]["movie"]
        assert passive["jobs"][0]["run"] == precise["jobs"][0]["run"]


def test_menu_owner_receipt_plan_rejects_precision_and_missing_fact_drift():
    plan = yaml.safe_load((
        ROOT / "config/phase4_fmv_menu_v1_owner_batch.yaml").read_text())
    plan["v2_receipt"]["precise"] = "yes"
    errors = batch.validate_plan(plan)
    assert any("precise flag is invalid" in error for error in errors)

    plan = yaml.safe_load((
        ROOT / "config/phase4_fmv_menu_v1_owner_batch.yaml").read_text())
    plan["v2_receipt"]["missing_fact_id"] = "E15/not-the-planned-fact"
    errors = batch.validate_plan(plan)
    assert any("differs from escalation" in error for error in errors)


def test_levelb_dma_preflight_admits_only_complete_atomic_transfer_pagination():
    passive = yaml.safe_load((
        ROOT / "config/phase4_fmv_levelb_region_b_dma_passive_batch.yaml"
    ).read_text())
    precise = yaml.safe_load((
        ROOT / "config/phase4_fmv_levelb_region_b_dma_transfer_batch.yaml"
    ).read_text())

    assert batch.validate_plan(passive, allow_executed=True) == []
    assert batch.validate_plan(precise, allow_executed=True) == []
    assert all(
        job["capture"]["transfer_pagination"] == {
            "page_size": 10000, "max_pages": 10,
        }
        for job in precise["jobs"]
    )

    missing = copy.deepcopy(precise)
    del missing["jobs"][0]["capture"]["transfer_pagination"]
    assert any(
        "capture transfer_pagination must contain exactly" in error
        for error in batch.validate_plan(missing, allow_executed=True)
    )

    undersized = copy.deepcopy(precise)
    undersized["jobs"][0]["capture"]["transfer_pagination"]["max_pages"] = 9
    errors = batch.validate_plan(undersized, allow_executed=True)
    assert any("cannot retain the 100000-event ring" in error for error in errors)
    assert any("differs from typed observer result limits" in error
               for error in errors)

    prior = passive["v2_receipt"]["execution"]["capture_window"]
    current = precise["v2_receipt"]["execution"]["capture_window"]
    assert prior == {
        "clock": "emulator_frame", "start": 0, "stop": 16120,
        "stop_inclusive": False,
    }
    assert current == {
        "clock": "emulator_frame", "start": 0, "stop": 16080,
        "stop_inclusive": False,
    }
    assert current["stop"] < prior["stop"]


def test_transfer_result_requires_exact_ordered_nontruncated_pages():
    plan = {
        "jobs": [
            {
                "id": "native",
                "capture": {
                    "transfer_pagination": {"page_size": 2, "max_pages": 2},
                },
            },
        ],
        "v2_receipt": {
            "observer_plan": {
                "operations": [{"method": "transferLog.start"}],
                "result_limits": {
                    "max_records": 4, "max_pages": 2, "max_bytes": 4096,
                },
            },
            "assertion_plan": {
                "required_first_transfer_index": 1,
                "require_contiguous_indexes": True,
            },
        },
    }
    pagination = {
        "page_size": 2,
        "max_pages": 2,
        "page_count": 2,
        "total": 3,
        "returned": 3,
        "truncated": False,
        "enabled": True,
        "pagination_complete": True,
        "pages": [
            {
                "offset": 0, "limit": 2, "returned": 2,
                "events": [{"index": 1}, {"index": 2}],
            },
            {
                "offset": 2, "limit": 2, "returned": 1,
                "events": [{"index": 3}],
            },
        ],
    }
    result = {
        "jobs": [{
            "id": "native",
            "result": {"capture": {"traces": {
                "transfer_pagination": pagination,
            }}},
        }],
    }
    assert batch._validate_transfer_batch_result(plan, result) == [
        {"job_id": "native", "page": 0, "offset": 0, "record_count": 2},
        {"job_id": "native", "page": 1, "offset": 2, "record_count": 1},
    ]

    for field, value, message in (
        ("truncated", True, "incomplete or truncated"),
        ("pagination_complete", False, "incomplete or truncated"),
        ("total", 4, "exact total"),
    ):
        changed = copy.deepcopy(result)
        changed["jobs"][0]["result"]["capture"]["traces"][
            "transfer_pagination"][field] = value
        with pytest.raises(RuntimeError, match=message):
            batch._validate_transfer_batch_result(plan, changed)

    changed = copy.deepcopy(result)
    changed["jobs"][0]["result"]["capture"]["traces"][
        "transfer_pagination"]["pages"][1]["offset"] = 1
    with pytest.raises(RuntimeError, match="is not contiguous"):
        batch._validate_transfer_batch_result(plan, changed)

    changed = copy.deepcopy(result)
    changed["jobs"][0]["result"]["capture"]["traces"][
        "transfer_pagination"]["pages"][1]["events"][0]["index"] = 4
    with pytest.raises(RuntimeError, match="indexes are not contiguous"):
        batch._validate_transfer_batch_result(plan, changed)


def test_transfer_trace_totals_do_not_double_count_legacy_slice():
    job = {
        "result": {
            "capture": {
                "traces": {
                    "transfers": [{"index": 1}, {"index": 2}],
                    "transfer_pagination": {
                        "total": 3,
                        "truncated": False,
                        "pages": [
                            {"events": [
                                {"index": 1}, {"index": 2}, {"index": 3},
                            ]},
                        ],
                    },
                },
            },
        },
    }
    assert batch._trace_totals(job) == (3, False)

    changed = copy.deepcopy(job)
    changed["result"]["capture"]["traces"]["transfer_pagination"][
        "truncated"] = True
    assert batch._trace_totals(changed) == (3, True)


def test_cold_boot_receipt_rejects_authored_delayed_capture():
    plan = yaml.safe_load((
        ROOT / "config/phase4_fmv_levelb_region_b_dma_passive_batch.yaml"
    ).read_text())
    plan["v2_receipt"]["execution"]["capture_window"]["start"] = 15720
    errors = batch.validate_plan(plan)
    assert any(
        "cold-boot capture must begin at the execution bound" in error
        for error in errors
    )


def test_v2_raw_counters_are_derived_from_completed_atomic_jobs():
    document = {
        "result": {
            "state": "completed",
            "jobs": [
                {
                    "id": "positive", "state": "completed",
                    "result": {
                        "run": {"frames_advanced": 20},
                        "status": {"frame": 21},
                    },
                },
                {
                    "id": "negative", "state": "completed",
                    "result": {
                        "run": {"frames_advanced": 20},
                        "status": {"frame": 21},
                    },
                },
            ],
        },
    }
    raw = batch._raw_result_document(
        document, "owned-session", {
            "bound": {
                "clock": "emulator_frame", "start": 1, "stop": 22,
                "stop_inclusive": False,
            },
            "capture_window": {
                "clock": "emulator_frame", "start": 1, "stop": 22,
                "stop_inclusive": False,
            },
        })
    assert raw["complete"] is True
    assert raw["counters"] == {
        "server_session_id": "owned-session",
        "launches": 1,
        "atomic_jobs": 2,
        "replay_frames": 40,
        "observer_frames": 40,
        "instructions": 0,
    }
    assert [row["replay_start"] for row in raw["results"]] == [1, 1]


def test_v2_movie_counters_reject_unstaged_playback_index():
    document = {
        "result": {
            "state": "completed",
            "jobs": [{
                "id": "positive", "state": "completed",
                "result": {
                    "run": {
                        "frames_advanced": 4006,
                        "start_playback_index": 0,
                        "target_frame": 4006,
                    },
                    "status": {"frame": 269217},
                },
            }],
        },
    }
    with pytest.raises(
            RuntimeError,
            match="observed movie_frame span 0..4006 escapes typed bound"):
        batch._raw_result_document(
            document, "owned-session", {
                "bound": {
                    "clock": "movie_frame", "start": 300, "stop": 4006,
                    "stop_inclusive": False,
                },
                "capture_window": {
                    "clock": "movie_frame", "start": 300, "stop": 4006,
                    "stop_inclusive": False,
                },
            })


def test_v2_movie_counters_join_staged_replay_to_post_prelude_observer():
    document = {
        "result": {
            "state": "completed",
            "jobs": [{
                "id": "positive", "state": "completed",
                "result": {
                    "staged_prelude": {
                        "frames_advanced": 300,
                        "start_playback_index": 0,
                        "target_frame": 300,
                        "movie": {"playback_index": 300},
                    },
                    "run": {
                        "frames_advanced": 3706,
                        "start_playback_index": 300,
                        "target_frame": 4006,
                    },
                    "status": {"frame": 269217},
                },
            }],
        },
    }
    raw = batch._raw_result_document(
        document, "owned-session", {
            "bound": {
                "clock": "movie_frame", "start": 0, "stop": 4006,
                "stop_inclusive": False,
            },
            "capture_window": {
                "clock": "movie_frame", "start": 300, "stop": 4006,
                "stop_inclusive": False,
            },
        })
    assert raw["results"][0] == {
        "job_id": "positive",
        "server_session_id": "owned-session",
        "status": "completed",
        "replay_start": 0,
        "replay_stop": 4006,
        "observer_start": 300,
        "observer_stop": 4006,
        "instruction_start": 0,
        "instruction_stop": 0,
    }
    assert raw["counters"]["replay_frames"] == 4006
    assert raw["counters"]["observer_frames"] == 3706

    changed = copy.deepcopy(document)
    changed["result"]["jobs"][0]["result"]["staged_prelude"]["movie"][
        "playback_index"] = 299
    with pytest.raises(RuntimeError, match="not contiguous"):
        batch._raw_result_document(
            changed, "owned-session", {
                "bound": {
                    "clock": "movie_frame", "start": 0, "stop": 4006,
                    "stop_inclusive": False,
                },
                "capture_window": {
                    "clock": "movie_frame", "start": 300, "stop": 4006,
                    "stop_inclusive": False,
                },
            })
