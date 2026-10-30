#!/usr/bin/env python3
"""Reproduce C15 status-mask denial in two independent respawn writers.

The retained frame-domain capsules are validated and queried first.  They bind
the natural status word and exact reset frames, but cannot execute a one-bit
counterfactual.  A fresh isolated DuckStation run therefore branches from each
exact pre-reset boundary, clears only player status mask ``0x0010``, replays the
same recorded frame, and compares the result with an unmodified same-state
control.  No movie, save-state, capsule, or RAM bytes are retained.
"""
from __future__ import annotations

import argparse
import copy
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from typing import Any

try:
    import phase4_checkpoint_respawn as c15
    from live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_respawn_status_policy
    from tools import phase4_checkpoint_respawn as c15
    from tools.live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_respawn_status_policy.json"
CAPSULE_INDEX = ROOT / "analysis/phase4_trace_capsule_set.json"
CAPSULE_VALIDATOR = ROOT / "tools/phase4_trace_capsules.py"
OPERATOR_ROOT = Path(os.environ.get(
    "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads" / "ABL"))).resolve()
EXTERNAL_EVIDENCE_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()
MOVIE_ROOT = OPERATOR_ROOT / "movies" / "Phase4"
CAPSULE_ROOT = EXTERNAL_EVIDENCE_ROOT / "trace-capsules" / "Phase4" / "v2"
CAPSULE_COMPARISON_ROOT = (
    EXTERNAL_EVIDENCE_ROOT / "trace-capsules" / "Phase4" / "v1")
CAPSULE_BINARY = (
    EXTERNAL_EVIDENCE_ROOT / "duckstation-binaries" /
    "duckstation-qt-trace-capsule-v1-20260718")
CAPSULE_RUNTIME = (
    EXTERNAL_EVIDENCE_ROOT / "duckstation-runtimes" /
    "trace-capsule-v1-20260718")
CAPSULE_RUNTIME_MANIFEST = CAPSULE_RUNTIME / "SHA256SUMS"
CAPSULE_READER = (
    EXTERNAL_EVIDENCE_ROOT / "duckstation-tools" /
    "trace_capsule_query-v1-20260718.py")
CAPSULE_READER_SHA256 = (
    "b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde")
SUPPLEMENTAL_CAPSULE_ROOT = (
    EXTERNAL_EVIDENCE_ROOT / "trace-capsules" / "Phase4" /
    "a10-a11-v2-20260719")
SUPPLEMENTAL_COMPARISON_ROOT = (
    EXTERNAL_EVIDENCE_ROOT / "trace-capsules" / "Phase4" /
    "a10-a11-v1-20260719")
SUPPLEMENTAL_MOVIES = (
    OPERATOR_ROOT / "movies" / "Phase_Helpers" / "carry_handstand.movie.json",
    OPERATOR_ROOT / "movies" / "seed_as_enemy.movie.json",
)
BONUS_CAPSULE_ROOT = (
    EXTERNAL_EVIDENCE_ROOT / "trace-capsules" / "Phase4" /
    "bonus-objectives-v2-20260719")
BONUS_COMPARISON_ROOT = (
    EXTERNAL_EVIDENCE_ROOT / "trace-capsules" / "Phase4" /
    "bonus-objectives-v1-20260719")
BONUS_MOVIES = (
    OPERATOR_ROOT / "movies" / "Bonus_Level_01.movie.json",
    OPERATOR_ROOT / "movies" / "Bonus_Level_02.movie.json",
    OPERATOR_ROOT / "movies" / "Bonus_Level_03.movie.json",
)
EXPECTED_CAPSULE_COUNT = 55
CHECKPOINT_ARTIFACT = ROOT / "analysis/phase4_checkpoint_respawn.json"
CHECKPOINT_ARTIFACT_SHA256 = (
    "51f953c286482d3408ff85e89a26bbd2a1f7749b250e81cfc0672ce398c2a53e")
