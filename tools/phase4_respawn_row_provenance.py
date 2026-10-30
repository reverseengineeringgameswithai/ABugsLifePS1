#!/usr/bin/env python3
"""Regenerate the Phase-4 C15 authored respawn-row provenance join."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

import yaml

try:
    from build_identity import load_baselines, verify_staged_input
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_respawn_row_provenance
    from tools.build_identity import load_baselines, verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_respawn_row_provenance.json"
C15_ARTIFACT = ROOT / "analysis/phase4_checkpoint_respawn.json"
C15_ARTIFACT_SHA256 = \
    "fc71182a5ffeb1acc15a305d4c707ac2f2846ebc173497d48a4bbc3fd1fc0660"
EXPECTED_MOVIE_SHA256 = \
    "09daafa2f94a2252e805dea1096e82458bca6864863092b2269ffe57b6dcc502"
MOVIE_FIXTURE_REL = "movies/go_to_end/LEVEL02.movie.json"
SCENARIO = ROOT / (
    "tools/scenarios/duckstation/pristine_c15_authored_row_provenance.yaml")
PROGRESSION_STATE = ROOT / "level01_end_of_stage.sav"
EXPECTED_PROGRESSION_STATE_SHA256 = \
    "42047329754c56f6daaf413e192ba8e88ca40889714bbc9f57216f3462ed739f"
BLANK_CARD_SHA256 = \
    "3eb75d0be15aa48327f9ed0b8bba8cc3e38f1d5921163cfde5f1eb1a58cf8636"
PROGRESSION_CARD_SHA256 = \
    "5ca4ee4e23d76fe4eb596d0fe7766c481dcac456557756734f28c903fa242d4c"
PROGRESSION_MARKER = b"BASCUS-94288LEV02:00"
PROGRESSION_RECEIPT = "phase4_respawn_progression.json"
MOVIE_EDIT_START = 6307
MOVIE_EDIT_END = 6316
EXPECTED_EDITED_MOVIE_SEMANTIC_SHA256 = \
    "8ad070c7d00135e6f48956819a8b73669203691145139edb1db5f4c635389e47"

SCENE_WORD = 0x80082504
DAT_BASE_POINTER = 0x80082498
DAT_TYPE_TABLE = 0x80096DA0
DAT_TYPE_01_SLOT = DAT_TYPE_TABLE + 4
PARSER_START = 0x8001CDC0
PARSER_END = 0x8001D3CC
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
PRE_FRAME = 6300
TARGET_FRAME = 7600
EXPECTED_SCENE = 3
EXPECTED_DAT = "LEVEL03/LEVEL.DAT"
EXPECTED_TYPE_01_OFFSET = 0x458
EXPECTED_TYPE_01_COUNT = 18
EXPECTED_TYPE_01_RECORD_SHA256 = \
    "6adbdd60b3935d76caf6b929cb108fd4b338d39c1888a2ad4abe92d21416fee3"
EXPECTED_TYPE_01_PLUS_HEADER_SHA256 = \
    "fec6e92f69fc84357c1e56e03d2ff1e78423703faf532779b3660bbbda26382d"
EXPECTED_DAT_BASE = 0x8015E22C
EXPECTED_TYPE_01_POINTER = EXPECTED_DAT_BASE + EXPECTED_TYPE_01_OFFSET
SELECTED_ROW = 6
EXPECTED_SELECTED_ROW_OFFSET = EXPECTED_TYPE_01_OFFSET + 4 + SELECTED_ROW * 12
EXPECTED_SELECTED_ROW_ADDRESS = EXPECTED_DAT_BASE + EXPECTED_SELECTED_ROW_OFFSET
EXPECTED_SELECTED_ROW_XYZ = [15678, 0, 15438]
EXPECTED_SELECTED_ROW_SHA256 = \
    "88bb66f2ac5168493c220dcdf576a7adff6664b315802d8ed70c93c3c4ac0f49"

PARSER_WORDS = {
    "type_table_base_high": (0x8001CE80, 0x3C048009),
    "type_table_base_low": (0x8001CE84, 0x24846DA0),
    "nonnegative_type_scale": (0x8001CED4, 0x00021080),
    "nonnegative_type_slot_add": (0x8001CED8, 0x00441021),
    "nonnegative_type_pointer_store": (0x8001CEDC, 0xAC520000),
    "normal_record_count_load": (0x8001CEFC, 0x86430000),
    "normal_record_stride_12": (0x8001CF0C, 0x00021080),
    "record_header_add": (0x8001CF10, 0x24420004),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    data = bytes.fromhex(row["hex"])
    if len(data) != length:
        raise SystemExit(f"short debugger read at 0x{address:08X}")
    return data


def _read_u32(client: Any, address: int) -> int:
    return struct.unpack("<I", _read_memory(client, address, 4))[0]


def _method_present(capabilities: dict[str, Any], method: str) -> bool:
    return any((row.get("name") if isinstance(row, dict) else row) == method
               for row in capabilities.get("methods") or [])


def _hex(value: int) -> str:
    return f"0x{value:08X}"


def _declarative_scenario() -> dict[str, Any]:
    document = yaml.safe_load(SCENARIO.read_text())
    progression = document.get("progression") or {}
    playback = document.get("playback") or {}
    branch = playback.get("branch") or {}
    edit = branch.get("edit") or {}
    expected_card = progression.get("expected_card") or {}
    actions = progression.get("actions") or []
    expected_actions = [
        {"kind": "hold", "button": "up", "frames": 1500},
        {"kind": "press", "button": "cross", "frames": 10},
        {"kind": "wait", "frames": 400},
        {"kind": "press", "button": "square", "frames": 10},
        {"kind": "wait", "frames": 1200},
        {"kind": "press", "button": "square", "frames": 10},
        {"kind": "wait", "frames": 1000},
        {"kind": "press", "button": "square", "frames": 10},
        {"kind": "wait", "frames": 1000},
    ]
    checks = {
        "schema": document.get("schema") ==
        "abl-duckstation-two-process-scenario/1",
        "runner": document.get("runner") ==
        "tools/phase4_respawn_row_provenance.py",
        "state": progression.get("state") == "level01_end_of_stage.sav",
        "state_sha256": progression.get("state_sha256") ==
        EXPECTED_PROGRESSION_STATE_SHA256,
        "actions": actions == expected_actions,
        "card": expected_card.get("sha256") == PROGRESSION_CARD_SHA256 and
        expected_card.get("marker") == PROGRESSION_MARKER.decode() and
        expected_card.get("marker_count") == 1 and
        expected_card.get("retained_bytes") is False,
        "movie": playback.get("movie") == MOVIE_FIXTURE_REL and
        playback.get("movie_sha256") == EXPECTED_MOVIE_SHA256 and
        playback.get("from_boot") is True,
        "control": playback.get("control") == {
            "target_frame": TARGET_FRAME, "expected_scene": 1},
        "edit": edit == {
            "button": "left", "value": False,
            "start_frame": MOVIE_EDIT_START,
            "end_frame_exclusive": MOVIE_EDIT_END,
            "edited_frame_count": MOVIE_EDIT_END - MOVIE_EDIT_START,
        },
        "branch": branch.get("semantic_sha256") ==
        EXPECTED_EDITED_MOVIE_SEMANTIC_SHA256 and
        branch.get("derivative_saved") is False and
        branch.get("pre_edit_frame") == PRE_FRAME and
        branch.get("target_frame") == TARGET_FRAME and
        branch.get("require_pre_edit_boundary_equal_to_control") is True,
        "assertions": len(document.get("assertions") or []) == 11,
    }
    failed = sorted(label for label, passed in checks.items() if not passed)
    if failed:
        raise SystemExit(f"C15 declarative scenario changed: {failed}")
    return {
        "path": str(SCENARIO.relative_to(ROOT)),
        "sha256": _sha256(SCENARIO),
        "schema": document["schema"],
        "id": document["id"],
        "assertion_count": len(document["assertions"]),
    }


def _record_size(count: int, record_type: int) -> int:
    if record_type < 0:
        value = 3 * count + 1
        value = (value + (1 if value < 0 else 0)) >> 1
        return (value << 2) + 0x10
    if record_type == 0x3F:
        return 4 + count * 0x10
    return 4 + count * 0x0C


def parse_top_level_records(data: bytes) -> list[dict[str, Any]]:
    if len(data) < 4:
        raise SystemExit("DAT is too small for its top-level count")
    record_count = struct.unpack_from("<i", data, 0)[0]
    if not 0 <= record_count <= 1024:
        raise SystemExit(f"implausible DAT top-level count: {record_count}")
    offset = 4
    records = []
    for index in range(record_count):
        if offset + 4 > len(data):
            raise SystemExit(f"DAT record {index} header exceeds file")
        count, record_type = struct.unpack_from("<hh", data, offset)
        size = _record_size(count, record_type)
        if size < 4 or offset + size > len(data):
            raise SystemExit(
                f"DAT record {index} has invalid size {size} at 0x{offset:X}")
        records.append({
            "index": index, "type": record_type, "count": count,
            "offset": offset, "size": size,
        })
        offset += size
    return records


def build_static_census() -> dict[str, Any]:
    baselines = load_baselines()
    staged_root = ROOT / "REBUILD/files"
    rows = []
    for path in sorted(staged_root.glob("LEVEL*/*.DAT")):
        rel = path.relative_to(staged_root).as_posix()
        data = path.read_bytes()
        verify_staged_input(rel, data, baselines)
        type_rows = []
        for record in parse_top_level_records(data):
            if record["type"] != 1:
                continue
            offset, size = record["offset"], record["size"]
            raw = data[offset:offset + size]
            plus = data[offset:min(len(data), offset + size + 4)]
            type_rows.append({
                **record,
                "offset": f"0x{offset:X}",
                "record_sha256": _sha256_bytes(raw),
                "plus_next_header_size": len(plus),
                "plus_next_header_sha256": _sha256_bytes(plus),
            })
        rows.append({
            "path": f"REBUILD/files/{rel}",
            "staged_rel": rel,
            "size": len(data),
            "sha256": _sha256_bytes(data),
            "type_01_records": type_rows,
        })

    matches = [
        {"path": row["path"], **record}
        for row in rows for record in row["type_01_records"]
        if record["plus_next_header_sha256"] ==
        EXPECTED_TYPE_01_PLUS_HEADER_SHA256
    ]
    exe_rel = "SCUS_942.88"
    exe = (staged_root / exe_rel).read_bytes()
    verify_staged_input(exe_rel, exe, baselines)
    instructions = {}
    for label, (address, expected) in PARSER_WORDS.items():
        offset = EXE_HEADER + address - EXE_BASE
        actual = struct.unpack_from("<I", exe, offset)[0]
        if actual != expected:
            raise SystemExit(
                f"DAT parser instruction changed at 0x{address:08X}: "
                f"0x{actual:08X} != 0x{expected:08X}")
        instructions[label] = {
            "address": _hex(address), "instruction_word": _hex(actual),
        }
    parser = exe[
        EXE_HEADER + PARSER_START - EXE_BASE:
        EXE_HEADER + PARSER_END - EXE_BASE]
    asm = ROOT / "asm/hand_written/8001cdc0_dat_parser_relocator.s"
    return {
        "scan_scope": {
            "glob": "REBUILD/files/LEVEL*/*.DAT",
            "staged_input_count": len(rows),
            "type_01_record_count": sum(
                len(row["type_01_records"]) for row in rows),
            "all_inputs_hash_verified": True,
        },
        "staged_inputs": rows,
        "unique_runtime_window_matches": matches,
        "parser": {
            "resident_executable": "REBUILD/files/SCUS_942.88",
            "function_range": [_hex(PARSER_START), _hex(PARSER_END)],
            "function_size": len(parser),
            "function_sha256": _sha256_bytes(parser),
            "shipping_build_unit": str(asm.relative_to(ROOT)),
            "shipping_build_unit_sha256": _sha256(asm),
            "instructions": instructions,
            "bounded_semantics": (
                "For each non-negative top-level type t, store the current "
                "record pointer at 0x80096DA0 + t*4; non-0x3F records "
                "advance by header 4 + count*12."),
        },
    }


def _base_movie_pin(movie_path: Path) -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    path = movie_path.resolve()
    if not path.is_absolute():
        raise SystemExit("cold-boot C15 movie path must be absolute")
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise SystemExit("cold-boot C15 movie must be provisioned in the checkout") from exc
    if rel != MOVIE_FIXTURE_REL:
        raise SystemExit(
            f"cold-boot C15 movie must be {MOVIE_FIXTURE_REL}, got {rel}")
    pin = entries.get(rel)
    if not pin or pin.get("media_class") != "pristine_serial" or \
            not path.is_file() or path.stat().st_size != pin.get("size") or \
            _sha256(path) != pin.get("sha256") or \
            pin.get("sha256") != EXPECTED_MOVIE_SHA256:
        raise SystemExit(f"cold-boot C15 movie is not centrally pinned: {pin}")
    movie = json.loads(path.read_text())
    start = movie.get("start_state") or {}
    if movie.get("format") != "DuckStationInputMovie" or \
            movie.get("version") != 3 or start.get("from_boot") is not True or \
            start.get("game_serial") != "SCUS-94288" or \
            len(movie.get("frames") or []) <= TARGET_FRAME:
        raise SystemExit("cold-boot C15 movie is not a usable v3 from-boot fixture")
    return {
        # Keep the runtime path absolute: it is a transient/provisioning detail,
        # while the central manifest, hash, size and media class are authority.
        "path": str(path), "fixture": MOVIE_FIXTURE_REL,
        "sha256": pin["sha256"], "size": pin["size"],
        "media_class": pin["media_class"], "frames": len(movie["frames"]),
        "start_state": {"from_boot": True, "game_serial": "SCUS-94288"},
        "manifest": str(FIXTURE_SET.relative_to(ROOT)),
    }


def _card_path(config_dir: Path) -> Path:
    return Path(config_dir).resolve() / (
        "duckstation/memcards/Disney-Pixar A Bug's Life (USA)_1.mcd")


def _card_identity(config_dir: Path) -> dict[str, Any]:
    path = _card_path(config_dir)
    if not path.is_file():
        raise SystemExit(f"isolated progression card is absent: {path}")
    data = path.read_bytes()
    return {
        "isolated_card_path": str(path),
        "size": len(data),
        "sha256": _sha256_bytes(data),
        "progression_marker": PROGRESSION_MARKER.decode(),
        "progression_marker_count": data.count(PROGRESSION_MARKER),
    }


def _blank_card_identity(config_dir: Path) -> dict[str, Any]:
    path = _card_path(config_dir)
    if not path.exists():
        return {
            "isolated_card_path": str(path),
            "exists": False,
            "sha256": None,
            "expected_materialized_blank_sha256": BLANK_CARD_SHA256,
            "progression_marker_count": 0,
        }
    row = _card_identity(config_dir)
    if row["size"] != 131072 or row["sha256"] != BLANK_CARD_SHA256 or \
            row["progression_marker_count"] != 0:
        raise SystemExit(f"progression preparation did not start from a blank card: {row}")
    return {**row, "exists": True}


def _progression_state_pin() -> dict[str, Any]:
    pin = verify_declared_save_fixture(
        PROGRESSION_STATE, allowed_media_classes={"pristine"})
    if pin["sha256"] != EXPECTED_PROGRESSION_STATE_SHA256:
        raise SystemExit(f"progression state identity changed: {pin}")
    return pin


def _advance_frames(client: Any, frames: int) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    start = status.get("frame")
    if not isinstance(start, int):
        raise SystemExit(f"debugger returned no frame before progression: {status}")
    return client.call("emulator.advanceToFrame", {
        "frame": start + frames, "max_frames": frames + 10})


def _press(client: Any, button: str) -> dict[str, Any]:
    return client.call("emulator.pressButton", {
        "button": button, "frames": 10, "port": 0,
        "release_after": True})


def _movie_cleanup(client: Any, registry_ids: list[str] | None = None) -> None:
    try:
        client.call("movie.stopPlayback", {})
    except Exception:
        pass
    for movie_id in reversed(registry_ids or []):
        try:
            client.call("movie.remove", {"movieId": movie_id})
        except Exception:
            pass
    try:
        client.call("movie.clear", {})
    except Exception:
        pass


def _prepare_progression(
        client: Any, args: argparse.Namespace) -> dict[str, Any]:
    if args.instance_state != "recreated":
        raise SystemExit("progression preparation requires --instance-state recreated")
    status = client.call("debugger.status", {})
    media_before = verified_media_identity(client, status)
    state_pin = _progression_state_pin()
    state_inspection = inspect_state_before_load(
        client, PROGRESSION_STATE, media_before)

    client.call("debugger.pause", {})
    client.call("emulator.clearControllerState", {"port": 0})
    loaded = client.call("emulator.loadState", {
        "path": str(PROGRESSION_STATE.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False})
    if loaded.get("loaded") is not True:
        raise SystemExit(f"progression state did not load: {loaded}")
    blank = _blank_card_identity(args.config_dir)
    start = _runtime_snapshot(client, "progression_state_loaded")
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True}})
    _advance_frames(client, 1500)
    client.call("emulator.clearControllerState", {"port": 0})
    at_save_question = _runtime_snapshot(client, "level_complete_save_question")
    sequence = []
    sequence.append({"button": "cross", "response": _press(client, "cross")})
    sequence.append({"wait_frames": 400, "response": _advance_frames(client, 400)})
    sequence.append({"button": "square", "response": _press(client, "square")})
    sequence.append({"wait_frames": 1200, "response": _advance_frames(client, 1200)})
    sequence.append({"button": "square", "response": _press(client, "square")})
    sequence.append({"wait_frames": 1000, "response": _advance_frames(client, 1000)})
    sequence.append({"button": "square", "response": _press(client, "square")})
    sequence.append({"wait_frames": 1000, "response": _advance_frames(client, 1000)})
    generated = _card_identity(args.config_dir)
    media_after = verified_media_identity(
        client, client.call("debugger.status", {}))
    if start["scene"] != 1 or at_save_question["scene"] != 0 or \
            generated["size"] != 131072 or \
            generated["sha256"] != PROGRESSION_CARD_SHA256 or \
            generated["progression_marker_count"] != 1:
        raise SystemExit(
            "native progression recipe did not reproduce: "
            f"scenes={[start['scene'], at_save_question['scene']]}, "
            f"card={generated}")

    provenance = finish_run(
        args, generator="tools/phase4_respawn_row_provenance.py",
        anchor={
            "type": "transient native LEVEL01 completion to memory-card progression",
            "state": state_pin,
            "state_inspection": state_inspection,
            "media_identity": media_after,
            "generated_card": generated,
        },
        timing={
            "cpu_execution_mode": "CachedInterpreter",
            "cpu_overclock_percent": 100,
            "cd_read_speedup": 1,
            "cd_seek_speedup": 1,
            "rewind": False,
            "run_ahead": False,
            "recipe": {
                "hold_up_frames": 1500,
                "buttons": ["cross", "square", "square", "square"],
                "button_hold_frames": 10,
                "wait_frames": [400, 1200, 1000, 1000],
            },
        })
    receipt = {
        "schema": "abl-phase4-respawn-progression/1",
        "state": state_pin,
        "state_inspection": state_inspection,
        "blank_card": blank,
        "generated_card": generated,
        "start": start,
        "at_save_question": at_save_question,
        "sequence": sequence,
        "media_before": media_before,
        "media_after": media_after,
        "run_provenance": provenance,
    }
    receipt_path = Path(args.config_dir).resolve() / PROGRESSION_RECEIPT
    receipt_path.write_text(json.dumps(receipt, indent=1) + "\n")
    print(f"[respawn-row-provenance] prepared transient progression: {receipt_path}")
    return receipt


def _load_progression_receipt(args: argparse.Namespace) -> dict[str, Any]:
    if args.instance_state != "reused":
        raise SystemExit("C15 target replay requires --instance-state reused")
    path = Path(args.config_dir).resolve() / PROGRESSION_RECEIPT
    try:
        receipt = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"missing/invalid transient progression receipt: {path}: {exc}") from exc
    generated = receipt.get("generated_card") or {}
    run = receipt.get("run_provenance") or {}
    state = receipt.get("state") or {}
    current = _card_identity(args.config_dir)
    if receipt.get("schema") != "abl-phase4-respawn-progression/1" or \
            state.get("sha256") != EXPECTED_PROGRESSION_STATE_SHA256 or \
            generated.get("sha256") != PROGRESSION_CARD_SHA256 or \
            generated.get("progression_marker_count") != 1 or \
            current.get("sha256") != PROGRESSION_CARD_SHA256 or \
            current.get("progression_marker_count") != 1 or \
            (run.get("cleanup") or {}).get("owned_pid_stopped") is not True or \
            (run.get("debugger") or {}).get("recreated") is not True:
        raise SystemExit(
            "transient progression receipt/card did not verify: "
            f"receipt={receipt}, current={current}")
    return {"receipt": receipt, "current_card": current}


def _runtime_snapshot(client: Any, label: str) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    movie = client.call("movie.status", {})
    return {
        "label": label,
        "scene": _read_u32(client, SCENE_WORD),
        "frame": status.get("frame"),
        "cycle": status.get("cycle"),
        "pc": status.get("pc"),
        "sp": status.get("sp"),
        "movie": {
            "playing": movie.get("playing"),
            "playback_index": movie.get("playback_index"),
            "frame_count": movie.get("frame_count"),
            "reproducible": movie.get("reproducible"),
            "truncated": movie.get("truncated"),
        },
    }


def _existing_causal_join() -> dict[str, Any]:
    if _sha256(C15_ARTIFACT) != C15_ARTIFACT_SHA256:
        raise SystemExit("retained C15 causal artifact identity changed")
    doc = json.loads(C15_ARTIFACT.read_text())
    selector = doc["live"]["reset_owner"]["selector"]
    owner = doc["live"]["reset_owner"]
    branch = owner["branches"] \
        ["selected_x_source_plus_128"]["post_reset"]["snapshot"]
    denial = owner["branches"]["selector_status_bit_cleared"]
    denial_post = denial["post_reset"]["snapshot"]
    denial_coverage = denial["post_reset"]["cycle_neutral_trace"]["coverage"]
    denial_selector = next(
        (row for row in denial_coverage
         if row.get("label") == "overlay_safe_anchor_selector"), None)
    if selector["selected"]["index"] != SELECTED_ROW or \
            int(selector["runtime_table_pointer"], 16) != EXPECTED_TYPE_01_POINTER or \
            int(selector["selected_x_source_address"], 16) != \
            EXPECTED_SELECTED_ROW_ADDRESS or \
            branch["safe_anchor_xyz"] != [505792, 30120, 494016] or \
            branch["live_xyz"] != [505792, 30120, 494016] or \
            owner["selector_denial_single_variable_guard"][
                "changed_byte_addresses"] != ["0x800A6590"] or \
            denial["mutation"] != {
                "status_address": "0x800A6590", "cleared_mask": "0x0010",
                "status_before": 20, "status_after": 4} or \
            denial_post["safe_anchor_xyz"] != [507900, 31787, 503976] or \
            denial_post["live_xyz"] != [507900, 31787, 503976] or \
            denial_selector is None or denial_selector["total_hits"] != 17:
        raise SystemExit("retained C15 selected-row causal predicate changed")
    return {
        "artifact": str(C15_ARTIFACT.relative_to(ROOT)),
        "artifact_sha256": C15_ARTIFACT_SHA256,
        "selected_row": SELECTED_ROW,
        "selected_source_address": _hex(EXPECTED_SELECTED_ROW_ADDRESS),
        "single_variable_mutation": "selected raw X +128 only",
        "observed_effect": (
            "safe/live X +4096 at frame 157; Z and health/lives unchanged; "
            "Y ground-recomputed"),
        "mutated_safe_xyz": branch["safe_anchor_xyz"],
        "mutated_live_xyz": branch["live_xyz"],
        "selector_denial": {
            "single_changed_byte": "0x800A6590",
            "status_before": "0x0014",
            "status_after": "0x0004",
            "cleared_mask": "0x0010",
            "selector_total_hits": denial_selector["total_hits"],
            "post_safe_xyz": denial_post["safe_anchor_xyz"],
            "post_live_xyz": denial_post["live_xyz"],
        },
    }


def _run_live(
        client: Any, static: dict[str, Any], movie_path: Path,
        progression: dict[str, Any]) -> dict[str, Any]:
    pin = _base_movie_pin(movie_path)
    movie_doc = json.loads(movie_path.read_text())
    frames = movie_doc["frames"]
    for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
        pad = (frames[index].get("ports") or {}).get("0") or {}
        if pad.get("left") is not True:
            raise SystemExit(f"base LEVEL02 Left window changed at frame {index}")
    status = client.call("debugger.status", {})
    media_before = verified_media_identity(client, status)
    progression_config = Path(
        progression["current_card"]["isolated_card_path"]).parents[2]
    card_before = _card_identity(progression_config)
    client.call("debugger.pause", {})
    _movie_cleanup(client)
    registry_ids = []
    try:
        loaded = client.call("movie.load", {
            "path": str(movie_path.resolve())})
        control_started = client.call("movie.startPlayback", {
            "start_frame": 0, "load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": PRE_FRAME, "max_frames": PRE_FRAME + 100}, timeout=900)
        control_before = _runtime_snapshot(client, "control_before_edit_window")
        client.call("movie.advanceToFrame", {
            "frame": TARGET_FRAME, "max_frames": TARGET_FRAME - PRE_FRAME + 100},
            timeout=900)
        control_after = _runtime_snapshot(client, "control_wrong_scene")
        control_status = client.call("movie.status", {})
        client.call("movie.stopPlayback", {})

        base = client.call("movie.store", {})
        registry_ids.append(base["movieId"])
        branch = client.call("movie.branch", {
            "movieId": base["movieId"], "fromFrame": len(frames)})
        registry_ids.append(branch["movieId"])
        edits = []
        for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
            pad = dict(frames[index]["ports"]["0"])
            pad["left"] = False
            edits.append(client.call("movie.editFrame", {
                "movieId": branch["movieId"], "frame": index,
                "input": {"0": pad}}))
        activated = client.call("movie.activate", {"movieId": branch["movieId"]})
        edited_doc = client.call("movie.get", {"movieId": branch["movieId"]})
        edited_semantic_sha256 = _sha256_bytes(json.dumps(
            edited_doc, sort_keys=True, separators=(",", ":")).encode())
        edited_started = client.call("movie.startPlayback", {
            "start_frame": 0, "load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": PRE_FRAME, "max_frames": PRE_FRAME + 100}, timeout=900)
        before = _runtime_snapshot(client, "edited_before_edit_window")
        client.call("movie.advanceToFrame", {
            "frame": TARGET_FRAME, "max_frames": TARGET_FRAME - PRE_FRAME + 100},
            timeout=900)
        after = _runtime_snapshot(client, "edited_scene_loaded")

        dat_base = _read_u32(client, DAT_BASE_POINTER)
        type_pointer = _read_u32(client, DAT_TYPE_01_SLOT)
        header = _read_memory(client, type_pointer, 4)
        count, record_type = struct.unpack("<hh", header)
        record_size = _record_size(count, record_type)
        record = _read_memory(client, type_pointer, record_size)
        plus = _read_memory(client, type_pointer, record_size + 4)
        selected_address = type_pointer + 4 + SELECTED_ROW * 12
        selected_raw = _read_memory(client, selected_address, 12)
        selected_xyz = list(struct.unpack("<iii", selected_raw))
        final_movie = client.call("movie.status", {})
        media_after = verified_media_identity(
            client, client.call("debugger.status", {}))
        card_after = _card_identity(progression_config)
    finally:
        _movie_cleanup(client, registry_ids)

    matches = static["unique_runtime_window_matches"]
    equal_pre_edit = all(control_before.get(key) == before.get(key)
                         for key in ("scene", "frame", "cycle", "pc", "sp"))
    if control_started.get("reproducible") is not True or \
            control_after["scene"] != 1 or \
            control_status.get("reproducible") is not True or \
            control_status.get("truncated") is not False or \
            edited_semantic_sha256 != EXPECTED_EDITED_MOVIE_SEMANTIC_SHA256 or \
            edited_started.get("reproducible") is not True or \
            not equal_pre_edit or before["scene"] != 0 or \
            after["scene"] != EXPECTED_SCENE or \
            final_movie.get("reproducible") is not True or \
            final_movie.get("truncated") is not False or \
            card_before["sha256"] != PROGRESSION_CARD_SHA256 or \
            card_after != card_before or \
            dat_base != EXPECTED_DAT_BASE or \
            type_pointer != EXPECTED_TYPE_01_POINTER or \
            (count, record_type) != (EXPECTED_TYPE_01_COUNT, 1) or \
            _sha256_bytes(record) != EXPECTED_TYPE_01_RECORD_SHA256 or \
            _sha256_bytes(plus) != EXPECTED_TYPE_01_PLUS_HEADER_SHA256 or \
            selected_address != EXPECTED_SELECTED_ROW_ADDRESS or \
            selected_xyz != EXPECTED_SELECTED_ROW_XYZ or \
            _sha256_bytes(selected_raw) != EXPECTED_SELECTED_ROW_SHA256 or \
            len(matches) != 1 or matches[0]["path"] != \
            f"REBUILD/files/{EXPECTED_DAT}" or \
            matches[0]["offset"] != f"0x{EXPECTED_TYPE_01_OFFSET:X}":
        raise SystemExit(
            "C15 authored-row provenance predicates did not reproduce: "
            f"control={[control_started.get('reproducible'), control_after['scene'], control_status]}, "
            f"edited={[edited_semantic_sha256, edited_started.get('reproducible')]}, "
            f"pre_equal={equal_pre_edit}, scenes={[before['scene'], after['scene']]}, "
            f"movie={[final_movie.get('reproducible'), final_movie.get('truncated')]}, "
            f"cards={[card_before, card_after]}, "
            f"dat={[_hex(dat_base), _hex(type_pointer), count, record_type]}, "
            f"record={_sha256_bytes(record)}, plus={_sha256_bytes(plus)}, "
            f"selected={[_hex(selected_address), selected_xyz, _sha256_bytes(selected_raw)]}, "
            f"matches={matches}")

    return {
        "movie": pin,
        "movie_load": loaded,
        "progression": progression,
        "control": {
            "movie_start": control_started,
            "before": control_before,
            "after": control_after,
            "movie_status": control_status,
            "bounded_result": (
                "With the current transient LEV02:00 card, the unedited stale "
                "Left burst selects scene 1 instead of scene 3."),
        },
        "in_memory_edit": {
            "base_registry": base,
            "branch": branch,
            "activated": activated,
            "button_removed": "left",
            "start_frame": MOVIE_EDIT_START,
            "end_frame_exclusive": MOVIE_EDIT_END,
            "edited_frame_count": len(edits),
            "edited_movie_semantic_sha256": edited_semantic_sha256,
            "derivative_saved": False,
        },
        "movie_start": edited_started,
        "trace_window": [PRE_FRAME, TARGET_FRAME],
        "before": before,
        "after": after,
        "pre_edit_boundary_equal_to_control": equal_pre_edit,
        "movie_status": final_movie,
        "media_before": media_before,
        "media_after": media_after,
        "card_before": card_before,
        "card_after": card_after,
        "runtime_dat": {
            "base_pointer_global": _hex(DAT_BASE_POINTER),
            "base": _hex(dat_base),
            "type_table_base": _hex(DAT_TYPE_TABLE),
            "type_01_slot": _hex(DAT_TYPE_01_SLOT),
            "type_01_pointer": _hex(type_pointer),
            "type_01_file_offset": f"0x{type_pointer - dat_base:X}",
            "type": record_type,
            "count": count,
            "record_size": record_size,
            "record_sha256": _sha256_bytes(record),
            "plus_next_header_size": len(plus),
            "plus_next_header_sha256": _sha256_bytes(plus),
            "staged_byte_identical": True,
        },
        "selected_row": {
            "index": SELECTED_ROW,
            "runtime_address": _hex(selected_address),
            "file_offset": f"0x{selected_address - dat_base:X}",
            "raw_xyz": selected_xyz,
            "scaled_xz": [selected_xyz[0] * 32, selected_xyz[2] * 32],
            "row_sha256": _sha256_bytes(selected_raw),
            "staged_byte_identical": True,
        },
    }


def evidence_gaps(doc: dict[str, Any]) -> list[str]:
    gaps = []
    static = doc.get("static_census") or {}
    live = doc.get("live") or {}
    runtime = live.get("runtime_dat") or {}
    selected = live.get("selected_row") or {}
    causal = doc.get("existing_causal_join") or {}
    matches = static.get("unique_runtime_window_matches") or []
    parser = static.get("parser") or {}
    run = doc.get("run_provenance") or {}
    progression = live.get("progression") or {}
    receipt = progression.get("receipt") or {}
    progression_run = receipt.get("run_provenance") or {}
    current_card = progression.get("current_card") or {}
    control = live.get("control") or {}
    edit = live.get("in_memory_edit") or {}
    try:
        scenario = _declarative_scenario()
    except (OSError, yaml.YAMLError, SystemExit) as exc:
        scenario = {}
        gaps.append(f"declarative scenario failed: {exc}")
    if doc.get("schema") != "abl-phase4-respawn-row-provenance/2":
        gaps.append("schema changed")
    if doc.get("declarative_scenario") != scenario:
        gaps.append("declarative two-process scenario changed")
    if len(matches) != 1 or matches[0].get("path") != \
            "REBUILD/files/LEVEL03/LEVEL.DAT" or \
            matches[0].get("offset") != "0x458":
        gaps.append("staged DAT match is not unique LEVEL03 offset 0x458")
    if parser.get("function_sha256") != \
            "7ffcc86cb4c6f0af5dc27d591a07ccbe7315a427a66e6f2a715fee7c9b553981" or \
            ((parser.get("instructions") or {}).get(
                "nonnegative_type_pointer_store") or {}).get(
                    "instruction_word") != "0xAC520000":
        gaps.append("shipping DAT parser identity or slot store changed")
    if live.get("after", {}).get("scene") != EXPECTED_SCENE or \
            live.get("movie_status", {}).get("reproducible") is not True or \
            live.get("movie_status", {}).get("truncated") is not False:
        gaps.append("cold-boot scene replay changed")
    if receipt.get("schema") != "abl-phase4-respawn-progression/1" or \
            (receipt.get("state") or {}).get("sha256") != \
            EXPECTED_PROGRESSION_STATE_SHA256 or \
            (receipt.get("generated_card") or {}).get("sha256") != \
            PROGRESSION_CARD_SHA256 or \
            (receipt.get("generated_card") or {}).get(
                "progression_marker_count") != 1 or \
            (progression_run.get("cleanup") or {}).get(
                "owned_pid_stopped") is not True or \
            (progression_run.get("debugger") or {}).get("recreated") is not True or \
            current_card.get("sha256") != PROGRESSION_CARD_SHA256:
        gaps.append("native transient progression receipt/card changed")
    if (control.get("after") or {}).get("scene") != 1 or \
            (control.get("movie_status") or {}).get("reproducible") is not True or \
            (control.get("movie_status") or {}).get("truncated") is not False:
        gaps.append("unedited stale-movie control changed")
    if edit.get("button_removed") != "left" or \
            edit.get("start_frame") != MOVIE_EDIT_START or \
            edit.get("end_frame_exclusive") != MOVIE_EDIT_END or \
            edit.get("edited_frame_count") != MOVIE_EDIT_END - MOVIE_EDIT_START or \
            edit.get("edited_movie_semantic_sha256") != \
            EXPECTED_EDITED_MOVIE_SEMANTIC_SHA256 or \
            edit.get("derivative_saved") is not False or \
            live.get("pre_edit_boundary_equal_to_control") is not True:
        gaps.append("current-binary in-memory movie repair changed")
    if (live.get("card_before") or {}).get("sha256") != \
            PROGRESSION_CARD_SHA256 or \
            live.get("card_after") != live.get("card_before"):
        gaps.append("transient progression card changed during cold boot")
    if runtime.get("base") != _hex(EXPECTED_DAT_BASE) or \
            runtime.get("type_01_pointer") != _hex(EXPECTED_TYPE_01_POINTER) or \
            runtime.get("type_01_file_offset") != "0x458" or \
            runtime.get("count") != EXPECTED_TYPE_01_COUNT or \
            runtime.get("record_sha256") != EXPECTED_TYPE_01_RECORD_SHA256 or \
            runtime.get("staged_byte_identical") is not True:
        gaps.append("runtime type-0x01 record did not join the staged DAT")
    if selected.get("index") != SELECTED_ROW or \
            selected.get("runtime_address") != \
            _hex(EXPECTED_SELECTED_ROW_ADDRESS) or \
            selected.get("file_offset") != "0x4A4" or \
            selected.get("raw_xyz") != EXPECTED_SELECTED_ROW_XYZ or \
            selected.get("row_sha256") != EXPECTED_SELECTED_ROW_SHA256 or \
            selected.get("staged_byte_identical") is not True:
        gaps.append("selected row-6 source join changed")
    if causal.get("artifact_sha256") != C15_ARTIFACT_SHA256 or \
            causal.get("selected_row") != SELECTED_ROW or \
            causal.get("selected_source_address") != \
            _hex(EXPECTED_SELECTED_ROW_ADDRESS) or \
            causal.get("mutated_safe_xyz") != [505792, 30120, 494016] or \
            causal.get("mutated_live_xyz") != [505792, 30120, 494016] or \
            causal.get("selector_denial") != {
                "single_changed_byte": "0x800A6590",
                "status_before": "0x0014", "status_after": "0x0004",
                "cleared_mask": "0x0010", "selector_total_hits": 17,
                "post_safe_xyz": [507900, 31787, 503976],
                "post_live_xyz": [507900, 31787, 503976]}:
        gaps.append("prior selected-row causal join changed")
    for label in ("media_before", "media_after"):
        if ((live.get(label) or {}).get("hash_verification") or {}).get(
                "pristine_verified") is not True:
            gaps.append(f"{label} is not hash-verified pristine media")
    for label in ("media_before", "media_after"):
        if (((receipt.get(label) or {}).get("hash_verification") or {}).get(
                "pristine_verified") is not True):
            gaps.append(f"progression {label} is not hash-verified pristine media")
    if (run.get("cleanup") or {}).get("owned_pid_stopped") is not True:
        gaps.append("isolated owned PID was not stopped")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    scenario = _declarative_scenario()
    capabilities = client.call("debugger.capabilities", {})
    common_required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "emulator.getMediaInfo",
    }
    progression_required = {
        "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.pressButton", "emulator.advanceToFrame",
    }
    target_required = {
        "debugger.readMemory", "movie.load", "movie.store", "movie.branch",
        "movie.editFrame", "movie.activate", "movie.get", "movie.remove",
        "movie.startPlayback", "movie.advanceToFrame", "movie.stopPlayback",
        "movie.status", "movie.clear",
    }
    required = common_required | (
        progression_required if args.prepare_progression else target_required)
    missing = sorted(method for method in required
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks C15 provenance methods: {missing}")

    if args.prepare_progression:
        _prepare_progression(client, args)
        return 0
    if args.movie is None:
        raise SystemExit("target replay requires --movie")

    static = build_static_census()
    causal = _existing_causal_join()
    progression = _load_progression_receipt(args)
    live = _run_live(client, static, args.movie, progression)
    provenance = finish_run(
        args, generator="tools/phase4_respawn_row_provenance.py",
        anchor={
            "type": (
                "current-binary cold-boot authored DAT type-0x01 row provenance "
                "after native transient progression"),
            "movie": live["movie"],
            "media_identity": live["media_after"],
            "progression_card": live["card_after"],
        },
        timing={
            "cpu_execution_mode": "CachedInterpreter",
            "cpu_overclock_percent": 100,
            "cd_read_speedup": 1,
            "cd_seek_speedup": 1,
            "rewind": False,
            "run_ahead": False,
            "movie_window": [PRE_FRAME, TARGET_FRAME],
        })
    document = {
        "_comment": (
            "Phase-4 C15 provenance: native progression generated from a pinned "
            "pristine LEVEL01 completion state supplies a transient LEV02:00 card. "
            "After an emulator restart, a nine-frame in-memory repair of the pinned "
            "from-boot movie joins the live scene-3 DAT type-0x01 pointer and selected "
            "row to the unique hash-pinned LEVEL03/LEVEL.DAT record and the prior "
            "causal row mutation and one-bit selector denial. No memory-card or "
            "derivative-movie bytes are retained."),
        "schema": "abl-phase4-respawn-row-provenance/2",
        "generated": date.today().isoformat(),
        "campaign_state": "active_partial",
        "declarative_scenario": scenario,
        "static_census": static,
        "live": live,
        "existing_causal_join": causal,
        "bounded_conclusion": (
            "In scene 3, 0x80096DA4 is not a bespoke respawn-table owner. It is "
            "DAT type-table slot 1, populated by the resident parser with the "
            "LEVEL03/LEVEL.DAT type-0x01 record at file offset 0x458. The "
            "LEVEL03 respawn selector causally consumes authored row 6 from "
            "that record. Clearing only player status mask 0x0010 at the exact "
            "frame-156 boundary denies all selector stores while the resident "
            "handler consumes the prior safe anchor. The current-binary cold boot "
            "is independent of the old undeclared completed-game memory card; "
            "the mask source/general policy and other variants remain open."),
        "remaining": [
            "Source and general activation policy of status mask 0x0010, denial behavior in other row-selecting variants, plus reset scope.",
            "Indirect/additional overlay variants, actor, scripted and exceptional death classes, remaining-stage, save/load and scene-transition breadth.",
        ],
        "source_dependencies": {
            "analysis/phase4_checkpoint_respawn.json": C15_ARTIFACT_SHA256,
            MOVIE_FIXTURE_REL: EXPECTED_MOVIE_SHA256,
            "level01_end_of_stage.sav": EXPECTED_PROGRESSION_STATE_SHA256,
            str(SCENARIO.relative_to(ROOT)): _sha256(SCENARIO),
            "tools/build_identity.py": _sha256(ROOT / "tools/build_identity.py"),
            "docs/DAT_FORMAT_AND_RELOCATION.md": _sha256(
                ROOT / "docs/DAT_FORMAT_AND_RELOCATION.md"),
        },
        "run_provenance": provenance,
    }
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained C15 provenance predicates failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print(f"[respawn-row-provenance] retained C15 evidence: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    parser.add_argument("--movie", type=Path)
    parser.add_argument(
        "--prepare-progression", action="store_true",
        help="generate and receipt a transient LEV02:00 card, then stop the owned PID")
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(
                args, generator="tools/phase4_respawn_row_provenance.py",
                anchor={"type": "aborted before retained C15 row provenance"},
                timing={})
        except BaseException as cleanup_error:
            print(
                f"owned C15 provenance instance cleanup also failed: {cleanup_error}",
                file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
