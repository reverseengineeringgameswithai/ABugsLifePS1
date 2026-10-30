#!/usr/bin/env python3
"""Reject Phase-4 campaign progress mixed into pre-trial seed repair."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import subprocess
import sys

import yaml


SCHEMA = "abl-phase4-seed-repair-scope/1"
HEX64 = re.compile(r"[0-9a-f]{64}")

# These are dependency/control-plane summaries. They may need a hash refresh after
# Phase-3 evidence is replayed, but they cannot themselves establish campaign
# progress because the complete 107-row debt projection is compared separately.
ALLOWED_PHASE4_SUMMARIES = {
    "analysis/phase4_assertion_pin_reconciliation.json",
    "analysis/phase4_campaign_inventory.json",
    "analysis/phase4_closure_debt.json",
    "analysis/phase4_fixture_audit.json",
    "analysis/phase4_gate.json",
    "analysis/phase4_knowledge_audit.json",
}

# A legacy-index rollover can make the pre-trial freshness check impossible even
# when every historical execution/media leaf is unchanged.  These paths may change
# together only under legacy_index_control_repair(): the immutable-base index must
# remain byte-identical and the candidate generator must reproduce it without a
# wall-clock date.  This is deliberately not a general Phase-4 method allowlist.
LEGACY_INDEX_CONTROL_REPAIR_PATHS = {
    "tests/test_phase4_method_metrics.py",
    "tests/test_phase4_seed_repair_scope.py",
    "tools/phase4_method_legacy_live_index.py",
    "tools/phase4_seed_repair_scope.py",
}

# A current dependency-only regeneration can make the immutable pre-v2 index
# stale even though its historical execution/media payload is unchanged.  The
# repair is admitted only with a fresh projection guard, the bounded identity
# reconciler, its mutation guards, and the sole generated C16 consumer.
LEGACY_INDEX_DEPENDENCY_REPAIR_CORE_PATHS = {
    "analysis/phase4_method_legacy_live_index.json",
    "tests/test_phase4_method_metrics.py",
    "tests/test_phase4_seed_repair_scope.py",
    "tools/phase4_seed_repair_scope.py",
}
LEGACY_INDEX_DEPENDENCY_CHAIN_PATHS = {
    "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json",
    "analysis/phase4_fmv_levelb_transition_relocalization.json",
    "config/phase4_fmv_levelb_transition_relocalization.yaml",
    "config/phase4_fmv_levelb_two_pc_first_hit.yaml",
    "config/phase4_fmv_levelb_two_pc_first_hit_runtime.yaml",
    "analysis/phase4_fmv_levelb_two_pc_first_hit.json",
    "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json",
    "config/phase4_fmv_levelb_pre15792_partition.yaml",
    "analysis/phase4_fmv_levelb_pre15792_partition.json",
    "config/phase4_fmv_frame_sync_wait_ownership.yaml",
    "analysis/phase4_fmv_frame_sync_wait_ownership.json",
}
LEGACY_INDEX_DEPENDENCY_CHAIN_IDENTITIES = {
    "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json",
    "analysis/phase4_fmv_levelb_transition_relocalization.json",
    "config/phase4_fmv_levelb_two_pc_first_hit.yaml",
    "analysis/phase4_fmv_levelb_two_pc_first_hit.json",
    "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json",
    "analysis/phase4_fmv_levelb_pre15792_partition.json",
    "analysis/phase4_fmv_frame_sync_wait_ownership.json",
}
LEGACY_INDEX_DEPENDENCY_REPAIR_CONSUMER_PATHS = {
    "analysis/phase4_fmv_c16_selector_control_result.json",
    "analysis/phase4_fmv_resident_identity.json",
    "analysis/phase4_upstream_dependency_reconciliation.json",
    "config/phase4_campaigns.yaml",
    "config/phase4_fmv_c16_selector_control_result.yaml",
    "config/phase4_fmv_resident_identity.yaml",
    "config/phase4_live_escalations.yaml",
    "tests/test_phase4_assertion_pin_reconciliation.py",
    "tests/test_phase4_fmv_resident_identity.py",
    "tests/test_phase4_offline_queue.py",
    "tests/test_phase4_upstream_dependency_reconciliation.py",
    "tools/phase4_reconcile_assertion_pins.py",
    "tools/phase4_reconcile_upstream_dependencies.py",
} | LEGACY_INDEX_DEPENDENCY_CHAIN_PATHS
LEGACY_INDEX_DEPENDENCY_REPAIR_GENERATED_PATHS = {
    "analysis/phase4_coverage_matrix.json",
    "analysis/phase4_derived_index.json",
    "analysis/phase4_live_escalations.json",
    "analysis/phase4_movie_inventory.json",
    "analysis/phase4_offline_opportunity_queue.json",
    "analysis/phase4_priority.json",
}
LEGACY_INDEX_DEPENDENCY_REPAIR_PATHS = (
    LEGACY_INDEX_DEPENDENCY_REPAIR_CORE_PATHS |
    LEGACY_INDEX_DEPENDENCY_REPAIR_CONSUMER_PATHS |
    LEGACY_INDEX_DEPENDENCY_REPAIR_GENERATED_PATHS
)

# Regenerating the authoritative fixture audit changes a joined hash in the
# opportunity queue and current live-audit ledger.  Admit that pair only when an
# independent projection proves that queue classifications and every authored/live
# execution leaf are unchanged and both tracked generators reproduce the candidate.
DEPENDENCY_REFRESH_PATHS = {
    "analysis/phase4_live_escalations.json",
    "analysis/phase4_offline_opportunity_queue.json",
}

# The iteration-96 result was already banked as executed failed-plan evidence,
# but its focused ledger test retained the preceding planned partition.  Admit
# only the exact guard correction, together with this scope rule and its tests.
# Every behavioral/live artifact stays byte-identical to the immutable seed.
LIVE_LEDGER_PARTITION_GUARD_REPAIR_PATHS = {
    "tests/test_phase4_offline_queue.py",
    "tests/test_phase4_seed_repair_scope.py",
    "tools/phase4_seed_repair_scope.py",
}
LIVE_LEDGER_PARTITION_BEHAVIOR_PATHS = {
    "analysis/phase4_closure_debt.json",
    "analysis/phase4_fmv_c16_selector_control_result.json",
    "analysis/phase4_live_escalations.json",
    "config/phase4_campaigns.yaml",
    "config/phase4_fmv_c16_selector_control_result.yaml",
    "config/phase4_live_escalations.yaml",
    ("ObsidianVault/Experiments/"
     "EXP_2026-07-27_phase4_fmv_c16_selector_control_falsified.md"),
    ("ObsidianVault/Playbooks/Game Solving Roadmap/"
     "Game Solving Campaign - FMV Playback and Skip.md"),
    ("ObsidianVault/Playbooks/Game Solving Roadmap/"
     "Phase 4 - Solve Every Gameplay and Engine Subsystem.md"),
}

# The movie-ready queue is a generated identity/eligibility index, but the shared
# Phase-0..2 fixture scanner initially treated every fixture-looking string in that
# queue as a new behavioral consumer.  Because the scanner is also protected by the
# Phase-4 inventory, admit only the exact cycle-breaking source transformation and
# its paired regression/scope guards.
FIXTURE_INDEX_CONTROL_REPAIR_PATHS = {
    "tests/test_knowledge_closure.py",
    "tests/test_phase4_seed_repair_scope.py",
    "tools/knowledge_closure_audit.py",
    "tools/phase4_seed_repair_scope.py",
}


def _expected_fixture_index_source(base_source: str) -> str:
    replacements = (
        (
            "import argparse\nimport ast\nimport fnmatch\n",
            "import argparse\nimport ast\nimport base64\nimport fnmatch\n",
        ),
        (
            "import re\nimport subprocess\nfrom collections import defaultdict\n",
            "import re\nimport subprocess\nimport zlib\n"
            "from collections import defaultdict\n",
        ),
        (
            '        "phase4_movie_inventory.json",\n',
            '        "phase4_movie_inventory.json",\n'
            '        "phase4_movie_priority_queue.json",\n',
        ),
        (
            '''def preserve_semantic_receipt_date(path: Path, doc: dict) -> dict:
    """Keep an existing receipt date when only the wall clock changed."""
    if not path.is_file():
        return doc
    try:
        retained = json.loads(path.read_text())
    except json.JSONDecodeError:
        return doc
    retained_semantic = {
        key: value for key, value in retained.items() if key != "generated"}
    computed_semantic = {
        key: value for key, value in doc.items() if key != "generated"}
    if retained_semantic == computed_semantic and isinstance(
            retained.get("generated"), str):
        doc["generated"] = retained["generated"]
    return doc
''',
            '''def retained_current_replay(path: Path) -> dict | None:
    """Read the exact current replay retained behind compatibility-path bytes."""
    inventory = ROOT / "analysis/phase3_evidence_inventory.json"
    try:
        retained = json.loads(inventory.read_text())
        key = (
            "compatibility_external_fixture_set"
            if path == FIXTURE_SET
            else "compatibility_knowledge_report"
        )
        row = retained[key]
        if row.get("replay_document_encoding") != "zlib+base64":
            return None
        raw = zlib.decompress(base64.b64decode(
            row["replay_document_zlib_base64"], validate=True))
        replay = json.loads(raw)
    except (OSError, KeyError, TypeError, ValueError, zlib.error,
            json.JSONDecodeError):
        return None
    return replay if isinstance(replay, dict) else None


def preserve_semantic_receipt_date(path: Path, doc: dict) -> dict:
    """Keep the retained current-replay date when only the wall clock changed."""
    candidates = [retained_current_replay(path)]
    try:
        candidates.append(json.loads(path.read_text()))
    except (OSError, json.JSONDecodeError):
        pass
    computed_semantic = {
        key: value for key, value in doc.items() if key != "generated"}
    for retained in candidates:
        if not isinstance(retained, dict):
            continue
        retained_semantic = {
            key: value for key, value in retained.items() if key != "generated"}
        if retained_semantic == computed_semantic and isinstance(
                retained.get("generated"), str):
            doc["generated"] = retained["generated"]
            break
    return doc
''',
        ),
    )
    expected = base_source
    for old, new in replacements:
        if expected.count(old) != 1:
            raise ValueError(
                "immutable-base fixture-index source lacks the exact repair anchor")
        expected = expected.replace(old, new)
    return expected


def _expected_fixture_index_guard(base_source: str) -> str:
    fixture_name = "homing_" + "berry.sav"
    anchor = f'    assert fixtures == ["{fixture_name}"]\n\n\n'
    addition = '''def test_movie_priority_queue_is_an_index_not_a_fixture_consumer():
    consumers = closure_audit.fixture_consumers()
    assert all(
        "analysis/phase4_movie_priority_queue.json" not in paths
        for paths in consumers.values()
    )


'''
    if base_source.count(anchor) != 1:
        raise ValueError(
            "immutable-base fixture-index guard lacks the exact repair anchor")
    return base_source.replace(anchor, anchor + addition)


def fixture_index_control_repair(
        repo: Path, base: str, candidate: str, changed: list[str],
) -> tuple[bool, list[str]]:
    """Admit only the exact behavior-neutral movie-priority index-cycle repair."""
    primary = {
        "tests/test_knowledge_closure.py",
        "tools/knowledge_closure_audit.py",
    }
    if not (set(changed) & primary):
        return False, []
    requested = sorted(
        set(changed) & FIXTURE_INDEX_CONTROL_REPAIR_PATHS)
    gaps = []
    if set(requested) != FIXTURE_INDEX_CONTROL_REPAIR_PATHS:
        gaps.append(
            "fixture-index control repair did not update its generator and "
            "regression/scope guards together")
    try:
        source_path = "tools/knowledge_closure_audit.py"
        base_source = base_blob(repo, base, source_path).decode("utf-8")
        candidate_source = _candidate_blob(
            repo, candidate, source_path).decode("utf-8")
        if candidate_source != _expected_fixture_index_source(base_source):
            gaps.append(
                "fixture-index generator changed beyond the exact queue "
                "exclusion and retained-current date repair")

        guard_path = "tests/test_knowledge_closure.py"
        base_guard = base_blob(repo, base, guard_path).decode("utf-8")
        candidate_guard = _candidate_blob(
            repo, candidate, guard_path).decode("utf-8")
        if candidate_guard != _expected_fixture_index_guard(base_guard):
            gaps.append(
                "fixture-index regression guard changed beyond the exact "
                "movie-priority non-consumer assertion")

        for path in (
                "analysis/phase0_2_external_fixture_set.json",
                "analysis/phase0_2_knowledge_closure_report.json"):
            if base_blob(repo, base, path) != _candidate_blob(
                    repo, candidate, path):
                gaps.append(
                    f"{path}: fixture-index repair changed compatibility bytes")

        base_inventory = json.loads(base_blob(
            repo, base, "analysis/phase3_evidence_inventory.json"))
        candidate_inventory = _candidate_json(
            repo, candidate, "analysis/phase3_evidence_inventory.json")
        for key in (
                "compatibility_external_fixture_set",
                "compatibility_knowledge_report"):
            if base_inventory.get(key) != candidate_inventory.get(key):
                gaps.append(
                    f"fixture-index repair changed retained current replay: {key}")

        scope_guard = _candidate_blob(
            repo, candidate,
            "tests/test_phase4_seed_repair_scope.py").decode("utf-8")
        for name in (
                "test_scope_admits_exact_fixture_index_control_repair",
                "test_scope_rejects_fixture_index_control_repair_with_extra_"
                "source_drift"):
            if name not in scope_guard:
                gaps.append(
                    f"fixture-index scope mutation guard is absent: {name}")
    except (json.JSONDecodeError, subprocess.CalledProcessError,
            UnicodeDecodeError, ValueError) as exc:
        gaps.append(f"cannot validate exact fixture-index control repair: {exc}")
    return not gaps, gaps


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_repo_path(value: object, where: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or \
            "\\" in value or posixpath.normpath(value) != value or \
            value in {".", ".."} or value.startswith("../"):
        raise ValueError(f"{where} has an unsafe repository path")
    return value


def base_blob(repo: Path, base: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{base}:{path}"])


def load_debt(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "abl-phase4-closure-debt/1" or \
            doc.get("valid") is not True or doc.get("errors"):
        raise ValueError(f"{path}: invalid Phase-4 closure debt")
    rows = doc.get("rows")
    if not isinstance(rows, list) or len(rows) != 107:
        raise ValueError(f"{path}: expected exactly 107 debt rows")
    by_id = {row.get("row_id"): row for row in rows}
    if len(by_id) != 107 or None in by_id:
        raise ValueError(f"{path}: duplicate or missing row IDs")
    return doc


def phase4_specific(path: str) -> bool:
    lowered = path.lower()
    return (
        path.startswith("analysis/phase4_")
        or path.startswith("config/phase4_")
        or path.startswith("tools/phase4_")
        or path.startswith("tests/test_phase4_")
        or path.startswith("engineering-specs/phase4")
        or "phase 4 - solve every gameplay and engine subsystem.md" in lowered
        or "phase 4 - reverse engineering operating method.md" in lowered
    )


def base_campaign_paths(repo: Path, base: str) -> set[str]:
    """Read protected campaign paths from the immutable pre-repair inventory."""
    raw = subprocess.check_output([
        "git", "-C", str(repo), "show",
        f"{base}:analysis/phase4_campaign_inventory.json",
    ])
    inventory = json.loads(raw)
    if inventory.get("structural_ready") is not True or \
            inventory.get("closure_ready") is not True:
        raise ValueError("base Phase-4 campaign inventory is not closure-ready")
    paths: set[str] = set()
    for key in ("schemas", "tests", "notes"):
        values = inventory.get(key)
        if not isinstance(values, list) or not all(
                isinstance(item, str) for item in values):
            raise ValueError(f"base Phase-4 inventory {key} is malformed")
        paths.update(values)
    generators = inventory.get("generators")
    if not isinstance(generators, dict):
        raise ValueError("base Phase-4 generator inventory is malformed")
    for generator, declaration in generators.items():
        if not isinstance(generator, str) or not isinstance(declaration, dict):
            raise ValueError("base Phase-4 generator declaration is malformed")
        paths.add(generator)
        for output in declaration.get("outputs") or []:
            if isinstance(output, dict) and isinstance(output.get("path"), str):
                paths.add(output["path"])
            elif isinstance(output, str):
                paths.add(output)
            else:
                raise ValueError(
                    f"base Phase-4 generator output is malformed: {generator}")
    rows = inventory.get("rows")
    if not isinstance(rows, dict) or len(rows) != 107:
        raise ValueError("base Phase-4 inventory does not contain 107 rows")
    for row in rows.values():
        if not isinstance(row, dict):
            raise ValueError("base Phase-4 row inventory is malformed")
        for surface in row.get("source_surfaces") or []:
            if not isinstance(surface, dict):
                raise ValueError("base Phase-4 source surface is malformed")
            for key in ("semantic_c", "asm"):
                values = surface.get(key) or []
                if not isinstance(values, list) or not all(
                        isinstance(item, str) for item in values):
                    raise ValueError("base Phase-4 source paths are malformed")
                paths.update(values)
        frontier = row.get("frontier") or {}
        for group in ("functions", "state"):
            for item in frontier.get(group) or []:
                if not isinstance(item, dict):
                    raise ValueError("base Phase-4 frontier is malformed")
                canon = item.get("canon") or []
                if not isinstance(canon, list) or not all(
                        isinstance(value, str) for value in canon):
                    raise ValueError("base Phase-4 Canon paths are malformed")
                paths.update(canon)
    return paths


def base_seed_repair_paths(repo: Path, base: str) -> set[str]:
    """Derive the complete permitted repair surface from base Phase-3 banking."""
    raw = subprocess.check_output([
        "git", "-C", str(repo), "show",
        f"{base}:analysis/phase3_evidence_inventory.json",
    ])
    inventory = json.loads(raw)
    generators = inventory.get("generators")
    summary = inventory.get("summary")
    if not isinstance(generators, dict) or not isinstance(summary, dict):
        raise ValueError("base Phase-3 evidence inventory is malformed")
    for key in (
            "missing_generator_declarations", "stale_generator_declarations",
            "orphan_artifacts", "missing_outputs"):
        if summary.get(key):
            raise ValueError(
                f"base Phase-3 evidence inventory has structural gap: {key}")
    paths = {"analysis/phase3_evidence_inventory.json"}
    for generator, declaration in generators.items():
        if not isinstance(generator, str) or not isinstance(declaration, dict):
            raise ValueError("base Phase-3 generator declaration is malformed")
        paths.add(canonical_repo_path(
            generator, "base Phase-3 generator declaration"))
        for key in ("source_path_literals", "guards", "notes"):
            values = declaration.get(key) or []
            if not isinstance(values, list) or not all(
                    isinstance(item, str) for item in values):
                raise ValueError(
                    f"base Phase-3 {generator} {key} is malformed")
            paths.update(
                canonical_repo_path(
                    item, f"base Phase-3 {generator} {key}")
                for item in values
            )
        dependencies = declaration.get("shared_dependencies") or []
        if not isinstance(dependencies, list):
            raise ValueError(
                f"base Phase-3 {generator} shared_dependencies is malformed")
        for dependency in dependencies:
            if not isinstance(dependency, dict) or \
                    set(dependency) != {"path", "sha256"}:
                raise ValueError(
                    f"base Phase-3 {generator} shared_dependencies is malformed")
            path = canonical_repo_path(
                dependency["path"],
                f"base Phase-3 {generator} shared dependency")
            digest = dependency["sha256"]
            if not isinstance(digest, str) or not HEX64.fullmatch(digest) or \
                    hashlib.sha256(base_blob(repo, base, path)).hexdigest() != digest:
                raise ValueError(
                    f"base Phase-3 {generator} shared dependency pin is invalid: "
                    f"{path}")
            paths.add(path)
        for output in declaration.get("outputs") or []:
            if not isinstance(output, dict) or not isinstance(
                    output.get("path"), str):
                raise ValueError(
                    f"base Phase-3 {generator} output is malformed")
            paths.add(canonical_repo_path(
                output["path"], f"base Phase-3 {generator} output"))
    return paths


def semantic_rows(doc: dict) -> dict:
    """Retain every campaign scheduling and nine-dimension debt field."""
    return {
        row["row_id"]: row
        for row in doc["rows"]
    }


def legacy_index_control_repair(
        repo: Path, base: str, candidate: str, changed: list[str],
) -> tuple[bool, list[str]]:
    """Admit only a behavior-neutral, checkout-stable legacy-index repair."""
    requested = sorted(
        set(changed) & LEGACY_INDEX_CONTROL_REPAIR_PATHS)
    if not requested:
        return False, []
    gaps = []
    if set(requested) != LEGACY_INDEX_CONTROL_REPAIR_PATHS:
        gaps.append(
            "legacy-index control repair did not update its generator and both "
            "mutation guards together")

    index_path = "analysis/phase4_method_legacy_live_index.json"
    try:
        base_index = base_blob(repo, base, index_path)
        candidate_index = subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{candidate}:{index_path}"])
    except subprocess.CalledProcessError:
        gaps.append("legacy-index control repair cannot resolve both index blobs")
        base_index = candidate_index = b""
    if base_index != candidate_index:
        gaps.append(
            "legacy-index control repair changed retained historical evidence")

    generator_path = repo / "tools" / "phase4_method_legacy_live_index.py"
    try:
        generator_source = generator_path.read_text(encoding="utf-8")
    except OSError:
        generator_source = ""
    if "date.today" in generator_source:
        gaps.append("legacy-index generator still depends on the wall clock")
    try:
        retained = json.loads(candidate_index)
    except (json.JSONDecodeError, TypeError):
        retained = {}
        gaps.append("candidate legacy index is not valid JSON")
    created = retained.get("generated")
    if not isinstance(created, str) or \
            f'INDEX_CREATED = "{created}"' not in generator_source:
        gaps.append(
            "legacy-index generator does not pin the retained cutoff creation date")

    check = subprocess.run(
        ["python3", str(generator_path), "--check"],
        cwd=repo, text=True, capture_output=True,
    )
    if check.returncode != 0:
        gaps.append(
            "candidate legacy-index generator does not reproduce the retained "
            f"index: {(check.stdout + check.stderr).strip()}")
    return not gaps, gaps


def _candidate_json(repo: Path, candidate: str, path: str) -> dict:
    raw = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{candidate}:{path}"])
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object")
    return value


def _candidate_blob(repo: Path, candidate: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{candidate}:{path}"])


def _legacy_projection_sha256(entry: dict) -> str:
    projected = {
        key: value for key, value in entry.items()
        if key != "derived_post_run_audit"
    }
    encoded = json.dumps(
        projected, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalized_legacy_consumer_config(document: dict) -> dict:
    normalized = json.loads(json.dumps(document))
    staged = normalized.get("staged_successor") or {}
    admission = staged.get("method_admission") or {}
    legacy = admission.get("legacy_index")
    if isinstance(legacy, dict) and "sha256" in legacy:
        legacy["sha256"] = "<current-legacy-index-identity>"
    validator = admission.get("validator")
    if isinstance(validator, dict) and "sha256" in validator:
        validator["sha256"] = "<current-method-validator-identity>"
    return normalized


def _normalized_legacy_consumer_result(document: dict) -> dict:
    normalized = json.loads(json.dumps(document))
    admission = normalized.get("method_admission") or {}
    legacy = admission.get("legacy_index")
    if isinstance(legacy, dict) and "sha256" in legacy:
        legacy["sha256"] = "<current-legacy-index-identity>"
    validator = admission.get("validator")
    if isinstance(validator, dict) and "sha256" in validator:
        validator["sha256"] = "<current-method-validator-identity>"
    dependencies = normalized.get("source_dependencies") or {}
    config_path = "config/phase4_fmv_c16_selector_control_result.yaml"
    if config_path in dependencies:
        dependencies[config_path] = "<current-consumer-config-identity>"
    return normalized


def _normalized_legacy_index_dependency(document: dict) -> dict:
    """Normalize only a generated artifact's current legacy-index identity."""
    normalized = json.loads(json.dumps(document))
    dependencies = normalized.get("source_dependencies") or {}
    if "analysis/phase4_method_legacy_live_index.json" in dependencies:
        dependencies["analysis/phase4_method_legacy_live_index.json"] = \
            "<current-legacy-index-identity>"
    return normalized


