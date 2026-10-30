#!/usr/bin/env python3
"""Build and query a fail-closed external DuckDB/Parquet trace warehouse."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/phase4_trace_warehouse.yaml"
CAPSULE_SET_PATH = ROOT / "analysis/phase4_trace_capsule_set.json"
PILOT_PATH = ROOT / "analysis/phase4_trace_warehouse_pilot.json"
POLICY_SCHEMA = "abl-phase4-trace-warehouse-policy/1"
IMPORT_SCHEMA = "abl-phase4-trace-warehouse-import/1"
EXTERNAL_MANIFEST_SCHEMA = "abl-phase4-trace-warehouse-manifest/1"
PILOT_SCHEMA = "abl-phase4-trace-warehouse-pilot/1"
CAPSULE_SET_SCHEMA = "abl-phase4-trace-capsule-set-v2"
CAPSULE_SET_SCHEMAS = frozenset({
    "abl-phase4-trace-capsule-set-v1",
    CAPSULE_SET_SCHEMA,
})
EVENT_KEYS = {
    "capsule_id", "movie", "cohort", "frame", "domain", "key",
    "before_hex", "after_hex", "block_pc", "block_count",
}
EVENT_FRAME_CONTRACT = {
    "coordinate": "movie_relative_frame_boundary",
    "interval": "closed",
    "lower_bound": 0,
    "upper_bound": "retained_capsule.frames",
}
CAPSULE_ROW_KEYS = {
    "block_mode", "capsule_bytes", "capsule_directory", "capsule_file_count",
    "capsule_manifest_sha256", "capsule_tree_sha256", "control_match",
    "duckstation_binary_sha256", "frames", "media_class", "movie",
    "movie_bytes", "movie_sha256", "preservation_required", "start_state",
}
CAPSULE_START_STATE_KEYS = {"bytes", "path", "sha256"}
EXPECTED_POLICY = {
    "schema": POLICY_SCHEMA,
    "engine": {
        "name": "DuckDB", "version": "1.5.5", "extensions_allowed": False,
    },
    "input": {
        "schema": IMPORT_SCHEMA,
        "require_complete_capsule_set": True,
        "require_control_match": True,
        "reject_truncation_or_errors": True,
        "allowed_domains": ["register", "ram", "vram", "spu", "block"],
        "allowed_cohorts": ["positive", "negative", "control"],
        "max_partitions": 4096,
        "max_partition_bytes": 1073741824,
        "max_rows": 100000000,
        "event_frame": EVENT_FRAME_CONTRACT,
    },
    "output": {
        "external_only": True,
        "overwrite": False,
        "compression": "zstd",
        "files": {
            "database": "trace_warehouse.duckdb",
            "manifest": "trace_warehouse.manifest.json",
            "partitions": "parquet",
        },
    },
    "queries": [
        {
            "id": "first_change",
            "purpose": "Earliest observed frame for each changed domain/key in each capsule.",
        },
        {
            "id": "cohort_contrast",
            "purpose": "Positive versus negative/control movie coverage by domain/key.",
        },
        {
            "id": "block_enrichment",
            "purpose": "Positive versus negative/control block-count enrichment.",
        },
        {
            "id": "cross_movie",
            "purpose": "Cross-movie recurrence of each changed domain/key.",
        },
    ],
    "authority": {
        "frame_boundary_only": True,
        "exact_causality": False,
        "campaign_promotion": False,
        "live_escalation_requires_named_missing_domain": True,
    },
}


class WarehouseError(RuntimeError):
    """A warehouse input or preservation boundary failed closed."""


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _hex64(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
            char not in "0123456789abcdef" for char in value):
        raise WarehouseError(f"{field} must be a lowercase SHA-256")
    return value


def _strict_int(value: Any, field: str, *, minimum: int = 0) -> int:
    """Accept JSON integers, but never Python's bool-as-int subtype."""
    if type(value) is not int or value < minimum:
        raise WarehouseError(f"{field} must be an integer >= {minimum}")
    return value


