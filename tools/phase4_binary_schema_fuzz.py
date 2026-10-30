#!/usr/bin/env python3
"""Validate read-only Kaitai schemas and fuzz bounded binary parser adapters."""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
from pathlib import Path
import resource
import struct
import sys
from typing import Any
import warnings

import yaml


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import decode_level_raw  # noqa: E402
import recompress_level_raw  # noqa: E402
import seed_table  # noqa: E402


POLICY_PATH = ROOT / "config/phase4_binary_schema_fuzz.yaml"
PILOT_PATH = ROOT / "analysis/phase4_binary_schema_fuzz_pilot.json"
POLICY_SCHEMA = "abl-phase4-binary-schema-fuzz-policy/1"
PILOT_SCHEMA = "abl-phase4-binary-schema-fuzz-pilot/1"
KNOWN_ADAPTERS = {"seed_table", "level_raw_container", "level_raw_chunk"}
EXPECTED_SCHEMA_IDS = {
    "seed_table": "abl_seed_table",
    "level_raw_container": "abl_level_raw_container",
    "level_raw_chunk": "abl_level_raw_chunk",
}
EXPECTED_ENDIAN = {
    "seed_table": "le",
    "level_raw_container": "be",
    "level_raw_chunk": "be",
}
EXPECTED_SEED = 424242
EXPECTED_LIMITS = {
    "max_input_bytes": 1048576,
    "max_output_bytes": 4194304,
    "max_cases_per_target": 96,
    "timeout_ms": 500,
    "memory_bytes": 268435456,
}
EXPECTED_SCHEMAS = [
    {
        "id": "seed_table",
        "path": "schemas/phase4/abl_seed_table.ksy",
        "adapter": "seed_table",
        "endian": "le",
    },
    {
        "id": "level_raw_container",
        "path": "schemas/phase4/abl_level_raw_container.ksy",
        "adapter": "level_raw_container",
        "endian": "be",
    },
    {
        "id": "level_raw_chunk",
        "path": "schemas/phase4/abl_level_raw_chunk.ksy",
        "adapter": "level_raw_chunk",
        "endian": "be",
    },
]
EXPECTED_MUTATION_OPERATORS = [
    "truncate", "flip_bit", "overwrite_u32_boundary", "append_bytes",
]
EXPECTED_AUTHORITY_POLICY = {
    "synthetic_corpus_only": True,
    "read_only_schemas": True,
    "existing_writers_unchanged": True,
    "reject_crash": True,
    "reject_timeout": True,
    "reject_output_limit": True,
    "deterministic_replay_required": True,
    "afl_or_libfuzzer_export_external_only": True,
    "retail_or_derived_corpus_must_remain_external": True,
}
EXPECTED_POLICY_FIELDS = {
    "schema", "seed", "limits", "schemas", "mutation_operators", "policy",
}


class FuzzError(RuntimeError):
    """Schema, corpus, sandbox, or deterministic-fuzz contract failure."""


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def validate_policy(doc: Any) -> dict[str, Any]:
    """Fail closed unless *doc* is the exact approved in-memory policy."""
    if type(doc) is not dict or doc.get("schema") != POLICY_SCHEMA:
        raise FuzzError(f"binary-schema fuzz policy must use {POLICY_SCHEMA}")
    if set(doc) != EXPECTED_POLICY_FIELDS:
        raise FuzzError("binary-schema fuzz policy has unknown or missing fields")
    if type(doc.get("seed")) is not int or doc["seed"] != EXPECTED_SEED:
        raise FuzzError("binary-schema fuzz seed drifted")
    limits = doc.get("limits")
    if type(limits) is not dict or set(limits) != set(EXPECTED_LIMITS):
        raise FuzzError("binary-schema fuzz resource limit fields drifted")
    for key, approved in EXPECTED_LIMITS.items():
        value = limits[key]
        # bool is an int subclass, so an isinstance check does not fail closed.
        if type(value) is not int:
            raise FuzzError(f"limits.{key} must be an exact integer")
        if value != approved:
            raise FuzzError(
                f"limits.{key} drifted from approved value {approved}")
    authority = doc.get("policy")
    if type(authority) is not dict or set(authority) != set(EXPECTED_AUTHORITY_POLICY):
        raise FuzzError("binary-schema fuzz authority policy fields drifted")
    if any(type(authority[key]) is not bool
           for key in EXPECTED_AUTHORITY_POLICY):
        raise FuzzError("binary-schema fuzz authority values must be exact booleans")
    if authority != EXPECTED_AUTHORITY_POLICY:
        raise FuzzError("binary-schema fuzz authority policy drifted")
    schemas = doc.get("schemas")
    if type(schemas) is not list or len(schemas) != len(EXPECTED_SCHEMAS):
        raise FuzzError("schema declarations drifted from the bounded adapter set")
    for declaration, expected in zip(schemas, EXPECTED_SCHEMAS):
        if type(declaration) is not dict or set(declaration) != set(expected):
            raise FuzzError("schema declarations drifted from the bounded adapter set")
        if any(type(declaration[key]) is not str for key in expected):
            raise FuzzError("schema declaration values must be exact strings")
        if declaration != expected:
            raise FuzzError("schema declarations drifted from the bounded adapter set")
    operators = doc.get("mutation_operators")
    if type(operators) is not list:
        raise FuzzError("mutation operator contract drifted")
    if any(type(operator) is not str for operator in operators):
        raise FuzzError("mutation operators must be exact strings")
    if operators != EXPECTED_MUTATION_OPERATORS:
        raise FuzzError("mutation operator contract drifted")
    return doc


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FuzzError(f"cannot load binary-schema fuzz policy: {exc}") from exc
    return validate_policy(doc)


