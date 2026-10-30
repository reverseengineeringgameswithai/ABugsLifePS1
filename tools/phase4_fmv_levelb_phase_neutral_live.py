#!/usr/bin/env python3
"""Revalidate the E15 full-level lead with passive from-boot controls.

The earlier scenario.bootAndRun receipt started the from-boot movie with
``load_start_state:false`` and therefore reported ``reproducible:false``.
This bounded collector uses ``movie.traceToFrame`` instead: the RPC resets the
movie to its recorded boot anchor for an uninstrumented cached-interpreter run
and a passive-coverage run, then compares their deterministic signatures.
Raw output and the transient neutral movie must remain outside the repository.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

import phase4_common as common


MOVIE = Path(
    "~/Downloads/ABL/movies/100% Runs/LEVEL01.movie.json")
CUE = Path(
    "~/Downloads/ABL/"
    "Disney-Pixar A Bug's Life (v1.0).cue")
BIN = Path(
    "~/Downloads/ABL/"
    "Disney-Pixar A Bug's Life (v1.0).bin")
CLIENT = Path.home() / (
    "duckstation/scripts/debugger-client/duckstation_debug_client.py")

EXPECTED = {
    "movie_sha256":
        "ece62d4e6f92b887b0500dd8ac3bec48f3638ad5d9858cda7d5b0afb3a8d2602",
    "cue_sha256":
        "463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644",
    "bin_sha256":
        "2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566",
    "binary_sha256":
        "55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8",
    "source_revision": "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5",
    "dirty_state_hash":
        "72dd936c8a6f92f6370815da7d9e192c3bcc2371",
}

SOURCE_MOVIE_FRAMES = 15230
DERIVED_MOVIE_FRAMES = 15231
TRACE_TARGET_FRAME = 15230
COMPLETED_LEVEL_B_CALL = "0x8005031c"
LEVEL_A_RESET_CALL = "0x8005b788"
SELECTED_LIMIT_WRITE = "0x800b6dc0"

TRACE_RANGES = (
    {
        "start": "0x8004fa40", "end": "0x8005038c",
        "label": "resident_fmv_sequence", "max_pcs": 1024,
    },
    {
        "start": "0x8005b714", "end": "0x8005bc64",
        "label": "level_a_reset_owner", "max_pcs": 1024,
    },
    {
        "start": "0x8003e7c0", "end": "0x8003f358",
        "label": "fmv_loader", "max_pcs": 1024,
    },
    {
        "start": "0x800b6250", "end": "0x800b65b0",
        "label": "fmv_selector", "max_pcs": 1024,
    },
    {
        "start": "0x800b6b00", "end": "0x800b6b60",
        "label": "fmv_completion_limit", "max_pcs": 128,
    },
    {
        "start": "0x800b6d68", "end": "0x800b752c",
        "label": "fmv_player", "max_pcs": 1024,
    },
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_client() -> Any:
    spec = importlib.util.spec_from_file_location(
        "phase4_fmv_levelb_phase_neutral_client", CLIENT)
    _require(spec is not None and spec.loader is not None,
             f"cannot load debugger client: {CLIENT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _method_present(capabilities: dict, method: str) -> bool:
    return method in (capabilities.get("methods") or {})


def _non_neutral(pad: dict) -> bool:
    for key, value in pad.items():
        if key in {"lx", "ly", "rx", "ry"}:
            if int(value) != 128:
                return True
        elif bool(value):
            return True
    return False


def _write_replay_movie(path: Path, *, neutralize: bool) -> dict:
    movie = json.loads(MOVIE.read_text())
    frames = movie.get("frames") or []
    _require(
        movie.get("format") == "DuckStationInputMovie" and
        movie.get("version") == 3 and
        len(frames) == SOURCE_MOVIE_FRAMES and
        (movie.get("start_state") or {}).get("from_boot") is True,
        "source movie metadata drifted")
    source_prefix_sha256 = _sha256_bytes(
        json.dumps(frames, separators=(",", ":"), sort_keys=True).encode())
    changed: list[int] = []
    if neutralize:
        for row in frames:
            ports = row.get("ports") or {}
            pad = ports.get("0") or {}
            if _non_neutral(pad):
                changed.append(int(row["frame"]))
                ports["0"] = {}
    derived_prefix_sha256 = _sha256_bytes(
        json.dumps(frames, separators=(",", ":"), sort_keys=True).encode())
    if not neutralize:
        _require(
            derived_prefix_sha256 == source_prefix_sha256,
            "original replay prefix drifted")
    frames.append({
        "frame": SOURCE_MOVIE_FRAMES,
        "ports": {"0": {}},
    })
    payload = json.dumps(
        movie, separators=(",", ":"), sort_keys=True).encode() + b"\n"
    path.write_bytes(payload)
    return {
        "source_path": str(MOVIE),
        "source_sha256": common.sha256(MOVIE),
        "derived_sha256": common.sha256(path),
        "derived_bytes": path.stat().st_size,
        "source_frame_count": SOURCE_MOVIE_FRAMES,
        "derived_frame_count": len(frames),
        "trace_target_frame": TRACE_TARGET_FRAME,
        "appended_unexecuted_padding_frames": 1,
        "source_prefix_sha256": source_prefix_sha256,
        "derived_prefix_sha256": derived_prefix_sha256,
        "source_prefix_semantically_identical": not neutralize,
        "changed_frame_count": len(changed),
        "first_changed_frame": changed[0] if changed else None,
        "last_changed_frame": changed[-1] if changed else None,
        "changed_frames_sha256": _sha256_bytes(
            json.dumps(changed, separators=(",", ":")).encode()),
        "changed_field": "all non-neutral port-0 buttons/axes -> neutral",
        "anchor": "from_boot",
        "transient_storage":
            "temporary /var/tmp directory removed before collector exit",
    }


def _compact_trace(trace: dict) -> dict:
    coverage = []
    for row in trace.get("coverage") or []:
        data = row.get("coverage") or {}
        pcs = data.get("pcs") or []
        coverage.append({
            "label": row.get("label"),
            "range": row.get("range"),
            "total_hits": data.get("total_hits"),
            "distinct_pc_count": data.get("distinct_pc_count"),
            "truncated": data.get("truncated", False),
            "pcs_sha256": _sha256_bytes(
                json.dumps(pcs, separators=(",", ":")).encode()),
            "pcs": pcs,
        })
    return {
        key: trace.get(key) for key in (
            "target_frame", "trace_mode", "configured_execution_mode",
            "comparison_execution_mode", "control", "instrumented",
            "comparison", "status")
    } | {"coverage": coverage}


def _trace(client: Any, path: Path, label: str) -> dict:
    trace = _compact_trace(client.call("movie.traceToFrame", {
        "path": str(path),
        "frame": TRACE_TARGET_FRAME,
        "ranges": list(TRACE_RANGES),
    }, timeout=1800))
    comparison = trace.get("comparison") or {}
    _require(
        comparison.get("cycle_neutral") is True and
        all(comparison.get(key) is True for key in (
            "same_ram", "same_registers", "same_cycle", "same_frame")),
        f"{label}: passive replay was not phase-neutral")
    _require(
        all(row["truncated"] is False for row in trace["coverage"]),
        f"{label}: passive coverage truncated")
    status = client.call("movie.status", {})
    _require(
        status.get("reproducible") is True and
        status.get("truncated") is False and
        status.get("playback_index") == TRACE_TARGET_FRAME and
        status.get("frame_count") == DERIVED_MOVIE_FRAMES and
        (status.get("start_state") or {}).get("from_boot") is True,
        f"{label}: movie did not retain its recorded boot anchor")
    by_label = {row["label"]: row for row in trace["coverage"]}
    sequence_pcs = by_label["resident_fmv_sequence"]["pcs"]
    level_a_pcs = by_label["level_a_reset_owner"]["pcs"]
    completion_pcs = by_label["fmv_completion_limit"]["pcs"]
    if label == "original_movie":
        _require(
            LEVEL_A_RESET_CALL in level_a_pcs,
            "original movie did not execute the static level-A reset call")
        _require(
            SELECTED_LIMIT_WRITE in {
                pc.lower() for pc in by_label["fmv_player"]["pcs"]
            } or SELECTED_LIMIT_WRITE in {
                pc.lower() for pc in completion_pcs
            },
            "original movie did not execute the FMV selected-limit path")
    return {
        "movie_status": status,
        "cycle_neutral_trace": trace,
        "observed": {
            "completed_level_b_call":
                COMPLETED_LEVEL_B_CALL in {
                    pc.lower() for pc in sequence_pcs
                },
            "level_a_reset_call":
                LEVEL_A_RESET_CALL in {
                    pc.lower() for pc in level_a_pcs
                },
            "selected_limit_writer":
                SELECTED_LIMIT_WRITE in {
                    pc.lower() for pc in by_label["fmv_player"]["pcs"]
                },
        },
    }


def _cleanup(client: Any) -> list[dict]:
    rows = []
    for method, params in (
            ("movie.stopPlayback", {}),
            ("movie.clear", {}),
            ("debugger.clearBreakpoints", {}),
            ("accessLog.clear", {}),
            ("execTrace.clear", {}),
            ("functionTrace.stop", {}),
            ("functionTrace.clear", {}),
            ("provenanceLog.stop", {}),
            ("provenanceLog.clear", {}),
            ("emulator.clearControllerState", {"port": 0}),
            ("emulator.setTurbo", {"enabled": False}),
            ("emulator.setFastForward", {"enabled": False})):
        try:
            result = client.call(method, params)
            rows.append({"method": method, "ok": True, "result": result})
        except Exception as exc:  # cleanup evidence, followed by owned-PID stop
            rows.append({"method": method, "ok": False, "error": str(exc)})
    return rows


def collect(port: int, token: str) -> dict:
    for label, path, digest in (
            ("movie", MOVIE, EXPECTED["movie_sha256"]),
            ("cue", CUE, EXPECTED["cue_sha256"]),
            ("bin", BIN, EXPECTED["bin_sha256"])):
        _require(
            path.is_file() and common.sha256(path) == digest,
            f"{label} fixture identity drifted")

    module = _load_client()
    client = module.DebuggerClient("127.0.0.1", port, "ws")
    client.authenticate(token)
    client.transport.sock.settimeout(1800)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.capabilities", "debugger.status",
        "debugger.clearBreakpoints", "emulator.getMediaInfo",
        "scenario.runBatch", "scenario.loadStateAndRun",
        "scenario.bootAndRun", "capture.atomic",
        "movie.traceToFrame", "movie.status", "movie.stopPlayback",
        "movie.clear", "accessLog.clear", "execTrace.clear",
        "functionTrace.stop", "functionTrace.clear",
        "provenanceLog.start", "provenanceLog.get",
        "provenanceLog.stop", "provenanceLog.clear",
        "emulator.clearControllerState", "emulator.setTurbo",
        "emulator.setFastForward",
    }
    missing = sorted(
        method for method in required
        if not _method_present(capabilities, method))
    _require(not missing, f"running debugger lacks methods: {missing}")
    _require(
        (capabilities.get("api") or {}).get("version") == "2.1.0" and
        (capabilities.get("api") or {}).get("schema_version") ==
        "2026-07-18" and
        (capabilities.get("binary") or {}).get("sha256") ==
        EXPECTED["binary_sha256"] and
        (capabilities.get("source") or {}).get("revision") ==
        EXPECTED["source_revision"] and
        (capabilities.get("source") or {}).get("dirty") is True and
        (capabilities.get("source") or {}).get("dirty_state_hash") ==
        EXPECTED["dirty_state_hash"],
        "debugger capability identity drifted")

    status = client.call("debugger.status", {})
    media = client.call("emulator.getMediaInfo", {})
    _require(
        status.get("valid") is True and
        status.get("game_serial") == "SCUS-94288" and
        status.get("game_title") == "Disney-Pixar A Bug's Life" and
        Path(str(status.get("game_path") or "")).resolve() == CUE.resolve(),
        f"debugger status media identity drifted: {status}")
    _require(
        media.get("has_media") is True and
        media.get("game_serial") == "SCUS-94288" and
        media.get("game_title") == "Disney-Pixar A Bug's Life" and
        Path(str(media.get("path") or "")).resolve() == CUE.resolve(),
        f"mounted media identity drifted: {media}")
    media["verified_cue_sha256"] = common.sha256(CUE)
    media["verified_track_sha256"] = common.sha256(BIN)

    cleanup: list[dict] = []
    original: dict | None = None
    neutral: dict | None = None
    original_recipe: dict | None = None
    neutral_recipe: dict | None = None
    try:
        with tempfile.TemporaryDirectory(
            prefix="abl-p4-e15-levelb-neutral-", dir="/var/tmp") as tmp:
            original_path = Path(tmp) / "LEVEL01.padded.movie.json"
            neutral_path = Path(tmp) / "LEVEL01.neutral.movie.json"
            original_recipe = _write_replay_movie(
                original_path, neutralize=False)
            neutral_recipe = _write_replay_movie(
                neutral_path, neutralize=True)
            original = _trace(client, original_path, "original_movie")
            neutral = _trace(client, neutral_path, "neutral_movie")
    finally:
        cleanup = _cleanup(client)

    _require(
        original is not None and neutral is not None and
        original_recipe is not None and
        neutral_recipe is not None,
        "phase-neutral traces did not complete")
    _require(
        all(row["ok"] is True for row in cleanup),
        "instrumentation/controller cleanup failed")
    return {
        "schema": "abl-phase4-fmv-levelb-phase-neutral-live/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": {
            "rpc": "movie.traceToFrame",
            "target_frame": TRACE_TARGET_FRAME,
            "source_frame_count": SOURCE_MOVIE_FRAMES,
            "derived_frame_count": DERIVED_MOVIE_FRAMES,
            "trace_mode": "passive_cached_block_coverage",
            "control":
                "internal uninstrumented replay from recorded boot anchor",
            "fallback_reason":
                "scenario.bootAndRun hardcodes movie load_start_state=false "
                "in the pinned runtime and cannot produce reproducible=true",
        },
        "capabilities": capabilities,
        "initial_status": status,
        "mounted_media": media,
        "fixtures": {
            "movie": {
                "absolute_path": str(MOVIE),
                "sha256": common.sha256(MOVIE),
                "bytes": MOVIE.stat().st_size,
            },
            "cue": {
                "absolute_path": str(CUE),
                "sha256": common.sha256(CUE),
                "bytes": CUE.stat().st_size,
            },
            "bin": {
                "absolute_path": str(BIN),
                "sha256": common.sha256(BIN),
                "bytes": BIN.stat().st_size,
            },
        },
        "original_replay_derivative": original_recipe,
        "neutral_derivative": neutral_recipe,
        "original_movie": original,
        "neutral_movie": neutral,
        "cleanup": cleanup,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.config_dir.is_absolute():
        raise SystemExit("--config-dir must be absolute")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = collect(args.port, args.token)
    document["isolated_instance"] = {
        "config_dir": str(args.config_dir),
        "port": args.port,
        "host": "127.0.0.1",
        "transport": "ws",
        "profile_recreated": True,
        "token_retained": False,
    }
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(
        "PASS: reproducible phase-neutral full-level controls -> "
        f"{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
