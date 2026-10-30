#!/usr/bin/env python3
"""Reconcile C16 artifact metadata after unrelated A10/A11 baseline edits."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import importlib
import json
from pathlib import Path
import sys

import phase4_common as common


OUTPUT = common.ROOT / "analysis/phase4_baseline_dependency_reconciliation.json"
BASELINE = common.ROOT / "analysis/mechanics_baseline.yaml"
TARGETS = (
    ("analysis/phase4_c16_bonus_death.json", "phase4_c16_bonus_death",
     "bonus_context_identity", "build_bonus_context_identity"),
    ("analysis/phase4_c16_boss_death.json", "phase4_c16_boss_death",
     "boss_context_identity", "build_boss_context_identity"),
    ("analysis/phase4_c16_thumper_death.json", "phase4_c16_thumper_death",
     "thumper_context_identity", "build_context_identity"),
)
ALLOWED_CHANGED_ROWS = ("A10_handstand", "A11_seed_as_weapon")


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_sha(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def rendered(document: dict) -> bytes:
    return (json.dumps(document, indent=2) + "\n").encode()


def artifact_rendered(document: dict) -> bytes:
    """Preserve the established generated-artifact indentation."""
    return (json.dumps(document, indent=1) + "\n").encode()


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = json.loads(OUTPUT.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def build() -> tuple[list[tuple[Path, dict]], dict]:
    baseline = common.load_yaml(BASELINE)
    rows = {row["id"]: row for row in baseline.get("rows") or []}
    missing = sorted(set(ALLOWED_CHANGED_ROWS) - set(rows))
    if missing:
        raise ValueError(f"expected changed rows are absent: {missing}")
    baseline_sha = file_sha(BASELINE)
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.is_file() else {}
    previous_rows = {row["path"]: row for row in previous.get("artifacts") or []}
    updates = []
    report_rows = []
    for relative, module_name, context_field, context_builder in TARGETS:
        path = common.ROOT / relative
        document = json.loads(path.read_text())
        dependencies = document.get("source_dependencies") or {}
        observed_baseline = dependencies.get("analysis/mechanics_baseline.yaml")
        if not observed_baseline:
            raise ValueError(f"{relative}: no mechanics baseline dependency")
        module = importlib.import_module(module_name)
        current_context = getattr(module, context_builder)()
        if document.get(context_field) != current_context:
            raise ValueError(f"{relative}: baseline-derived context changed; live regeneration required")
        before_payload = dict(document)
        before_payload.pop("source_dependencies", None)
        payload_sha = object_sha(before_payload)
        prior = previous_rows.get(relative) or {}
        original_artifact_sha = prior.get("artifact_sha256_before") or file_sha(path)
        original_baseline_sha = prior.get("baseline_sha256_before") or observed_baseline
        document["source_dependencies"]["analysis/mechanics_baseline.yaml"] = baseline_sha
        updates.append((path, document))
        report_rows.append({
            "path": relative,
            "context_field": context_field,
            "context_sha256": object_sha(current_context),
            "baseline_sha256_before": original_baseline_sha,
            "baseline_sha256_after": baseline_sha,
            "artifact_sha256_before": original_artifact_sha,
            "artifact_sha256_after": hashlib.sha256(artifact_rendered(document)).hexdigest(),
            "runtime_evidence_payload_sha256": payload_sha,
            "only_source_dependency_metadata_changed": True,
            "current_context_matches_retained_artifact": True,
        })
    report = {
        "_comment": "Generated metadata-only reconciliation. The three C16 runtime payloads and their baseline-derived context identities are unchanged; A10/A11 baseline evidence does not require replaying unrelated C16 controls.",
        "schema": "abl-phase4-baseline-dependency-reconciliation/1",
        "generated": stable_generated(),
        "generator": "python3 tools/phase4_reconcile_baseline_dependencies.py --write",
        "source_dependencies": {
            "analysis/mechanics_baseline.yaml": baseline_sha,
            "tools/phase4_reconcile_baseline_dependencies.py": file_sha(Path(__file__)),
        },
        "allowed_changed_rows": list(ALLOWED_CHANGED_ROWS),
        "artifacts": report_rows,
        "errors": [],
        "valid": True,
    }
    return updates, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        updates, report = build()
    except (OSError, ValueError, KeyError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.write:
        for path, document in updates:
            path.write_bytes(artifact_rendered(document))
        OUTPUT.write_bytes(rendered(report))
    elif args.check:
        if any(path.read_bytes() != artifact_rendered(document) for path, document in updates):
            print("reconciled C16 artifact metadata is stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != rendered(report):
            print("baseline dependency reconciliation report is stale", file=sys.stderr)
            return 1
    else:
        print(rendered(report).decode(), end="")
    print("PASS: 3 C16 artifacts retain identical runtime/context payloads", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
