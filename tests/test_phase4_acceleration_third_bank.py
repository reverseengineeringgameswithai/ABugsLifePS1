"""Bank-only guards for acceleration investments 7-9."""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_acceleration_third_bank as bank  # noqa: E402


REVIEWED_COMMIT = "a" * 40
LATE_ROUND_REGRESSIONS = (
    "bank_structured_decision_contract",
    "bank_exact_python_runtime",
    "evidence_round6_complete_strict_types",
    "bank_git_preflight_fail_closed",
    "fuzz_supplied_policy_entrypoints",
    "bank_prior_regression_catalog_complete",
    "warehouse_complete_retained_binding_set",
)


def valid_decision() -> dict:
    artifacts = []
    for path in bank.RETAINED_ARTIFACTS:
        digest = bank.sha256(bank.ROOT / path)
        artifacts.append({
            "path": path,
            "recorded_sha256": digest,
            "recomputed_sha256": digest,
            "byte_exact": True,
        })
    checks = [{
        "id": check_id,
        "command": bank.INTEGRATION_COMMANDS[check_id],
        "exit_code": 0,
        "passed": True,
        "summary": f"{check_id} passed independently",
    } for check_id in bank.INTEGRATION_CHECKS]
    regressions = [{
        "id": regression_id,
        "passed": True,
        "test_nodeids": list(bank.PRIOR_EXPLOIT_TESTS[regression_id]),
    } for regression_id in bank.PRIOR_EXPLOIT_REGRESSIONS]
    suite = {
        "passed": 1242,
        "failed": 78,
        "skipped": 1,
        "failed_nodeids_sha256": "b" * 64,
    }
    return {
        "schema": bank.SCHEMA,
        "run_id": "phase4-acceleration-third3-hard-truth-r4",
        "reviewed_commit": REVIEWED_COMMIT,
        "accepted_parent": bank.ACCEPTED_PARENT,
        "verified_at": "2026-08-01T02:00:00-04:00",
        "verdict": "accepted",
        "gaps": [],
        "required_inputs": [],
        "evidence": {
            "identities_isolation": {
                "candidate_commit": REVIEWED_COMMIT,
                "accepted_parent": bank.ACCEPTED_PARENT,
                "candidate_worktree_clean": True,
                "verification_checkout_detached": True,
                "external_outputs_outside_repository": True,
                "duckstation_untouched": True,
                "redux_untouched": True,
            },
            "environment": {
                "python": "3.14.5",
                "pytest": "9.1.1",
                "pyyaml": "6.0.3",
                "unicorn": "2.1.4",
                "duckdb": "1.5.5",
                "numpy": "2.5.1",
                "requirements_provisioned": True,
            },
            "retained_artifact_reproduction": {
                "artifacts": artifacts,
                "warehouse_query_packs_reproduced": [
                    "first_change", "cohort_contrast", "block_enrichment",
                    "cross_movie",
                ],
                "fuzz_cases_reproduced_twice": 285,
                "external_registry_objects_reproduced": 178,
                "disposable_external_runs_passed": True,
            },
            "focused_integration_checks": checks,
            "prior_exploit_regressions": regressions,
            "candidate_parent_differential": {
                "candidate": {"commit": REVIEWED_COMMIT, **suite},
                "parent": {"commit": bank.ACCEPTED_PARENT, **suite},
                "same_failed_nodeids": True,
                "candidate_only_failures": [],
                "parent_only_failures": [],
            },
        },
        "conclusion": "The bounded third acceleration tranche meets its contract.",
    }


DECISION = valid_decision()


def candidate() -> str:
    return """---
status: accepted
acceleration_ratchet: accepted
acceleration_next3_ratchet: accepted
acceleration_third3_ratchet: pending
---
<!-- PHASE4_ACCELERATION_THIRD3_RATCHET_VERDICT_START -->
Pending independent hard-truth verification.
<!-- PHASE4_ACCELERATION_THIRD3_RATCHET_VERDICT_END -->
Body.
"""


def mutate(path: tuple[object, ...], value: object) -> dict:
    changed = copy.deepcopy(DECISION)
    cursor = changed
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    return changed


def test_valid_decision_has_exact_nonempty_evidence_contract():
    bank.validate_decision(DECISION, REVIEWED_COMMIT)
    assert set(DECISION) == bank.TOP_LEVEL_KEYS
    assert set(DECISION["evidence"]) == bank.EVIDENCE_KEYS


