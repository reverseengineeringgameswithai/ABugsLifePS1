#!/usr/bin/env python3
"""Bank an external hard-truth acceptance for scheduler investments 10-12."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NOTE = ROOT / "ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Acceleration Tooling Strategy.md"
START = "<!-- PHASE4_ACCELERATION_SCHEDULER3_RATCHET_VERDICT_START -->"
END = "<!-- PHASE4_ACCELERATION_SCHEDULER3_RATCHET_VERDICT_END -->"
SCHEMA = "abl-phase4-acceleration-scheduler-hard-truth-decision/1"
ACCEPTED_PARENT = "4f477bd1653dc897c04fd3411dd9b5c5e2e1bd97"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TOP_KEYS = (
    "schema", "run_id", "reviewed_commit", "accepted_parent", "verified_at",
    "verdict", "gaps", "required_inputs", "evidence", "conclusion",
)
EVIDENCE_KEYS = (
    "identities_isolation", "retained_reproduction", "mutation_checks",
    "integration_checks", "candidate_parent_differential",
)
IDENTITY_KEYS = (
    "candidate_commit", "accepted_parent", "verification_checkout_detached",
    "candidate_worktree_clean", "duckstation_untouched", "redux_untouched",
    "external_outputs_outside_repository",
)
REPRODUCTION_KEYS = (
    "queue_sha256", "gate_sha256", "evidence_dag_sha256", "rows",
    "candidate_batches", "all_fixture_covers_complete",
    "cooldown_sequence_reproduced", "expected_value_reproduced",
    "weighted_cover_reproduced",
)
DIFFERENTIAL_KEYS = (
    "candidate_commit", "parent_commit", "candidate_passed", "candidate_failed",
    "candidate_skipped", "parent_passed", "parent_failed", "parent_skipped",
    "candidate_failed_nodeids_sha256", "parent_failed_nodeids_sha256",
    "same_failed_nodeids", "candidate_only_failures", "parent_only_failures",
)
INTEGRATION_IDS = (
    "focused_scheduler", "movie_priority_controller", "all_acceleration_regressions",
    "inventory_freshness", "pristine_build_identity", "evidence_dag",
    "phase4_gate", "vault_validation", "forbidden_artifacts",
)
INTEGRATION_COMMANDS = {
    "focused_scheduler": (
        "python -m pytest -q tests/test_phase4_scheduler_policy.py "
        "tests/test_phase4_acceleration_scheduler_bank.py"
    ),
    "movie_priority_controller": (
        "python -m pytest -q tests/test_phase4_movie_priority.py"
    ),
    "all_acceleration_regressions": (
        "python -m pytest -q tests/test_phase4_acceleration_bank.py "
        "tests/test_phase4_acceleration_next_bank.py "
        "tests/test_phase4_acceleration_third_bank.py "
        "tests/test_phase4_acceleration_scheduler_bank.py "
        "tests/test_phase4_scheduler_policy.py "
        "tests/test_phase4_movie_priority.py "
        "tests/test_phase4_closure_debt.py tests/test_phase4_evidence_dag.py "
        "tests/test_phase4_method_metrics.py "
        "tests/test_phase4_mips_oracle.py tests/test_phase4_trace_warehouse.py "
        "tests/test_phase4_binary_schema_fuzz.py "
        "tests/test_phase4_external_evidence.py"
    ),
    "inventory_freshness": (
        "python -m pytest -q tests/test_phase4_registry.py::"
        "test_generator_artifact_test_and_schema_discovery_has_no_omissions "
        "tests/test_phase4_registry.py::"
        "test_retained_artifact_source_dependencies_are_recomputed_and_visible"
    ),
    "pristine_build_identity": "python tools/build_identity.py --verify",
    "evidence_dag": "python tools/phase4_evidence_dag.py --check",
    "phase4_gate": "python tools/phase4_gate.py --check",
    "vault_validation": "python tools/validate_vault.py --check",
    "forbidden_artifacts": (
        "python -m pytest -q tests/test_no_forbidden_artifacts.py"
    ),
}
MUTATION_TESTS = {
    "policy_exact_types": (
        "tests/test_phase4_scheduler_policy.py::"
        "test_policy_rejects_authority_type_shape_and_value_drift",
    ),
    "scheduler_integer_inputs": (
        "tests/test_phase4_scheduler_policy.py::"
        "test_expected_value_rejects_boolean_authoritative_numbers",
    ),
    "packet_progress_snapshot_binding": (
        "tests/test_phase4_scheduler_policy.py::"
        "test_packet_rejects_fabricated_or_type_drifted_progress",
        "tests/test_phase4_scheduler_policy.py::"
        "test_equal_debt_snapshots_cannot_claim_a_reduction",
        "tests/test_phase4_scheduler_policy.py::"
        "test_debt_snapshot_campaign_must_match_attempted_packet",
    ),
    "packet_history_continuity": (
        "tests/test_phase4_scheduler_policy.py::"
        "test_packet_rejects_history_reset_truncation_and_selected_batch_forgery",
        "tests/test_phase4_scheduler_policy.py::"
        "test_attempt_history_capacity_fails_closed_without_truncation",
        "tests/test_phase4_scheduler_policy.py::"
        "test_packet_requires_exact_evidence_for_every_historical_attempt",
        "tests/test_phase4_scheduler_policy.py::"
        "test_real_source_backed_debt_reduction_can_advance_to_new_queue",
        "tests/test_phase4_scheduler_policy.py::"
        "test_historical_queue_rebuild_uses_bound_ownership_snapshot",
    ),
    "fixture_identity_aliasing": (
        "tests/test_phase4_scheduler_policy.py::"
        "test_weighted_cover_rejects_conflicting_shared_path_identity",
    ),
    "capsule_payload_tree": (
        "tests/test_phase4_movie_priority.py::"
        "test_capsule_manifest_without_exact_payload_tree_is_rejected",
        "tests/test_phase4_movie_priority.py::"
        "test_capsule_positive_result_is_not_reused_after_payload_drift",
        "tests/test_phase4_movie_priority.py::"
        "test_queue_authority_fingerprint_tracks_derived_index_payload",
    ),
    "fixture_mandatory_evidence": (
        "tests/test_phase4_scheduler_policy.py::"
        "test_capsule_requirements_remain_uncovered_without_verified_evidence",
        "tests/test_phase4_scheduler_policy.py::"
        "test_capsule_availability_cannot_shrink_out_of_cover_universe",
    ),
    "debt_snapshot_authority": (
        "tests/test_phase4_scheduler_policy.py::"
        "test_debt_snapshots_require_canonical_rows_and_consistent_counts",
    ),
    "queue_readiness_types": (
        "tests/test_phase4_scheduler_policy.py::"
        "test_expected_value_rejects_boolean_readiness_collections",
        "tests/test_phase4_scheduler_policy.py::"
        "test_packet_rejects_readiness_type_drift_even_on_ineligible_rows",
    ),
    "queue_batch_regeneration": (
        "tests/test_phase4_scheduler_policy.py::"
        "test_packet_rejects_forged_batch_metadata_and_coupling",
        "tests/test_phase4_scheduler_policy.py::"
        "test_packet_rejects_coordinated_self_consistent_queue_provenance_forgery",
    ),
    "controller_snapshot_propagation": (
        "tests/test_phase4_movie_priority.py::"
        "test_controller_threads_movie_ready_through_every_continuation",
        "tests/test_phase4_movie_priority.py::"
        "test_controller_policy_propagation_and_verifier_cadence_are_mutation_guarded",
    ),
    "bank_independent_commit_and_artifacts": (
        "tests/test_phase4_acceleration_scheduler_bank.py::"
        "test_bank_requires_commit_authority_outside_decision_content",
        "tests/test_phase4_acceleration_scheduler_bank.py::"
        "test_retained_reproduction_is_bound_to_current_artifacts",
    ),
}
ARTIFACT_PATHS = {
    "queue_sha256": ROOT / "analysis/phase4_movie_priority_queue.json",
    "gate_sha256": ROOT / "analysis/phase4_gate.json",
    "evidence_dag_sha256": ROOT / "analysis/phase4_evidence_dag.json",
}


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def load_decision(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    document = json.loads(
        raw.decode("utf-8"), object_pairs_hook=_pairs_no_duplicates,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number: {value}")))
    if not isinstance(document, dict):
        raise ValueError("decision must be one JSON object")
    return document, raw


def _exact_keys(value: Any, keys: tuple[str, ...], label: str,
                errors: list[str]) -> dict:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    if tuple(value) != keys:
        errors.append(f"{label} fields/order must be exactly {list(keys)}")
    return value


def _strict_int(value: Any, label: str, errors: list[str], minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        errors.append(f"{label} must be an integer >= {minimum}")


def artifact_facts() -> dict[str, Any]:
    queue = json.loads(ARTIFACT_PATHS["queue_sha256"].read_text(
        encoding="utf-8"))
    return {
        **{
            key: hashlib.sha256(path.read_bytes()).hexdigest()
            for key, path in ARTIFACT_PATHS.items()
        },
        "rows": len(queue.get("rows") or []),
        "candidate_batches": len(queue.get("candidate_batches") or []),
        "all_fixture_covers_complete": bool(queue.get("candidate_batches")) and all(
            (batch.get("fixture_cover") or {}).get("complete") is True
            and (batch.get("fixture_cover") or {}).get("uncovered") == []
            for batch in queue.get("candidate_batches") or []),
    }


def validate_decision(document: Any, expected_commit: str) -> list[str]:
    errors: list[str] = []
    top = _exact_keys(document, TOP_KEYS, "decision", errors)
    if top.get("schema") != SCHEMA:
        errors.append("decision schema is invalid")
    if not isinstance(top.get("run_id"), str) or not top["run_id"].strip():
        errors.append("run_id must be a non-empty string")
    if not HEX40.fullmatch(str(top.get("reviewed_commit") or "")) or \
            top.get("reviewed_commit") != expected_commit:
        errors.append("reviewed_commit is not the exact candidate")
    if top.get("accepted_parent") != ACCEPTED_PARENT:
        errors.append("accepted_parent is not the scheduler tranche parent")
    try:
        parsed = datetime.fromisoformat(str(top.get("verified_at") or "").replace(
            "Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
    except ValueError:
        errors.append("verified_at must be a real timezone-bearing RFC3339 timestamp")
    if top.get("verdict") != "accepted":
        errors.append("verdict must be accepted")
    for key in ("gaps", "required_inputs"):
        if top.get(key) != []:
            errors.append(f"{key} must be exactly empty")
    conclusion = top.get("conclusion")
    if not isinstance(conclusion, str) or not conclusion.strip() or \
            any(token in conclusion for token in ("\n", "\r", "<!--", "-->")):
        errors.append("conclusion must be one safe non-empty line")

    evidence = _exact_keys(top.get("evidence"), EVIDENCE_KEYS, "evidence", errors)
    identities = _exact_keys(evidence.get("identities_isolation"), IDENTITY_KEYS,
                             "identities_isolation", errors)
    if identities.get("candidate_commit") != expected_commit:
        errors.append("identity candidate does not match reviewed commit")
    if identities.get("accepted_parent") != ACCEPTED_PARENT:
        errors.append("identity accepted parent is wrong")
    for key in IDENTITY_KEYS[2:]:
        if identities.get(key) is not True:
            errors.append(f"identities_isolation.{key} must be literal true")

    reproduction = _exact_keys(evidence.get("retained_reproduction"),
                               REPRODUCTION_KEYS, "retained_reproduction", errors)
    try:
        actual_artifacts = artifact_facts()
    except (OSError, json.JSONDecodeError) as exc:
        actual_artifacts = {}
        errors.append(f"cannot reproduce retained scheduler artifacts: {exc}")
    for key in ("queue_sha256", "gate_sha256", "evidence_dag_sha256"):
        if not HEX64.fullmatch(str(reproduction.get(key) or "")):
            errors.append(f"retained_reproduction.{key} must be SHA-256")
        if actual_artifacts and reproduction.get(key) != actual_artifacts[key]:
            errors.append(f"retained_reproduction.{key} is not the current artifact")
    for key, expected in (("rows", 107),):
        _strict_int(reproduction.get(key), f"retained_reproduction.{key}", errors, 1)
        if reproduction.get(key) != expected:
            errors.append(f"retained_reproduction.{key} must be exactly {expected}")
        if actual_artifacts and reproduction.get(key) != actual_artifacts[key]:
            errors.append(f"retained_reproduction.{key} is not current")
    _strict_int(reproduction.get("candidate_batches"),
                "retained_reproduction.candidate_batches", errors, 1)
    if actual_artifacts and reproduction.get("candidate_batches") != \
            actual_artifacts["candidate_batches"]:
        errors.append("retained_reproduction.candidate_batches is not current")
    if actual_artifacts and reproduction.get("all_fixture_covers_complete") != \
            actual_artifacts["all_fixture_covers_complete"]:
        errors.append("retained fixture-cover result is not current")
    for key in REPRODUCTION_KEYS[5:]:
        if reproduction.get(key) is not True:
            errors.append(f"retained_reproduction.{key} must be literal true")

    mutations = evidence.get("mutation_checks")
    if not isinstance(mutations, list) or len(mutations) != len(MUTATION_TESTS):
        errors.append("mutation_checks must enumerate the exact reviewed catalog")
    else:
        ids: list[str] = []
        for index, item in enumerate(mutations):
            row = _exact_keys(item, ("id", "passed", "test_nodeids"),
                              f"mutation_checks[{index}]", errors)
            if not isinstance(row.get("id"), str) or not row["id"].strip():
                errors.append(f"mutation_checks[{index}].id is invalid")
            else:
                ids.append(row["id"])
            if row.get("passed") is not True:
                errors.append(f"mutation_checks[{index}].passed must be true")
            nodeids = row.get("test_nodeids")
            if not isinstance(nodeids, list) or not nodeids or not all(
                    isinstance(node, str) and "::" in node for node in nodeids):
                errors.append(f"mutation_checks[{index}].test_nodeids are invalid")
        if len(ids) != len(set(ids)):
            errors.append("mutation check IDs must be unique")
        if tuple(ids) != tuple(MUTATION_TESTS):
            errors.append("mutation check IDs/order are not the reviewed catalog")
        for row in mutations:
            mutation_id = row.get("id")
            if mutation_id in MUTATION_TESTS and tuple(row.get("test_nodeids") or []) \
                    != MUTATION_TESTS[mutation_id]:
                errors.append(
                    f"mutation check {mutation_id} nodeids are not exact")

    integrations = evidence.get("integration_checks")
    if not isinstance(integrations, list) or len(integrations) != len(
            INTEGRATION_IDS):
        errors.append("integration_checks must enumerate the exact check set")
    else:
        if tuple(item.get("id") for item in integrations
                 if isinstance(item, dict)) != INTEGRATION_IDS:
            errors.append("integration check IDs/order are invalid")
        for index, item in enumerate(integrations):
            row = _exact_keys(item, ("id", "command", "exit_code", "passed",
                                     "summary"),
                              f"integration_checks[{index}]", errors)
            if not isinstance(row.get("command"), str) or not row["command"].strip():
                errors.append(f"integration_checks[{index}].command is invalid")
            elif row.get("id") in INTEGRATION_COMMANDS and \
                    row.get("command") != INTEGRATION_COMMANDS[row["id"]]:
                errors.append(
                    f"integration_checks[{index}].command is not exact")
            _strict_int(row.get("exit_code"),
                        f"integration_checks[{index}].exit_code", errors)
            if row.get("exit_code") != 0 or row.get("passed") is not True:
                errors.append(f"integration_checks[{index}] did not pass exactly")
            if not isinstance(row.get("summary"), str) or not row["summary"].strip():
                errors.append(f"integration_checks[{index}].summary is invalid")

    diff = _exact_keys(evidence.get("candidate_parent_differential"),
                       DIFFERENTIAL_KEYS, "candidate_parent_differential", errors)
    if diff.get("candidate_commit") != expected_commit or \
            diff.get("parent_commit") != ACCEPTED_PARENT:
        errors.append("differential identities are invalid")
    for key in ("candidate_passed", "candidate_failed", "candidate_skipped",
                "parent_passed", "parent_failed", "parent_skipped"):
        _strict_int(diff.get(key), f"differential.{key}", errors)
    for key in ("candidate_failed_nodeids_sha256",
                "parent_failed_nodeids_sha256"):
        if not HEX64.fullmatch(str(diff.get(key) or "")):
            errors.append(f"differential.{key} must be SHA-256")
    candidate_only = diff.get("candidate_only_failures")
    parent_only = diff.get("parent_only_failures")
    for label, values in (("candidate_only_failures", candidate_only),
                          ("parent_only_failures", parent_only)):
        if not isinstance(values, list) or not all(
                isinstance(nodeid, str) and "::" in nodeid
                for nodeid in values) or len(values) != len(set(values)):
            errors.append(
                f"differential.{label} must be a unique test-nodeid list")
    if candidate_only != []:
        errors.append("candidate/parent differential has candidate-only failures")
    hashes_equal = diff.get("candidate_failed_nodeids_sha256") == \
        diff.get("parent_failed_nodeids_sha256")
    sets_equal = candidate_only == [] and parent_only == []
    if type(diff.get("same_failed_nodeids")) is not bool or \
            diff.get("same_failed_nodeids") != (hashes_equal and sets_equal):
        errors.append("differential same_failed_nodeids is not exactly derived")
    if type(diff.get("candidate_failed")) is int and \
            type(diff.get("parent_failed")) is int and \
            isinstance(parent_only, list) and all(
            isinstance(nodeid, str) and "::" in nodeid
            for nodeid in parent_only):
        expected_parent_failed = diff.get("candidate_failed", -1) + len(parent_only)
        if diff.get("parent_failed") != expected_parent_failed:
            errors.append(
                "differential parent failure count disagrees with improvements")
    return sorted(set(errors))


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def git_preflight(expected_commit: str) -> list[str]:
    errors: list[str] = []
    try:
        head = _git("rev-parse", "HEAD")
        if head != expected_commit:
            errors.append("HEAD no longer matches the reviewed commit")
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ACCEPTED_PARENT,
             expected_commit], cwd=ROOT)
        if ancestor.returncode != 0:
            errors.append("accepted parent is not an ancestor of reviewed commit")
        if _git("status", "--porcelain=v1", "--untracked-files=all"):
            errors.append("candidate worktree is not clean immediately before bank")
    except RuntimeError as exc:
        errors.append(f"git preflight failed closed: {exc}")
    return errors


def bank(decision_path: Path, expected_commit: str) -> None:
    document, raw = load_decision(decision_path)
    if not HEX40.fullmatch(expected_commit):
        raise SystemExit("ERROR: --reviewed-commit must be an exact lowercase commit")
    errors = validate_decision(document, expected_commit)
    errors.extend(git_preflight(expected_commit))
    note = NOTE.read_text(encoding="utf-8")
    if "acceleration_scheduler3_ratchet: pending" not in note:
        errors.append("scheduler ratchet frontmatter is not pending exactly once")
    if note.count(START) != 1 or note.count(END) != 1:
        errors.append("scheduler ratchet marker is missing or duplicated")
    if errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in sorted(set(errors))))
    decision_sha = hashlib.sha256(raw).hexdigest()
    replacement = (
        f"{START}\nHard-truth accepted. Run `{document['run_id']}` reviewed commit "
        f"`{expected_commit}` at {document['verified_at']}. Conclusion: "
        f"{document['conclusion']} Decision SHA-256: `{decision_sha}`.\n{END}")
    start = note.index(START)
    end = note.index(END, start) + len(END)
    note = note[:start] + replacement + note[end:]
    note = note.replace("acceleration_scheduler3_ratchet: pending",
                        "acceleration_scheduler3_ratchet: accepted", 1)
    NOTE.write_text(note, encoding="utf-8")
    print(f"[phase4-acceleration-scheduler-bank] accepted {expected_commit}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decision", type=Path)
    parser.add_argument("--reviewed-commit", required=True)
    args = parser.parse_args()
    bank(args.decision, args.reviewed_commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
