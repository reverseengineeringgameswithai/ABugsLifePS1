"""Phase-3 knowledge-closure guard (the roadmap's Definition of Finished).

A finding is not finished because it was demonstrated — it must be banked so a
later agent or mod can locate, verify and consume it without repeating the work.
This test runs the audit and requires it to hold, and (crucially) proves the
audit can FAIL: an artifact that cannot fail is exactly the self-grading trap
Phase 2 was reopened for twice."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "analysis" / "phase3_knowledge_audit.json"
FINDINGS = ROOT / "config" / "phase3_findings.yaml"
sys.path.insert(0, str(ROOT / "tools"))
import phase3_knowledge_audit as knowledge  # noqa: E402


def run_audit():
    return subprocess.run([sys.executable, "tools/phase3_knowledge_audit.py"],
                          cwd=ROOT, capture_output=True, text=True)


def test_every_finding_is_finished():
    proc = run_audit()
    doc = json.loads(AUDIT.read_text())
    assert proc.returncode == 0, doc["rows"]
    assert doc["open_gaps"] == 0
    assert doc["finished"] == doc["findings"] >= 7
    assert doc["debugger_api_documentation_gaps"] == []


def test_every_finding_declares_a_mod_contract_with_an_unsafe_assumption():
    """'An address without its ownership and lifecycle is not a safe extension
    point' — so every finding must tell a mod what it may NOT assume."""
    doc = yaml.safe_load(FINDINGS.read_text())
    for f in doc["findings"]:
        c = (f.get("mod_contract") or "").strip()
        assert len(c) > 80, f["id"]
        assert any(w in c for w in ("UNSAFE", "must NOT", "NOWHERE", "HANGS",
                                    "does NOT")), f["id"]
        assert (f.get("residuals") or "").strip(), f["id"]


def test_original_findings_cannot_use_experiment_notes_as_canon():
    doc = yaml.safe_load(FINDINGS.read_text())
    for finding in doc["findings"]:
        assert finding["canon"].startswith("ObsidianVault/Canon/"), finding["id"]
    damaged = dict(doc["findings"][0])
    damaged["canon"] = (
        "ObsidianVault/Experiments/Runtime Tests/"
        "EXP_2026-07-13_a07_spin_move_disproof.md"
    )
    assert any("not placed in ObsidianVault/Canon" in gap
               for gap in knowledge.audit_one(damaged))


def test_corrections_record_what_they_supersede():
    """When a claim is corrected, the old one must be listed as superseded so a
    future agent does not revive it."""
    doc = json.loads(AUDIT.read_text())
    sup = " ".join(doc["superseded_claims"])
    for dead in ("knockback_velocity", "active_type", "non-zero bytes",
                 "velocity_y"):
        assert dead in sup, dead


def test_the_audit_can_actually_fail():
    """Falsification: point a finding at a guard test that does not exist. If the
    audit still passes, it is decoration, not a check."""
    backup = FINDINGS.read_text()
    try:
        FINDINGS.write_text(backup.replace(
            "guard: tests/test_phase3_records.py::test_velocity_fields_and_ttl_are_typed",
            "guard: tests/test_phase3_records.py::test_nonexistent_guard", 1))
        proc = run_audit()
        assert proc.returncode == 1, "audit passed with a phantom guard"
        doc = json.loads(AUDIT.read_text())
        assert doc["open_gaps"] >= 1
    finally:
        FINDINGS.write_text(backup)
        run_audit()          # restore the committed artifact
