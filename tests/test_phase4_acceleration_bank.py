"""Deterministic bank-only guards for the acceleration hard-truth marker."""

import copy
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_acceleration_bank as bank  # noqa: E402


DECISION = {
    "schema": "abl-phase4-acceleration-hard-truth-decision/1",
    "run_id": "test-run",
    "reviewed_commit": "a" * 40,
    "verified_at": "2026-07-31T12:00:00-04:00",
    "verdict": "accepted",
    "gaps": [],
    "required_inputs": [],
    "conclusion": "The bounded tooling tranche meets its contract.",
}


def candidate_text() -> str:
    return """---
status: candidate
acceleration_ratchet: pending
---
<!-- PHASE4_ACCELERATION_RATCHET_VERDICT_START -->
Pending independent hard-truth verification.
<!-- PHASE4_ACCELERATION_RATCHET_VERDICT_END -->
Body remains byte-identical.
"""


def test_bank_changes_only_frontmatter_and_verdict_marker():
    result = bank.bank_text(candidate_text(), DECISION, "b" * 64)
    assert "status: accepted" in result
    assert "acceleration_ratchet: accepted" in result
    assert "`test-run`" in result and "`" + "a" * 40 + "`" in result
    assert "`" + "b" * 64 + "`" in result
    assert result.endswith("Body remains byte-identical.\n")


def test_bank_rejects_nonaccepted_or_gapped_decisions():
    rejected = copy.deepcopy(DECISION)
    rejected["verdict"] = "rejected"
    with pytest.raises(ValueError, match="accepted"):
        bank.validate_decision(rejected, "a" * 40)
    gapped = copy.deepcopy(DECISION)
    gapped["gaps"] = ["not done"]
    with pytest.raises(ValueError, match="empty gaps"):
        bank.validate_decision(gapped, "a" * 40)


def test_bank_rejects_wrong_commit_and_repeat_application():
    with pytest.raises(ValueError, match="differs"):
        bank.validate_decision(DECISION, "c" * 40)
    banked = bank.bank_text(candidate_text(), DECISION, "b" * 64)
    with pytest.raises(ValueError, match="already banked"):
        bank.bank_text(banked, DECISION, "b" * 64)
