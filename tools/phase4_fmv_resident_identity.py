#!/usr/bin/env python3
"""Bank the residency-qualified E15 shared-PC identity and synthetic control."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

import yaml

from build_identity import verify_staged_input
import exe_read


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_fmv_resident_identity.json"
SOURCE = ROOT / "config/phase4_fmv_resident_identity.yaml"
EXE_PATH = ROOT / "REBUILD/files/SCUS_942.88"
EXE_REL = "SCUS_942.88"
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
EXE_END = 0x80082800
ASM_PATH = ROOT / "asm/hand_written/8004fca0_scene_flow_dispatcher.s"
SEMANTIC_SOURCE = ROOT / "src_re/fmv_resident_code_identity.c"
SOURCE_MANIFEST = ROOT / "tools/repro_inputs.sha256"
RPC_MANIFEST = ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
ADAPTER = ROOT / "tools/phase4_duckstation_batch.py"
PASSIVE_PLAN = ROOT / "config/phase4_fmv_c16_staged_selector_passive_batch.yaml"
PRECISE_PLAN = ROOT / "config/phase4_fmv_c16_staged_selector_control_batch.yaml"
LIVE_SOURCE = ROOT / "config/phase4_live_escalations.yaml"
CONTROL_RESULT = ROOT / "analysis/phase4_fmv_c16_selector_control_result.json"
RPC_GENERATOR = ROOT / "tools/phase3_duckstation_rpc_manifest.py"
EXECUTED_DUCKSTATION_IDENTITY = {
    "source_revision": "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5",
    "dispatcher_sha256":
        "3c08833a893dca2b4db57d51fc452568bb2c4d14c2595d4b6a15612af9833151",
    "scenario_doc_sha256":
        "2b984ed2db98d9b14f228851c39a7dd4b2f2eee63badb4a20a98fd55f3f0fb45",
    "release_binary_sha256":
        "a236f79ab4b93518defe88f5f7b8799bdc1339e5f123df34c5ecbfac1dab62d1",
    "source_dirty_state_hash":
        "9beb0a7c2df2a77202685fea702a0c443a2d005e",
}
EXECUTED_ADAPTER_IDENTITY = {
    "path": "tools/phase4_duckstation_batch.py",
    "sha256":
        "f0022c92ebcba87250379261af5fd720fabf4f4c1cfb9607979f0b81946f3d27",
    "positive_negative_pair_required": True,
    "typed_v2_perturbation_required": True,
    "atomic_staged_prelude_supported": True,
    "raw_counter_clock_derived": True,
}

EXPECTED = {
    "image_sha256": "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20",
    "owner": {
        "start": 0x8004FCA0,
        "end": 0x800502C4,
        "sha256": "02fc946a4c8757792f646d23e5cabdac5e0cf4755211b733cc75aa15b2f0592f",
    },
    "callsites": (
        {
            "id": "game_over_lose",
            "window": (0x800500A4, 0x80050104),
            "window_sha256": "4aa82b8843e66504c47cee1f8c22dae99941580632a307a6e2f617abc53922aa",
            "selector": (0x800500D4, 0x2404002E, 46),
            "call": (0x800500D8, 0x0C00F9F0, 0x8003E7C0),
            "delay": (0x800500DC, 0x00002821, 0),
            "return_pc": 0x800500E0,
        },
        {
            "id": "finale_lev15c",
            "window": (0x80050258, 0x8005029C),
            "window_sha256": "f0636a7464d92d8fe63b63887ad1848be90d6f1701014f35a7a530ab9361602d",
            "selector": (0x80050280, 0x24040028, 40),
            "call": (0x80050284, 0x0C00F9F0, 0x8003E7C0),
            "delay": (0x80050288, 0x00002821, 0),
            "return_pc": 0x8005028C,
        },
    ),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _hex(value: int) -> str:
    return f"0x{value:08X}"


def _slice(data: bytes, start: int, end: int) -> bytes:
    first = EXE_HEADER + start - EXE_BASE
    last = EXE_HEADER + end - EXE_BASE
    if first < EXE_HEADER or last > len(data) or first >= last:
        raise SystemExit(f"invalid resident slice {_hex(start)}..{_hex(end)}")
    return data[first:last]


def _word(data: bytes, address: int) -> int:
    return struct.unpack("<I", _slice(data, address, address + 4))[0]


def _instruction(data: bytes, address: int) -> dict[str, Any]:
    word = _word(data, address)
    return {
        "pc": _hex(address),
        "word": f"0x{word:08X}",
        "mnemonic": exe_read.disasm_one(address, word),
    }


def _manifest_pin(path: str) -> str:
    rows = {}
    for line in SOURCE_MANIFEST.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(maxsplit=1)
        rows[rel.strip()] = digest
    if path not in rows:
        raise SystemExit(f"resident identity source is not pinned: {path}")
    return rows[path]


def _validate_source(source: dict[str, Any]) -> None:
    if source.get("schema") != "abl-phase4-fmv-resident-identity-source/1" or \
            source.get("campaign_id") != "fmv_playback" or \
            source.get("row_id") != "E15_fmv":
        raise SystemExit("resident identity source schema/campaign drifted")
    image = source.get("resident_image") or {}
    if image != {
        "path": "REBUILD/files/SCUS_942.88",
        "load_address": EXE_BASE,
        "end_address": EXE_END,
        "sha256": EXPECTED["image_sha256"],
    }:
        raise SystemExit("resident image source contract drifted")
    owner = source.get("owner") or {}
    expected_owner = EXPECTED["owner"]
    if owner.get("start") != expected_owner["start"] or \
            owner.get("end") != expected_owner["end"] or \
            owner.get("sha256") != expected_owner["sha256"] or \
            owner.get("exact_source") != \
            "asm/hand_written/8004fca0_scene_flow_dispatcher.s" or \
            owner.get("exact_source_sha256") != _manifest_pin(
                "asm/hand_written/8004fca0_scene_flow_dispatcher.s"):
        raise SystemExit("resident owner source contract drifted")
    rows = source.get("callsites") or []
    if len(rows) != len(EXPECTED["callsites"]):
        raise SystemExit("resident callsite source count drifted")
    for row, expected in zip(rows, EXPECTED["callsites"]):
        start, end = expected["window"]
        selector_pc, selector_word, selector = expected["selector"]
        call_pc, call_word, target = expected["call"]
        delay_pc, delay_word, mode = expected["delay"]
        if row != {
            "id": expected["id"],
            "identity_window": {
                "start": start, "end": end,
                "sha256": expected["window_sha256"],
            },
            "selector": {
                "pc": selector_pc, "word": selector_word, "value": selector,
            },
            "call": {"pc": call_pc, "word": call_word, "target": target},
            "delay": {"pc": delay_pc, "word": delay_word, "mode": mode},
            "return_pc": expected["return_pc"],
        }:
            raise SystemExit(
                f"resident callsite source contract drifted: {expected['id']}")
    control = source.get("synthetic_control") or {}
    difference = control.get("only_difference") or {}
    if difference != {
        "kind": "code_write",
        "address": 0x800500D4,
        "original_word": 0x2404002E,
        "replacement_word": 0x24040028,
    }:
        raise SystemExit("synthetic selector only-difference contract drifted")
    bound = control.get("execution_bound") or {}
    prelude = control.get("passive_prelude") or {}
    if bound != {
        "clock": "movie_frame", "start": 300, "stop": 4006,
        "stop_inclusive": False,
    } or prelude != {
        "clock": "movie_frame", "start": 299, "stop": 4006,
        "stop_inclusive": False,
    }:
        raise SystemExit("synthetic selector typed window contract drifted")
    method = control.get("method_support") or {}
    expected_method = {
        "status": "staged_prelude_executed_and_banked",
        "scenario_method": "scenario.loadStateAndRun",
        "atomic_method": "scenario.runBatch",
        "ordering":
            "after_state_load_and_movie_prelude_then_instrumentation_and_code_write",
        "staged_prelude": {
            "kind": "movie_advance",
            "exact_keys": ["kind", "target_frame", "max_frames"],
            "require_loaded_movie": True,
            "require_positive_target": True,
            "require_actual_playback_counters": True,
            "boot_recipe_rejected": True,
        },
        "operation": difference,
        "fail_closed": {
            "exact_keys": [
                "kind", "address", "original_word", "replacement_word",
            ],
            "require_aligned_cached_main_ram": True,
            "require_original_word_match": True,
            "require_replacement_readback": True,
            "invalidate_code_cache": True,
            "boot_recipe_rejected": True,
        },
        "duckstation": EXECUTED_DUCKSTATION_IDENTITY,
        "adapter": EXECUTED_ADAPTER_IDENTITY,
        "predeclared_plans": {
            "escalation_id":
                "P4-ITER99-E15-C16-STAGED-SELECTOR-LIFECYCLE-CONTROL",
            "missing_fact_id": "E15/c16-staged-selector40-lifecycle",
            "passive":
                "config/phase4_fmv_c16_staged_selector_passive_batch.yaml",
            "precise":
                "config/phase4_fmv_c16_staged_selector_control_batch.yaml",
            "execution_state": "executed",
        },
        "result_artifact": {
            "path": "analysis/phase4_fmv_c16_selector_control_result.json",
            "sha256": _sha256(CONTROL_RESULT),
            "falsifier_json_path": "falsifier.outcome",
            "falsifier_expected": "survived",
        },
    }
    if {key: method.get(key) for key in expected_method} != expected_method:
        raise SystemExit("synthetic selector method-support contract drifted")
    if not str(method.get("current_iteration_boundary") or "").startswith(
            "The atomic staged-prelude method executed"):
        raise SystemExit("synthetic selector iteration boundary is absent")
    result = json.loads(CONTROL_RESULT.read_text())
    if result.get("schema") != \
            "abl-phase4-fmv-c16-selector-control-result/3" or \
            (result.get("falsifier") or {}).get("outcome") != "survived" or \
            (result.get("record_counts") or {}).get(
                "method_trial_admissible_live_receipts") != 0 or \
            (result.get("record_counts") or {}).get(
                "intrinsically_valid_live_receipts") != 2 or \
            (result.get("method_admission") or {}).get("status") != (
                "rejected_conservative_pre_v2_overlap") or \
            (result.get("claim_boundary") or {}).get(
                "dimension_promoted") is not False:
        raise SystemExit("synthetic selector result artifact drifted")
    escalation_id = expected_method["predeclared_plans"]["escalation_id"]
    missing_fact_id = expected_method["predeclared_plans"]["missing_fact_id"]
    passive_plan = yaml.safe_load(PASSIVE_PLAN.read_text())
    precise_plan = yaml.safe_load(PRECISE_PLAN.read_text())
    for label, plan, receipt_id, target in (
            ("passive", passive_plan,
             "e15-c16-staged-selector-passive-prelude", 299),
            ("precise", precise_plan,
             "e15-c16-staged-selector40-lifecycle", 300)):
        if plan.get("escalation_ids") != [escalation_id] or \
                (plan.get("v2_receipt") or {}).get("id") != receipt_id or \
                (plan.get("v2_receipt") or {}).get(
                    "missing_fact_id") != missing_fact_id or \
                any((job.get("staged_prelude") or {}).get(
                    "target_frame") != target
                    for job in plan.get("jobs") or []):
            raise SystemExit(
                f"synthetic selector {label} predeclared plan drifted")
    live_source = yaml.safe_load(LIVE_SOURCE.read_text())
    live_entry = next((
        row for row in live_source.get("entries") or []
        if row.get("id") == escalation_id), None)
    if not live_entry or live_entry.get("state") != "executed" or \
            live_entry.get("missing_fact_id") != missing_fact_id:
        raise SystemExit("synthetic selector executed escalation drifted")
def build(*, exe_data: bytes | None = None,
          source_doc: dict[str, Any] | None = None,
          verify_identity: bool = True) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    source = yaml.safe_load(SOURCE.read_text()) if source_doc is None else source_doc
    _validate_source(source)
    control_result = json.loads(CONTROL_RESULT.read_text())
    if verify_identity:
        verify_staged_input(EXE_REL, exe)
    if verify_identity and _sha256_bytes(exe) != EXPECTED["image_sha256"]:
        raise SystemExit("resident executable identity drifted")

    owner_start = EXPECTED["owner"]["start"]
    owner_end = EXPECTED["owner"]["end"]
    owner_bytes = _slice(exe, owner_start, owner_end)
    if _sha256_bytes(owner_bytes) != EXPECTED["owner"]["sha256"]:
        raise SystemExit("resident scene-flow owner identity drifted")

    asm_pin = _manifest_pin("asm/hand_written/8004fca0_scene_flow_dispatcher.s")
    if _sha256(ASM_PATH) != asm_pin:
        raise SystemExit("resident scene-flow ASM identity drifted")

    callsites = []
    for expected in EXPECTED["callsites"]:
        start, end = expected["window"]
        window = _slice(exe, start, end)
        if _sha256_bytes(window) != expected["window_sha256"]:
            raise SystemExit(
                f"{expected['id']} resident identity window drifted")
        selector_pc, selector_word, selector = expected["selector"]
        call_pc, call_word, target = expected["call"]
        delay_pc, delay_word, mode = expected["delay"]
        for label, pc, word in (
                ("selector", selector_pc, selector_word),
                ("loader call", call_pc, call_word),
                ("delay slot", delay_pc, delay_word)):
            if _word(exe, pc) != word:
                raise SystemExit(
                    f"{expected['id']} {label} word drifted at {_hex(pc)}")
        actual_target = ((call_pc + 4) & 0xF0000000) | \
            ((call_word & 0x03FFFFFF) << 2)
        if call_word >> 26 != 3 or actual_target != target:
            raise SystemExit(f"{expected['id']} loader target drifted")
        callsites.append({
            "id": expected["id"],
            "owner": "scene_flow_dispatcher",
            "identity_window": {
                "start": _hex(start), "end": _hex(end),
                "size": len(window), "sha256": _sha256_bytes(window),
            },
            "selector": {
                "instruction": _instruction(exe, selector_pc),
                "value": selector,
            },
            "call": {
                "instruction": _instruction(exe, call_pc),
                "target": _hex(target),
            },
            "delay": {
                "instruction": _instruction(exe, delay_pc), "mode": mode,
            },
            "return_pc": _hex(expected["return_pc"]),
            "runtime_admission": [
                "resident_executable_sha256",
                "scene_flow_owner_sha256",
                "identity_window_sha256",
                "selector_word",
                "loader_call_word",
                "delay_slot_word",
            ],
        })

    control = source["synthetic_control"]
    return {
        "schema": "abl-phase4-fmv-resident-identity/1",
        "generated": "2026-07-27",
        "campaign_id": "fmv_playback",
        "row_id": "E15_fmv",
        "lane": "static",
        "inputs": {
            "resident_executable": {
                "path": "REBUILD/files/SCUS_942.88",
                "size": len(exe),
                "sha256": _sha256_bytes(exe),
                "identity_verified": verify_identity,
            },
            "source_contract": {
                "path": "config/phase4_fmv_resident_identity.yaml",
                "sha256": _sha256(SOURCE),
            },
            "exact_owner_source": {
                "path": "asm/hand_written/8004fca0_scene_flow_dispatcher.s",
                "sha256": _sha256(ASM_PATH),
                "manifest": "tools/repro_inputs.sha256",
                "manifest_sha256": _sha256(SOURCE_MANIFEST),
                "pin_verified": True,
            },
        },
        "resident_owner": {
            "id": "scene_flow_dispatcher",
            "start": _hex(owner_start),
            "end": _hex(owner_end),
            "size": len(owner_bytes),
            "sha256": _sha256_bytes(owner_bytes),
            "source_status": "exact_handwritten_asm",
            "semantic_source": {
                "path": "src_re/fmv_resident_code_identity.c",
                "sha256": _sha256(SEMANTIC_SOURCE),
                "status": "documentation_grade_not_build_input",
            },
        },
        "callsites": callsites,
        "synthetic_control": {
            **control,
            "admissibility": {
                "static_specification_complete": True,
                "scenario_method_supported": True,
                "atomic_staged_prelude_supported": True,
                "live_execution_predeclared": True,
                "intrinsic_v2_receipts_valid": True,
                "method_trial_receipts_admissible": False,
                "reason": control["method_support"][
                    "current_iteration_boundary"],
                "next_autonomous_action": (
                    "Statically enumerate the remaining natural-completion, "
                    "pause, repeat, viewer, level and error continuations "
                    "before another live escalation."),
            },
            "runtime_result": {
                "path": "analysis/phase4_fmv_c16_selector_control_result.json",
                "sha256": _sha256(CONTROL_RESULT),
                "classification":
                    control_result["claim_boundary"]["classification"],
                "falsifier": control_result["falsifier"]["outcome"],
                "intrinsically_valid_live_receipts":
                    control_result["record_counts"][
                        "intrinsically_valid_live_receipts"],
                "method_trial_admissible_live_receipts":
                    control_result["record_counts"][
                        "method_trial_admissible_live_receipts"],
                "method_admission_status":
                    control_result["method_admission"]["status"],
                "dimension_promoted":
                    control_result["claim_boundary"]["dimension_promoted"],
            },
        },
        "claims": source["claim_boundary"],
        "summary": {
            "resident_owner_ranges": 1,
            "qualified_shared_pcs": 2,
            "unclassified_shared_pcs": 0,
            "synthetic_only_difference_words": 1,
            "live_runs_authorized": 2,
            "method_trial_live_receipts_admitted": 0,
            "scenario_after_load_method_supported": True,
            "atomic_staged_prelude_supported": True,
            "dimension_promoted": False,
        },
        "source_dependencies": {
            "config/phase4_fmv_resident_identity.yaml": _sha256(SOURCE),
            "src_re/fmv_resident_code_identity.c": _sha256(SEMANTIC_SOURCE),
            "asm/hand_written/8004fca0_scene_flow_dispatcher.s": _sha256(ASM_PATH),
            "src/main/8003e7c0_fmv_bin_load.c": _sha256(
                ROOT / "src/main/8003e7c0_fmv_bin_load.c"),
            "analysis/phase3_duckstation_rpc_manifest.json": _sha256(
                RPC_MANIFEST),
            "tools/phase3_duckstation_rpc_manifest.py": _sha256(RPC_GENERATOR),
            "tools/phase4_duckstation_batch.py": _sha256(ADAPTER),
            "config/phase4_fmv_c16_staged_selector_passive_batch.yaml":
                _sha256(PASSIVE_PLAN),
            "config/phase4_fmv_c16_staged_selector_control_batch.yaml":
                _sha256(PRECISE_PLAN),
            "config/phase4_live_escalations.yaml": _sha256(LIVE_SOURCE),
            "analysis/phase4_fmv_c16_selector_control_result.json":
                _sha256(CONTROL_RESULT),
            "tools/phase4_fmv_resident_identity.py": _sha256(Path(__file__)),
            "tools/repro_inputs.sha256": _sha256(SOURCE_MANIFEST),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = json.dumps(document, indent=2) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
    if args.check or not args.write:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            raise SystemExit("phase4 FMV resident-identity artifact is stale")
    print(
        "PASS: 1 resident owner, 2 shared-PC identities, "
        "1 staged selector interface, 0 method-trial receipts admitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
