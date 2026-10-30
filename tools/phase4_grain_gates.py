#!/usr/bin/env python3
"""Regenerate the completed Phase-4 E09 native grain-gate campaign.

The campaign consumes the complete operator E09 movie directory only through
the central fixture manifest.  It replays every v3 movie from its inspected
pristine save, records natural outcomes, and pairs the three City Entrance
threshold-minus-one recordings with a single-byte threshold control.  It then
reproduces successful-open native death/respawn in both implementations and a
native frontend card save/load classification using an existing pinned movie.
"""
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
    from build_identity import verify_staged_input
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
except ModuleNotFoundError:
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_grain_gates.json"
MOVIE_DIR = ROOT / "movies/Phase4/E09"
GRAIN = 0x800A65A1
LIVES = 0x800A65A0
SCENE = 0x80082504

TUNNELS_TABLE = 0x800B4C1C
TUNNELS_COUNT = 9
TUNNELS_STRIDE = 0x14
TUNNELS_CODE = (0x800B4490, 0x800B4648)
TUNNELS_DENIAL_TIMER = 0x800B4D10

CITY_STATE = 0x800B4570
CITY_DENIAL_TIMER = 0x800B456C
CITY_CODE = (0x800B3D84, 0x800B3F38)
CITY_OVERLAY_REL = "LEVEL04/LEVEL.BIN"
CITY_OVERLAY = ROOT / "REBUILD/files" / CITY_OVERLAY_REL
CITY_OVERLAY_FUNCTION_OFFSET = 0x3E4

MEMORY_OVERLAY_REL = "BITS/MEMORY.BIN"
MEMORY_OVERLAY = ROOT / "REBUILD/files" / MEMORY_OVERLAY_REL
MEMORY_LOAD_BASE = 0x800B5788
MEMORY_CODE_FILE_OFFSET = 0x800
PROGRESS_BLOCK = 0x8009EC68
PROGRESS_BLOCK_LENGTH = 336
PROGRESS_MUTATION_OFFSET = PROGRESS_BLOCK_LENGTH - 1
MENU_MOVIE_REL = "movies/Menu-Navigation.movie_v2.json"
MENU_MOVIE = ROOT / MENU_MOVIE_REL
RUNTIME_FIXTURES = ROOT / "config/phase3_runtime_fixtures.yaml"
CARD_NAME = "Disney-Pixar A Bug's Life (USA)_1.mcd"

PLAYER_BASE = 0x800A6500
PLAYER_HEALTH = PLAYER_BASE + 0x94
ACTOR_BASE = 0x8009FD80
ACTOR_STRIDE = 0x84
ACTOR_CAPACITY = 64
LIFECYCLE_ACTORS = {
    "tunnels": {"index": 18, "expected_id": 9, "gate_index": 3},
    "city": {"index": 14, "expected_id": 17, "gate_index": 0},
}

MEMORY_WORDS = {
    "load_destination": (0x800BAB60, 0x24E7EC68),
    "load_source": (0x800BAB64, 0x24660288),
    "load_end": (0x800BAB74, 0x246803D8),
    "save_source": (0x800BADAC, 0x24C6EC68),
    "save_destination": (0x800BADB0, 0x24470288),
    "save_end": (0x800BADC0, 0x24C80150),
}

MOVIES = [
    "LEVEL02_gate01_closed_open.movie.json",
    "LEVEL02_gate02_closed_open.movie.json",
    "LEVEL02_gate03_closed_open.movie.json",
    "LEVEL02_gate04_closed_open.movie.json",
    "LEVEL02_gate05_open.movie.json",
    "LEVEL02_gate06_open.movie.json",
    "LEVEL02_gate07_closed_open.movie.json",
    "LEVEL02_gate08_closed_open.movie.json",
    "LEVEL02_gate09_closed_open.movie.json",
    "LEVEL07_gate01_closed_open.movie.json",
    "LEVEL07_gate02_closed_open.movie.json",
    "LEVEL07_gate03_closed_open.movie.json",
]

EXPECTED_TUNNELS_TABLE = [
    [4295, 26, 20, 193754, 131692],
    [4295, 23, 10, 505642, -451306],
    [4295, 24, 10, 832302, 291075],
    [4295, 22, 10, 509676, 510143],
    [4295, 25, 20, 833246, 612273],
    [4295, 21, 20, 1142934, 1308289],
    [4295, 28, 30, 1471643, 1410369],
    [4295, 20, 10, 1202034, 1986285],
    [4295, 27, 30, 1634925, 2534812],
]

