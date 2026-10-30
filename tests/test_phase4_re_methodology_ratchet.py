import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "phase4_re_methodology_ratchet.sh"
CONTRACT = ROOT / "engineering-specs" / "phase4-re-methodology-ratchet.md"
BANKER = ROOT / "tools" / "phase4_re_methodology_bank.py"


def test_shell_syntax_and_two_step_roles():
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
    source = SCRIPT.read_text(encoding="utf-8")
    assert "STEP 1 IMPLEMENTER ADVISORY" in source
    assert "STEP 2 HARD-TRUTH VERIFIER" in source
    assert "worktree add --detach" in source
    assert source.index("STEP 1 IMPLEMENTER ADVISORY") < source.index(
        "STEP 2 HARD-TRUTH VERIFIER"
    )


def test_contract_keeps_phase4_and_pristine_authority_intact():
    text = " ".join(CONTRACT.read_text(encoding="utf-8").split())
    required = (
        "hash-verified pristine retail image",
        "107-row",
        "src_re",
        "DuckStation external-debugger fork",
        "trace-capsule",
        "matching or documentation-grade",
        "clean-checkout",
        "does not close Phase 4",
    )
    for fragment in required:
        assert fragment in text


def test_prompts_force_current_duckstation_and_machine_layer_review():
    source = " ".join(SCRIPT.read_text(encoding="utf-8").split())
    for fragment in (
        "current DuckStation API documentation and C++ source",
        "representative relevant src_re C, ASM/symbols, typed schemas",
        "retained run history",
        "capsules/offline mathematics",
        "Do not launch DuckStation or replay movies",
        "best-supported efficient operating method",
    ):
        assert fragment in source


def test_only_method_note_and_reciprocal_link_are_advisory_writable():
    raw_source = SCRIPT.read_text(encoding="utf-8")
    source = " ".join(raw_source.split())
    assert '[[ "$path" == "$METHOD_REL" || "$path" == "$PHASE4_REL" ]]' in raw_source
    assert "may not close rows" in source
    assert "Do not edit Phase 4 implementation" in source
    assert '[[ "$bank_changed" == "$METHOD_REL" ]]' in source


def test_acceptance_requires_clean_independent_verifier():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "verifier_head" in source
    assert "verifier_status_tree" in source
    assert "accepted cannot carry gaps or required_input" in source
    assert "hard-truth verifier rejected" in source
    assert "vault validation failed after banking" in source
    assert "No merge was performed" in source


def test_openai_response_schema_types_fixed_role_and_status():
    source = SCRIPT.read_text(encoding="utf-8")
    assert (
        '"role": {"type": "string", "enum": ["implementer_advisory"]}' in source
    )
    assert (
        '"role": {"type": "string", "enum": ["hard_truth_verifier"]}' in source
    )
    assert '"status": {' in source
    assert '"type": "string"' in source


def test_banker_accepts_only_gap_free_verified_decision(tmp_path: Path):
    note = tmp_path / "method.md"
    note.write_text(
        """---
status: candidate
methodology_ratchet: pending
---

# Method

<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_START -->
Pending independent verification.
<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_END -->
""",
        encoding="utf-8",
    )
    verdict = tmp_path / "verdict.json"
    verdict.write_text(
        json.dumps(
            {
                "role": "hard_truth_verifier",
                "status": "accepted",
                "summary": "The current evidence supports the selected hybrid.",
                "gaps": [],
                "evidence": ["Inspected the queue and API source."],
                "validation": ["Fresh checkout remained clean."],
                "required_input": "",
                "reviewed_commit": "a" * 40,
                "note_path": "ObsidianVault/example.md",
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "python3",
            str(BANKER),
            "--note",
            str(note),
            "--verdict",
            str(verdict),
            "--run-id",
            "test-run",
            "--verified-at",
            "2026-07-25T00:00:00-04:00",
        ],
        check=True,
    )
    banked = note.read_text(encoding="utf-8")
    assert "status: accepted" in banked
    assert "methodology_ratchet: verified" in banked
    assert "Independent hard-truth acceptance" in banked
    assert "does not close Phase 4" in banked


@pytest.mark.parametrize(
    "status,gaps,required_input",
    [
        ("rejected", ["not best supported"], ""),
        ("accepted", ["hidden gap"], ""),
        ("accepted", [], "record a movie"),
    ],
)
def test_banker_rejects_non_acceptable_verdicts(
    tmp_path: Path, status: str, gaps: list[str], required_input: str
):
    note = tmp_path / "method.md"
    note.write_text(
        """status: candidate
methodology_ratchet: pending
<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_START -->
Pending independent verification.
<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_END -->
""",
        encoding="utf-8",
    )
    verdict = tmp_path / "verdict.json"
    verdict.write_text(
        json.dumps(
            {
                "role": "hard_truth_verifier",
                "status": status,
                "summary": "No.",
                "gaps": gaps,
                "evidence": [],
                "validation": [],
                "required_input": required_input,
                "reviewed_commit": "b" * 40,
                "note_path": "ObsidianVault/example.md",
            }
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            "python3",
            str(BANKER),
            "--note",
            str(note),
            "--verdict",
            str(verdict),
            "--run-id",
            "test-run",
            "--verified-at",
            "2026-07-25T00:00:00-04:00",
        ],
        text=True,
        capture_output=True,
    )
    assert completed.returncode != 0
    assert "status: candidate" in note.read_text(encoding="utf-8")
