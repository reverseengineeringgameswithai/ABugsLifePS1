#!/usr/bin/env python3
"""Classify the pinned LEVEL15 recording against the resident finale callers.

The movie filename and its retained scene timeline are leads, not proof that
the recording executes either resident finale owner.  This collector first
demonstrates why bare-PC coverage is insufficient across a cold boot, then
requires the statically reconstructed selector register at the LEV15C caller.
The LEV15D caller has no bare-PC hit and therefore needs no register filter.

Raw output remains external.  The tracked summarizer independently validates
the low-level comparisons and bounded negative result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import phase4_common as common


MOVIE = Path(
    "~/Downloads/ABL/movies/go_to_end/LEVEL15.movie.json")
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
        "ce573bb375b6c590529dc048d838bbc2f85e6c227a724fa11b711506dffb1256",
    "movie_bytes": 23911415,
    "movie_frames": 33268,
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

EARLY_TARGET = 1000
FINAL_TARGET = EXPECTED["movie_frames"]
FINALE_C_CALL = "0x80050284"
FINALE_D_CALL = "0x8005036c"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load_client() -> Any:
    spec = importlib.util.spec_from_file_location(
        "phase4_fmv_finale_route_debug_client", CLIENT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load debugger client: {CLIENT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _method_present(capabilities: dict, method: str) -> bool:
    methods = capabilities.get("methods") or {}
    if isinstance(methods, dict):
        return method in methods
    return any(
        (row.get("name") if isinstance(row, dict) else row) == method
        for row in methods)


def _trace(client: Any, *, target: int, address: str, label: str,
           register_filter: dict | None = None) -> dict:
    params: dict[str, Any] = {
        "path": str(MOVIE),
        "frame": target,
        "ranges": [{
            "start": address, "end": address, "label": label, "max_pcs": 4,
        }],
    }
    if register_filter:
        params["filter"] = {"registers": register_filter}
    result = client.call("movie.traceToFrame", params, timeout=1800)
    comparison = result.get("comparison") or {}
    _require(
        comparison.get("cycle_neutral") is True and
        all(comparison.get(key) is True for key in (
            "same_ram", "same_registers", "same_cycle", "same_frame")),
        f"{label}: cached-interpreter comparison diverged")
    coverage = result.get("coverage") or []
    _require(
        len(coverage) == 1 and
        (coverage[0].get("coverage") or {}).get("truncated") is False,
        f"{label}: exact-PC coverage is absent or truncated")
    movie = client.call("movie.status", {})
    complete_consumption = target == EXPECTED["movie_frames"]
    common_movie_identity = (
        movie.get("truncated") is False and
        movie.get("frame_count") == EXPECTED["movie_frames"] and
        (movie.get("start_state") or {}).get("from_boot") is True)
    if complete_consumption:
        _require(
            common_movie_identity and
            movie.get("playing") is False and
            movie.get("playback_index") == 0 and
            movie.get("reproducible") is False and
            result.get("target_frame") == EXPECTED["movie_frames"] and
            (result.get("control") or {}).get("movie_frame") == 0 and
            (result.get("instrumented") or {}).get("movie_frame") == 0,
            f"{label}: final input sample was not completely consumed")
    else:
        _require(
            common_movie_identity and
            movie.get("reproducible") is True and
            movie.get("playing") is True and
            movie.get("playback_index") == target,
            f"{label}: recorded boot anchor was not retained")
    return {
        "target_frame": target,
        "register_filter": register_filter,
        "complete_consumption": complete_consumption,
        "trace": result,
        "movie_status": movie,
    }


def _cleanup(client: Any) -> list[dict]:
    outcomes = []
    for method, params in (
            ("debugger.clearBreakpoints", {}),
            ("accessLog.clear", {}),
            ("execTrace.clear", {}),
            ("functionTrace.stop", {}),
            ("functionTrace.clear", {}),
            ("movie.stopPlayback", {}),
            ("movie.clear", {}),
            ("emulator.clearControllerState", {"port": 0}),
            ("emulator.setTurbo", {"enabled": False}),
            ("emulator.setFastForward", {"enabled": False})):
        try:
            outcomes.append({
                "method": method, "ok": True,
                "result": client.call(method, params),
            })
        except Exception as exc:
            outcomes.append({
                "method": method, "ok": False, "error": str(exc),
            })
    return outcomes


def collect(port: int, token: str) -> dict:
    for label, path, digest in (
            ("movie", MOVIE, EXPECTED["movie_sha256"]),
            ("cue", CUE, EXPECTED["cue_sha256"]),
            ("bin", BIN, EXPECTED["bin_sha256"])):
        _require(
            path.is_file() and common.sha256(path) == digest,
            f"{label} fixture identity drifted")
    _require(
        MOVIE.stat().st_size == EXPECTED["movie_bytes"],
        "movie size drifted")
    movie_document = common.load_json(MOVIE)
    _require(
        movie_document.get("format") == "DuckStationInputMovie" and
        movie_document.get("version") == 3 and
        len(movie_document.get("frames") or []) ==
        EXPECTED["movie_frames"] and
        (movie_document.get("start_state") or {}).get("from_boot") is True,
        "movie metadata drifted")

    module = _load_client()
    client = module.DebuggerClient("127.0.0.1", port, "ws")
    client.authenticate(token)
    client.transport.sock.settimeout(1800)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.capabilities", "debugger.status",
        "debugger.clearBreakpoints", "emulator.getMediaInfo",
        "movie.traceToFrame", "movie.status", "movie.stopPlayback",
        "movie.clear", "capture.atomic", "scenario.runBatch",
        "scenario.loadStateAndRun", "scenario.bootAndRun",
        "provenanceLog.start", "provenanceLog.get",
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
        Path(str(status.get("game_path") or "")).resolve() == CUE.resolve(),
        f"debugger status media identity drifted: {status}")
    _require(
        media.get("has_media") is True and
        media.get("game_serial") == "SCUS-94288" and
        Path(str(media.get("path") or "")).resolve() == CUE.resolve(),
        f"mounted media identity drifted: {media}")
    media["verified_cue_sha256"] = common.sha256(CUE)
    media["verified_track_sha256"] = common.sha256(BIN)

    cleanup: list[dict] = []
    try:
        early_alias = _trace(
            client, target=EARLY_TARGET, address=FINALE_C_CALL,
            label="bare_pc_alias_probe")
        early_exact = _trace(
            client, target=EARLY_TARGET, address=FINALE_C_CALL,
            label="finale_lev15c_selector_40_early",
            register_filter={"a0": "0x00000028"})
        finale_c = _trace(
            client, target=FINAL_TARGET, address=FINALE_C_CALL,
            label="finale_lev15c_selector_40_full",
            register_filter={"a0": "0x00000028"})
        finale_d = _trace(
            client, target=FINAL_TARGET, address=FINALE_D_CALL,
            label="all_levels_complete_lev15d_full")
    finally:
        cleanup = _cleanup(client)

    _require(
        all(row.get("ok") is True for row in cleanup),
        "instrumentation/controller cleanup failed")
    return {
        "schema": "abl-phase4-fmv-finale-route-probe-live/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": {
            "rpc": "movie.traceToFrame",
            "control":
                "internally matched cached-interpreter replay at each target",
            "bare_pc_limitation":
                "cold-boot address reuse requires the statically reconstructed "
                "a0=40 caller condition for LEV15C",
            "fallback_reason":
                "scenario.runBatch cannot express cycle-neutral exact-"
                "instruction register-filtered movie coverage",
            "complete_consumption_contract":
                "target frame_count so input sample frame_count-1 is applied; "
                "playback then stops and resets playback_index to zero",
        },
        "capabilities": capabilities,
        "initial_status": status,
        "mounted_media": media,
        "fixtures": {
            "movie": {
                "absolute_path": str(MOVIE),
                "sha256": common.sha256(MOVIE),
                "bytes": MOVIE.stat().st_size,
                "frame_count": EXPECTED["movie_frames"],
                "anchor": "from_boot",
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
        "early_bare_pc_alias": early_alias,
        "early_selector_filtered_control": early_exact,
        "full_finale_c_selector_filtered": finale_c,
        "full_finale_d_bare_pc": finale_d,
        "cleanup": cleanup,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.config_dir.is_absolute() or not str(
            args.config_dir).startswith("/var/tmp/"):
        raise SystemExit("--config-dir must be an absolute /var/tmp path")
    output = args.output.resolve()
    if common.ROOT == output or common.ROOT in output.parents:
        raise SystemExit("raw live output must remain outside Git")
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    document = collect(args.port, args.token)
    document["isolated_instance"] = {
        "config_dir": str(args.config_dir.resolve()),
        "port": args.port,
        "host": "127.0.0.1",
        "transport": "ws",
        "profile_recreated": True,
        "token_retained": False,
    }
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(f"PASS: LEVEL15 finale route classified -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