TUNNELS_WORDS = {
    "grain_read": (0x800B44BC, 0x92630000),
    "threshold_read": (0x800B44C0, 0x8C420008),
    "threshold_compare": (0x800B44C8, 0x0062182A),
    "closed_to_armed_writer": (0x800B4530, 0xAE550000),
    "denial_radius_40": (0x800B45CC, 0x28420640),
    "denial_sfx_76": (0x800B45D4, 0x2404004C),
    "denial_cooldown_60": (0x800B45F8, 0x2442003C),
    "open_floor_compare": (0x800B4614, 0x28C20709),
    "drop_step_minus_140": (0x800B4620, 0x24C6FF74),
    "drop_writer": (0x800B4624, 0xAE460000),
    "geometry_call": (0x800B462C, 0x0C00A40C),
    "nine_row_loop": (0x800B463C, 0x2A22002D),
}

CITY_WORDS = {
    "closed_sentinel": (0x800B3DC4, 0x2403FFFF),
    "grain_read": (0x800B3E04, 0x908465A1),
    "ten_times_index_plus_one": (0x800B3E10, 0x00021040),
    "threshold_compare": (0x800B3E14, 0x0082202A),
    "open_state_32": (0x800B3E28, 0x24020020),
    "state_writer": (0x800B3E2C, 0xAE220000),
    "open_feedback_call": (0x800B3E30, 0x0C00E3BA),
    "denial_sfx_76": (0x800B3E60, 0x2404004C),
    "denial_cooldown_60": (0x800B3E84, 0x2442003C),
    "denial_audio_call": (0x800B3E90, 0x0C014310),
    "countdown_writer": (0x800B3EC0, 0xAC620000),
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _word(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    data = bytes.fromhex(row["hex"])
    if len(data) != length:
        raise SystemExit(f"short debugger read at 0x{address:08X}")
    return data


def _read_u8(client: Any, address: int) -> int:
    return _read_memory(client, address, 1)[0]


def _read_u32(client: Any, address: int) -> int:
    return struct.unpack("<I", _read_memory(client, address, 4))[0]


def _read_s16(client: Any, address: int) -> int:
    return struct.unpack("<h", _read_memory(client, address, 2))[0]


def _s32(value: int) -> int:
    return value - 0x100000000 if value & 0x80000000 else value


def _method_present(capabilities: dict[str, Any], method: str) -> bool:
    return any((row.get("name") if isinstance(row, dict) else row) == method
               for row in capabilities.get("methods") or [])


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    rows = []
    for name in MOVIES:
        rel = f"movies/Phase4/E09/{name}"
        path = ROOT / rel
        pin = entries.get(rel)
        if not isinstance(pin, dict) or pin.get("media_class") != "pristine_serial":
            raise SystemExit(f"E09 movie is not centrally pristine_serial: {rel}")
        if pin.get("size") != path.stat().st_size or pin.get("sha256") != _sha256(path):
            raise SystemExit(f"E09 movie pin drifted: {rel}")
        movie = json.loads(path.read_text())
        start = movie.get("start_state") or {}
        save_path = Path(start.get("path") or "")
        save_rel = f"movies/Phase4/E09/{save_path.name}"
        declaration = verify_declared_save_fixture(
            ROOT / save_rel, allowed_media_classes={"pristine"})
        if movie.get("version") != 3 or movie.get("game_serial") != "SCUS-94288" \
                or start.get("game_serial") != "SCUS-94288" \
                or start.get("reproducible_only_from_state") is not True \
                or not movie.get("frames") \
                or start.get("file_size") != declaration["size"]:
            raise SystemExit(f"E09 movie metadata drifted: {rel}")
        rows.append({
            "path": rel, "sha256": pin["sha256"], "size": pin["size"],
            "media_class": pin["media_class"], "version": movie["version"],
            "initial_frame": movie["initial_frame"],
            "frames": len(movie["frames"]), "save": declaration,
        })
    menu_pin = entries.get(MENU_MOVIE_REL)
    if not isinstance(menu_pin, dict) or \
            menu_pin.get("media_class") != "pristine_serial" or \
            menu_pin.get("size") != MENU_MOVIE.stat().st_size or \
            menu_pin.get("sha256") != _sha256(MENU_MOVIE):
        raise SystemExit(f"native-card movie pin drifted: {MENU_MOVIE_REL}")
    menu = json.loads(MENU_MOVIE.read_text())
    if menu.get("version") != 3 or menu.get("game_serial") != "SCUS-94288" or \
            (menu.get("start_state") or {}).get("from_boot") is not True or \
            len(menu.get("frames") or []) != 7362:
        raise SystemExit("native-card movie metadata drifted")
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "movies": rows, "count": len(rows),
        "shared_card_movie": {
            "path": MENU_MOVIE_REL, "sha256": menu_pin["sha256"],
            "size": menu_pin["size"], "media_class": menu_pin["media_class"],
            "version": menu["version"], "frames": len(menu["frames"]),
            "start_state": "from_boot",
        },
    }


def _memory_file_offset(address: int) -> int:
    return MEMORY_CODE_FILE_OFFSET + address - MEMORY_LOAD_BASE


def build_static_census() -> dict[str, Any]:
    data = CITY_OVERLAY.read_bytes()
    verify_staged_input(CITY_OVERLAY_REL, data)
    start, end = CITY_CODE
    region = data[CITY_OVERLAY_FUNCTION_OFFSET:
                  CITY_OVERLAY_FUNCTION_OFFSET + end - start]
    words = {}
    for name, (address, expected) in CITY_WORDS.items():
        offset = CITY_OVERLAY_FUNCTION_OFFSET + address - start
        actual = _word(data, offset)
        if actual != expected:
            raise SystemExit(
                f"pristine City gate word drifted at 0x{address:08X}: "
                f"0x{actual:08X} != 0x{expected:08X}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    memory = MEMORY_OVERLAY.read_bytes()
    verify_staged_input(MEMORY_OVERLAY_REL, memory)
    memory_words = {}
    for name, (address, expected) in MEMORY_WORDS.items():
        actual = _word(memory, _memory_file_offset(address))
        if actual != expected:
            raise SystemExit(
                f"pristine MEMORY card word drifted at 0x{address:08X}: "
                f"0x{actual:08X} != 0x{expected:08X}")
        memory_words[name] = {
            "address": f"0x{address:08X}", "word": f"0x{actual:08X}"}
    return {
        "city_overlay": {"path": f"REBUILD/files/{CITY_OVERLAY_REL}",
                         "sha256": _sha256(CITY_OVERLAY), "size": len(data),
                         "load_base": "0x800B39A0"},
        "city_function": {"start": f"0x{start:08X}",
                          "end_exclusive": f"0x{end:08X}",
                          "file_offset": f"0x{CITY_OVERLAY_FUNCTION_OFFSET:X}",
                          "sha256": _sha256_bytes(region), "words": words},
        "memory_overlay": {
            "path": f"REBUILD/files/{MEMORY_OVERLAY_REL}",
            "sha256": _sha256(MEMORY_OVERLAY), "size": len(memory),
            "load_base": f"0x{MEMORY_LOAD_BASE:08X}",
            "code_file_offset": f"0x{MEMORY_CODE_FILE_OFFSET:X}",
        },
        "card_serialization": {
            "source_start": f"0x{PROGRESS_BLOCK:08X}",
            "length": PROGRESS_BLOCK_LENGTH,
            "source_end_exclusive":
                f"0x{PROGRESS_BLOCK + PROGRESS_BLOCK_LENGTH:08X}",
            "save_buffer_offset": 648,
            "save_copy": "resident scene/progress block -> card file buffer",
            "load_copy": "card file buffer -> resident scene/progress block",
            "instruction_words": memory_words,
            "excluded_overlay_state": [
                f"0x{TUNNELS_TABLE:08X}", f"0x{CITY_STATE:08X}"],
            "grain_hud_mirror": f"0x{GRAIN:08X}",
            "grain_hud_mirror_serialized_directly": False,
            "classification": (
                "native card data owns resident scene/pickup progress, not "
                "Region-A gate state or the live grain HUD mirror"),
        },
        "law": {
            "city_gate_count": 3, "city_thresholds": [10, 20, 30],
            "city_closed": -1, "city_open_countdown_start": 32,
            "denial_sfx": 76, "denial_cooldown_base": 60,
            "denial_cooldown_rule": "next byte from pointer 0x800822F4 plus 60, then decrement once per gate update",
            "tunnels_gate_count": 9, "tunnels_closed": 4295,
            "tunnels_armed": 4200, "tunnels_drop_step": -140,
            "tunnels_final": 1680,
        },
    }


def static_census_gaps(doc: dict[str, Any]) -> list[str]:
    gaps = []
    law = doc.get("law") or {}
    expected = {
        "city_gate_count": 3, "city_thresholds": [10, 20, 30],
        "city_closed": -1, "city_open_countdown_start": 32,
        "denial_sfx": 76, "denial_cooldown_base": 60,
        "denial_cooldown_rule": "next byte from pointer 0x800822F4 plus 60, then decrement once per gate update",
        "tunnels_gate_count": 9, "tunnels_closed": 4295,
        "tunnels_armed": 4200, "tunnels_drop_step": -140,
        "tunnels_final": 1680,
    }
    if law != expected:
        gaps.append("native grain-gate law drifted")
    if set((doc.get("city_function") or {}).get("words") or {}) != set(CITY_WORDS):
        gaps.append("City gate instruction frontier is incomplete")
    card = doc.get("card_serialization") or {}
    if card.get("source_start") != "0x8009EC68" or \
            card.get("length") != 336 or \
            card.get("source_end_exclusive") != "0x8009EDB8" or \
            set(card.get("instruction_words") or {}) != set(MEMORY_WORDS) or \
            card.get("excluded_overlay_state") != ["0x800B4C1C", "0x800B4570"] or \
            card.get("grain_hud_mirror_serialized_directly") is not False:
        gaps.append("native card serialization boundary drifted")
    return gaps


def _movie_cleanup(client: Any) -> None:
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass
    try:
        client.call("emulator.clearControllerState", {"port": 0})
    except Exception:
        pass


def _tunnels_table(client: Any) -> list[dict[str, int]]:
    raw = _read_memory(client, TUNNELS_TABLE, TUNNELS_COUNT * TUNNELS_STRIDE)
    rows = []
    for index in range(TUNNELS_COUNT):
        values = struct.unpack_from("<iiiii", raw, index * TUNNELS_STRIDE)
        rows.append(dict(zip(("state", "id", "threshold", "x", "z"), values),
                         index=index))
    return rows


def _snapshot(client: Any, expected_scene: int | None = None) -> dict[str, Any]:
    scene = _read_u32(client, SCENE)
    row: dict[str, Any] = {
        "status": client.call("debugger.status", {}),
        "scene": scene, "grain": _read_u8(client, GRAIN),
        "lives": _read_u8(client, LIVES),
    }
    if scene == 3 or expected_scene == 3:
        row["tunnels_table"] = _tunnels_table(client)
        row["tunnels_denial_timer"] = _s32(_read_u32(client, TUNNELS_DENIAL_TIMER))
    if scene == 4 or expected_scene == 4:
        row["city_gate_states"] = [
            _s32(_read_u32(client, CITY_STATE + index * 4)) for index in range(3)]
        row["city_denial_timer"] = _s32(_read_u32(client, CITY_DENIAL_TIMER))
    return row


def _player_snapshot(client: Any) -> dict[str, Any]:
    raw = _read_memory(client, PLAYER_BASE, 0x98)
    s32 = lambda offset: struct.unpack_from("<i", raw, offset)[0]
    return {
        "position": [s32(offset) for offset in (0x00, 0x04, 0x08)],
        "previous_position": [s32(offset) for offset in (0x10, 0x14, 0x18)],
        "safe_anchor": [s32(offset) for offset in (0x50, 0x54, 0x58)],
        "health": struct.unpack_from("<h", raw, 0x94)[0],
    }


def _lifecycle_snapshot(client: Any, expected_scene: int) -> dict[str, Any]:
    return {**_snapshot(client, expected_scene), "player": _player_snapshot(client)}


def _actor_snapshot(client: Any, index: int) -> dict[str, Any]:
    if not 0 <= index < ACTOR_CAPACITY:
        raise SystemExit(f"actor index outside fixed pool: {index}")
    address = ACTOR_BASE + index * ACTOR_STRIDE
    raw = _read_memory(client, address, ACTOR_STRIDE)
    return {
        "index": index, "address": f"0x{address:08X}",
        "id": struct.unpack_from("<I", raw, 0)[0],
        "position": [struct.unpack_from("<i", raw, offset)[0]
                     for offset in (0x04, 0x08, 0x0C)],
        "state": struct.unpack_from("<h", raw, 0x6C)[0],
        "callback": f"0x{struct.unpack_from('<I', raw, 0x7C)[0]:08X}",
    }


def _write_u16(client: Any, address: int, value: int) -> dict[str, Any]:
    return client.call("debugger.writeU16", {
        "address": f"0x{address:08X}", "value": value & 0xFFFF})


def _write_u32(client: Any, address: int, value: int) -> dict[str, Any]:
    return client.call("debugger.writeU32", {
        "address": f"0x{address:08X}", "value": value & 0xFFFFFFFF})


def _set_player_position(client: Any, xyz: list[int]) -> list[dict[str, Any]]:
    return [_write_u32(client, PLAYER_BASE + offset, value)
            for offset, value in zip((0x00, 0x04, 0x08, 0x10, 0x14, 0x18),
                                     (*xyz, *xyz))]


def _gate_projection(row: dict[str, Any], implementation: str) -> Any:
    if implementation == "tunnels":
        return [gate["state"] for gate in row["tunnels_table"]]
    return list(row["city_gate_states"])


def _run_successful_open_respawn(client: Any, implementation: str,
                                 precondition: dict[str, Any]) -> dict[str, Any]:
    spec = LIFECYCLE_ACTORS[implementation]
    expected_scene = 3 if implementation == "tunnels" else 4
    before = _lifecycle_snapshot(client, expected_scene)
    actor = _actor_snapshot(client, spec["index"])
    if before["scene"] != expected_scene or actor["id"] != spec["expected_id"]:
        raise SystemExit(
            f"{implementation} lifecycle precondition drifted: "
            f"scene={before['scene']} actor={actor}")
    before_gate = _gate_projection(before, implementation)
    expected_open = 1680 if implementation == "tunnels" else 0
    if before_gate[spec["gate_index"]] != expected_open:
        raise SystemExit(
            f"{implementation} target gate is not open: {before_gate}")

    writes = [_write_u16(client, PLAYER_HEALTH, 0)]
    writes.extend(_set_player_position(client, actor["position"]))
    trigger, fatal = [], None
    for _ in range(30):
        client.call("emulator.advanceFrames", {"frames": 1})
        row = _lifecycle_snapshot(client, expected_scene)
        trigger.append(row)
        if row["player"]["health"] < 0:
            fatal = row
            break
    if fatal is None:
        raise SystemExit(f"{implementation} native fatal contact did not begin")

    flow, respawn = [], None
    for _ in range(10):
        client.call("emulator.advanceFrames", {"frames": 60})
        row = _lifecycle_snapshot(client, expected_scene)
        flow.append(row)
        if row["lives"] == before["lives"] - 1 and row["player"]["health"] == 4:
            respawn = row
            break
    if respawn is None:
        raise SystemExit(f"{implementation} native respawn did not complete")

    fatal_gate = _gate_projection(fatal, implementation)
    respawn_gate = _gate_projection(respawn, implementation)
    displacement = [respawn["player"]["position"][index] -
                    before["player"]["safe_anchor"][index]
                    for index in range(3)]
    if fatal["scene"] != expected_scene or respawn["scene"] != expected_scene or \
            fatal["grain"] != before["grain"] or respawn["grain"] != before["grain"] or \
            fatal_gate != before_gate or respawn_gate != before_gate or \
            respawn["player"]["safe_anchor"] != before["player"]["safe_anchor"] or \
            any(abs(value) > 2048 for value in displacement):
        raise SystemExit(
            f"{implementation} successful-open state did not survive native "
            f"death/safe-anchor respawn")
    return {
        "implementation": implementation,
        "precondition": precondition,
        "target_gate_index": spec["gate_index"],
        "target_open_state": expected_open,
        "actor": actor,
        "perturbation": (
            "health:=0 and current/previous position:=verified hostile actor "
            "center; all subsequent death, life decrement and safe-anchor "
            "recovery are native"),
        "writes": writes, "before": before, "trigger": trigger,
        "fatal": fatal, "flow": flow, "respawn": respawn,
        "respawn_minus_safe_anchor": displacement,
        "classification": (
            "same-scene native death preserves the already-open gate, grain "
            "count and safe anchor while decrementing one life"),
    }


def _run_movie(client: Any, fixture: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / fixture["path"]
    _movie_cleanup(client)
    loaded = client.call("movie.load", {"path": str(path.resolve())})
    started = client.call("movie.startPlayback", {"load_start_state": True})
    before = _snapshot(client)
    frame = fixture["frames"] - 1
    client.call("movie.advanceToFrame", {"frame": frame,
                                          "max_frames": fixture["frames"] + 8},
                timeout=900)
    client.call("emulator.advanceFrames", {"frames": 1})
    after = _snapshot(client, expected_scene=before["scene"])
    status = client.call("movie.status", {})
    _movie_cleanup(client)
    if started.get("reproducible") is not True or status.get("reproducible") is not True \
            or status.get("truncated") is not False:
        raise SystemExit(f"E09 movie did not reproduce: {fixture['path']}: {status}")
    return {"fixture": fixture, "load": loaded, "started": started,
            "before": before, "after": after, "status": status}


def _run_city_threshold_control(client: Any, fixture: dict[str, Any],
                                index: int) -> dict[str, Any]:
    save = ROOT / fixture["save"]["path"]
    _movie_cleanup(client)
    loaded_state = client.call("emulator.loadState", {
        "path": str(save.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False})
    before = _snapshot(client)
    threshold = 10 * (index + 1)
    write = client.call("debugger.writeU8", {
        "address": f"0x{GRAIN:08X}", "value": threshold})
    loaded_movie = client.call("movie.load", {
        "path": str((ROOT / fixture["path"]).resolve())})
    started = client.call("movie.startPlayback", {"load_start_state": False})
    client.call("movie.advanceToFrame", {"frame": fixture["frames"] - 1,
                                          "max_frames": fixture["frames"] + 8},
                timeout=900)
    client.call("emulator.advanceFrames", {"frames": 1})
    after = _snapshot(client, expected_scene=4)
    status = client.call("movie.status", {})
    _movie_cleanup(client)
    if before["grain"] != threshold - 1 or before["city_gate_states"][index] != -1 \
            or after["grain"] != threshold or after["city_gate_states"][index] != 0 \
            or status.get("truncated") is not False:
        raise SystemExit(f"City gate threshold control failed for gate {index}: "
                         f"{before} -> {after}")
    return {"fixture": fixture, "gate_index": index, "threshold": threshold,
            "mutation": {"address": f"0x{GRAIN:08X}",
                         "before": threshold - 1, "after": threshold,
                         "write": write,
                         "movie_reproducible_flag_expected_false": True},
            "state_load": loaded_state, "movie_load": loaded_movie,
            "started": started, "before": before, "after": after,
            "status": status}


def _advance_movie(client: Any, target: int, current: int) -> int:
    while current < target:
        next_frame = min(target, current + 500)
        client.call("movie.advanceToFrame", {
            "frame": next_frame, "max_frames": next_frame - current + 8},
            timeout=900)
        current = next_frame
    return current


def _find_offsets(haystack: bytes, needle: bytes) -> list[int]:
    offsets, cursor = [], 0
    while True:
        cursor = haystack.find(needle, cursor)
        if cursor < 0:
            return offsets
        offsets.append(cursor)
        cursor += 1


def _card_diff(before: bytes, after: bytes) -> dict[str, Any]:
    changed = [index for index, pair in enumerate(zip(before, after))
               if pair[0] != pair[1]]
    spans = []
    for offset in changed:
        if not spans or offset != spans[-1][1] + 1:
            spans.append([offset, offset])
        else:
            spans[-1][1] = offset
    return {
        "size_before": len(before), "size_after": len(after),
        "changed_bytes": len(changed),
        "first_changed_offset": changed[0] if changed else None,
        "last_changed_offset": changed[-1] if changed else None,
        "changed_128_byte_frames": sorted({offset // 128 for offset in changed}),
        "changed_8192_byte_blocks": sorted({offset // 8192 for offset in changed}),
        "contiguous_span_count": len(spans),
    }


def _verify_repro_config(args: argparse.Namespace) -> dict[str, Any]:
    declared = yaml.safe_load(RUNTIME_FIXTURES.read_text())["fixtures"] \
        ["go_to_end_repro_memory_card"]
    seed = Path(args.card_seed).expanduser().resolve()
    if not seed.is_file() or seed.stat().st_size != declared["size"] or \
            _sha256(seed) != declared["sha256"]:
        raise SystemExit("native-card seed does not match its central runtime pin")
    config = Path(args.config_dir).resolve()
    isolated = config / "duckstation/memcards" / CARD_NAME
    if not isolated.is_file() or _sha256(isolated) != declared["sha256"]:
        raise SystemExit("isolated native-card copy was not freshly seeded")
    settings = (config / "duckstation/settings.ini").read_text()
    required = (
        "PatchFastBoot=false", "ExecutionMode=CachedInterpreter",
        "OverclockEnable=false", "Enable8MBRAM=false", "Directory=memcards")
    missing = [line for line in required if line not in settings]
    if missing:
        raise SystemExit(f"native-card repro settings missing: {missing}")
    return {
        "manifest": RUNTIME_FIXTURES.relative_to(ROOT).as_posix(),
        "seed_path": str(seed), "seed_sha256": declared["sha256"],
        "seed_size": declared["size"],
        "isolated_card_path": str(isolated),
        "isolated_card_initial_sha256": _sha256(isolated),
        "settings": list(required),
        "launcher": "tools/launch_repro_playback.sh",
    }


def _progress_snapshot(client: Any) -> dict[str, Any]:
    block = _read_memory(client, PROGRESS_BLOCK, PROGRESS_BLOCK_LENGTH)
    return {
        "status": client.call("debugger.status", {}),
        "movie_status": client.call("movie.status", {}),
        "scene": _read_u32(client, SCENE), "grain": _read_u8(client, GRAIN),
        "block_sha256": _sha256_bytes(block),
        "controlled_byte_offset": PROGRESS_MUTATION_OFFSET,
        "controlled_byte": block[PROGRESS_MUTATION_OFFSET],
    }


def _run_card_persistence(client: Any, args: argparse.Namespace,
                          fixture: dict[str, Any]) -> dict[str, Any]:
    repro = _verify_repro_config(args)
    seed = Path(repro["seed_path"])
    card = Path(repro["isolated_card_path"])
    seed_before = seed.read_bytes()
    card_before = card.read_bytes()
    if card_before != seed_before:
        raise SystemExit("isolated card differs from its verified seed before replay")

    _movie_cleanup(client)
    loaded = client.call("movie.load", {"path": str(MENU_MOVIE.resolve())})
    started = client.call("movie.startPlayback", {"load_start_state": True})
    current = _advance_movie(client, 3500, 0)
    default = _progress_snapshot(client)
    current = _advance_movie(client, 4300, current)
    native_load = _progress_snapshot(client)
    loaded_block = _read_memory(client, PROGRESS_BLOCK, PROGRESS_BLOCK_LENGTH)
    loaded_offsets = _find_offsets(card_before, loaded_block)
    if default["block_sha256"] == native_load["block_sha256"] or not loaded_offsets:
        raise SystemExit("native card load did not restore a serialized progress block")

    current = _advance_movie(client, 4750, current)
    before_mutation = _progress_snapshot(client)
    grain_write = client.call("debugger.writeU8", {
        "address": f"0x{GRAIN:08X}", "value": 37})
    progress_write = client.call("debugger.writeU8", {
        "address": f"0x{PROGRESS_BLOCK + PROGRESS_MUTATION_OFFSET:08X}",
        "value": 0x5A})
    mutated = _progress_snapshot(client)
    mutated_block = _read_memory(client, PROGRESS_BLOCK, PROGRESS_BLOCK_LENGTH)
    current = _advance_movie(client, 5000, current)
    at_save_dispatch = _progress_snapshot(client)
    _advance_movie(client, 5250, current)
    after_save = _progress_snapshot(client)
    status = client.call("movie.status", {})
    card_after = card.read_bytes()
    saved_offsets = _find_offsets(card_after, mutated_block)
    _movie_cleanup(client)

    if started.get("reproducible") is not True or \
            status.get("reproducible") is not True or \
            status.get("truncated") is not False or \
            before_mutation["controlled_byte"] != 100 or \
            mutated["grain"] != 37 or mutated["controlled_byte"] != 0x5A or \
            card_after == card_before or not saved_offsets or \
            _sha256_bytes(seed.read_bytes()) != repro["seed_sha256"]:
        raise SystemExit("native card save/load classification failed")
    repro["isolated_card_final_sha256"] = _sha256_bytes(card_after)
    repro["seed_final_sha256"] = _sha256_bytes(seed.read_bytes())
    return {
        "fixture": fixture, "repro_config": repro,
        "load": loaded, "started": started,
        "default_before_native_load": default,
        "native_load": {
            "after": native_load,
            "serialized_block_card_offsets": loaded_offsets,
            "classification": (
                "native frontend load replaced initialized resident state with "
                "an exact card-resident 336-byte progress block"),
        },
        "causal_mutation": {
            "grain_hud_mirror": {
                "address": f"0x{GRAIN:08X}", "before": before_mutation["grain"],
                "after": 37, "write": grain_write,
                "result": "outside the native serialized source range"},
            "resident_progress_byte": {
                "address":
                    f"0x{PROGRESS_BLOCK + PROGRESS_MUTATION_OFFSET:08X}",
                "offset": PROGRESS_MUTATION_OFFSET,
                "before": before_mutation["controlled_byte"], "after": 0x5A,
                "write": progress_write},
            "after": mutated,
        },
        "native_save": {
            "at_dispatch": at_save_dispatch, "after_flush": after_save,
            "serialized_block_sha256": _sha256_bytes(mutated_block),
            "serialized_block_card_offsets": saved_offsets,
            "card_before_sha256": _sha256_bytes(card_before),
            "card_after_sha256": _sha256_bytes(card_after),
            "diff": _card_diff(card_before, card_after),
            "classification": (
                "native frontend save copied the exact controlled resident "
                "progress block into a card file; no card bytes are retained"),
        },
        "failed_hypothesis": (
            "0x800A65A1 is a live HUD/objective mirror, not a direct card field; "
            "the native copy range instead owns persistent scene/pickup records"),
        "gate_persistence_law": (
            "Tunnels and City gate words are Region-A transient state and are "
            "not serialized. Scene setup initializes its gate shape; current "
            "progress regenerates grain, and threshold plus proximity/update "
            "can open the gate again."),
        "status": status,
    }


def _live_code_census(client: Any) -> dict[str, Any]:
    # A pinned Tunnels save owns this exact overlay image even though the staged
    # extraction differs.  Retain hashes and decisive words, never raw bytes.
    tunnels = _read_memory(client, TUNNELS_CODE[0],
                           TUNNELS_CODE[1] - TUNNELS_CODE[0])
    words = {}
    for name, (address, expected) in TUNNELS_WORDS.items():
        actual = _word(tunnels, address - TUNNELS_CODE[0])
        if actual != expected:
            raise SystemExit(f"live Tunnels gate word drifted at 0x{address:08X}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    table = _tunnels_table(client)
    if [[row[key] for key in ("state", "id", "threshold", "x", "z")]
            for row in table] != EXPECTED_TUNNELS_TABLE:
        raise SystemExit("live Tunnels nine-gate table drifted")
    return {
        "tunnels_function": {
            "start": f"0x{TUNNELS_CODE[0]:08X}",
            "end_exclusive": f"0x{TUNNELS_CODE[1]:08X}",
            "sha256": _sha256_bytes(tunnels), "words": words,
            "provenance": "hash-pinned pristine save-state overlay; staged overlay differs",
        },
        "tunnels_initial_table": table,
    }


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixtures = build_fixture_census()
    static = build_static_census()
    if static_census_gaps(static):
        raise SystemExit(f"static E09 census failed: {static_census_gaps(static)}")
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.writeU8", "debugger.writeU16",
        "debugger.writeU32", "emulator.getMediaInfo",
        "emulator.getStateInfo", "emulator.loadState",
        "emulator.clearControllerState", "emulator.advanceFrames",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks E09 methods: {missing}")
    card_persistence = _run_card_persistence(
        client, args, fixtures["shared_card_movie"])
    inspections = [inspect_state_before_load(
        client, ROOT / row["save"]["path"], media_identity)
        for row in fixtures["movies"]]

    # Load the first Tunnels anchor before hashing its save-owned overlay/table.
    first_save = ROOT / fixtures["movies"][0]["save"]["path"]
    client.call("emulator.loadState", {"path": str(first_save.resolve()),
                                       "pause_after_load": True,
                                       "validate_disc": True,
                                       "auto_select_disc": False})
    live_code = _live_code_census(client)
    replays = [_run_movie(client, row) for row in fixtures["movies"]]
    city_controls = [_run_city_threshold_control(client, fixtures["movies"][9 + i], i)
                     for i in range(3)]
    tunnels_precondition = _run_movie(client, fixtures["movies"][0])
    tunnels_lifecycle = _run_successful_open_respawn(
        client, "tunnels", {
            "fixture": tunnels_precondition["fixture"],
            "before": tunnels_precondition["before"],
            "after": tunnels_precondition["after"],
            "status": tunnels_precondition["status"],
            "kind": "natural pristine successful-open replay",
        })
    city_precondition = _run_city_threshold_control(client, fixtures["movies"][9], 0)
    city_lifecycle = _run_successful_open_respawn(
        client, "city", {
            "fixture": city_precondition["fixture"],
            "before": city_precondition["before"],
            "after": city_precondition["after"],
            "status": city_precondition["status"],
            "kind": "grain-only causal successful-open control",
        })
    final_media = verified_media_identity(client, client.call("debugger.status", {}))

    provenance = finish_run(
        args, generator="tools/phase4_grain_gates.py",
        anchor={
            "type": "completed E09 natural, causal, lifecycle and native-card campaign",
            "saves": [row["save"]["path"] for row in fixtures["movies"]],
            "fixture_sha256": {row["save"]["path"]: row["save"]["sha256"]
                                for row in fixtures["movies"]},
            "state_inspections": inspections,
            "card_fixture": fixtures["shared_card_movie"],
            "media_identity": media_identity,
            "final_media_identity": final_media,
        },
        timing={"cpu_overclock_percent": 100, "cd_read_speedup": 1,
                "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
                "movie_end_rule": (
                    "natural E09 replays consume every frame; native-card "
                    "classification stops after the frame-5250 save flush")})
    document = {
        "_comment": "Completed Phase-4 E09 evidence. Every external byte is centrally pinned; natural, causal, lifecycle and native-card branches remain explicitly separated.",
        "generated": date.today().isoformat(), "campaign_state": "completed",
        "fixture_census": fixtures, "static_census": static,
        "live_code_census": live_code,
        "live": {"card_persistence": card_persistence,
                 "natural_replays": replays,
                 "city_threshold_controls": city_controls,
                 "successful_open_death_respawn": {
                     "tunnels": tunnels_lifecycle,
                     "city": city_lifecycle}},
        "excluded_instrumentation": {
            "method": "accessLog watch on grain during LEVEL07 gate01 replay",
            "reason": "interpreter watch changed the final PC and RAM hash; it is not cycle/state-neutral and is excluded from behavioral predicates",
            "control_ram_sha256": "f73dc538be654ec7ce919eec2c6d9773472b6564b3ca888dfc6a8c082861c2e4",
            "instrumented_final_pc": "0x800106C0",
            "retained_lead": "76 reads at 0x800B3E04; statically corroborated by the pinned LEVEL04 overlay",
        },
        "bounded_residuals": {
            "tunnels_static_provenance": {
                "intersects_behavior": False,
                "boundary": "The checked-out staged Tunnels overlay differs from the centrally pinned save-owned image.",
                "rule": "Retain the live bounded hash/words; do not claim a staged byte match until a hash-verified retail extraction produces that exact image.",
            },
        },
        "run_provenance": provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[grain-gates] retained completed E09 evidence: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    parser.add_argument("--card-seed", type=Path, required=True,
                        help="centrally pinned replay memory-card seed")
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_grain_gates.py",
                       anchor={"type": "aborted before retained E09 evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned E09 instance cleanup also failed: {cleanup_error}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
