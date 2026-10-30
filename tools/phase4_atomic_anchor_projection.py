#!/usr/bin/env python3
"""Project one hash-pinned atomic anchor without retaining captured bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READER_REL = "tools/phase4_atomic_anchor_projection.py"
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


def _source(path: Path) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "sha256": sha256(path)}


def _bounded_int(
        value: Any, label: str, minimum: int, maximum: int
) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or \
            not minimum <= value <= maximum:
        raise ValueError(
            f"{label} must be an integer in {minimum}..{maximum}")
    return value


def query_anchor(
        document: Any, query: dict[str, Any], source: Path
) -> dict[str, Any]:
    expected_schema = query.get("expected_schema")
    expected_variant = query.get("expected_variant")
    expected_source_sha256 = query.get("expected_source_sha256")
    expected_media_sha256 = query.get("expected_media_sha256")
    expected_serial = query.get("expected_serial")
    job_id = query.get("job_id")
    memory_label = query.get("memory_label")
    expected_memory_address = query.get("expected_memory_address")
    expected_memory_sha256 = query.get("expected_memory_sha256")
    retired_memory_sha256 = query.get("retired_memory_sha256")
    expected_pc = query.get("expected_pc")
    strings = {
        "expected_schema": expected_schema,
        "expected_variant": expected_variant,
        "expected_source_sha256": expected_source_sha256,
        "expected_media_sha256": expected_media_sha256,
        "expected_serial": expected_serial,
        "job_id": job_id,
        "memory_label": memory_label,
        "expected_memory_address": expected_memory_address,
        "expected_memory_sha256": expected_memory_sha256,
        "retired_memory_sha256": retired_memory_sha256,
        "expected_pc": expected_pc,
    }
    if any(not isinstance(value, str) or not value
           for value in strings.values()):
        raise ValueError("atomic anchor query requires every string identity")
    for label in (
            "expected_source_sha256", "expected_media_sha256",
            "expected_memory_sha256", "retired_memory_sha256"):
        value = strings[label]
        if len(value) != 64 or any(char not in HEX64 for char in value):
            raise ValueError(f"atomic anchor {label} is not lowercase SHA-256")
    if sha256(source) != expected_source_sha256:
        raise ValueError("atomic anchor source SHA-256 drifted")
    if not isinstance(document, dict) or \
            document.get("schema") != expected_schema or \
            document.get("complete") is not True or \
            document.get("errors") != [] or \
            document.get("variant") != expected_variant:
        raise ValueError("atomic anchor result identity is not closed")
    if document.get("server_session_id") in (None, ""):
        raise ValueError("atomic anchor server-session identity is missing")
    result = document.get("result")
    jobs = result.get("jobs") if isinstance(result, dict) else None
    if not isinstance(jobs, list) or result.get("state") != "completed":
        raise ValueError("atomic anchor batch is incomplete")
    matches = [row for row in jobs if row.get("id") == job_id]
    if len(matches) != 1 or matches[0].get("state") != "completed":
        raise ValueError("atomic anchor job is not uniquely completed")
    job_result = matches[0].get("result")
    if not isinstance(job_result, dict) or \
            job_result.get("atomic_setup") is not True or \
            job_result.get("media_verified") is not True:
        raise ValueError("atomic anchor job setup is not closed")
    media = job_result.get("media")
    if not isinstance(media, dict) or \
            media.get("sha256") != expected_media_sha256 or \
            media.get("game_serial") != expected_serial:
        raise ValueError("atomic anchor pristine media identity drifted")

    capture = job_result.get("capture")
    cpu = capture.get("cpu") if isinstance(capture, dict) else None
    status = cpu.get("status") if isinstance(cpu, dict) else None
    registers = cpu.get("registers", {}).get("registers_hex") \
        if isinstance(cpu, dict) else None
    expected_frame = _bounded_int(
        query.get("expected_frame"), "atomic anchor expected frame",
        0, 100_000_000)
    expected_cycle = _bounded_int(
        query.get("expected_cycle"), "atomic anchor expected cycle",
        0, 10**18)
    if not isinstance(status, dict) or not isinstance(registers, dict) or \
            status != {
                "cycle": expected_cycle,
                "frame": expected_frame,
                "paused": True,
                "pc": expected_pc,
                "running": False,
                "sp": status.get("sp"),
                "valid": True,
            } or registers.get("pc") != expected_pc:
        raise ValueError("atomic anchor CPU boundary drifted")

    memories = capture.get("memory") if isinstance(capture, dict) else None
    memory_rows = [
        row for row in memories or []
        if isinstance(row, dict) and row.get("label") == memory_label
    ]
    expected_memory_length = _bounded_int(
        query.get("expected_memory_length"),
        "atomic anchor expected memory length", 1, 1_048_576)
    if len(memory_rows) != 1:
        raise ValueError("atomic anchor memory capture is not unique")
    memory = memory_rows[0]
    encoded = memory.get("hex")
    if not isinstance(encoded, str):
        raise ValueError("atomic anchor memory capture has no hex payload")
    try:
        raw = bytes.fromhex(encoded)
    except ValueError as exc:
        raise ValueError("atomic anchor memory capture hex is invalid") from exc
    observed_memory_sha256 = hashlib.sha256(raw).hexdigest()
    if memory.get("address", "").casefold() != \
            expected_memory_address.casefold() or \
            memory.get("length") != expected_memory_length or \
            memory.get("valid_bytes") != expected_memory_length or \
            len(raw) != expected_memory_length or \
            observed_memory_sha256 != expected_memory_sha256 or \
            observed_memory_sha256 == retired_memory_sha256:
        raise ValueError("atomic anchor memory identity drifted")

    selected_registers = {
        name: registers[name]
        for name in ("pc", "ra", "s0", "v0", "v1")
        if name in registers
    }
    if set(selected_registers) != {"pc", "ra", "s0", "v0", "v1"}:
        raise ValueError("atomic anchor selected registers are incomplete")
    return {
        "schema": "abl-phase4-offline-atomic-anchor-projection/1",
        "query": query,
        "source": _source(source),
        "result": {
            "schema": expected_schema,
            "variant": expected_variant,
            "server_session_id": document["server_session_id"],
            "batch_state": result["state"],
            "job_id": job_id,
            "job_state": matches[0]["state"],
            "media": {
                "game_serial": expected_serial,
                "sha256": expected_media_sha256,
                "verified": True,
            },
            "anchor": {
                "frame": expected_frame,
                "cycle": expected_cycle,
                "pc": expected_pc,
                "sp": status["sp"],
                "paused": True,
                "selected_registers": selected_registers,
            },
            "memory": {
                "label": memory_label,
                "address": expected_memory_address,
                "length": expected_memory_length,
                "sha256": observed_memory_sha256,
                "retired_memory_sha256": retired_memory_sha256,
                "retired_memory_absent": True,
                "payload_retained": False,
            },
        },
    }


def run_query(
        input_path: Path, output_path: Path, query: dict[str, Any]
) -> None:
    if query.get("kind") != "atomic_anchor_projection":
        raise ValueError("query kind must be atomic_anchor_projection")
    document = json.loads(input_path.read_bytes())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render(query_anchor(document, query, input_path)))


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
