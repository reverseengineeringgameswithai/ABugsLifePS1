#!/usr/bin/env python3
"""Catalog reusable Phase-4 external indexes so agents do not rescan capsules."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import sys

import phase4_common as common


POLICY = common.ROOT / "config/phase4_offline_queue.yaml"
CAPSULES = common.ROOT / "analysis/phase4_trace_capsule_set.json"
OUTPUT = common.ROOT / "analysis/phase4_derived_index.json"


def supported_index_schema(value: object) -> bool:
    return (isinstance(value, str)
            and value.startswith("abl-phase4-external-")
            and value.endswith("-index/1"))


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = json.loads(OUTPUT.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def build(policy: dict | None = None, capsule_doc: dict | None = None) -> dict:
    policy = policy or common.load_yaml(POLICY)
    capsule_doc = capsule_doc or common.load_json(CAPSULES)
    baseline_rows = set(common.baseline_rows())
    capsule_by_movie = {row["movie"]: row for row in capsule_doc.get("capsules") or []}
    errors: list[str] = []
    if policy.get("schema") != "abl-phase4-offline-queue-policy/1":
        errors.append("offline queue policy schema is invalid")
    indexes: dict[tuple[str, str], dict] = {}
    row_sources: dict[str, list[dict]] = defaultdict(list)
    artifact_rows: list[dict] = []
    for declaration in policy.get("offline_analysis_artifacts") or []:
        rel = str(declaration.get("path") or "")
        artifact_path = common.ROOT / rel
        if not artifact_path.is_file():
            errors.append(f"offline artifact is missing: {rel}")
            continue
        document = common.load_json(artifact_path)
        if document.get("schema") != declaration.get("schema"):
            errors.append(f"offline artifact schema mismatch: {rel}")
        if document.get("errors"):
            errors.append(f"offline artifact reports errors: {rel}")
        external = document.get("external_index") or {}
        absolute = Path(str(external.get("absolute_path") or ""))
        expected_hash = str(external.get("sha256") or "")
        external_schema = external.get("schema")
        if not supported_index_schema(external_schema):
            errors.append(f"external derived index schema is unsupported: {rel}")
        if not absolute.is_file():
            errors.append(f"external derived index is absent: {absolute}")
        elif common.sha256(absolute) != expected_hash:
            errors.append(f"external derived index hash mismatch: {absolute}")
        elif absolute.stat().st_size != external.get("bytes"):
            errors.append(f"external derived index size mismatch: {absolute}")
        key = (str(absolute), expected_hash)
        index = indexes.setdefault(key, {
            "absolute_path": str(absolute),
            "sha256": expected_hash,
            "bytes": external.get("bytes"),
            "schema": external_schema,
            "preservation_required": external.get("preservation_required") is True,
            "consuming_artifacts": [],
            "rows": [],
            "movies": [],
            "domains": [],
            "reconstructed_records": 0,
        })
        index["consuming_artifacts"].append(rel)
        selected = document.get("selected_rows") or []
        selected_ids: list[str] = []
        selected_movies: set[str] = set()
        for selected_row in selected:
            row_id = selected_row.get("row_id")
            if row_id not in baseline_rows:
                errors.append(f"{rel}: selected unknown row {row_id}")
                continue
            selected_ids.append(row_id)
            movies = selected_row.get("capsules") or []
            for movie in movies:
                if movie not in capsule_by_movie:
                    errors.append(f"{rel}: selected capsule is not current: {movie}")
                selected_movies.add(movie)
            row_sources[row_id].append({
                "artifact": rel,
                "artifact_sha256": common.sha256(artifact_path),
                "external_index_sha256": expected_hash,
                "movies": sorted(movies),
            })
        index["rows"] = sorted(set(index["rows"]) | set(selected_ids))
        index["movies"] = sorted(set(index["movies"]) | selected_movies)
        offline = document.get("offline_batch") or {}
        index["domains"] = sorted(set(index["domains"]) | set(offline.get("domains") or []))
        index["reconstructed_records"] = max(
            int(index["reconstructed_records"] or 0),
            int(offline.get("reconstructed_records") or 0),
        )
        artifact_rows.append({
            "path": rel,
            "sha256": common.sha256(artifact_path),
            "schema": document.get("schema"),
            "selected_rows": sorted(selected_ids),
            "external_index": str(absolute),
            "external_index_sha256": expected_hash,
        })
    index_rows = []
    for row in indexes.values():
        for key in ("consuming_artifacts", "rows", "movies", "domains"):
            row[key] = sorted(set(row[key]))
        if not row["preservation_required"]:
            errors.append(f"external derived index is not preservation-required: {row['absolute_path']}")
        index_rows.append(row)
    return {
        "_comment": "Central hash-only catalog of reusable external Phase-4 derived indexes. Query these before scanning retained capsules again; index bytes remain external and copyrighted/game-derived bytes are never committed.",
        "schema": "abl-phase4-derived-index/1",
        "generated": stable_generated(),
        "inputs": {
            "generator_sha256": common.sha256(Path(__file__)),
            "common_helper_sha256": common.sha256(common.ROOT / "tools/phase4_common.py"),
            "offline_policy_sha256": common.sha256(POLICY),
            "capsule_set_sha256": common.sha256(CAPSULES),
        },
        "artifacts": sorted(artifact_rows, key=lambda row: row["path"]),
        "external_indexes": sorted(index_rows, key=lambda row: row["absolute_path"]),
        "rows": [
            {"row_id": row_id, "sources": sorted(sources, key=lambda row: row["artifact"])}
            for row_id, sources in sorted(row_sources.items())
        ],
        "counts": {
            "offline_artifacts": len(artifact_rows),
            "unique_external_indexes": len(index_rows),
            "rows_with_derived_indexes": len(row_sources),
            "movies_indexed": len({movie for row in index_rows for movie in row["movies"]}),
            "external_bytes": sum(int(row["bytes"] or 0) for row in index_rows),
        },
        "errors": sorted(set(errors)),
        "valid": not errors,
    }


def render(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    text = render(document)
    if document["errors"]:
        for error in document["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.write:
        OUTPUT.write_text(text)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != text:
            print("Phase-4 derived-index catalog is missing or stale", file=sys.stderr)
            return 1
    else:
        print(text, end="")
    print(
        f"PASS: {document['counts']['unique_external_indexes']} reusable indexes, "
        f"{document['counts']['rows_with_derived_indexes']} rows", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
