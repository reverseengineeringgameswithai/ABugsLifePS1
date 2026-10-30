#!/usr/bin/env python3
"""Run bounded JSON evidence queries and derive replayable offline receipts.

The normal command surface is deliberately small: one retained input, one
retained output, and one canonical JSON query.  ``--emit-receipt`` adds a
one-time authoring mode which runs that same command, hashes its exact stdout
and artifacts, and writes the preservation manifest and receipt consumed by
``phase4_method_metrics.py``.  The recorded command never includes the
authoring-only paths, so the metrics validator can replay it independently.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
READER_REL = "tools/phase4_offline_receipt_query.py"
PASS_STDOUT = "PASS: offline query\n"
HEX64 = frozenset("0123456789abcdef")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def render(value: Any) -> bytes:
    return (json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False
    ) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_pointer(parts: tuple[str, ...]) -> str:
    if not parts:
        return ""
    return "/" + "/".join(
        part.replace("~", "~0").replace("/", "~1") for part in parts
    )


def _walk(value: Any, parts: tuple[str, ...] = ()) -> Iterator[tuple[str, Any]]:
    yield _json_pointer(parts), value
    if isinstance(value, dict):
        for key in sorted(value):
            yield from _walk(value[key], (*parts, str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, (*parts, str(index)))


def _source(path: Path) -> dict[str, Any]:
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def _query_index(document: Any, query: dict[str, Any], source: Path) -> dict[str, Any]:
    terms = query.get("terms")
    match = query.get("match")
    case_sensitive = query.get("case_sensitive")
    path_limit = query.get("path_limit")
    if not isinstance(terms, list) or not 1 <= len(terms) <= 32 or not all(
            isinstance(term, str) and 1 <= len(term) <= 256 for term in terms):
        raise ValueError("json_search terms must contain 1..32 bounded strings")
    if match not in {"exact", "substring"}:
        raise ValueError("json_search match must be exact or substring")
    if not isinstance(case_sensitive, bool):
        raise ValueError("json_search case_sensitive must be boolean")
    if not isinstance(path_limit, int) or isinstance(path_limit, bool) or \
            not 1 <= path_limit <= 256:
        raise ValueError("json_search path_limit must be 1..256")

    normalized_terms = terms if case_sensitive else [term.casefold() for term in terms]
    results = {
        term: {"count": 0, "paths": [], "paths_truncated": False}
        for term in terms
    }
    for pointer, value in _walk(document):
        if not isinstance(value, (str, int)):
            continue
        text = str(value)
        candidate = text if case_sensitive else text.casefold()
        for original, term in zip(terms, normalized_terms):
            hit = candidate == term if match == "exact" else term in candidate
            if not hit:
                continue
            result = results[original]
            result["count"] += 1
            if len(result["paths"]) < path_limit:
                result["paths"].append(pointer)
            else:
                result["paths_truncated"] = True

    top_level: dict[str, Any]
    if isinstance(document, dict):
        top_level = {}
        for key in sorted(document):
            value = document[key]
            if isinstance(value, (dict, list)):
                top_level[key] = {
                    "type": type(value).__name__,
                    "count": len(value),
                }
            elif isinstance(value, (str, int, bool)) or value is None:
                top_level[key] = value
            else:
                top_level[key] = {"type": type(value).__name__}
    else:
        top_level = {
            "type": type(document).__name__,
            "count": len(document) if isinstance(document, list) else None,
        }
    return {
        "schema": "abl-phase4-offline-json-search-result/1",
        "query": query,
        "source": _source(source),
        "top_level": top_level,
        "terms": results,
    }


def _active_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return value is not None and value != 128


def _intervals(frames: list[int]) -> list[dict[str, int]]:
    if not frames:
        return []
    result = []
    start = prior = frames[0]
    for frame in frames[1:]:
        if frame != prior + 1:
            result.append({"start": start, "stop": prior})
            start = frame
        prior = frame
    result.append({"start": start, "stop": prior})
    return result


def _query_movie(document: Any, query: dict[str, Any], source: Path) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ValueError("movie input is not a JSON object")
    frames = document.get("frames")
    if not isinstance(frames, list):
        raise ValueError("movie frames are not an array")
    expected_frames = query.get("expected_frames")
    if expected_frames is not None and expected_frames != len(frames):
        raise ValueError(
            f"movie frame count drifted: {len(frames)} != {expected_frames}")
    expected_sha256 = query.get("expected_sha256")
    actual_sha256 = sha256(source)
    if expected_sha256 is not None and expected_sha256 != actual_sha256:
        raise ValueError(
            f"movie SHA-256 drifted: {actual_sha256} != {expected_sha256}")

    active_frames: list[int] = []
    by_control: dict[str, list[int]] = defaultdict(list)
    explicit_frame_numbers = True
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError(f"movie frame {index} is not an object")
        number = frame.get("frame")
        if not isinstance(number, int) or isinstance(number, bool):
            number = index
            explicit_frame_numbers = False
        ports = frame.get("ports") or {}
        if not isinstance(ports, dict):
            raise ValueError(f"movie frame {index} ports are not an object")
        frame_active = False
        for port in sorted(ports, key=str):
            controls = ports[port] or {}
            if not isinstance(controls, dict):
                raise ValueError(
                    f"movie frame {index} port {port} is not an object")
            for control in sorted(controls):
                if _active_value(controls[control]):
                    frame_active = True
                    by_control[f"{port}:{control}"].append(number)
        if frame_active:
            active_frames.append(number)

    return {
        "schema": "abl-phase4-offline-movie-input-result/1",
        "query": query,
        "source": {
            **_source(source),
            "format": document.get("format"),
            "version": document.get("version"),
            "game_serial": document.get("game_serial"),
            "initial_frame": document.get("initial_frame"),
            "start_state": document.get("start_state"),
        },
        "frames": {
            "count": len(frames),
            "explicit_frame_numbers": explicit_frame_numbers,
            "active_count": len(active_frames),
            "first_active": active_frames[0] if active_frames else None,
            "last_active": active_frames[-1] if active_frames else None,
            "active_spans": _intervals(active_frames),
        },
        "controls": {
            control: {
                "active_count": len(values),
                "spans": _intervals(values),
            }
            for control, values in sorted(by_control.items())
        },
    }


def _bounded_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or \
            not minimum <= value <= maximum:
        raise ValueError(
            f"{label} must be an integer in {minimum}..{maximum}")
    return value


def _query_function_event_retention(
        document: Any, query: dict[str, Any], source: Path) -> dict[str, Any]:
    """Derive a finite same-anchor functionTrace retention contract.

    A saturated ring still retains monotonically increasing source indexes.
    The last index is therefore the exact number of events emitted in the
    completed bounded job, even when its prefix was discarded.  This query
    deliberately does not reconstruct the types of discarded events.
    """
    if not isinstance(document, dict) or document.get("schema") != \
            "abl-phase4-duckstation-batch-result/1":
        raise ValueError("function retention input is not a batch result")
    result = document.get("result")
    jobs = result.get("jobs") if isinstance(result, dict) else None
    if not isinstance(jobs, list):
        raise ValueError("function retention input has no job array")

    job_id = query.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("function retention job_id is required")
    matches = [row for row in jobs if row.get("id") == job_id]
    if len(matches) != 1:
        raise ValueError("function retention job is not unique")
    job = matches[0]
    if job.get("state") != "completed":
        raise ValueError("function retention job is incomplete")
    job_result = job.get("result")
    if not isinstance(job_result, dict):
        raise ValueError("function retention job has no result")

    window = query.get("window")
    if not isinstance(window, dict) or set(window) != {
            "clock", "start", "stop"} or window.get("clock") != "movie_frame":
        raise ValueError("function retention window must be a movie-frame bound")
    window_start = _bounded_int(
        window["start"], "function retention window start", 0, 10_000_000)
    window_stop = _bounded_int(
        window["stop"], "function retention window stop",
        window_start + 1, 10_000_000)
    stage = job_result.get("staged_prelude") or {}
    run = job_result.get("run") or {}
    if stage.get("target_frame") != window_start or \
            stage.get("frames_advanced") != window_start or \
            run.get("start_playback_index") != window_start or \
            run.get("target_frame") != window_stop or \
            run.get("frames_advanced") != window_stop - window_start:
        raise ValueError("function retention job/window counters drifted")

    configured_max = _bounded_int(
        query.get("configured_max_events"),
        "configured function-event limit", 1, 1_000_000)
    proposed_max = _bounded_int(
        query.get("proposed_max_events"),
        "proposed function-event limit", 1, 1_000_000)
    required_headroom = _bounded_int(
        query.get("required_headroom_events"),
        "required function-event headroom", 1, 1_000_000)
    expected_function = query.get("expected_function")
    expected_caller = query.get("expected_caller")
    if not isinstance(expected_function, str) or not expected_function or \
            not isinstance(expected_caller, str) or not expected_caller:
        raise ValueError("expected function and caller are required")

    capture = job_result.get("capture") or {}
    traces = capture.get("traces") or {}
    functions = traces.get("functions")
    if not isinstance(functions, list) or not functions:
        raise ValueError("function retention job has no function events")
    indexes = [row.get("index") for row in functions]
    if any(not isinstance(index, int) or isinstance(index, bool)
           for index in indexes) or \
            indexes != list(range(indexes[0], indexes[-1] + 1)):
        raise ValueError("function retention indexes are not contiguous")
    if len(functions) != configured_max:
        raise ValueError("function retention source did not fill its limit")
    if any(row.get("function") != expected_function or
           row.get("caller") != expected_caller
           for row in functions):
        raise ValueError("retained function/caller suffix drifted")
    if any(
            row.get("type") != ("entry" if row["index"] % 2 else "exit")
            for row in functions):
        raise ValueError("retained function entry/exit pairing drifted")

    total_emitted = indexes[-1]
    discarded_prefix = indexes[0] - 1
    headroom = proposed_max - total_emitted
    if proposed_max <= total_emitted or headroom < required_headroom:
        raise ValueError("proposed function-event limit lacks required headroom")
    frame_values = [row.get("frame") for row in functions]
    cycle_values = [row.get("cycle") for row in functions]
    if any(not isinstance(value, int) or isinstance(value, bool)
           for value in frame_values + cycle_values):
        raise ValueError("function retention event clocks are not integers")
    if frame_values != sorted(frame_values) or cycle_values != sorted(cycle_values):
        raise ValueError("function retention event clocks are not ordered")

    window_frames = window_stop - window_start
    return {
        "schema": "abl-phase4-offline-function-event-retention-result/1",
        "query": query,
        "source": _source(source),
        "job": {
            "id": job_id,
            "state": "completed",
            "window": window,
        },
        "observed": {
            "configured_max_events": configured_max,
            "retained_events": len(functions),
            "first_retained_index": indexes[0],
            "last_retained_index": indexes[-1],
            "discarded_prefix_events": discarded_prefix,
            "total_emitted_events": total_emitted,
            "retained_function": expected_function,
            "retained_caller": expected_caller,
            "retained_complete_calls": len(functions) // 2,
            "retained_emulator_frame_span": {
                "start": frame_values[0],
                "stop": frame_values[-1],
            },
            "retained_cpu_cycle_span": {
                "start": cycle_values[0],
                "stop": cycle_values[-1],
            },
            "event_rate": {
                "events": total_emitted,
                "movie_frames": window_frames,
                "events_per_movie_frame": f"{total_emitted / window_frames:.6f}",
            },
        },
        "successor_retention_contract": {
            "same_anchor_window": window,
            "max_events": proposed_max,
            "observed_event_upper_bound": total_emitted,
            "headroom_events": headroom,
            "required_headroom_events": required_headroom,
            "require_first_retained_index": 1,
            "require_last_retained_index_lte": total_emitted,
            "require_returned_events_lte": total_emitted,
            "require_returned_events_lt_max": True,
            "discarded_event_types_claimed": False,
            "bounded_for_same_anchor_window": True,
        },
    }


def run_query(input_path: Path, output_path: Path, query: dict[str, Any]) -> None:
    raw = input_path.read_bytes()
    document = json.loads(raw)
    if query.get("kind") == "json_search":
        result = _query_index(document, query, input_path)
    elif query.get("kind") == "movie_inputs":
        result = _query_movie(document, query, input_path)
    elif query.get("kind") == "function_event_retention":
        result = _query_function_event_retention(
            document, query, input_path)
    else:
        raise ValueError(
            "query kind must be json_search, movie_inputs, or "
            "function_event_retention")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render(result))


def _relative_run_path(path: Path, run_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(run_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"receipt artifact is outside run root: {path}") from exc


def _ref(path: Path, run_root: Path) -> dict[str, Any]:
    return {
        "scope": "run",
        "path": _relative_run_path(path, run_root),
        "sha256": sha256(path),
    }


def emit_receipt(
        input_path: Path,
        output_path: Path,
        query: dict[str, Any],
        receipt_path: Path,
        preservation_path: Path,
        run_root: Path,
        input_media_class: str,
) -> None:
    if input_media_class not in {"pristine", "derived_pristine_evidence"}:
        raise ValueError("offline input media class is not authority-bearing")
    input_token = f"@run/{_relative_run_path(input_path, run_root)}"
    output_token = f"@run/{_relative_run_path(output_path, run_root)}"
    command = [
        sys.executable,
        str(ROOT / READER_REL),
        "--input",
        str(input_path.resolve()),
        "--output",
        str(output_path.resolve()),
        "--query-json",
        canonical_bytes(query).decode("utf-8"),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0 or completed.stdout != PASS_STDOUT:
        raise RuntimeError(
            "offline query did not complete cleanly:\n" + completed.stdout)

    preservation = {
        "schema": "abl-phase4-method-external-preservation/1",
        "complete": True,
        "errors": [],
        "entries": [
            {
                "sha256": sha256(input_path),
                "size": input_path.stat().st_size,
                "media_class": input_media_class,
                "preservation_required": True,
            },
            {
                "sha256": sha256(output_path),
                "size": output_path.stat().st_size,
                "media_class": "derived_pristine_evidence",
                "preservation_required": True,
            },
        ],
    }
    if preservation["entries"][0]["sha256"] == \
            preservation["entries"][1]["sha256"]:
        raise ValueError("offline input and output unexpectedly have one identity")
    preservation_path.parent.mkdir(parents=True, exist_ok=True)
    preservation_path.write_bytes(render(preservation))

    receipt = {
        "schema": "abl-phase4-offline-query/1",
        "complete": True,
        "errors": [],
        "reader": {
            "scope": "repo",
            "path": READER_REL,
            "sha256": sha256(ROOT / READER_REL),
        },
        "command": [
            "python3",
            READER_REL,
            "--input",
            input_token,
            "--output",
            output_token,
            "--query-json",
            "@query",
        ],
        "execution": {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stdout_sha256": hashlib.sha256(
                completed.stdout.encode("utf-8")).hexdigest(),
        },
        "query": query,
        "external_inputs": [_ref(input_path, run_root)],
        "outputs": [_ref(output_path, run_root)],
        "external_preservation_manifest": _ref(
            preservation_path, run_root),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(render(receipt))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--query-json", required=True)
    parser.add_argument("--emit-receipt", type=Path)
    parser.add_argument("--preservation-manifest", type=Path)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument(
        "--input-media-class",
        choices=("pristine", "derived_pristine_evidence"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        query = json.loads(args.query_json)
        if not isinstance(query, dict) or not query:
            raise ValueError("query must be a nonempty JSON object")
        authoring = (
            args.emit_receipt,
            args.preservation_manifest,
            args.run_root,
            args.input_media_class,
        )
        if any(item is not None for item in authoring):
            if not all(item is not None for item in authoring):
                raise ValueError(
                    "receipt authoring requires receipt, preservation, run root "
                    "and input media class")
            emit_receipt(
                args.input,
                args.output,
                query,
                args.emit_receipt,
                args.preservation_manifest,
                args.run_root,
                args.input_media_class,
            )
        else:
            run_query(args.input, args.output, query)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(PASS_STDOUT, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
