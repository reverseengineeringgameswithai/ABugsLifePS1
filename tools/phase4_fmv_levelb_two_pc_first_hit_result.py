#!/usr/bin/env python3
"""Bank the bounded E15 two-PC first-hit falsifier."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

import phase4_common as common
import phase4_duckstation_two_pc_first_hit as first_hit


CONFIG_PATH = (
    common.ROOT / "config/phase4_fmv_levelb_two_pc_first_hit_result.yaml"
)
OUTPUT = (
    common.ROOT / "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json"
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


def _external(spec: dict, label: str) -> tuple[Path, dict]:
    path = (RUN_ROOT / spec["relative_path"]).resolve()
    _require(RUN_ROOT in path.parents, f"{label} escaped the run root")
    _require(path.is_file(), f"{label} is absent")
    _require(path.stat().st_size == spec["bytes"], f"{label} size drifted")
    _require(common.sha256(path) == spec["sha256"], f"{label} hash drifted")
    return path, common.load_json(path)


def _authorization() -> dict:
    _, ledger = _external(CONFIGURATION["before_ledger"], "before ledger")
    rows = [
        row for row in ledger.get("entries") or []
        if row.get("id") == CONFIGURATION["escalation_id"]
    ]
    _require(
        len(rows) == 1
        and rows[0].get("state") == "planned"
        and rows[0].get("target_row") == CONFIGURATION["row_id"]
        and rows[0].get("missing_fact_id")
        == CONFIGURATION["missing_fact_id"]
        and "no hit through the finite frame-15856 bound"
        in rows[0].get("hypothesis", ""),
        "immutable before-ledger authorization drifted",
    )
    _, packet = _external(CONFIGURATION["work_packet"], "work packet")
    _require(
        packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("campaign_id") == CONFIGURATION["campaign_id"]
        and packet.get("row_ids") == [CONFIGURATION["row_id"]]
        and packet.get("first_unmet_dimension") == "lifecycle"
        and packet.get("evidence_domain")
        == "native_control_and_exact_instruction_interface"
        and packet.get("escalation_id") == CONFIGURATION["escalation_id"]
        and "reaches frame 15856 without a target hit"
        in packet.get("explicit_falsifier", ""),
        "retained work packet drifted",
    )
    return {
        "before_ledger_sha256": CONFIGURATION["before_ledger"]["sha256"],
        "work_packet_sha256": CONFIGURATION["work_packet"]["sha256"],
        "first_unmet_dimension": packet["first_unmet_dimension"],
        "evidence_domain": packet["evidence_domain"],
    }


def _evidence(receipt: dict, label: str) -> None:
    for name, reference in receipt["evidence"].items():
        if reference["scope"] == "repo":
            path = common.ROOT / reference["path"]
        else:
            path = RUN_ROOT / reference["path"]
        _require(
            path.is_file() and common.sha256(path) == reference["sha256"],
            f"{label} {name} evidence drifted",
        )
    cleanup = common.load_json(
        RUN_ROOT / receipt["evidence"]["owned_pid_cleanup"]["path"]
    )
    _require(
        cleanup.get("complete") is True
        and cleanup.get("errors") == []
        and cleanup.get("owned_pid_stopped") is True
        and str(cleanup.get("config_dir") or "").startswith("/var/tmp/")
        and [row.get("kind") for row in cleanup.get("actions") or []]
        == ["stop_owned_pid", "confirm_pid_stopped"],
        f"{label} owned-PID cleanup drifted",
    )


def _base_receipt(role: str, spec: dict) -> tuple[dict, dict]:
    _, receipt = _external(spec, f"{role} receipt")
    _, batch = _external(spec["batch_result"], f"{role} batch result")
    precise = role == "native"
    media = CONFIGURATION["media"]
    expected_window = (
        {
            "clock": "emulator_frame",
            "start": CONFIGURATION["expected"]["native_anchor_frame"],
            "stop": CONFIGURATION["expected"]["native_frame_ceiling"],
            "stop_inclusive": False,
        }
        if precise else
        {
            "clock": "emulator_frame",
            "start": CONFIGURATION["expected"]["passive_capture_start"],
            "stop": CONFIGURATION["expected"]["passive_capture_stop"],
            "stop_inclusive": False,
        }
    )
    _require(
        receipt.get("schema") == "abl-phase4-live-run-receipt/2"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("precise") is precise
        and receipt.get("escalation_id") == CONFIGURATION["escalation_id"]
        and receipt.get("missing_fact_id") == CONFIGURATION["missing_fact_id"],
        f"{role} receipt closure drifted",
    )
    experiment = receipt["experiment"]
    _require(
        experiment["executor_role"] == "investigator"
        and experiment["domain"] == "interface"
        and experiment["anchor"] == {
            "kind": "cold_boot_movie",
            "media_sha256": media["bin_sha256"],
            "movie_sha256": media["movie_sha256"],
            "settings_sha256": media["settings_sha256"],
            "start": {"clock": "emulator_frame", "value": 0},
            "state_sha256": None,
        }
        and experiment["execution"]["capture_window"] == expected_window
        and experiment["duckstation_executable_sha256"]
        == CONFIGURATION["debugger"]["binary_sha256"],
        f"{role} typed experiment identity drifted",
    )
    _evidence(receipt, role)
    return receipt, batch


def _passive() -> dict:
    spec = CONFIGURATION["receipts"]["passive"]
    receipt, batch = _base_receipt("passive", spec)
    expected = CONFIGURATION["expected"]
    media = CONFIGURATION["media"]
    _require(
        receipt.get("prelude_receipt") is None
        and batch.get("schema") == "abl-phase4-duckstation-batch-result/1"
        and batch["result"]["state"] == "completed"
        and batch["expected_media"]["tracks"][0]["sha256"]
        == media["bin_sha256"]
        and batch["mounted_media"]["game_serial"] == media["serial"]
        and batch["expected_debugger"]["binary_sha256"]
        == CONFIGURATION["debugger"]["binary_sha256"],
        "passive batch/media/debugger identity drifted",
    )
    jobs = batch["result"]["jobs"]
    _require(
        len(jobs) == 2
        and all(
            row["state"] == "completed"
            and row["recipe"] == "bootAndRun"
            and row["result"]["media_verified"] is True
            and row["result"]["staged_prelude"]["target_frame"]
            == expected["passive_capture_start"]
            and row["result"]["run"]["status"]["frame"]
            == expected["passive_endpoint_frame"]
            and row["result"]["capture"]["frame"]
            == expected["passive_endpoint_frame"]
            and row["result"]["capture"]["cycle"]
            == expected["passive_endpoint_cycle"]
            and row["result"]["capture"]["cpu"]["status"]["pc"]
            == expected["passive_endpoint_pc"]
            for row in jobs
        ),
        "passive atomic jobs drifted",
    )
    first = jobs[0]["result"]
    repeat = jobs[1]["result"]
    _require(
        first["staged_prelude"] == repeat["staged_prelude"]
        and first["run"]["status"] == repeat["run"]["status"]
        and first["capture"] == repeat["capture"],
        "passive same-anchor endpoints diverged",
    )
    return {
        "role": "passive",
        "precise": False,
        "receipt_sha256": spec["sha256"],
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "capture_window": receipt["experiment"]["execution"]["capture_window"],
        "jobs": 2,
        "repeat_equal": True,
        "endpoint": {
            "frame": first["capture"]["frame"],
            "cycle": first["capture"]["cycle"],
            "pc": first["capture"]["cpu"]["status"]["pc"],
            "sp": first["capture"]["cpu"]["status"]["sp"],
        },
        "owned_pid_stopped": True,
    }


def _native() -> dict:
    spec = CONFIGURATION["receipts"]["native"]
    receipt, batch = _base_receipt("native", spec)
    _, direct = _external(spec["direct_result"], "native direct result")
    expected = CONFIGURATION["expected"]
    prelude = receipt.get("prelude_receipt") or {}
    _require(
        prelude.get("sha256")
        == CONFIGURATION["receipts"]["passive"]["sha256"],
        "native receipt lost its passive-prelude join",
    )
    _require(
        batch.get("schema")
        == "abl-phase4-fmv-levelb-two-pc-first-hit-live-result/1"
        and batch.get("complete") is True
        and batch.get("errors") == []
        and batch["result"]["state"] == "completed"
        and len(batch["result"]["jobs"]) == 1
        and batch["result"]["jobs"][0]["state"] == "completed"
        and batch["result"]["jobs"][0]["result"]["capture"]["frame"]
        == expected["native_anchor_frame"]
        and batch["result"]["jobs"][0]["result"]["capture"]["cycle"]
        == expected["native_anchor_cycle"]
        and batch["result"]["jobs"][0]["result"]["capture"]["cpu"]["status"]["pc"]
        == expected["native_anchor_pc"],
        "native atomic anchor drifted",
    )
    identity = direct["verified_identity"]
    debugger = CONFIGURATION["debugger"]
    media = CONFIGURATION["media"]
    _require(
        direct.get("schema") == first_hit.RESULT_SCHEMA
        and direct.get("complete") is True
        and direct.get("errors") == []
        and direct.get("outcome") == expected["outcome"]
        and direct.get("first_hit") is None
        and direct["falsifier"] == {
            "code": expected["falsifier_code"],
            "reason": expected["falsifier_reason"],
        }
        and direct["execution"] == {
            "clock": "emulator_frame",
            "anchor_frame": expected["native_anchor_frame"],
            "frame_ceiling": expected["native_frame_ceiling"],
            "failure_frame": expected["native_failure_frame"],
        }
        and direct["cleanup"] == {"remaining_breakpoints": 0}
        and identity["media_serial"] == media["serial"]
        and identity["media_sha256"] == media["bin_sha256"]
        and identity["binary_sha256"] == debugger["binary_sha256"]
        and identity["source_revision"] == debugger["source_revision"]
        and identity["source_dirty_state_hash"] == debugger["dirty_state_hash"]
        and identity["dispatcher_sha256"] == debugger["dispatcher_sha256"],
        "native two-PC falsifier payload drifted",
    )
    events = direct["command_events"]["events"]
    cursor = 0

    def retained_rpc(
        server_session_id: str,
        method: str,
        params: dict,
        socket_timeout_ms: int,
    ) -> dict:
        nonlocal cursor
        _require(cursor < len(events), "native command stream ended early")
        event = events[cursor]
        cursor += 1
        _require(
            event["server_session_id"] == server_session_id
            and event["method"] == method
            and event["params"] == params
            and event["socket_timeout_ms"] == socket_timeout_ms
            and event["result_sha256"]
            == first_hit.sha256_bytes(first_hit.canonical_bytes(event["result"])),
            "native command stream differs from the typed adapter request",
        )
        return event["result"]

    plan = common.load_yaml(
        common.ROOT / "config/phase4_fmv_levelb_two_pc_first_hit.yaml"
    )["first_hit_plan"]
    reason = ""
    try:
        first_hit.execute_first_hit(
            retained_rpc,
            plan,
            direct["server_session_id"],
            identity,
            sleep=lambda _seconds: None,
        )
    except first_hit.FirstHitFalsifiedError as exc:
        reason = str(exc)
    _require(
        cursor == len(events)
        and reason == expected["falsifier_reason"]
        and events[-3]["method"] == "debugger.removeBreakpoint"
        and events[-2]["method"] == "debugger.removeBreakpoint"
        and events[-1]["method"] == "debugger.listBreakpoints"
        and events[-1]["result"].get("breakpoints") == [],
        "native adapter replay did not reproduce bounded falsifier and cleanup",
    )
    return {
        "role": "native",
        "precise": True,
        "receipt_sha256": spec["sha256"],
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "direct_result_sha256": spec["direct_result"]["sha256"],
        "capture_window": receipt["experiment"]["execution"]["capture_window"],
        "server_session_id": direct["server_session_id"],
        "anchor_frame": direct["execution"]["anchor_frame"],
        "failure_frame": direct["execution"]["failure_frame"],
        "frame_ceiling": direct["execution"]["frame_ceiling"],
        "command_event_count": len(events),
        "candidate_hits": 0,
        "outcome": direct["outcome"],
        "falsifier_code": direct["falsifier"]["code"],
        "falsifier_reason": direct["falsifier"]["reason"],
        "owned_breakpoints_removed": 2,
        "remaining_breakpoints": 0,
        "owned_pid_stopped": True,
    }


def build() -> dict:
    authorization = _authorization()
    passive = _passive()
    native = _native()
    _require(
        passive["capture_window"]["start"] < native["capture_window"]["start"]
        and passive["capture_window"]["stop"] > native["capture_window"]["stop"],
        "passive prelude is not strictly wider than the precise window",
    )
    return {
        "schema": "abl-phase4-fmv-levelb-two-pc-first-hit-result/1",
        "generated": _stable_generated(),
        "campaign": CONFIGURATION["campaign_id"],
        "row": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "missing_fact_id": CONFIGURATION["missing_fact_id"],
        "summary": (
            "The pristine passive repeat agreed, but the native two-PC "
            "observer escaped the finite 15792..15856 window without either "
            "candidate hit. The predeclared claim is falsified; no branch, "
            "DMA event, or dimension is promoted."
        ),
        "inputs": {
            "authorization": authorization,
            "config": {
                "path": str(CONFIG_PATH.relative_to(common.ROOT)),
                "sha256": common.sha256(CONFIG_PATH),
            },
        },
        "receipts": [passive, native],
        "observation": {
            "passive_repeat_equal": True,
            "passive_window_strictly_wider": True,
            "native_anchor": {
                "frame": native["anchor_frame"],
                "pc": CONFIGURATION["expected"]["native_anchor_pc"],
            },
            "candidate_pc_hits": 0,
            "natural_first_hit_observed": False,
            "dma_events_claimed": 0,
        },
        "falsifier": {
            "claim": (
                "The first completed-Level-B scene-setup call after the "
                "frame-15792 anchor must hit exactly one of 0x8004FD74 and "
                "0x8005029C through frame 15856."
            ),
            "outcome": "falsified",
            "code": native["falsifier_code"],
            "reason": native["falsifier_reason"],
            "native_receipt_sha256": native["receipt_sha256"],
        },
        "record_counts": {
            "completed_atomic_jobs": 3,
            "emulator_launches": 2,
            "investigator_live_receipts": 2,
            "passive_live_receipts": 1,
            "precise_live_receipts": 1,
            "direct_command_events": native["command_event_count"],
            "candidate_pc_hits": 0,
            "owned_breakpoints_removed": 2,
            "owned_pids_stopped": 2,
            "offline_queries": 0,
            "offline_queries_reused": 1,
            "fresh_verifier_receipts": 0,
            "promotion_admissible_live_receipts": 0,
            "promoted_dimensions": 0,
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "source_dependencies": {
            str(CONFIG_PATH.relative_to(common.ROOT)): common.sha256(CONFIG_PATH),
            "analysis/phase4_fmv_levelb_two_pc_first_hit.json": common.sha256(
                common.ROOT / "analysis/phase4_fmv_levelb_two_pc_first_hit.json"
            ),
            "analysis/phase4_fmv_levelb_transition_relocalization.json":
                common.sha256(
                    common.ROOT
                    / "analysis/phase4_fmv_levelb_transition_relocalization.json"
                ),
            "tools/phase4_duckstation_two_pc_first_hit.py": common.sha256(
                common.ROOT / "tools/phase4_duckstation_two_pc_first_hit.py"
            ),
            "tools/phase4_fmv_levelb_two_pc_first_hit_live.py": common.sha256(
                common.ROOT / "tools/phase4_fmv_levelb_two_pc_first_hit_live.py"
            ),
            "tools/phase4_method_metrics.py": common.sha256(
                common.ROOT / "tools/phase4_method_metrics.py"
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
    rendered = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            raise SystemExit("phase4 FMV two-PC first-hit result is stale")
    else:
        print(rendered, end="")
    print("PASS: two-PC first-hit falsifier banked; no dimension promoted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
