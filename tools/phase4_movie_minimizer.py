#!/usr/bin/env python3
"""Hierarchically minimize DuckStation movies/scenarios with fail-closed replay receipts."""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/phase4_movie_minimizer.yaml"
PILOT_PATH = ROOT / "analysis/phase4_movie_minimizer_pilot.json"
MOVIE_FORMAT = "DuckStationInputMovie"
RECEIPT_SCHEMA = "abl-phase4-movie-minimizer-replay/1"
PILOT_SCHEMA = "abl-phase4-movie-minimizer-pilot/1"
HEX64 = re.compile(r"[0-9a-f]{64}")


class MinimizerError(RuntimeError):
    """Invalid input, replay contract, or minimization outcome."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise MinimizerError(f"cannot load minimizer policy: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("schema") != \
            "abl-phase4-movie-minimizer-policy/1":
        raise MinimizerError("wrong movie-minimizer policy schema")
    if policy.get("emulator") != "DuckStation" or \
            policy.get("required_execution_mode") != "Interpreter" or \
            policy.get("required_replay_roles") != ["assertion", "control"]:
        raise MinimizerError("policy must require DuckStation Interpreter assertion/control")
    buttons = policy.get("buttons")
    axes = policy.get("axes")
    if not isinstance(buttons, list) or len(buttons) != 16 or len(set(buttons)) != 16 or \
            not isinstance(axes, list) or set(axes) != {"lx", "ly", "rx", "ry"} or \
            set(buttons) & set(axes):
        raise MinimizerError("policy controller surface is not the closed 16-button/4-axis set")
    if policy.get("axis_neutral") != 128 or \
            not isinstance(policy.get("default_max_evaluations"), int) or \
            policy["default_max_evaluations"] < 1 or policy.get("minimum_frames") != 1:
        raise MinimizerError("policy bounds are invalid")
    for key in ("allow_source_overwrite", "allow_repository_output"):
        if policy.get(key) is not False:
            raise MinimizerError(f"policy must keep {key} false")
    for key in ("preserve_anchor_class", "require_media_identity",
                "require_recreated_isolated_config", "require_control_for_every_candidate"):
        if policy.get(key) is not True:
            raise MinimizerError(f"policy must keep {key} true")
    return policy


def anchor_class(movie: dict[str, Any], scenario: dict[str, Any] | None) -> str:
    start = movie.get("start_state") or {}
    if start.get("from_boot") is True:
        return "cold_boot"
    if start.get("path"):
        return "save_state"
    anchor = (scenario or {}).get("anchor") or {}
    if anchor.get("type") == "save_state":
        return "save_state"
    return "cold_boot"


def validate_movie(movie: Any, policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(movie, dict) or movie.get("format") != MOVIE_FORMAT:
        raise MinimizerError(f"movie must use format {MOVIE_FORMAT}")
    if movie.get("version") not in {1, 2, 3}:
        raise MinimizerError("movie version must be 1, 2, or 3")
    frames = movie.get("frames")
    if not isinstance(frames, list) or len(frames) < int(policy["minimum_frames"]):
        raise MinimizerError("movie has no minimizable frames")
    buttons = set(policy["buttons"])
    axes = set(policy["axes"])
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict) or frame.get("frame") != index:
            raise MinimizerError("movie frames must be contiguous and zero-indexed")
        ports = frame.get("ports")
        if not isinstance(ports, dict):
            raise MinimizerError(f"frame {index}: ports must be a mapping")
        for port, state in ports.items():
            if not str(port).isdigit() or not isinstance(state, dict):
                raise MinimizerError(f"frame {index}: malformed port {port!r}")
            for key, value in state.items():
                if key in buttons and not isinstance(value, bool):
                    raise MinimizerError(f"frame {index}: button {key} is not boolean")
                if key in axes and (not isinstance(value, int) or isinstance(value, bool)
                                    or not 0 <= value <= 255):
                    raise MinimizerError(f"frame {index}: axis {key} is outside 0..255")
                if key not in buttons | axes:
                    raise MinimizerError(f"frame {index}: unknown controller field {key!r}")
    return copy.deepcopy(movie)


def load_movie(path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    try:
        return validate_movie(json.loads(path.read_text(encoding="utf-8")), policy)
    except (OSError, json.JSONDecodeError) as exc:
        raise MinimizerError(f"cannot load movie {path}: {exc}") from exc


def assertion_ids(scenario: dict[str, Any] | None) -> list[str]:
    if scenario is None:
        return []
    result: list[str] = []
    for phase in scenario.get("phases") or []:
        for assertion in phase.get("assertions") or []:
            value = assertion.get("id") if isinstance(assertion, dict) else None
            if not isinstance(value, str) or not value or value in result:
                raise MinimizerError("scenario has missing or duplicate assertion IDs")
            result.append(value)
    if not result:
        raise MinimizerError("scenario minimization requires immutable assertion IDs")
    return result


def load_scenario(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise MinimizerError(f"cannot load scenario {path}: {exc}") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("playback"), dict):
        raise MinimizerError("scenario needs a playback mapping")
    assertion_ids(doc)
    return doc


def neutral_state(state: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    buttons = set(policy["buttons"])
    axes = set(policy["axes"])
    neutral = int(policy["axis_neutral"])
    return {key: (False if key in buttons else neutral if key in axes else value)
            for key, value in state.items()}


def reindex(movie: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(movie)
    for index, frame in enumerate(result["frames"]):
        frame["frame"] = index
    return result


def delete_range(movie: dict[str, Any], start: int, stop: int) -> dict[str, Any]:
    result = copy.deepcopy(movie)
    result["frames"] = result["frames"][:start] + result["frames"][stop:]
    return reindex(result)


def shift_scenario_after_delete(scenario: dict[str, Any] | None, start: int,
                                stop: int) -> dict[str, Any] | None:
    if scenario is None:
        return None
    removed = stop - start
    result = copy.deepcopy(scenario)
    playback = result.get("playback") or {}
    if isinstance(playback.get("start_frame"), int):
        value = playback["start_frame"]
        playback["start_frame"] = value - removed if value >= stop else \
            start if value >= start else value
    for phase in result.get("phases") or []:
        trigger = phase.get("trigger") or {}
        if trigger.get("type") != "movie_frame" or not isinstance(trigger.get("target"), int):
            continue
        value = trigger["target"]
        trigger["target"] = value - removed if value >= stop else \
            start if value >= start else value
    return result


def neutralize_range(movie: dict[str, Any], start: int, stop: int,
                     policy: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(movie)
    for frame in result["frames"][start:stop]:
        frame["ports"] = {port: neutral_state(state, policy)
                          for port, state in frame["ports"].items()}
    return result


def neutralize_control(movie: dict[str, Any], port: str, control: str,
                       policy: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(movie)
    neutral: Any = False if control in set(policy["buttons"]) else int(policy["axis_neutral"])
    for frame in result["frames"]:
        state = frame.get("ports", {}).get(port)
        if isinstance(state, dict) and control in state:
            state[control] = neutral
    return result


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any((("token" in str(key).lower() and not str(key).lower().endswith("_sha256"))
                    or "password" in str(key).lower() or "secret" in str(key).lower())
                   or _contains_secret_key(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_secret_key(child) for child in value)
    return False


def validate_replay_receipt(receipt: Any, *, movie_sha256: str,
                            scenario_sha256: str | None, anchor: str,
                            expected_assertions: list[str],
                            expected_media_serial: str | None = None) -> None:
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        raise MinimizerError("replay receipt schema is invalid")
    if _contains_secret_key(receipt):
        raise MinimizerError("replay receipt contains a raw secret field")
    runtime = receipt.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("emulator") != "DuckStation":
        raise MinimizerError("replay receipt is not from DuckStation")
    for key in ("execution_mode", "movie_execution_mode"):
        if runtime.get(key) != "Interpreter":
            raise MinimizerError(f"replay receipt {key} is not Interpreter")
    config_dir = Path(str(runtime.get("config_dir") or ""))
    if not config_dir.is_absolute() or runtime.get("isolated") is not True or \
            runtime.get("config_recreated") is not True or \
            runtime.get("normal_profile_used") is not False:
        raise MinimizerError("replay did not prove a recreated isolated config")
    if runtime.get("loopback_host") not in {"127.0.0.1", "::1"}:
        raise MinimizerError("replay debugger host is not loopback")
    port = runtime.get("port")
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise MinimizerError("replay debugger port is invalid")
    for key in ("token_sha256", "media_sha256", "binary_sha256"):
        if not HEX64.fullmatch(str(runtime.get(key) or "")):
            raise MinimizerError(f"replay receipt lacks {key}")
    if runtime.get("media_verified") is not True or \
            runtime.get("movie_reproducible") is not True:
        raise MinimizerError("replay media/movie identity was not verified")
    media_serial = runtime.get("media_serial")
    if not isinstance(media_serial, str) or not media_serial.strip() or \
            (expected_media_serial is not None and media_serial != expected_media_serial):
        raise MinimizerError("replay media serial is absent or differs from the scenario")
    for key in ("config_identity_sha256", "launcher_sha256"):
        if not HEX64.fullmatch(str(runtime.get(key) or "")):
            raise MinimizerError(f"replay receipt lacks {key}")
    settings = runtime.get("settings")
    if not isinstance(settings, dict) or settings.get("verified") is not True or \
            settings.get("cpu_execution_mode") != "Interpreter":
        raise MinimizerError("runtime settings do not verify Interpreter mode")
    if runtime.get("pid_owned_by_config") is not True or \
            runtime.get("cleanup_complete") is not True:
        raise MinimizerError("replay lifecycle ownership/cleanup is incomplete")
    if not str(runtime.get("source_revision") or "").strip():
        raise MinimizerError("replay receipt lacks DuckStation source revision")
    if receipt.get("movie_sha256") != movie_sha256 or \
            receipt.get("scenario_sha256") != scenario_sha256:
        raise MinimizerError("replay receipt does not bind the candidate bytes")
    anchor_row = receipt.get("anchor")
    if not isinstance(anchor_row, dict) or anchor_row.get("source_class") != anchor or \
            anchor_row.get("candidate_class") != anchor or \
            anchor_row.get("identity_verified") is not True or \
            not HEX64.fullmatch(str(anchor_row.get("identity_sha256") or "")):
        raise MinimizerError("replay changed or failed to verify the anchor class")
    receipt_assertions = receipt.get("assertion_ids")
    if not isinstance(receipt_assertions, list) or not all(
            isinstance(value, str) and value for value in receipt_assertions) or \
            len(receipt_assertions) != len(set(receipt_assertions)) or \
            sorted(receipt_assertions) != sorted(expected_assertions):
        raise MinimizerError("replay receipt assertion universe changed")
    replays = receipt.get("replays")
    if not isinstance(replays, list) or len(replays) != 2:
        raise MinimizerError("receipt needs exactly assertion and control replays")
    by_role = {row.get("role"): row for row in replays if isinstance(row, dict)}
    if set(by_role) != {"assertion", "control"}:
        raise MinimizerError("receipt replay roles are incomplete or duplicated")
    run_ids = set()
    for role, row in by_role.items():
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or not run_id or run_id in run_ids:
            raise MinimizerError("assertion/control replays need distinct run IDs")
        run_ids.add(run_id)
        if row.get("passed") is not True or row.get("errors") != [] or \
                row.get("truncated") is not False or \
                row.get("movie_sha256") != movie_sha256:
            raise MinimizerError(f"{role} replay did not pass its full contract")
    if receipt.get("instrumentation_rearmed_after_load") is not True:
        raise MinimizerError("replay did not prove instrumentation re-arm after load")


@dataclass
class Evaluation:
    accepted: bool
    receipt_sha256: str | None = None
    detail: str = ""


Evaluator = Callable[[dict[str, Any], dict[str, Any] | None], Evaluation]


class ExternalOracle:
    def __init__(self, command: list[str], scenario: dict[str, Any] | None,
                 anchor: str, expected_assertions: list[str]):
        if not command or not any("{movie}" in part for part in command) or \
                not any("{receipt}" in part for part in command):
            raise MinimizerError("oracle command needs {movie} and {receipt} placeholders")
        if scenario is not None and not any("{scenario}" in part for part in command):
            raise MinimizerError("scenario oracle command needs {scenario}")
        self.command = command
        self.base_scenario = scenario
        self.anchor = anchor
        self.expected_assertions = expected_assertions
        target = (scenario or {}).get("target") or {}
        self.expected_media_serial = target.get("expected_serial")

    def __call__(self, movie: dict[str, Any], scenario: dict[str, Any] | None) -> Evaluation:
        with tempfile.TemporaryDirectory(prefix="abl-phase4-minimize-") as raw:
            directory = Path(raw)
            movie_path = directory / "candidate.movie.json"
            movie_bytes = canonical_json(movie)
            movie_path.write_bytes(movie_bytes)
            scenario_path = directory / "candidate.scenario.yaml"
            scenario_sha: str | None = None
            if scenario is not None:
                scenario_doc = copy.deepcopy(scenario)
                scenario_doc.setdefault("playback", {})["movie"] = str(movie_path)
                scenario_bytes = yaml.safe_dump(scenario_doc, sort_keys=False).encode()
                scenario_path.write_bytes(scenario_bytes)
                scenario_sha = sha256_bytes(scenario_bytes)
            receipt_path = directory / "receipt.json"
            replacements = {"{movie}": str(movie_path), "{scenario}": str(scenario_path),
                            "{receipt}": str(receipt_path)}
            command = [part.replace("{movie}", replacements["{movie}"])
                       .replace("{scenario}", replacements["{scenario}"])
                       .replace("{receipt}", replacements["{receipt}"])
                       for part in self.command]
            proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                  check=False, env={**os.environ, "PYTHONHASHSEED": "0"})
            if proc.returncode != 0 or not receipt_path.is_file():
                return Evaluation(False, detail=(
                    f"oracle exit={proc.returncode} stdout={proc.stdout[-500:]} "
                    f"stderr={proc.stderr[-500:]}"))
            try:
                raw_receipt = receipt_path.read_bytes()
                receipt = json.loads(raw_receipt)
                validate_replay_receipt(
                    receipt, movie_sha256=sha256_bytes(movie_bytes),
                    scenario_sha256=scenario_sha, anchor=self.anchor,
                    expected_assertions=self.expected_assertions,
                    expected_media_serial=self.expected_media_serial)
            except (OSError, json.JSONDecodeError, MinimizerError) as exc:
                return Evaluation(False, detail=str(exc))
            return Evaluation(True, sha256_bytes(raw_receipt), "full replay contract passed")


class Minimizer:
    def __init__(self, movie: dict[str, Any], scenario: dict[str, Any] | None,
                 policy: dict[str, Any], evaluator: Evaluator, max_evaluations: int):
        self.movie = movie
        self.scenario = scenario
        self.policy = policy
        self.evaluator = evaluator
        self.max_evaluations = max_evaluations
        self.evaluations = 0
        self.accepted = 0
        self.history: list[dict[str, Any]] = []
        self._seen: set[str] = set()

    def evaluate(self, movie: dict[str, Any], scenario: dict[str, Any] | None,
                 operation: str) -> bool:
        if self.evaluations >= self.max_evaluations:
            return False
        key = sha256_bytes(canonical_json({"movie": movie, "scenario": scenario}))
        if key in self._seen:
            return False
        self._seen.add(key)
        self.evaluations += 1
        result = self.evaluator(movie, scenario)
        self.history.append({"evaluation": self.evaluations, "operation": operation,
                             "candidate_sha256": key, "accepted": result.accepted,
                             "receipt_sha256": result.receipt_sha256,
                             "detail": result.detail})
        if result.accepted:
            self.movie = movie
            self.scenario = scenario
            self.accepted += 1
        return result.accepted

    def _chunks(self, length: int, granularity: int) -> list[tuple[int, int]]:
        width = max(1, math.ceil(length / granularity))
        return [(start, min(length, start + width)) for start in range(0, length, width)]

    def minimize_deleted_ranges(self) -> None:
        granularity = 2
        minimum = int(self.policy["minimum_frames"])
        while len(self.movie["frames"]) > minimum and self.evaluations < self.max_evaluations:
            length = len(self.movie["frames"])
            changed = False
            for start, stop in self._chunks(length, granularity):
                if length - (stop - start) < minimum:
                    continue
                candidate = delete_range(self.movie, start, stop)
                scenario = shift_scenario_after_delete(self.scenario, start, stop)
                if self.evaluate(candidate, scenario, f"delete_frames:{start}:{stop}"):
                    granularity = max(2, granularity - 1)
                    changed = True
                    break
            if changed:
                continue
            if granularity >= length:
                break
            granularity = min(length, granularity * 2)

    def minimize_neutral_ranges(self) -> None:
        granularity = 2
        while self.evaluations < self.max_evaluations:
            length = len(self.movie["frames"])
            changed = False
            for start, stop in self._chunks(length, granularity):
                candidate = neutralize_range(self.movie, start, stop, self.policy)
                if canonical_json(candidate) == canonical_json(self.movie):
                    continue
                if self.evaluate(candidate, self.scenario, f"neutralize_frames:{start}:{stop}"):
                    granularity = max(2, granularity - 1)
                    changed = True
                    break
            if changed:
                continue
            if granularity >= length:
                break
            granularity = min(length, granularity * 2)

    def minimize_controls(self) -> None:
        controls = sorted({(port, control)
                           for frame in self.movie["frames"]
                           for port, state in frame["ports"].items()
                           for control in state})
        for port, control in controls:
            if self.evaluations >= self.max_evaluations:
                break
            candidate = neutralize_control(self.movie, port, control, self.policy)
            if canonical_json(candidate) == canonical_json(self.movie):
                continue
            self.evaluate(candidate, self.scenario, f"neutralize_control:{port}:{control}")

    def tighten_scenario(self) -> None:
        if self.scenario is None:
            return
        playback = self.scenario.get("playback") or {}
        current = int(playback.get("start_frame", 0))
        targets = [int((phase.get("trigger") or {}).get("target"))
                   for phase in self.scenario.get("phases") or []
                   if (phase.get("trigger") or {}).get("type") == "movie_frame"]
        maximum = min(min(targets) if targets else len(self.movie["frames"]) - 1,
                      len(self.movie["frames"]) - 1)
        candidates = sorted(set([maximum, (current + maximum) // 2]), reverse=True)
        for value in candidates:
            if value <= current or self.evaluations >= self.max_evaluations:
                continue
            scenario = copy.deepcopy(self.scenario)
            scenario.setdefault("playback", {})["start_frame"] = value
            if self.evaluate(self.movie, scenario, f"tighten_start_frame:{value}"):
                current = value

    def run(self) -> dict[str, Any]:
        if not self.evaluate(self.movie, self.scenario, "baseline"):
            raise MinimizerError("source movie/scenario does not pass the replay contract")
        before = len(self.movie["frames"])
        self.tighten_scenario()
        self.minimize_deleted_ranges()
        self.minimize_neutral_ranges()
        self.minimize_controls()
        active = 0
        for frame in self.movie["frames"]:
            for state in frame["ports"].values():
                if state != neutral_state(state, self.policy):
                    active += 1
                    break
        return {
            "movie": self.movie,
            "scenario": self.scenario,
            "summary": {"frames_before": before, "frames_after": len(self.movie["frames"]),
                        "active_frames_after": active, "evaluations": self.evaluations,
                        "accepted_reductions": max(0, self.accepted - 1),
                        "evaluation_limit_reached": self.evaluations >= self.max_evaluations},
            "history": self.history,
        }


def synthetic_movie() -> dict[str, Any]:
    buttons = load_policy()["buttons"]
    frames = []
    for index in range(12):
        state = {key: False for key in buttons}
        if index == 3:
            state["cross"] = True
        if index == 6:
            state["triangle"] = True
        if index == 9:
            state["square"] = True
        frames.append({"frame": index, "ports": {"0": state}})
    return {"format": MOVIE_FORMAT, "version": 3, "game_serial": "SYNTHETIC",
            "start_state": {"from_boot": True}, "frames": frames}


def build_pilot() -> dict[str, Any]:
    policy = load_policy()
    movie = validate_movie(synthetic_movie(), policy)

    def evaluator(candidate: dict[str, Any], _: dict[str, Any] | None) -> Evaluation:
        states = [frame["ports"]["0"] for frame in candidate["frames"]]
        accepted = any(row.get("cross") is True for row in states) and \
            any(row.get("square") is True for row in states)
        return Evaluation(accepted, detail="synthetic predicate; not runtime evidence")

    result = Minimizer(movie, None, policy, evaluator, 256).run()
    return {
        "schema": PILOT_SCHEMA,
        "policy_sha256": sha256_bytes(POLICY_PATH.read_bytes()),
        "generator_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "input_class": "synthetic_non_game_movie",
        "runtime_evidence": False,
        "algorithm": "hierarchical deletion, neutralization, control simplification",
        "summary": result["summary"],
        "required_signals_retained": ["cross", "square"],
        "irrelevant_signal_removed": "triangle",
        "production_contract": {
            "emulator": "DuckStation",
            "execution_mode": "Interpreter",
            "movie_execution_mode": "Interpreter",
            "separate_assertion_and_control_replays_per_candidate": True,
            "isolated_recreated_config": True,
            "media_and_candidate_hash_binding": True,
            "runtime_settings_verified": True,
            "owned_pid_cleanup_required": True,
            "anchor_class_preserved": True,
            "source_overwrite_forbidden": True,
            "repository_output_forbidden": True,
        },
    }


def write_external_result(result: dict[str, Any], output_dir: Path,
                          source_movie: Path) -> tuple[Path, Path | None, Path]:
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise MinimizerError("minimized movies/scenarios must remain outside the repository")
    output_dir.mkdir(parents=True, exist_ok=True)
    movie_path = output_dir / f"{source_movie.stem}.minimized.json"
    if movie_path.resolve() == source_movie.resolve():
        raise MinimizerError("source movie overwrite is forbidden")
    scenario_path = None
    if result["scenario"] is not None:
        scenario_path = output_dir / f"{source_movie.stem}.minimized.scenario.yaml"
    report_path = output_dir / f"{source_movie.stem}.minimization-report.json"
    planned = [path for path in (movie_path, scenario_path, report_path)
               if path is not None]
    # Path.exists() is false for a dangling symlink.  Such a link can still be
    # followed by write_bytes(), including back into the repository, so both
    # lexical occupancy and the resolved destination must be checked before the
    # first output is created.
    collisions = [path for path in planned if os.path.lexists(path)]
    if collisions:
        raise MinimizerError(f"refusing to overwrite existing external outputs: {collisions}")
    unsafe = []
    for path in planned:
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            continue
        unsafe.append(path)
    if unsafe:
        raise MinimizerError(f"resolved output destinations enter the repository: {unsafe}")
    movie_path.write_bytes(canonical_json(result["movie"]))
    if result["scenario"] is not None:
        scenario = copy.deepcopy(result["scenario"])
        scenario.setdefault("playback", {})["movie"] = str(movie_path)
        scenario_path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    report = {"schema": "abl-phase4-movie-minimization-report/1",
              "source_movie": str(source_movie.resolve()),
              "source_movie_sha256": sha256_bytes(source_movie.read_bytes()),
              "minimized_movie": str(movie_path),
              "minimized_movie_sha256": sha256_bytes(movie_path.read_bytes()),
              "scenario": str(scenario_path) if scenario_path else None,
              "summary": result["summary"], "history": result["history"]}
    report_path.write_bytes(canonical_json(report))
    return movie_path, scenario_path, report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    pilot = parser.add_mutually_exclusive_group()
    pilot.add_argument("--write-pilot", action="store_true")
    pilot.add_argument("--check-pilot", action="store_true")
    parser.add_argument("--movie", type=Path)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--oracle-command-json",
                        help="JSON string list with {movie}, {scenario}, {receipt}")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--max-evaluations", type=int)
    args = parser.parse_args()
    if args.write_pilot or args.check_pilot:
        rendered = canonical_json(build_pilot())
        if args.write_pilot:
            PILOT_PATH.write_bytes(rendered)
            print(f"[phase4-movie-minimizer] wrote {PILOT_PATH.relative_to(ROOT)}")
            return 0
        if not PILOT_PATH.is_file() or PILOT_PATH.read_bytes() != rendered:
            raise MinimizerError("retained movie minimizer pilot is stale")
        print("[phase4-movie-minimizer] synthetic pilot reproduces")
        return 0
    if not args.movie or not args.oracle_command_json or not args.output_dir:
        parser.error("production minimization needs --movie, --oracle-command-json, --output-dir")
    try:
        command = json.loads(args.oracle_command_json)
    except json.JSONDecodeError as exc:
        raise MinimizerError(f"oracle command is not JSON: {exc}") from exc
    if not isinstance(command, list) or not all(isinstance(x, str) for x in command):
        raise MinimizerError("oracle command JSON must be a string list")
    policy = load_policy()
    movie_path = args.movie.resolve()
    scenario_path = args.scenario.resolve() if args.scenario else None
    movie = load_movie(movie_path, policy)
    scenario = load_scenario(scenario_path)
    anchor = anchor_class(movie, scenario)
    expected = assertion_ids(scenario)
    evaluator = ExternalOracle(command, scenario, anchor, expected)
    limit = args.max_evaluations or int(policy["default_max_evaluations"])
    if limit < 1:
        raise MinimizerError("max evaluations must be positive")
    result = Minimizer(movie, scenario, policy, evaluator, limit).run()
    paths = write_external_result(result, args.output_dir, movie_path)
    print(f"[phase4-movie-minimizer] frames {result['summary']['frames_before']} -> "
          f"{result['summary']['frames_after']}; evaluations={result['summary']['evaluations']}")
    print("\n".join(str(path) for path in paths if path))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MinimizerError as exc:
        print(f"phase4 movie minimizer error: {exc}", file=sys.stderr)
        raise SystemExit(2)
