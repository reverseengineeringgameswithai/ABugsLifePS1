#!/usr/bin/env python3
"""Declarative, isolated DuckStation scenario execution for ABL.

The first supported vertical slice is deliberately small: a cold-boot input movie,
an exact movie-frame trigger, typed memory assertions, and JSON/Markdown reports.
Additional trigger and evidence types are added behind the same phase model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DUCK = Path(os.environ.get("DUCKSTATION_DIR", Path.home() / "duckstation")).resolve()
CLIENT_DIR = DUCK / "scripts" / "debugger-client"
FORK_LAUNCHER = CLIENT_DIR / "launch_debugger_instance.sh"
REPRO_LAUNCHER = ROOT / "tools" / "launch_repro_playback.sh"
BINARY = DUCK / "build-release" / "bin" / "duckstation-qt"

REQUIRED_RUNTIME_METHODS = frozenset({
    # Session identity and media.
    "debugger.capabilities", "debugger.status", "emulator.getMediaInfo",
    # Cold-boot/movie path and typed execution used by declarative scenarios.
    "debugger.pause", "debugger.reset", "debugger.readMemory",
    "movie.load", "movie.startPlayback", "movie.status", "movie.stopPlayback",
    "emulator.advanceFrames", "emulator.advanceUntil", "emulator.pressButton",
    "emulator.captureFrame", "emulator.getStateInfo", "emulator.loadState",
    "emulator.setControllerState", "emulator.clearControllerState", "emulator.setTurbo",
    # Fail-closed cleanup/instrumentation methods.
    "debugger.clearBreakpoints", "accessLog.clear", "execTrace.clear",
    "functionTrace.stop", "functionTrace.clear",
})

sys.path.insert(0, str(CLIENT_DIR))
from duckstation_debug_client import DebuggerClient  # noqa: E402


class ScenarioError(RuntimeError):
    """A schema, lifecycle, identity, trigger, or assertion failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_runtime_capabilities(capabilities: Any, expected_binary: Path, *,
                                required_methods: set[str] | frozenset[str] = frozenset(),
                                require_api_schema: bool = False) -> dict[str, Any]:
    """Bind an authenticated RPC server to the executable and method schema in use."""
    if not isinstance(capabilities, dict):
        raise ScenarioError("runtime capabilities response is not an object")
    binary = capabilities.get("binary")
    if not isinstance(binary, dict):
        raise ScenarioError("runtime binary identity is missing")
    expected_path = expected_binary.resolve()
    try:
        actual_path = Path(str(binary.get("path", ""))).expanduser().resolve()
    except (OSError, ValueError) as exc:
        raise ScenarioError(f"runtime binary identity has an invalid path: {exc}") from exc
    expected_hash = sha256(expected_path)
    actual_hash = str(binary.get("sha256", "")).lower()
    if actual_path != expected_path or actual_hash != expected_hash:
        raise ScenarioError(
            "runtime binary identity mismatch: "
            f"expected {expected_path} {expected_hash}, got {actual_path} {actual_hash or '<missing>'}")

    methods = capabilities.get("methods")
    method_count = capabilities.get("method_count")
    if not isinstance(methods, dict):
        raise ScenarioError("runtime capability method inventory is missing")
    if isinstance(method_count, bool) or not isinstance(method_count, (int, float)) \
            or int(method_count) != method_count or int(method_count) != len(methods):
        raise ScenarioError(
            f"runtime capability method count mismatch: declared {method_count!r}, inventory {len(methods)}")
    missing = sorted(set(required_methods) - set(methods))
    if missing:
        raise ScenarioError("runtime capability inventory is missing required methods: " + ", ".join(missing))

    api = capabilities.get("api")
    schema_coverage = capabilities.get("schema_coverage")
    if require_api_schema:
        if not isinstance(api, dict) or any(not api.get(key) for key in
                                            ("name", "version", "schema_version", "jsonrpc")):
            raise ScenarioError("runtime capability API/schema identity is incomplete")
        if api.get("jsonrpc") != "2.0":
            raise ScenarioError(f"runtime capability JSON-RPC schema is unsupported: {api.get('jsonrpc')!r}")
        if not isinstance(schema_coverage, dict) or not schema_coverage.get(
                "method_inventory_complete"):
            raise ScenarioError("runtime capability method inventory is not declared complete")
        malformed = sorted(name for name, schema in methods.items()
                           if not isinstance(schema, dict)
                           or not {"params", "result", "scenario_execution_policy"} <= set(schema))
        if malformed:
            raise ScenarioError("runtime capability method schema is incomplete: " + ", ".join(malformed[:8]))

    methods_sha256 = hashlib.sha256(
        json.dumps(methods, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "verified": True,
        "api": api,
        "source": capabilities.get("source"),
        "binary": binary,
        "method_count": len(methods),
        "method_names": sorted(methods),
        "methods_sha256": methods_sha256,
        "required_methods": sorted(required_methods),
        "schema_coverage": schema_coverage,
        "scenario_execution_gate": capabilities.get("scenario_execution_gate"),
    }


def parse_int(value: Any, field: str = "value") -> int:
    if isinstance(value, bool):
        raise ScenarioError(f"{field} must be an integer, not boolean")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError as exc:
            raise ScenarioError(f"{field} is not an integer: {value!r}") from exc
    raise ScenarioError(f"{field} must be an integer or 0x-prefixed string")


def resolve_path(value: str | os.PathLike[str], *, base: Path = ROOT) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(expanded)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def load_scenario(path: Path) -> dict[str, Any]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ScenarioError(f"cannot load scenario {path}: {exc}") from exc
    validate_scenario(doc, path)
    return doc


def validate_scenario(doc: Any, source: Path | None = None) -> None:
    where = f" in {source}" if source else ""
    if not isinstance(doc, dict):
        raise ScenarioError(f"scenario{where} must be a mapping")
    if doc.get("schema_version") != 1:
        raise ScenarioError(f"scenario{where} needs schema_version: 1")
    if not isinstance(doc.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", doc["id"]):
        raise ScenarioError(f"scenario{where} has an invalid id")
    target = doc.get("target")
    if not isinstance(target, dict) or not target.get("disc") or not target.get("expected_serial"):
        raise ScenarioError(f"scenario{where} target needs disc and expected_serial")
    launch = doc.get("launch", {})
    if launch.get("profile", "repro") not in {"repro", "generic"}:
        raise ScenarioError(f"scenario{where} launch.profile must be repro or generic")
    execution_mode = launch.get("execution_mode")
    if execution_mode is not None:
        if execution_mode not in {"Interpreter", "CachedInterpreter", "Recompiler"}:
            raise ScenarioError(f"scenario{where} launch.execution_mode is unsupported")
        if launch.get("profile", "repro") != "repro":
            raise ScenarioError(
                f"scenario{where} launch.execution_mode currently requires profile: repro")
    playback = doc.get("playback")
    anchor = doc.get("anchor")
    if playback is not None and (not isinstance(playback, dict) or not playback.get("movie")):
        raise ScenarioError(f"scenario{where} playback must declare movie")
    if isinstance(playback, dict):
        neutral_frames = parse_int(playback.get("preplay_neutral_frames", 0),
                                   "playback.preplay_neutral_frames")
        if neutral_frames < 0:
            raise ScenarioError(f"scenario{where} playback.preplay_neutral_frames must be non-negative")
        if neutral_frames and not playback.get("pause_before_start", False):
            raise ScenarioError(
                f"scenario{where} preplay_neutral_frames requires pause_before_start: true")
    if playback is None:
        if not isinstance(anchor, dict) or anchor.get("type") != "save_state" or not anchor.get("path"):
            raise ScenarioError(f"scenario{where} needs playback.movie or a save_state anchor")
    phases = doc.get("phases")
    if not isinstance(phases, list) or not phases:
        raise ScenarioError(f"scenario{where} needs at least one phase")
    phase_ids: set[str] = set()
    assertion_ids: set[str] = set()
    for phase in phases:
        if not isinstance(phase, dict) or not phase.get("id"):
            raise ScenarioError(f"scenario{where} phase needs an id")
        if phase["id"] in phase_ids:
            raise ScenarioError(f"scenario{where} duplicate phase id {phase['id']!r}")
        phase_ids.add(phase["id"])
        trigger = phase.get("trigger")
        trigger_types = {"movie_frame", "movie_frame_realtime", "emulator_frame", "memory", "register", "pc",
                         "breakpoint", "gpu", "audio", "rpc_poll"}
        if not isinstance(trigger, dict) or trigger.get("type") not in trigger_types:
            raise ScenarioError(f"scenario{where} phase {phase['id']} has unsupported trigger.type")
        if trigger["type"] in {"movie_frame", "movie_frame_realtime"} and playback is None:
            raise ScenarioError(f"scenario{where} movie frame trigger needs playback.movie")
        if trigger["type"] in {"movie_frame", "movie_frame_realtime", "emulator_frame"}:
            if parse_int(trigger.get("target"), "trigger.target") < 0:
                raise ScenarioError(f"scenario{where} phase {phase['id']} has negative frame target")
        for action_key in ("before", "after"):
            actions = phase.get(action_key, [])
            if not isinstance(actions, list) or any(not isinstance(a, dict) or not a.get("type") for a in actions):
                raise ScenarioError(f"scenario{where} phase {phase['id']} {action_key} must be typed actions")
        captures = phase.get("captures", [])
        if not isinstance(captures, list) or any(not isinstance(c, dict) or not c.get("type") for c in captures):
            raise ScenarioError(f"scenario{where} phase {phase['id']} captures must be typed declarations")
        assertions = phase.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            raise ScenarioError(f"scenario{where} phase {phase['id']} needs assertions")
        for assertion in assertions:
            assertion_types = {"memory", "register", "function_hit_count", "access_hit_count", "exec_hit_count",
                               "rpc", "capture", "render_diff"}
            if not isinstance(assertion, dict) or assertion.get("type") not in assertion_types:
                raise ScenarioError(f"scenario{where} phase {phase['id']} has unsupported assertion type")
            aid = assertion.get("id")
            if not isinstance(aid, str) or not aid or aid in assertion_ids:
                raise ScenarioError(f"scenario{where} has missing/duplicate assertion id {aid!r}")
            assertion_ids.add(aid)
            if assertion["type"] == "memory":
                parse_int(assertion.get("address"), f"assertion {aid} address")
                if assertion.get("width") not in {"u8", "s8", "u16", "s16", "u32", "s32"}:
                    raise ScenarioError(f"assertion {aid} has unsupported width")
            if assertion.get("op", "eq") not in {"eq", "ne", "lt", "le", "gt", "ge", "between"}:
                raise ScenarioError(f"assertion {aid} has unsupported comparison")
            if assertion.get("op", "eq") == "between":
                expected = assertion.get("expected")
                if not isinstance(expected, list) or len(expected) != 2:
                    raise ScenarioError(f"assertion {aid} between expects [low, high]")
                parse_int(expected[0], f"assertion {aid} expected low")
                parse_int(expected[1], f"assertion {aid} expected high")
            elif assertion["type"] not in {"rpc", "capture"}:
                parse_int(assertion.get("expected"), f"assertion {aid} expected")


def compare(actual: Any, op: str, expected: Any) -> bool:
    if op == "between":
        low, high = (parse_int(v) for v in expected)
        return low <= actual <= high
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    value = parse_int(expected)
    return {
        "lt": actual < value,
        "le": actual <= value,
        "gt": actual > value,
        "ge": actual >= value,
    }[op]


def format_expected(op: str, expected: Any) -> str:
    if op == "between":
        return f"[{parse_int(expected[0])}, {parse_int(expected[1])}]"
    return json.dumps(expected) if isinstance(expected, (dict, list, str, bool)) else str(expected)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run_text(command: list[str], cwd: Path = ROOT) -> str:
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return proc.stdout.strip()


def _disc_files(cue: Path) -> list[Path]:
    files = [cue]
    if cue.suffix.lower() == ".cue":
        for line in cue.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r'^\s*FILE\s+"([^"]+)"', line, re.I)
            if match:
                candidate = (cue.parent / match.group(1)).resolve()
                if candidate.is_file() and candidate not in files:
                    files.append(candidate)
    return files


def get_path(value: Any, path: str | None) -> Any:
    """Read a dotted key/index path from an RPC/capture result."""
    current = value
    if not path:
        return current
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ScenarioError(f"result path {path!r} is missing at {part!r}")
    return current


@dataclass
class IsolatedLifecycle:
    disc: Path
    profile: str
    report: dict[str, Any]
    execution_mode: str | None = None
    config_dir: Path | None = None
    port: int | None = None
    token: str | None = None
    pid: int | None = None
    client: Any = None
    started: bool = False

    def start(self) -> Any:
        self.config_dir = Path(tempfile.mkdtemp(prefix="abl-ps1-scenario-", dir="/tmp")).resolve()
        self.port = _free_port()
        # Keep the token an unambiguous argv value for both launchers.  A raw
        # urlsafe token can begin with ``-`` and be parsed as another option by
        # the debugger client's argument parser, leaving a live but unverifiable
        # instance behind after its readiness probe fails.
        self.token = "abl_" + secrets.token_urlsafe(24)
        launcher = REPRO_LAUNCHER if self.profile == "repro" else FORK_LAUNCHER
        command = [str(launcher)]
        if self.profile == "generic":
            command.append("start")
        elif self.execution_mode is not None:
            command += ["--execution-mode", self.execution_mode]
        command += [
            "--config-dir", str(self.config_dir), "--port", str(self.port),
            "--token", self.token, "--disc", str(self.disc),
        ]
        self.report["lifecycle"] = {
            "profile": self.profile,
            "execution_mode": self.execution_mode,
            "config_dir": str(self.config_dir),
            "port": self.port,
            "token_sha256": hashlib.sha256(self.token.encode()).hexdigest(),
            "launcher": str(launcher),
            "launch_command_redacted": ["<token>" if x == self.token else x for x in command],
            "reused": False,
            "cleanup": {"attempted": False, "success": False},
        }
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        self.report["lifecycle"]["launch_stdout"] = proc.stdout.replace(self.token, "<token>").strip()
        self.report["lifecycle"]["launch_stderr"] = proc.stderr.replace(self.token, "<token>").strip()
        if proc.returncode != 0:
            raise ScenarioError(f"isolated DuckStation launch failed ({proc.returncode}): {proc.stderr or proc.stdout}")
        pidfile = self.config_dir / "instance.pid"
        if not pidfile.is_file():
            raise ScenarioError(f"launcher reported success without {pidfile}")
        self.pid = int(pidfile.read_text().strip())
        self.report["lifecycle"]["pid"] = self.pid
        self.started = True
        self.client = DebuggerClient("127.0.0.1", self.port, "ws")
        self.client.authenticate(self.token)
        return self.client

    def cleanup(self) -> None:
        if "lifecycle" not in self.report:
            return
        cleanup = self.report["lifecycle"]["cleanup"]
        cleanup["attempted"] = True
        errors: list[str] = []
        if self.client is not None:
            for method, params in (
                ("debugger.pause", {}),
                ("debugger.clearBreakpoints", {}),
                ("accessLog.clear", {}),
                ("execTrace.clear", {}),
                ("functionTrace.stop", {}),
                ("functionTrace.clear", {}),
                ("movie.stopPlayback", {}),
                ("emulator.clearControllerState", {"port": 0}),
                ("emulator.setTurbo", {"enabled": False}),
            ):
                try:
                    self.client.call(method, params, timeout=5)
                except Exception as exc:  # best-effort cleanup is reported, then PID-scoped stop runs
                    errors.append(f"{method}: {exc}")
        if self.started and self.config_dir is not None:
            proc = subprocess.run(
                [str(FORK_LAUNCHER), "stop", "--config-dir", str(self.config_dir)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            cleanup["stop_stdout"] = proc.stdout.strip()
            cleanup["stop_stderr"] = proc.stderr.strip()
            cleanup["stop_returncode"] = proc.returncode
            if proc.returncode != 0:
                errors.append(f"launcher stop returned {proc.returncode}")
        cleanup["errors"] = errors
        cleanup["success"] = self.started and not errors and not (self.config_dir / "instance.pid").exists()


class ScenarioRunner:
    def __init__(self, scenario_path: Path, scenario: dict[str, Any], *, disc_override: Path | None = None,
                 expected_overrides: dict[str, int] | None = None,
                 evidence_dir: Path | None = None):
        self.scenario_path = scenario_path
        self.scenario = scenario
        self.disc = disc_override or resolve_path(scenario["target"]["disc"])
        self.movie = resolve_path(scenario["playback"]["movie"]) if scenario.get("playback") else None
        self.save_state = resolve_path(scenario["anchor"]["path"]) if scenario.get("anchor") else None
        self.expected_overrides = expected_overrides or {}
        self.requested_evidence_dir = evidence_dir.resolve() if evidence_dir is not None else None
        self.captures: dict[str, Any] = {}
        self.instrumentation: dict[str, Any] = {}
        self.evidence_dir: Path | None = None
        self.report: dict[str, Any] = {
            "schema_version": 1,
            "scenario_id": scenario["id"],
            "scenario_path": str(scenario_path),
            "started_at": utc_now(),
            "status": "error",
            "phases": [],
            "errors": [],
        }

    def _record_environment(self) -> None:
        inputs = [(self.disc, "disc"), (BINARY, "duckstation_binary")]
        if self.movie is not None:
            inputs.append((self.movie, "movie"))
        if self.save_state is not None:
            inputs.append((self.save_state, "save_state"))
        for path, label in inputs:
            if not path.is_file():
                raise ScenarioError(f"{label} does not exist: {path}")
        disc_files = _disc_files(self.disc)
        self.report["inputs"] = {
            "disc": [{"path": str(p), "size": p.stat().st_size, "sha256": sha256(p)} for p in disc_files],
            "scenario": {"path": str(self.scenario_path),
                         "size": self.scenario_path.stat().st_size,
                         "sha256": sha256(self.scenario_path)},
        }
        if self.movie is not None:
            self.report["inputs"]["movie"] = {
                "path": str(self.movie), "size": self.movie.stat().st_size, "sha256": sha256(self.movie)}
        if self.save_state is not None:
            self.report["inputs"]["save_state"] = {
                "path": str(self.save_state), "size": self.save_state.stat().st_size,
                "sha256": sha256(self.save_state)}
        self.report["source"] = {
            "repository_head": _run_text(["git", "rev-parse", "HEAD"]),
            "repository_status": _run_text(["git", "status", "--short"]).splitlines(),
            "scenario_runner": str(Path(__file__).resolve()),
            "scenario_runner_sha256": sha256(Path(__file__).resolve()),
            "debugger_client": str((CLIENT_DIR / "duckstation_debug_client.py").resolve()),
            "debugger_client_sha256": sha256(CLIENT_DIR / "duckstation_debug_client.py"),
            "launcher": str((REPRO_LAUNCHER if self.scenario.get("launch", {}).get(
                "profile", "repro") == "repro" else FORK_LAUNCHER).resolve()),
            "launcher_sha256": sha256(REPRO_LAUNCHER if self.scenario.get(
                "launch", {}).get("profile", "repro") == "repro" else FORK_LAUNCHER),
            "duckstation_head": _run_text(["git", "-C", str(DUCK), "rev-parse", "HEAD"]),
            "duckstation_status": _run_text(["git", "-C", str(DUCK), "status", "--short"]).splitlines(),
            "duckstation_binary": str(BINARY),
            "duckstation_binary_sha256": sha256(BINARY),
        }

    def _read_memory(self, client: Any, assertion: dict[str, Any]) -> int:
        width = assertion["width"]
        size = int(width[1:]) // 8
        address = parse_int(assertion["address"], "assertion address")
        response = client.call(
            "debugger.readMemory", {"address": f"0x{address:08x}", "length": size}, timeout=10)
        raw = bytes.fromhex(response["hex"])
        return int.from_bytes(raw, "little", signed=width.startswith("s"))

    def _perform_action(self, client: Any, action: dict[str, Any]) -> dict[str, Any]:
        kind = action["type"]
        name = action.get("id") or action.get("as") or kind
        if kind == "rpc":
            method, params = action["method"], action.get("params", {})
        elif kind == "breakpoint_add":
            method, params = "debugger.addBreakpoint", dict(action.get("params", {}))
            params.setdefault("address", action.get("address"))
            params.setdefault("type", action.get("breakpoint_type", "execute"))
            if "condition" in action:
                params["condition"] = action["condition"]
            if "actions" in action:
                params["actions"] = action["actions"]
        elif kind == "access_trace_start":
            method, params = "accessLog.addWatch", dict(action.get("params", {}))
            for key in ("address", "length"):
                if key in action:
                    params[key] = action[key]
            params.setdefault("type", action.get("access_type", "readwrite"))
        elif kind == "exec_trace_start":
            method, params = "execTrace.addWatch", dict(action.get("params", {}))
            if "pc" in action:
                params["pc"] = action["pc"]
            if "capture" in action:
                params["capture"] = action["capture"]
            params.setdefault("max_events", parse_int(action.get("max_events", 1024)))
            params.setdefault("stop_on_hit", bool(action.get("stop_on_hit", False)))
        elif kind == "function_trace_start":
            method, params = "functionTrace.start", dict(action.get("params", {}))
            if "functions" in action:
                params["functions"] = action["functions"]
        elif kind == "function_trace_stop":
            method, params = "functionTrace.stop", {}
        elif kind == "spu_trace_start":
            method, params = "spu.trace.start", action.get("params", {"clear": True})
        elif kind == "gpu_causality_start":
            method, params = "gpu.causality.start", action.get("params", {})
        elif kind == "trace_arm_when":
            method, params = "trace.armWhen", action.get("params", {})
        else:
            raise ScenarioError(f"unsupported action type: {kind}")
        result = client.call(method, params, timeout=float(action.get("timeout_seconds", 30)))
        record = {"id": name, "type": kind, "method": method, "params": params, "result": result}
        self.instrumentation[name] = result
        return record

    def _run_trigger(self, client: Any, trigger: dict[str, Any]) -> dict[str, Any]:
        kind = trigger["type"]
        timeout = float(trigger.get("timeout_seconds", 180))
        if kind == "movie_frame":
            target = parse_int(trigger["target"])
            return client.call(
                "movie.advanceToFrame",
                {"frame": target, "max_frames": parse_int(trigger.get("max_frames", target + 600))},
                timeout=timeout,
            )
        if kind == "movie_frame_realtime":
            target = parse_int(trigger["target"])
            max_frames = parse_int(trigger.get("max_frames", target + 600))
            interval = float(trigger.get("poll_interval_seconds", 0.002))
            if interval <= 0:
                raise ScenarioError("movie_frame_realtime poll_interval_seconds must be positive")
            start = client.call("movie.status", {}, timeout=10)
            start_index = parse_int(start["playback_index"])
            if target < start_index or target - start_index > max_frames:
                raise ScenarioError(
                    f"realtime target {target} outside start {start_index} + max_frames {max_frames}")
            deadline = time.monotonic() + timeout
            last = start
            client.call("debugger.resume", {}, timeout=10)
            try:
                while time.monotonic() < deadline:
                    last = client.call("movie.status", {}, timeout=10)
                    if parse_int(last["playback_index"]) >= target:
                        break
                    if not last.get("playing", False):
                        raise ScenarioError(f"movie stopped before realtime target {target}")
                    time.sleep(interval)
                else:
                    raise ScenarioError(f"realtime movie target {target} timed out")
            finally:
                client.call("debugger.pause", {}, timeout=10)
            status = client.call("debugger.status", {}, timeout=10)
            end_index = parse_int(last["playback_index"])
            if end_index - start_index > max_frames:
                raise ScenarioError(
                    f"realtime target overshot max_frames: {start_index} -> {end_index} > {max_frames}")
            return {
                "start_playback_index": start_index,
                "target_frame": target,
                "playback_index": end_index,
                "frames_advanced": end_index - start_index,
                "movie": last,
                "status": status,
                "realtime": True,
            }
        if kind == "emulator_frame":
            target = parse_int(trigger["target"])
            return client.call(
                "emulator.advanceToFrame",
                {"frame": target, "max_frames": parse_int(trigger.get("max_frames", 100000))},
                timeout=timeout,
            )
        if kind in {"memory", "register", "pc"}:
            condition = {"kind": kind, "op": trigger.get("op", "eq")}
            if kind == "memory":
                condition.update(address=f"0x{parse_int(trigger['address']):08x}",
                                 type=trigger.get("width", "u32"))
            elif kind == "register":
                condition["name"] = trigger["name"]
            if condition["op"] in {"eq", "ne", "lt", "le", "gt", "ge"}:
                condition["value"] = parse_int(trigger["value"])
            if condition["op"] == "stable":
                condition["frames"] = parse_int(trigger["frames"])
            return client.call(
                "emulator.advanceUntil",
                {"condition": condition, "max_frames": parse_int(trigger["max_frames"]),
                 "observe": bool(trigger.get("observe", False))}, timeout=timeout)
        if kind == "breakpoint":
            params = {"address": trigger["address"],
                      "type": trigger.get("breakpoint_type", "execute"), "enabled": True}
            for key in ("condition", "actions"):
                if key in trigger:
                    params[key] = trigger[key]
            added = client.call("debugger.addBreakpoint", params, timeout=10)
            try:
                advanced = client.call(
                    "emulator.advanceFrames", {"frames": parse_int(trigger["max_frames"])},
                    timeout=timeout)
                status = client.call("debugger.status", {}, timeout=10)
                return {"breakpoint": added, "advance": advanced, "status": status}
            finally:
                bp_id = added.get("id") or added.get("breakpoint_id")
                if bp_id is not None:
                    client.call("debugger.removeBreakpoint", {"id": bp_id}, timeout=10)
        if kind in {"gpu", "audio", "rpc_poll"}:
            method = trigger["method"]
            if kind == "gpu" and not method.startswith("gpu."):
                raise ScenarioError("gpu trigger method must start with gpu.")
            if kind == "audio" and not method.startswith("spu."):
                raise ScenarioError("audio trigger method must start with spu.")
            max_frames = parse_int(trigger["max_frames"])
            step = parse_int(trigger.get("step_frames", 1))
            advanced = 0
            last = None
            while advanced <= max_frames:
                last = client.call(method, trigger.get("params", {}), timeout=30)
                actual = get_path(last, trigger.get("path"))
                if compare(actual, trigger.get("op", "eq"), trigger.get("expected")):
                    return {"frames_advanced": advanced, "actual": actual, "result": last}
                if advanced == max_frames:
                    break
                amount = min(step, max_frames - advanced)
                client.call("emulator.advanceFrames", {"frames": amount}, timeout=30)
                advanced += amount
            raise ScenarioError(
                f"{kind} trigger did not satisfy {trigger.get('path')} "
                f"{trigger.get('op', 'eq')} {trigger.get('expected')!r} in {max_frames} frames")
        raise ScenarioError(f"unsupported trigger type: {kind}")

    def _capture(self, client: Any, declaration: dict[str, Any]) -> dict[str, Any]:
        kind = declaration["type"]
        name = declaration.get("id") or declaration.get("as")
        if not name:
            raise ScenarioError(f"capture type {kind} needs id/as")
        if kind == "atomic":
            method, params = "capture.atomic", declaration.get("params", {})
            result = client.call(method, params, timeout=float(declaration.get("timeout_seconds", 30)))
        elif kind == "rpc":
            method, params = declaration["method"], declaration.get("params", {})
            result = client.call(method, params, timeout=float(declaration.get("timeout_seconds", 30)))
        elif kind == "frame_snapshot":
            method, params = "gpu.captureFrameSnapshot", declaration.get("params", {})
            result = client.call(method, params, timeout=30)
        elif kind == "screenshot":
            assert self.evidence_dir is not None
            filename = declaration.get("filename", f"{name}.png")
            path = (self.evidence_dir / filename).resolve()
            if self.evidence_dir not in path.parents:
                raise ScenarioError("screenshot filename escapes the evidence directory")
            method, params = "emulator.captureFrame", {"path": str(path)}
            result = client.call(method, params, timeout=30)
            client.call("emulator.advanceFrames", {"frames": 1}, timeout=30)
            result = {"rpc": result, "path": str(path),
                      "sha256": sha256(path) if path.is_file() else None}
        else:
            raise ScenarioError(f"unsupported capture type: {kind}")
        self.captures[name] = result
        return {"id": name, "type": kind, "method": method, "params": params, "result": result}

    def _assertion(self, client: Any, assertion: dict[str, Any]) -> dict[str, Any]:
        kind = assertion["type"]
        expected = self.expected_overrides.get(assertion["id"], assertion["expected"])
        op = assertion.get("op", "eq")
        source: dict[str, Any] = {}
        if kind == "memory":
            actual = self._read_memory(client, assertion)
            source = {"address": f"0x{parse_int(assertion['address']):08x}", "width": assertion["width"]}
        elif kind == "register":
            response = client.call("debugger.getRegister", {"name": assertion["name"]}, timeout=10)
            raw = response.get("value", response.get("value_u32", response.get("hex")))
            actual = parse_int(raw, f"register {assertion['name']}")
            source = {"register": assertion["name"], "response": response}
        elif kind == "function_hit_count":
            response = client.call("functionTrace.get", assertion.get("params", {}), timeout=30)
            events = response.get("events", [])
            function = assertion.get("function")
            event_kind = assertion.get("event")
            if function is not None:
                events = [e for e in events if function in
                          {e.get("function"), e.get("symbol"), e.get("address"), e.get("address_hex")}]
            if event_kind is not None:
                events = [e for e in events if e.get("event") == event_kind or e.get("type") == event_kind]
            actual = len(events)
            source = {"total_events": len(response.get("events", [])), "truncated": response.get("truncated", False)}
        elif kind == "access_hit_count":
            watch = assertion.get("watch")
            watch_result = self.instrumentation.get(watch, {})
            watch_id = assertion.get("watch_id", watch_result.get("watch_id", watch_result.get("id")))
            if watch_id is None:
                raise ScenarioError(f"access assertion {assertion['id']} cannot resolve watch id {watch!r}")
            response = client.call("accessLog.get", {"watch_id": watch_id, "offset": 0,
                                                     "limit": parse_int(assertion.get("limit", 10000))}, timeout=30)
            actual = int(response.get("hit_count", response.get("total", len(response.get("events", [])))))
            source = {"watch_id": watch_id, "truncated": response.get("truncated", False)}
        elif kind == "exec_hit_count":
            watch = assertion.get("watch")
            watch_result = self.instrumentation.get(watch, {})
            watch_id = assertion.get("watch_id", watch_result.get("watch_id", watch_result.get("id")))
            if watch_id is None:
                raise ScenarioError(f"exec assertion {assertion['id']} cannot resolve watch id {watch!r}")
            response = client.call("execTrace.get", {"watch_id": watch_id, "offset": 0,
                                                    "limit": parse_int(assertion.get("limit", 10000))}, timeout=30)
            actual = int(response.get("hit_count", response.get("total", len(response.get("events", [])))))
            source = {"watch_id": watch_id, "truncated": response.get("truncated", False)}
        elif kind == "rpc":
            response = client.call(assertion["method"], assertion.get("params", {}),
                                   timeout=float(assertion.get("timeout_seconds", 30)))
            actual = get_path(response, assertion.get("path"))
            source = {"method": assertion["method"], "path": assertion.get("path")}
        elif kind == "capture":
            capture = self.captures.get(assertion["capture"])
            if capture is None:
                raise ScenarioError(f"unknown capture {assertion['capture']!r}")
            actual = get_path(capture, assertion.get("path"))
            source = {"capture": assertion["capture"], "path": assertion.get("path")}
        elif kind == "render_diff":
            capture = self.captures.get(assertion["against"])
            if not isinstance(capture, dict):
                raise ScenarioError(f"render assertion needs frame snapshot {assertion['against']!r}")
            snapshot_id = capture.get("snapshotId", capture.get("snapshot_id"))
            response = client.call("gpu.diffCurrentFrame",
                                   {"against": snapshot_id, **assertion.get("params", {})}, timeout=30)
            actual = get_path(response, assertion.get("path", "metrics.changedPixels"))
            source = {"against": assertion["against"], "snapshot_id": snapshot_id,
                      "path": assertion.get("path", "metrics.changedPixels")}
        else:
            raise ScenarioError(f"unsupported assertion type: {kind}")
        passed = compare(actual, op, expected)
        out = {"id": assertion["id"], "type": kind, "passed": passed, "op": op,
               "expected": expected, "expected_display": format_expected(op, expected),
               "actual": actual, "description": assertion.get("description", ""), **source}
        if isinstance(actual, int):
            out["actual_hex"] = f"0x{actual & 0xffffffff:x}"
        return out

    def run(self) -> dict[str, Any]:
        lifecycle: IsolatedLifecycle | None = None
        try:
            self._record_environment()
            launch = self.scenario.get("launch", {})
            lifecycle = IsolatedLifecycle(
                self.disc, launch.get("profile", "repro"), self.report,
                execution_mode=launch.get("execution_mode"))
            client = lifecycle.start()
            # This is the first authenticated RPC call. It binds the process serving
            # this connection, not merely the expected binary path hashed pre-launch.
            capabilities = client.call("debugger.capabilities", {}, timeout=10)
            self.report["runtime_capabilities"] = verify_runtime_capabilities(
                capabilities, BINARY, required_methods=REQUIRED_RUNTIME_METHODS,
                require_api_schema=True)
            # Keep file evidence outside the disposable DuckStation config when the
            # caller supplies a report-owned directory. The isolated launcher removes
            # its config on cleanup, which would otherwise leave dead screenshot paths
            # in an otherwise valid receipt.
            self.evidence_dir = self.requested_evidence_dir or lifecycle.config_dir / "evidence"
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
            self.report["evidence_dir"] = str(self.evidence_dir)
            status = client.call("debugger.status", {}, timeout=10)
            media = client.call("emulator.getMediaInfo", {}, timeout=10)
            self.report["identity"] = {"status": status, "media": media}
            expected_serial = self.scenario["target"]["expected_serial"]
            if status.get("game_serial") != expected_serial:
                raise ScenarioError(
                    f"media identity mismatch: expected {expected_serial}, got {status.get('game_serial')!r}")

            if self.movie is not None:
                movie_doc = json.loads(self.movie.read_text(encoding="utf-8"))
                if movie_doc.get("game_serial") != expected_serial:
                    raise ScenarioError(
                        f"movie serial mismatch: expected {expected_serial}, got {movie_doc.get('game_serial')!r}")
                playback_cfg = self.scenario["playback"]
                pre_reset_turbo = None
                if playback_cfg.get("turbo_before_reset", False):
                    pre_reset_turbo = client.call("emulator.setTurbo", {"enabled": True}, timeout=10)
                reset = None
                if playback_cfg.get("reset_before_start", False):
                    reset = client.call("debugger.reset", {}, timeout=30)
                paused_for_movie = None
                if playback_cfg.get("pause_before_start", False):
                    # Opt-in deterministic from-boot attachment. Older movies may have
                    # been recorded after a known running-guest delay; reproduce that
                    # delay explicitly with preplay_neutral_frames below.
                    paused_for_movie = client.call("debugger.pause", {}, timeout=10)
                loaded = client.call("movie.load", {"path": str(self.movie)}, timeout=10)
                neutral_frames = parse_int(playback_cfg.get("preplay_neutral_frames", 0))
                neutral_advance = None
                if neutral_frames:
                    if paused_for_movie is None:
                        raise ScenarioError("preplay_neutral_frames requires pause_before_start:true")
                    neutral_advance = client.call(
                        "emulator.advanceFrames", {"frames": neutral_frames}, timeout=60)
                started = client.call("movie.startPlayback", {
                    "start_frame": parse_int(playback_cfg.get("start_frame", 0)),
                    "load_start_state": bool(playback_cfg.get("load_start_state", True)),
                }, timeout=30)
                self.report["playback"] = {"movie_metadata": movie_doc.get("start_state"),
                                           "turbo_before_reset": pre_reset_turbo,
                                           "reset_before_start": reset,
                                           "paused_for_movie": paused_for_movie,
                                           "preplay_neutral_frames": neutral_frames,
                                           "preplay_neutral_advance": neutral_advance,
                                           "load": loaded, "start": started}
                if playback_cfg.get("require_reproducible", True) and not started.get("reproducible"):
                    raise ScenarioError("movie playback did not report reproducible:true")
            else:
                assert self.save_state is not None
                info = client.call("emulator.getStateInfo", {"path": str(self.save_state)}, timeout=30)
                state_serial = info.get("game_serial") or info.get("serial")
                if state_serial and state_serial != expected_serial:
                    raise ScenarioError(
                        f"save-state serial mismatch: expected {expected_serial}, got {state_serial!r}")
                loaded = client.call("emulator.loadState", {
                    "path": str(self.save_state), "pause_after_load": True, "validate_disc": True}, timeout=60)
                self.report["anchor"] = {"type": "save_state", "info": info, "load": loaded}

            self.report["setup_actions"] = [
                self._perform_action(client, action) for action in self.scenario.get("setup", [])]

            all_passed = True
            for phase in self.scenario["phases"]:
                trigger = phase["trigger"]
                before = [self._perform_action(client, action) for action in phase.get("before", [])]
                trigger_result = self._run_trigger(client, trigger)
                client.call("debugger.pause", {}, timeout=10)
                trigger_status = client.call("debugger.status", {}, timeout=10)
                movie_status = client.call("movie.status", {}, timeout=10) if self.movie is not None else None
                phase_report: dict[str, Any] = {
                    "id": phase["id"],
                    "before": before,
                    "trigger": {"declaration": trigger, "result": trigger_result,
                                "status": trigger_status, "movie_status": movie_status},
                    "captures": [],
                    "assertions": [],
                }
                for declaration in phase.get("captures", []):
                    phase_report["captures"].append(self._capture(client, declaration))
                for assertion in phase["assertions"]:
                    result = self._assertion(client, assertion)
                    all_passed &= result["passed"]
                    phase_report["assertions"].append(result)
                phase_report["after"] = [
                    self._perform_action(client, action) for action in phase.get("after", [])]
                self.report["phases"].append(phase_report)
            self.report["status"] = "passed" if all_passed else "failed"
        except Exception as exc:
            self.report["errors"].append(f"{type(exc).__name__}: {exc}")
            self.report["status"] = "error"
        finally:
            if lifecycle is not None:
                lifecycle.cleanup()
                cleanup = self.report.get("lifecycle", {}).get("cleanup", {})
                if lifecycle.started and not cleanup.get("success"):
                    self.report["errors"].append("LifecycleError: owned instance cleanup did not succeed")
                    self.report["status"] = "error"
            self.report["finished_at"] = utc_now()
        return self.report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# Scenario report: {report['scenario_id']}", "", f"Status: **{report['status'].upper()}**",
             "", f"Started: `{report.get('started_at')}`  ", f"Finished: `{report.get('finished_at')}`", ""]
    identity = report.get("identity", {}).get("status", {})
    if identity:
        lines += ["## Identity", "", f"- Serial: `{identity.get('game_serial')}`",
                  f"- Title: `{identity.get('game_title')}`", f"- Frame: `{identity.get('frame_number', identity.get('frame'))}`", ""]
    for phase in report.get("phases", []):
        lines += [f"## Phase `{phase['id']}`", ""]
        for assertion in phase.get("assertions", []):
            mark = "PASS" if assertion["passed"] else "FAIL"
            source = assertion.get("address") or assertion.get("register") or assertion.get("method") \
                or assertion.get("capture") or assertion.get("watch_id") or assertion.get("against") \
                or assertion["type"]
            width = f" ({assertion['width']})" if assertion.get("width") else ""
            actual_hex = f" (`{assertion['actual_hex']}`)" if assertion.get("actual_hex") else ""
            lines.append(
                f"- **{mark}** `{assertion['id']}` from `{source}`{width}: "
                f"expected `{assertion['op']} {assertion['expected_display']}`, got "
                f"`{assertion['actual']}`{actual_hex}.")
        lines.append("")
    if report.get("errors"):
        lines += ["## Errors", ""] + [f"- {e}" for e in report["errors"]] + [""]
    cleanup = report.get("lifecycle", {}).get("cleanup", {})
    if cleanup:
        lines += ["## Isolation and cleanup", "",
                  f"- Config: `{report['lifecycle'].get('config_dir')}`",
                  f"- Port: `{report['lifecycle'].get('port')}`",
                  f"- PID-scoped cleanup: `{'success' if cleanup.get('success') else 'failed'}`", ""]
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = report["scenario_id"]
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path
