#!/usr/bin/env python3
"""Bank the closed E15 late passive control and rejected precise branch."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

import phase4_common as common
import phase4_duckstation_late_batch as late
import phase4_fmv_cd_event_exit_result as receipt_validation


CONFIG_PATH = (
    common.ROOT / "config/phase4_fmv_levelb_region_b_dma_late_result.yaml"
)
OUTPUT = (
    common.ROOT / "analysis/phase4_fmv_levelb_region_b_dma_late_result.json"
)
CONFIGURATION = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIGURATION["run_root"]).resolve()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def _artifact(spec: dict, label: str) -> tuple[Path, dict]:
    return receipt_validation._artifact(spec, label, run_root=RUN_ROOT)


def _plan(spec: dict) -> dict:
    path = common.ROOT / spec["plan"]["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["plan"]["sha256"],
        f"{spec.get('role', 'precise')} plan identity drifted",
    )
    plan = common.load_yaml(path)
    _require(
        late.validate_plan(plan, allow_executed=True) == [],
        f"{spec.get('role', 'precise')} plan no longer validates",
    )
    return plan


def _memory(capture: dict, label: str) -> dict:
    rows = [
        row for row in capture.get("memory") or [] if row.get("label") == label
    ]
    _require(len(rows) == 1, f"{label} capture is not unique")
    row = rows[0]
    _require(
        row.get("valid_bytes") == row.get("length")
        and len(row.get("hex") or "") == 2 * row["length"],
        f"{label} capture is incomplete",
    )
    return row


def _validate_authorization() -> dict:
    _, ledger = _artifact(CONFIGURATION["before_ledger"], "before ledger")
    rows = [
        row for row in ledger.get("entries") or []
        if row.get("id") == CONFIGURATION["escalation_id"]
    ]
    _require(
        len(rows) == 1
        and rows[0].get("state") == "planned"
        and rows[0].get("target_row") == CONFIGURATION["row_id"]
        and rows[0].get("missing_fact_id")
        == CONFIGURATION["missing_fact_id"],
        "immutable before-ledger did not authorize the escalation",
    )
    hypothesis = rows[0].get("hypothesis", "")
    _require(
        "truncated or discontinuous pages" in hypothesis
        and "promotes no dimension" in hypothesis,
        "immutable before-ledger lost the pagination falsifier",
    )
    _, packet = _artifact(CONFIGURATION["work_packet"], "work packet")
    _require(
        packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("campaign_id") == CONFIGURATION["campaign_id"]
        and packet.get("row_ids") == [CONFIGURATION["row_id"]]
        and packet.get("first_unmet_dimension") == "lifecycle"
        and packet.get("evidence_domain") == "dma"
        and packet.get("escalation_id") == CONFIGURATION["escalation_id"]
        and "incomplete, discontinuous, saturated or truncated"
        in packet.get("falsifier", ""),
        "retained work packet drifted from the authorized claim",
    )
    return {
        "before_ledger_sha256": CONFIGURATION["before_ledger"]["sha256"],
        "work_packet_sha256": CONFIGURATION["work_packet"]["sha256"],
        "first_unmet_dimension": packet["first_unmet_dimension"],
    }


def _validate_reused_offline() -> dict:
    spec = CONFIGURATION["reused_offline_query"]
    root = Path(spec["run_root"]).resolve()
    path = (root / spec["receipt"]["relative_path"]).resolve()
    _require(
        root in path.parents
        and path.is_file()
        and common.sha256(path) == spec["receipt"]["sha256"],
        "reused offline receipt identity drifted",
    )
    receipt = common.load_json(path)
    _require(
        receipt.get("schema") == "abl-phase4-offline-query/1"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("execution", {}).get("exit_code") == 0
        and any(
            row.get("sha256") == spec["external_index_sha256"]
            for row in receipt.get("external_inputs") or []
        ),
        "reused offline receipt is not closed over the retained index",
    )
    return {
        "receipt_sha256": spec["receipt"]["sha256"],
        "external_index_sha256": spec["external_index_sha256"],
        "counted_as_new_query": False,
    }


def _validate_static_source() -> dict:
    spec = CONFIGURATION["static_source"]
    path = common.ROOT / spec["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["sha256"],
        "static replacement-ownership source identity drifted",
    )
    source = common.load_json(path)
    policy = source["completed_level_b_replacement_policy"]
    _require(
        source.get("schema")
        == "abl-phase4-fmv-region-b-replacement-ownership/2"
        and source.get("row") == CONFIGURATION["row_id"]
        and policy["common_resource_policy"]["path"] == r"bits\memory.bin"
        and policy["common_resource_policy"]["destination"] == "0x800B5788"
        and len(policy["conditional_transition_requests"]) == 2
        and source["ownership"]["replacement_byte_owner"]
        == "E16_streaming_overlays"
        and source["claim_boundary"]["dimension_promoted"] is False,
        "static replacement request contract drifted",
    )
    return {
        "sha256": spec["sha256"],
        "resource": policy["common_resource_policy"]["path"],
        "destination": policy["common_resource_policy"]["destination"],
        "conditional_transition_requests": len(
            policy["conditional_transition_requests"]
        ),
        "replacement_byte_owner": source["ownership"][
            "replacement_byte_owner"
        ],
    }


def _validate_passive() -> dict:
    spec = CONFIGURATION["passive"]
    _, receipt = _artifact(spec["receipt"], "passive receipt")
    _, batch = _artifact(spec["batch_result"], "passive batch result")
    _, raw = _artifact(spec["raw_results"], "passive raw results")
    _, cleanup = _artifact(spec["cleanup"], "passive cleanup")
    _, pagination = _artifact(spec["pagination"], "passive pagination")
    _, events = _artifact(spec["command_events"], "passive command events")
    plan = _plan(spec)

    media = CONFIGURATION["media"]
    debugger = CONFIGURATION["debugger"]
    expected = CONFIGURATION["expected_endpoint"]
    _require(
        receipt.get("schema") == "abl-phase4-live-run-receipt/2"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("precise") is False
        and receipt.get("prelude_receipt") is None
        and receipt.get("escalation_id") == CONFIGURATION["escalation_id"]
        and receipt.get("missing_fact_id") == CONFIGURATION["missing_fact_id"],
        "passive receipt closure identity drifted",
    )
    experiment = receipt["experiment"]
    _require(
        experiment["executor_role"] == "investigator"
        and experiment["domain"] == "dma"
        and experiment["anchor"] == {
            "kind": "cold_boot_movie",
            "media_sha256": media["bin_sha256"],
            "movie_sha256": media["movie_sha256"],
            "settings_sha256": media["settings_sha256"],
            "start": {"clock": "emulator_frame", "value": 0},
            "state_sha256": None,
        }
        and experiment["execution"]["bound"] == {
            "clock": "emulator_frame",
            "start": 0,
            "stop": spec["replay_stop"],
            "stop_inclusive": False,
        }
        and experiment["execution"]["capture_window"] == {
            "clock": "emulator_frame",
            "start": spec["capture_start"],
            "stop": spec["replay_stop"],
            "stop_inclusive": False,
        }
        and experiment["adapter_source_sha256"]
        == debugger["adapter_sha256_at_execution"]
        and experiment["duckstation_executable_sha256"]
        == debugger["binary_sha256"]
        and experiment["duckstation_source_sha256"]
        == debugger["source_sha256"]
        and experiment["api_surface_sha256"]
        == debugger["api_surface_sha256"],
        "passive typed experiment identity drifted",
    )
    _require(
        batch.get("schema") == "abl-phase4-duckstation-batch-result/1"
        and batch.get("row_ids") == [CONFIGURATION["row_id"]]
        and batch.get("escalation_ids") == [CONFIGURATION["escalation_id"]]
        and batch["result"]["state"] == "completed"
        and batch["expected_media"]["sha256"] == media["cue_sha256"]
        and batch["expected_media"]["tracks"][0]["sha256"]
        == media["bin_sha256"]
        and batch["mounted_media"]["game_serial"] == media["serial"]
        and batch["expected_debugger"]["binary_sha256"]
        == debugger["binary_sha256"]
        and batch["expected_debugger"]["source_revision"]
        == debugger["source_revision"]
        and batch["expected_debugger"]["dirty_state_hash"]
        == debugger["dirty_state_hash"]
        and batch["plan_sha256"]
        == late.sha256_bytes(late.plan_bytes(late._execution_plan(plan))),
        "passive batch/media/debugger/plan identity drifted",
    )
    jobs = batch["result"]["jobs"]
    _require(
        len(jobs) == 2
        and [row["id"] for row in jobs] == [row["id"] for row in plan["jobs"]]
        and all(
            row["state"] == "completed"
            and row["recipe"] == "bootAndRun"
            and row["result"]["media_verified"] is True
            and row["result"].get("after_load") is None
            and row["result"]["staged_prelude"]["start_frame"]
            == expected["staged_start_frame"]
            and row["result"]["staged_prelude"]["target_frame"]
            == expected["staged_stop_frame"]
            and row["result"]["staged_prelude"]["frames_advanced"]
            == expected["staged_frames_advanced"]
            and row["result"]["staged_prelude"]["status"]["frame"]
            == expected["staged_stop_frame"]
            and row["result"]["run"]["frames_advanced"]
            == expected["observed_frames"]
            for row in jobs
        ),
        "passive staged atomic jobs are incomplete or changed method",
    )
    _require(
        raw.get("schema") == "abl-phase4-live-raw-results/1"
        and raw.get("complete") is True
        and raw.get("errors") == []
        and raw["counters"] == {
            "server_session_id": raw["sessions"][0]["server_session_id"],
            "launches": 1,
            "atomic_jobs": 2,
            "replay_frames": 32238,
            "observer_frames": 800,
            "instructions": 0,
        }
        and [row["job_id"] for row in raw["results"]]
        == [row["id"] for row in jobs]
        and all(
            row["replay_start"] == expected["staged_start_frame"]
            and row["replay_stop"] == expected["frame"]
            and row["observer_start"] == expected["staged_stop_frame"]
            and row["observer_stop"] == expected["frame"]
            and row["instruction_start"] == row["instruction_stop"] == 0
            and row["status"] == "completed"
            for row in raw["results"]
        ),
        "passive raw counters drifted",
    )
    _require(
        cleanup.get("schema") == "abl-phase4-owned-pid-cleanup/1"
        and cleanup.get("complete") is True
        and cleanup.get("errors") == []
        and cleanup.get("owned_pid_stopped") is True
        and str(cleanup.get("config_dir") or "").startswith("/var/tmp/")
        and [row.get("kind") for row in cleanup.get("actions") or []]
        == ["stop_owned_pid", "confirm_pid_stopped"],
        "passive owned-PID cleanup drifted",
    )
    _require(
        pagination.get("schema") == "abl-phase4-live-pagination/1"
        and pagination.get("complete") is True
        and pagination.get("errors") == []
        and pagination.get("pages") == [{"page": 0, "record_count": 0}]
        and pagination.get("pages_complete") is True
        and pagination.get("truncated") is False,
        "passive pagination drifted",
    )
    receipt_validation._validate_command_events(events, batch, raw)
    for key in (
        "raw_results", "owned_pid_cleanup", "pagination", "command_events"
    ):
        config_key = "cleanup" if key == "owned_pid_cleanup" else key
        _require(
            receipt["evidence"][key]["sha256"] == spec[config_key]["sha256"],
            f"passive receipt evidence join drifted for {key}",
        )
    receipt_validation._validate_preservation(
        receipt, spec["role"], run_root=RUN_ROOT
    )
    media_path = receipt_validation._validate_reference(
        receipt["evidence"]["media_capabilities"],
        "passive media/capabilities",
        run_root=RUN_ROOT,
    )
    media_doc = common.load_json(media_path)
    _require(
        media_doc.get("schema") == "abl-phase4-live-media-capabilities/1"
        and media_doc.get("complete") is True
        and media_doc.get("errors") == []
        and media_doc.get("mounted_serial") == media["serial"]
        and media_doc.get("pristine_media_sha256") == media["bin_sha256"]
        and media_doc.get("duckstation_executable_sha256")
        == debugger["binary_sha256"]
        and media_doc.get("duckstation_source_sha256")
        == debugger["source_sha256"]
        and media_doc.get("api_surface_sha256")
        == debugger["api_surface_sha256"],
        "passive normalized media/capability identity drifted",
    )

    first = jobs[0]["result"]
    second = jobs[1]["result"]
    _require(
        first["staged_prelude"] == second["staged_prelude"]
        and first["run"]["status"] == second["run"]["status"]
        and first["capture"] == second["capture"],
        "passive same-anchor endpoints diverged",
    )
    capture = first["capture"]
    _require(
        capture["frame"] == expected["frame"]
        and capture["cycle"] == expected["cycle"]
        and capture["cpu"]["status"]["pc"] == expected["pc"]
        and capture["cpu"]["status"]["sp"] == expected["sp"]
        and capture["movie"]["frame_count"] == expected["movie_frame_count"]
        and capture["movie"]["start_state"]["from_boot"] is True
        and capture["movie"]["truncated"] is False
        and _memory(capture, "scene")["hex"] == expected["scene_hex_le"]
        and _memory(capture, "fmv_running_latch")["hex"]
        == expected["fmv_running_latch_hex_le"]
        and _memory(capture, "music_progress_id")["hex"]
        == expected["music_progress_id_hex_le"]
        and _memory(capture, "selected_frame_limit")["hex"]
        == expected["selected_frame_limit_hex_le"]
        and _memory(capture, "region_b_head")["length"] == 256,
        "passive endpoint contract drifted",
    )
    return {
        "role": spec["role"],
        "precise": False,
        "receipt_sha256": spec["receipt"]["sha256"],
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "raw_results_sha256": spec["raw_results"]["sha256"],
        "cleanup_sha256": spec["cleanup"]["sha256"],
        "pagination_sha256": spec["pagination"]["sha256"],
        "command_events_sha256": spec["command_events"]["sha256"],
        "endpoint": {
            "staged_start_frame": expected["staged_start_frame"],
            "staged_stop_frame": expected["staged_stop_frame"],
            "staged_frames_advanced": expected["staged_frames_advanced"],
            "frame": capture["frame"],
            "cycle": capture["cycle"],
            "pc": capture["cpu"]["status"]["pc"],
            "sp": capture["cpu"]["status"]["sp"],
            "movie_frame_count": capture["movie"]["frame_count"],
            "scene_hex_le": _memory(capture, "scene")["hex"],
            "fmv_running_latch_hex_le": _memory(
                capture, "fmv_running_latch"
            )["hex"],
            "region_b_head_sha256": late.sha256_bytes(
                bytes.fromhex(_memory(capture, "region_b_head")["hex"])
            ),
        },
        "repeat_equal": True,
        "jobs": 2,
        "replay_frames": raw["counters"]["replay_frames"],
        "observer_frames": raw["counters"]["observer_frames"],
        "owned_pid_stopped": True,
    }


def _validate_precise_rejection() -> dict:
    spec = CONFIGURATION["precise_rejection"]
    plan = _plan(spec)
    receipt_path = (RUN_ROOT / spec["receipt_relative_path"]).resolve()
    _require(
        RUN_ROOT in receipt_path.parents
        and spec["receipt_absent"] is True
        and not receipt_path.exists()
        and spec["classification"] == "failed_closed_before_receipt"
        and spec["rejected_condition"]
        == "transfer_pagination_incomplete_or_truncated"
        and spec["evidence_admitted"] is False
        and spec["retry_same_method"] is False,
        "rejected precise attempt gained evidence or lost fail-closed status",
    )
    assertion = plan["v2_receipt"]["assertion_plan"]
    _require(
        assertion["required_channel"] == 3
        and assertion["required_direction"] == "from_device"
        and assertion["required_first_address"] == 0x800B5788
        and assertion["require_contiguous_indexes"] is True
        and assertion["require_truncated"] is False,
        "precise plan lost the predeclared DMA falsifier",
    )
    return {
        "classification": spec["classification"],
        "rejected_condition": spec["rejected_condition"],
        "receipt_relative_path": spec["receipt_relative_path"],
        "receipt_present": False,
        "evidence_admitted": False,
        "retry_same_method": False,
        "plan_sha256": spec["plan"]["sha256"],
    }


def build() -> dict:
    authorization = _validate_authorization()
    offline = _validate_reused_offline()
    static = _validate_static_source()
    passive = _validate_passive()
    rejection = _validate_precise_rejection()
    record_counts = {
        "completed_atomic_jobs": passive["jobs"],
        "emulator_launches": 1,
        "investigator_live_receipts": 1,
        "offline_queries": 0,
        "offline_queries_reused": 1,
        "observer_frames": passive["observer_frames"],
        "owned_pids_stopped": 1,
        "precise_live_receipts": 0,
        "promotion_admissible_live_receipts": 0,
        "promoted_dimensions": 0,
        "replay_frames": passive["replay_frames"],
    }
    return {
        "_comment": (
            "Generated from one closed staged passive investigator receipt. "
            "The late precise branch failed closed before receipt emission; "
            "it contributes no DMA event and promotes no dimension."
        ),
        "schema": "abl-phase4-fmv-levelb-region-b-dma-late-result/1",
        "generated": _stable_generated(),
        "campaign": CONFIGURATION["campaign_id"],
        "row": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "missing_fact_id": CONFIGURATION["missing_fact_id"],
        "inputs": {
            "authorization": authorization,
            "offline_query": offline,
            "static_source": static,
            "config": {
                "path": str(CONFIG_PATH.relative_to(common.ROOT)),
                "sha256": common.sha256(CONFIG_PATH),
            },
        },
        "receipts": [passive],
        "precise_rejection": rejection,
        "observation": {
            "offline": offline,
            "passive": {
                "repeat_equal": passive["repeat_equal"],
                "endpoint": passive["endpoint"],
            },
            "precise": {
                "receipt_present": False,
                "dma_events_admitted": 0,
                "first_region_b_dma_identified": False,
            },
        },
        "falsifier": {
            "claim": (
                "The precise pair must retain complete, nontruncated, "
                "contiguous transfer pages and the same endpoint before any "
                "first post-teardown Region-B DMA event is interpreted."
            ),
            "outcome": "not_evaluated",
            "method_outcome": "rejected",
            "reasons": [
                "precise_receipt_absent",
                "transfer_pagination_rejected_before_receipt",
            ],
            "evidence": {
                "passive_repeat_equal": True,
                "passive_receipt_closed": True,
                "precise_receipt_closed": False,
                "precise_dma_events_admitted": 0,
                "owned_pids_stopped_in_admitted_receipts": 1,
            },
        },
        "record_counts": record_counts,
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "source_dependencies": {
            str(CONFIG_PATH.relative_to(common.ROOT)): common.sha256(
                CONFIG_PATH
            ),
            CONFIGURATION["static_source"]["path"]: common.sha256(
                common.ROOT / CONFIGURATION["static_source"]["path"]
            ),
            "analysis/phase3_duckstation_rpc_manifest.json": common.sha256(
                common.ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
            ),
            "tools/phase4_duckstation_batch.py": common.sha256(
                common.ROOT / "tools/phase4_duckstation_batch.py"
            ),
            "tools/phase4_duckstation_late_batch.py": common.sha256(
                common.ROOT / "tools/phase4_duckstation_late_batch.py"
            ),
            CONFIGURATION["passive"]["plan"]["path"]: common.sha256(
                common.ROOT / CONFIGURATION["passive"]["plan"]["path"]
            ),
            CONFIGURATION["precise_rejection"]["plan"]["path"]: common.sha256(
                common.ROOT
                / CONFIGURATION["precise_rejection"]["plan"]["path"]
            ),
        },
        "raw_external_bytes_committed": False,
        "valid": True,
        "errors": [],
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
            raise SystemExit("phase4 FMV late Region-B DMA result is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: staged passive DMA control closed; precise receipt absent "
        "and unadmitted; no dimension promoted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
