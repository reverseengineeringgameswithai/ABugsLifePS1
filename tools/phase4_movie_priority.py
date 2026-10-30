#!/usr/bin/env python3
"""Generate and select the Phase-4 movie-ready work-order queue."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from copy import deepcopy
from datetime import date
from fractions import Fraction
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any
import zlib

import yaml

import phase4_closure_debt
import phase4_common as common
import phase4_derived_index
import phase4_inventory
import phase4_offline_queue
import phase4_scheduler_policy as scheduler_policy


POLICY_PATH = common.ROOT / "config/phase4_movie_priority.yaml"
SCHEDULER_POLICY_PATH = scheduler_policy.POLICY_PATH
DEBT_PATH = common.ROOT / "analysis/phase4_closure_debt.json"
OFFLINE_PATH = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
FIXTURE_AUDIT_PATH = common.ROOT / "analysis/phase4_fixture_audit.json"
FIXTURE_SET_PATH = common.FIXTURE_SET_PATH
MOVIE_INVENTORY_PATH = common.ROOT / "analysis/phase4_movie_inventory.json"
CAPSULE_PATH = common.ROOT / "analysis/phase4_trace_capsule_set.json"
DERIVED_PATH = common.ROOT / "analysis/phase4_derived_index.json"
OWNERSHIP_PATH = common.ROOT / "analysis/phase3_ownership_graph.json"
OUTPUT = common.ROOT / "analysis/phase4_movie_priority_queue.json"
SCHEMA = "abl-phase4-movie-priority-queue/2"
PACKET_SCHEMA = scheduler_policy.PACKET_SCHEMA
EXPECTED_SCORE_COMPONENTS = (
    "retained_evidence",
    "static_ownership",
    "bounded_frontier",
    "control_quality",
    "remaining_debt",
    "dependency_leverage",
)
SOURCE_KEYS = (
    "policy", "scheduler", "debt", "offline", "fixture_audit",
    "fixture_set", "movie_inventory", "capsule", "derived", "ownership",
)
SOURCE_PATHS = {
    "policy": POLICY_PATH,
    "scheduler": SCHEDULER_POLICY_PATH,
    "debt": DEBT_PATH,
    "offline": OFFLINE_PATH,
    "fixture_audit": FIXTURE_AUDIT_PATH,
    "fixture_set": FIXTURE_SET_PATH,
    "movie_inventory": MOVIE_INVENTORY_PATH,
    "capsule": CAPSULE_PATH,
    "derived": DERIVED_PATH,
    "ownership": OWNERSHIP_PATH,
}
SOURCE_INPUT_KEYS = {
    "policy": "policy_sha256",
    "scheduler": "scheduler_policy_sha256",
    "debt": "closure_debt_sha256",
    "offline": "offline_queue_sha256",
    "fixture_audit": "fixture_audit_sha256",
    "fixture_set": "fixture_set_sha256",
    "movie_inventory": "movie_inventory_sha256",
    "capsule": "capsule_catalog_sha256",
    "derived": "derived_index_sha256",
    "ownership": "ownership_sha256",
}


def _encode_source(raw: bytes) -> str:
    return base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")


def _decode_source(value: Any, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is not non-empty canonical zlib/base64")
    try:
        raw = zlib.decompress(base64.b64decode(value, validate=True))
    except (ValueError, zlib.error) as exc:
        raise ValueError(f"{label} is not valid zlib/base64") from exc
    if _encode_source(raw) != value:
        raise ValueError(f"{label} is not canonical zlib/base64")
    return raw


def _parse_source(name: str, raw: bytes) -> dict:
    try:
        document = yaml.safe_load(raw.decode("utf-8")) if name in {
            "policy", "scheduler"} else json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ValueError(f"queue source {name} is invalid: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"queue source {name} must be one object")
    return document


def _canonical_source_bytes(name: str, document: dict) -> bytes:
    if name in {"policy", "scheduler"}:
        return yaml.safe_dump(
            document, sort_keys=False, allow_unicode=True).encode("utf-8")
    return json_bytes(document)


def decode_source_snapshot(snapshot: Any) -> tuple[str, dict[str, bytes], dict[str, dict]]:
    if not isinstance(snapshot, dict) or set(snapshot) != {"generated", "sources"}:
        raise ValueError("queue source snapshot fields are not exact")
    generated = snapshot.get("generated")
    sources = snapshot.get("sources")
    if not isinstance(generated, str) or not generated or \
            not isinstance(sources, dict) or set(sources) != set(SOURCE_KEYS):
        raise ValueError("queue source snapshot identity is invalid")
    raw = {name: _decode_source(sources[name], f"queue source {name}")
           for name in SOURCE_KEYS}
    return generated, raw, {name: _parse_source(name, raw[name])
                            for name in SOURCE_KEYS}


def _runtime_path_facts(path: Path, recursive: bool = False) -> list[list[object]]:
    if not path.exists() and not path.is_symlink():
        return [[str(path), "missing"]]
    paths = [path]
    if recursive and path.is_dir() and not path.is_symlink():
        paths.extend(sorted(path.rglob("*")))
    facts: list[list[object]] = []
    for item in paths:
        stat = item.lstat()
        facts.append([
            str(item), item.is_file(), item.is_dir(), item.is_symlink(),
            stat.st_dev, stat.st_ino, stat.st_size,
            stat.st_mtime_ns, stat.st_ctime_ns,
        ])
    return facts


def authority_runtime_fingerprint(
        fixture_set: dict, movie_inventory: dict, capsule_doc: dict,
        derived: dict) -> str:
    """Fingerprint every mutable runtime byte/tree used by one queue snapshot."""
    files: set[Path] = set()
    for logical in (fixture_set.get("entries") or {}):
        if isinstance(logical, str) and logical:
            files.add(common.ROOT / logical)
    for row in movie_inventory.get("files") or []:
        logical = row.get("path") if isinstance(row, dict) else None
        if isinstance(logical, str) and logical:
            files.add(common.ROOT / logical)
    for row in derived.get("external_indexes") or []:
        absolute = row.get("absolute_path") if isinstance(row, dict) else None
        if isinstance(absolute, str) and absolute:
            files.add(Path(absolute))
    facts: list[object] = []
    for path in sorted(files):
        facts.extend(_runtime_path_facts(path))
    directories = sorted({
        str(item.get("capsule_directory") or "")
        for item in capsule_doc.get("capsules") or []
    })
    for raw_directory in directories:
        directory = Path(raw_directory)
        facts.append([raw_directory, _runtime_path_facts(directory, True)])
    return hashlib.sha256(json.dumps(
        facts, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def json_bytes(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def document_sha256(document: dict) -> str:
    return hashlib.sha256(json_bytes(document)).hexdigest()


def _phase4_path(value: str) -> bool:
    parts = PurePosixPath(value).parts
    return len(parts) >= 3 and parts[:2] == ("movies", "Phase4")


def _current_file(path: str, inventory_row: dict | None,
                  pin: dict | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    actual = common.ROOT / path
    if inventory_row is None:
        errors.append(f"{path}: absent from the current movie inventory")
        return False, errors
    if not actual.is_file() or actual.is_symlink():
        errors.append(f"{path}: provisioned file is absent or is a symlink")
        return False, errors
    actual_hash = common.sha256(actual)
    actual_size = actual.stat().st_size
    if inventory_row.get("sha256") != actual_hash or \
            inventory_row.get("bytes") != actual_size:
        errors.append(f"{path}: movie inventory disagrees with provisioned bytes")
    if pin is None:
        errors.append(f"{path}: central fixture pin is absent")
    else:
        if pin.get("sha256") != actual_hash or pin.get("size") != actual_size:
            errors.append(f"{path}: central fixture pin does not verify current bytes")
        if pin.get("preservation_required") is not True:
            errors.append(f"{path}: central fixture is not preservation-required")
    if inventory_row.get("centrally_declared") is not True or \
            inventory_row.get("declared_hash_matches") is not True or \
            inventory_row.get("declared_size_matches") is not True:
        errors.append(f"{path}: movie inventory does not verify its central pin")
    return not errors, errors


def _capsule_status(capsule: dict | None, movie_path: str,
                    movie_hash: str, state_path: str,
                    state_hash: str,
                    verification_cache: dict[tuple, tuple[dict, list[str]]]
                    | None = None) -> tuple[dict | None, list[str]]:
    if capsule is None:
        return None, []
    errors: list[str] = []
    directory = Path(str(capsule.get("capsule_directory") or ""))
    manifest = directory / "manifest.json"
    manifest_doc: dict = {}
    if capsule.get("preservation_required") is not True:
        errors.append(f"{movie_path}: capsule is not preservation-required")
    if not manifest.is_file() or manifest.is_symlink():
        errors.append(f"{movie_path}: capsule manifest is missing")
    elif common.sha256(manifest) != capsule.get("capsule_manifest_sha256"):
        errors.append(f"{movie_path}: capsule manifest hash mismatch")
    else:
        try:
            manifest_doc = common.load_json(manifest)
        except (OSError, json.JSONDecodeError):
            errors.append(f"{movie_path}: capsule manifest is invalid JSON")
    if capsule.get("movie_sha256") != movie_hash:
        errors.append(f"{movie_path}: capsule movie hash differs from the central pin")
    start = capsule.get("start_state") or {}
    if start.get("path") != state_path or start.get("sha256") != state_hash:
        errors.append(f"{movie_path}: capsule start-state identity differs")
    tree_hash = capsule.get("capsule_tree_sha256")
    if not isinstance(tree_hash, str) or len(tree_hash) != 64 or \
            set(tree_hash) - set("0123456789abcdef"):
        errors.append(f"{movie_path}: capsule tree identity is invalid")

    # A positive preservation result must describe bytes that still exist now.
    # Reusing a prior result from declared metadata alone lets a payload disappear
    # or drift between two anchors while the second anchor keeps its evidence
    # credit.  Keep the parameter for API compatibility, but deliberately rehash
    # the tree on every observation.
    tree_result = None
    if tree_result is None:
        tree_errors: list[str] = []
        tree_facts = {"tree_verified": False}
        files = manifest_doc.get("files") if manifest_doc else None
        if not isinstance(files, list) or not files:
            tree_errors.append(f"{movie_path}: capsule payload manifest is empty/invalid")
        else:
            declared_paths: list[str] = []
            tree_digest = hashlib.sha256()
            total_bytes = 0
            for index, file_row in enumerate(files):
                if not isinstance(file_row, dict) or set(file_row) != {
                        "path", "sha256", "bytes"}:
                    tree_errors.append(
                        f"{movie_path}: capsule payload row {index} is invalid")
                    continue
                logical = file_row.get("path")
                digest = file_row.get("sha256")
                size = file_row.get("bytes")
                pure = PurePosixPath(logical) if isinstance(logical, str) else None
                if pure is None or pure.is_absolute() or not pure.parts or \
                        any(part in {"", ".", ".."} for part in pure.parts) or \
                        "\\" in logical:
                    tree_errors.append(
                        f"{movie_path}: capsule payload path {logical!r} is unsafe")
                    continue
                if logical in declared_paths:
                    tree_errors.append(
                        f"{movie_path}: capsule payload path {logical!r} is duplicated")
                    continue
                declared_paths.append(logical)
                if not isinstance(digest, str) or len(digest) != 64 or \
                        set(digest) - set("0123456789abcdef") or \
                        type(size) is not int or size < 0:
                    tree_errors.append(
                        f"{movie_path}: capsule payload pin {logical!r} is invalid")
                    continue
                payload = directory.joinpath(*pure.parts)
                if not payload.is_file() or payload.is_symlink():
                    tree_errors.append(
                        f"{movie_path}: capsule payload is missing/symlink: {logical}")
                    continue
                actual_size = payload.stat().st_size
                actual_hash = common.sha256(payload)
                if actual_size != size or actual_hash != digest:
                    tree_errors.append(
                        f"{movie_path}: capsule payload pin mismatch: {logical}")
                    continue
                tree_digest.update(logical.encode())
                tree_digest.update(b"\0")
                tree_digest.update(actual_hash.encode())
                tree_digest.update(b"\0")
                total_bytes += actual_size
            actual_paths: set[str] = set()
            if directory.is_dir() and not directory.is_symlink():
                for actual in directory.rglob("*"):
                    if actual.is_symlink():
                        tree_errors.append(
                            f"{movie_path}: capsule tree contains a symlink: {actual}")
                    elif actual.is_file() and actual != manifest:
                        actual_paths.add(actual.relative_to(directory).as_posix())
            else:
                tree_errors.append(f"{movie_path}: capsule directory is invalid")
            if actual_paths != set(declared_paths):
                tree_errors.append(
                    f"{movie_path}: capsule payload tree does not exactly match manifest")
            if type(capsule.get("capsule_file_count")) is not int or \
                    capsule.get("capsule_file_count") != len(declared_paths):
                tree_errors.append(f"{movie_path}: capsule file count is not exact")
            if type(capsule.get("capsule_bytes")) is not int or \
                    capsule.get("capsule_bytes") != total_bytes:
                tree_errors.append(f"{movie_path}: capsule byte count is not exact")
            if not tree_errors and tree_digest.hexdigest() != tree_hash:
                tree_errors.append(f"{movie_path}: capsule tree hash mismatch")
            tree_facts = {
                "tree_verified": not tree_errors,
                "payload_file_count": len(declared_paths),
                "payload_bytes": total_bytes,
            }
        tree_result = (tree_facts, tree_errors)
    tree_facts, tree_errors = tree_result
    errors.extend(tree_errors)

    capture = (manifest_doc.get("capture") or {}).get("status") or {}
    if manifest_doc and (
            manifest_doc.get("complete") is not True
            or capture.get("complete") is not True
            or capture.get("truncated") is not False
            or capture.get("error") != ""):
        errors.append(f"{movie_path}: capsule manifest is incomplete/truncated")
    control = manifest_doc.get("control") or {}
    capsule_fingerprint = control.get("capsule_fingerprint") or {}
    control_fingerprint = control.get("control_fingerprint") or {}
    fingerprint_fields = {
        "registers": "registers_sha256",
        "ram": "ram_sha256",
        "vram": "vram_sha256",
        "spu_ram": "spu_ram_sha256",
    }
    verified_domains: list[str] = []
    for domain, field in fingerprint_fields.items():
        value = capsule_fingerprint.get(field)
        if isinstance(value, str) and len(value) == 64 and \
                not set(value) - set("0123456789abcdef"):
            verified_domains.append(domain)
    files = manifest_doc.get("files") or []
    declared_paths = {
        item.get("path") for item in files if isinstance(item, dict)
    }
    if capture.get("blocks", 0) > 0 and any(
            isinstance(path, str) and path.startswith("chunks/")
            for path in declared_paths):
        verified_domains.append("block_flow")
    if capture.get("checkpoints") and any(
            isinstance(path, str) and path.startswith("checkpoints/")
            for path in declared_paths):
        verified_domains.append("run_local_full_state_checkpoints")
    expected_domains = (
        "registers", "ram", "vram", "spu_ram", "block_flow",
        "run_local_full_state_checkpoints",
    )
    verified_domains = [domain for domain in expected_domains
                        if domain in verified_domains and
                        tree_facts.get("tree_verified") is True]
    independent_control = bool(
        tree_facts.get("tree_verified") is True
        and
        capsule.get("control_match") is True
        and control.get("mismatches") == {}
        and capsule_fingerprint
        and capsule_fingerprint == control_fingerprint)
    return {
        "movie": movie_path,
        "capsule_directory": str(directory),
        "capsule_manifest_sha256": capsule.get("capsule_manifest_sha256"),
        "capsule_tree_sha256": capsule.get("capsule_tree_sha256"),
        "capsule_file_count": capsule.get("capsule_file_count"),
        "capsule_bytes": capsule.get("capsule_bytes"),
        "control_match": capsule.get("control_match") is True,
        "independent_control_verified": independent_control,
        "verified_domains": verified_domains,
        "frames": capsule.get("frames"),
        "preservation_verified": not errors and manifest_doc != {},
    }, errors


def _anchor(movie_path: str, movie_rows: dict[str, dict],
            fixture_entries: dict[str, dict], capsules: dict[str, dict],
            policy: dict,
            capsule_verification_cache: dict[tuple, tuple[dict, list[str]]]
            | None = None) -> tuple[dict, list[str]]:
    errors: list[str] = []
    movie_row = movie_rows.get(movie_path)
    movie_pin = fixture_entries.get(movie_path)
    if not _phase4_path(movie_path):
        errors.append(
            f"{movie_path}: movie is not under case-sensitive movies/Phase4/")
    movie_ok, movie_errors = _current_file(movie_path, movie_row, movie_pin)
    errors.extend(movie_errors)
    movie_class = (movie_pin or {}).get("media_class")
    if movie_class not in set(policy.get("eligible_movie_media_classes") or []):
        errors.append(f"{movie_path}: movie media classification is not eligible")

    state_path = str((movie_row or {}).get("declared_start_state") or "")
    state_row = movie_rows.get(state_path)
    state_pin = fixture_entries.get(state_path)
    if not state_path:
        errors.append(f"{movie_path}: declared start-state path is absent")
    elif not _phase4_path(state_path):
        errors.append(
            f"{movie_path}: start state is not under case-sensitive movies/Phase4/")
    state_ok, state_errors = _current_file(state_path, state_row, state_pin) \
        if state_path else (False, [])
    errors.extend(state_errors)
    state_class = (state_pin or {}).get("media_class")
    if state_class not in set(
            policy.get("eligible_start_state_media_classes") or []):
        errors.append(f"{movie_path}: start-state media classification is not eligible")
    if (movie_row or {}).get("kind") != "movie":
        errors.append(f"{movie_path}: inventory kind is not movie")
    if state_path and (state_row or {}).get("kind") != "start_state":
        errors.append(f"{state_path}: inventory kind is not start_state")

    movie_hash = str((movie_pin or {}).get("sha256") or "")
    state_hash = str((state_pin or {}).get("sha256") or "")
    capsule_row, capsule_errors = _capsule_status(
        capsules.get(movie_path), movie_path, movie_hash, state_path, state_hash,
        capsule_verification_cache)
    errors.extend(capsule_errors)
    return {
        "movie": {
            "path": movie_path,
            "sha256": movie_hash or None,
            "bytes": (movie_pin or {}).get("size"),
            "media_class": movie_class,
            "central_pin_verified": movie_ok,
            "preservation_required": (movie_pin or {}).get(
                "preservation_required") is True,
            "frame_count": (movie_row or {}).get("declared_frame_count"),
        },
        "start_state": {
            "path": state_path or None,
            "sha256": state_hash or None,
            "bytes": (state_pin or {}).get("size"),
            "media_class": state_class,
            "central_pin_verified": state_ok,
            "preservation_required": (state_pin or {}).get(
                "preservation_required") is True,
        },
        "capsule": capsule_row,
        "verified": not errors,
        "errors": sorted(set(errors)),
    }, errors


def _derived_sources(
        row_id: str, derived: dict,
        verification_cache: dict[str, bool]) -> tuple[list[dict], list[str]]:
    row = next(
        (item for item in derived.get("rows") or []
         if item.get("row_id") == row_id),
        None,
    )
    if not row:
        return [], []
    indexes = {
        item["sha256"]: item for item in derived.get("external_indexes") or []
    }
    result: list[dict] = []
    errors: list[str] = []
    for source in row.get("sources") or []:
        sha = source.get("external_index_sha256")
        index = indexes.get(sha)
        if index is None:
            errors.append(
                f"{row_id}: derived source {sha!r} has no catalog index")
            continue
        path = Path(str(index.get("absolute_path") or ""))
        if sha not in verification_cache:
            verification_cache[sha] = (
                path.is_file()
                and not path.is_symlink()
                and path.stat().st_size == index.get("bytes")
                and common.sha256(path) == sha
                and index.get("preservation_required") is True
            )
        verified = verification_cache[sha]
        if not verified:
            errors.append(
                f"{row_id}: derived index preservation dependency is missing: {path}")
        result.append({
            "artifact": source.get("artifact"),
            "artifact_sha256": source.get("artifact_sha256"),
            "external_index": str(path),
            "external_index_sha256": sha,
            "domains": index.get("domains") or [],
            "movies": source.get("movies") or [],
            "preservation_verified": verified,
        })
    return result, errors


def _score(row: dict, queue_row: dict, ownership_row: dict,
           anchors: list[dict], derived_sources: list[dict],
           policy: dict) -> tuple[dict, int, str]:
    weights = policy["score_weights"]
    capsules = [anchor["capsule"] for anchor in anchors if anchor.get("capsule")]
    retained_inputs = {
        "capsules": len(capsules),
        "derived_indexes": len({
            item["external_index_sha256"] for item in derived_sources}),
        "prior_offline_analyses": len(
            queue_row.get("prior_offline_analysis") or []),
    }
    retained_points = min(
        int(weights["retained_evidence"]["maximum"]),
        (int(weights["retained_evidence"]["capsule"])
         if retained_inputs["capsules"] else 0)
        + (int(weights["retained_evidence"]["derived_index"])
           if retained_inputs["derived_indexes"] else 0)
        + (int(weights["retained_evidence"]["prior_offline_analysis"])
           if retained_inputs["prior_offline_analyses"] else 0),
    )

    functions = len(ownership_row.get("functions") or [])
    typed_state = len(ownership_row.get("state") or [])
    readers = sum(bool(item.get("sites") or item.get("evidence"))
                  for item in ownership_row.get("readers") or [])
    writers = sum(bool(item.get("sites") or item.get("evidence"))
                  for item in ownership_row.get("writers") or [])
    overlay_asset = bool(
        ownership_row.get("overlay") or ownership_row.get("assets"))
    static_inputs = {
        "functions": functions,
        "typed_state_records": typed_state,
        "reader_groups": readers,
        "writer_groups": writers,
        "overlay_or_asset_surface": overlay_asset,
    }
    static_points = min(
        int(weights["static_ownership"]["maximum"]),
        min(functions, 3) * int(weights["static_ownership"]["function"])
        + min(typed_state, 3) * int(weights["static_ownership"]["typed_state"])
        + (int(weights["static_ownership"]["readers"]) if readers else 0)
        + (int(weights["static_ownership"]["writers"]) if writers else 0)
        + (int(weights["static_ownership"]["overlay_or_asset"])
           if overlay_asset else 0),
    )

    blocker_domains = sorted(
        (ownership_row.get("frontier_blockers") or {}).keys())
    has_static_frontier = bool(functions or typed_state or readers or writers)
    bounded_points = 0
    if has_static_frontier:
        bounded_points = max(
            0,
            min(
                int(weights["bounded_frontier"]["maximum"]),
                int(weights["bounded_frontier"]["base"])
                - len(blocker_domains)
                * int(weights["bounded_frontier"]["per_open_domain_penalty"]),
            ),
        )

    all_anchor_controls = bool(capsules) and all(
        item.get("control_match") is True for item in capsules)
    control_points = min(
        int(weights["control_quality"]["maximum"]),
        (int(weights["control_quality"]["verified_movie_start_anchor"])
         if anchors and all(anchor["verified"] for anchor in anchors) else 0)
        + (int(weights["control_quality"]["independent_capsule_control"])
           if all_anchor_controls else 0),
    )

    remaining = int(row["derived_remaining"])
    remaining_points = max(
        0, min(int(weights["remaining_debt"]["maximum"]), 10 - remaining + 1))
    unlocks = int(row.get("dependency_unlock_count") or 0)
    leverage_points = min(
        int(weights["dependency_leverage"]["maximum"]),
        unlocks * int(weights["dependency_leverage"]["per_dependent_family"]),
    )
    components = {
        "retained_evidence": {
            "points": retained_points,
            "maximum": int(weights["retained_evidence"]["maximum"]),
            "inputs": retained_inputs,
            "rationale": (
                "Fixed availability bonuses for at least one retained capsule, "
                "derived index and prior offline analysis; movie quantity adds zero."),
        },
        "static_ownership": {
            "points": static_points,
            "maximum": int(weights["static_ownership"]["maximum"]),
            "inputs": static_inputs,
            "rationale": (
                "Rewards already typed functions/state/readers/writers and an "
                "asset/overlay surface, capped to prevent large catalogs dominating."),
        },
        "bounded_frontier": {
            "points": bounded_points,
            "maximum": int(weights["bounded_frontier"]["maximum"]),
            "inputs": {
                "has_static_frontier": has_static_frontier,
                "open_frontier_domains": blocker_domains,
            },
            "rationale": (
                "A declared static frontier starts at the fixed base and loses "
                "points for each named open ownership domain."),
        },
        "control_quality": {
            "points": control_points,
            "maximum": int(weights["control_quality"]["maximum"]),
            "inputs": {
                "verified_movie_start_anchor": bool(
                    anchors and all(anchor["verified"] for anchor in anchors)),
                "all_capsules_independently_control_matched": all_anchor_controls,
                "movie_count_not_scored": len(anchors),
            },
            "rationale": (
                "Scores anchor integrity and independent capsule controls once; "
                "having many movies does not make a row easy."),
        },
        "remaining_debt": {
            "points": remaining_points,
            "maximum": int(weights["remaining_debt"]["maximum"]),
            "inputs": {"derived_remaining_dimensions": remaining},
            "rationale": (
                "Fewer independently re-derived remaining dimensions lowers closure "
                "cost, without changing any dimension state."),
        },
        "dependency_leverage": {
            "points": leverage_points,
            "maximum": int(weights["dependency_leverage"]["maximum"]),
            "inputs": {"dependent_family_count": unlocks},
            "rationale": (
                "Rewards rows whose closure contract can unlock more dependent "
                "campaign families."),
        },
    }
    total = sum(item["points"] for item in components.values())
    rationale = (
        f"score={total}: retained={retained_points}, static={static_points}, "
        f"frontier={bounded_points}, controls={control_points}, "
        f"debt={remaining_points}, leverage={leverage_points}; "
        "movie count is not a score input"
    )
    return components, total, rationale


def _coupling(left: dict, right: dict) -> tuple[int, list[str]]:
    reasons: list[str] = []
    left_movies = {
        anchor["movie"]["sha256"] for anchor in left["movie_anchors"]}
    right_movies = {
        anchor["movie"]["sha256"] for anchor in right["movie_anchors"]}
    shared_movies = sorted(left_movies & right_movies)
    if shared_movies:
        reasons.append(
            "shared exact movie SHA-256: " + ", ".join(shared_movies))
    left_indexes = {
        item["external_index_sha256"] for item in left["derived_indexes"]}
    right_indexes = {
        item["external_index_sha256"] for item in right["derived_indexes"]}
    shared_indexes = sorted(left_indexes & right_indexes)
    if shared_indexes:
        reasons.append(
            "shared retained derived-index SHA-256: "
            + ", ".join(shared_indexes))
    if left.get("campaign_id") and left.get("campaign_id") == right.get("campaign_id"):
        reasons.append(f"shared active campaign: {left['campaign_id']}")
    return (
        len(shared_movies) * 4 + len(shared_indexes) * 3
        + (2 if left.get("campaign_id")
           and left.get("campaign_id") == right.get("campaign_id") else 0),
        reasons,
    )


def _batches(ranked: list[dict], maximum: int) -> list[dict]:
    remaining = list(ranked)
    result: list[dict] = []
    while remaining:
        seed = remaining.pop(0)
        selected = [seed]
        coupling: list[dict] = []
        while len(selected) < maximum and remaining:
            candidates: list[tuple[int, int, dict, list[str]]] = []
            for index, candidate in enumerate(remaining):
                best_strength = 0
                best_reasons: list[str] = []
                best_peer = None
                for peer in selected:
                    strength, reasons = _coupling(peer, candidate)
                    if strength > best_strength:
                        best_strength = strength
                        best_reasons = reasons
                        best_peer = peer["row_id"]
                if best_strength:
                    candidates.append((
                        -best_strength, index, candidate,
                        [f"{best_peer} -> {candidate['row_id']}: {reason}"
                         for reason in best_reasons],
                    ))
            if not candidates:
                break
            _, index, candidate, reasons = min(candidates)
            selected.append(candidate)
            coupling.append({
                "row_id": candidate["row_id"],
                "reasons": reasons,
            })
            remaining.pop(index)
        row_ids = [item["row_id"] for item in selected]
        result.append({
            "rank": len(result) + 1,
            "batch_id": "movie-ready:" + "+".join(row_ids),
            "rows": row_ids,
            "score_total": sum(item["score"]["total"] for item in selected),
            "coupling": coupling or [{
                "row_id": seed["row_id"],
                "reasons": [
                    "single-row campaign packet; no unrelated movie row was forced in"],
            }],
            "rationale": (
                "Highest remaining ranked seed plus at most two rows joined by "
                "an exact movie, retained derived index, or active campaign."),
        })
    return result


def _source_documents(
        debt: dict | None, offline: dict | None, fixture_audit: dict | None,
        movie_inventory: dict | None, capsule: dict | None,
        derived: dict | None,
) -> tuple[dict, dict, dict, dict, dict, dict, list[str]]:
    errors: list[str] = []
    capsule_doc = capsule or common.load_json(CAPSULE_PATH)
    if movie_inventory is None:
        movie_inventory = phase4_offline_queue.build_movie_inventory(
            common.ROOT / "movies", capsule_doc)
        retained = common.load_json(MOVIE_INVENTORY_PATH)
        if common.semantic_without_generated(retained) != \
                common.semantic_without_generated(movie_inventory):
            errors.append("movie inventory is stale against provisioned files")
    if offline is None:
        offline = phase4_offline_queue.build_queue(movie_inventory)
        retained = common.load_json(OFFLINE_PATH)
        if common.semantic_without_generated(retained) != \
                common.semantic_without_generated(offline):
            errors.append("offline opportunity queue is stale")
    if debt is None:
        debt = phase4_closure_debt.build(queue=offline)
        retained = common.load_json(DEBT_PATH)
        if common.semantic_without_generated(retained) != \
                common.semantic_without_generated(debt):
            errors.append("closure-debt ledger is stale")
    if fixture_audit is None:
        fixture_audit = phase4_inventory.build_fixture_audit()
        retained = common.load_json(FIXTURE_AUDIT_PATH)
        if common.semantic_without_generated(retained) != \
                common.semantic_without_generated(fixture_audit):
            errors.append("Phase-4 fixture audit is stale")
    if derived is None:
        derived = phase4_derived_index.build(capsule_doc=capsule_doc)
        retained = common.load_json(DERIVED_PATH)
        if common.semantic_without_generated(retained) != \
                common.semantic_without_generated(derived):
            errors.append("derived-index catalog is stale")
    return (
        debt, offline, fixture_audit, movie_inventory, capsule_doc, derived,
        errors,
    )


def build(
        *, policy: dict | None = None, debt: dict | None = None,
        offline: dict | None = None, fixture_audit: dict | None = None,
        fixture_set: dict | None = None, movie_inventory: dict | None = None,
        capsule: dict | None = None, derived: dict | None = None,
        ownership: dict | None = None, scheduler: dict | None = None,
        _source_raw: dict[str, bytes] | None = None,
        _generated: str | None = None,
) -> dict:
    provided = {
        "policy": policy is not None,
        "scheduler": scheduler is not None,
        "debt": debt is not None,
        "offline": offline is not None,
        "fixture_audit": fixture_audit is not None,
        "fixture_set": fixture_set is not None,
        "movie_inventory": movie_inventory is not None,
        "capsule": capsule is not None,
        "derived": derived is not None,
        "ownership": ownership is not None,
    }
    policy = policy or common.load_yaml(POLICY_PATH)
    scheduler = scheduler or common.load_yaml(SCHEDULER_POLICY_PATH)
    fixture_set = fixture_set or common.load_json(FIXTURE_SET_PATH)
    ownership = ownership or common.load_json(OWNERSHIP_PATH)
    debt, offline, fixture_audit, movie_inventory, capsule, derived, errors = \
        _source_documents(
            debt, offline, fixture_audit, movie_inventory, capsule, derived)
    documents = {
        "policy": policy,
        "scheduler": scheduler,
        "debt": debt,
        "offline": offline,
        "fixture_audit": fixture_audit,
        "fixture_set": fixture_set,
        "movie_inventory": movie_inventory,
        "capsule": capsule,
        "derived": derived,
        "ownership": ownership,
    }
    if _source_raw is not None and set(_source_raw) != set(SOURCE_KEYS):
        raise ValueError("queue source raw-byte universe is not exact")
    source_raw: dict[str, bytes] = {}
    for name in SOURCE_KEYS:
        if _source_raw is not None:
            raw = _source_raw[name]
            if not isinstance(raw, bytes):
                raise ValueError(f"queue source {name} must be raw bytes")
        elif not provided[name]:
            raw = SOURCE_PATHS[name].read_bytes()
        else:
            raw = _canonical_source_bytes(name, documents[name])
        parsed = _parse_source(name, raw)
        if provided[name] or _source_raw is not None:
            if parsed != documents[name]:
                raise ValueError(
                    f"queue source {name} bytes disagree with supplied document")
        else:
            documents[name] = parsed
        source_raw[name] = raw
    policy = documents["policy"]
    scheduler = documents["scheduler"]
    debt = documents["debt"]
    offline = documents["offline"]
    fixture_audit = documents["fixture_audit"]
    fixture_set = documents["fixture_set"]
    movie_inventory = documents["movie_inventory"]
    capsule = documents["capsule"]
    derived = documents["derived"]
    ownership = documents["ownership"]
    generated = _generated or stable_generated()
    source_snapshot = {
        "generated": generated,
        "sources": {name: _encode_source(source_raw[name])
                    for name in SOURCE_KEYS},
    }

    if policy.get("schema") != "abl-phase4-movie-priority-policy/1" or \
            policy.get("selection_policy") != "movie-ready":
        errors.append("movie-priority policy schema/name is invalid")
    errors.extend(scheduler_policy.validate_policy(scheduler))
    weights = policy.get("score_weights") or {}
    if tuple(weights) != EXPECTED_SCORE_COMPONENTS:
        errors.append("movie-priority score component order/set is invalid")
    deferred_rows = [
        item.get("row_id") for item in
        policy.get("defer_while_other_eligible") or []
    ]
    if deferred_rows != ["E15_fmv"]:
        errors.append(
            "movie-ready policy must defer exactly E15_fmv while alternatives remain")
    compatibility = policy.get("compatibility_semantics") or {}
    if "no player-facing checkpoint mechanic" not in str(
            compatibility.get("C15_checkpoints") or ""):
        errors.append("C15 compatibility semantics no longer preserve safe respawn")
    maximum = int(policy.get("max_rows_per_batch") or 0)
    if maximum < 1 or maximum > 3:
        errors.append("movie-ready batch limit must be between one and three")

    debt_rows = {item.get("row_id"): item for item in debt.get("rows") or []}
    offline_rows = {
        item.get("row_id"): item for item in offline.get("rows") or []}
    ownership_rows = ownership.get("rows") or {}
    mechanics_rows = common.baseline_rows()
    expected_rows = set(mechanics_rows)
    for label, rows in (
        ("closure debt", debt_rows),
        ("offline queue", offline_rows),
        ("ownership", ownership_rows),
        ("fixture audit", fixture_audit.get("rows") or {}),
    ):
        if set(rows) != expected_rows:
            errors.append(f"{label} does not enumerate the current 107 rows")
    if len(expected_rows) != 107:
        errors.append(
            f"mechanics registry contains {len(expected_rows)} rows, expected 107")
    if debt.get("valid") is not True or debt.get("errors"):
        errors.append("closure-debt ledger is invalid")
    if offline.get("valid") is not True or offline.get("errors"):
        errors.append("offline opportunity queue is invalid")
    if fixture_audit.get("structural_ready") is not True or \
            any(fixture_audit.get("structural_gaps", {}).values()):
        errors.append("central Phase-4 fixture audit has preservation gaps")
    if movie_inventory.get("valid") is not True or \
            movie_inventory.get("errors"):
        errors.append("movie inventory is invalid")
    if capsule.get("complete") is not True or capsule.get("errors"):
        errors.append("capsule catalog is incomplete")
    if derived.get("valid") is not True or derived.get("errors"):
        errors.append("derived-index catalog is invalid")

    fixture_entries = fixture_set.get("entries") or {}
    movie_rows = {
        item["path"]: item for item in movie_inventory.get("files") or []}
    capsule_rows = {
        item["movie"]: item for item in capsule.get("capsules") or []}
    derived_verification_cache: dict[str, bool] = {}
    capsule_verification_cache: dict[tuple, tuple[dict, list[str]]] = {}
    rows: list[dict] = []
    for row_id in sorted(expected_rows):
        debt_row = debt_rows.get(row_id) or {}
        queue_row = offline_rows.get(row_id) or {}
        dimensions = debt_row.get("dimensions") or {}
        derived_remaining = sum(
            item.get("state") not in {"met", "not_applicable"}
            for item in dimensions.values())
        count_remaining = (debt_row.get("counts") or {}).get("remaining")
        row_errors: list[str] = []
        if len(dimensions) != 9:
            row_errors.append(f"{row_id}: debt row does not have nine dimensions")
        if count_remaining != derived_remaining:
            row_errors.append(
                f"{row_id}: authored remaining count disagrees with dimension leaves")
        phase4_movies = sorted({
            item.get("path") for item in queue_row.get("relevant_movies") or []
            if isinstance(item.get("path"), str)
            and _phase4_path(item["path"])
        })
        anchors: list[dict] = []
        for movie_path in phase4_movies:
            anchor, anchor_errors = _anchor(
                movie_path, movie_rows, fixture_entries, capsule_rows, policy,
                capsule_verification_cache)
            anchors.append(anchor)
            row_errors.extend(anchor_errors)
        valid_anchors = [anchor for anchor in anchors if anchor["verified"]]
        derived_sources, derived_errors = _derived_sources(
            row_id, derived, derived_verification_cache)
        row_errors.extend(derived_errors)
        errors.extend(row_errors)
        count_positive = (
            isinstance(count_remaining, int)
            and count_remaining > 0
            and count_remaining == derived_remaining
        )
        eligible = (
            count_positive
            and derived_remaining > 0
            and bool(valid_anchors)
            and len(valid_anchors) == len(anchors)
            and not row_errors
        )
        reasons: list[str] = []
        if derived_remaining <= 0:
            reasons.append("closure debt counts.remaining re-derives to zero")
        if not phase4_movies:
            reasons.append(
                "no associated movie under case-sensitive movies/Phase4/")
        if phase4_movies and not valid_anchors:
            reasons.append("no movie/start-state anchor passes central preservation")
        reasons.extend(row_errors)
        semantic_name = debt_row.get("name")
        if row_id == "C15_checkpoints":
            semantic_name = (
                "Safe respawn anchor (historical C15_checkpoints identifier; "
                "no player-facing checkpoint mechanic)")
        result = {
            "row_id": row_id,
            "name": semantic_name,
            "family": debt_row.get("family"),
            "campaign_id": debt_row.get("campaign_id"),
            "completion_state_informational_only": debt_row.get(
                "completion_state"),
            "reported_remaining_informational_only": count_remaining,
            "derived_remaining": derived_remaining,
            "dimension_states": {
                name: item.get("state") for name, item in dimensions.items()},
            "dependency_unlock_count": debt_row.get(
                "dependency_unlock_count") or 0,
            "next_lane": debt_row.get("next_lane"),
            "next_action": debt_row.get("next_action"),
            "eligibility": {
                "eligible": eligible,
                "requirements": {
                    "remaining_debt_positive": count_positive,
                    "case_sensitive_phase4_movie": bool(phase4_movies),
                    "verified_movie_start_anchor": bool(valid_anchors),
                    "no_missing_preservation_dependency": not row_errors,
                },
                "reasons": sorted(set(reasons)),
            },
            "movie_anchors": anchors,
            "capsule_availability": [
                anchor["capsule"] for anchor in anchors
                if anchor.get("capsule")],
            "derived_indexes": derived_sources,
            "static_ownership": {
                "source": "analysis/phase3_ownership_graph.json",
                "source_sha256": hashlib.sha256(
                    source_raw["ownership"]).hexdigest(),
                "function_count": len(
                    (ownership_rows.get(row_id) or {}).get("functions") or []),
                "typed_state_count": len(
                    (ownership_rows.get(row_id) or {}).get("state") or []),
                "reader_group_count": len(
                    (ownership_rows.get(row_id) or {}).get("readers") or []),
                "writer_group_count": len(
                    (ownership_rows.get(row_id) or {}).get("writers") or []),
                "overlay_count": len(
                    (ownership_rows.get(row_id) or {}).get("overlay") or []),
                "asset_count": len(
                    (ownership_rows.get(row_id) or {}).get("assets") or []),
            },
            "frontier_blocker_domains": sorted(
                ((ownership_rows.get(row_id) or {}).get(
                    "frontier_blockers") or {}).keys()),
            "prior_offline_analysis": queue_row.get(
                "prior_offline_analysis") or [],
            "score": None,
            "rank": None,
            "selection": {
                "selectable": False,
                "deferred": False,
                "defer_reason": None,
            },
        }
        if eligible:
            components, total, rationale = _score(
                result, queue_row, ownership_rows.get(row_id) or {},
                anchors, derived_sources, policy)
            result["score"] = {
                "total": total,
                "components": components,
                "rationale": rationale,
            }
            result["expected_value"] = scheduler_policy.expected_value(
                result, scheduler)
        else:
            result["expected_value"] = None
        rows.append(result)

    eligible_rows = [row for row in rows if row["eligibility"]["eligible"]]
    other_eligible = {
        row["row_id"] for row in eligible_rows
        if row["row_id"] not in deferred_rows
    }
    defer_reasons = {
        item["row_id"]: str(item.get("reason") or "").strip()
        for item in policy.get("defer_while_other_eligible") or []
    }
    for row in eligible_rows:
        deferred = row["row_id"] in deferred_rows and bool(other_eligible)
        row["selection"] = {
            "selectable": not deferred,
            "deferred": deferred,
            "defer_reason": defer_reasons.get(row["row_id"]) if deferred else None,
        }
    ranked = sorted(
        (row for row in eligible_rows if row["selection"]["selectable"]),
        key=lambda row: (
            -Fraction(
                int(row["expected_value"]["benefit_units"]),
                int(row["expected_value"]["cost_units"])),
            -int(row["dependency_unlock_count"]),
            int(row["derived_remaining"]),
            row["row_id"],
        ),
    )
    for rank, row in enumerate(ranked, 1):
        row["rank"] = rank
    for row in eligible_rows:
        if row["selection"]["deferred"]:
            row["rank"] = None
    batches = _batches(ranked, maximum)
    row_map = {row["row_id"]: row for row in rows}
    for batch in batches:
        batch_rows = [row_map[row_id] for row_id in batch["rows"]]
        batch["expected_value"] = {
            "benefit_units": sum(
                row["expected_value"]["benefit_units"] for row in batch_rows),
            "cost_units": sum(
                row["expected_value"]["cost_units"] for row in batch_rows),
        }
        batch["expected_value"]["score_per_1000"] = (
            batch["expected_value"]["benefit_units"] * 1000
            // batch["expected_value"]["cost_units"])
        batch["fixture_cover"] = scheduler_policy.weighted_fixture_cover(
            batch_rows, scheduler)
        if not batch["fixture_cover"]["complete"]:
            errors.append(
                f"{batch['batch_id']}: fixture cover leaves requirements uncovered")
    batches.sort(key=lambda batch: (
        -Fraction(
            int(batch["expected_value"]["benefit_units"]),
            int(batch["expected_value"]["cost_units"])),
        batch["batch_id"],
    ))
    for rank, batch in enumerate(batches, 1):
        batch["rank"] = rank
    selected = deepcopy(batches[0]) if batches else None
    counts = Counter(
        "eligible" if row["eligibility"]["eligible"] else "ineligible"
        for row in rows)
    counts.update({
        "rows": len(rows),
        "selectable": len(ranked),
        "deferred": sum(row["selection"]["deferred"] for row in rows),
        "candidate_batches": len(batches),
    })
    inputs = {
        "generator_sha256": common.sha256(Path(__file__)),
        "common_helper_sha256": common.sha256(
            common.ROOT / "tools/phase4_common.py"),
        "policy_sha256": hashlib.sha256(source_raw["policy"]).hexdigest(),
        "scheduler_policy_sha256": hashlib.sha256(
            source_raw["scheduler"]).hexdigest(),
        "scheduler_helper_sha256": common.sha256(
            common.ROOT / "tools/phase4_scheduler_policy.py"),
        "mechanics_sha256": common.sha256(common.BASELINE_PATH),
        "closure_debt_sha256": hashlib.sha256(source_raw["debt"]).hexdigest(),
        "offline_queue_sha256": hashlib.sha256(source_raw["offline"]).hexdigest(),
        "fixture_audit_sha256": hashlib.sha256(
            source_raw["fixture_audit"]).hexdigest(),
        "fixture_set_sha256": hashlib.sha256(
            source_raw["fixture_set"]).hexdigest(),
        "movie_inventory_sha256": hashlib.sha256(
            source_raw["movie_inventory"]).hexdigest(),
        "movie_tree_sha256": movie_inventory.get("tree_sha256"),
        "capsule_catalog_sha256": hashlib.sha256(
            source_raw["capsule"]).hexdigest(),
        "derived_index_sha256": hashlib.sha256(
            source_raw["derived"]).hexdigest(),
        "ownership_sha256": hashlib.sha256(
            source_raw["ownership"]).hexdigest(),
    }
    return {
        "_comment": (
            "Generated work-order queue only. A movie is a trigger/evidence "
            "anchor, never proof that a row or dimension is solved."),
        "schema": SCHEMA,
        "generated": generated,
        "selection_policy": "movie-ready",
        "scheduler_policy_schema": scheduler_policy.SCHEMA,
        "non_closure_meaning": (
            "Ranks currently preserved movie-backed work without changing the "
            "107-row backlog, any debt dimension, or the Phase-4 exit gate."),
        "inputs": inputs,
        "source_snapshot": source_snapshot,
        "score_component_order": list(EXPECTED_SCORE_COMPONENTS),
        "rows": rows,
        "candidate_batches": batches,
        "selected_batch": selected,
        "counts": dict(sorted(counts.items())),
        "errors": sorted(set(errors)),
        "valid": not errors,
    }


def packet(
        queue: dict, previous_packet: dict | None = None,
        previous_progress: dict | None = None,
        previous_queue: dict | None = None,
        previous_debt_before: bytes | None = None,
        previous_debt_after: bytes | None = None,
) -> dict:
    if queue.get("schema") != SCHEMA or queue.get("valid") is not True or \
            queue.get("errors"):
        raise ValueError("movie-ready packet requires a valid priority queue")
    policy = common.load_yaml(SCHEDULER_POLICY_PATH)
    return scheduler_policy.packet(
        queue, policy, previous_packet, previous_progress, previous_queue,
        previous_debt_before, previous_debt_after)


def validate_retained(document: dict, expected: dict | None = None) -> list[str]:
    expected = expected or build()
    errors: list[str] = []
    if document != expected:
        errors.append("retained movie-priority artifact differs from regeneration")
    if document.get("schema") != SCHEMA:
        errors.append("retained movie-priority schema is invalid")
    if document.get("valid") is not True or document.get("errors"):
        errors.append("retained movie-priority artifact is not valid")
    rows = document.get("rows")
    if not isinstance(rows, list) or len(rows) != 107 or \
            len({row.get("row_id") for row in rows}) != 107:
        errors.append("retained movie-priority row universe is not exactly 107")
    selected = document.get("selected_batch")
    if selected and len(selected.get("rows") or []) > 3:
        errors.append("retained selected batch exceeds three rows")
    for batch in document.get("candidate_batches") or []:
        cover = batch.get("fixture_cover") or {}
        if cover.get("complete") is not True or cover.get("uncovered") != []:
            errors.append(f"{batch.get('batch_id')}: retained fixture cover is incomplete")
    return sorted(set(errors))


def render(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--previous-packet", type=Path)
    parser.add_argument("--previous-progress", type=Path)
    parser.add_argument("--previous-queue", type=Path)
    parser.add_argument("--previous-debt-before", type=Path)
    parser.add_argument("--previous-debt-after", type=Path)
    args = parser.parse_args()
    document = build()
    if document["errors"]:
        for error in document["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    text = render(document)
    if args.packet:
        previous = common.load_json(args.previous_packet) \
            if args.previous_packet else None
        progress = common.load_json(args.previous_progress) \
            if args.previous_progress else None
        previous_queue = common.load_json(args.previous_queue) \
            if args.previous_queue else None
        previous_debt_before = args.previous_debt_before.read_bytes() \
            if args.previous_debt_before else None
        previous_debt_after = args.previous_debt_after.read_bytes() \
            if args.previous_debt_after else None
        try:
            packet_doc = packet(
                document, previous, progress, previous_queue,
                previous_debt_before, previous_debt_after)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        args.packet.parent.mkdir(parents=True, exist_ok=True)
        args.packet.write_text(render(packet_doc), encoding="utf-8")
    elif args.write:
        OUTPUT.write_text(text, encoding="utf-8")
    elif args.check:
        if not OUTPUT.is_file():
            print("Phase-4 movie-priority queue is missing", file=sys.stderr)
            return 1
        retained = common.load_json(OUTPUT)
        retained_errors = validate_retained(retained, document)
        if retained_errors:
            for error in retained_errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
    else:
        print(text, end="")
    selected = document.get("selected_batch") or {}
    print(
        f"PASS: rows={document['counts']['rows']} "
        f"eligible={document['counts']['eligible']} "
        f"selectable={document['counts']['selectable']} "
        f"selected={selected.get('batch_id', 'none')}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