@pytest.mark.parametrize("mutation,match", [
    ({"unexpected": True}, "fields differ"),
    ({"delete": "accepted_parent"}, "fields differ"),
])
def test_top_level_contract_rejects_unknown_and_missing_fields(mutation, match):
    changed = copy.deepcopy(DECISION)
    if "delete" in mutation:
        del changed[mutation["delete"]]
    else:
        changed.update(mutation)
    with pytest.raises(ValueError, match=match):
        bank.validate_decision(changed, REVIEWED_COMMIT)
    with pytest.raises(ValueError, match="JSON object"):
        bank.validate_decision([], REVIEWED_COMMIT)


def test_json_loader_rejects_duplicate_fields_and_nonfinite_numbers():
    with pytest.raises(ValueError, match="duplicate JSON field"):
        bank.parse_decision_json('{"schema": "first", "schema": "second"}')
    with pytest.raises(ValueError, match="non-finite"):
        bank.parse_decision_json('{"value": NaN}')


@pytest.mark.parametrize("path,value", [
    (("schema",), [bank.SCHEMA]),
    (("run_id",), ["run"]),
    (("reviewed_commit",), [REVIEWED_COMMIT]),
    (("accepted_parent",), [bank.ACCEPTED_PARENT]),
    (("verified_at",), ["2026-08-01T02:00:00Z"]),
    (("verdict",), ["accepted"]),
    (("gaps",), {}),
    (("required_inputs",), ""),
    (("evidence",), []),
    (("conclusion",), ["accepted"]),
])
def test_top_level_scalar_and_container_type_drift_is_rejected(path, value):
    with pytest.raises(ValueError):
        bank.validate_decision(mutate(path, value), REVIEWED_COMMIT)


def test_decision_rejects_rejection_nonempty_gaps_and_wrong_candidate():
    with pytest.raises(ValueError, match="accepted"):
        bank.validate_decision(mutate(("verdict",), "rejected"), REVIEWED_COMMIT)
    with pytest.raises(ValueError, match="must be empty"):
        bank.validate_decision(mutate(("required_inputs",), ["receipt"]), REVIEWED_COMMIT)
    with pytest.raises(ValueError, match="differs"):
        bank.validate_decision(DECISION, "c" * 40)
    with pytest.raises(ValueError, match="differ"):
        bank.validate_decision(mutate(("reviewed_commit",), bank.ACCEPTED_PARENT),
                               bank.ACCEPTED_PARENT)


@pytest.mark.parametrize("path,value", [
    (("run_id",), "run with spaces"),
    (("run_id",), "run\nsecond-line"),
    (("conclusion",), "accepted\nextra marker text"),
    (("conclusion",), bank.START),
])
def test_note_authored_decision_strings_cannot_inject_lines_or_markers(path, value):
    with pytest.raises(ValueError):
        bank.validate_decision(mutate(path, value), REVIEWED_COMMIT)


def test_accepted_parent_is_mandatory_exact_and_repeated_in_evidence_and_suite():
    for path in (
            ("accepted_parent",),
            ("evidence", "identities_isolation", "accepted_parent"),
            ("evidence", "candidate_parent_differential", "parent", "commit")):
        with pytest.raises(ValueError, match="parent|required identity"):
            bank.validate_decision(mutate(path, "c" * 40), REVIEWED_COMMIT)


@pytest.mark.parametrize("timestamp", [
    "2026-08-01 02:00:00-04:00",
    "2026-08-01T02:00:00",
    "2026-13-01T02:00:00Z",
    "2026-02-30T02:00:00Z",
    "2026-08-01T25:00:00Z",
    "2026-08-01T02:00:00+24:00",
    "2026-08-01T02:00:00z",
    178,
])
def test_verified_at_must_be_a_real_rfc3339_timestamp(timestamp):
    with pytest.raises(ValueError, match="RFC3339"):
        bank.validate_decision(mutate(("verified_at",), timestamp), REVIEWED_COMMIT)


def test_each_evidence_domain_is_mandatory_exact_and_nonempty():
    for domain in bank.EVIDENCE_KEYS:
        changed = copy.deepcopy(DECISION)
        del changed["evidence"][domain]
        with pytest.raises(ValueError, match="fields differ"):
            bank.validate_decision(changed, REVIEWED_COMMIT)
    changed = copy.deepcopy(DECISION)
    changed["evidence"]["unexpected"] = {}
    with pytest.raises(ValueError, match="fields differ"):
        bank.validate_decision(changed, REVIEWED_COMMIT)
    for domain in bank.EVIDENCE_KEYS:
        with pytest.raises(ValueError):
            bank.validate_decision(mutate(("evidence", domain), {}), REVIEWED_COMMIT)


