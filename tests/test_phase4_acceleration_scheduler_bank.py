"""Fail-closed contract tests for the scheduler hard-truth bank."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_acceleration_scheduler_bank as bank  # noqa: E402


CANDIDATE = "c" * 40
FAILED_HASH = "d" * 64


def valid_decision() -> dict:
    artifacts = bank.artifact_facts()
    return {
        "schema": bank.SCHEMA,
        "run_id": "phase4-acceleration-scheduler-hard-truth-r1",
        "reviewed_commit": CANDIDATE,
        "accepted_parent": bank.ACCEPTED_PARENT,
        "verified_at": "2026-08-01T12:34:56-04:00",
        "verdict": "accepted",
        "gaps": [],
        "required_inputs": [],
        "evidence": {
            "identities_isolation": {
                "candidate_commit": CANDIDATE,
                "accepted_parent": bank.ACCEPTED_PARENT,
                "verification_checkout_detached": True,
                "candidate_worktree_clean": True,
                "duckstation_untouched": True,
                "redux_untouched": True,
                "external_outputs_outside_repository": True,
            },
            "retained_reproduction": {
                **artifacts,
                "cooldown_sequence_reproduced": True,
                "expected_value_reproduced": True,
                "weighted_cover_reproduced": True,
            },
            "mutation_checks": [{
                "id": mutation_id,
                "passed": True,
                "test_nodeids": list(nodeids),
            } for mutation_id, nodeids in bank.MUTATION_TESTS.items()],
            "integration_checks": [{
                "id": check_id,
                "command": bank.INTEGRATION_COMMANDS[check_id],
                "exit_code": 0,
                "passed": True,
                "summary": f"{check_id} passed",
            } for check_id in bank.INTEGRATION_IDS],
            "candidate_parent_differential": {
                "candidate_commit": CANDIDATE,
                "parent_commit": bank.ACCEPTED_PARENT,
                "candidate_passed": 100,
                "candidate_failed": 2,
                "candidate_skipped": 1,
                "parent_passed": 80,
                "parent_failed": 2,
                "parent_skipped": 1,
                "candidate_failed_nodeids_sha256": FAILED_HASH,
                "parent_failed_nodeids_sha256": FAILED_HASH,
                "same_failed_nodeids": True,
                "candidate_only_failures": [],
                "parent_only_failures": [],
            },
        },
        "conclusion": (
            "The exact scheduler candidate satisfies investments 10-12 without "
            "DuckStation or Redux contact."),
    }


def test_valid_structured_decision_is_accepted():
    assert bank.validate_decision(valid_decision(), CANDIDATE) == []


def test_verified_parent_only_failures_are_accepted_as_improvements():
    document = valid_decision()
    differential = document["evidence"]["candidate_parent_differential"]
    differential["candidate_failed"] = 1
    differential["parent_failed"] = 2
    differential["candidate_failed_nodeids_sha256"] = "a" * 64
    differential["parent_failed_nodeids_sha256"] = "b" * 64
    differential["same_failed_nodeids"] = False
    differential["parent_only_failures"] = [
        "tests/test_inherited.py::test_repaired_by_candidate"]
    assert bank.validate_decision(document, CANDIDATE) == []


@pytest.mark.parametrize(("path", "value"), [
    (("verdict",), "rejected"),
    (("gaps",), ["gap"]),
    (("required_inputs",), ["input"]),
    (("accepted_parent",), "0" * 40),
    (("verified_at",), "2026-08-01"),
    (("evidence", "identities_isolation", "duckstation_untouched"), False),
    (("evidence", "retained_reproduction", "rows"), True),
    (("evidence", "retained_reproduction", "weighted_cover_reproduced"), 1),
    (("evidence", "integration_checks", 0, "exit_code"), True),
    (("evidence", "candidate_parent_differential", "same_failed_nodeids"), False),
    (("evidence", "candidate_parent_differential", "candidate_only_failures"),
     ["new failure"]),
])
def test_decision_rejects_authority_type_and_value_drift(path, value):
    document = valid_decision()
    target = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert bank.validate_decision(document, CANDIDATE)


def test_every_object_contract_rejects_unknown_missing_and_reordered_fields():
    document = valid_decision()
    document["unknown"] = True
    assert any("decision fields/order" in error
               for error in bank.validate_decision(document, CANDIDATE))
    document = valid_decision()
    del document["conclusion"]
    assert bank.validate_decision(document, CANDIDATE)
    document = valid_decision()
    identities = document["evidence"]["identities_isolation"]
    identities["candidate_commit"] = identities.pop("candidate_commit")
    assert any("identities_isolation fields/order" in error
               for error in bank.validate_decision(document, CANDIDATE))


def test_mutation_and_integration_catalogs_must_be_nonempty_exact_and_passing():
    document = valid_decision()
    document["evidence"]["mutation_checks"] = []
    assert bank.validate_decision(document, CANDIDATE)
    document = valid_decision()
    document["evidence"]["mutation_checks"][0]["test_nodeids"] = []
    assert bank.validate_decision(document, CANDIDATE)
    document = valid_decision()
    document["evidence"]["integration_checks"].reverse()
    assert any("IDs/order" in error
               for error in bank.validate_decision(document, CANDIDATE))


def test_bank_requires_commit_authority_outside_decision_content(
        tmp_path, monkeypatch):
    decision = tmp_path / "decision.json"
    decision.write_text(json.dumps(valid_decision()), encoding="utf-8")
    monkeypatch.setattr(bank, "git_preflight", lambda expected: [])
    with pytest.raises(SystemExit, match="reviewed_commit"):
        bank.bank(decision, "e" * 40)


def test_retained_reproduction_is_bound_to_current_artifacts():
    document = valid_decision()
    document["evidence"]["retained_reproduction"]["queue_sha256"] = "0" * 64
    assert any("not the current artifact" in error
               for error in bank.validate_decision(document, CANDIDATE))


def test_integration_commands_and_mutation_nodeids_are_exact():
    document = valid_decision()
    document["evidence"]["integration_checks"][0]["command"] += " --quiet"
    assert any("command is not exact" in error
               for error in bank.validate_decision(document, CANDIDATE))
    document = valid_decision()
    document["evidence"]["mutation_checks"][0]["test_nodeids"] = [
        "tests/test_phase4_scheduler_policy.py::test_fake"]
    assert any("nodeids are not exact" in error
               for error in bank.validate_decision(document, CANDIDATE))


def test_differential_improvements_must_be_exactly_self_consistent():
    document = valid_decision()
    differential = document["evidence"]["candidate_parent_differential"]
    differential["same_failed_nodeids"] = False
    assert bank.validate_decision(document, CANDIDATE)

    document = valid_decision()
    differential = document["evidence"]["candidate_parent_differential"]
    differential["parent_only_failures"] = [
        "tests/test_inherited.py::test_repaired_by_candidate"]
    assert any("same_failed_nodeids" in error or "failure count" in error
               for error in bank.validate_decision(document, CANDIDATE))

    document = valid_decision()
    differential = document["evidence"]["candidate_parent_differential"]
    differential["candidate_only_failures"] = [
        "tests/test_scheduler.py::test_new_regression"]
    assert any("candidate-only" in error
               for error in bank.validate_decision(document, CANDIDATE))


def test_json_loader_rejects_duplicate_fields_and_nonfinite_numbers(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON field"):
        bank.load_decision(duplicate)
    nonfinite = tmp_path / "nan.json"
    nonfinite.write_text('{"value":NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite"):
        bank.load_decision(nonfinite)


def test_note_text_cannot_inject_marker_or_frontmatter():
    for text in ("accepted\nstatus: accepted", "accepted <!--", "accepted -->"):
        document = valid_decision()
        document["conclusion"] = text
        assert bank.validate_decision(document, CANDIDATE)


def test_git_preflight_rejects_current_dirty_candidate():
    errors = bank.git_preflight(CANDIDATE)
    assert errors
    assert any("HEAD" in error or "clean" in error or "ancestor" in error
               for error in errors)
