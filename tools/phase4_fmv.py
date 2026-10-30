#!/usr/bin/env python3
"""Regenerate the active Phase-4 E15 FMV playback/skip campaign.

Static evidence exhaustively binds the pristine FMV.BIN manifest and its
per-movie frame-count table.  Live evidence replays the existing operator FMV
skip movie from a load-free-inspected pristine state and compares it with a
single-variable derivative in which only the recorded Start hold is removed.
A separately pinned from-boot movie is transiently neutralized to reproduce
natural boot-logo/title/intro completion, Region-B reuse and frontend handoff.
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
    import fmv_frame_table
    from build_identity import verify_staged_input
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_fmv
    from tools import fmv_frame_table
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_fmv.json"
MOVIE_REL = "movies/Phase4/E15_fmv_skip.movie.json"
SAVE_REL = "movies/Phase4/E15_fmv_skip.movie.sav"
MOVIE = ROOT / MOVIE_REL
SAVE = ROOT / SAVE_REL
COLD_BOOT_MOVIE_REL = "movies/go_to_end/LEVEL01.movie.json"
COLD_BOOT_MOVIE = ROOT / COLD_BOOT_MOVIE_REL
FMV_REL = "FMV/FMV.BIN"
FMV_BIN = ROOT / "REBUILD/files" / FMV_REL
EXE_REL = "SCUS_942.88"
EXE = ROOT / "REBUILD/files" / EXE_REL
EXE_LOAD = 0x80010000
EXE_HEADER = 0x800

START_FRAMES = list(range(334, 343))
PRE_TRIGGER_FRAME = 333
POST_TRIGGER_FRAME = 343
FINAL_FRAME = 541

COLD_BOOT_WARMUP_FRAME = 1800
COLD_BOOT_POINTS = (
    ("dlogo_selected", 2000),
    ("dlogo_completed", 3000),
    ("title_reset", 3200),
    ("title_completed", 4600),
    ("intro_reset", 4800),
    ("intro_completed", 8400),
    ("overlay_retired", 8500),
    ("frontend_transition", 9400),
)

FMV_RUNNING_LATCH = 0x80082250
SCENE = 0x80082504
MASTER_STATE = 0x800823A0
SHELL_SUBSTATE = 0x8008243C
STR_BACKLOC = 0x80088FFC
FMV_COMPLETE = 0x800CAC10
FMV_TOTAL_FRAMES = 0x80131EEE
FMV_OVERLAY_HEAD_SHA256 = "ab33c20549aa18877259dbd83cc4925c9ea24db0e160b3f450eaad29551954db"

TRACE_RANGES = (
    {"start": "0x8003E7C0", "end": "0x8003F600",
     "label": "resident_fmv_load_and_wait", "max_pcs": 8192},
    {"start": "0x8004FA40", "end": "0x8005038C",
     "label": "resident_shell_and_completion", "max_pcs": 8192},
    {"start": "0x8006D8E8", "end": "0x80070B20",
     "label": "libcd_libpress_streaming", "max_pcs": 16384},
    {"start": "0x800B5788", "end": "0x80131F00",
     "label": "fmv_overlay", "max_pcs": 200000},
)

COLD_BOOT_TRACE_RANGES = TRACE_RANGES + (
    {"start": "0x800B6B00", "end": "0x800B6B60",
     "label": "fmv_completion_limit", "max_pcs": 256},
)

# Filled from a retained cycle-neutral cold-boot replay.  The exact signatures
# are intentionally source constants rather than accepting a generated
# comparison boolean as proof.
EXPECTED_COLD_BOOT_SIGNATURES: dict[str, dict[str, Any]] = {
    "dlogo_selected": {
        "ram_sha256": "5b03362fabf3d4abb94da01e41a87cb96ff8e33d8502344a55797a66132ea33d",
        "registers_sha256": "84077f2a3cb831d8e1c911ca518912e465e047d441e03c0fd4c04545c2a489a2",
        "frame": 2001, "cycle": 1132392482, "pc": "0x00001ea8",
        "sp": "0x801ff580", "movie_frame": 2000,
    },
    "dlogo_completed": {
        "ram_sha256": "2612e7d9655307eedcd25d28692ca62a5c681c2781d40336439794ad788ba651",
        "registers_sha256": "3b520ba581f636c14e9aabba410c81bb155c1a4994d71a80453a4a910f3adfa0",
        "frame": 3001, "cycle": 1698596257, "pc": "0x8006e568",
        "sp": "0x801ff5c0", "movie_frame": 3000,
    },
    "title_reset": {
        "ram_sha256": "2feca8ca69ea6ccd9a72cb821149a409afe9466a72376c9b694a3252aba7674a",
        "registers_sha256": "8b828e434e7695b0acb2be257c9150faff14baa6316a38097b5d1cc57c4537e2",
        "frame": 3201, "cycle": 1811837012, "pc": "0x00001ea8",
        "sp": "0x801fef58", "movie_frame": 3200,
    },
    "title_completed": {
        "ram_sha256": "a66d68f5235bff06c64c3ab855ccd820b8e000e946f2b523d1ca2adfb5a66c42",
        "registers_sha256": "942e52f310b83d9aaa21614ffdd2211fb0b9305ff4e7b61e26a06f27258f7037",
        "frame": 4601, "cycle": 2604522297, "pc": "0x8006e4b4",
        "sp": "0x801ff5c0", "movie_frame": 4600,
    },
    "intro_reset": {
        "ram_sha256": "aa26880fafbf959390cc5904fde05c2c7eb2037919d625312cbf830fc3477d60",
        "registers_sha256": "288ed775fcd1833cb8c52ef1447dca46228e5adf2b57f02cf7e09b1919487259",
        "frame": 4801, "cycle": 2717763052, "pc": "0x80065210",
        "sp": "0x801fee48", "movie_frame": 4800,
    },
    "intro_completed": {
        "ram_sha256": "eead0266a133060d54dc6b6d636c681b10198f101070fc94cb9d5bd0dae5e43a",
        "registers_sha256": "6b169e5f8b986117bd82d2c826e18bf38ce5ad57c67cf4f86da8d9044ea84273",
        "frame": 8401, "cycle": 4756096643, "pc": "0x80065210",
        "sp": "0x801ff5a0", "movie_frame": 8400,
    },
    "overlay_retired": {
        "ram_sha256": "5a30705d32511bd8d59425ee59103bd966db8d56e8e6ac464e9279101b809245",
        "registers_sha256": "42877724bab5ce6bbd01ffde0a28e0d9aa4082837556d787546dc0da31c92ff7",
        "frame": 8501, "cycle": 4812717023, "pc": "0x80065210",
        "sp": "0x801ffd38", "movie_frame": 8500,
    },
    "frontend_transition": {
        "ram_sha256": "a7c7d53e554fb9a6a0c8677ef14507a2fe6f62c4a18cc968e0232a9aff5ce37d",
        "registers_sha256": "dd0c7942321d82f501232c1a220c87592877dc793d32e0ea30e0f3a0e7e1d127",
        "frame": 9401, "cycle": 5322300418, "pc": "0x800707f4",
        "sp": "0x801ffdc8", "movie_frame": 9400,
    },
}

RESIDENT_REGIONS = {
    "fmv_bin_load": (0x8003E7C0, 0x8003E83C),
    "fmv_wait_and_completion_bridge": (0x8003EFC8, 0x8003F358),
    "fmv_sequence_completion_check": (0x800502C4, 0x8005038C),
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
    methods = capabilities.get("methods") or []
    return any((row.get("name") if isinstance(row, dict) else row) == method
               for row in methods)


def _exe_slice(exe: bytes, start: int, end: int) -> bytes:
    lo = EXE_HEADER + start - EXE_LOAD
    hi = EXE_HEADER + end - EXE_LOAD
    if lo < EXE_HEADER or hi > len(exe) or hi <= lo:
        raise SystemExit(f"invalid executable range 0x{start:08X}..0x{end:08X}")
    return exe[lo:hi]


def build_static_census() -> dict[str, Any]:
    fmv = FMV_BIN.read_bytes()
    exe = EXE.read_bytes()
    verify_staged_input(FMV_REL, fmv)
    verify_staged_input(EXE_REL, exe)
    movies = fmv_frame_table.manifest_movies(fmv)
    table = fmv_frame_table.frame_table(fmv)
    if len(movies) != 40 or len(table) != 40:
        raise SystemExit(
            f"pristine FMV manifest/table count drifted: {len(movies)}/{len(table)}")
    overlay_head_sha256 = _sha256_bytes(fmv[:0x100])
    if overlay_head_sha256 != FMV_OVERLAY_HEAD_SHA256:
        raise SystemExit("pristine FMV overlay head identity drifted")
    rows = []
    for index, ((offset, count), movie) in enumerate(zip(table, movies)):
        word = struct.unpack_from("<I", fmv, offset)[0]
        if word != 0x24050000 | count:
            raise SystemExit(
                f"FMV table opcode drifted at 0x{offset:X}: 0x{word:08X}")
        rows.append({
            "index": index, "path": movie.replace("\\", "/"),
            "frame_count": count, "file_offset": f"0x{offset:04X}",
            "runtime_address": f"0x{fmv_frame_table.OVERLAY_BASE + offset:08X}",
            "instruction_word": f"0x{word:08X}",
        })
    if len({row["path"].upper() for row in rows}) != 40:
        raise SystemExit("FMV manifest contains duplicate normalized paths")
    regions = {
        name: {
            "start": f"0x{start:08X}", "end": f"0x{end:08X}",
            "size": end - start,
            "sha256": _sha256_bytes(_exe_slice(exe, start, end)),
        }
        for name, (start, end) in RESIDENT_REGIONS.items()
    }
    return {
        "fmv_bin": {"path": f"REBUILD/files/{FMV_REL}",
                    "sha256": _sha256_bytes(fmv), "size": len(fmv),
                    "overlay_head_sha256": overlay_head_sha256},
        "resident_executable": {"path": f"REBUILD/files/{EXE_REL}",
                                "sha256": _sha256_bytes(exe), "size": len(exe)},
        "manifest_and_frame_table": {
            "entries": rows, "manifest_count": len(movies),
            "frame_table_count": len(table),
            "minimum_frame_count": min(row["frame_count"] for row in rows),
            "maximum_frame_count": max(row["frame_count"] for row in rows),
        },
        "resident_regions": regions,
        "typed_state": {
            "fmv_running_latch": {"address": "0x80082250", "width": "u32"},
            "completion_request": {"address": "0x800CAC10", "width": "u32",
                                   "residency": "FMV.BIN overlay"},
            "selected_frame_limit": {"address": "0x80131EEE", "width": "s16",
                                     "residency": "FMV.BIN overlay"},
        },
    }


def _pad_non_neutral(pad: dict[str, Any]) -> bool:
    axes = {"lx", "ly", "rx", "ry"}
    return any(bool(value) for key, value in pad.items() if key not in axes) or \
        any(pad.get(axis, 128) != 128 for axis in axes)


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    movie_pin = entries.get(MOVIE_REL)
    cold_boot_pin = entries.get(COLD_BOOT_MOVIE_REL)
    save = verify_declared_save_fixture(SAVE, allowed_media_classes={"pristine"})
    if not isinstance(movie_pin, dict) or \
            movie_pin.get("media_class") != "pristine_serial" or \
            movie_pin.get("sha256") != _sha256(MOVIE) or \
            movie_pin.get("size") != MOVIE.stat().st_size:
        raise SystemExit("E15 FMV movie central pin drifted")
    if not isinstance(cold_boot_pin, dict) or \
            cold_boot_pin.get("media_class") != "pristine_serial" or \
            cold_boot_pin.get("sha256") != _sha256(COLD_BOOT_MOVIE) or \
            cold_boot_pin.get("size") != COLD_BOOT_MOVIE.stat().st_size:
        raise SystemExit("E15 cold-boot movie central pin drifted")
    movie = json.loads(MOVIE.read_text())
    cold_boot = json.loads(COLD_BOOT_MOVIE.read_text())
    start = movie.get("start_state") or {}
    active = [
        row["frame"] for row in movie.get("frames") or []
        if any(bool(value) for value in (row.get("ports", {}).get("0") or {}).values())
    ]
    if movie.get("version") != 3 or movie.get("game_serial") != "SCUS-94288" or \
            start.get("game_serial") != "SCUS-94288" or \
            start.get("from_boot") is not False or \
            start.get("reproducible_only_from_state") is not True or \
            start.get("file_size") != save["size"] or \
            len(movie.get("frames") or []) != FINAL_FRAME or active != START_FRAMES:
        raise SystemExit(f"E15 FMV movie metadata/input drifted: active={active}")
    for frame in START_FRAMES:
        pad = movie["frames"][frame]["ports"]["0"]
        if pad.get("start") is not True or sum(bool(value) for value in pad.values()) != 1:
            raise SystemExit(f"E15 movie frame {frame} is not Start-only")
    cold_start = cold_boot.get("start_state") or {}
    changed = [
        row["frame"] for row in cold_boot.get("frames") or []
        if _pad_non_neutral((row.get("ports") or {}).get("0") or {})
    ]
    if cold_boot.get("version") != 3 or \
            cold_boot.get("game_serial") != "SCUS-94288" or \
            cold_start.get("game_serial") != "SCUS-94288" or \
            cold_start.get("from_boot") is not True or \
            cold_start.get("file_size") != 0 or \
            cold_start.get("reproducible_only_from_state") is not False or \
            len(cold_boot.get("frames") or []) != 10348 or \
            len(changed) != 7429 or changed[0] != 1758 or changed[-1] != 10347:
        raise SystemExit(
            "E15 cold-boot movie metadata/input drifted: "
            f"count={len(changed)} first={changed[:1]} last={changed[-1:]}")
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "movie": {"path": MOVIE_REL, "sha256": movie_pin["sha256"],
                  "size": movie_pin["size"], "media_class": movie_pin["media_class"],
                  "version": movie["version"], "frames": len(movie["frames"]),
                  "initial_frame": movie["initial_frame"],
                  "recorded_start_frames": active},
        "cold_boot_movie": {
            "path": COLD_BOOT_MOVIE_REL,
            "sha256": cold_boot_pin["sha256"], "size": cold_boot_pin["size"],
            "media_class": cold_boot_pin["media_class"],
            "version": cold_boot["version"],
            "frames": len(cold_boot["frames"]),
            "initial_frame": cold_boot["initial_frame"],
            "from_boot": cold_start["from_boot"],
            "non_neutral_frame_count": len(changed),
            "first_non_neutral_frame": changed[0],
            "last_non_neutral_frame": changed[-1],
            "non_neutral_frames_sha256": _sha256_bytes(
                json.dumps(changed, separators=(",", ":")).encode()),
        },
        "save": save,
        "declared_start_state": {
            "frame": start.get("frame"), "pc": start.get("pc"),
            "sp": start.get("sp"), "game_serial": start.get("game_serial"),
            "from_boot": start.get("from_boot"),
            "reproducible_only_from_state": start.get("reproducible_only_from_state"),
        },
        "classification_boundary": (
            "filenames are leads; the retained Start-only edit, neutral cold-boot "
            "recipe and measured typed/trace outcomes establish the conclusions"),
    }


def _write_neutral_cold_boot_movie(path: Path) -> dict[str, Any]:
    """Create an ephemeral, from-boot timing movie with every input neutral."""
    movie = json.loads(COLD_BOOT_MOVIE.read_text())
    changed = []
    for row in movie.get("frames") or []:
        pad = (row.get("ports") or {}).get("0") or {}
        if _pad_non_neutral(pad):
            changed.append(row["frame"])
            row["ports"]["0"] = {}
    if len(changed) != 7429 or changed[0] != 1758 or changed[-1] != 10347:
        raise SystemExit("cold-boot neutralization frontier drifted")
    payload = json.dumps(movie, separators=(",", ":")).encode() + b"\n"
    path.write_bytes(payload)
    return {
        "source_path": COLD_BOOT_MOVIE_REL,
        "source_sha256": _sha256(COLD_BOOT_MOVIE),
        "derived_sha256": _sha256_bytes(payload),
        "source_frame_count": len(movie["frames"]),
        "derived_frame_count": len(movie["frames"]),
        "changed_frame_count": len(changed),
        "first_changed_frame": changed[0],
        "last_changed_frame": changed[-1],
        "changed_frames_sha256": _sha256_bytes(
            json.dumps(changed, separators=(",", ":")).encode()),
        "changed_field": "all non-neutral port-0 buttons/axes -> neutral",
        "anchor": "from_boot",
        "transient_storage": "temporary directory; derivative deleted before retention",
    }


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    data = bytes.fromhex(row["hex"])
    if len(data) != length:
        raise SystemExit(f"short debugger read at 0x{address:08X}")
    return data


def _snapshot(client: Any) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    overlay_head_sha256 = _sha256_bytes(
        _read_memory(client, fmv_frame_table.OVERLAY_BASE, 0x100))
    overlay_resident = overlay_head_sha256 == FMV_OVERLAY_HEAD_SHA256
    return {
        "status": {key: status.get(key) for key in
                   ("pc", "sp", "frame", "cycle", "paused", "game_serial")},
        "resident": {
            "fmv_running_latch": struct.unpack(
                "<I", _read_memory(client, FMV_RUNNING_LATCH, 4))[0],
            "scene": struct.unpack("<I", _read_memory(client, SCENE, 4))[0],
            "master_state": struct.unpack(
                "<H", _read_memory(client, MASTER_STATE, 2))[0],
            "shell_substate": struct.unpack(
                "<I", _read_memory(client, SHELL_SUBSTATE, 4))[0],
            "str_backloc": struct.unpack(
                "<I", _read_memory(client, STR_BACKLOC, 4))[0],
        },
        "region_b": {
            "overlay_resident": overlay_resident,
            "overlay_head_sha256": overlay_head_sha256,
            "resident_fields": {
                "completion_request": struct.unpack(
                    "<I", _read_memory(client, FMV_COMPLETE, 4))[0],
                "selected_frame_limit": struct.unpack(
                    "<h", _read_memory(client, FMV_TOTAL_FRAMES, 2))[0],
            } if overlay_resident else None,
        },
    }


def _compact_trace(trace: dict[str, Any], *, retain_pcs: bool = True) -> dict[str, Any]:
    coverage = []
    for row in trace.get("coverage") or []:
        data = row.get("coverage") or {}
        pcs = data.get("pcs") or []
        coverage.append({
            "label": row.get("label"), "range": row.get("range"),
            "total_hits": data.get("total_hits"),
            "distinct_pc_count": data.get("distinct_pc_count"),
            "truncated": data.get("truncated", False),
            "pcs_sha256": _sha256_bytes(
                json.dumps(pcs, separators=(",", ":")).encode()),
            "first_pc": pcs[0] if pcs else None,
            "last_pc": pcs[-1] if pcs else None,
            "pcs": pcs if retain_pcs or row.get("label") == "fmv_completion_limit" else [],
        })
    return {
        key: trace.get(key) for key in (
            "target_frame", "trace_mode", "configured_execution_mode",
            "comparison_execution_mode", "control", "instrumented", "comparison")
    } | {"coverage": coverage}


def _trace_snapshot(
        client: Any, path: Path | None, frame: int, *,
        ranges: tuple[dict[str, Any], ...] = TRACE_RANGES,
        retain_pcs: bool = True) -> dict[str, Any]:
    params = {"frame": frame, "ranges": list(ranges)}
    if path is not None:
        params["path"] = str(path.resolve())
    trace = _compact_trace(
        client.call("movie.traceToFrame", params, timeout=900),
        retain_pcs=retain_pcs)
    if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row["truncated"] for row in trace["coverage"]):
        raise SystemExit(f"E15 trace was not cycle-neutral at movie frame {frame}")
    status = client.call("movie.status", {})
    if status.get("reproducible") is not True or status.get("truncated") is not False:
        raise SystemExit(f"E15 movie lost reproducibility at frame {frame}: {status}")
    return {"movie_frame": frame, "movie_status": status,
            "snapshot": _snapshot(client), "cycle_neutral_trace": trace}


def _trace_signature_gaps(trace: dict[str, Any], label: str) -> list[str]:
    gaps = []
    control = trace.get("control") or {}
    instrumented = trace.get("instrumented") or {}
    keys = ("ram_sha256", "registers_sha256", "cycle", "frame",
            "movie_frame", "pc", "sp")
    unequal = [key for key in keys if control.get(key) != instrumented.get(key)]
    comparison = trace.get("comparison") or {}
    derived = {
        "same_ram": control.get("ram_sha256") == instrumented.get("ram_sha256"),
        "same_registers": control.get("registers_sha256") == instrumented.get("registers_sha256"),
        "same_cycle": control.get("cycle") == instrumented.get("cycle"),
        "same_frame": control.get("frame") == instrumented.get("frame") and
                      control.get("movie_frame") == instrumented.get("movie_frame"),
    }
    derived["cycle_neutral"] = all(derived.values()) and not unequal
    for key, value in derived.items():
        if comparison.get(key) is not value:
            gaps.append(f"{label} comparison.{key} is not derived from signatures")
    if unequal:
        gaps.append(f"{label} control/instrumented signatures diverged: {unequal}")
    return gaps


def _activate_neutral_movie(client: Any) -> dict[str, Any]:
    """Edit the loaded movie in memory so the anchor/parser remain identical."""
    client.call("movie.stopPlayback", {})
    client.call("movie.load", {"path": str(MOVIE.resolve())})
    stored = client.call("movie.store", {})
    movie_id = stored["movieId"]
    changed = []
    for frame in START_FRAMES:
        client.call("movie.editFrame", {
            "movieId": movie_id, "frame": frame, "input": {"0": {}}})
        changed.append(frame)
    edited = client.call("movie.get", {"movieId": movie_id})
    activated = client.call("movie.activate", {"movieId": movie_id})
    return {
        "source_sha256": _sha256(MOVIE),
        "derived_semantic_sha256": _sha256_bytes(
            json.dumps(edited, sort_keys=True, separators=(",", ":")).encode()),
        "changed_frames": changed, "changed_field": "ports.0.start true -> false",
        "source_frame_count": FINAL_FRAME,
        "derived_frame_count": activated["frame_count"],
        "rerecord_count": edited.get("rerecord_count"),
        "transient_storage": "debugger in-memory registry; no recording bytes retained",
    }


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps = []
    static = document.get("static_census") or {}
    table = (static.get("manifest_and_frame_table") or {}).get("entries") or []
    if len(table) != 40 or any(
            int(row["instruction_word"], 16) != 0x24050000 | row["frame_count"]
            for row in table):
        gaps.append("FMV manifest/frame table no longer has 40 exact addiu rows")
    live = document.get("live") or {}
    natural = live.get("natural_start_skip") or {}
    neutral = live.get("start_removed_control") or {}
    pre_a = (natural.get("pre_trigger") or {}).get("cycle_neutral_trace") or {}
    pre_b = (neutral.get("pre_trigger") or {}).get("cycle_neutral_trace") or {}
    sig_a = pre_a.get("control") or {}
    sig_b = pre_b.get("control") or {}
    for key in ("ram_sha256", "registers_sha256", "cycle", "frame", "pc", "sp"):
        if sig_a.get(key) != sig_b.get(key):
            gaps.append(f"natural/control pre-trigger {key} diverged")
    expected_pre = {
        "ram_sha256": "1044d5b7d0bb6dc5a563a18c98e497e66f7919152d3ddcf1b093e2f4a01224e5",
        "registers_sha256": "754f0d34004d6508c9410c0c667bcf2726cb94bcb12241db10630a0622b63117",
        "cycle": 2585837573, "frame": 4568, "movie_frame": 333,
        "pc": "0x80070d00", "sp": "0x801ff600",
    }
    if sig_a != expected_pre or sig_b != expected_pre:
        gaps.append("stable retained pre-trigger signature changed")
    post_a = (natural.get("post_trigger") or {}).get("snapshot") or {}
    post_b = (neutral.get("post_trigger") or {}).get("snapshot") or {}
    final_a = (natural.get("final") or {}).get("snapshot") or {}
    final_b = (neutral.get("final") or {}).get("snapshot") or {}
    if ((post_a.get("status") or {}).get("pc"),
            (post_b.get("status") or {}).get("pc")) != \
            ("0x80065340", "0x800b98f0"):
        gaps.append("Start/control immediate post-input PCs changed")
    post_region_a = post_a.get("region_b") or {}
    post_region_b = post_b.get("region_b") or {}
    expected_resident = {
        "overlay_resident": True,
        "overlay_head_sha256": FMV_OVERLAY_HEAD_SHA256,
        "resident_fields": {"completion_request": 0,
                            "selected_frame_limit": 386},
    }
    if post_region_a != expected_resident or post_region_b != expected_resident:
        gaps.append("Start/control immediate FMV overlay state changed")
    final_region_a = final_a.get("region_b") or {}
    final_region_b = final_b.get("region_b") or {}
    if final_region_a.get("overlay_resident") is not False or \
            final_region_a.get("resident_fields") is not None or \
            final_region_b != expected_resident:
        gaps.append("Start-only final FMV overlay residency divergence changed")
    if ((final_a.get("resident") or {}).get("str_backloc"),
            (final_b.get("resident") or {}).get("str_backloc")) != (73, 163):
        gaps.append("Start-only final stream-backloc divergence changed")
    for branch in (natural, neutral):
        for point in ("pre_trigger", "post_trigger", "final"):
            trace = (branch.get(point) or {}).get("cycle_neutral_trace") or {}
            gaps.extend(_trace_signature_gaps(trace, f"state {point}"))
            if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                    any(row.get("truncated") or not row.get("total_hits")
                        for row in trace.get("coverage") or []):
                gaps.append(f"{point} retained trace is not cycle-neutral and complete")
    cold = live.get("cold_boot_natural_completion") or {}
    recipe = cold.get("neutral_input_recipe") or {}
    cold_fixture = (document.get("fixture_census") or {}).get("cold_boot_movie") or {}
    expected_recipe = {
        "source_sha256": "bfedc0d0f4828998fc598257b35ad090180ad6cb01ea317bc40229f977dc40fb",
        "source_frame_count": 10348,
        "derived_frame_count": 10348,
        "changed_frame_count": 7429,
        "first_changed_frame": 1758,
        "last_changed_frame": 10347,
    }
    for key, value in expected_recipe.items():
        if recipe.get(key) != value:
            gaps.append(f"cold-boot neutral recipe {key} changed")
    if recipe.get("changed_frames_sha256") != \
            cold_fixture.get("non_neutral_frames_sha256"):
        gaps.append("cold-boot neutral recipe frame digest changed")
    expected_typed = {
        "dlogo_selected": (2000, True, 0, 156, 0, 0, 0, 0),
        "dlogo_completed": (3000, True, 1, 156, 154, 0, 0, 0),
        "title_reset": (3200, True, 0, 0, 154, 0, 0, 0),
        "title_completed": (4600, True, 1, 440, 438, 0, 0, 0),
        "intro_reset": (4800, True, 0, 0, 438, 0, 0, 0),
        "intro_completed": (8400, True, 1, 1750, 1748, 0, 0, 0),
        "overlay_retired": (8500, False, None, None, 1748, 0, 0, 0),
        "frontend_transition": (9400, False, None, None, 1748, 1, 1, 0),
    }
    points = cold.get("points") or {}
    for label, expected in expected_typed.items():
        frame, resident, completion, limit, backloc, scene, shell, running = expected
        point = points.get(label) or {}
        snapshot = point.get("snapshot") or {}
        region = snapshot.get("region_b") or {}
        fields = region.get("resident_fields")
        resident_state = snapshot.get("resident") or {}
        if point.get("movie_frame") != frame or \
                region.get("overlay_resident") is not resident or \
                (fields or {}).get("completion_request") != completion or \
                (fields or {}).get("selected_frame_limit") != limit or \
                resident_state.get("str_backloc") != backloc or \
                resident_state.get("scene") != scene or \
                resident_state.get("shell_substate") != shell or \
                resident_state.get("fmv_running_latch") != running:
            gaps.append(f"cold-boot typed boundary {label} changed")
        movie_status = point.get("movie_status") or {}
        if movie_status.get("reproducible") is not True or \
                (movie_status.get("start_state") or {}).get("from_boot") is not True:
            gaps.append(f"cold-boot point {label} lost from-boot reproducibility")
        trace = point.get("cycle_neutral_trace") or {}
        gaps.extend(_trace_signature_gaps(trace, f"cold-boot {label}"))
        if any(row.get("truncated") for row in trace.get("coverage") or []):
            gaps.append(f"cold-boot point {label} trace truncated")
        expected_signature = EXPECTED_COLD_BOOT_SIGNATURES.get(label)
        if expected_signature and (trace.get("control") or {}) != expected_signature:
            gaps.append(f"cold-boot point {label} retained signature changed")
    final_coverage = ((points.get("frontend_transition") or {}).get(
        "cycle_neutral_trace") or {}).get("coverage") or []
    coverage_by_label = {row.get("label"): row for row in final_coverage}
    if any(not (coverage_by_label.get(label) or {}).get("total_hits")
           for label in ("resident_fmv_load_and_wait",
                         "resident_shell_and_completion",
                         "libcd_libpress_streaming", "fmv_overlay",
                         "fmv_completion_limit")):
        gaps.append("cold-boot final trace has a zero-coverage frontier")
    completion_pcs = set(
        (coverage_by_label.get("fmv_completion_limit") or {}).get("pcs") or [])
    if not {"0x800b6b18", "0x800b6b48"}.issubset(completion_pcs):
        gaps.append("cold-boot completion-limit PCs are absent")
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned live process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    fixtures = build_fixture_census()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.readMemory",
        "debugger.pause", "emulator.getMediaInfo", "emulator.getStateInfo",
        "movie.load", "movie.startPlayback", "movie.traceToFrame",
        "movie.stopPlayback", "movie.status", "movie.clear", "movie.store",
        "movie.editFrame", "movie.get", "movie.activate",
    }
    missing = sorted(method for method in required
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks E15 methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, SAVE, media_identity)

    def branch(path: Path | None) -> dict[str, Any]:
        return {
            "pre_trigger": _trace_snapshot(client, path, PRE_TRIGGER_FRAME),
            "post_trigger": _trace_snapshot(client, path, POST_TRIGGER_FRAME),
            "final": _trace_snapshot(client, path, FINAL_FRAME),
        }

    # The first cached-interpreter coverage request after a freshly launched
    # recompiler instance transitions the execution backend.  Do not compare
    # that transition call with a later steady-state call: warm it once, then
    # require the retained natural/control signatures to agree exactly.
    warmup = _trace_snapshot(client, MOVIE, PRE_TRIGGER_FRAME)
    natural = branch(MOVIE)
    edit = _activate_neutral_movie(client)
    neutral = branch(None)
    with tempfile.TemporaryDirectory(prefix="abl-phase4-fmv-neutral-boot-") as temp_dir:
        neutral_boot_path = Path(temp_dir) / "neutral-from-boot.movie.json"
        neutral_boot_recipe = _write_neutral_cold_boot_movie(neutral_boot_path)
        cold_warmup = _trace_snapshot(
            client, neutral_boot_path, COLD_BOOT_WARMUP_FRAME,
            ranges=COLD_BOOT_TRACE_RANGES, retain_pcs=False)
        cold_points = {
            label: _trace_snapshot(
                client, neutral_boot_path, frame,
                ranges=COLD_BOOT_TRACE_RANGES, retain_pcs=False)
            for label, frame in COLD_BOOT_POINTS
        }
    final_media = verified_media_identity(client, client.call("debugger.status", {}))
    document = {
        "_comment": (
            "Active E15 evidence: exhaustive pristine FMV manifest/frame-count "
            "table, a state-anchored Start-only skip counterfactual and natural "
            "cold-boot completion/reuse of three streams."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-fmv/1", "campaign_state": "active_partial",
        "static_census": static, "fixture_census": fixtures,
        "live": {"discarded_execution_mode_warmup": warmup,
                 "input_edit": edit, "natural_start_skip": natural,
                 "start_removed_control": neutral,
                 "cold_boot_natural_completion": {
                     "discarded_execution_mode_warmup": cold_warmup,
                     "neutral_input_recipe": neutral_boot_recipe,
                     "points": cold_points,
                 }},
        "bounded_interpretation": {
            "observation": (
                "The branches are identical immediately before recorded Start, "
                "diverge at the immediate post-input PC, and by the final "
                "sample only the Start-removed branch retains FMV.BIN at region B."),
            "inference": (
                "Fresh Start is a native FMV skip input for this inspected pristine anchor."),
            "causal_confirmation": (
                "Only nine ports.0.start samples differ; every retained coverage "
                "branch is cycle/RAM/register/frame neutral against its own control."),
            "forbidden_claim": (
                "Three natural cold-boot streams and one state-anchored clip do not "
                "close every manifest entry, movie viewer, pause/stop, stream/decode "
                "error, level transition or frontend ownership boundary."),
        },
        "bounded_open_frontier": {
            "natural_completion": (
                "Closed for neutral cold-boot dlogo/title/intro only; level-owned and "
                "viewer-owned natural completion remain separate breadth work."),
            "breadth": (
                "Replay representative level A/B, alternate, lose and movie-viewer "
                "owners for the 36 manifest entries without live evidence."),
            "exceptional_paths": "Capture decode timeout/CD failure and pause/stop behavior without manufacturing success.",
            "next_experiment": (
                "Use existing end-of-level/menu movies to bind one natural level-B "
                "transition and one movie-viewer selection, then test pause/stop/reuse."),
        },
        "source_dependencies": {
            "tools/fmv_frame_table.py": _sha256(ROOT / "tools/fmv_frame_table.py"),
            "src_re/fmv_player_streaming.c": _sha256(ROOT / "src_re/fmv_player_streaming.c"),
            "src/main/8003e7c0_fmv_bin_load.c": _sha256(
                ROOT / "src/main/8003e7c0_fmv_bin_load.c"),
        },
        "run_provenance": {},
    }
    gaps = evidence_gaps(document)
    if gaps:
        diagnostic = Path("/tmp/abl-phase4-fmv-failed-evidence.json")
        diagnostic.write_text(json.dumps(document, indent=1) + "\n")
        raise SystemExit(f"retained E15 evidence failed: {gaps}")
    document["run_provenance"] = finish_run(
        args, generator="tools/phase4_fmv.py",
        anchor={
            "type": (
                "state-anchored FMV Start skip control plus neutral from-boot natural "
                "dlogo/title/intro completion and frontend transition"),
            "save": SAVE_REL,
            "fixture_sha256": {
                SAVE_REL: fixtures["save"]["sha256"],
                COLD_BOOT_MOVIE_REL: fixtures["cold_boot_movie"]["sha256"],
            },
            "state_inspections": [inspection], "media_identity": media_identity,
            "final_media_identity": final_media,
            "movie": fixtures["movie"], "transient_counterfactual": edit,
            "cold_boot_movie": fixtures["cold_boot_movie"],
            "cold_boot_neutral_recipe": neutral_boot_recipe,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "movie_frames": {"pre_trigger": PRE_TRIGGER_FRAME,
                             "post_trigger": POST_TRIGGER_FRAME,
                             "final": FINAL_FRAME,
                             "cold_boot_warmup": COLD_BOOT_WARMUP_FRAME,
                             "cold_boot_points": dict(COLD_BOOT_POINTS)},
            "coverage_control": (
                "one discarded backend-transition warm-up, then movie.traceToFrame "
                "uninstrumented versus passive cached-block replay for both anchors"),
        })
    cleanup_gaps = evidence_gaps(document)
    if cleanup_gaps:
        raise SystemExit(f"retained E15 cleanup evidence failed: {cleanup_gaps}")
    write_live_evidence(OUTPUT, document)
    print("[phase4-fmv] retained 40-entry frontier, Start skip, and three natural boot completions")
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
                args, generator="tools/phase4_fmv.py",
                anchor={"type": "aborted before retained E15 evidence"}, timing={})
        except BaseException as cleanup_error:
            print(f"owned E15 cleanup also failed: {cleanup_error}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