def test_identity_and_isolation_evidence_is_exact_typed_and_candidate_bound():
    base = ("evidence", "identities_isolation")
    with pytest.raises(ValueError, match="fields differ"):
        changed = copy.deepcopy(DECISION)
        changed["evidence"]["identities_isolation"]["unknown"] = True
        bank.validate_decision(changed, REVIEWED_COMMIT)
    with pytest.raises(ValueError, match="differs"):
        bank.validate_decision(mutate(base + ("candidate_commit",), "c" * 40),
                               REVIEWED_COMMIT)
    for field in (
            "candidate_worktree_clean", "verification_checkout_detached",
            "external_outputs_outside_repository", "duckstation_untouched",
            "redux_untouched"):
        for value in (False, 1, "true"):
            with pytest.raises(ValueError, match="JSON true"):
                bank.validate_decision(mutate(base + (field,), value), REVIEWED_COMMIT)


def test_environment_evidence_is_exact_and_pinned():
    base = ("evidence", "environment")
    for field in ("pytest", "pyyaml", "unicorn", "duckdb", "numpy"):
        with pytest.raises(ValueError, match=field):
            bank.validate_decision(mutate(base + (field,), "0.0.0"), REVIEWED_COMMIT)
    for python in (
            "0.0.0", "3.13.0", "3.14.4", "3.14.6", "999.999.999",
            "3.14", "3.14.5-dev", 3145):
        with pytest.raises(ValueError, match="python"):
            bank.validate_decision(mutate(base + ("python",), python), REVIEWED_COMMIT)
    for value in (False, 1, "true"):
        with pytest.raises(ValueError, match="requirements_provisioned"):
            bank.validate_decision(
                mutate(base + ("requirements_provisioned",), value), REVIEWED_COMMIT)
    changed = copy.deepcopy(DECISION)
    changed["evidence"]["environment"]["extra"] = "drift"
    with pytest.raises(ValueError, match="fields differ"):
        bank.validate_decision(changed, REVIEWED_COMMIT)


def test_retained_reproduction_binds_exact_artifacts_hashes_and_counts():
    base = ("evidence", "retained_artifact_reproduction")
    artifacts = base + ("artifacts",)
    with pytest.raises(ValueError, match="order/path"):
        bank.validate_decision(mutate(artifacts + (0, "path"), bank.RETAINED_ARTIFACTS[1]),
                               REVIEWED_COMMIT)
    for field in ("recorded_sha256", "recomputed_sha256"):
        with pytest.raises(ValueError, match="SHA-256"):
            bank.validate_decision(mutate(artifacts + (0, field), "c" * 64),
                                   REVIEWED_COMMIT)
    for value in (False, 1, "true"):
        with pytest.raises(ValueError, match="byte_exact"):
            bank.validate_decision(mutate(artifacts + (0, "byte_exact"), value),
                                   REVIEWED_COMMIT)
    with pytest.raises(ValueError, match="four-pack"):
        bank.validate_decision(mutate(base + ("warehouse_query_packs_reproduced",),
                                      ["first_change"]), REVIEWED_COMMIT)
    for path, value in (
            (base + ("fuzz_cases_reproduced_twice",), 284),
            (base + ("fuzz_cases_reproduced_twice",), True),
            (base + ("external_registry_objects_reproduced",), 177),
            (base + ("external_registry_objects_reproduced",), True),
            (base + ("disposable_external_runs_passed",), False)):
        with pytest.raises(ValueError):
            bank.validate_decision(mutate(path, value), REVIEWED_COMMIT)
    changed = copy.deepcopy(DECISION)
    changed["evidence"]["retained_artifact_reproduction"]["artifacts"][0]["extra"] = 1
    with pytest.raises(ValueError, match="fields differ"):
        bank.validate_decision(changed, REVIEWED_COMMIT)


def test_focused_integration_checks_require_exact_order_success_and_evidence():
    checks = ("evidence", "focused_integration_checks")
    with pytest.raises(ValueError, match="exact check set"):
        bank.validate_decision(mutate(checks, DECISION["evidence"][
            "focused_integration_checks"][:-1]), REVIEWED_COMMIT)
    for field, value in (
            ("id", "invented"), ("command", ""), ("exit_code", 1),
            ("exit_code", False), ("passed", False), ("passed", 1),
            ("summary", "")):
        with pytest.raises(ValueError):
            bank.validate_decision(mutate(checks + (0, field), value), REVIEWED_COMMIT)
    changed = copy.deepcopy(DECISION)
    changed["evidence"]["focused_integration_checks"][0]["unknown"] = True
    with pytest.raises(ValueError, match="fields differ"):
        bank.validate_decision(changed, REVIEWED_COMMIT)