def _walk_values(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child)


def validate_kaitai_schemas(policy: dict[str, Any]) -> list[dict[str, Any]]:
    reports = []
    seen: set[str] = set()
    for declaration in policy["schemas"]:
        if set(declaration) != {"id", "path", "adapter", "endian"}:
            raise FuzzError("schema declaration has unknown or missing fields")
        adapter = declaration["adapter"]
        relative = declaration["path"]
        if declaration["id"] != adapter or adapter in seen:
            raise FuzzError("schema IDs/adapters must be unique and identical")
        declared_endian = declaration["endian"]
        if not isinstance(declared_endian, str):
            raise FuzzError(f"{adapter}: declared endian must be a string")
        if declared_endian != EXPECTED_ENDIAN[adapter]:
            raise FuzzError(f"{adapter}: declared endian contract drifted")
        seen.add(adapter)
        path = ROOT / relative
        try:
            path.resolve(strict=True).relative_to(ROOT.resolve())
        except (OSError, ValueError) as exc:
            raise FuzzError(f"unsafe or missing schema path: {relative}") from exc
        if path.suffix != ".ksy" or path.is_symlink():
            raise FuzzError(f"schema must be a regular non-symlink .ksy file: {relative}")
        try:
            schema = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise FuzzError(f"cannot parse Kaitai schema {relative}: {exc}") from exc
        meta = schema.get("meta") if isinstance(schema, dict) else None
        if not isinstance(meta, dict) or meta.get("id") != EXPECTED_SCHEMA_IDS[adapter]:
            raise FuzzError(f"{relative}: unexpected Kaitai meta.id")
        if meta.get("license") != "CC0-1.0":
            raise FuzzError(f"{relative}: license contract drifted")
        schema_endian = meta.get("endian")
        if not isinstance(schema_endian, str):
            raise FuzzError(f"{relative}: Kaitai endian must be a string")
        if schema_endian != declared_endian:
            raise FuzzError(f"{relative}: Kaitai endian contract drifted")
        if not isinstance(schema.get("seq"), list) or not schema["seq"]:
            raise FuzzError(f"{relative}: Kaitai seq is empty")
        forbidden = {"process", "instances", "io", "contents"}
        found = {key for key, _ in _walk_values(schema) if key in forbidden}
        if found:
            raise FuzzError(f"{relative}: read-only schema contains forbidden keys {sorted(found)}")
        reports.append({"id": adapter, "path": relative, "sha256": sha256_file(path),
                        "meta_id": meta["id"], "endian": meta["endian"],
                        "read_only": True})
    return reports


def synthetic_seeds() -> dict[str, bytes]:
    seed_blob = struct.pack("<I", seed_table.SEED_MARKER)
    seed_blob += struct.pack("<iii", 1, -2, 3) + bytes(range(16))
    seed_blob += struct.pack("<iii", 0, 0, 0) + bytes(16)
    decompressed = bytes(range(64))
    chunk = recompress_level_raw.compress_chunk(decompressed, header6=b"ABLKSY")
    container = chunk + struct.pack(">I", seed_table.CHUNK_TERMINATOR)
    return {"seed_table": seed_blob, "level_raw_container": container,
            "level_raw_chunk": chunk}


