#!/usr/bin/env python3
"""Generate the complete Phase-4 movie inventory and offline opportunity queue."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys
from typing import Any

import phase4_common as common
import phase4_coverage
import phase4_inventory
import phase4_priority


MOVIE_OUTPUT = common.ROOT / "analysis/phase4_movie_inventory.json"
QUEUE_OUTPUT = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
POLICY_PATH = common.ROOT / "config/phase4_offline_queue.yaml"
ESCALATION_SOURCE_PATH = common.ROOT / "config/phase4_live_escalations.yaml"
CAPSULE_PATH = common.ROOT / "analysis/phase4_trace_capsule_set.json"
COVERAGE_PATH = common.ROOT / "analysis/phase4_coverage_matrix.json"
FIXTURE_AUDIT_PATH = common.ROOT / "analysis/phase4_fixture_audit.json"
PRIORITY_PATH = common.ROOT / "analysis/phase4_priority.json"
OWNERSHIP_PATH = common.ROOT / "analysis/phase3_ownership_graph.json"
CLASSIFICATIONS = ("offline_ready", "offline_partial", "live_required", "no_capsule")
MOVIE_CODE = re.compile(r"(?i)(?:^|[/_.-])([a-f][0-9]{2})(?=[/_.-]|$)")


def stable_generated(path: Path) -> str:
    if path.is_file():
        try:
            value = json.loads(path.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def json_bytes(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_kind(path: Path) -> str:
    name = path.name
    if name.endswith(".movie.json"):
        return "movie"
    if name.endswith(".movie.sav"):
        return "start_state"
    if name.endswith(".movie.bak"):
        return "backup"
    return "other"


def movie_metadata(path: Path) -> tuple[dict, list[str]]:
    errors: list[str] = []
    try:
        document = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"{path}: cannot parse movie metadata: {exc}"]
    start = document.get("start_state") or {}
    raw_path = str(start.get("path") or "")
    logical_state = None
    if raw_path:
        marker = "/movies/"
        if marker in raw_path:
            logical_state = "movies/" + raw_path.split(marker, 1)[1]
        elif raw_path.startswith("movies/"):
            logical_state = raw_path
        else:
            logical_state = Path(raw_path).name
    frames = document.get("frames")
    return {
        "format": document.get("format"),
        "version": document.get("version"),
        "declared_game_serial": document.get("game_serial"),
        "declared_start_state": logical_state,
        "declared_from_boot": bool(start.get("from_boot")),
        "declared_frame_count": len(frames) if isinstance(frames, list) else None,
        "serial_is_metadata_not_media_proof": True,
    }, errors


def build_movie_inventory(movie_root: Path, capsule_doc: dict) -> dict:
    movie_root = movie_root.resolve()
    phase4_root = movie_root / "Phase4"
    declarations = common.load_json(common.FIXTURE_SET_PATH).get("entries") or {}
    capsule_movies = {row["movie"]: row for row in capsule_doc.get("capsules") or []}
    capsule_states = {
        row["start_state"]["path"]: row
        for row in capsule_doc.get("capsules") or [] if row.get("start_state")
    }
    errors: list[str] = []
    if not movie_root.is_dir():
        errors.append(f"movie root is absent: {movie_root}")
        files: list[Path] = []
    else:
        files = sorted(path for path in movie_root.rglob("*") if path.is_file())

    tree = hashlib.sha256()
    rows: list[dict] = []
    for path in files:
        rel = path.relative_to(movie_root)
        logical = str(Path("movies") / rel)
        actual_hash = common.sha256(path)
        size = path.stat().st_size
        tree.update(str(rel).encode())
        tree.update(b"\0")
        tree.update(str(size).encode())
        tree.update(b"\0")
        tree.update(actual_hash.encode())
        tree.update(b"\0")
        pin = declarations.get(logical)
        hash_matches = bool(pin and pin.get("sha256") == actual_hash)
        size_matches = bool(pin and pin.get("size") == size)
        consumed = logical in capsule_movies or logical in capsule_states
        metadata: dict[str, Any] = {}
        if file_kind(path) == "movie":
            metadata, metadata_errors = movie_metadata(path)
            errors.extend(metadata_errors)
        row = {
            "path": logical,
            "kind": file_kind(path),
            "phase4": path.is_relative_to(phase4_root),
            "bytes": size,
            "sha256": actual_hash,
            "centrally_declared": pin is not None,
            "declared_media_class": pin.get("media_class") if pin else "undeclared_external_lead",
            "declared_hash_matches": hash_matches,
            "declared_size_matches": size_matches,
            "consumed_by_capsule_set": consumed,
            **metadata,
        }
        rows.append(row)
        if consumed and not (pin and hash_matches and size_matches):
            errors.append(f"consumed fixture lacks a current central pin: {logical}")
        if consumed and (not pin or pin.get("media_class") not in {
                "pristine", "pristine_serial"}):
            errors.append(f"consumed fixture is not pristine eligible: {logical}")

    paths = {row["path"] for row in rows}
    expected_consumed = set(capsule_movies) | set(capsule_states)
    for missing in sorted(expected_consumed - paths):
        errors.append(f"capsule fixture missing from current movie tree: {missing}")
    phase4_rows = [row for row in rows if row["phase4"]]
    counts = {
        "all_files": len(rows),
        "all_bytes": sum(row["bytes"] for row in rows),
        "all_movies": sum(row["kind"] == "movie" for row in rows),
        "all_start_states": sum(row["kind"] == "start_state" for row in rows),
        "all_backups": sum(row["kind"] == "backup" for row in rows),
        "phase4_files": len(phase4_rows),
        "phase4_bytes": sum(row["bytes"] for row in phase4_rows),
        "phase4_movies": sum(row["kind"] == "movie" for row in phase4_rows),
        "phase4_start_states": sum(row["kind"] == "start_state" for row in phase4_rows),
        "phase4_backups": sum(row["kind"] == "backup" for row in phase4_rows),
        "consumed_files": sum(row["consumed_by_capsule_set"] for row in rows),
        "undeclared_files": sum(not row["centrally_declared"] for row in rows),
    }
    return {
        "_comment": "Recursive hash-only inventory of the provisioned movie tree in the tested checkout. Filenames and JSON serial strings are leads, not media proof. Only centrally pinned capsule movie/state pairs are consumed.",
        "schema": "abl-phase4-movie-inventory/1",
        "generated": stable_generated(MOVIE_OUTPUT),
        "movie_root": "movies",
        "tree_sha256": tree.hexdigest(),
        "fixture_set_sha256": common.sha256(common.FIXTURE_SET_PATH),
        "capsule_set_sha256": common.sha256(CAPSULE_PATH),
        "counts": counts,
        "files": rows,
        "errors": sorted(set(errors)),
        "valid": not errors,
    }


def source_freshness_errors(coverage: dict, fixture: dict, priority: dict,
                            capsule: dict) -> list[str]:
    errors: list[str] = []
    expected_coverage = {
        "mechanics_sha256": common.sha256(common.BASELINE_PATH),
        "registry_sha256": common.sha256(common.REGISTRY_PATH),
        "findings_sha256": common.sha256(common.FINDINGS_PATH),
    }
    for key, expected in expected_coverage.items():
        if (coverage.get("inputs") or {}).get(key) != expected:
            errors.append(f"coverage matrix stale for {key}")
    expected_fixture = {
        "mechanics_sha256": common.sha256(common.BASELINE_PATH),
        "fixture_set_sha256": common.sha256(common.FIXTURE_SET_PATH),
        "phase2_row_coverage_sha256": common.sha256(
            common.ROOT / "analysis/phase2_row_coverage.json"),
    }
    for key, expected in expected_fixture.items():
        if (fixture.get("inputs") or {}).get(key) != expected:
            errors.append(f"fixture audit stale for {key}")
    priority_inputs = priority.get("inputs") or {}
    if (priority_inputs.get("campaign_registry") or {}).get("sha256") != common.sha256(common.REGISTRY_PATH):
        errors.append("priority report stale for campaign registry")
    if (priority_inputs.get("mechanics") or {}).get("sha256") != common.sha256(common.BASELINE_PATH):
        errors.append("priority report stale for mechanics registry")
    if (priority_inputs.get("ownership") or {}).get("sha256") != common.sha256(OWNERSHIP_PATH):
        errors.append("priority report stale for ownership graph")
    if not capsule.get("complete") or capsule.get("errors"):
        errors.append("capsule set is incomplete or reports errors")
    if capsule.get("schema") != "abl-phase4-trace-capsule-set-v2":
        errors.append("capsule set does not enforce the complete runtime-bundle contract")
    runtime = capsule.get("duckstation_runtime_bundle") or {}
    runtime_manifest = runtime.get("manifest") or {}
    runtime_executable = runtime.get("executable") or {}
    for label, row in (("manifest", runtime_manifest), ("executable", runtime_executable)):
        path = Path(str(row.get("absolute_path") or ""))
        if not path.is_file() or common.sha256(path) != row.get("sha256"):
            errors.append(f"exact DuckStation runtime {label} is missing or hash-mismatched")
    if runtime.get("validated") is not True or \
            runtime.get("manifest_covers_runtime_exactly") is not True:
        errors.append("DuckStation runtime bundle is not completely manifest-validated")
    binary = capsule.get("duckstation_binary_snapshot") or {}
    if runtime_executable.get("sha256") != binary.get("sha256"):
        errors.append("DuckStation runtime executable differs from capsule binary identity")
    reader = capsule.get("offline_reader_snapshot") or {}
    reader_path = Path(str(reader.get("absolute_path") or ""))
    if not reader_path.is_file() or common.sha256(reader_path) != reader.get("sha256"):
        errors.append("exact offline reader snapshot is missing or hash-mismatched")
    if len(capsule.get("capsules") or []) != 55 or capsule.get("movie_count") != 55:
        errors.append("capsule index does not contain the current 55 rows")
    return errors


def normalize_fixture_movie(reference: str, movie_rows: dict[str, dict],
                            basenames: dict[str, list[str]]) -> str | None:
    candidates = [reference]
    if not reference.startswith("movies/"):
        candidates.append(str(Path("movies") / reference))
    for candidate in candidates:
        if candidate in movie_rows and movie_rows[candidate]["kind"] == "movie":
            return candidate
        if candidate.endswith(".movie.sav"):
            movie_candidate = candidate.removesuffix(".movie.sav") + ".movie.json"
            if movie_candidate in movie_rows:
                return movie_candidate
    name = Path(reference).name
    if name.endswith(".movie.sav"):
        name = name.removesuffix(".movie.sav") + ".movie.json"
    matches = basenames.get(name) or []
    return matches[0] if len(matches) == 1 else None


def row_codes(rows: dict[str, dict]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row_id in rows:
        code = row_id.split("_", 1)[0].upper()
        if code in result:
            raise ValueError(f"duplicate mechanic code: {code}")
        result[code] = row_id
    return result


def query_ranges(policy: dict, ownership_row: dict) -> list[dict]:
    ranges = [dict(row) for row in policy.get("common_ranges") or []]
    seen = {(row["domain"], int(row["offset"]), int(row["length"])) for row in ranges}
    for state in ownership_row.get("state") or []:
        address = state.get("address")
        try:
            offset = int(str(address), 0) & 0x1FFFFF
        except (TypeError, ValueError):
            continue
        key = ("ram", offset, 4)
        if key in seen:
            continue
        seen.add(key)
        ranges.append({
            "id": "typed_state_" + "_".join(state.get("semantic_ids") or [f"{offset:06x}"]),
            "domain": "ram",
            "offset": offset,
            "length": 4,
            "purpose": f"Typed Phase-3 state at {address}; four-byte frame-boundary probe.",
        })
    return ranges


def offline_queries(reader: Path, capsules: list[dict], ranges: list[dict]) -> list[dict]:
    result: list[dict] = []
    for capsule in capsules:
        directory = Path(capsule["capsule_directory"])
        base = f"python3 {shlex.quote(str(reader))} {shlex.quote(str(directory))}"
        end = int(capsule.get("frames") or 0)
        result.append({
            "capsule_movie": capsule["movie"],
            "domain": "manifest/registers/ram/vram/spu/block_flow",
            "window": "all retained frame boundaries",
            "command": base + " summary",
        })
        result.append({
            "capsule_movie": capsule["movie"],
            "domain": "block_flow",
            "window": f"movie frames 0..{end}",
            "command": base + f" hotspots --start 0 --end {end} --top 40",
        })
        for row in ranges:
            offset, length = int(row["offset"]), int(row["length"])
            result.append({
                "capsule_movie": capsule["movie"],
                "domain": row["domain"],
                "range_id": row["id"],
                "window": "all retained frame boundaries",
                "command": base + f" changes --domain {row['domain']} --offset 0x{offset:x} --length 0x{length:x}",
            })
    return result


def row_unknowns(ownership_row: dict, has_capsules: bool) -> list[str]:
    unknowns: list[str] = []
    for lifecycle in ownership_row.get("lifecycle") or []:
        for key in ("known_limit", "next_experiment"):
            value = str(lifecycle.get(key) or "").strip()
            if value:
                unknowns.append(value)
    for domain, blocker in sorted((ownership_row.get("frontier_blockers") or {}).items()):
        missing = str((blocker or {}).get("missing_link") or "").strip()
        next_experiment = str((blocker or {}).get("next_experiment") or "").strip()
        if missing:
            unknowns.append(f"{domain}: {missing}")
        if next_experiment:
            unknowns.append(f"{domain} next experiment: {next_experiment}")
    if has_capsules:
        unknowns.extend([
            "Frame-boundary capsules do not identify exact CPU writers, DMA producers, GPU submissions, or SPU voice events.",
            "Frame-boundary capsules cannot execute a counterfactual or native negative control.",
            "Capsule block flow is passive block-start evidence, not an every-cycle instruction trace.",
        ])
    return list(dict.fromkeys(unknowns))


def retained_offline_analysis(policy: dict, capsule_doc: dict) -> tuple[dict[str, list[dict]], dict, list[str]]:
    """Revalidate prior offline batches without trusting an authored pass flag."""
    by_row: dict[str, list[dict]] = defaultdict(list)
    inputs: dict[str, str] = {}
    errors: list[str] = []
    reader = capsule_doc.get("offline_reader_snapshot") or {}
    for spec in policy.get("offline_analysis_artifacts") or []:
        relative = spec.get("path")
        path = common.ROOT / str(relative or "")
        if not relative or not path.is_file():
            errors.append(f"offline analysis artifact is absent: {relative!r}")
            continue
        try:
            document = common.load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot parse offline analysis artifact {relative}: {exc}")
            continue
        if document.get("schema") != spec.get("schema"):
            errors.append(f"offline analysis schema mismatch: {relative}")
        if document.get("errors"):
            errors.append(f"offline analysis reports errors: {relative}")
        dependencies = document.get("source_dependencies") or {}
        for source_rel, expected in dependencies.items():
            source = common.ROOT / source_rel
            if not source.is_file() or common.sha256(source) != expected:
                errors.append(f"offline analysis source is stale: {relative}:{source_rel}")
        batch = document.get("offline_batch") or {}
        if batch.get("reader_sha256") != reader.get("sha256"):
            errors.append(f"offline analysis reader is stale: {relative}")
        external = document.get("external_index") or {}
        external_path = Path(str(external.get("absolute_path") or ""))
        if not external_path.is_file():
            errors.append(f"offline analysis external index is absent: {relative}")
        elif (external_path.stat().st_size != external.get("bytes")
              or common.sha256(external_path) != external.get("sha256")):
            errors.append(f"offline analysis external index is stale: {relative}")
        rows = document.get("selected_rows") or []
        if not rows or len(rows) != len({row.get("row_id") for row in rows}):
            errors.append(f"offline analysis selected rows are empty/duplicate: {relative}")
        for row in rows:
            row_id = row.get("row_id")
            if row_id:
                by_row[row_id].append({
                    "artifact": relative,
                    "schema": document.get("schema"),
                    "external_index_sha256": external.get("sha256"),
                    "reader_sha256": batch.get("reader_sha256"),
                    "selection_queue_rank": row.get("queue_rank"),
                })
        inputs[relative] = common.sha256(path)
    return by_row, inputs, errors


def build_queue(movie_inventory: dict) -> dict:
    mechanics = common.load_yaml(common.BASELINE_PATH)
    registry = common.load_yaml(common.REGISTRY_PATH)
    policy = common.load_yaml(POLICY_PATH)
    escalation_source = common.load_yaml(ESCALATION_SOURCE_PATH)
    retained_coverage = common.load_json(COVERAGE_PATH)
    retained_fixture = common.load_json(FIXTURE_AUDIT_PATH)
    retained_priority = common.load_json(PRIORITY_PATH)
    capsule_doc = common.load_json(CAPSULE_PATH)
    ownership = common.load_json(OWNERSHIP_PATH)
    mechanics_rows = common.baseline_rows(mechanics)
    owners, duplicates = common.primary_owners(registry)
    coverage = phase4_coverage.build(registry, mechanics)
    fixture = phase4_inventory.build_fixture_audit(mechanics, registry)
    priority = phase4_priority.build(registry, mechanics)
    errors = source_freshness_errors(
        retained_coverage, retained_fixture, retained_priority, capsule_doc)
    for label, retained, derived in (
        ("coverage matrix", retained_coverage, coverage),
        ("fixture audit", retained_fixture, fixture),
        ("priority report", retained_priority, priority),
    ):
        if common.semantic_without_generated(retained) != common.semantic_without_generated(derived):
            errors.append(f"{label} does not match current low-level derivation")
    errors.extend(common.validate_registry(registry, mechanics))
    errors.extend(movie_inventory.get("errors") or [])
    if duplicates:
        errors.append(f"duplicate primary ownership: {duplicates}")
    row_sets = {
        "mechanics": set(mechanics_rows),
        "coverage": set(coverage.get("rows") or {}),
        "fixture_audit": set(fixture.get("rows") or {}),
        "ownership": set(ownership.get("rows") or {}),
    }
    expected_rows = set(mechanics_rows)
    for source, actual in row_sets.items():
        if actual != expected_rows:
            errors.append(f"{source} row set differs from the 107-row mechanics registry")
    if len(expected_rows) != 107:
        errors.append(f"authoritative mechanics registry has {len(expected_rows)} rows, expected 107")
    if policy.get("schema") != "abl-phase4-offline-queue-policy/1":
        errors.append("offline queue policy schema is invalid")
    if escalation_source.get("schema") != "abl-phase4-live-escalation-source/1":
        errors.append("live escalation source schema is invalid")
    prior_offline, offline_inputs, offline_errors = retained_offline_analysis(
        policy, capsule_doc)
    errors.extend(offline_errors)

    movie_rows = {row["path"]: row for row in movie_inventory.get("files") or []}
    movie_only = {key: value for key, value in movie_rows.items() if value["kind"] == "movie"}
    basenames: dict[str, list[str]] = defaultdict(list)
    for logical in movie_only:
        basenames[Path(logical).name].append(logical)
    code_to_row = row_codes(mechanics_rows)
    relevant_movies: dict[str, set[str]] = defaultdict(set)
    for logical in movie_only:
        codes = MOVIE_CODE.findall(logical)
        for code in codes:
            row_id = code_to_row.get(code.upper())
            if row_id:
                relevant_movies[row_id].add(logical)
    for logical, row_ids in (policy.get("explicit_movie_rows") or {}).items():
        if logical not in movie_only:
            errors.append(f"explicit movie alias is absent from inventory: {logical}")
        for row_id in row_ids or []:
            if row_id not in mechanics_rows:
                errors.append(f"explicit movie alias names unknown row: {row_id}")
            else:
                relevant_movies[row_id].add(logical)
    for row_id, audit in (fixture.get("rows") or {}).items():
        for reference in audit.get("references") or []:
            normalized = normalize_fixture_movie(reference, movie_rows, basenames)
            if normalized:
                relevant_movies[row_id].add(normalized)

    capsules_by_movie = {
        row["movie"]: row for row in capsule_doc.get("capsules") or []}
    for logical in capsules_by_movie:
        codes = MOVIE_CODE.findall(logical)
        for code in codes:
            row_id = code_to_row.get(code.upper())
            if row_id:
                relevant_movies[row_id].add(logical)
    for logical, row_ids in (policy.get("explicit_movie_rows") or {}).items():
        if logical in capsules_by_movie:
            for row_id in row_ids or []:
                relevant_movies[row_id].add(logical)

    family_by_id = {row["id"]: row for row in registry.get("families") or []}
    family_order = {family_id: index for index, family_id in enumerate(priority.get("priority_order") or [])}
    active_rows = {
        row_id for campaign in registry.get("child_campaigns") or []
        for row_id in campaign.get("rows") or []
    }
    prior_by_row: dict[str, list[str]] = defaultdict(list)
    for entry in escalation_source.get("entries") or []:
        row_id = entry.get("target_row")
        if row_id in mechanics_rows:
            prior_by_row[row_id].append(entry.get("id"))

    reader_info = capsule_doc.get("offline_reader_snapshot") or {}
    reader = Path(reader_info.get("absolute_path") or "")
    preliminary: list[dict] = []
    for row_id in sorted(mechanics_rows):
        mechanic = mechanics_rows[row_id]
        coverage_row = (coverage.get("rows") or {}).get(row_id) or {}
        ownership_row = (ownership.get("rows") or {}).get(row_id) or {}
        family_id = owners.get(row_id)
        family = family_by_id.get(family_id) or {}
        logical_movies = sorted(relevant_movies.get(row_id) or [])
        movie_evidence = []
        for logical in logical_movies:
            item = movie_rows.get(logical)
            if not item:
                continue
            movie_evidence.append({
                "path": logical,
                "sha256": item["sha256"],
                "bytes": item["bytes"],
                "media_class": item["declared_media_class"],
                "central_pin_current": item["centrally_declared"] and item["declared_hash_matches"] and item["declared_size_matches"],
                "declared_start_state": item.get("declared_start_state"),
                "serial_is_metadata_not_media_proof": True,
            })
        capsule_rows = [capsules_by_movie[path] for path in logical_movies if path in capsules_by_movie]
        capsule_evidence = [{
            "movie": item["movie"],
            "movie_sha256": item["movie_sha256"],
            "start_state": item["start_state"],
            "capsule_directory": item["capsule_directory"],
            "capsule_manifest_sha256": item["capsule_manifest_sha256"],
            "capsule_tree_sha256": item["capsule_tree_sha256"],
            "frames": item["frames"],
            "domains": ["registers", "ram", "vram", "spu_ram", "block_flow", "run_local_full_state_checkpoints"],
            "control_match": item["control_match"],
        } for item in capsule_rows]
        state = coverage_row.get("state")
        eligible_movie_lead = any(
            row["central_pin_current"] and row["media_class"] in {"pristine", "pristine_serial"}
            for row in movie_evidence)
        prior_analysis = prior_offline.get(row_id) or []
        if capsule_rows:
            classification = "offline_partial" if (
                state != "open" or row_id in active_rows or prior_analysis
            ) else "offline_ready"
        elif state == "open" and eligible_movie_lead:
            classification = "live_required"
        else:
            classification = "no_capsule"
        ranges = query_ranges(policy, ownership_row)
        dependencies = {
            "family_dependency_rows": list(family.get("dependency_rows") or []),
            "dependent_families": sorted(
                other["id"] for other in registry.get("families") or []
                if row_id in (other.get("dependency_rows") or [])),
            "frontier_blocker_domains": sorted((ownership_row.get("frontier_blockers") or {}).keys()),
        }
        preliminary.append({
            "row_id": row_id,
            "name": mechanic.get("name"),
            "current_completion_state": state,
            "completion_derived_from": {
                "coverage_matrix": "analysis/phase4_coverage_matrix.json",
                "campaigns": coverage_row.get("completed_campaigns") or [],
                "reviewed_absence": bool(coverage_row.get("reviewed_absence")),
                "method": "phase4_coverage.build low-level evidence audits; authored pass/complete fields are forbidden",
            },
            "campaign": {
                "family": family_id,
                "family_number": family.get("number"),
                "family_title": family.get("title"),
                "family_priority_tier": family.get("priority_tier"),
                "active_child_campaign": row_id in active_rows,
            },
            "dependencies": dependencies,
            "relevant_movies": movie_evidence,
            "relevant_capsules": capsule_evidence,
            "available_domains": sorted({domain for item in capsule_evidence for domain in item["domains"]}),
            "offline_batch_queries": offline_queries(reader, capsule_rows, ranges),
            "offline_answerable_questions": ([
                "At which exact retained movie/frame boundaries do the typed state and shared player/actor/contact ranges change?",
                "Which passive basic-block starts are hottest over the full movie and around any derived state-change window?",
                "Which VRAM and SPU-RAM frame-boundary change points correlate with RAM/state transitions?",
                "Do multiple relevant capsules share change-point, register, RAM, VRAM, SPU-RAM, or block-flow signatures?",
            ] if capsule_rows else []),
            "offline_derivable_assertions": ([
                "Exact frame-boundary register and reconstructed-domain values/hashes for any named frame.",
                "Exact frame indices at which a named RAM/VRAM/SPU-RAM range intersects a retained delta run.",
                "Bounded cross-movie correlations and block-start hotspot counts without writer/causality promotion.",
                "Capsule manifest completeness, pristine authority pins, nontruncation and independent control match.",
            ] if capsule_rows else []),
            "named_unknowns": row_unknowns(ownership_row, bool(capsule_rows)),
            "prior_escalation": {
                "ledger_ids": sorted(value for value in prior_by_row.get(row_id, []) if value),
                "source": "config/phase4_live_escalations.yaml",
            },
            "prior_offline_analysis": prior_analysis,
            "classification": classification,
            "priority_inputs": {
                "family_order": family_order.get(family_id, 999),
                "family_tier": family.get("priority_tier"),
                "open": state == "open",
                "capsule_count": len(capsule_rows),
                "new_campaign": row_id not in active_rows,
            },
        })

    class_order = {name: index for index, name in enumerate(CLASSIFICATIONS)}
    preliminary.sort(key=lambda row: (
        0 if row["current_completion_state"] == "open" else 1,
        class_order[row["classification"]],
        row["priority_inputs"]["family_order"],
        -row["priority_inputs"]["capsule_count"],
        row["row_id"],
    ))
    for rank, row in enumerate(preliminary, 1):
        row["priority"] = {
            "rank": rank,
            "basis": "open rows first; offline-ready before partial/live/no-capsule; then dependency-derived family order, capsule breadth and row ID",
        }
    counts = Counter(row["classification"] for row in preliminary)
    for classification in CLASSIFICATIONS:
        counts.setdefault(classification, 0)
    counts.update({
        "rows": len(preliminary),
        "open": sum(row["current_completion_state"] == "open" for row in preliminary),
        "complete": sum(row["current_completion_state"] != "open" for row in preliminary),
    })
    input_hashes = {
        "mechanics_registry_sha256": common.sha256(common.BASELINE_PATH),
        "campaign_registry_sha256": common.sha256(common.REGISTRY_PATH),
        "coverage_matrix_sha256": common.sha256(COVERAGE_PATH),
        "fixture_audit_sha256": common.sha256(FIXTURE_AUDIT_PATH),
        "priority_sha256": common.sha256(PRIORITY_PATH),
        "ownership_sha256": common.sha256(OWNERSHIP_PATH),
        "capsule_index_sha256": common.sha256(CAPSULE_PATH),
        "fixture_set_sha256": common.sha256(common.FIXTURE_SET_PATH),
        "policy_sha256": common.sha256(POLICY_PATH),
        "live_escalation_source_sha256": common.sha256(ESCALATION_SOURCE_PATH),
        "movie_inventory_sha256": bytes_sha256(json_bytes(movie_inventory)),
        "movie_tree_sha256": movie_inventory.get("tree_sha256"),
        "offline_reader_sha256": reader_info.get("sha256"),
        "offline_analysis_artifact_sha256": offline_inputs,
    }
    document = {
        "_comment": "Generated 107-row Phase-4 offline scheduler. Completion is re-derived from low-level campaign evidence; no authored pass/complete field is consumed.",
        "schema": "abl-phase4-offline-opportunity-queue/1",
        "generated": stable_generated(QUEUE_OUTPUT),
        "inputs": input_hashes,
        "classification_values": list(CLASSIFICATIONS),
        "counts": dict(counts),
        "rows": preliminary,
        "errors": sorted(set(errors)),
    }
    document["errors"].extend(structural_errors(document, expected_rows, input_hashes))
    document["errors"] = sorted(set(document["errors"]))
    document["valid"] = not document["errors"]
    return document


def structural_errors(document: dict, expected_rows: set[str] | None = None,
                      expected_inputs: dict | None = None) -> list[str]:
    errors: list[str] = []
    rows = document.get("rows") or []
    row_ids = [row.get("row_id") for row in rows]
    if len(rows) != 107:
        errors.append(f"queue row count is {len(rows)}, expected 107")
    duplicates = sorted(row_id for row_id, count in Counter(row_ids).items() if count > 1)
    if duplicates:
        errors.append(f"queue has duplicate rows: {duplicates}")
    if expected_rows is not None and set(row_ids) != expected_rows:
        errors.append("queue row set omits or adds authoritative mechanics rows")
    if expected_inputs is not None and document.get("inputs") != expected_inputs:
        errors.append("queue source hashes are stale")
    for row in rows:
        classification = row.get("classification")
        if classification not in CLASSIFICATIONS:
            errors.append(f"{row.get('row_id')}: invalid or missing classification {classification!r}")
        if any(key in row for key in common.SELF_CERTIFYING_KEYS):
            errors.append(f"{row.get('row_id')}: self-certifying field present")
        for key in (
            "current_completion_state", "campaign", "dependencies", "relevant_movies",
            "relevant_capsules", "available_domains", "offline_batch_queries",
            "offline_answerable_questions", "offline_derivable_assertions",
            "named_unknowns", "prior_escalation", "priority",
            "prior_offline_analysis",
        ):
            if key not in row:
                errors.append(f"{row.get('row_id')}: missing required field {key}")
    derived_counts = Counter(row.get("classification") for row in rows)
    for classification in CLASSIFICATIONS:
        if document.get("counts", {}).get(classification, 0) != derived_counts[classification]:
            errors.append(f"queue count mismatch for {classification}")
    expected_state_counts = {
        "rows": len(rows),
        "open": sum(row.get("current_completion_state") == "open" for row in rows),
        "complete": sum(row.get("current_completion_state") != "open" for row in rows),
    }
    for name, expected in expected_state_counts.items():
        if document.get("counts", {}).get(name) != expected:
            errors.append(f"queue count mismatch for {name}")
    return errors


def write_or_check(path: Path, document: dict, write: bool, check: bool) -> bool:
    rendered = json_bytes(document)
    if write:
        path.write_bytes(rendered)
        return True
    if check:
        return path.is_file() and path.read_bytes() == rendered
    print(rendered.decode(), end="")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--movie-root", type=Path, default=common.ROOT / "movies",
        help=(
            "provisioned, centrally declared movie tree in the tested checkout; "
            "never defaults to the mutable operator checkout"))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--inventory-only", action="store_true",
        help="refresh/check the recursive movie inventory before dependent audits")
    args = parser.parse_args()
    capsule = common.load_json(CAPSULE_PATH)
    movie = build_movie_inventory(args.movie_root, capsule)
    if args.inventory_only:
        if movie["errors"]:
            for error in movie["errors"]:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        if not write_or_check(MOVIE_OUTPUT, movie, args.write, args.check):
            print("phase4 movie inventory is missing or stale", file=sys.stderr)
            return 1
        print(
            f"PASS: movie inventory files={movie['counts']['all_files']} "
            f"phase4={movie['counts']['phase4_files']} "
            f"consumed={movie['counts']['consumed_files']}",
            file=sys.stderr,
        )
        return 0
    queue = build_queue(movie)
    if queue["errors"]:
        for error in queue["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    movie_ok = write_or_check(MOVIE_OUTPUT, movie, args.write, args.check)
    queue_ok = write_or_check(QUEUE_OUTPUT, queue, args.write, args.check)
    if args.check and not movie_ok:
        print("phase4 movie inventory is missing or stale", file=sys.stderr)
    if args.check and not queue_ok:
        print("phase4 offline opportunity queue is missing or stale", file=sys.stderr)
    if not (movie_ok and queue_ok):
        return 1
    print(
        f"PASS: rows={queue['counts']['rows']} open={queue['counts']['open']} "
        + " ".join(f"{name}={queue['counts'].get(name, 0)}" for name in CLASSIFICATIONS),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
