"""Consistency ratchet for the ObsidianVault (RCA campaign).

Runs the vault linter (tools/validate_vault.py) against the committed vault and
asserts every finding count is at or below the ceilings in
tests/vault_lint_baseline.json. Counts may only ever go DOWN: as the RCA phases
remediate, the baseline is lowered, so a regression (a re-introduced dangling
link, an evidence-policy violation, a duplicate note) fails CI.

CI-safe: pure read of committed markdown, no emulator/GPU/media.
"""
import json
from pathlib import Path

import pytest

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate_vault  # noqa: E402

BASELINE = json.loads((ROOT / "tests" / "vault_lint_baseline.json").read_text())["max"]

_findings, _counts = validate_vault.audit()


@pytest.mark.parametrize("category", sorted(BASELINE))
def test_no_regression(category):
    ceiling = BASELINE[category]
    actual = _counts[category]
    assert actual <= ceiling, (
        f"vault-lint regression in {category}: {actual} > baseline {ceiling}. "
        f"Run `python tools/validate_vault.py --json` to see the offending notes. "
        f"If this is intentional cleanup, LOWER the ceiling in vault_lint_baseline.json."
    )


def test_baseline_has_all_categories():
    for c in ("dangling_links", "archive_only", "evidence_policy",
              "evidence_deadfile", "dup_address", "missing_alias", "schema"):
        assert c in BASELINE, f"baseline missing category {c}"


def test_linter_runs_clean():
    # audit() must not raise and must return a count for every category
    assert set(_counts) >= set(validate_vault.CATEGORIES)