def _normalized_artifact_assertions(
        node, artifact: str, *, expected_sha256: str | None = None,
) -> tuple[object, int, bool]:
    """Normalize only pins on one named artifact and verify current identity."""
    current_ok = True
    count = 0
    if isinstance(node, dict):
        result = {}
        is_assertion = node.get("artifact") == artifact and "sha256" in node
        for key, value in node.items():
            if is_assertion and key == "sha256":
                count += 1
                if expected_sha256 is not None and value != expected_sha256:
                    current_ok = False
                result[key] = "<current-artifact-identity>"
            else:
                normalized, nested_count, nested_ok = \
                    _normalized_artifact_assertions(
                        value, artifact, expected_sha256=expected_sha256)
                result[key] = normalized
                count += nested_count
                current_ok = current_ok and nested_ok
        return result, count, current_ok
    if isinstance(node, list):
        result = []
        for value in node:
            normalized, nested_count, nested_ok = \
                _normalized_artifact_assertions(
                    value, artifact, expected_sha256=expected_sha256)
            result.append(normalized)
            count += nested_count
            current_ok = current_ok and nested_ok
        return result, count, current_ok
    return node, 0, True


def _replace_exact_identities(node, replacements: dict[str, str]):
    if isinstance(node, str):
        return replacements.get(node, node)
    if isinstance(node, dict):
        return {
            key: _replace_exact_identities(value, replacements)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [
            _replace_exact_identities(value, replacements)
            for value in node
        ]
    return node


def _replace_text_identities(
        text: str, replacements: dict[str, str],
) -> str:
    """Replace exact hash tokens embedded in guard source text."""
    for identity, marker in replacements.items():
        text = text.replace(identity, marker)
    return text


def _artifact_identity_replacements(
        repo: Path, base: str, candidate: str, paths: set[str],
) -> dict[str, str]:
    """Map the before/after hashes of named artifacts to path-specific markers."""
    replacements = {}
    for relative in sorted(paths):
        try:
            before = hashlib.sha256(base_blob(
                repo, base, relative)).hexdigest()
            after = hashlib.sha256(_candidate_blob(
                repo, candidate, relative)).hexdigest()
        except subprocess.CalledProcessError:
            continue
        marker = f"<current:{relative}>"
        replacements[before] = marker
        replacements[after] = marker
    return replacements


def _generated_dependency_projection(
        path: str, document: dict,
        identity_replacements: dict[str, str] | None = None,
) -> dict:
    """Remove current dependency identities, never behavioral/scheduling rows."""
    projected = json.loads(json.dumps(document))
    if "generated" in projected:
        projected["generated"] = "<stable-generated-metadata>"
    if path in LEGACY_INDEX_DEPENDENCY_REPAIR_GENERATED_PATHS:
        projected["inputs"] = "<current-dependency-identities>"
    if path == "analysis/phase4_live_escalations.json":
        for entry in projected.get("entries") or []:
            entry.pop("derived_pre_run_audit", None)
            entry.pop("derived_post_run_audit", None)
            if entry.get("id") in {
                    "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL",
                    "P4-ITER99-E15-C16-STAGED-SELECTOR-LIFECYCLE-CONTROL",
            }:
                joined = (entry.get("execution_result") or {}).get(
                    "banked_analysis")
                if isinstance(joined, dict) and "sha256" in joined:
                    joined["sha256"] = "<current-c16-control-identity>"
    if identity_replacements:
        projected = _replace_exact_identities(
            projected, identity_replacements)
    return projected


def _validate_c16_dependency_chain(
        repo: Path, base: str, candidate: str, result_path: str,
        candidate_result: dict, gaps: list[str],
) -> None:
    resident_config_path = "config/phase4_fmv_resident_identity.yaml"
    live_config_path = "config/phase4_live_escalations.yaml"
    resident_path = "analysis/phase4_fmv_resident_identity.json"
    base_c16_sha = hashlib.sha256(
        base_blob(repo, base, result_path)).hexdigest()
    candidate_c16_sha = hashlib.sha256(
        _candidate_blob(repo, candidate, result_path)).hexdigest()
    base_resident_config_sha = hashlib.sha256(
        base_blob(repo, base, resident_config_path)).hexdigest()
    candidate_resident_config_sha = hashlib.sha256(
        _candidate_blob(repo, candidate, resident_config_path)).hexdigest()
    base_live_config_sha = hashlib.sha256(
        base_blob(repo, base, live_config_path)).hexdigest()
    candidate_live_config_sha = hashlib.sha256(
        _candidate_blob(repo, candidate, live_config_path)).hexdigest()
    dependency_replacements = {
        base_c16_sha: "<current-c16-control-identity>",
        candidate_c16_sha: "<current-c16-control-identity>",
        base_resident_config_sha: "<current-resident-config-identity>",
        candidate_resident_config_sha: "<current-resident-config-identity>",
        base_live_config_sha: "<current-live-config-identity>",
        candidate_live_config_sha: "<current-live-config-identity>",
    }
    for relative in sorted(LEGACY_INDEX_DEPENDENCY_CHAIN_PATHS):
        try:
            before = hashlib.sha256(base_blob(
                repo, base, relative)).hexdigest()
            after = hashlib.sha256(_candidate_blob(
                repo, candidate, relative)).hexdigest()
        except subprocess.CalledProcessError:
            continue
        marker = f"<current:{relative}>"
        dependency_replacements[before] = marker
        dependency_replacements[after] = marker
    for dependency_config in (resident_config_path, live_config_path):
        base_dependency = yaml.safe_load(
            base_blob(repo, base, dependency_config))
        candidate_dependency = yaml.safe_load(
            _candidate_blob(repo, candidate, dependency_config))
        if _replace_exact_identities(
                base_dependency, dependency_replacements) != \
                _replace_exact_identities(
                    candidate_dependency, dependency_replacements):
            gaps.append(
                f"{dependency_config}: changed beyond current C16 "
                "artifact identities")

    base_resident = json.loads(base_blob(repo, base, resident_path))
    candidate_resident = _candidate_json(repo, candidate, resident_path)
    if _replace_exact_identities(
            base_resident, dependency_replacements) != \
            _replace_exact_identities(
                candidate_resident, dependency_replacements):
        gaps.append(
            "resident-identity artifact changed beyond joined C16/config "
            "dependency identities")
    candidate_resident_sha = hashlib.sha256(
        _candidate_blob(repo, candidate, resident_path)).hexdigest()

    resident_test_path = "tests/test_phase4_fmv_resident_identity.py"
    base_resident_sha = hashlib.sha256(
        base_blob(repo, base, resident_path)).hexdigest()
    base_test = base_blob(repo, base, resident_test_path).decode()
    candidate_test = _candidate_blob(
        repo, candidate, resident_test_path).decode()
    normalized_base_test = base_test.replace(
        base_resident_sha, "<current-resident-identity>").replace(
            base_c16_sha, "<current-c16-control-identity>")
    normalized_candidate_test = candidate_test.replace(
        candidate_resident_sha, "<current-resident-identity>").replace(
            candidate_c16_sha, "<current-c16-control-identity>")
    if normalized_base_test != normalized_candidate_test:
        gaps.append(
            "resident-identity guard changed beyond its current artifact pin")

    offline_test_path = "tests/test_phase4_offline_queue.py"
    base_offline_test = base_blob(repo, base, offline_test_path).decode()
    candidate_offline_test = _candidate_blob(
        repo, candidate, offline_test_path).decode()
    if _replace_text_identities(
            base_offline_test, dependency_replacements) != \
            _replace_text_identities(
                candidate_offline_test, dependency_replacements):
        gaps.append(
            "live-ledger guard changed beyond current dependency artifact pins")

    campaigns_path = "config/phase4_campaigns.yaml"
    base_campaigns = yaml.safe_load(base_blob(repo, base, campaigns_path))
    candidate_campaigns = yaml.safe_load(
        _candidate_blob(repo, candidate, campaigns_path))
    normalized_base, base_count, _ = _normalized_artifact_assertions(
        base_campaigns, result_path)
    normalized_candidate, candidate_count, candidate_current = \
        _normalized_artifact_assertions(
            candidate_campaigns, result_path,
            expected_sha256=candidate_c16_sha)
    normalized_base, base_resident_count, _ = \
        _normalized_artifact_assertions(
            normalized_base, resident_path)
    normalized_candidate, candidate_resident_count, \
        candidate_resident_current = _normalized_artifact_assertions(
            normalized_candidate, resident_path,
            expected_sha256=candidate_resident_sha)
    normalized_base = _replace_exact_identities(
        normalized_base, dependency_replacements)
    normalized_candidate = _replace_exact_identities(
        normalized_candidate, dependency_replacements)
    campaigns_changed = (
        base_blob(repo, base, campaigns_path) !=
        _candidate_blob(repo, candidate, campaigns_path))
    if (base_count or candidate_count or campaigns_changed) and (
            base_count != candidate_count or candidate_count == 0 or
            not candidate_current or normalized_base != normalized_candidate):
        gaps.append(
            "campaign C16 assertions changed beyond current artifact pins")
    if base_resident_count != candidate_resident_count or \
            not candidate_resident_current:
        gaps.append(
            "campaign resident assertions changed beyond current artifact pins")


def legacy_index_dependency_repair(
        repo: Path, base: str, candidate: str, changed: list[str],
) -> tuple[bool, list[str]]:
    """Admit a generated dependency-only legacy-index refresh, never replay."""
    requested = sorted(
        set(changed) & LEGACY_INDEX_DEPENDENCY_REPAIR_PATHS)
    index_path = "analysis/phase4_method_legacy_live_index.json"
    if index_path not in requested:
        return False, []
    gaps = []
    if not LEGACY_INDEX_DEPENDENCY_REPAIR_CORE_PATHS <= set(requested):
        gaps.append(
            "legacy-index dependency repair lacks its generated index, current-"
            "projection guard, scope rule, or scope mutation guard")

    live_path = "analysis/phase4_live_escalations.json"
    generator_path = "tools/phase4_method_legacy_live_index.py"
    dependency_identity_paths = (
        LEGACY_INDEX_DEPENDENCY_CHAIN_PATHS | {
            "analysis/phase4_fmv_c16_selector_control_result.json",
            "analysis/phase4_fmv_resident_identity.json",
        }
    )
    dependency_identity_replacements = _artifact_identity_replacements(
        repo, base, candidate, dependency_identity_paths)
    try:
        base_live_bytes = base_blob(repo, base, live_path)
        candidate_live_bytes = _candidate_blob(repo, candidate, live_path)
        if _generated_dependency_projection(
                live_path, json.loads(base_live_bytes),
                dependency_identity_replacements) != \
                _generated_dependency_projection(
                    live_path, json.loads(candidate_live_bytes),
                    dependency_identity_replacements):
            gaps.append(
                "legacy-index dependency repair changed a retained live "
                "execution/control leaf")
        live = json.loads(candidate_live_bytes)
        base_index = json.loads(base_blob(repo, base, index_path))
        candidate_index = _candidate_json(repo, candidate, index_path)
        if base_blob(repo, base, generator_path) != \
                _candidate_blob(repo, candidate, generator_path):
            gaps.append(
                "legacy-index dependency repair changed its projection generator")

        base_entries = base_index.get("entries")
        candidate_entries = candidate_index.get("entries")
        if not isinstance(base_entries, list) or \
                not isinstance(candidate_entries, list) or \
                len(base_entries) != len(candidate_entries):
            raise ValueError("legacy index entry set changed")
        changed_ids = []
        source_entries = {
            row.get("id"): row for row in live.get("entries") or []
            if isinstance(row, dict)
        }
        for before, after in zip(base_entries, candidate_entries):
            if not isinstance(before, dict) or not isinstance(after, dict):
                raise ValueError("legacy index entry is not an object")
            before_normalized = dict(before)
            after_normalized = dict(after)
            before_sha = before_normalized.pop("source_entry_sha256", None)
            after_sha = after_normalized.pop("source_entry_sha256", None)
            if before_normalized != after_normalized:
                gaps.append(
                    f"{after.get('escalation_id')}: legacy entry changed beyond "
                    "its generated source projection")
                continue
            escalation_id = after.get("escalation_id")
            source = source_entries.get(escalation_id)
            if source is None or after_sha != _legacy_projection_sha256(source):
                gaps.append(
                    f"{escalation_id}: candidate legacy projection is not derived "
                    "from the immutable retained live entry")
            if before_sha != after_sha:
                changed_ids.append(escalation_id)

        base_without_entries = dict(base_index)
        candidate_without_entries = dict(candidate_index)
        base_without_entries.pop("entries", None)
        candidate_without_entries.pop("entries", None)
        if base_without_entries != candidate_without_entries:
            gaps.append(
                "legacy-index dependency repair changed cutoff/schema/count metadata")
        if not changed_ids:
            gaps.append("legacy-index dependency repair changed no stale projections")

        reconciliation = _candidate_json(
            repo, candidate,
            "analysis/phase4_upstream_dependency_reconciliation.json")
        if reconciliation.get("valid") is not True or \
                reconciliation.get("errors") or \
                reconciliation.get(
                    "joined_live_escalation_only_sha_leaves_changed") is not True:
            gaps.append(
                "upstream reconciliation does not prove dependency-only live joins")
        pins = {
            row.get("entry_id"): row
            for row in reconciliation.get("joined_live_escalation_pins") or []
            if isinstance(row, dict)
        }
        artifact_proofs = {
            row.get("path"): row
            for row in reconciliation.get("artifacts") or []
            if isinstance(row, dict)
        }
        base_reconciliation = json.loads(base_blob(
            repo, base,
            "analysis/phase4_upstream_dependency_reconciliation.json"))
        base_artifact_proofs = {
            row.get("path"): row
            for row in base_reconciliation.get("artifacts") or []
            if isinstance(row, dict)
        }
        for escalation_id in changed_ids:
            source = source_entries[escalation_id]
            joined = (source.get("execution_result") or {}).get(
                "banked_analysis") or {}
            pin = pins.get(escalation_id) or {}
            relative = joined.get("path")
            digest = joined.get("sha256")
            proof = artifact_proofs.get(relative) or {}
            base_proof = base_artifact_proofs.get(relative) or {}
            try:
                current_digest = hashlib.sha256(
                    _candidate_blob(repo, candidate, relative)).hexdigest()
            except (subprocess.CalledProcessError, TypeError):
                current_digest = None
            if pin.get("pin_kind") != "controlled_banked_analysis" or \
                    pin.get("behavioral_payload_preserved") is not True or \
                    pin.get("path") != relative or \
                    pin.get("sha256_after") != digest or \
                    current_digest != digest:
                gaps.append(
                    f"{escalation_id}: changed projection lacks a current, "
                    "behavior-preserving banked-analysis join")
            if proof.get("artifact_sha256_after") != digest or \
                    proof.get(
                        "only_dependency_metadata_or_joined_identity_changed"
                    ) is not True or \
                    proof.get("historical_run_provenance_preserved") is not True or \
                    not HEX64.fullmatch(str(
                        proof.get("normalized_runtime_payload_sha256") or "")):
                gaps.append(
                    f"{escalation_id}: changed projection lacks the reconciler's "
                    "normalized-payload and historical-provenance proof")
            if base_proof.get("historical_run_provenance_preserved") is not True or \
                    proof.get("normalized_runtime_payload_sha256") != \
                    base_proof.get("normalized_runtime_payload_sha256"):
                gaps.append(
                    f"{escalation_id}: changed projection does not preserve the "
                    "immutable-base normalized runtime payload")
        c16_path = "analysis/phase4_fmv_c16_selector_control_result.json"
        c16_sha = hashlib.sha256(
            _candidate_blob(repo, candidate, c16_path)).hexdigest()
        if (repo / "tools/phase4_fmv_c16_selector_control_result.py").is_file():
            for c16_id in (
                    "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL",
                    "P4-ITER99-E15-C16-STAGED-SELECTOR-LIFECYCLE-CONTROL",
            ):
                c16_pin = pins.get(c16_id) or {}
                if c16_pin.get("pin_kind") != \
                        "controlled_banked_analysis" or \
                        c16_pin.get("behavioral_payload_preserved") is not True or \
                        c16_pin.get("path") != c16_path or \
                        c16_pin.get("sha256_after") != c16_sha:
                    gaps.append(
                        f"{c16_id}: current C16 dependency lacks a "
                        "behavior-preserving upstream reconciliation pin")
    except (json.JSONDecodeError, subprocess.CalledProcessError,
            TypeError, ValueError) as exc:
        gaps.append(f"cannot validate dependency-only legacy index: {exc}")
        candidate_index = {}

    current_index_sha = hashlib.sha256(
        _candidate_blob(repo, candidate, index_path)).hexdigest()
    config_path = "config/phase4_fmv_c16_selector_control_result.yaml"
    result_path = "analysis/phase4_fmv_c16_selector_control_result.json"
    try:
        base_config = yaml.safe_load(base_blob(repo, base, config_path))
        candidate_config = yaml.safe_load(
            _candidate_blob(repo, candidate, config_path))
        base_staged = base_config.get("staged_successor") or {} \
            if isinstance(base_config, dict) else {}
        candidate_staged = candidate_config.get("staged_successor") or {} \
            if isinstance(candidate_config, dict) else {}
        base_legacy = (
            ((base_staged.get("method_admission") or {}).get(
                "legacy_index") or {})
            if isinstance(base_config, dict) else {})
        candidate_legacy = (
            ((candidate_staged.get("method_admission") or {}).get(
                "legacy_index") or {})
            if isinstance(candidate_config, dict) else {})
        if base_legacy and isinstance(candidate_config, dict):
            validator = (candidate_staged.get("method_admission") or {}).get(
                "validator") or {}
            validator_path = validator.get("path")
            validator_sha = (
                hashlib.sha256(
                    _candidate_blob(repo, candidate, validator_path)).hexdigest()
                if isinstance(validator_path, str) else None)
            if candidate_legacy.get("sha256") != current_index_sha or \
                    validator.get("sha256") != validator_sha or \
                    _normalized_legacy_consumer_config(base_config) != \
                    _normalized_legacy_consumer_config(candidate_config):
                gaps.append(
                    "C16 legacy-index source pin changed beyond its current SHA-256")
        elif base_blob(repo, base, config_path) != \
                _candidate_blob(repo, candidate, config_path):
            gaps.append(
                "untyped C16 legacy-index source changed during dependency repair")

        base_result = json.loads(base_blob(repo, base, result_path))
        candidate_result = _candidate_json(repo, candidate, result_path)
        base_result_legacy = ((base_result.get("method_admission") or {}).get(
            "legacy_index") or {})
        candidate_result_legacy = (
            (candidate_result.get("method_admission") or {}).get(
                "legacy_index") or {})
        if base_result_legacy:
            config_sha = hashlib.sha256(
                _candidate_blob(repo, candidate, config_path)).hexdigest()
            dependencies = candidate_result.get("source_dependencies") or {}
            validator = (candidate_result.get("method_admission") or {}).get(
                "validator") or {}
            validator_path = validator.get("path")
            validator_sha = (
                hashlib.sha256(
                    _candidate_blob(repo, candidate, validator_path)).hexdigest()
                if isinstance(validator_path, str) else None)
            if candidate_result_legacy.get("sha256") != current_index_sha or \
                    validator.get("sha256") != validator_sha or \
                    dependencies.get(config_path) != config_sha or \
                    _normalized_legacy_consumer_result(base_result) != \
                    _normalized_legacy_consumer_result(candidate_result):
                gaps.append(
                    "generated C16 legacy consumer changed beyond joined "
                    "dependency identities")

        if base_result_legacy:
            _validate_c16_dependency_chain(
                repo, base, candidate, result_path, candidate_result, gaps)

        exact_pc_path = \
            "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json"
        try:
            base_exact_pc = json.loads(base_blob(repo, base, exact_pc_path))
        except subprocess.CalledProcessError:
            base_exact_pc = None
        if base_exact_pc is not None:
            candidate_exact_pc = _candidate_json(
                repo, candidate, exact_pc_path)
            candidate_dependencies = candidate_exact_pc.get(
                "source_dependencies") or {}
            base_index_pin = (base_exact_pc.get("source_dependencies") or {}).get(
                index_path)
            if base_index_pin != current_index_sha and \
                    exact_pc_path not in changed:
                gaps.append(
                    "generated exact-PC result did not refresh its stale "
                    "legacy-index dependency")
            if candidate_dependencies.get(index_path) != current_index_sha or \
                    _normalized_legacy_index_dependency(base_exact_pc) != \
                    _normalized_legacy_index_dependency(candidate_exact_pc):
                gaps.append(
                    "generated exact-PC result changed beyond its current "
                    "legacy-index dependency")

        chain_replacements = {
            hashlib.sha256(base_blob(repo, base, index_path)).hexdigest():
                "<current-legacy-index-identity>",
            current_index_sha: "<current-legacy-index-identity>",
        }
        for relative in sorted(LEGACY_INDEX_DEPENDENCY_CHAIN_PATHS):
            try:
                before = hashlib.sha256(base_blob(
                    repo, base, relative)).hexdigest()
                after = hashlib.sha256(_candidate_blob(
                    repo, candidate, relative)).hexdigest()
            except subprocess.CalledProcessError:
                continue
            marker = f"<current:{relative}>"
            chain_replacements[before] = marker
            chain_replacements[after] = marker
        for relative in sorted(LEGACY_INDEX_DEPENDENCY_CHAIN_PATHS):
            try:
                base_chain = yaml.safe_load(base_blob(repo, base, relative))
                candidate_chain = yaml.safe_load(
                    _candidate_blob(repo, candidate, relative))
            except subprocess.CalledProcessError:
                continue
            if _replace_exact_identities(
                    base_chain, chain_replacements) != \
                    _replace_exact_identities(
                        candidate_chain, chain_replacements):
                gaps.append(
                    f"{relative}: generated post-falsifier chain changed "
                    "beyond joined dependency identities")
    except (AttributeError, json.JSONDecodeError, subprocess.CalledProcessError,
            TypeError, yaml.YAMLError) as exc:
        gaps.append(f"cannot validate legacy-index C16 consumer: {exc}")

    try:
        assertion_report = _candidate_json(
            repo, candidate,
            "analysis/phase4_assertion_pin_reconciliation.json")
        identity_rows = {
            row.get("path"): row
            for row in assertion_report.get("identity_artifacts") or []
            if isinstance(row, dict)
        }
        if assertion_report.get("valid") is not True or \
                assertion_report.get("errors") or \
                (identity_rows.get(index_path) or {}).get(
                    "sha256") != current_index_sha:
            gaps.append(
                "assertion reconciliation does not retain the current legacy index")
        exact_pc_path = \
            "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json"
        try:
            current_exact_pc_sha = hashlib.sha256(
                _candidate_blob(repo, candidate, exact_pc_path)).hexdigest()
        except subprocess.CalledProcessError:
            current_exact_pc_sha = None
        if current_exact_pc_sha is not None and \
                (identity_rows.get(exact_pc_path) or {}).get(
                    "sha256") != current_exact_pc_sha:
            gaps.append(
                "assertion reconciliation omits the current exact-PC result")
        for relative in sorted(LEGACY_INDEX_DEPENDENCY_CHAIN_IDENTITIES):
            try:
                current = hashlib.sha256(
                    _candidate_blob(repo, candidate, relative)).hexdigest()
            except subprocess.CalledProcessError:
                continue
            if (identity_rows.get(relative) or {}).get("sha256") != current:
                gaps.append(
                    f"assertion reconciliation omits current chain identity: "
                    f"{relative}")
    except (json.JSONDecodeError, subprocess.CalledProcessError, TypeError) as exc:
        gaps.append(f"cannot validate legacy-index assertion reconciliation: {exc}")

    for generated_path in sorted(
            set(changed) &
            LEGACY_INDEX_DEPENDENCY_REPAIR_GENERATED_PATHS):
        try:
            before = json.loads(base_blob(repo, base, generated_path))
            after = _candidate_json(repo, candidate, generated_path)
            if _generated_dependency_projection(
                    generated_path, before,
                    dependency_identity_replacements) != \
                    _generated_dependency_projection(
                        generated_path, after,
                        dependency_identity_replacements):
                gaps.append(
                    f"{generated_path}: dependency regeneration changed "
                    "behavioral, classification, or scheduling payload")
        except (json.JSONDecodeError, subprocess.CalledProcessError,
                TypeError, ValueError) as exc:
            gaps.append(
                f"{generated_path}: cannot validate generated dependency "
                f"projection: {exc}")

    for command, label in (
        (
            [sys.executable, generator_path, "--check"],
            "legacy-index generator",
        ),
        (
            [
                sys.executable, "tools/phase4_reconcile_assertion_pins.py",
                "--check",
            ],
            "legacy-index identity reconciler",
        ),
        (
            [
                sys.executable, "tools/phase4_fmv_c16_selector_control_result.py",
                "--check",
            ],
            "generated C16 legacy-index consumer",
        ),
        (
            [
                sys.executable, "tools/phase4_fmv_resident_identity.py",
                "--check",
            ],
            "generated resident-identity consumer",
        ),
        (
            [
                sys.executable,
                "tools/phase4_fmv_levelb_region_b_dma_exact_pc_result.py",
                "--check",
            ],
            "generated exact-PC legacy-index consumer",
        ),
        (
            [
                sys.executable, "tools/phase4_reconcile_upstream_dependencies.py",
                "--check",
            ],
            "upstream dependency reconciler",
        ),
    ):
        path = repo / command[1]
        if not path.is_file():
            continue
        check = subprocess.run(
            command, cwd=repo, text=True, capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if check.returncode != 0:
            gaps.append(
                f"{label} does not reproduce: "
                f"{(check.stdout + check.stderr).strip()}")

    try:
        method_guard = _candidate_blob(
            repo, candidate, "tests/test_phase4_method_metrics.py").decode()
        scope_guard = _candidate_blob(
            repo, candidate, "tests/test_phase4_seed_repair_scope.py").decode()
        assertion_source = _candidate_blob(
            repo, candidate,
            "tools/phase4_reconcile_assertion_pins.py").decode()
        if "assert retained == legacy.build()" not in method_guard:
            gaps.append("legacy-index current-projection regression guard is absent")
        if "test_scope_admits_dependency_only_legacy_index_refresh" not in \
                scope_guard:
            gaps.append("legacy-index dependency-repair scope mutation guard is absent")
        if "test_scope_rejects_dependency_legacy_refresh_with_changed_" \
                "normalized_payload" not in scope_guard:
            gaps.append(
                "legacy-index immutable normalized-payload mutation guard is absent")
        if "test_exact_pc_legacy_consumer_normalizes_only_index_identity" not in \
                scope_guard:
            gaps.append(
                "legacy-index exact-PC consumer mutation guard is absent")
        if index_path not in assertion_source:
            gaps.append("bounded assertion reconciler omits the legacy index")
        if current_exact_pc_sha is not None and not all(
                relative in assertion_source
                for relative in LEGACY_INDEX_DEPENDENCY_CHAIN_IDENTITIES):
            gaps.append(
                "bounded assertion reconciler omits the post-falsifier "
                "dependency chain")
    except (subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        gaps.append(f"cannot inspect legacy-index dependency guards: {exc}")
    return not gaps, gaps


def _expected_live_ledger_guard(base_source: str) -> str:
    replacements = (
        (
            """    assert len(executed) == 18
    assert [entry["id"] for entry in planned] == [
        "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL",
    ]
""",
            """    assert len(executed) == 19
    assert planned == []
""",
        ),
        (
            """        if entry["execution_result"].get("execution_kind") ==
        "v2_receipt_set"]
""",
            """        if entry["execution_result"].get("execution_kind") ==
        "v2_receipt_set"
        and entry["id"] !=
        "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL"]
""",
        ),
        (
            """    planned = document["entries"][-1]
    assert planned["id"] == \\
        "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL"
    assert planned["state"] == "planned"
    assert planned["missing_fact_id"] == "E15/c16-selector40-lifecycle"
    assert len(planned["receipt_plan"]["receipts"]) == 2
    assert document["counts"] == {"entries": 19, "executed": 18, "planned": 1}
""",
            """    selector_control = document["entries"][-1]
    assert selector_control["id"] == \\
        "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL"
    assert selector_control["state"] == "executed"
    assert selector_control["missing_fact_id"] == \\
        "E15/c16-selector40-lifecycle"
    assert len(selector_control["receipt_plan"]["receipts"]) == 2
    assert selector_control["execution_result"]["execution_kind"] == \\
        "v2_receipt_set"
    assert selector_control["execution_result"]["control_outcome"] == \\
        "falsified"
    assert selector_control["execution_result"]["record_counts"] == {
        "emulator_launches": 2,
        "completed_atomic_jobs": 4,
        "exact_after_load_writes": 1,
        "lifecycle_observer_events": 0,
        "owned_pids_stopped": 2,
        "admissible_live_receipts": 0,
    }
    assert selector_control["execution_result"]["banked_analysis"] == {
        "path": "analysis/phase4_fmv_c16_selector_control_result.json",
        "sha256":
            "bd8a8fba7aeb81d5ccaaf974de457e284a744e2fc9f26750843147769c802159",
    }
    assert document["counts"] == {"entries": 19, "executed": 19, "planned": 0}
""",
        ),
    )
    expected = base_source
    for old, new in replacements:
        if expected.count(old) != 1:
            raise ValueError(
                "immutable-base live-ledger test does not have the expected "
                "single stale guard")
        expected = expected.replace(old, new)
    return expected


def live_ledger_partition_guard_repair(
        repo: Path, base: str, candidate: str, changed: list[str],
) -> tuple[bool, list[str]]:
    """Admit the exact stale planned/executed test repair, never live drift."""
    requested = sorted(
        set(changed) & LIVE_LEDGER_PARTITION_GUARD_REPAIR_PATHS)
    if not requested:
        return False, []
    gaps = []
    if set(requested) != LIVE_LEDGER_PARTITION_GUARD_REPAIR_PATHS:
        gaps.append(
            "live-ledger partition guard repair did not update its focused "
            "test, scope rule, and scope mutation guards together")

    for path in sorted(LIVE_LEDGER_PARTITION_BEHAVIOR_PATHS):
        try:
            if base_blob(repo, base, path) != \
                    _candidate_blob(repo, candidate, path):
                gaps.append(
                    f"{path}: live-ledger guard repair changed retained "
                    "behavior, execution evidence, debt, or narrative handoff")
        except subprocess.CalledProcessError:
            gaps.append(
                f"{path}: live-ledger guard repair cannot resolve both blobs")

    test_path = "tests/test_phase4_offline_queue.py"
    try:
        expected_test = _expected_live_ledger_guard(
            base_blob(repo, base, test_path).decode("utf-8"))
        candidate_test = _candidate_blob(
            repo, candidate, test_path).decode("utf-8")
        if candidate_test != expected_test:
            gaps.append(
                "focused live-ledger guard changed beyond the exact stale "
                "planned/executed partition and failed-plan assertions")
    except (UnicodeDecodeError, ValueError, subprocess.CalledProcessError) as exc:
        gaps.append(f"cannot derive exact live-ledger guard repair: {exc}")

    try:
        ledger = _candidate_json(
            repo, candidate, "analysis/phase4_live_escalations.json")
        result_path = "analysis/phase4_fmv_c16_selector_control_result.json"
        result_sha = hashlib.sha256(
            _candidate_blob(repo, candidate, result_path)).hexdigest()
        entries = ledger.get("entries")
        selector = next(
            row for row in entries
            if row.get("id") ==
            "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL")
        execution = selector.get("execution_result") or {}
        if ledger.get("counts") != {
                "entries": 19, "executed": 19, "planned": 0} or \
                selector.get("state") != "executed" or \
                execution.get("execution_kind") != "v2_receipt_set" or \
                execution.get("control_outcome") != "falsified" or \
                (execution.get("record_counts") or {}).get(
                    "admissible_live_receipts") != 0 or \
                (execution.get("record_counts") or {}).get(
                    "lifecycle_observer_events") != 0 or \
                execution.get("banked_analysis") != {
                    "path": result_path, "sha256": result_sha}:
            gaps.append(
                "candidate ledger does not retain the exact 19-executed, "
                "zero-admissible iteration-96 failed-plan boundary")
    except (StopIteration, TypeError, ValueError, subprocess.CalledProcessError,
            json.JSONDecodeError) as exc:
        gaps.append(f"cannot validate retained live-ledger partition: {exc}")

    for command, label in (
        (
            [sys.executable, "tools/phase4_live_escalations.py", "--check"],
            "live-escalation generator",
        ),
        (
            [
                sys.executable, "-m", "pytest", "-q",
                "-p", "no:cacheprovider",
                "tests/test_phase4_offline_queue.py::"
                "test_live_ledger_is_generated_and_retains_executed_"
                "missing_capsule_runs",
            ],
            "focused live-ledger guard",
        ),
    ):
        check = subprocess.run(
            command, cwd=repo, text=True, capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if check.returncode != 0:
            gaps.append(
                f"{label} does not reproduce: "
                f"{(check.stdout + check.stderr).strip()}")
    return not gaps, gaps


def _dependency_projection(path: str, document: dict) -> dict:
    projected = json.loads(json.dumps(document))
    if path == "analysis/phase4_offline_opportunity_queue.json":
        (projected.get("inputs") or {}).pop("fixture_audit_sha256", None)
    elif path == "analysis/phase4_live_escalations.json":
        (projected.get("inputs") or {}).pop("queue_sha256", None)
        for entry in projected.get("entries") or []:
            for audit_name in ("derived_pre_run_audit",
                               "derived_post_run_audit"):
                audit = entry.get(audit_name) or {}
                hashes = audit.get("queue_source_hashes") or {}
                hashes.pop("fixture_audit_sha256", None)
    return projected


def phase4_dependency_refresh(
        repo: Path, base: str, candidate: str, changed: list[str],
) -> tuple[bool, list[str]]:
    """Admit the queue/live join refresh without admitting behavioral edits."""
    requested = sorted(set(changed) & DEPENDENCY_REFRESH_PATHS)
    if not requested:
        return False, []
    gaps = []
    if set(requested) != DEPENDENCY_REFRESH_PATHS:
        gaps.append(
            "Phase-4 dependency refresh did not update queue and live audit "
            "ledger together")
    for path in sorted(DEPENDENCY_REFRESH_PATHS):
        try:
            base_doc = json.loads(base_blob(repo, base, path))
            candidate_doc = _candidate_json(repo, candidate, path)
        except (subprocess.CalledProcessError, json.JSONDecodeError,
                ValueError, TypeError) as exc:
            gaps.append(f"{path}: cannot compare dependency refresh: {exc}")
            continue
        if _dependency_projection(path, base_doc) != \
                _dependency_projection(path, candidate_doc):
            gaps.append(
                f"{path}: dependency refresh changed a behavioral, execution, "
                "classification, or scheduling leaf")
    for tool in (
        "tools/phase4_offline_queue.py",
        "tools/phase4_live_escalations.py",
    ):
        check = subprocess.run(
            ["python3", str(repo / tool), "--check"],
            cwd=repo, text=True, capture_output=True,
        )
        if check.returncode != 0:
            gaps.append(
                f"{tool}: candidate dependency artifact is stale: "
                f"{(check.stdout + check.stderr).strip()}")
    return not gaps, gaps


def build(
        repo: Path, base: str, candidate: str, before_path: Path,
        after_path: Path,
) -> dict:
    before = load_debt(before_path)
    after = load_debt(after_path)
    changed = subprocess.check_output(
        ["git", "-C", str(repo), "diff", "--name-only", "-z",
         f"{base}..{candidate}"],
    ).decode("utf-8").split("\0")
    changed = sorted(path for path in changed if path)
    protected = base_campaign_paths(repo, base)
    seed_allowed = base_seed_repair_paths(repo, base)
    fixture_index_ok, fixture_index_gaps = fixture_index_control_repair(
        repo, base, candidate, changed)
    after_fixture_index = (
        [path for path in changed
         if path not in FIXTURE_INDEX_CONTROL_REPAIR_PATHS]
        if fixture_index_ok else changed
    )
    legacy_dependency_ok, legacy_dependency_gaps = \
        legacy_index_dependency_repair(
            repo, base, candidate, after_fixture_index)
    after_legacy_dependency = (
        [path for path in after_fixture_index
         if path not in LEGACY_INDEX_DEPENDENCY_REPAIR_PATHS]
        if legacy_dependency_ok else after_fixture_index
    )
    full_legacy_requested = (
        set(after_legacy_dependency) & LEGACY_INDEX_CONTROL_REPAIR_PATHS
        == LEGACY_INDEX_CONTROL_REPAIR_PATHS
    )
    live_partition_changed = (
        [path for path in after_legacy_dependency
         if path not in LEGACY_INDEX_CONTROL_REPAIR_PATHS]
        if full_legacy_requested else after_legacy_dependency
    )
    live_partition_ok, live_partition_gaps = \
        live_ledger_partition_guard_repair(
            repo, base, candidate, live_partition_changed)
    legacy_changed = (
        [path for path in after_legacy_dependency
         if path not in LIVE_LEDGER_PARTITION_GUARD_REPAIR_PATHS]
        if live_partition_ok else after_legacy_dependency
    )
    legacy_control_ok, legacy_control_gaps = legacy_index_control_repair(
        repo, base, candidate, legacy_changed)
    dependency_refresh_changed = (
        [path for path in after_fixture_index
         if path not in LEGACY_INDEX_DEPENDENCY_REPAIR_PATHS]
        if legacy_dependency_ok else after_fixture_index
    )
    dependency_refresh_ok, dependency_refresh_gaps = phase4_dependency_refresh(
        repo, base, candidate, dependency_refresh_changed)
    admitted_control_paths = (
        LEGACY_INDEX_CONTROL_REPAIR_PATHS if legacy_control_ok else set())
    admitted_legacy_dependency_paths = (
        LEGACY_INDEX_DEPENDENCY_REPAIR_PATHS
        if legacy_dependency_ok else set())
    admitted_live_partition_paths = (
        LIVE_LEDGER_PARTITION_GUARD_REPAIR_PATHS
        if live_partition_ok else set())
    admitted_dependency_paths = (
        DEPENDENCY_REFRESH_PATHS if dependency_refresh_ok else set())
    admitted_fixture_index_paths = (
        FIXTURE_INDEX_CONTROL_REPAIR_PATHS if fixture_index_ok else set())
    # A Phase-3 declaration does not grant permission to change a path that the
    # immutable Phase-4 inventory also consumes as campaign knowledge/source.
    # The small summary set is safe because the complete 107-row projection is
    # compared below and none of these files is an authoritative campaign source.
    forbidden = sorted(path for path in changed if (
        path not in ALLOWED_PHASE4_SUMMARIES
        and path not in admitted_control_paths
        and path not in admitted_legacy_dependency_paths
        and path not in admitted_live_partition_paths
        and path not in admitted_dependency_paths
        and path not in admitted_fixture_index_paths
        and (path not in seed_allowed or path in protected)
    ))
    debt_equal = (
        semantic_rows(before) == semantic_rows(after)
        and before.get("dimension_order") == after.get("dimension_order")
        and before.get("scheduler") == after.get("scheduler")
    )
    errors = []
    if not debt_equal:
        errors.append(
            "Phase-4 row, dimension, scheduler, or campaign debt changed during "
            "pre-trial seed repair"
        )
    errors.extend(legacy_control_gaps)
    errors.extend(legacy_dependency_gaps)
    errors.extend(live_partition_gaps)
    errors.extend(dependency_refresh_gaps)
    errors.extend(fixture_index_gaps)
    if forbidden:
        errors.append(
            "Phase-4 campaign/method source changed during prerequisite repair: "
            + ", ".join(forbidden)
        )
    return {
        "schema": SCHEMA,
        "base_commit": base,
        "candidate_commit": candidate,
        "debt_before_sha256": sha256(before_path),
        "debt_after_sha256": sha256(after_path),
        "debt_projection_equal": debt_equal,
        "changed_paths": changed,
        "base_campaign_protected_path_count": len(protected),
        "base_seed_repair_allowed_path_count": len(seed_allowed),
        "allowed_phase4_summary_changes": sorted(
            set(changed) & ALLOWED_PHASE4_SUMMARIES
        ),
        "legacy_index_control_repair": {
            "requested_paths": sorted(
                set(legacy_changed) & LEGACY_INDEX_CONTROL_REPAIR_PATHS),
            "admitted": legacy_control_ok,
            "gaps": legacy_control_gaps,
        },
        "legacy_index_dependency_repair": {
            "requested_paths": sorted(
                set(changed) & LEGACY_INDEX_DEPENDENCY_REPAIR_PATHS),
            "admitted": legacy_dependency_ok,
            "gaps": legacy_dependency_gaps,
        },
        "live_ledger_partition_guard_repair": {
            "requested_paths": sorted(
                set(live_partition_changed) &
                LIVE_LEDGER_PARTITION_GUARD_REPAIR_PATHS),
            "admitted": live_partition_ok,
            "gaps": live_partition_gaps,
        },
        "phase4_dependency_refresh": {
            "requested_paths": sorted(
                set(dependency_refresh_changed) & DEPENDENCY_REFRESH_PATHS),
            "admitted": dependency_refresh_ok,
            "gaps": dependency_refresh_gaps,
        },
        "fixture_index_control_repair": {
            "requested_paths": sorted(
                set(changed) & FIXTURE_INDEX_CONTROL_REPAIR_PATHS),
            "admitted": fixture_index_ok,
            "gaps": fixture_index_gaps,
        },
        "forbidden_phase4_changes": forbidden,
        "complete": not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--debt-before", type=Path, required=True)
    parser.add_argument("--debt-after", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        doc = build(
            args.repo.resolve(), args.base, args.candidate,
            args.debt_before.resolve(), args.debt_after.resolve(),
        )
    except (OSError, ValueError, KeyError, TypeError,
            json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        doc = {
            "schema": SCHEMA,
            "base_commit": args.base,
            "candidate_commit": args.candidate,
            "complete": False,
            "errors": [str(exc)],
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    if not doc["complete"]:
        for error in doc["errors"]:
            print(f"FAIL: {error}")
        return 1
    print(
        "PASS: seed repair preserved all 107 Phase-4 debt rows and changed no "
        "Phase-4 campaign source"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