def _require_exact_typed(value: Any, expected: Any, field: str) -> None:
    """Require a recursively exact policy value without bool/int coercion."""
    if type(value) is not type(expected):
        raise WarehouseError(
            f"{field} type drifted: {type(value).__name__} != "
            f"{type(expected).__name__}")
    if isinstance(expected, dict):
        if set(value) != set(expected):
            raise WarehouseError(f"{field} fields drifted")
        for key, expected_value in expected.items():
            _require_exact_typed(value[key], expected_value, f"{field}.{key}")
    elif isinstance(expected, list):
        if len(value) != len(expected):
            raise WarehouseError(f"{field} length drifted")
        for index, (actual_value, expected_value) in enumerate(zip(value, expected)):
            _require_exact_typed(actual_value, expected_value, f"{field}[{index}]")
    elif value != expected:
        raise WarehouseError(f"{field} value drifted")


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WarehouseError(f"cannot load warehouse policy: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != POLICY_SCHEMA:
        raise WarehouseError(f"warehouse policy must use {POLICY_SCHEMA}")
    _require_exact_typed(doc, EXPECTED_POLICY, "policy")
    return doc


def import_duckdb() -> Any:
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - environment diagnostic
        raise WarehouseError("duckdb 1.5.5 is required; install tools/requirements.txt") from exc
    if duckdb.__version__ != "1.5.5":
        raise WarehouseError(f"DuckDB version drift: {duckdb.__version__} != 1.5.5")
    return duckdb


def validate_capsule_set(doc: dict[str, Any], policy: dict[str, Any]) -> dict[str, dict]:
    if doc.get("schema") not in CAPSULE_SET_SCHEMAS:
        raise WarehouseError("capsule set schema is not a supported retained contract")
    if policy["input"]["require_complete_capsule_set"] and doc.get("complete") is not True:
        raise WarehouseError("capsule set is incomplete")
    capsules = doc.get("capsules")
    if not isinstance(capsules, list):
        raise WarehouseError("capsule rows must be a list")
    capsule_count = _strict_int(doc.get("capsule_count"), "capsule_count", minimum=1)
    if capsule_count != len(capsules):
        raise WarehouseError("capsule count does not match capsule rows")
    if policy["input"]["reject_truncation_or_errors"] and doc.get("errors") != []:
        raise WarehouseError("capsule set errors must be exactly []")
    if (doc.get("reproducibility_comparison") or {}).get("mismatches") != []:
        raise WarehouseError("capsule reproducibility comparison has mismatches")
    if (doc.get("reproducibility_comparison") or {}).get(
            "frame_chunks_byte_identical") is not True:
        raise WarehouseError("capsule frame chunks are not reproducible")
    by_movie: dict[str, dict] = {}
    for row in capsules:
        if not isinstance(row, dict):
            raise WarehouseError("capsule row must be an object")
        if set(row) != CAPSULE_ROW_KEYS:
            raise WarehouseError("capsule row has unknown or missing fields")
        movie = row.get("movie")
        if not isinstance(movie, str) or not movie or movie in by_movie:
            raise WarehouseError("capsule movies must be non-empty and unique")
        for field in ("block_mode", "capsule_directory", "media_class"):
            if type(row[field]) is not str or not row[field]:
                raise WarehouseError(f"{movie}.{field} must be a non-empty string")
        if row["block_mode"] != "counts":
            raise WarehouseError(f"{movie}.block_mode must be counts")
        _hex64(row.get("capsule_manifest_sha256"), f"{movie}.manifest")
        _hex64(row.get("capsule_tree_sha256"), f"{movie}.tree")
        _hex64(row.get("duckstation_binary_sha256"), f"{movie}.duckstation_binary")
        _hex64(row.get("movie_sha256"), f"{movie}.movie")
        if policy["input"]["require_control_match"] and row.get("control_match") is not True:
            raise WarehouseError(f"{movie}: capsule control does not match")
        if type(row["preservation_required"]) is not bool or \
                row["preservation_required"] is not True:
            raise WarehouseError(f"{movie}.preservation_required must be true")
        _strict_int(row.get("frames"), f"{movie}.frames", minimum=1)
        for field in ("capsule_bytes", "capsule_file_count", "movie_bytes"):
            _strict_int(row.get(field), f"{movie}.{field}", minimum=1)
        start_state = row.get("start_state")
        if not isinstance(start_state, dict) or set(start_state) != CAPSULE_START_STATE_KEYS:
            raise WarehouseError(f"{movie}.start_state has unknown or missing fields")
        if type(start_state["path"]) is not str or not start_state["path"]:
            raise WarehouseError(f"{movie}.start_state.path must be a non-empty string")
        _strict_int(start_state["bytes"], f"{movie}.start_state.bytes", minimum=1)
        _hex64(start_state["sha256"], f"{movie}.start_state.sha256")
        by_movie[movie] = row
    return by_movie


def _outside_repository(path: Path, *, must_exist: bool) -> Path:
    resolved = path.resolve(strict=must_exist)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise WarehouseError(f"path must remain outside repository: {path}")


def _safe_external_file(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise WarehouseError(f"partition path must be non-empty and relative: {relative!r}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or relative != pure.as_posix():
        raise WarehouseError(f"partition path must be canonical POSIX relative: {relative!r}")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise WarehouseError(f"unsafe partition path: {relative!r}")
    candidate = root.joinpath(*pure.parts)
    current = root
    for part in pure.parts:
        current = current / part
        if current.is_symlink():
            raise WarehouseError(f"symlinked partition path is forbidden: {relative}")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise WarehouseError(f"partition escapes dataset root: {relative}") from exc
    if not resolved.is_file():
        raise WarehouseError(f"partition is not a regular file: {relative}")
    return resolved


def validate_import_manifest(doc: dict[str, Any], manifest_path: Path,
                             capsule_set: dict[str, Any],
                             policy: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    if doc.get("schema") != IMPORT_SCHEMA:
        raise WarehouseError(f"import manifest must use {IMPORT_SCHEMA}")
    expected_set_hash = sha256_bytes(canonical_json(capsule_set))
    if doc.get("capsule_set_sha256") != expected_set_hash:
        raise WarehouseError("import manifest capsule-set identity mismatch")
    retained = validate_capsule_set(capsule_set, policy)
    capsules = doc.get("capsules")
    if not isinstance(capsules, list) or not capsules:
        raise WarehouseError("import manifest has no capsules")
    allowed_cohorts = set(policy["input"]["allowed_cohorts"])
    by_id: dict[str, dict] = {}
    bound_movies: set[str] = set()
    for item in capsules:
        if not isinstance(item, dict) or set(item) != {
                "id", "movie", "cohort", "capsule_manifest_sha256",
                "capsule_tree_sha256"}:
            raise WarehouseError("capsule binding has unknown or missing fields")
        capsule_id = item["id"]
        movie = item["movie"]
        if not isinstance(capsule_id, str) or not capsule_id or capsule_id in by_id:
            raise WarehouseError("capsule IDs must be non-empty and unique")
        if not isinstance(movie, str) or not movie or movie in bound_movies:
            raise WarehouseError("each retained movie may be bound exactly once")
        if item["cohort"] not in allowed_cohorts:
            raise WarehouseError(f"{capsule_id}: forbidden cohort")
        for field in ("capsule_manifest_sha256", "capsule_tree_sha256"):
            _hex64(item[field], f"{capsule_id}.{field}")
        retained_row = retained.get(movie)
        if retained_row is None:
            by_id[capsule_id] = {**item, "retained_frame_upper": None}
            bound_movies.add(movie)
            continue
        for field in ("capsule_manifest_sha256", "capsule_tree_sha256"):
            if item[field] != retained_row[field]:
                raise WarehouseError(f"{capsule_id}: {field} mismatch")
        by_id[capsule_id] = {
            **item,
            # Internal-only binding for the closed movie-relative boundary
            # interval [0, frames]. A movie with N input frames has N+1
            # captured boundaries: its initial anchor and its final boundary.
            "retained_frame_upper": retained_row["frames"],
        }
        bound_movies.add(movie)
    if policy["input"]["require_complete_capsule_set"]:
        retained_movies = set(retained)
        missing_movies = sorted(retained_movies - bound_movies)
        unexpected_movies = sorted(bound_movies - retained_movies)
        if missing_movies or unexpected_movies:
            raise WarehouseError(
                "capsule bindings must equal the complete retained movie set: "
                f"missing={missing_movies!r}; unexpected={unexpected_movies!r}")
    else:
        unexpected_movies = sorted(bound_movies - set(retained))
        if unexpected_movies:
            raise WarehouseError(
                "capsule bindings contain movies absent from retained capsule set: "
                f"unexpected={unexpected_movies!r}")
    partitions = doc.get("partitions")
    if not isinstance(partitions, list) or not partitions:
        raise WarehouseError("import manifest has no partitions")
    if len(partitions) > policy["input"]["max_partitions"]:
        raise WarehouseError("partition count exceeds policy")
    dataset_root = _outside_repository(manifest_path.parent, must_exist=True)
    seen_paths: set[str] = set()
    seen_physical_files: set[tuple[int, int]] = set()
    validated: list[dict] = []
    total_rows = 0
    for partition in partitions:
        if not isinstance(partition, dict) or set(partition) != {
                "path", "sha256", "bytes", "rows"}:
            raise WarehouseError("partition declaration has unknown or missing fields")
        relative = partition["path"]
        if not isinstance(relative, str):
            raise WarehouseError("partition path must be a string")
        if relative in seen_paths:
            raise WarehouseError(f"duplicate partition: {relative}")
        seen_paths.add(relative)
        path = _safe_external_file(dataset_root, relative)
        stat = path.stat()
        physical_identity = (stat.st_dev, stat.st_ino)
        if physical_identity in seen_physical_files:
            raise WarehouseError(
                f"duplicate resolved physical partition identity: {relative}")
        seen_physical_files.add(physical_identity)
        expected_bytes = partition["bytes"]
        expected_rows = partition["rows"]
        if (type(expected_bytes) is not int or expected_bytes < 0 or
                expected_bytes > policy["input"]["max_partition_bytes"]):
            raise WarehouseError(f"{relative}: byte count exceeds policy")
        if type(expected_rows) is not int or expected_rows < 1:
            raise WarehouseError(f"{relative}: invalid row count")
        if stat.st_size != expected_bytes:
            raise WarehouseError(f"{relative}: byte count mismatch")
        if sha256_file(path) != _hex64(partition["sha256"], f"{relative}.sha256"):
            raise WarehouseError(f"{relative}: SHA-256 mismatch")
        total_rows += expected_rows
        validated.append({**partition, "resolved_path": path})
    if total_rows > policy["input"]["max_rows"]:
        raise WarehouseError("declared row count exceeds policy")
    return list(by_id.values()), validated


def read_events(partitions: list[dict], capsule_bindings: list[dict],
                policy: dict[str, Any]) -> list[tuple]:
    capsules = {row["id"]: row for row in capsule_bindings}
    allowed_domains = set(policy["input"]["allowed_domains"])
    events: list[tuple] = []
    for partition in partitions:
        rows = 0
        with partition["resolved_path"].open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise WarehouseError(
                        f"{partition['path']}:{line_number}: invalid JSON") from exc
                if not isinstance(row, dict) or set(row) != EVENT_KEYS:
                    raise WarehouseError(
                        f"{partition['path']}:{line_number}: event field contract mismatch")
                binding = capsules.get(row["capsule_id"])
                if binding is None or row["movie"] != binding["movie"] or \
                        row["cohort"] != binding["cohort"]:
                    raise WarehouseError(
                        f"{partition['path']}:{line_number}: capsule binding mismatch")
                frame = row["frame"]
                if type(frame) is not int:
                    raise WarehouseError(
                        f"{partition['path']}:{line_number}: frame must be an integer")
                frame_upper = binding["retained_frame_upper"]
                if not 0 <= frame <= frame_upper:
                    raise WarehouseError(
                        f"{partition['path']}:{line_number}: frame {frame} escapes closed "
                        f"movie-relative capsule boundary span [0, {frame_upper}]")
                if (not isinstance(row["domain"], str) or
                        row["domain"] not in allowed_domains or
                        not isinstance(row["key"], str) or not row["key"]):
                    raise WarehouseError(
                        f"{partition['path']}:{line_number}: invalid event identity")
                for name in ("before_hex", "after_hex", "block_pc"):
                    if row[name] is not None and not isinstance(row[name], str):
                        raise WarehouseError(
                            f"{partition['path']}:{line_number}: {name} must be string/null")
                if type(row["block_count"]) is not int or row["block_count"] < 0:
                    raise WarehouseError(
                        f"{partition['path']}:{line_number}: invalid block_count")
                events.append(tuple(row[key] for key in (
                    "capsule_id", "movie", "cohort", "frame", "domain", "key",
                    "before_hex", "after_hex", "block_pc", "block_count")))
                rows += 1
        if rows != partition["rows"]:
            raise WarehouseError(f"{partition['path']}: declared/actual row count mismatch")
    return events


QUERY_SQL = {
    "first_change": """
        SELECT capsule_id, movie, domain, key, min(frame) AS first_frame
        FROM events
        WHERE domain <> 'block' AND before_hex IS DISTINCT FROM after_hex
        GROUP BY capsule_id, movie, domain, key
        ORDER BY capsule_id, domain, key
    """,
    "cohort_contrast": """
        SELECT domain, key,
          count(DISTINCT capsule_id) FILTER (WHERE cohort = 'positive') AS positive_movies,
          count(DISTINCT capsule_id) FILTER (WHERE cohort IN ('negative','control')) AS comparison_movies
        FROM events
        WHERE domain <> 'block' AND before_hex IS DISTINCT FROM after_hex
        GROUP BY domain, key
        ORDER BY domain, key
    """,
    "block_enrichment": """
        SELECT coalesce(block_pc, key) AS block_pc,
          sum(block_count) FILTER (WHERE cohort = 'positive') AS positive_count,
          sum(block_count) FILTER (WHERE cohort IN ('negative','control')) AS comparison_count
        FROM events
        WHERE domain = 'block'
        GROUP BY coalesce(block_pc, key)
        ORDER BY coalesce(positive_count, 0) - coalesce(comparison_count, 0) DESC, block_pc
    """,
    "cross_movie": """
        SELECT domain, key, count(DISTINCT movie) AS movies,
          min(frame) AS first_frame, max(frame) AS last_frame
        FROM events
        WHERE domain <> 'block' AND before_hex IS DISTINCT FROM after_hex
        GROUP BY domain, key
        ORDER BY movies DESC, domain, key
    """,
}


def _rows(connection: Any, query_id: str) -> list[dict[str, Any]]:
    cursor = connection.execute(QUERY_SQL[query_id])
    names = [row[0] for row in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _configure(connection: Any) -> None:
    connection.execute("SET autoinstall_known_extensions = false")
    connection.execute("SET autoload_known_extensions = false")
    connection.execute("SET allow_community_extensions = false")
    connection.execute("SET threads = 1")


def build_warehouse(import_manifest_path: Path, capsule_set_path: Path,
                    output_dir: Path, policy_path: Path = POLICY_PATH) -> dict[str, Any]:
    policy = load_policy(policy_path)
    duckdb = import_duckdb()
    manifest_path = _outside_repository(import_manifest_path, must_exist=True)
    set_path = capsule_set_path.resolve(strict=True)
    try:
        manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        capsule_set = json.loads(set_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WarehouseError(f"cannot load warehouse inputs: {exc}") from exc
    bindings, partitions = validate_import_manifest(
        manifest_doc, manifest_path, capsule_set, policy)
    events = read_events(partitions, bindings, policy)
    output = _outside_repository(output_dir, must_exist=False)
    if output.exists() or output.is_symlink():
        raise WarehouseError(f"refusing to overwrite existing output: {output}")
    if output.parent.is_symlink():
        raise WarehouseError("output parent may not be a symlink")
    output.mkdir(parents=False)
    parquet_dir = output / policy["output"]["files"]["partitions"]
    parquet_dir.mkdir()
    database_path = output / policy["output"]["files"]["database"]
    try:
        connection = duckdb.connect(str(database_path), config={"allow_unsigned_extensions": "false"})
        _configure(connection)
        connection.execute("""
            CREATE TABLE events (
              capsule_id VARCHAR NOT NULL, movie VARCHAR NOT NULL,
              cohort VARCHAR NOT NULL, frame UBIGINT NOT NULL,
              domain VARCHAR NOT NULL, key VARCHAR NOT NULL,
              before_hex VARCHAR, after_hex VARCHAR, block_pc VARCHAR,
              block_count UBIGINT NOT NULL
            )
        """)
        connection.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", events)
        for domain in sorted(set(row[4] for row in events)):
            target = parquet_dir / f"domain={domain}.parquet"
            escaped_target = str(target).replace("'", "''")
            connection.execute(
                "COPY (SELECT * FROM events WHERE domain = ? ORDER BY capsule_id, frame, key) "
                f"TO '{escaped_target}' (FORMAT parquet, COMPRESSION zstd)", [domain])
        query_results = {query_id: _rows(connection, query_id) for query_id in QUERY_SQL}
        connection.execute("CHECKPOINT")
        connection.close()
        files = []
        for path in sorted(p for p in output.rglob("*") if p.is_file()):
            files.append({"path": str(path.relative_to(output)), "bytes": path.stat().st_size,
                          "sha256": sha256_file(path)})
        report = {
            "schema": EXTERNAL_MANIFEST_SCHEMA,
            "engine": {"name": "DuckDB", "version": duckdb.__version__,
                       "extensions_allowed": False},
            "source": {
                "import_manifest_sha256": sha256_file(manifest_path),
                "capsule_set_sha256": sha256_bytes(canonical_json(capsule_set)),
                "capsules": len(bindings), "partitions": len(partitions),
            },
            "summary": {"events": len(events), "domains": sorted(set(r[4] for r in events))},
            "event_frame": EVENT_FRAME_CONTRACT,
            "files": files,
            "queries": query_results,
            "authority": policy["authority"],
            "external_only": True,
        }
        external_manifest = output / policy["output"]["files"]["manifest"]
        external_manifest.write_bytes(canonical_json(report))
        return report
    except BaseException:
        shutil.rmtree(output, ignore_errors=True)
        raise


def _synthetic_capsule_set() -> dict[str, Any]:
    capsules = []
    for index, movie in enumerate(("positive.movie", "negative.movie", "control.movie"), 1):
        capsules.append({
            "block_mode": "counts",
            "capsule_bytes": 1000 + index,
            "capsule_directory": f"synthetic/trace-capsules/{movie}",
            "capsule_file_count": 10 + index,
            "movie": movie, "capsule_manifest_sha256": sha256_bytes(f"manifest-{index}".encode()),
            "capsule_tree_sha256": sha256_bytes(f"tree-{index}".encode()),
            "control_match": True,
            "duckstation_binary_sha256": sha256_bytes(b"synthetic-duckstation"),
            "frames": 10,
            "media_class": "synthetic test fixture; not runtime evidence",
            "movie_bytes": 100 + index,
            "movie_sha256": sha256_bytes(f"movie-{index}".encode()),
            "preservation_required": True,
            "start_state": {
                "bytes": 200 + index,
                "path": f"synthetic/{movie}.sav",
                "sha256": sha256_bytes(f"state-{index}".encode()),
            },
        })
    return {
        "schema": CAPSULE_SET_SCHEMA, "complete": True, "capsule_count": 3,
        "capsules": capsules,
        "errors": [],
        "reproducibility_comparison": {"mismatches": [],
                                        "frame_chunks_byte_identical": True},
    }


def _event(capsule_id: str, movie: str, cohort: str, frame: int, domain: str,
           key: str, before: str | None, after: str | None,
           block_pc: str | None = None, count: int = 0) -> dict[str, Any]:
    return {"capsule_id": capsule_id, "movie": movie, "cohort": cohort,
            "frame": frame, "domain": domain, "key": key,
            "before_hex": before, "after_hex": after,
            "block_pc": block_pc, "block_count": count}


def build_pilot() -> dict[str, Any]:
    policy = load_policy()
    duckdb = import_duckdb()
    capsule_set = _synthetic_capsule_set()
    events = [
        _event("p", "positive.movie", "positive", 2, "ram", "player.hp", "0a", "09"),
        _event("p", "positive.movie", "positive", 5, "ram", "goal.flag", "00", "01"),
        _event("p", "positive.movie", "positive", 1, "register", "v0", "00", "01"),
        _event("p", "positive.movie", "positive", 2, "block", "0x80010000", None, None,
               "0x80010000", 12),
        _event("n", "negative.movie", "negative", 3, "ram", "player.hp", "0a", "0a"),
        _event("n", "negative.movie", "negative", 3, "block", "0x80010000", None, None,
               "0x80010000", 2),
        _event("c", "control.movie", "control", 4, "ram", "player.hp", "0a", "0a"),
        _event("c", "control.movie", "control", 4, "block", "0x80020000", None, None,
               "0x80020000", 3),
    ]
    with tempfile.TemporaryDirectory(prefix="abl-phase4-warehouse-") as temp:
        temp_root = Path(temp)
        dataset = temp_root / "dataset"
        dataset.mkdir()
        capsule_path = temp_root / "capsules.json"
        capsule_path.write_bytes(canonical_json(capsule_set))
        partition_path = dataset / "events.jsonl"
        partition_bytes = b"".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            for row in events)
        partition_path.write_bytes(partition_bytes)
        bindings = []
        for capsule_id, cohort, capsule in zip(
                ("p", "n", "c"), ("positive", "negative", "control"),
                capsule_set["capsules"]):
            bindings.append({
                "id": capsule_id, "movie": capsule["movie"], "cohort": cohort,
                "capsule_manifest_sha256": capsule["capsule_manifest_sha256"],
                "capsule_tree_sha256": capsule["capsule_tree_sha256"],
            })
        import_doc = {
            "schema": IMPORT_SCHEMA,
            "capsule_set_sha256": sha256_bytes(canonical_json(capsule_set)),
            "capsules": bindings,
            "partitions": [{"path": "events.jsonl", "sha256": sha256_bytes(partition_bytes),
                            "bytes": len(partition_bytes), "rows": len(events)}],
        }
        manifest_path = dataset / "import.json"
        manifest_path.write_bytes(canonical_json(import_doc))
        built = build_warehouse(manifest_path, capsule_path, temp_root / "warehouse")
    return {
        "schema": PILOT_SCHEMA,
        "runtime_evidence": False,
        "synthetic_only": True,
        "engine": {"name": "DuckDB", "version": duckdb.__version__,
                   "extensions_allowed": False},
        "inputs": {"capsules": 3, "events": len(events), "domains": 3},
        "queries": built["queries"],
        "summary": {"query_packs": len(QUERY_SQL), "failures": 0},
        "production_contract": {
            "capsule_set_complete_and_control_matched": True,
            "external_database_and_parquet_only": True,
            "frame_boundary_localization_not_exact_causality": True,
            "event_frame_interval": EVENT_FRAME_CONTRACT,
            "campaign_promotion": False,
        },
        "source_dependencies": {
            "tools/phase4_trace_warehouse.py": sha256_file(Path(__file__)),
            "config/phase4_trace_warehouse.yaml": sha256_file(POLICY_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--import-manifest", type=Path, required=True)
    build.add_argument("--capsule-set", type=Path, default=CAPSULE_SET_PATH)
    build.add_argument("--output-dir", type=Path, required=True)
    sub.add_parser("pilot")
    args = parser.parse_args()
    if args.command == "build":
        report = build_warehouse(args.import_manifest, args.capsule_set, args.output_dir)
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0
    report = build_pilot()
    PILOT_PATH.write_bytes(canonical_json(report))
    print(f"[phase4-trace-warehouse] {report['summary']['query_packs']} synthetic query packs; OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
