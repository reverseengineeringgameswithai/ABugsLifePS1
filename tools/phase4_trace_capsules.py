#!/usr/bin/env python3
"""Validate the external Phase-4 trace-capsule preservation set and emit hash-only repository metadata."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MOVIES = ROOT / "movies" / "Phase4"
DEFAULT_OUTPUT = ROOT / "analysis" / "phase4_trace_capsule_set.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(root: Path, movie: Path) -> str:
    return str(movie.relative_to(root)).removesuffix(".movie.json").replace("/", "__")


def repository_movie_path(movie_root: Path, movie: Path) -> str:
    """Return a stable logical fixture path when media is provisioned externally."""
    return str(Path("movies") / "Phase4" / movie.relative_to(movie_root))


def repository_start_state(start_state: dict | None) -> dict | None:
    """Strip host paths while retaining the centrally pinned save identity."""
    if not start_state:
        return None
    rel = Path(start_state.get("path", ""))
    logical = rel if rel.parts[:2] == ("movies", "Phase4") else Path("movies") / "Phase4" / rel
    return {
        "path": str(logical),
        "sha256": start_state.get("sha256"),
        "bytes": start_state.get("bytes"),
    }


def validate(capsule_root: Path, movie_root: Path, comparison_root: Path | None = None,
             require_comparison: bool = False, binary_snapshot: Path | None = None,
             offline_reader_snapshot: Path | None = None) -> dict:
    movies = sorted(movie_root.rglob("*.movie.json"))
    rows = []
    total_bytes = total_frames = 0
    errors = []
    collection_path = capsule_root / "collection.json"
    collection = json.loads(collection_path.read_text()) if collection_path.is_file() else {}
    collection_sha = sha256(collection_path) if collection_path.is_file() else None
    if not collection:
        errors.append(f"missing collection manifest: {collection_path}")
    for media_file in collection.get("media_files", []):
        path = Path(media_file.get("absolute_path", ""))
        if not path.is_file() or sha256(path) != media_file.get("sha256"):
            errors.append(f"pristine media pin mismatch: {path}")
    source_snapshot = collection.get("duckstation_source_snapshot", {})
    source_path = Path(source_snapshot.get("absolute_path", ""))
    if not source_path.is_file() or sha256(source_path) != source_snapshot.get("sha256"):
        errors.append(f"DuckStation source snapshot missing or hash-mismatched: {source_path}")
    binary_hashes = set()
    for movie in movies:
        directory = capsule_root / safe_name(movie_root, movie)
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            errors.append(f"missing manifest: {manifest_path}")
            continue
        manifest = json.loads(manifest_path.read_text())
        movie_hash = sha256(movie)
        if not manifest.get("complete"):
            errors.append(f"not complete: {manifest_path}")
        if manifest.get("movie", {}).get("sha256") != movie_hash:
            errors.append(f"movie hash mismatch: {movie}")
        if manifest.get("authority", {}).get("expected_serial") != "SCUS-94288":
            errors.append(f"wrong authority serial: {manifest_path}")
        if manifest.get("control", {}).get("mismatches"):
            errors.append(f"control mismatch retained: {manifest_path}")
        if manifest.get("capture", {}).get("status", {}).get("truncated"):
            errors.append(f"truncated capsule: {manifest_path}")
        if manifest.get("authority", {}).get("collection_manifest", {}).get("sha256") != collection_sha:
            errors.append(f"collection-manifest reference mismatch: {manifest_path}")

        files = manifest.get("files", [])
        tree_digest = hashlib.sha256()
        capsule_bytes = 0
        for file in files:
            path = directory / file["path"]
            if not path.is_file():
                errors.append(f"missing capsule file: {path}")
                continue
            actual = sha256(path)
            if actual != file.get("sha256") or path.stat().st_size != file.get("bytes"):
                errors.append(f"capsule file pin mismatch: {path}")
            tree_digest.update(file["path"].encode())
            tree_digest.update(b"\0")
            tree_digest.update(actual.encode())
            tree_digest.update(b"\0")
            capsule_bytes += path.stat().st_size

        total_bytes += capsule_bytes
        total_frames += manifest.get("frame_count", 0)
        binary_hash = manifest.get("duckstation", {}).get("capabilities", {}).get("binary", {}).get("sha256")
        if binary_hash:
            binary_hashes.add(binary_hash)
        else:
            errors.append(f"missing running DuckStation binary hash: {manifest_path}")
        rows.append({
            "movie": repository_movie_path(movie_root, movie),
            "movie_sha256": movie_hash,
            "movie_bytes": movie.stat().st_size,
            "start_state": repository_start_state(manifest.get("start_state")),
            "frames": manifest.get("frame_count"),
            "capsule_directory": str(directory),
            "capsule_manifest_sha256": sha256(manifest_path),
            "capsule_tree_sha256": tree_digest.hexdigest(),
            "capsule_file_count": len(files),
            "capsule_bytes": capsule_bytes,
            "block_mode": manifest.get("capture", {}).get("status", {}).get("block_mode"),
            "duckstation_binary_sha256": binary_hash,
            "control_match": not bool(manifest.get("control", {}).get("mismatches")),
            "preservation_required": True,
            "media_class": "external copyrighted/game-derived evidence; never commit",
        })

    binary_snapshot_row = None
    if len(binary_hashes) != 1:
        errors.append(f"capsules do not identify one exact DuckStation binary: {sorted(binary_hashes)}")
    if binary_snapshot:
        if not binary_snapshot.is_file():
            errors.append(f"DuckStation binary snapshot missing: {binary_snapshot}")
        else:
            binary_snapshot_hash = sha256(binary_snapshot)
            if binary_hashes and binary_snapshot_hash not in binary_hashes:
                errors.append(f"DuckStation binary snapshot hash mismatch: {binary_snapshot}")
            binary_snapshot_row = {
                "absolute_path": str(binary_snapshot),
                "bytes": binary_snapshot.stat().st_size,
                "sha256": binary_snapshot_hash,
            }
    else:
        errors.append("exact DuckStation binary snapshot was not declared")

    offline_reader_row = None
    if offline_reader_snapshot:
        if not offline_reader_snapshot.is_file():
            errors.append(f"offline capsule reader snapshot missing: {offline_reader_snapshot}")
        else:
            offline_reader_row = {
                "absolute_path": str(offline_reader_snapshot),
                "bytes": offline_reader_snapshot.stat().st_size,
                "sha256": sha256(offline_reader_snapshot),
            }
    else:
        errors.append("exact offline capsule reader snapshot was not declared")

    batch_path = capsule_root / "batch.json"
    if not batch_path.is_file():
        errors.append(f"missing batch manifest: {batch_path}")
        batch_sha = None
    else:
        batch = json.loads(batch_path.read_text())
        batch_sha = sha256(batch_path)
        if batch.get("failures") or len(batch.get("completed", [])) != len(movies):
            errors.append("batch.json does not report every movie complete")

    comparison = None
    if comparison_root:
        exact = 0
        checkpoint_exact = 0
        mismatches = []
        checkpoint_differences = []
        for movie in movies:
            name = safe_name(movie_root, movie)
            left_path = capsule_root / name / "manifest.json"
            right_path = comparison_root / name / "manifest.json"
            if not left_path.is_file() or not right_path.is_file():
                mismatches.append({"movie": repository_movie_path(movie_root, movie),
                                   "reason": "missing manifest"})
                continue
            left_files = json.loads(left_path.read_text()).get("files", [])
            right_files = json.loads(right_path.read_text()).get("files", [])
            left = {row["path"]: row["sha256"] for row in left_files if row["path"].startswith("chunks/")}
            right = {row["path"]: row["sha256"] for row in right_files if row["path"].startswith("chunks/")}
            left_checkpoints = {row["path"]: row["sha256"] for row in left_files
                                if row["path"].startswith("checkpoints/")}
            right_checkpoints = {row["path"]: row["sha256"] for row in right_files
                                 if row["path"].startswith("checkpoints/")}
            if left == right and left:
                exact += 1
            else:
                mismatches.append({"movie": repository_movie_path(movie_root, movie),
                                   "reason": "frame-chunk hashes differ"})
            if left_checkpoints == right_checkpoints and left_checkpoints:
                checkpoint_exact += 1
            else:
                checkpoint_differences.append(repository_movie_path(movie_root, movie))
        comparison = {"root": str(comparison_root), "exact_capsules": exact, "requested": len(movies),
                      "mismatches": mismatches,
                      "frame_chunks_byte_identical": exact == len(movies) and not mismatches,
                      "checkpoint_exact_capsules": checkpoint_exact,
                      "checkpoint_differences": checkpoint_differences,
                      "checkpoint_note": "Flat save-state blobs include bounded session/host serialization bytes; "
                                         "frame-domain chunks and within-run control fingerprints are authoritative."}
        if require_comparison and mismatches:
            errors.append(f"reproducibility comparison has {len(mismatches)} mismatches")

    return {
        "_comment": "Hash-only preservation index for external Phase-4 trace capsules. No movie/save/state bytes belong in Git.",
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-trace-capsule-set-v1",
        "authority": "hash-verified pristine SCUS-94288 retail media; ALLMODS is not an input",
        "generator": "python3 tools/phase4_trace_capsules.py --capsule-root <final-root> "
                     "--comparison-root <independent-root> --require-byte-identical-comparison "
                     "--binary-snapshot <exact-running-binary> "
                     "--offline-reader-snapshot <exact-offline-reader> --write",
        "capsule_root": str(capsule_root),
        "batch_manifest_sha256": batch_sha,
        "collection_manifest_sha256": collection_sha,
        "duckstation_source_snapshot": source_snapshot,
        "duckstation_binary_snapshot": binary_snapshot_row,
        "offline_reader_snapshot": offline_reader_row,
        "pristine_media": collection.get("media_files", []),
        "movie_count": len(movies),
        "capsule_count": len(rows),
        "total_movie_frames": total_frames,
        "total_external_bytes": total_bytes,
        "preservation_contract": {
            "required": ["capsule root including batch.json, per-capsule manifest/chunks/checkpoints",
                         "movies/Phase4 movie/save fixture set", "the exact DuckStation binary snapshot",
                         "the exact DuckStation source snapshot", "the exact offline reader snapshot"],
            "repository_retains": "hashes, roles, commands, schemas, tests, and Obsidian links only",
            "offline_reader": offline_reader_row,
        },
        "capsules": rows,
        "reproducibility_comparison": comparison,
        "errors": errors,
        "complete": not errors and len(rows) == len(movies),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capsule-root", type=Path, required=True)
    parser.add_argument("--movie-root", type=Path, default=DEFAULT_MOVIES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--comparison-root", type=Path)
    parser.add_argument("--binary-snapshot", type=Path, required=True)
    parser.add_argument("--offline-reader-snapshot", type=Path, required=True)
    parser.add_argument("--require-byte-identical-comparison", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = validate(args.capsule_root.resolve(), args.movie_root.resolve(),
                      args.comparison_root.resolve() if args.comparison_root else None,
                      args.require_byte_identical_comparison, args.binary_snapshot.resolve(),
                      args.offline_reader_snapshot.resolve())
    if args.check and args.output.is_file():
        # Freshness is about regenerated facts, not the wall-clock date of the validation run.
        report["generated"] = json.loads(args.output.read_text()).get("generated", report["generated"])
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write:
        args.output.write_text(rendered)
    elif args.check:
        if not args.output.is_file() or args.output.read_text() != rendered:
            print("phase4 trace-capsule preservation index is missing or stale", file=sys.stderr)
            return 1
    else:
        print(rendered, end="")
    if not report["complete"]:
        for error in report["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {report['capsule_count']}/{report['movie_count']} capsules, "
          f"{report['total_external_bytes']} external bytes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
