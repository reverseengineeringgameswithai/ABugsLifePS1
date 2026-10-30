#!/usr/bin/env python3
"""Reconcile C15's offline capsule lane without replaying its live control."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

import phase4_common as common
import phase4_respawn_status_policy as policy


ARTIFACT = common.ROOT / "analysis/phase4_respawn_status_policy.json"
OUTPUT = common.ROOT / "analysis/phase4_capsule_consumer_reconciliation.json"
HISTORICAL_LIVE_GENERATOR_SHA256 = (
    "dc92cbbccd4f2544231ef36775f7ad78c9a530b6233590e176637418992bf339")
ALLOWED_TOP_LEVEL_CHANGES = ("capsule_first_lane", "source_dependencies")


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_sha(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def artifact_rendered(document: dict) -> bytes:
    return (json.dumps(document, indent=1) + "\n").encode()


def report_rendered(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def stable_generated(previous: dict) -> str:
    value = previous.get("generated")
    return value if isinstance(value, str) and value else date.today().isoformat()


def retained_live_payload(document: dict) -> dict:
    """Exclude only the regenerated offline lane and dependency metadata."""
    return {key: value for key, value in document.items()
            if key not in ALLOWED_TOP_LEVEL_CHANGES}


def build(*, verify_external: bool = False) -> tuple[dict, dict]:
    document = json.loads(ARTIFACT.read_text())
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.is_file() else {}
    run = document.get("run_provenance") or {}
    if run.get("generator_sha256") != HISTORICAL_LIVE_GENERATOR_SHA256:
        raise ValueError("C15 historical live generator identity drifted")

    previous_lane = document.get("capsule_first_lane") or {}
    current_lane = policy.build_capsule_first_census(
        verify_external=verify_external)
    previous_relevant = previous_lane.get("relevant_capsules") or []
    current_relevant = current_lane.get("relevant_capsules") or []
    if previous_relevant != current_relevant:
        raise ValueError(
            "C15 relevant capsule hashes or exact typed RAM queries changed; "
            "the retained live control cannot be metadata-reconciled")
    if current_lane.get("capsule_count") != policy.EXPECTED_CAPSULE_COUNT:
        raise ValueError("current capsule lane is incomplete")

    live_payload_sha = object_sha(retained_live_payload(document))
    prior_live_sha = previous.get("retained_live_payload_sha256")
    if prior_live_sha and prior_live_sha != live_payload_sha:
        raise ValueError("C15 retained live evidence payload changed")

    original_artifact_sha = (
        previous.get("artifact_sha256_before") or file_sha(ARTIFACT))
    original_lane_sha = (
        previous.get("capsule_lane_sha256_before") or object_sha(previous_lane))
    original_index_sha = (
        previous.get("capsule_index_sha256_before") or
        previous_lane.get("preservation_index_sha256"))
    original_validator_sha = (
        previous.get("capsule_validator_sha256_before") or
        (document.get("source_dependencies") or {}).get(
            "tools/phase4_trace_capsules.py"))

    document["capsule_first_lane"] = current_lane
    dependencies = document.get("source_dependencies") or {}
    dependencies["analysis/phase4_trace_capsule_set.json"] = file_sha(
        policy.CAPSULE_INDEX)
    dependencies["tools/phase4_trace_capsules.py"] = file_sha(
        policy.CAPSULE_VALIDATOR)
    document["source_dependencies"] = dependencies
    artifact_after = hashlib.sha256(artifact_rendered(document)).hexdigest()

    report = {
        "_comment": (
            "Generated offline-only C15 reconciliation. The current 55-row "
            "capsule set and exact reader reproduce both retained E10 typed RAM "
            "query sets. Historical live counterfactual evidence and its original "
            "generator identity remain untouched."),
        "schema": "abl-phase4-capsule-consumer-reconciliation/1",
        "generated": stable_generated(previous),
        "generator": (
            "python3 tools/phase4_reconcile_capsule_consumers.py "
            "--verify-external --write"),
        "allowed_top_level_changes": list(ALLOWED_TOP_LEVEL_CHANGES),
        "artifact": "analysis/phase4_respawn_status_policy.json",
        "artifact_sha256_before": original_artifact_sha,
        "artifact_sha256_after": artifact_after,
        "capsule_lane_sha256_before": original_lane_sha,
        "capsule_lane_sha256_after": object_sha(current_lane),
        "capsule_index_sha256_before": original_index_sha,
        "capsule_index_sha256_after": file_sha(policy.CAPSULE_INDEX),
        "capsule_validator_sha256_before": original_validator_sha,
        "capsule_validator_sha256_after": file_sha(policy.CAPSULE_VALIDATOR),
        "historical_live_generator_sha256": HISTORICAL_LIVE_GENERATOR_SHA256,
        "current_generator_sha256": file_sha(Path(policy.__file__)),
        "retained_live_payload_sha256": live_payload_sha,
        "relevant_capsule_query_sha256_before": object_sha(previous_relevant),
        "relevant_capsule_query_sha256_after": object_sha(current_relevant),
        "relevant_capsule_queries_identical": True,
        "current_capsule_count": current_lane["capsule_count"],
        "current_movie_count": current_lane["movie_count"],
        "current_total_external_bytes": current_lane["total_external_bytes"],
        "freshness_validator": current_lane["freshness_validator"],
        "historical_live_provenance_preserved": True,
        "live_replay_required": False,
        "source_dependencies": {
            "analysis/phase4_trace_capsule_set.json": file_sha(policy.CAPSULE_INDEX),
            "tools/phase4_trace_capsules.py": file_sha(policy.CAPSULE_VALIDATOR),
            "tools/phase4_respawn_status_policy.py": file_sha(Path(policy.__file__)),
            "tools/phase4_reconcile_capsule_consumers.py": file_sha(Path(__file__)),
        },
        "errors": [],
        "valid": True,
    }
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-external", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        artifact, report = build(verify_external=args.verify_external)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.write:
        ARTIFACT.write_bytes(artifact_rendered(artifact))
        OUTPUT.write_bytes(report_rendered(report))
    elif args.check:
        if ARTIFACT.read_bytes() != artifact_rendered(artifact):
            print("C15 capsule consumer is stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != report_rendered(report):
            print("C15 capsule-consumer reconciliation report is stale", file=sys.stderr)
            return 1
    else:
        print(report_rendered(report).decode(), end="")
    print(
        "PASS: C15 55-capsule preflight current; 2/2 E10 query sets unchanged",
        file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