STATUS_ADDRESS = c15.PLAYER + 0x90
STATUS_MASK = 0x0010

CASES = (
    {
        **c15.PIT_BREADTH_CASES[0],
        "capsule": "E10__hazard_pit_LEVEL05",
        "capsule_records": 263,
        "writer_kind": "nearest_row_selector",
        "scenario": (
            "tools/scenarios/duckstation/"
            "pristine_scene10_pit_status_denial.yaml"),
    },
    {
        **c15.PIT_BREADTH_CASES[1],
        "capsule": "E10__hazard_pit_LEVEL07",
        "capsule_records": 343,
        "writer_kind": "fixed_tuple_selector",
        "scenario": (
            "tools/scenarios/duckstation/"
            "pristine_scene4_pit_status_denial.yaml"),
    },
)

EXPECTED_POST = {
    "scene_10_pit": {
        "control_safe_xyz": [-159648, 3628, 1182816],
        "denial_safe_xyz": [-103436, -4903, 1209759],
        "denial_heading": 3141,
    },
    "scene_4_pit": {
        "control_safe_xyz": [727892, 9584, 165941],
        "denial_safe_xyz": [744984, 4861, 139049],
        "denial_heading": 1965,
    },
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _method_present(capabilities: dict[str, Any], method: str) -> bool:
    return any((row.get("name") if isinstance(row, dict) else row) == method
               for row in capabilities.get("methods") or [])


def _typed_capsule_read(data: bytes) -> dict[str, Any]:
    if len(data) != 0xA4:
        raise SystemExit(f"C15 capsule reader returned {len(data)} bytes, not 164")
    status = struct.unpack_from("<H", data, 0x90)[0]
    return {
        "live_xyz": list(struct.unpack_from("<iii", data, 0x00)),
        "safe_anchor_xyz": list(struct.unpack_from("<iii", data, 0x50)),
        "safe_anchor_heading": struct.unpack_from("<h", data, 0x78)[0],
        "player_status_word": status,
        "respawn_selector_status_bit_0x0010": bool(status & STATUS_MASK),
        "true_health": struct.unpack_from("<h", data, 0x94)[0],
        "lives": data[0xA0],
    }


def _reader_call(capsule: Path, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CAPSULE_READER), str(capsule), *args],
        capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise SystemExit(
            f"C15 capsule query failed ({result.returncode}): {result.stderr}")
    return result.stdout.strip()


