#!/usr/bin/env python3
"""Regenerate the active Phase-4 C16 lives/game-over/Continue campaign.

The operator recording is never treated as authority by filename.  This tool
verifies its central pins and load-free save metadata, replays it on mounted
hash-verified pristine media, and derives three transient counterfactuals:

* the last Start burst is removed to isolate the Continue transition;
* every pre-death movement sample is neutralized to prove the contact trigger;
* only the starting lives byte is changed from zero to one to select ordinary
  respawn instead of final-life game over.

No movie or save bytes produced by those controls are retained in Git.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
from typing import Any

try:
    from build_identity import verify_staged_input
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_lives_gameover
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_lives_gameover.json"
MOVIE_REL = "movies/Phase4/C16_gameover_continue.movie.json"
SAVE_REL = "movies/Phase4/C16_gameover_continue.movie.sav"
MOVIE = ROOT / MOVIE_REL
SAVE = ROOT / SAVE_REL
EXE_REL = "SCUS_942.88"
EXE = ROOT / "REBUILD/files" / EXE_REL
EXE_LOAD = 0x80010000
EXE_HEADER = 0x800

FINAL_FRAME = 4006
DEATH_SAMPLE_FRAME = 400
CONTINUE_PRE_FRAME = 3662
CONTINUE_POST_FRAME = 3700
CONTINUE_START_FRAMES = tuple(range(3663, 3670))
PRE_DEATH_MOVEMENT_FRAMES = tuple(range(40, 122))

SCENE = 0x80082504
MASTER_STATE = 0x800823A0
FADE_TIMER = 0x80082470
HEALTH = 0x800A6594
LIVES = 0x800A65A0

FIELDS: dict[str, tuple[int, str]] = {
    "scene": (SCENE, "u32"),
    "master_state": (MASTER_STATE, "u16"),
    "fade_timer": (FADE_TIMER, "s16"),
    "health": (HEALTH, "s16"),
    "lives": (LIVES, "u8"),
}
WIDTHS = {"u8": (1, "B"), "u16": (2, "H"), "s16": (2, "h"),
          "u32": (4, "I"), "s32": (4, "i")}

STATIC_REGIONS = {
    "damage_and_death_initiator": (0x8004A700, 0x8004AA34),
    "scene_flow_dispatcher": (0x8004FCA0, 0x800502C4),
    "scene_config_apply": (0x80055538, 0x80055648),
    "respawn_transition_state_handler": (0x8005B12C, 0x8005B440),
    "gameplay_state_reset_cursor_seed": (0x8005B714, 0x8005B7EC),
}
STATIC_WORDS = {
    "fatal_health_write": (0x8004A888, 0xA4236594),
    "final_life_reader": (0x800500BC, 0x904265A0),
    "final_life_branch": (0x800500C4, 0x1440000B),
    "game_over_movie_selector": (0x800500D4, 0x2404002E),
    "ordinary_respawn_call": (0x800500F4, 0x0C016C4B),
    "respawn_health_restore": (0x8005B30C, 0xA4226594),
    "respawn_lives_decrement": (0x8005B348, 0xA02665A0),
    "continue_scene_config_lives_write": (0x80055550, 0xA02265A0),
}

DAMAGE_RANGE = {
    "start": "0x8004A700", "end": "0x8004AA34",
    "label": "damage_and_death_initiator", "max_pcs": 2048,
}
SCENE_FLOW_RANGE = {
    "start": "0x8004FCA0", "end": "0x800502C4",
    "label": "scene_flow_dispatcher", "max_pcs": 4096,
}
RESPAWN_RANGE = {
    "start": "0x8005B12C", "end": "0x8005B440",
    "label": "respawn_transition_state_handler", "max_pcs": 2048,
}
SCENE_CONFIG_RANGE = {
    "start": "0x80055538", "end": "0x80055644",
    "label": "scene_config_apply", "max_pcs": 1024,
}

EXPECTED_SEGMENTS = [
    {"first": 0, "last": 39, "input": {}},
    {"first": 40, "last": 69, "input": {"down": True, "right": True}},
    {"first": 70, "last": 109, "input": {"right": True}},
    {"first": 110, "last": 118, "input": {"down": True, "right": True}},
    {"first": 119, "last": 121, "input": {"right": True}},
    {"first": 122, "last": 2585, "input": {}},
    {"first": 2586, "last": 2595, "input": {"start": True}},
    {"first": 2596, "last": 3009, "input": {}},
    {"first": 3010, "last": 3017, "input": {"start": True}},
    {"first": 3018, "last": 3361, "input": {}},
    {"first": 3362, "last": 3365, "input": {"start": True}},
    {"first": 3366, "last": 3662, "input": {}},
    {"first": 3663, "last": 3669, "input": {"start": True}},
    {"first": 3670, "last": 4005, "input": {}},
]

EXPECTED_SIGNATURES = {
    "continue_pre": {
        "ram_sha256": "1f9d550e6ff8dfe24c5975aee7ab3d5217949392ca338feaebcb64a00da67166",
        "registers_sha256": "bdb08aa76ba80422b3d1989cf11e1959478f5ba7d0e1d00f2d9feebd27e20a2f",
        "cycle": 152236326375, "frame": 268873, "movie_frame": 3662,
        "pc": "0x8003f334", "sp": "0x801fff58",
    },
    "continue_natural_post": {
        "ram_sha256": "7eb6b6386c492c839fd7ccc981527c3fa40c669b0cd63620d7794251e6fb96cd",
        "registers_sha256": "9654bfa43bfb4ddb1fa32a828382d491e7e28ddc71c7293f03ad69eb7ab972ac",
        "cycle": 152257842119, "frame": 268911, "movie_frame": 3700,
        "pc": "0xbfc02bac", "sp": "0x801ffed8",
    },
    "continue_removed_post": {
        "ram_sha256": "414a0966f9cc352ee4bc0e8c8ff86deed5251d5e315691b7291f14163a40fb60",
        "registers_sha256": "e944e3a1b67e0f1f8e53e48a3fbb4125f2f384122a2389dfc2eb4bef3d4185b8",
        "cycle": 152257842118, "frame": 268911, "movie_frame": 3700,
        "pc": "0x8003f334", "sp": "0x801fff58",
    },
    "final_life_death": {
        "ram_sha256": "d994b8530999a3c194df433721450573fc70953c9fafbb17222d3e123928ecef",
        "registers_sha256": "25763a2e720bde74582f921c5e171d55ac36941b9983d1d85ba9354fdf5cecc2",
        "cycle": 150389369660, "frame": 265611, "movie_frame": 400,
        "pc": "0x80065210", "sp": "0x801ffda0",
    },
    "neutral_no_death": {
        "ram_sha256": "8de6c37b5a9dbbcb4b8f8d90404208418780f28c1d31995276a5e65246075578",
        "registers_sha256": "c85d3dfcce67302d035ecfca51403529d22e5b499cdc40415444fca293b391f2",
        "cycle": 150389369660, "frame": 265611, "movie_frame": 400,
        "pc": "0x8004fea4", "sp": "0x801fffd0",
    },
    "ordinary_respawn": {
        "ram_sha256": "f7d0dd15172dea1528dec205a4d26aeb98f0cc449cd315970af9dc1959400e57",
        "registers_sha256": "6ec0b0d3ba6fdae7f864a7b63c5036d0f23860d5f80c0f78125514aeba6fd935",
        "cycle": 150389369661, "frame": 265611, "movie_frame": 400,
        "pc": "0x800135a8", "sp": "0x801ffe60",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _method_present(capabilities: dict[str, Any], method: str) -> bool:
    return any((row.get("name") if isinstance(row, dict) else row) == method
               for row in capabilities.get("methods") or [])


def _exe_slice(exe: bytes, start: int, end: int) -> bytes:
    lo = EXE_HEADER + start - EXE_LOAD
    hi = EXE_HEADER + end - EXE_LOAD
    if lo < EXE_HEADER or hi > len(exe) or hi <= lo:
        raise SystemExit(f"invalid executable range 0x{start:08X}..0x{end:08X}")
    return exe[lo:hi]


def _exe_word(exe: bytes, address: int) -> int:
    return struct.unpack("<I", _exe_slice(exe, address, address + 4))[0]


def build_static_census() -> dict[str, Any]:
    exe = EXE.read_bytes()
    verify_staged_input(EXE_REL, exe)
    regions = {
        name: {
            "start": f"0x{start:08X}", "end": f"0x{end:08X}",
            "size": end - start,
            "file_offset": f"0x{EXE_HEADER + start - EXE_LOAD:X}",
            "sha256": _sha256_bytes(_exe_slice(exe, start, end)),
        }
        for name, (start, end) in STATIC_REGIONS.items()
    }
    words = {}
    for name, (address, expected) in STATIC_WORDS.items():
        actual = _exe_word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"C16 static word drifted at 0x{address:08X}: "
                f"0x{actual:08X} != 0x{expected:08X}")
        words[name] = {
            "address": f"0x{address:08X}",
            "file_offset": f"0x{EXE_HEADER + address - EXE_LOAD:X}",
            "instruction_word": f"0x{actual:08X}",
        }
    return {
        "resident_executable": {
            "path": f"REBUILD/files/{EXE_REL}", "sha256": _sha256(EXE),
            "size": EXE.stat().st_size,
        },
        "regions": regions,
        "instructions": words,
        "typed_state": {
            name: {"address": f"0x{address:08X}", "width": width,
                   "residency": "resident"}
            for name, (address, width) in FIELDS.items()
        },
        "source_status": {
            "scene_config_apply": (
                "matching C exists at src/main/80055538_scene_config_apply.c; "
                "the retained executable slice and exact lives store are authority"),
            "other_regions": (
                "exact resident assembly transcriptions are hashed as source "
                "dependencies; semantic names do not replace executable bytes"),
        },
    }


def _pad_signature(pad: dict[str, Any]) -> dict[str, Any]:
    axes = {"lx", "ly", "rx", "ry"}
    result = {key: value for key, value in pad.items()
              if key not in axes and bool(value)}
    result.update({key: value for key, value in pad.items()
                   if key in axes and value != 128})
    return dict(sorted(result.items()))


def _input_segments(movie: dict[str, Any]) -> list[dict[str, Any]]:
    frames = movie.get("frames") or []
    if not frames:
        return []
    rows = []
    first = 0
    signature = _pad_signature((frames[0].get("ports") or {}).get("0") or {})
    for index, row in enumerate(frames[1:], 1):
        current = _pad_signature((row.get("ports") or {}).get("0") or {})
        if current != signature:
            rows.append({"first": first, "last": index - 1, "input": signature})
            first, signature = index, current
    rows.append({"first": first, "last": len(frames) - 1, "input": signature})
    return rows


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    movie_pin = entries.get(MOVIE_REL)
    save = verify_declared_save_fixture(SAVE, allowed_media_classes={"pristine"})
    if not isinstance(movie_pin, dict) or \
            movie_pin.get("media_class") != "pristine_serial" or \
            movie_pin.get("sha256") != _sha256(MOVIE) or \
            movie_pin.get("size") != MOVIE.stat().st_size:
        raise SystemExit("C16 movie central pin drifted")
    movie = json.loads(MOVIE.read_text())
    start = movie.get("start_state") or {}
    segments = _input_segments(movie)
    if movie.get("version") != 3 or movie.get("game_serial") != "SCUS-94288" or \
            len(movie.get("frames") or []) != FINAL_FRAME or \
            start.get("game_serial") != "SCUS-94288" or \
            start.get("from_boot") is not False or \
            start.get("reproducible_only_from_state") is not True or \
            start.get("file_size") != save["size"] or segments != EXPECTED_SEGMENTS:
        raise SystemExit("C16 movie metadata or exact input segments drifted")
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "movie": {
            "path": MOVIE_REL, "sha256": movie_pin["sha256"],
            "size": movie_pin["size"], "media_class": movie_pin["media_class"],
            "version": movie["version"], "frames": len(movie["frames"]),
            "initial_frame": movie.get("initial_frame"),
            "input_segments": segments,
        },
        "save": save,
        "declared_start_state": {
            "frame": start.get("frame"), "pc": start.get("pc"),
            "sp": start.get("sp"), "game_serial": start.get("game_serial"),
            "from_boot": start.get("from_boot"),
            "reproducible_only_from_state": start.get("reproducible_only_from_state"),
        },
        "classification_boundary": (
            "The filename is only a lead. Central byte pins, load-free save "
            "inspection, pristine mounted-media verification, natural replay, "
            "and three single-variable controls establish the retained result."),
    }


def _canonical_movie_hash(movie: dict[str, Any], anchor: str) -> str:
    canonical = json.loads(json.dumps(movie))
    (canonical.get("start_state") or {})["path"] = anchor
    return _sha256_bytes(json.dumps(
        canonical, sort_keys=True, separators=(",", ":")).encode())


def _write_variant(
        source: dict[str, Any], path: Path, *, start_state: Path,
        anchor_label: str, edit: str | None = None) -> dict[str, Any]:
    movie = json.loads(json.dumps(source))
    movie["start_state"]["path"] = str(start_state.resolve())
    movie["start_state"]["file_size"] = start_state.stat().st_size
    changed = []
    if edit == "continue_removed":
        for frame in CONTINUE_START_FRAMES:
            pad = movie["frames"][frame]["ports"]["0"]
            if pad.get("start") is not True:
                raise SystemExit(f"C16 Continue source frame {frame} is not Start")
            pad["start"] = False
            changed.append(frame)
    elif edit == "pre_death_neutral":
        for frame in PRE_DEATH_MOVEMENT_FRAMES:
            pad = movie["frames"][frame]["ports"]["0"]
            if not _pad_signature(pad):
                raise SystemExit(f"C16 movement source frame {frame} is neutral")
            movie["frames"][frame]["ports"]["0"] = {}
            changed.append(frame)
    elif edit is not None:
        raise SystemExit(f"unknown C16 movie edit: {edit}")
    path.write_text(json.dumps(movie, separators=(",", ":")) + "\n")
    return {
        "source_sha256": _sha256(MOVIE),
        "semantic_sha256": _canonical_movie_hash(movie, anchor_label),
        "source_frame_count": len(source["frames"]),
        "derived_frame_count": len(movie["frames"]),
        "changed_frames": changed,
        "changed_field": {
            None: "start_state host path normalized to centrally pinned save",
            "continue_removed": "ports.0.start true -> false",
            "pre_death_neutral": "pre-death movement port -> neutral",
        }[edit],
        "anchor": anchor_label,
        "transient_storage": "temporary directory; derivative deleted before retention",
    }


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    data = bytes.fromhex(row["hex"])
    if len(data) != length:
        raise SystemExit(f"short debugger read at 0x{address:08X}")
    return data


def _read_main_ram(client: Any) -> bytes:
    return b"".join(_read_memory(client, 0x80000000 + offset, 0x10000)
                    for offset in range(0, 0x200000, 0x10000))


def _snapshot(client: Any) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    typed = {}
    for name, (address, width) in FIELDS.items():
        size, fmt = WIDTHS[width]
        typed[name] = struct.unpack("<" + fmt, _read_memory(client, address, size))[0]
    return {
        "status": {key: status.get(key) for key in
                   ("pc", "sp", "frame", "cycle", "paused", "game_serial")},
        "typed": typed,
    }


def _compact_trace(trace: dict[str, Any]) -> dict[str, Any]:
    coverage = []
    for row in trace.get("coverage") or []:
        data = row.get("coverage") or {}
        pcs = data.get("pcs") or []
        coverage.append({
            "label": row.get("label"), "range": row.get("range"),
            "total_hits": data.get("total_hits"),
            "distinct_pc_count": data.get("distinct_pc_count"),
            "truncated": data.get("truncated", False),
            "pcs": pcs,
            "pcs_sha256": _sha256_bytes(
                json.dumps(pcs, separators=(",", ":")).encode()),
        })
    return {
        key: trace.get(key) for key in (
            "target_frame", "trace_mode", "configured_execution_mode",
            "comparison_execution_mode", "control", "instrumented", "comparison")
    } | {"coverage": coverage}


def _trace_snapshot(client: Any, path: Path, frame: int,
                    trace_range: dict[str, Any]) -> dict[str, Any]:
    trace = _compact_trace(client.call("movie.traceToFrame", {
        "path": str(path.resolve()), "frame": frame, "ranges": [trace_range]},
        timeout=900))
    if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row["truncated"] for row in trace["coverage"]):
        raise SystemExit(f"C16 trace is not cycle-neutral at movie frame {frame}")
    movie = client.call("movie.status", {})
    return {
        "movie_frame": frame,
        "movie_status": {key: movie.get(key) for key in
                         ("reproducible", "truncated", "frame_count",
                          "playback_index", "playing")},
        "snapshot": _snapshot(client), "cycle_neutral_trace": trace,
    }


def _replay_final(client: Any, path: Path) -> dict[str, Any]:
    client.call("movie.stopPlayback", {})
    client.call("movie.load", {"path": str(path.resolve())})
    started = client.call("movie.startPlayback", {
        "start_frame": 0, "load_start_state": True})
    client.call("movie.advanceToFrame", {"frame": FINAL_FRAME,
                                         "max_frames": FINAL_FRAME + 1})
    status = client.call("movie.status", {})
    if started.get("reproducible") is not True or \
            status.get("reproducible") is not True or status.get("truncated") is not False:
        raise SystemExit("C16 final replay lost reproducibility")
    return {
        "movie_frame": FINAL_FRAME,
        "movie_status": {key: status.get(key) for key in
                         ("reproducible", "truncated", "frame_count",
                          "playback_index", "playing")},
        "snapshot": _snapshot(client),
    }


def _create_lives_one_state(client: Any, path: Path,
                            media_identity: dict[str, Any]) -> dict[str, Any]:
    client.call("emulator.loadState", {
        "path": str(SAVE.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False})
    verified_media_identity(client, client.call("debugger.status", {}))
    before = _read_main_ram(client)
    if before[LIVES - 0x80000000] != 0:
        raise SystemExit("C16 fixture no longer starts on the final playable life")
    written = client.call("debugger.writeU8", {
        "address": f"0x{LIVES:08X}", "value": 1})
    after = _read_main_ram(client)
    differences = [index for index, (left, right) in enumerate(zip(before, after))
                   if left != right]
    if differences != [LIVES - 0x80000000] or \
            written.get("written") not in (1, True):
        raise SystemExit(f"C16 lives-one state mutated unexpected RAM: {differences[:16]}")
    saved = client.call("emulator.saveState", {"path": str(path.resolve())})
    info = client.call("emulator.getStateInfo", {"path": str(path.resolve())})
    if saved.get("saved") is not True or info.get("valid") is not True or \
            info.get("serial") != media_identity.get("game_serial") or \
            Path(info.get("media_path") or "").resolve() != \
            Path(media_identity["game_path"]).resolve():
        raise SystemExit(f"C16 transient lives-one state inspection failed: {saved} / {info}")
    return {
        "source_fixture": SAVE_REL,
        "source_sha256": _sha256(SAVE),
        "derived_sha256": _sha256(path), "derived_size": path.stat().st_size,
        "derived_state_version": info.get("version"),
        "derived_serial": info.get("serial"),
        "mutation": {
            "address": f"0x{LIVES:08X}", "width": "u8",
            "before": 0, "after": 1,
            "main_ram_difference_count": 1,
            "main_ram_difference_addresses": [f"0x{LIVES:08X}"],
            "source_main_ram_sha256": _sha256_bytes(before),
            "derived_main_ram_sha256": _sha256_bytes(after),
        },
        "transient_storage": "temporary directory; derivative deleted before retention",
    }


def _access_events(client: Any, *, movie: Path, start_frame: int,
                   run_frames: int, watches: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    try:
        client.call("movie.stopPlayback", {})
    except Exception:
        pass
    client.call("accessLog.clear", {})
    client.call("movie.load", {"path": str(movie.resolve())})
    client.call("movie.startPlayback", {"start_frame": 0, "load_start_state": True})
    if start_frame:
        client.call("movie.advanceToFrame", {"frame": start_frame,
                                             "max_frames": start_frame + 1})
    watch_rows = [client.call("accessLog.addWatch", row) for row in watches]
    run = client.call("accessLog.run", {"frames": run_frames})
    events = client.call("accessLog.get", {"offset": 0, "limit": 512})
    client.call("accessLog.clear", {})
    return {
        "execution_mode_boundary": (
            "accessLog forces the interpreter; event PCs/words/old/new values "
            "are writer attribution only, while fixed-frame behavior comes from "
            "the separate cycle-neutral cached-interpreter traces"),
        "start_movie_frame": start_frame, "frames_run": run_frames,
        "watches": watch_rows,
        "events": events.get("events") or [],
        "total": events.get("total"), "truncated": events.get("truncated"),
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
        "final_snapshot": _snapshot(client),
    }


def _trace_signature_gaps(row: dict[str, Any], label: str) -> list[str]:
    gaps = []
    trace = row.get("cycle_neutral_trace") or {}
    control = trace.get("control") or {}
    instrumented = trace.get("instrumented") or {}
    keys = ("ram_sha256", "registers_sha256", "cycle", "frame",
            "movie_frame", "pc", "sp")
    unequal = [key for key in keys if control.get(key) != instrumented.get(key)]
    if unequal or (trace.get("comparison") or {}).get("cycle_neutral") is not True:
        gaps.append(f"{label} control/instrumented signatures diverged: {unequal}")
    if any(item.get("truncated") for item in trace.get("coverage") or []):
        gaps.append(f"{label} coverage truncated")
    return gaps


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps = []
    if document.get("campaign_state") != "active_partial":
        gaps.append("C16 campaign state is not active_partial")
    live = document.get("live") or {}
    final_life = live.get("final_life_game_over") or {}
    neutral = live.get("neutral_input_no_death") or {}
    ordinary = live.get("one_life_ordinary_respawn") or {}
    continued = live.get("continue_transition") or {}
    traced = {
        "final_life_damage": final_life.get("damage_trace") or {},
        "final_life_scene_flow": final_life.get("scene_flow_trace") or {},
        "neutral": neutral.get("damage_trace") or {},
        "ordinary": ordinary.get("respawn_trace") or {},
        "continue_pre_natural": continued.get("natural_pre") or {},
        "continue_pre_removed": continued.get("removed_pre") or {},
        "continue_post_natural": continued.get("natural_post") or {},
        "continue_post_removed": continued.get("removed_post") or {},
    }
    for label, row in traced.items():
        gaps.extend(_trace_signature_gaps(row, label))

    controls = {label: (row.get("cycle_neutral_trace") or {}).get("control") or {}
                for label, row in traced.items()}
    expected_for = {
        "final_life_damage": "final_life_death",
        "neutral": "neutral_no_death", "ordinary": "ordinary_respawn",
        "continue_pre_natural": "continue_pre",
        "continue_pre_removed": "continue_pre",
        "continue_post_natural": "continue_natural_post",
        "continue_post_removed": "continue_removed_post",
    }
    for label, expected_name in expected_for.items():
        if controls[label] != EXPECTED_SIGNATURES[expected_name]:
            gaps.append(f"{label} retained control signature changed")
    if controls["final_life_scene_flow"] != EXPECTED_SIGNATURES["final_life_death"]:
        gaps.append("final-life damage/scene-flow controls diverged")

    typed = lambda row: ((row.get("snapshot") or {}).get("typed") or {})
    if typed(traced["final_life_damage"]) != {
            "scene": 9, "master_state": 2, "fade_timer": 0,
            "health": -1, "lives": 0}:
        gaps.append("natural final-life death state changed")
    if typed(traced["neutral"]) != {
            "scene": 9, "master_state": 0, "fade_timer": 0,
            "health": 1, "lives": 0}:
        gaps.append("neutral no-death state changed")
    if typed(traced["ordinary"]) != {
            "scene": 9, "master_state": 0, "fade_timer": 22,
            "health": 4, "lives": 0}:
        gaps.append("one-life ordinary respawn state changed")
    natural_post = typed(traced["continue_post_natural"])
    removed_post = typed(traced["continue_post_removed"])
    if natural_post.get("scene") != 0 or natural_post.get("lives") != 5 or \
            removed_post.get("scene") != 0 or removed_post.get("lives") != 0:
        gaps.append("Continue lives-reset divergence changed")
    if typed(traced["continue_pre_natural"]) != typed(traced["continue_pre_removed"]):
        gaps.append("Continue branches differ before the edited input")

    coverage = lambda row: ((row.get("cycle_neutral_trace") or {})
                            .get("coverage") or [{}])[0]
    natural_damage_pcs = set(coverage(traced["final_life_damage"]).get("pcs") or [])
    neutral_damage = coverage(traced["neutral"])
    scene_flow_pcs = set(coverage(traced["final_life_scene_flow"]).get("pcs") or [])
    respawn_pcs = set(coverage(traced["ordinary"]).get("pcs") or [])
    continue_pcs = set(coverage(traced["continue_post_natural"]).get("pcs") or [])
    removed_pcs = set(coverage(traced["continue_post_removed"]).get("pcs") or [])
    if "0x8004a888" not in natural_damage_pcs or \
            neutral_damage.get("total_hits") != 0:
        gaps.append("damage positive/neutral coverage boundary changed")
    if not {"0x800500bc", "0x800500d4"}.issubset(scene_flow_pcs) or \
            "0x800500f4" in scene_flow_pcs:
        gaps.append("final-life game-over scene-flow branch changed")
    if not {"0x8005b30c", "0x8005b348"}.issubset(respawn_pcs):
        gaps.append("ordinary respawn writer coverage changed")
    if "0x80055550" not in continue_pcs or "0x80055550" in removed_pcs:
        gaps.append("Continue scene-config writer coverage changed")

    natural_final = typed(continued.get("natural_final") or {})
    removed_final = typed(continued.get("removed_final") or {})
    if natural_final.get("lives") != 5 or removed_final.get("lives") != 0 or \
            natural_final.get("scene") != 0 or removed_final.get("scene") != 0:
        gaps.append("Continue final persistence boundary changed")

    continue_events = (continued.get("writer_attribution") or {}).get("events") or []
    continue_writes = [(row.get("instruction_pc"), row.get("instruction_word"),
                        row.get("value"), row.get("new_value"))
                       for row in continue_events]
    if continue_writes != [("0x80055550", "0xa02265a0", 0, 5)]:
        gaps.append("Continue lives writer attribution changed")
    ordinary_events = (ordinary.get("writer_attribution") or {}).get("events") or []
    ordinary_writes = [(row.get("instruction_pc"), row.get("instruction_word"),
                        row.get("value"), row.get("new_value"))
                       for row in ordinary_events]
    if ordinary_writes != [
            ("0x8004a888", "0xa4236594", 0, 65535),
            ("0x8005b30c", "0xa4226594", 65535, 4),
            ("0x8005b348", "0xa02665a0", 1, 0)]:
        gaps.append("ordinary death/respawn writer attribution changed")
    if (continued.get("writer_attribution") or {}).get("truncated") is not False or \
            (ordinary.get("writer_attribution") or {}).get("truncated") is not False:
        gaps.append("writer attribution truncated")

    recipe = ordinary.get("state_recipe") or {}
    mutation = recipe.get("mutation") or {}
    if mutation.get("main_ram_difference_count") != 1 or \
            mutation.get("main_ram_difference_addresses") != ["0x800A65A0"] or \
            mutation.get("before") != 0 or mutation.get("after") != 1:
        gaps.append("one-life state mutation is not single-variable")
    if (neutral.get("movie_recipe") or {}).get("changed_frames") != \
            list(PRE_DEATH_MOVEMENT_FRAMES) or \
            (continued.get("removed_movie_recipe") or {}).get("changed_frames") != \
            list(CONTINUE_START_FRAMES):
        gaps.append("movie single-variable edit frontier changed")

    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned C16 live process was not stopped")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    fixtures = build_fixture_census()
    source_movie = json.loads(MOVIE.read_text())
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.readMemory",
        "debugger.writeU8", "debugger.pause", "emulator.getMediaInfo",
        "emulator.getStateInfo", "emulator.loadState", "emulator.saveState",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.traceToFrame", "movie.stopPlayback", "movie.status",
        "accessLog.addWatch", "accessLog.run", "accessLog.get", "accessLog.clear",
    }
    missing = sorted(method for method in required
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks C16 methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, SAVE, media_identity)

    with tempfile.TemporaryDirectory(prefix="abl-phase4-c16-") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        natural_path = temp_dir / "natural.movie.json"
        removed_path = temp_dir / "continue-removed.movie.json"
        neutral_path = temp_dir / "pre-death-neutral.movie.json"
        lives_one_state = temp_dir / "lives-one.sav"
        lives_one_movie = temp_dir / "lives-one.movie.json"

        natural_recipe = _write_variant(
            source_movie, natural_path, start_state=SAVE,
            anchor_label="<centrally-pinned-C16-save>")
        removed_recipe = _write_variant(
            source_movie, removed_path, start_state=SAVE,
            anchor_label="<centrally-pinned-C16-save>", edit="continue_removed")
        neutral_recipe = _write_variant(
            source_movie, neutral_path, start_state=SAVE,
            anchor_label="<centrally-pinned-C16-save>", edit="pre_death_neutral")
        lives_one_recipe = _create_lives_one_state(
            client, lives_one_state, media_identity)
        lives_one_movie_recipe = _write_variant(
            source_movie, lives_one_movie, start_state=lives_one_state,
            anchor_label="<transient-one-byte-lives-state>")

        # Discard the first coverage request, which transitions a newly launched
        # recompiler instance to the cached-interpreter coverage backend.
        warmup = _trace_snapshot(client, natural_path, 0, DAMAGE_RANGE)

        final_life_damage = _trace_snapshot(
            client, natural_path, DEATH_SAMPLE_FRAME, DAMAGE_RANGE)
        final_life_scene_flow = _trace_snapshot(
            client, natural_path, DEATH_SAMPLE_FRAME, SCENE_FLOW_RANGE)
        neutral_no_death = _trace_snapshot(
            client, neutral_path, DEATH_SAMPLE_FRAME, DAMAGE_RANGE)
        ordinary_respawn = _trace_snapshot(
            client, lives_one_movie, DEATH_SAMPLE_FRAME, RESPAWN_RANGE)

        natural_pre = _trace_snapshot(
            client, natural_path, CONTINUE_PRE_FRAME, SCENE_CONFIG_RANGE)
        removed_pre = _trace_snapshot(
            client, removed_path, CONTINUE_PRE_FRAME, SCENE_CONFIG_RANGE)
        natural_post = _trace_snapshot(
            client, natural_path, CONTINUE_POST_FRAME, SCENE_CONFIG_RANGE)
        removed_post = _trace_snapshot(
            client, removed_path, CONTINUE_POST_FRAME, SCENE_CONFIG_RANGE)
        natural_final = _replay_final(client, natural_path)
        removed_final = _replay_final(client, removed_path)

        continue_writers = _access_events(
            client, movie=natural_path, start_frame=CONTINUE_PRE_FRAME,
            run_frames=40, watches=({
                "address": f"0x{LIVES:08X}", "length": 1, "type": "write",
                "label": "lives", "max_events": 64,
            },))
        ordinary_writers = _access_events(
            client, movie=lives_one_movie, start_frame=200, run_frames=500,
            watches=(
                {"address": f"0x{HEALTH:08X}", "length": 2, "type": "write",
                 "label": "health", "max_events": 128},
                {"address": f"0x{LIVES:08X}", "length": 1, "type": "write",
                 "label": "lives", "max_events": 128},
            ))
        final_media = verified_media_identity(
            client, client.call("debugger.status", {}))

        document = {
            "_comment": (
                "Active C16 evidence: pristine natural final-life game over, "
                "one-byte ordinary-respawn control, neutral no-death control, "
                "and fourth-Start Continue reset control. Checkpoints, remaining "
                "death classes, menu/save policy and stage breadth remain open."),
            "generated": date.today().isoformat(),
            "schema": "abl-phase4-lives-gameover/1",
            "campaign_state": "active_partial",
            "static_census": static, "fixture_census": fixtures,
            "live": {
                "discarded_execution_mode_warmup": warmup,
                "natural_movie_recipe": natural_recipe,
                "final_life_game_over": {
                    "damage_trace": final_life_damage,
                    "scene_flow_trace": final_life_scene_flow,
                },
                "neutral_input_no_death": {
                    "movie_recipe": neutral_recipe,
                    "damage_trace": neutral_no_death,
                },
                "one_life_ordinary_respawn": {
                    "state_recipe": lives_one_recipe,
                    "movie_recipe": lives_one_movie_recipe,
                    "respawn_trace": ordinary_respawn,
                    "writer_attribution": ordinary_writers,
                },
                "continue_transition": {
                    "removed_movie_recipe": removed_recipe,
                    "natural_pre": natural_pre, "removed_pre": removed_pre,
                    "natural_post": natural_post, "removed_post": removed_post,
                    "natural_final": natural_final, "removed_final": removed_final,
                    "writer_attribution": continue_writers,
                },
            },
            "bounded_interpretation": {
                "observation": (
                    "Natural movement reaches health -1 on lives 0 and selects "
                    "game-over flow. With only lives 0->1 at the same anchor it "
                    "restores health 4 and decrements lives to 0 in scene 9. "
                    "With only pre-death movement neutralized no damage occurs. "
                    "Natural fourth Start executes scene_config_apply and writes "
                    "lives 0->5; removing only that Start leaves lives 0."),
                "inference": (
                    "Lives zero is the final playable life; death then selects "
                    "game over, while ordinary death restores health and consumes "
                    "one stored life. Continue applies scene configuration whose "
                    "first byte supplies the five-life reset."),
                "causal_confirmation": (
                    "The controls alter exactly one RAM byte, 82 pre-death input "
                    "frames, or the seven fourth-Start samples. Fixed-frame traces "
                    "are RAM/register/cycle/frame neutral against their own "
                    "uninstrumented runs and exact writer PCs are byte-pinned."),
                "forbidden_claim": (
                    "This recording does not close checkpoint coupling, every "
                    "hazard/death class, Continue menu choice breadth, card-save "
                    "effects, stage breadth, or C15/E10/E14 ownership."),
            },
            "bounded_open_frontier": {
                "checkpoint_interaction": (
                    "C15 must reproduce mid-level checkpoint capture and death "
                    "restore before C16 can claim checkpoint coupling."),
                "death_classes": (
                    "Join representative pit, actor/contact and scripted hazard "
                    "deaths to the same scene-flow boundary without borrowing "
                    "enemy or hazard-family completion."),
                "menu_and_save": (
                    "Reproduce Continue versus alternate frontend choices and "
                    "join E14 native card serialization before claiming save policy."),
                "stage_breadth": (
                    "The dedicated natural game-over anchor is Bug Bar only; other "
                    "stage classes remain supporting Phase-2 breadth, not C16 closure."),
                "next_experiment": (
                    "Select an existing mid-level death recording that crosses an "
                    "authored checkpoint, then trace checkpoint capture, respawn "
                    "restore, and Continue/card boundaries separately."),
            },
            "source_dependencies": {
                path: _sha256(ROOT / path) for path in (
                    "asm/hand_written/8004a700_resident_level_transition_initiator.s",
                    "asm/hand_written/8004fca0_scene_flow_dispatcher.s",
                    "asm/hand_written/8005b134_respawn_transition_state_handler.s",
                    "asm/hand_written/8005b714_gameplay_state_reset_cursor_seed.s",
                    "src/main/80055538_scene_config_apply.c",
                )
            },
            "run_provenance": {},
        }
        gaps = evidence_gaps(document)
        if gaps:
            diagnostic = Path("/tmp/abl-phase4-c16-failed-evidence.json")
            diagnostic.write_text(json.dumps(document, indent=1) + "\n")
            raise SystemExit(f"retained C16 evidence failed: {gaps}")
        document["run_provenance"] = finish_run(
            args, generator="tools/phase4_lives_gameover.py",
            anchor={
                "type": (
                    "state-anchored pristine natural game over plus transient "
                    "one-byte lives, neutral-input and fourth-Start controls"),
                "save": SAVE_REL,
                "fixture_sha256": {SAVE_REL: fixtures["save"]["sha256"]},
                "state_inspections": [inspection],
                "media_identity": media_identity,
                "final_media_identity": final_media,
                "movie": fixtures["movie"],
                "transient_controls": {
                    "one_life_state": lives_one_recipe,
                    "neutral_input_movie": neutral_recipe,
                    "continue_removed_movie": removed_recipe,
                },
            },
            timing={
                "cpu_overclock_percent": 100, "cd_read_speedup": 1,
                "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
                "movie_frames": {
                    "death_sample": DEATH_SAMPLE_FRAME,
                    "continue_pre": CONTINUE_PRE_FRAME,
                    "continue_post": CONTINUE_POST_FRAME,
                    "final": FINAL_FRAME,
                },
                "coverage_control": (
                    "one discarded backend-transition warm-up, then "
                    "movie.traceToFrame uninstrumented versus passive cached-block "
                    "replay; accessLog runs are writer attribution only"),
            })
        cleanup_gaps = evidence_gaps(document)
        if cleanup_gaps:
            raise SystemExit(f"retained C16 cleanup evidence failed: {cleanup_gaps}")
        write_live_evidence(OUTPUT, document)
    print("[phase4-c16] retained final-life, ordinary-respawn, neutral, and Continue controls")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(
                args, generator="tools/phase4_lives_gameover.py",
                anchor={"type": "aborted before retained C16 evidence"}, timing={})
        except BaseException as cleanup_error:
            print(f"owned C16 cleanup also failed: {cleanup_error}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
