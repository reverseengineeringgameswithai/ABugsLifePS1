#!/usr/bin/env python3
"""Bank the repeated bounded E15 exact-PC falsifier."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_fmv_levelb_region_b_dma_exact_pc_result.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json"
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
        and rows[0].get("missing_fact_id") == CONFIGURATION["missing_fact_id"],
        "immutable before-ledger authorization drifted",
    )
    _, packet = _external(CONFIGURATION["work_packet"], "work packet")
    _require(
        packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("campaign_id") == CONFIGURATION["campaign_id"]
        and packet.get("row_ids") == [CONFIGURATION["row_id"]]
        and packet.get("first_unmet_dimension") == "lifecycle"
        and packet.get("evidence_domain") == "dma"
        and packet.get("escalation_id") == CONFIGURATION["escalation_id"]
        and "misses an exact stop" in packet.get("explicit_falsifier", ""),
        "retained work packet drifted",
    )
    return {
        "before_ledger_sha256": CONFIGURATION["before_ledger"]["sha256"],
        "work_packet_sha256": CONFIGURATION["work_packet"]["sha256"],
        "first_unmet_dimension": packet["first_unmet_dimension"],
    }


def _validate_receipt(role: str, spec: dict) -> dict:
    path, receipt = _external(spec, f"{role} receipt")
    _, batch = _external(spec["batch_result"], f"{role} batch result")
    precise = role != "passive"
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
    media = CONFIGURATION["media"]
    _require(
        experiment["executor_role"] == "investigator"
        and experiment["domain"] == "dma"
        and experiment["anchor"]["kind"] == "cold_boot_movie"
        and experiment["anchor"]["media_sha256"] == media["bin_sha256"]
        and experiment["anchor"]["movie_sha256"] == media["movie_sha256"]
        and experiment["anchor"]["settings_sha256"] == media["settings_sha256"]
        and experiment["anchor"]["state_sha256"] is None,
        f"{role} receipt anchor drifted",
    )
    for name, ref in receipt["evidence"].items():
        if ref["scope"] == "repo":
            evidence_path = common.ROOT / ref["path"]
        else:
            evidence_path = RUN_ROOT / ref["path"]
        _require(
            evidence_path.is_file() and common.sha256(evidence_path) == ref["sha256"],
            f"{role} {name} evidence drifted",
        )
    cleanup = common.load_json(
        RUN_ROOT / receipt["evidence"]["owned_pid_cleanup"]["path"]
    )
    _require(
        cleanup.get("complete") is True
        and cleanup.get("owned_pid_stopped") is True
        and [row.get("kind") for row in cleanup.get("actions") or []]
        == ["stop_owned_pid", "confirm_pid_stopped"],
        f"{role} owned-PID cleanup drifted",
    )
    summary = {
        "role": role,
        "receipt_sha256": common.sha256(path),
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "precise": precise,
        "capture_window": experiment["execution"]["capture_window"],
        "owned_pid": cleanup["owned_pid"],
        "owned_pid_stopped": True,
    }
    if not precise:
        _require(
            batch.get("schema") == "abl-phase4-duckstation-batch-result/1"
            and (batch.get("result") or {}).get("state") == "completed",
            "passive batch result drifted",
        )
        _require(receipt.get("prelude_receipt") is None, "passive prelude is recursive")
        return summary

    prelude = receipt.get("prelude_receipt") or {}
    _require(
        prelude.get("sha256") == CONFIGURATION["receipts"]["passive"]["sha256"],
        f"{role} precise receipt lost its passive-prelude join",
    )
    _, exact = _external(spec["exact_result"], f"{role} exact result")
    _require(
        batch.get("schema")
        == "abl-phase4-fmv-levelb-region-b-dma-exact-pc-live-result/1"
        and batch.get("complete") is True
        and batch.get("errors") == [],
        f"{role} batch result drifted",
    )
    expected = CONFIGURATION["expected"]
    _require(
        exact.get("schema") == "abl-phase4-duckstation-exact-pc-result/1"
        and exact.get("complete") is True
        and exact.get("errors") == []
        and exact.get("outcome") == expected["outcome"]
        and exact["falsifier"]["code"] == expected["falsifier_code"]
        and exact["falsifier"]["reason"] == expected["falsifier_reason"]
        and exact["execution"] == {
            "clock": "emulator_frame",
            "anchor_frame": expected["anchor_frame"],
            "frame_ceiling": expected["frame_ceiling"],
            "failure_frame": expected["failure_frame"],
        }
        and exact["transfer"] == {
            "pages": [],
            "total": 0,
            "truncated": False,
            "indexes_contiguous": True,
            "retained_bytes": 2,
        },
        f"{role} exact-PC falsifier payload drifted",
    )
    identity = exact["verified_identity"]
    debugger = CONFIGURATION["debugger"]
    _require(
        identity["media_serial"] == media["serial"]
        and identity["media_sha256"] == media["bin_sha256"]
        and identity["binary_sha256"] == debugger["binary_sha256"]
        and identity["source_revision"] == debugger["source_revision"]
        and identity["source_dirty_state_hash"] == debugger["dirty_state_hash"],
        f"{role} exact-PC identity drifted",
    )
    methods = [row["method"] for row in exact["command_events"]["events"]]
    _require(
        methods[0:2] == ["debugger.status", "debugger.runUntilAddress"]
        and methods[-1] == "debugger.pause"
        and "transferLog.start" not in methods,
        f"{role} falsified command prefix drifted",
    )
    summary.update({
        "exact_result_sha256": spec["exact_result"]["sha256"],
        "outcome": exact["outcome"],
        "falsifier_code": exact["falsifier"]["code"],
        "falsifier_reason": exact["falsifier"]["reason"],
        "anchor_frame": exact["execution"]["anchor_frame"],
        "failure_frame": exact["execution"]["failure_frame"],
        "frame_ceiling": exact["execution"]["frame_ceiling"],
        "transfer_events": exact["transfer"]["total"],
        "command_event_count": len(methods),
        "terminal_method": methods[-1],
        "server_session_id": exact["server_session_id"],
    })
    return summary


def build() -> dict:
    authorization = _authorization()
    rows = [
        _validate_receipt(role, CONFIGURATION["receipts"][role])
        for role in ("passive", "native", "repeat")
    ]
    passive, native, repeat = rows
    _require(
        passive["capture_window"]["start"] < native["capture_window"]["start"]
        and passive["capture_window"]["stop"] > native["capture_window"]["stop"]
        and native["capture_window"] == repeat["capture_window"],
        "passive prelude is not strictly wider than both precise windows",
    )
    _require(
        native["server_session_id"] != repeat["server_session_id"]
        and all(
            native[key] == repeat[key]
            for key in (
                "outcome", "falsifier_code", "falsifier_reason",
                "anchor_frame", "failure_frame", "frame_ceiling",
                "transfer_events", "terminal_method",
            )
        ),
        "independent exact-PC falsifier did not repeat",
    )
    return {
        "schema": "abl-phase4-fmv-levelb-region-b-dma-exact-pc-result/1",
        "generated": _stable_generated(),
        "campaign": CONFIGURATION["campaign_id"],
        "row": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "missing_fact_id": CONFIGURATION["missing_fact_id"],
        "summary": (
            "Two independent pristine-media exact-PC runs escaped the finite "
            "15816..15880 window at frame 15881 before the start stop. The "
            "predeclared claim is falsified; no DMA event or dimension is promoted."
        ),
        "inputs": {
            "authorization": authorization,
            "config": {
                "path": str(CONFIG_PATH.relative_to(common.ROOT)),
                "sha256": common.sha256(CONFIG_PATH),
            },
        },
        "receipts": rows,
        "observation": {
            "passive_window_strictly_wider": True,
            "independent_server_sessions": True,
            "exact_pc_repeat_equal": True,
            "precise_receipts_closed": 2,
            "dma_events_claimed": 0,
        },
        "falsifier": {
            "claim": (
                "Both precise runs must hit 0x80046078 from the paused frame-15816 "
                "anchor inside the finite frame-15880 ceiling."
            ),
            "outcome": "falsified_repeated",
            "reason": CONFIGURATION["expected"]["falsifier_reason"],
            "native_receipt_sha256": native["receipt_sha256"],
            "repeat_receipt_sha256": repeat["receipt_sha256"],
        },
        "record_counts": {
            "offline_queries": 0,
            "offline_queries_reused": 1,
            "investigator_live_receipts": 3,
            "passive_live_receipts": 1,
            "precise_live_receipts": 2,
            "fresh_verifier_receipts": 0,
            "promotion_admissible_live_receipts": 0,
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "source_dependencies": {
            str(CONFIG_PATH.relative_to(common.ROOT)): common.sha256(CONFIG_PATH),
            "tools/phase4_duckstation_exact_pc_batch.py": common.sha256(
                common.ROOT / "tools/phase4_duckstation_exact_pc_batch.py"
            ),
            "tools/phase4_method_metrics.py": common.sha256(
                common.ROOT / "tools/phase4_method_metrics.py"
            ),
            "analysis/phase4_method_legacy_live_index.json": common.sha256(
                common.ROOT / "analysis/phase4_method_legacy_live_index.json"
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
            raise SystemExit("phase4 FMV exact-PC result is stale")
    else:
        print(rendered, end="")
    print("PASS: repeated exact-PC falsifier banked; no DMA or dimension promoted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