def build_capsule_first_census(*, verify_external: bool) -> dict[str, Any]:
    index = json.loads(CAPSULE_INDEX.read_text())
    if index.get("complete") is not True or index.get("errors") != [] or \
            index.get("capsule_count") != EXPECTED_CAPSULE_COUNT or \
            index.get("movie_count") != EXPECTED_CAPSULE_COUNT or \
            len(index.get("capsules") or []) != EXPECTED_CAPSULE_COUNT:
        raise SystemExit("C15 capsule preservation index is not complete 55/55")
    reader_pin = (index.get("offline_reader_snapshot") or {}).get("sha256")
    if reader_pin != CAPSULE_READER_SHA256:
        raise SystemExit("C15 capsule reader pin drifted")
    by_movie = {row["movie"]: row for row in index.get("capsules") or []}

    validator = {
        "command": (
            "python3 tools/phase4_trace_capsules.py --movie-root "
            "<operator-root>/movies/Phase4 --capsule-root "
            "<external-evidence-root>/trace-capsules/Phase4/v2 "
            "--comparison-root <external-evidence-root>/trace-capsules/Phase4/v1 "
            "--require-byte-identical-comparison --binary-snapshot "
            "<external-evidence-root>/duckstation-binaries/"
            "duckstation-qt-trace-capsule-v1-20260718 --runtime-root "
            "<external-evidence-root>/duckstation-runtimes/"
            "trace-capsule-v1-20260718 --runtime-manifest "
            "<external-evidence-root>/duckstation-runtimes/"
            "trace-capsule-v1-20260718/SHA256SUMS --offline-reader-snapshot "
            "<external-evidence-root>/duckstation-tools/"
            "trace_capsule_query-v1-20260718.py --supplemental-set a10-a11 "
            "<external-evidence-root>/trace-capsules/Phase4/a10-a11-v2-20260719 "
            "<external-evidence-root>/trace-capsules/Phase4/a10-a11-v1-20260719 "
            "<operator-root>/movies <operator-root>/movies/Phase_Helpers/"
            "carry_handstand.movie.json <operator-root>/movies/seed_as_enemy.movie.json "
            "--supplemental-set bonus-objectives <external-evidence-root>/trace-capsules/"
            "Phase4/bonus-objectives-v2-20260719 <external-evidence-root>/trace-capsules/"
            "Phase4/bonus-objectives-v1-20260719 <operator-root>/movies "
            "<operator-root>/movies/Bonus_Level_01.movie.json <operator-root>/movies/"
            "Bonus_Level_02.movie.json <operator-root>/movies/Bonus_Level_03.movie.json --check"),
        "result": (
            f"PASS {index['capsule_count']}/{index['movie_count']} capsules; "
            f"{index['total_external_bytes']:,} external bytes"),
        "observed_output": (
            f"PASS: {index['capsule_count']}/{index['movie_count']} capsules, "
            f"{index['total_external_bytes']} external bytes"),
    }
    query_inputs = (CAPSULE_ROOT, CAPSULE_READER, *SUPPLEMENTAL_MOVIES)
    for required in query_inputs:
        if not required.exists():
            raise SystemExit(f"C15 capsule query input is absent: {required}")
    if _sha256(CAPSULE_READER) != CAPSULE_READER_SHA256:
        raise SystemExit("C15 exact external capsule reader bytes drifted")
    if verify_external:
        for required in (CAPSULE_ROOT, CAPSULE_COMPARISON_ROOT, CAPSULE_BINARY,
                         CAPSULE_RUNTIME, CAPSULE_RUNTIME_MANIFEST, CAPSULE_READER,
                         SUPPLEMENTAL_CAPSULE_ROOT,
                         SUPPLEMENTAL_COMPARISON_ROOT, *SUPPLEMENTAL_MOVIES,
                         BONUS_CAPSULE_ROOT, BONUS_COMPARISON_ROOT, *BONUS_MOVIES):
            if not required.exists():
                raise SystemExit(f"C15 capsule-first input is absent: {required}")
        checked = subprocess.run(
            [sys.executable, str(CAPSULE_VALIDATOR),
             "--movie-root", str(MOVIE_ROOT),
             "--capsule-root", str(CAPSULE_ROOT),
             "--comparison-root", str(CAPSULE_COMPARISON_ROOT),
             "--require-byte-identical-comparison",
             "--binary-snapshot", str(CAPSULE_BINARY),
             "--runtime-root", str(CAPSULE_RUNTIME),
             "--runtime-manifest", str(CAPSULE_RUNTIME_MANIFEST),
             "--offline-reader-snapshot", str(CAPSULE_READER),
             "--supplemental-set", "a10-a11",
             str(SUPPLEMENTAL_CAPSULE_ROOT),
             str(SUPPLEMENTAL_COMPARISON_ROOT),
             str(OPERATOR_ROOT / "movies"),
             *[str(movie) for movie in SUPPLEMENTAL_MOVIES],
             "--supplemental-set", "bonus-objectives",
             str(BONUS_CAPSULE_ROOT), str(BONUS_COMPARISON_ROOT),
             str(OPERATOR_ROOT / "movies"),
             *[str(movie) for movie in BONUS_MOVIES],
             "--check"],
            capture_output=True, text=True, timeout=900)
        validator_output = (checked.stdout + checked.stderr).strip()
        if checked.returncode or validator["observed_output"] not in validator_output:
            raise SystemExit(
                f"C15 capsule freshness validation failed: "
                f"{checked.stdout}\n{checked.stderr}")

    rows = []
    for case in CASES:
        pin = by_movie.get(case["movie_rel"])
        if not pin or pin.get("control_match") is not True or \
                pin.get("preservation_required") is not True:
            raise SystemExit(f"C15 capsule pin is absent/incomplete: {case['id']}")
        movie_path = OPERATOR_ROOT / case["movie_rel"]
        if not movie_path.is_file() or pin.get("movie_sha256") != _sha256(movie_path):
            raise SystemExit(f"C15 capsule/movie hash join drifted: {case['id']}")
        row = {
            "id": case["id"],
            "movie": case["movie_rel"],
            "movie_sha256": pin["movie_sha256"],
            "capsule_manifest_sha256": pin["capsule_manifest_sha256"],
            "capsule_tree_sha256": pin["capsule_tree_sha256"],
            "control_match": pin["control_match"],
            "records": case["capsule_records"],
            "queries": [],
        }
        capsule = CAPSULE_ROOT / case["capsule"]
        summary = json.loads(_reader_call(capsule, "summary"))
        if summary.get("complete") is not True or \
                summary.get("records") != case["capsule_records"]:
            raise SystemExit(f"C15 capsule summary drifted: {case['id']}")
        for frame in (case["pre_reset_frame"], case["reset_frame"]):
            raw = bytes.fromhex(_reader_call(
                capsule, "read", "--frame", str(frame), "--domain", "ram",
                "--offset", "0xa6500", "--length", "164"))
            row["queries"].append({
                "movie_frame": frame,
                "domain": "ram",
                "offset": "0xA6500",
                "length": 164,
                "typed_result": _typed_capsule_read(raw),
            })
        rows.append(row)
    return {
        "preservation_index": CAPSULE_INDEX.relative_to(ROOT).as_posix(),
        "preservation_index_sha256": _sha256(CAPSULE_INDEX),
        "capsule_count": index["capsule_count"],
        "movie_count": index["movie_count"],
        "total_external_bytes": index["total_external_bytes"],
        "offline_reader_sha256": reader_pin,
        "freshness_validator": validator,
        "relevant_capsules": rows,
        "escalation_reason": (
            "Frame-boundary RAM reconstruction fixes the natural status word "
            "at 0x0014 and the exact reset frames, but a retained capsule cannot "
            "execute the one-bit 0x0010 counterfactual or prove which writer PCs "
            "are skipped. An isolated live same-state branch is required."),
    }