def test_prior_exploit_regressions_require_every_exact_passing_test_binding():
    regressions = ("evidence", "prior_exploit_regressions")
    with pytest.raises(ValueError, match="exact exploit set"):
        bank.validate_decision(mutate(regressions, DECISION["evidence"][
            "prior_exploit_regressions"][:-1]), REVIEWED_COMMIT)
    for field, value in (
            ("id", "invented"), ("passed", False), ("passed", 1),
            ("test_nodeids", []), ("test_nodeids", [""]),
            ("test_nodeids", ["one", "one"])):
        with pytest.raises(ValueError):
            bank.validate_decision(mutate(regressions + (0, field), value),
                                   REVIEWED_COMMIT)
    changed = copy.deepcopy(DECISION)
    changed["evidence"]["prior_exploit_regressions"][0]["unknown"] = True
    with pytest.raises(ValueError, match="fields differ"):
        bank.validate_decision(changed, REVIEWED_COMMIT)


def test_prior_exploit_catalog_is_ordered_nonempty_and_has_unique_nodeids():
    assert tuple(bank.PRIOR_EXPLOIT_TESTS) == bank.PRIOR_EXPLOIT_REGRESSIONS
    assert bank.PRIOR_EXPLOIT_REGRESSIONS[-len(
        LATE_ROUND_REGRESSIONS):] == LATE_ROUND_REGRESSIONS
    nodeids = []
    for regression_id in bank.PRIOR_EXPLOIT_REGRESSIONS:
        bound = bank.PRIOR_EXPLOIT_TESTS[regression_id]
        assert type(bound) is tuple and bound
        assert all(type(nodeid) is str and nodeid for nodeid in bound)
        nodeids.extend(bound)
    assert len(nodeids) == len(set(nodeids))


@pytest.mark.parametrize("regression_id", LATE_ROUND_REGRESSIONS)
def test_each_late_round_regression_group_is_mandatory(regression_id):
    changed = valid_decision()
    rows = changed["evidence"]["prior_exploit_regressions"]
    rows.pop(bank.PRIOR_EXPLOIT_REGRESSIONS.index(regression_id))
    with pytest.raises(ValueError, match="exact exploit set"):
        bank.validate_decision(changed, REVIEWED_COMMIT)


@pytest.mark.parametrize("mutation", ["omit", "alter"])
@pytest.mark.parametrize("regression_id", LATE_ROUND_REGRESSIONS)
def test_each_late_round_nodeid_list_is_exact(regression_id, mutation):
    changed = valid_decision()
    index = bank.PRIOR_EXPLOIT_REGRESSIONS.index(regression_id)
    nodeids = changed["evidence"]["prior_exploit_regressions"][
        index]["test_nodeids"]
    if mutation == "omit":
        nodeids.pop()
    else:
        nodeids[0] += "_altered"
    with pytest.raises(ValueError, match="exact adversarial test node IDs"):
        bank.validate_decision(changed, REVIEWED_COMMIT)


def test_candidate_parent_differential_rejects_parentless_and_type_drifted_claims():
    differential = ("evidence", "candidate_parent_differential")
    for field, value in (
            ("same_failed_nodeids", False), ("same_failed_nodeids", 1),
            ("candidate_only_failures", ["candidate::failure"]),
            ("parent_only_failures", ["parent::failure"])):
        with pytest.raises(ValueError):
            bank.validate_decision(mutate(differential + (field,), value),
                                   REVIEWED_COMMIT)
    for suite in ("candidate", "parent"):
        for field, value in (
                ("passed", True), ("failed", False), ("skipped", "1"),
                ("failed_nodeids_sha256", "not-a-hash")):
            with pytest.raises(ValueError):
                bank.validate_decision(mutate(differential + (suite, field), value),
                                       REVIEWED_COMMIT)
    with pytest.raises(ValueError, match="failed counts differ"):
        bank.validate_decision(mutate(differential + ("candidate", "failed"), 77),
                               REVIEWED_COMMIT)
    with pytest.raises(ValueError, match="failed node IDs differ"):
        bank.validate_decision(mutate(differential + (
            "candidate", "failed_nodeids_sha256"), "c" * 64), REVIEWED_COMMIT)
    changed = copy.deepcopy(DECISION)
    del changed["evidence"]["candidate_parent_differential"]["parent"]
    with pytest.raises(ValueError, match="fields differ"):
        bank.validate_decision(changed, REVIEWED_COMMIT)
    changed = copy.deepcopy(DECISION)
    changed["evidence"]["candidate_parent_differential"]["candidate"]["unknown"] = 0
    with pytest.raises(ValueError, match="fields differ"):
        bank.validate_decision(changed, REVIEWED_COMMIT)


