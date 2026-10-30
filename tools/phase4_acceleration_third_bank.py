#!/usr/bin/env python3
"""Bank an accepted hard-truth decision for acceleration investments 7-9."""
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
START = "<!-- PHASE4_ACCELERATION_THIRD3_RATCHET_VERDICT_START -->"
END = "<!-- PHASE4_ACCELERATION_THIRD3_RATCHET_VERDICT_END -->"
SCHEMA = "abl-phase4-acceleration-third3-hard-truth-decision/1"
ACCEPTED_PARENT = "f5f0b8ef3ec32fe9a32c3d6a9aa9ef06d70033cb"
TOP_LEVEL_KEYS = {
    "schema", "run_id", "reviewed_commit", "accepted_parent", "verified_at",
    "verdict", "gaps", "required_inputs", "evidence", "conclusion",
}
EVIDENCE_KEYS = {
    "identities_isolation", "environment", "retained_artifact_reproduction",
    "focused_integration_checks", "prior_exploit_regressions",
    "candidate_parent_differential",
}
RETAINED_ARTIFACTS = (
    "analysis/phase4_trace_warehouse_pilot.json",
    "analysis/phase4_binary_schema_fuzz_pilot.json",
    "analysis/phase4_external_evidence_manifest.json",
    "analysis/phase4_external_evidence_pilot.json",
)
INTEGRATION_COMMANDS = {
    "focused_pytest": (
        "python -m pytest -q tests/test_phase4_trace_warehouse.py "
        "tests/test_phase4_binary_schema_fuzz.py "
        "tests/test_phase4_external_evidence.py "
        "tests/test_phase4_acceleration_third_bank.py"
    ),
    "inventory_freshness": (
        "python -m pytest -q "
        "tests/test_phase4_registry.py::"
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
INTEGRATION_CHECKS = tuple(INTEGRATION_COMMANDS)
PRIOR_EXPLOIT_REGRESSIONS = (
    "evidence_distinct_failure_domains",
    "evidence_device_domain_and_root_independence",
    "evidence_hardlink_and_inode_alias_rejection",
    "binary_schema_endianness_exact",
    "warehouse_top_level_errors_empty",
    "warehouse_frame_interval_and_bool_rejection",
    "warehouse_unique_movie_binding",
    "warehouse_canonical_physical_partition_identity",
    "warehouse_exact_policy_and_row_schema",
    "fuzz_exact_limits_and_bool_rejection",
    "evidence_exact_runtime_tree_manifest",
    "evidence_exact_capsule_tree_manifest",
    "bank_structured_decision_contract",
    "bank_exact_python_runtime",
    "evidence_round6_complete_strict_types",
    "bank_git_preflight_fail_closed",
    "fuzz_supplied_policy_entrypoints",
    "bank_prior_regression_catalog_complete",
    "warehouse_complete_retained_binding_set",
)
PRIOR_EXPLOIT_TESTS = {
    "evidence_distinct_failure_domains": (
        "tests/test_phase4_external_evidence.py::"
        "test_same_device_directories_and_same_declared_domain_count_once",
    ),
    "evidence_device_domain_and_root_independence": (
        "tests/test_phase4_external_evidence.py::"
        "test_distinct_device_and_declared_domain_model_requires_both_dimensions",
        "tests/test_phase4_external_evidence.py::"
        "test_nested_roots_are_rejected_and_private_annex_is_not_independent",
    ),
    "evidence_hardlink_and_inode_alias_rejection": (
        "tests/test_phase4_external_evidence.py::"
        "test_remote_aliases_and_shared_physical_content_cannot_fake_independence",
    ),
    "binary_schema_endianness_exact": (
        "tests/test_phase4_binary_schema_fuzz.py::"
        "test_each_kaitai_schema_rejects_endian_drift",
        "tests/test_phase4_binary_schema_fuzz.py::"
        "test_each_schema_declaration_rejects_endian_drift",
    ),
    "warehouse_top_level_errors_empty": (
        "tests/test_phase4_trace_warehouse.py::"
        "test_capsule_set_rejects_incomplete_control_truncation_and_repro_drift",
    ),
    "warehouse_frame_interval_and_bool_rejection": (
        "tests/test_phase4_trace_warehouse.py::"
        "test_event_frame_rejects_outside_capsule_boundary_span_and_bool",
        "tests/test_phase4_trace_warehouse.py::"
        "test_block_and_partition_counts_reject_bool_as_int",
    ),
    "warehouse_unique_movie_binding": (
        "tests/test_phase4_trace_warehouse.py::"
        "test_import_rejects_second_binding_for_same_retained_movie",
        "tests/test_phase4_trace_warehouse.py::"
        "test_cross_movie_query_defensively_counts_distinct_movie_not_capsule_id",
    ),
    "warehouse_canonical_physical_partition_identity": (
        "tests/test_phase4_trace_warehouse.py::"
        "test_import_rejects_noncanonical_alias_and_hardlink_identity",
    ),
    "warehouse_exact_policy_and_row_schema": (
        "tests/test_phase4_trace_warehouse.py::"
        "test_policy_is_recursively_exact_typed_and_fail_closed",
        "tests/test_phase4_trace_warehouse.py::"
        "test_capsule_rows_match_exact_retained_v2_schema",
    ),
    "fuzz_exact_limits_and_bool_rejection": (
        "tests/test_phase4_binary_schema_fuzz.py::"
        "test_each_resource_limit_is_exactly_pinned",
        "tests/test_phase4_binary_schema_fuzz.py::"
        "test_each_authority_field_is_exact_bool_true",
        "tests/test_phase4_binary_schema_fuzz.py::"
        "test_remaining_policy_authority_is_exactly_pinned",
    ),
    "evidence_exact_runtime_tree_manifest": (
        "tests/test_phase4_external_evidence.py::"
        "test_runtime_tree_binds_manifest_and_rejects_undeclared_entries",
    ),
    "evidence_exact_capsule_tree_manifest": (
        "tests/test_phase4_external_evidence.py::"
        "test_capsule_tree_verifier_recomputes_manifest_tree_and_detects_drift",
    ),
    "bank_structured_decision_contract": (
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_valid_decision_has_exact_nonempty_evidence_contract",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_top_level_contract_rejects_unknown_and_missing_fields",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_json_loader_rejects_duplicate_fields_and_nonfinite_numbers",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_top_level_scalar_and_container_type_drift_is_rejected",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_decision_rejects_rejection_nonempty_gaps_and_wrong_candidate",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_note_authored_decision_strings_cannot_inject_lines_or_markers",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_accepted_parent_is_mandatory_exact_and_repeated_in_evidence_and_suite",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_verified_at_must_be_a_real_rfc3339_timestamp",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_each_evidence_domain_is_mandatory_exact_and_nonempty",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_identity_and_isolation_evidence_is_exact_typed_and_candidate_bound",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_retained_reproduction_binds_exact_artifacts_hashes_and_counts",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_focused_integration_checks_require_exact_order_success_and_evidence",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_prior_exploit_regressions_require_every_exact_passing_test_binding",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_candidate_parent_differential_rejects_parentless_and_type_drifted_claims",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_bank_changes_only_third_ratchet_and_marker",
        "tests/test_phase4_acceleration_third_bank.py::test_bank_rejects_repeat",
    ),
    "bank_exact_python_runtime": (
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_environment_evidence_is_exact_and_pinned",
    ),
    "evidence_round6_complete_strict_types": (
        "tests/test_phase4_external_evidence.py::"
        "test_policy_is_one_complete_recursively_typed_and_ordered_contract",
        "tests/test_phase4_external_evidence.py::"
        "test_registry_rejects_every_round6_shape_type_and_authority_mutation",
        "tests/test_phase4_external_evidence.py::"
        "test_receipts_reject_complete_top_level_nested_and_scalar_type_drift",
        "tests/test_phase4_external_evidence.py::"
        "test_two_real_st_dev_copies_cannot_turn_bool_or_float_counts_into_readiness",
    ),
    "bank_git_preflight_fail_closed": (
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_git_preflight_accepts_clean_descendant_in_disposable_repository",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_git_preflight_rejects_dirty_tracked_file",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_git_preflight_rejects_staged_change",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_git_preflight_rejects_nonignored_untracked_file",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_git_preflight_allows_ignored_external_support",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_git_preflight_rejects_unrelated_history",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_git_preflight_rejects_wrong_head",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_git_preflight_fails_closed_when_git_command_fails",
    ),
    "fuzz_supplied_policy_entrypoints": (
        "tests/test_phase4_binary_schema_fuzz.py::"
        "test_high_level_entrypoints_validate_every_truthy_policy_before_work",
        "tests/test_phase4_binary_schema_fuzz.py::"
        "test_supplied_non_policy_never_falls_back_to_loading_or_creates_output",
    ),
    "bank_prior_regression_catalog_complete": (
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_prior_exploit_catalog_is_ordered_nonempty_and_has_unique_nodeids",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_each_late_round_regression_group_is_mandatory",
        "tests/test_phase4_acceleration_third_bank.py::"
        "test_each_late_round_nodeid_list_is_exact",
    ),
    "warehouse_complete_retained_binding_set": (
        "tests/test_phase4_trace_warehouse.py::"
        "test_import_and_public_build_require_complete_retained_movie_binding_set",
    ),
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
RFC3339_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?"
    r"(?:Z|[+-][0-9]{2}:[0-9]{2})"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    if any(type(key) is not str for key in value):
        raise ValueError(f"{label} field names must be strings")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        unknown = sorted(actual - keys)
        raise ValueError(f"{label} fields differ: missing={missing}; unknown={unknown}")
    return value


def _exact_list(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        raise ValueError(f"{label} must be a JSON array")
    return value


def _string(value: Any, label: str, *, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value.strip()):
        raise ValueError(f"{label} must be a non-empty JSON string")
    return value


def _boolean(value: Any, label: str, expected: bool) -> None:
    if type(value) is not bool or value is not expected:
        raise ValueError(f"{label} must be JSON {str(expected).lower()}")


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be a JSON integer >= {minimum}")
    return value


def _sha256(value: Any, label: str) -> str:
    value = _string(value, label)
    if SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return value


def _commit(value: Any, label: str) -> str:
    value = _string(value, label)
    if COMMIT_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a full lowercase Git object ID")
    return value


def _rfc3339(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} must be a real RFC3339 timestamp")
    if RFC3339_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be an RFC3339 timestamp with timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} is not a real RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include an RFC3339 timezone")
    return value


def _single_line(value: Any, label: str, *, pattern: str | None = None) -> str:
    value = _string(value, label)
    if any(character in value for character in ("\r", "\n")):
        raise ValueError(f"{label} must be a single-line JSON string")
    if pattern is not None and re.fullmatch(pattern, value) is None:
        raise ValueError(f"{label} contains forbidden characters")
    return value


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def parse_decision_json(text: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number is forbidden: {value}")

    value = json.loads(text, object_pairs_hook=_unique_json_object,
                       parse_constant=reject_constant)
    if type(value) is not dict:
        raise ValueError("decision must be a JSON object")
    return value


def _empty_string_list(value: Any, label: str) -> None:
    rows = _exact_list(value, label)
    if rows:
        raise ValueError(f"{label} must be empty")


def _validate_identities(value: Any, reviewed_commit: str) -> None:
    row = _exact_object(value, {
        "candidate_commit", "accepted_parent", "candidate_worktree_clean",
        "verification_checkout_detached", "external_outputs_outside_repository",
        "duckstation_untouched", "redux_untouched",
    }, "evidence.identities_isolation")
    if _commit(row["candidate_commit"], "identities candidate_commit") != reviewed_commit:
        raise ValueError("identities candidate_commit differs from reviewed_commit")
    if _commit(row["accepted_parent"], "identities accepted_parent") != ACCEPTED_PARENT:
        raise ValueError("identities accepted_parent is not the pinned accepted parent")
    for key in (
            "candidate_worktree_clean", "verification_checkout_detached",
            "external_outputs_outside_repository", "duckstation_untouched",
            "redux_untouched"):
        _boolean(row[key], f"identities {key}", True)


def _validate_environment(value: Any) -> None:
    row = _exact_object(value, {
        "python", "pytest", "pyyaml", "unicorn", "duckdb", "numpy",
        "requirements_provisioned",
    }, "evidence.environment")
    python = _string(row["python"], "environment python")
    if python != "3.14.5":
        raise ValueError("environment python must be exactly 3.14.5")
    expected = {
        "pytest": "9.1.1", "pyyaml": "6.0.3", "unicorn": "2.1.4",
        "duckdb": "1.5.5", "numpy": "2.5.1",
    }
    for key, pinned in expected.items():
        if type(row[key]) is not str or row[key] != pinned:
            raise ValueError(f"environment {key} must be exactly {pinned}")
    _boolean(row["requirements_provisioned"],
             "environment requirements_provisioned", True)


def _validate_artifacts(value: Any) -> None:
    row = _exact_object(value, {
        "artifacts", "warehouse_query_packs_reproduced",
        "fuzz_cases_reproduced_twice", "external_registry_objects_reproduced",
        "disposable_external_runs_passed",
    }, "evidence.retained_artifact_reproduction")
    artifacts = _exact_list(row["artifacts"], "retained artifacts")
    if len(artifacts) != len(RETAINED_ARTIFACTS):
        raise ValueError("retained artifacts must cover the exact retained set")
    for index, expected_path in enumerate(RETAINED_ARTIFACTS):
        item = _exact_object(artifacts[index], {
            "path", "recorded_sha256", "recomputed_sha256", "byte_exact",
        }, f"retained artifact {index}")
        if type(item["path"]) is not str or item["path"] != expected_path:
            raise ValueError("retained artifact order/path differs from the exact set")
        actual_sha256 = sha256(ROOT / expected_path)
        if _sha256(item["recorded_sha256"], "recorded artifact SHA-256") != actual_sha256:
            raise ValueError(f"recorded SHA-256 differs for {expected_path}")
        if _sha256(item["recomputed_sha256"], "recomputed artifact SHA-256") != actual_sha256:
            raise ValueError(f"recomputed SHA-256 differs for {expected_path}")
        _boolean(item["byte_exact"], "retained artifact byte_exact", True)
    if _exact_list(row["warehouse_query_packs_reproduced"],
                   "warehouse query packs") != [
            "first_change", "cohort_contrast", "block_enrichment", "cross_movie"]:
        raise ValueError("warehouse query packs must be the exact ordered four-pack")
    if _integer(row["fuzz_cases_reproduced_twice"],
                "fuzz cases reproduced twice", minimum=1) != 285:
        raise ValueError("fuzz_cases_reproduced_twice must be exactly 285")
    if _integer(row["external_registry_objects_reproduced"],
                "external registry objects reproduced", minimum=1) != 178:
        raise ValueError("external_registry_objects_reproduced must be exactly 178")
    _boolean(row["disposable_external_runs_passed"],
             "disposable_external_runs_passed", True)


def _validate_check_rows(value: Any) -> None:
    rows = _exact_list(value, "evidence.focused_integration_checks")
    if len(rows) != len(INTEGRATION_CHECKS):
        raise ValueError("focused integration checks must cover the exact check set")
    for index, expected_id in enumerate(INTEGRATION_CHECKS):
        row = _exact_object(rows[index], {
            "id", "command", "exit_code", "passed", "summary",
        }, f"focused integration check {index}")
        if type(row["id"]) is not str or row["id"] != expected_id:
            raise ValueError("focused integration check IDs/order differ")
        if type(row["command"]) is not str or row["command"] != \
                INTEGRATION_COMMANDS[expected_id]:
            raise ValueError(f"check {expected_id} command differs from the exact command")
        if _integer(row["exit_code"], f"check {expected_id} exit_code") != 0:
            raise ValueError(f"check {expected_id} exit_code must be zero")
        _boolean(row["passed"], f"check {expected_id} passed", True)
        _string(row["summary"], f"check {expected_id} summary")


def _validate_regressions(value: Any) -> None:
    rows = _exact_list(value, "evidence.prior_exploit_regressions")
    if len(rows) != len(PRIOR_EXPLOIT_REGRESSIONS):
        raise ValueError("prior exploit regressions must cover the exact exploit set")
    for index, expected_id in enumerate(PRIOR_EXPLOIT_REGRESSIONS):
        row = _exact_object(rows[index], {
            "id", "passed", "test_nodeids",
        }, f"prior exploit regression {index}")
        if type(row["id"]) is not str or row["id"] != expected_id:
            raise ValueError("prior exploit regression IDs/order differ")
        _boolean(row["passed"], f"regression {expected_id} passed", True)
        nodeids = _exact_list(row["test_nodeids"],
                              f"regression {expected_id} test_nodeids")
        if nodeids != list(PRIOR_EXPLOIT_TESTS[expected_id]):
            raise ValueError(
                f"regression {expected_id} must bind its exact adversarial test node IDs")


def _validate_suite(value: Any, label: str, expected_commit: str) -> dict[str, Any]:
    row = _exact_object(value, {
        "commit", "passed", "failed", "skipped", "failed_nodeids_sha256",
    }, label)
    if _commit(row["commit"], f"{label} commit") != expected_commit:
        raise ValueError(f"{label} commit differs from the required identity")
    _integer(row["passed"], f"{label} passed", minimum=1)
    _integer(row["failed"], f"{label} failed")
    _integer(row["skipped"], f"{label} skipped")
    _sha256(row["failed_nodeids_sha256"], f"{label} failed_nodeids_sha256")
    return row


def _validate_differential(value: Any, reviewed_commit: str) -> None:
    row = _exact_object(value, {
        "candidate", "parent", "same_failed_nodeids",
        "candidate_only_failures", "parent_only_failures",
    }, "evidence.candidate_parent_differential")
    candidate = _validate_suite(row["candidate"], "candidate suite", reviewed_commit)
    parent = _validate_suite(row["parent"], "parent suite", ACCEPTED_PARENT)
    _boolean(row["same_failed_nodeids"], "same_failed_nodeids", True)
    _empty_string_list(row["candidate_only_failures"], "candidate_only_failures")
    _empty_string_list(row["parent_only_failures"], "parent_only_failures")
    if candidate["failed"] != parent["failed"]:
        raise ValueError("candidate and parent failed counts differ")
    if candidate["failed_nodeids_sha256"] != parent["failed_nodeids_sha256"]:
        raise ValueError("candidate and parent failed node IDs differ")


def _validate_evidence(value: Any, reviewed_commit: str) -> None:
    evidence = _exact_object(value, EVIDENCE_KEYS, "evidence")
    _validate_identities(evidence["identities_isolation"], reviewed_commit)
    _validate_environment(evidence["environment"])
    _validate_artifacts(evidence["retained_artifact_reproduction"])
    _validate_check_rows(evidence["focused_integration_checks"])
    _validate_regressions(evidence["prior_exploit_regressions"])
    _validate_differential(evidence["candidate_parent_differential"], reviewed_commit)


def validate_decision(decision: dict, reviewed_commit: str) -> None:
    decision = _exact_object(decision, TOP_LEVEL_KEYS, "decision")
    reviewed_commit = _commit(reviewed_commit, "requested reviewed_commit")
    if reviewed_commit == ACCEPTED_PARENT:
        raise ValueError("reviewed commit must differ from the accepted parent")
    if type(decision["schema"]) is not str or decision["schema"] != SCHEMA:
        raise ValueError("invalid third-three hard-truth decision schema")
    _single_line(decision["run_id"], "decision run_id", pattern=r"[A-Za-z0-9._:-]+")
    if _commit(decision["reviewed_commit"], "decision reviewed_commit") != reviewed_commit:
        raise ValueError("decision reviewed_commit differs from the requested commit")
    if _commit(decision["accepted_parent"], "decision accepted_parent") != ACCEPTED_PARENT:
        raise ValueError("decision accepted_parent is not the pinned accepted parent")
    _rfc3339(decision["verified_at"], "decision verified_at")
    if type(decision["verdict"]) is not str or decision["verdict"] != "accepted":
        raise ValueError("only an accepted hard-truth decision may be banked")
    _empty_string_list(decision["gaps"], "decision gaps")
    _empty_string_list(decision["required_inputs"], "decision required_inputs")
    _validate_evidence(decision["evidence"], reviewed_commit)
    conclusion = _single_line(decision["conclusion"], "decision conclusion")
    if START in conclusion or END in conclusion:
        raise ValueError("decision conclusion contains a reserved verdict marker")


def bank_text(text: str, decision: dict, decision_sha256: str) -> str:
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("third-three verdict markers must occur exactly once")
    text, count = re.subn(r"(?m)^acceleration_third3_ratchet: pending$",
                          "acceleration_third3_ratchet: accepted", text)
    if count != 1:
        raise ValueError("third-three pending frontmatter is absent or already banked")
    verdict = (
        f"{START}\nHard-truth accepted. Run `{decision['run_id']}` reviewed commit "
        f"`{decision['reviewed_commit']}` at {decision['verified_at']}. Conclusion: "
        f"{decision['conclusion']} Decision SHA-256: `{decision_sha256}`.\n{END}")
    return re.sub(re.escape(START) + r".*?" + re.escape(END), verdict, text,
                  count=1, flags=re.DOTALL)


def _run_git(args: tuple[str, ...], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run one read-only Git preflight command and fail closed on any error."""
    command = ("git", *args)
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True,
                                check=False)
    except OSError as exc:
        raise ValueError(
            f"Git preflight command could not run: {' '.join(command)}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or \
            f"exit code {result.returncode}"
        raise ValueError(
            f"Git preflight command failed: {' '.join(command)}: {detail}")
    return result


def verify_banking_git_state(reviewed_commit: str, *, repo_root: Path = ROOT,
                             accepted_parent: str = ACCEPTED_PARENT) -> str:
    """Bind banking to a clean descendant checked out at the reviewed commit."""
    reviewed_commit = _commit(reviewed_commit, "requested reviewed_commit")
    accepted_parent = _commit(accepted_parent, "accepted parent")
    repo_root = repo_root.resolve(strict=True)

    head_result = _run_git(("rev-parse", "--verify", "HEAD^{commit}"), cwd=repo_root)
    head_lines = head_result.stdout.splitlines()
    if head_lines != [reviewed_commit]:
        raise ValueError("banking worktree is not at the reviewed commit")

    _run_git(("merge-base", "--is-ancestor", accepted_parent, reviewed_commit),
             cwd=repo_root)

    status_result = _run_git(
        ("status", "--porcelain=v1", "--untracked-files=normal"), cwd=repo_root)
    if status_result.stdout != "":
        raise ValueError(
            "banking worktree must be clean (including staged, unstaged, and "
            "non-ignored untracked files)")
    return head_lines[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--reviewed-commit", required=True)
    args = parser.parse_args()
    decision_path = args.decision.resolve(strict=True)
    try:
        decision_path.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("hard-truth decision must remain external to repository")
    decision = parse_decision_json(decision_path.read_text(encoding="utf-8"))
    validate_decision(decision, args.reviewed_commit)
    head = verify_banking_git_state(args.reviewed_commit)
    NOTE.write_text(bank_text(NOTE.read_text(encoding="utf-8"), decision,
                              sha256(decision_path)), encoding="utf-8")
    print(f"[phase4-acceleration-third-bank] banked {decision['run_id']} for {head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