def build_fixture_census() -> list[dict[str, Any]]:
    prior = c15.build_fixture_census()
    by_id = {row["id"]: row for row in prior["pit_breadth"]}
    return [copy.deepcopy(by_id[case["id"]]) for case in CASES]


def build_static_census() -> dict[str, Any]:
    prior = c15.build_static_census()
    writers = prior["pit_transition_writers"]
    return {
        "resident_handler": copy.deepcopy(
            prior["regions"]["respawn_transition_state_handler"]),
        "resident_handler_instructions": {
            name: copy.deepcopy(row)
            for name, row in prior["instructions"].items()
            if name.startswith("respawn_")
        },
        "writers": {
            case["id"]: copy.deepcopy(writers[case["id"]]) for case in CASES
        },
    }


def _ranges(case: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    start, end = c15.PIT_WRITER_STATIC[case["id"]]["runtime_range"]
    return (
        {"start": f"0x{start:08X}", "end": f"0x{end:08X}",
         "label": "transition_writer", "max_pcs": 4096},
        {"start": "0x8005B12C", "end": "0x8005B440",
         "label": "respawn_transition_state_handler", "max_pcs": 4096},
    )


def _run_case(client: Any, case: dict[str, Any], temp_dir: Path,
              static: dict[str, Any]) -> dict[str, Any]:
    movie_path = ROOT / case["movie_rel"]
    source = json.loads(movie_path.read_text())
    ranges = _ranges(case)
    pre = c15._trace_snapshot(
        client, movie_path, case["pre_reset_frame"], ranges=ranges)
    natural = c15._trace_snapshot(
        client, movie_path, case["reset_frame"], ranges=ranges)
    origin = c15._trace_snapshot(
        client, movie_path, case["pre_reset_frame"], ranges=ranges)
    if not c15._trace_signatures_equal(pre, origin):
        raise SystemExit(f"C15 {case['id']} pre-reset origin did not reproduce")
    if origin["snapshot"]["player_status_word"] != 0x0014:
        raise SystemExit(f"C15 {case['id']} natural status word is not 0x0014")

    writer_spec = c15.PIT_WRITER_STATIC[case["id"]]
    start, end = writer_spec["runtime_range"]
    runtime_writer = c15._read_memory(client, start, end - start)
    expected_writer = static["writers"][case["id"]]
    if _sha256_bytes(runtime_writer) != expected_writer["sha256"]:
        raise SystemExit(f"C15 {case['id']} runtime writer is not pristine")

    base_state = temp_dir / f"{case['id']}-status-base.sav"
    base_info = c15._save_state(client, base_state)
    base_ram = c15._read_main_ram(client)
    branches: dict[str, dict[str, Any]] = {}
    start_rams: dict[str, bytes] = {}
    for name, clear_mask in (("natural_status_control", False),
                             ("status_bit_0x0010_cleared", True)):
        c15._load_state(client, base_state)
        before = struct.unpack(
            "<H", c15._read_memory(client, STATUS_ADDRESS, 2))[0]
        if before != 0x0014:
            raise SystemExit(f"C15 {case['id']} branch lost status 0x0014")
        if clear_mask:
            c15._write_u16(client, STATUS_ADDRESS, before & ~STATUS_MASK)
        after = struct.unpack(
            "<H", c15._read_memory(client, STATUS_ADDRESS, 2))[0]
        start_ram = c15._read_main_ram(client)
        start_rams[name] = start_ram
        start_snapshot = c15._snapshot(client)
        state = temp_dir / f"{case['id']}-{name}.sav"
        state_info = c15._save_state(client, state)
        suffix = temp_dir / f"{case['id']}-{name}.movie.json"
        recipe = c15._write_suffix(
            source, state, state_info, suffix, f"{case['id']}:{name}",
            start_snapshot, source_frame=case["pre_reset_frame"])
        replay = c15._trace_snapshot(
            client, suffix, case["reset_frame"] - case["pre_reset_frame"],
            ranges=ranges)
        branches[name] = {
            "mutation": {
                "address": "0x800A6590", "width": "u16",
                "before": before, "after": after,
                "cleared_mask": STATUS_MASK if clear_mask else 0,
            },
            "start_snapshot": start_snapshot,
            "start_main_ram_sha256": _sha256_bytes(start_ram),
            "suffix_recipe": recipe,
            "post_reset": replay,
        }

    changed = c15._diff_addresses(
        start_rams["natural_status_control"],
        start_rams["status_bit_0x0010_cleared"])
    control = branches["natural_status_control"]["post_reset"]
    denial = branches["status_bit_0x0010_cleared"]["post_reset"]
    control_coverage = c15._coverage_by_label(control)
    denial_coverage = c15._coverage_by_label(denial)
    handler_equal = all(
        control_coverage["respawn_transition_state_handler"].get(key) ==
        denial_coverage["respawn_transition_state_handler"].get(key)
        for key in ("total_hits", "distinct_pc_count", "pcs_sha256", "pcs"))

    return {
        "id": case["id"],
        "writer_kind": case["writer_kind"],
        "fixture": {"movie": case["movie_rel"], "save": case["save_rel"]},
        "boundary": {
            "pre_reset_frame": case["pre_reset_frame"],
            "reset_frame": case["reset_frame"], "scene": case["scene"],
        },
        "natural_boundary": {"pre_reset": pre, "reset": natural},
        "runtime_writer": {
            "address_range": [f"0x{start:08X}", f"0x{end:08X}"],
            "size": len(runtime_writer),
            "sha256": _sha256_bytes(runtime_writer),
            "pristine_static_identity": expected_writer,
        },
        "base_state": base_info,
        "base_main_ram_sha256": _sha256_bytes(base_ram),
        "branches": branches,
        "single_variable_guard": {
            "changed_byte_addresses": changed,
            "changed_word": "0x800A6590",
            "allowed_word_range": ["0x800A6590", "0x800A6591"],
        },
        "coverage_relation": {
            "resident_handler_exactly_equal": handler_equal,
            "comparison_fields": [
                "total_hits", "distinct_pc_count", "pcs_sha256", "pcs"],
        },
        "causal_result": (
            "Clearing only status mask 0x0010 skips this transition writer's "
            "safe-tuple stores while the same resident handler consumes the "
            "previously retained safe tuple. The control executes the writer "
            "and replaces that tuple."),
        "transient_storage": (
            "base/branch states and one-frame movie derivatives were deleted "
            "before retention"),
    }


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if document.get("schema") != "abl-phase4-respawn-status-policy/1" or \
            document.get("campaign_state") != "active_partial":
        gaps.append("C15 status-policy artifact schema/state changed")
    capsule = document.get("capsule_first_lane") or {}
    if capsule.get("capsule_count") != EXPECTED_CAPSULE_COUNT or \
            capsule.get("movie_count") != EXPECTED_CAPSULE_COUNT or \
            capsule.get("offline_reader_sha256") != CAPSULE_READER_SHA256:
        gaps.append("capsule-first freshness/preservation identity changed")
    if "cannot execute" not in capsule.get("escalation_reason", ""):
        gaps.append("live escalation reason is not explicit")
    if document.get("fixture_census") != build_fixture_census():
        gaps.append("fixture census changed")
    if document.get("static_census") != build_static_census():
        gaps.append("static writer/handler census changed")

    rows = document.get("live_cases") or []
    if [row.get("id") for row in rows] != [case["id"] for case in CASES]:
        gaps.append("live status-policy case set changed")
    by_id = {row.get("id"): row for row in rows}
    required_handler_pcs = {
        "0x8005b1dc", "0x8005b1e4", "0x8005b1ec",
        "0x8005b29c", "0x8005b2a4", "0x8005b2ac",
        "0x8005b30c", "0x8005b348",
    }
    for case in CASES:
        case_id = case["id"]
        row = by_id.get(case_id) or {}
        expected = EXPECTED_POST[case_id]
        branches = row.get("branches") or {}
        control = (branches.get("natural_status_control") or {}).get(
            "post_reset") or {}
        denial = (branches.get("status_bit_0x0010_cleared") or {}).get(
            "post_reset") or {}
        control_snapshot = control.get("snapshot") or {}
        denial_snapshot = denial.get("snapshot") or {}
        pre_snapshot = (((row.get("natural_boundary") or {}).get("pre_reset")
                         or {}).get("snapshot") or {})
        if pre_snapshot.get("player_status_word") != 0x0014:
            gaps.append(f"{case_id} natural status word changed")
        if row.get("single_variable_guard", {}).get(
                "changed_byte_addresses") != ["0x800A6590"]:
            gaps.append(f"{case_id} mutation is not a one-byte status diff")
        denial_mutation = (branches.get("status_bit_0x0010_cleared") or {}).get(
            "mutation") or {}
        if (denial_mutation.get("before"), denial_mutation.get("after"),
                denial_mutation.get("cleared_mask")) != (0x0014, 0x0004, 0x0010):
            gaps.append(f"{case_id} exact status mutation changed")
        if control_snapshot.get("safe_anchor_xyz") != \
                expected["control_safe_xyz"] or \
                control_snapshot.get("live_xyz") != expected["control_safe_xyz"]:
            gaps.append(f"{case_id} natural writer control outcome changed")
        if denial_snapshot.get("safe_anchor_xyz") != \
                expected["denial_safe_xyz"] or \
                denial_snapshot.get("live_xyz") != expected["denial_safe_xyz"] or \
                denial_snapshot.get("safe_anchor_heading") != \
                expected["denial_heading"]:
            gaps.append(f"{case_id} denied writer did not retain prior tuple")
        if (denial_snapshot.get("scene"), denial_snapshot.get("true_health"),
                denial_snapshot.get("lives")) != \
                (case["scene"], case["post_health"], case["post_lives"]):
            gaps.append(f"{case_id} denied path lost resident reset outcome")

        control_cov = c15._coverage_by_label(control)
        denial_cov = c15._coverage_by_label(denial)
        writer_instructions = c15.PIT_WRITER_STATIC[case_id]["instructions"]
        gate_pcs = {
            f"0x{writer_instructions[name][0]:08x}"
            for name in ("status_load", "status_gate")
        }
        store_pcs = {
            f"0x{address:08x}" for name, (address, _) in writer_instructions.items()
            if "store" in name and "status" not in name
        }
        control_writer_pcs = set(
            (control_cov.get("transition_writer") or {}).get("pcs") or [])
        denial_writer_pcs = set(
            (denial_cov.get("transition_writer") or {}).get("pcs") or [])
        if not gate_pcs.issubset(control_writer_pcs & denial_writer_pcs):
            gaps.append(f"{case_id} exact status gate coverage changed")
        if not store_pcs.issubset(control_writer_pcs):
            gaps.append(f"{case_id} control lost transition-writer stores")
        if store_pcs.intersection(denial_writer_pcs):
            gaps.append(f"{case_id} denial executed transition-writer stores")
        for name, coverage in (("control", control_cov), ("denial", denial_cov)):
            handler_pcs = set((coverage.get(
                "respawn_transition_state_handler") or {}).get("pcs") or [])
            if not required_handler_pcs.issubset(handler_pcs):
                gaps.append(f"{case_id} {name} lost exact resident handler chain")
        if row.get("coverage_relation", {}).get(
                "resident_handler_exactly_equal") is not True:
            gaps.append(f"{case_id} resident handler coverage diverged")
        for branch in (control, denial):
            trace = branch.get("cycle_neutral_trace") or {}
            if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                    any(item.get("truncated") for item in trace.get("coverage") or []):
                gaps.append(f"{case_id} passive trace lost cycle neutrality")

    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned status-policy DuckStation process was not stopped")
    if (document.get("run_provenance") or {}).get("anchor") and \
            retained_pristine_save_gaps(document, require_selection=False):
        gaps.append("retained status-policy save/media provenance failed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    if _sha256(CHECKPOINT_ARTIFACT) != CHECKPOINT_ARTIFACT_SHA256:
        raise SystemExit("C15 parent checkpoint artifact hash drifted")
    capsule_first = build_capsule_first_census(verify_external=True)
    fixtures = build_fixture_census()
    static = build_static_census()

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.writeU16", "emulator.getMediaInfo",
        "emulator.getStateInfo", "emulator.loadState", "emulator.saveState",
        "movie.load", "movie.startPlayback", "movie.traceToFrame",
        "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks C15 status methods: {missing}")
    client.call("debugger.pause", {})
    inspections = [
        inspect_state_before_load(client, ROOT / case["save_rel"], media_identity)
        for case in CASES
    ]

    with tempfile.TemporaryDirectory(
            prefix="abl-phase4-c15-status-") as temp_text:
        temp_dir = Path(temp_text)
        live_cases = [
            _run_case(client, case, temp_dir, static) for case in CASES
        ]
        final_media = verified_media_identity(
            client, client.call("debugger.status", {}))
        provenance = finish_run(
            args, generator="tools/phase4_respawn_status_policy.py",
            anchor={
                "type": (
                    "existing state-anchored LEVEL05/LEVEL07 pit discovery leads"),
                "saves": [case["save_rel"] for case in CASES],
                "state_inspections": inspections,
                "fixture_sha256": {
                    row["save"]["path"]: row["save"]["sha256"]
                    for row in fixtures
                },
                "media_identity": media_identity,
                "final_media_identity": final_media,
            },
            timing={
                "cpu_overclock_percent": 100, "cd_read_speedup": 1,
                "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
                "capsule_first": (
                    "freshness-validated exact pinned reader; frame-domain "
                    "status/tuple reconstruction before live escalation"),
                "behavioral_sampling": (
                    "same pre-reset transient state; status control versus only "
                    "mask 0x0010 cleared; exact next recorded frame; passive "
                    "cached-block coverage independently compared with each "
                    "uninstrumented replay"),
            })

    document = {
        "_comment": (
            "Focused C15 breadth evidence. It proves mask necessity for two "
            "more exact writers but not the mask source or general policy."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-respawn-status-policy/1",
        "campaign_state": "active_partial",
        "capsule_first_lane": capsule_first,
        "fixture_census": fixtures,
        "static_census": static,
        "live_cases": live_cases,
        "bounded_interpretation": {
            "observation": (
                "All three natural pit capsules expose status word 0x0014 at "
                "their exact reset boundary; the two new live controls execute "
                "their independently pinned transition writers."),
            "causal_confirmation": (
                "In scene 10 and scene 4, clearing only status bit 0x0010 "
                "prevents the exact transition writer stores while identical "
                "resident-handler coverage copies the prior safe tuple, restores "
                "health, and consumes the same life as the natural control."),
            "inference": (
                "Mask 0x0010 is a necessary precondition shared by the known "
                "LEVEL03 nearest-row, LEVEL10 nearest-row, and LEVEL04 fixed-tuple "
                "writers at these reproduced pit boundaries."),
            "still_unknown": (
                "Who sets/clears mask 0x0010, its whole-word and general policy, "
                "indirect/additional writers, other death classes and stages, "
                "and save/load or scene-transition persistence remain open."),
        },
        "declarative_scenarios": [
            {"path": case["scenario"],
             "sha256": _sha256(ROOT / case["scenario"]), "assertions": 22}
            for case in CASES
        ],
        "source_dependencies": {
            "analysis/phase4_checkpoint_respawn.json": CHECKPOINT_ARTIFACT_SHA256,
            "analysis/phase4_trace_capsule_set.json": _sha256(CAPSULE_INDEX),
            "tools/phase4_checkpoint_respawn.py": _sha256(
                ROOT / "tools/phase4_checkpoint_respawn.py"),
            "tools/phase4_trace_capsules.py": _sha256(CAPSULE_VALIDATOR),
            "analysis/phase0_2_external_fixture_set.json": _sha256(
                ROOT / "analysis/phase0_2_external_fixture_set.json"),
            "REBUILD/files/LEVEL10/LEVEL.BIN": _sha256(
                ROOT / "REBUILD/files/LEVEL10/LEVEL.BIN"),
            "REBUILD/files/LEVEL04/LEVEL.BIN": _sha256(
                ROOT / "REBUILD/files/LEVEL04/LEVEL.BIN"),
        },
        "run_provenance": provenance,
    }
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained C15 status-policy evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print("[respawn-status-policy] active partial; LEVEL10/LEVEL04 denial reproduced")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        if (Path(args.config_dir) / "instance.pid").is_file():
            try:
                finish_run(
                    args, generator="tools/phase4_respawn_status_policy.py",
                    anchor={"type": "aborted before retained C15 status evidence"},
                    timing={})
            except BaseException as cleanup_error:
                print(
                    f"owned C15 status cleanup also failed: {cleanup_error}",
                    file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