def mutate(seed: bytes, max_cases: int, max_input_bytes: int) -> list[bytes]:
    cases: dict[str, bytes] = {sha256_bytes(seed): seed}

    def add(value: bytes) -> None:
        if len(value) <= max_input_bytes:
            cases.setdefault(sha256_bytes(value), value)

    for stop in sorted({0, 1, 2, 3, 4, 7, 8, 13, 14, len(seed) // 2, len(seed) - 1}):
        if 0 <= stop < len(seed):
            add(seed[:stop])
    positions = sorted({0, 1, 3, 4, 7, 8, 13, 14, len(seed) // 3,
                        len(seed) // 2, max(0, len(seed) - 1)})
    for position in positions:
        if position < len(seed):
            for bit in (0, 3, 7):
                changed = bytearray(seed)
                changed[position] ^= 1 << bit
                add(bytes(changed))
    for offset in range(0, min(len(seed) - 3, 32), 4):
        for boundary in (0, 1, 0x7FFFFFFF, 0xFFFFFFFF):
            for endian in ("<I", ">I"):
                changed = bytearray(seed)
                struct.pack_into(endian, changed, offset, boundary)
                add(bytes(changed))
    for suffix in (b"\x00", b"\xff" * 4, b"ABL" * 7):
        add(seed + suffix)
    return [cases[key] for key in sorted(cases)][:max_cases]


def _strict_container(data: bytes, max_output: int) -> int:
    offset = 0
    chunks = 0
    declared_output = 0
    while True:
        if offset + 4 > len(data):
            raise ValueError("container lacks a complete terminator")
        word0 = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        if word0 == seed_table.CHUNK_TERMINATOR:
            if offset != len(data):
                raise ValueError("container has trailing bytes after terminator")
            return chunks
        if offset + 10 > len(data):
            raise ValueError("chunk header is truncated")
        word1 = struct.unpack_from(">I", data, offset)[0]
        offset += 10
        if word1 > len(data) - offset:
            raise ValueError("chunk payload overruns container")
        declared_output += word0
        if declared_output > max_output:
            raise OverflowError("declared decompressed output exceeds policy")
        offset += word1
        chunks += 1


def _bounded_chunk(data: bytes, max_output: int) -> int:
    if len(data) < seed_table.CHUNK_HEADER_LEN:
        raise ValueError("compressed chunk header is truncated")
    decompressed_size, compressed_size = struct.unpack_from(">II", data, 0)
    if compressed_size != len(data) - seed_table.CHUNK_HEADER_LEN:
        raise ValueError("compressed size does not exactly bind input")
    if decompressed_size > max_output:
        raise OverflowError("declared decompressed output exceeds policy")
    output = decode_level_raw.decompress_chunk(data)
    if len(output) != decompressed_size:
        raise ValueError("actual output differs from declared size")
    return len(output)


def _execute_adapter(adapter: str, data: bytes, max_output: int) -> int:
    if adapter == "seed_table":
        return len(seed_table.parse_seed_table(data))
    if adapter == "level_raw_container":
        return _strict_container(data, max_output)
    if adapter == "level_raw_chunk":
        return _bounded_chunk(data, max_output)
    raise FuzzError(f"unknown adapter {adapter}")


EXPECTED_REJECTIONS = (ValueError, IndexError, struct.error, RuntimeError,
                       OverflowError, EOFError, AssertionError)


def _worker(adapter: str, data: bytes, maximum_output: int, memory_bytes: int,
            result_pipe: Any) -> None:
    try:
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        output_units = _execute_adapter(adapter, data, maximum_output)
        result_pipe.send(("ok", output_units, None))
    except EXPECTED_REJECTIONS as exc:
        result_pipe.send(("rejected", None, type(exc).__name__))
    except BaseException as exc:  # pragma: no cover - deliberately adversarial
        try:
            result_pipe.send(("crash", None, type(exc).__name__))
        except BaseException:
            pass
    finally:
        result_pipe.close()


def run_case(adapter: str, data: bytes, limits: dict[str, int]) -> dict[str, Any]:
    if len(data) > limits["max_input_bytes"]:
        return {"status": "input_limit", "detail": None}
    context = multiprocessing.get_context("fork")
    parent_pipe, child_pipe = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(
        adapter, data, limits["max_output_bytes"], limits["memory_bytes"], child_pipe))
    # Python 3.14 warns whenever os.fork observes runtime helper threads (for
    # example after an unrelated DuckDB test). The CLI pilot is single-threaded,
    # and the child performs no shared-state work; contain the noisy generic
    # warning here so a larger pytest process does not emit one per fuzz case.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"This process .* is multi-threaded.*",
                                category=DeprecationWarning)
        process.start()
    child_pipe.close()
    process.join(limits["timeout_ms"] / 1000)
    if process.is_alive():
        process.terminate()
        process.join(1)
        if process.is_alive():  # pragma: no cover - terminate normally works
            process.kill()
            process.join()
        parent_pipe.close()
        return {"status": "timeout", "detail": None}
    if not parent_pipe.poll():
        parent_pipe.close()
        return {"status": "crash", "detail": f"exit_{process.exitcode}"}
    status, units, detail = parent_pipe.recv()
    parent_pipe.close()
    if status == "ok" and isinstance(units, int) and units > limits["max_output_bytes"]:
        return {"status": "output_limit", "detail": None}
    return {"status": status, "detail": detail}


def run_pilot(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = load_policy() if policy is None else validate_policy(policy)
    schemas = validate_kaitai_schemas(policy)
    seeds = synthetic_seeds()
    target_reports = []
    all_failures = []
    for declaration in policy["schemas"]:
        adapter = declaration["adapter"]
        corpus = mutate(seeds[adapter], policy["limits"]["max_cases_per_target"],
                        policy["limits"]["max_input_bytes"])
        first = [run_case(adapter, case, policy["limits"]) for case in corpus]
        second = [run_case(adapter, case, policy["limits"]) for case in corpus]
        nondeterministic = [index for index, pair in enumerate(zip(first, second))
                            if pair[0] != pair[1]]
        counts = {status: sum(row["status"] == status for row in first)
                  for status in ("ok", "rejected", "crash", "timeout",
                                 "input_limit", "output_limit")}
        failures = []
        for status in ("crash", "timeout", "input_limit", "output_limit"):
            if counts[status]:
                failures.append(f"{status}:{counts[status]}")
        if nondeterministic:
            failures.append(f"nondeterministic:{len(nondeterministic)}")
        all_failures.extend(f"{adapter}:{failure}" for failure in failures)
        target_reports.append({
            "id": adapter, "seed_sha256": sha256_bytes(seeds[adapter]),
            "corpus_sha256": sha256_bytes(b"".join(
                bytes.fromhex(sha256_bytes(case)) for case in corpus)),
            "cases": len(corpus), "classifications": counts,
            "deterministic_replay": not nondeterministic, "failures": failures,
        })
    return {
        "schema": PILOT_SCHEMA,
        "runtime_evidence": False,
        "synthetic_only": True,
        "seed": policy["seed"],
        "schemas": schemas,
        "targets": target_reports,
        "summary": {"schemas": len(schemas),
                    "cases": sum(row["cases"] for row in target_reports),
                    "failures": all_failures},
        "production_contract": {
            "read_only_schemas": True,
            "existing_writers_unchanged": True,
            "bounded_child_processes": True,
            "external_long_running_corpora_only": True,
            "campaign_promotion": False,
        },
        "source_dependencies": {
            "tools/phase4_binary_schema_fuzz.py": sha256_file(Path(__file__)),
            "config/phase4_binary_schema_fuzz.yaml": sha256_file(POLICY_PATH),
            **{row["path"]: row["sha256"] for row in schemas},
        },
    }


def _external_output(path: Path) -> Path:
    resolved_parent = path.parent.resolve(strict=True)
    resolved = resolved_parent / path.name
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise FuzzError("corpus export must remain outside the repository")
    if path.exists() or path.is_symlink():
        raise FuzzError("refusing to overwrite existing corpus export")
    if path.parent.is_symlink():
        raise FuzzError("corpus export parent may not be a symlink")
    return resolved


def export_synthetic_corpus(output: Path, policy: dict[str, Any] | None = None) -> dict:
    policy = load_policy() if policy is None else validate_policy(policy)
    target = _external_output(output)
    target.mkdir()
    files = []
    try:
        for adapter, seed in synthetic_seeds().items():
            directory = target / adapter
            directory.mkdir()
            for index, case in enumerate(mutate(
                    seed, policy["limits"]["max_cases_per_target"],
                    policy["limits"]["max_input_bytes"])):
                path = directory / f"case-{index:04d}-{sha256_bytes(case)[:12]}"
                path.write_bytes(case)
                files.append({"path": str(path.relative_to(target)), "sha256": sha256_bytes(case),
                              "bytes": len(case)})
    except BaseException:
        import shutil
        shutil.rmtree(target, ignore_errors=True)
        raise
    return {"schema": "abl-phase4-binary-fuzz-corpus/1", "synthetic_only": True,
            "files": files}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pilot")
    export = sub.add_parser("export-corpus")
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "export-corpus":
        print(json.dumps(export_synthetic_corpus(args.output), indent=1, sort_keys=True))
        return 0
    report = run_pilot()
    if report["summary"]["failures"]:
        raise FuzzError(f"binary fuzz pilot failed: {report['summary']['failures']}")
    PILOT_PATH.write_bytes(canonical_json(report))
    print(f"[phase4-binary-schema-fuzz] {report['summary']['cases']} cases; OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