def test_bank_changes_only_third_ratchet_and_marker():
    result = bank.bank_text(candidate(), DECISION, "b" * 64)
    assert "acceleration_ratchet: accepted" in result
    assert "acceleration_next3_ratchet: accepted" in result
    assert "acceleration_third3_ratchet: accepted" in result
    assert DECISION["run_id"] in result and "b" * 64 in result
    assert result.endswith("Body.\n")


def test_bank_rejects_repeat():
    banked = bank.bank_text(candidate(), DECISION, "b" * 64)
    with pytest.raises(ValueError, match="already banked"):
        bank.bank_text(banked, DECISION, "b" * 64)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(("git", *args), cwd=repo, text=True,
                          capture_output=True, check=True).stdout.strip()


def disposable_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "bank-preflight"
    repo.mkdir()
    git(repo, "init", "--quiet")
    git(repo, "config", "user.name", "Bank Preflight Test")
    git(repo, "config", "user.email", "bank-preflight@example.invalid")
    (repo / "tracked.txt").write_text("parent\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "--quiet", "-m", "accepted parent")
    parent = git(repo, "rev-parse", "HEAD")
    (repo / "tracked.txt").write_text("reviewed\n", encoding="utf-8")
    git(repo, "commit", "--quiet", "-am", "reviewed candidate")
    reviewed = git(repo, "rev-parse", "HEAD")
    return repo, parent, reviewed


def test_git_preflight_accepts_clean_descendant_in_disposable_repository(tmp_path):
    repo, parent, reviewed = disposable_repository(tmp_path)
    assert bank.verify_banking_git_state(
        reviewed, repo_root=repo, accepted_parent=parent) == reviewed


def test_git_preflight_rejects_dirty_tracked_file(tmp_path):
    repo, parent, reviewed = disposable_repository(tmp_path)
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be clean"):
        bank.verify_banking_git_state(
            reviewed, repo_root=repo, accepted_parent=parent)


def test_git_preflight_rejects_staged_change(tmp_path):
    repo, parent, reviewed = disposable_repository(tmp_path)
    (repo / "tracked.txt").write_text("staged\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    with pytest.raises(ValueError, match="must be clean"):
        bank.verify_banking_git_state(
            reviewed, repo_root=repo, accepted_parent=parent)


def test_git_preflight_rejects_nonignored_untracked_file(tmp_path):
    repo, parent, reviewed = disposable_repository(tmp_path)
    (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be clean"):
        bank.verify_banking_git_state(
            reviewed, repo_root=repo, accepted_parent=parent)


def test_git_preflight_allows_ignored_external_support(tmp_path):
    repo, parent, _ = disposable_repository(tmp_path)
    (repo / ".gitignore").write_text("external-support/\n", encoding="utf-8")
    git(repo, "add", ".gitignore")
    git(repo, "commit", "--quiet", "-m", "declare ignored support")
    reviewed = git(repo, "rev-parse", "HEAD")
    support = repo / "external-support"
    support.mkdir()
    (support / "receipt.json").write_text("{}\n", encoding="utf-8")
    assert bank.verify_banking_git_state(
        reviewed, repo_root=repo, accepted_parent=parent) == reviewed


def test_git_preflight_rejects_unrelated_history(tmp_path):
    repo, _, reviewed = disposable_repository(tmp_path)
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    unrelated_parent = subprocess.run(
        ("git", "commit-tree", tree), cwd=repo, input="unrelated root\n", text=True,
        capture_output=True, check=True).stdout.strip()
    with pytest.raises(ValueError, match="Git preflight command failed"):
        bank.verify_banking_git_state(
            reviewed, repo_root=repo, accepted_parent=unrelated_parent)


def test_git_preflight_rejects_wrong_head(tmp_path):
    repo, parent, reviewed = disposable_repository(tmp_path)
    git(repo, "checkout", "--quiet", "--detach", parent)
    with pytest.raises(ValueError, match="not at the reviewed commit"):
        bank.verify_banking_git_state(
            reviewed, repo_root=repo, accepted_parent=parent)


def test_git_preflight_fails_closed_when_git_command_fails(tmp_path):
    repo, parent, reviewed = disposable_repository(tmp_path)
    (repo / ".git" / "HEAD").write_text("invalid HEAD\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Git preflight command failed"):
        bank.verify_banking_git_state(
            reviewed, repo_root=repo, accepted_parent=parent)
