"""Bank-only guards for acceleration investments 4-6."""
from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_acceleration_next_bank as bank  # noqa: E402


DECISION = {
    "schema": bank.SCHEMA,
    "run_id": "test-next3",
    "reviewed_commit": "a" * 40,
    "verified_at": "2026-07-31T23:00:00-04:00",
    "verdict": "accepted",
    "gaps": [],
    "required_inputs": [],
    "conclusion": "The bounded next-three acceleration tranche meets its contract.",
}


def candidate() -> str:
    return """---
status: accepted
acceleration_ratchet: accepted
acceleration_next3_ratchet: pending
---
<!-- PHASE4_ACCELERATION_NEXT3_RATCHET_VERDICT_START -->
Pending independent hard-truth verification.
<!-- PHASE4_ACCELERATION_NEXT3_RATCHET_VERDICT_END -->
Body.
"""


def test_bank_changes_only_next_ratchet_and_marker():
    result = bank.bank_text(candidate(), DECISION, "b" * 64)
    assert "status: accepted" in result
    assert "acceleration_ratchet: accepted" in result
    assert "acceleration_next3_ratchet: accepted" in result
    assert "test-next3" in result and "b" * 64 in result
    assert result.endswith("Body.\n")


def test_bank_rejects_rejection_gaps_wrong_commit_and_repeat():
    changed = copy.deepcopy(DECISION)
    changed["verdict"] = "rejected"
    with pytest.raises(ValueError, match="accepted"):
        bank.validate_decision(changed, "a" * 40)
    changed = copy.deepcopy(DECISION)
    changed["gaps"] = ["gap"]
    with pytest.raises(ValueError, match="empty"):
        bank.validate_decision(changed, "a" * 40)
    with pytest.raises(ValueError, match="differs"):
        bank.validate_decision(DECISION, "c" * 40)
    banked = bank.bank_text(candidate(), DECISION, "b" * 64)
    with pytest.raises(ValueError, match="already banked"):
        bank.bank_text(banked, DECISION, "b" * 64)
