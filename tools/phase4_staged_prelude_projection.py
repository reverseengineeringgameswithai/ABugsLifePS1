#!/usr/bin/env python3
"""Project a paired staged-prelude CPU boundary from a retained batch result."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READER_REL = "tools/phase4_staged_prelude_projection.py"
PASS_STDOUT = "PASS: offline query\n"
HEX64 = frozenset("0123456789abcdef")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def render(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source(path: Path) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "sha256": sha256(path)}


def _bounded_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{label} must be an integer in {minimum}..{maximum}")
    return value


def _hex_pc(value: Any, label: str) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError(f"{label} is not a hexadecimal PC")
    try:
        return int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} is not a hexadecimal PC") from exc


def query_prelude(
    document: Any, query: dict[str, Any], source: Path
) -> dict[str, Any]:
    expected_source = query.get("expected_source_sha256")
    if (
        not isinstance(expected_source, str)
        or len(expected_source) != 64
        or any(char not in HEX64 for char in expected_source)
        or sha256(source) != expected_source
    ):
        raise ValueError("staged-prelude source SHA-256 drifted")

    expected_schema = query.get("expected_schema")
    expected_serial = query.get("expected_serial")
    expected_media = query.get("expected_cue_sha256")
    expected_track = query.get("expected_track_sha256")
    expected_binary = query.get("expected_binary_sha256")
    expected_revision = query.get("expected_source_revision")
    expected_dirty = query.get("expected_dirty_state_hash")
    job_ids = query.get("job_ids")
    if not all(
        isinstance(value, str) and value
        for value in (
            expected_schema,
            expected_serial,
            expected_media,
            expected_track,
            expected_binary,
            expected_revision,
            expected_dirty,
        )
    ):
        raise ValueError("staged-prelude string identities are incomplete")
    if not isinstance(job_ids, list) or len(job_ids) != 2 or any(
        not isinstance(value, str) or not value for value in job_ids
    ):
        raise ValueError("staged-prelude query requires exactly two job IDs")

    if (
        not isinstance(document, dict)
        or document.get("schema") != expected_schema
        or document.get("campaign_id") != query.get("campaign_id")
        or document.get("row_ids") != [query.get("row_id")]
    ):
        raise ValueError("staged-prelude batch identity drifted")
    debugger = document.get("expected_debugger") or {}
    if (
        debugger.get("binary_sha256") != expected_binary
        or debugger.get("source_revision") != expected_revision
        or debugger.get("dirty_state_hash") != expected_dirty
    ):
        raise ValueError("staged-prelude debugger identity drifted")
    mounted = document.get("mounted_media") or {}
    declared_media = document.get("expected_media") or {}
    declared_tracks = declared_media.get("tracks")
    if (
        mounted.get("game_serial") != expected_serial
        or declared_media.get("serial") != expected_serial
        or declared_media.get("sha256") != expected_media
        or not isinstance(declared_tracks, list)
        or len(declared_tracks) != 1
        or declared_tracks[0].get("sha256") != expected_track
    ):
        raise ValueError("staged-prelude mounted-media identity drifted")

    result = document.get("result")
    jobs = result.get("jobs") if isinstance(result, dict) else None
    if (
        not isinstance(jobs, list)
        or result.get("state") != "completed"
        or [row.get("id") for row in jobs] != job_ids
        or any(row.get("state") != "completed" for row in jobs)
    ):
        raise ValueError("staged-prelude jobs are not exactly completed")

    expected_start = _bounded_int(
        query.get("expected_start_frame"), "staged-prelude start frame", 0, 10**8
    )
    expected_frame = _bounded_int(
        query.get("expected_frame"), "staged-prelude frame", expected_start, 10**8
    )
    expected_advanced = _bounded_int(
        query.get("expected_frames_advanced"),
        "staged-prelude frames advanced",
        0,
        10**8,
    )
    expected_run_frames = _bounded_int(
        query.get("expected_run_frames"), "staged-prelude run frames", 1, 10**8
    )
    expected_pc = query.get("expected_pc")
    expected_pc_value = _hex_pc(expected_pc, "staged-prelude expected PC")

    preludes: list[dict[str, Any]] = []
    for row in jobs:
        job_result = row.get("result") or {}
        media = job_result.get("media") or {}
        prelude = job_result.get("staged_prelude") or {}
        status = prelude.get("status") or {}
        run = job_result.get("run") or {}
        if (
            job_result.get("atomic_setup") is not True
            or job_result.get("media_verified") is not True
            or media.get("game_serial") != expected_serial
            or media.get("sha256") != expected_media
            or job_result.get("instrumentation") != []
            or prelude.get("start_frame") != expected_start
            or prelude.get("target_frame") != expected_frame
            or prelude.get("frames_advanced") != expected_advanced
            or status.get("frame") != expected_frame
            or status.get("valid") is not True
            or status.get("paused") is not True
            or status.get("running") is not False
            or run.get("frames_advanced") != expected_run_frames
        ):
            raise ValueError("staged-prelude job boundary drifted")
        pc = _hex_pc(status.get("pc"), "staged-prelude PC")
        if pc != expected_pc_value:
            raise ValueError("staged-prelude PC differs from the expected boundary")
        cycle = _bounded_int(
            status.get("cycle"), "staged-prelude cycle", 0, 10**18
        )
        sp = status.get("sp")
        if not isinstance(sp, str) or not sp.startswith("0x"):
            raise ValueError("staged-prelude stack pointer is invalid")
        preludes.append(
            {
                "job_id": row["id"],
                "frame": expected_frame,
                "cycle": cycle,
                "pc": status["pc"],
                "sp": sp,
            }
        )

    first = preludes[0]
    if any(
        row[key] != first[key]
        for row in preludes[1:]
        for key in ("frame", "cycle", "pc", "sp")
    ):
        raise ValueError("paired staged-prelude CPU boundaries diverged")

    return {
        "schema": "abl-phase4-offline-staged-prelude-projection/1",
        "query": query,
        "source": _source(source),
        "result": {
            "batch_state": "completed",
            "jobs": preludes,
            "paired_cpu_boundary_equal": True,
            "boundary": {
                "frame": first["frame"],
                "cycle": first["cycle"],
                "pc": first["pc"],
                "sp": first["sp"],
                "pc_expected": expected_pc,
            },
            "media": {
                "game_serial": expected_serial,
                "cue_sha256": expected_media,
                "track_sha256": expected_track,
                "verified": True,
            },
            "payload_retained": False,
        },
    }


def run_query(input_path: Path, output_path: Path, query: dict[str, Any]) -> None:
    if query.get("kind") != "staged_prelude_projection":
        raise ValueError("query kind must be staged_prelude_projection")
    document = json.loads(input_path.read_bytes())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render(query_prelude(document, query, input_path)))


def _relative_run_path(path: Path, run_root: Path) -> str:
    try:
        return path.resolve().relative_to(run_root.resolve()).as_posix()
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
            "offline query did not complete cleanly:\n" + completed.stdout
        )

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
                completed.stdout.encode("utf-8")
            ).hexdigest(),
        },
        "query": query,
        "external_inputs": [_ref(input_path, run_root)],
        "outputs": [_ref(output_path, run_root)],
        "external_preservation_manifest": _ref(preservation_path, run_root),
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
                    "and input media class"
                )
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
