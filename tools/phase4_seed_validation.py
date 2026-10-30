#!/usr/bin/env python3
"""Capture and replay the fixed semantic checks for a repaired Phase-4 seed."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


SCHEMA = "abl-phase4-seed-validation/1"
CHECKS = (
    ("pristine_identity",
     ("python3", "-B", "tools/build_identity.py", "--verify")),
    ("phase3_gate",
     ("python3", "-B", "tools/phase3_gate_audit.py")),
    ("phase3_phase4_guards", (
        "python3", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "tests/test_phase3_duckstation_rpc_manifest.py",
        "tests/test_phase3_evidence_inventory.py",
        "tests/test_phase3_runtime_guards.py",
        "tests/test_phase3_gate.py",
        "tests/test_phase4_gate.py",
    )),
    ("vault", ("python3", "-B", "tools/validate_vault.py", "--check")),
)


def canonical_output(value: str) -> str:
    value = re.sub(r"\bin \d+(?:\.\d+)?s\b", "in <TIME>s", value)
    value = re.sub(r"\(\d+:\d+(?::\d+)?\)", "(<TIME>)", value)
    return value


def command_for(spec: tuple[str, ...]) -> list[str]:
    command = list(spec)
    if command[0] == "python3":
        command[0] = sys.executable
    return command


def semantic_ok(check_id: str, output: str, exit_code: int) -> bool:
    if exit_code != 0 or "Traceback (most recent call last)" in output:
        return False
    lower = output.lower()
    if re.search(r"\b(?:failed|error)s?\b", lower):
        return False
    if check_id == "pristine_identity":
        return "[build_identity] PASS: 327/327" in output
    if check_id == "phase3_gate":
        return "[gate] Phase-3 exit gate: MET" in output
    if check_id == "phase3_phase4_guards":
        return re.search(r"(?m)\b\d+ passed\b", output) is not None
    if check_id == "vault":
        return all(
            re.search(rf"(?m)^\s*{name}\s+0\s*$", output)
            for name in (
                "dangling_links", "evidence_policy", "evidence_deadfile",
                "dup_address", "missing_alias", "schema",
            )
        )
    return False


def run_check(root: Path, check_id: str, spec: tuple[str, ...]) -> dict:
    command = command_for(spec)
    proc = subprocess.run(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=600,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(root),
        },
    )
    canonical = canonical_output(proc.stdout)
    return {
        "id": check_id,
        "command": command,
        "exit_code": proc.returncode,
        "output": proc.stdout,
        "canonical_output_sha256": hashlib.sha256(
            canonical.encode("utf-8")).hexdigest(),
        "semantic_ok": semantic_ok(check_id, proc.stdout, proc.returncode),
    }


def capture(root: Path, candidate: str) -> dict:
    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    before = subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain=v1",
         "--untracked-files=all"], text=True)
    rows = [run_check(root, check_id, spec) for check_id, spec in CHECKS]
    after = subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain=v1",
         "--untracked-files=all"], text=True)
    errors = []
    if head != candidate:
        errors.append("tested checkout is not at the candidate commit")
    if before:
        errors.append("tested checkout was dirty before validation")
    if after != before:
        errors.append("validation changed the tested checkout")
    if not all(row["semantic_ok"] for row in rows):
        errors.append("one or more fixed semantic checks failed")
    return {
        "schema": SCHEMA,
        "candidate_commit": candidate,
        "checks": rows,
        "complete": not errors,
        "errors": errors,
    }


def validate_and_replay(path: Path, root: Path, candidate: str) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if set(doc) != {
            "schema", "candidate_commit", "checks", "complete", "errors"} or \
            doc["schema"] != SCHEMA or doc["candidate_commit"] != candidate or \
            doc["complete"] is not True or doc["errors"]:
        raise ValueError("seed validation report is not closed")
    expected = {check_id: spec for check_id, spec in CHECKS}
    if not isinstance(doc["checks"], list) or \
            {row.get("id") for row in doc["checks"]} != set(expected) or \
            len(doc["checks"]) != len(expected):
        raise ValueError("seed validation report has the wrong fixed checks")
    for row in doc["checks"]:
        if set(row) != {
                "id", "command", "exit_code", "output",
                "canonical_output_sha256", "semantic_ok"}:
            raise ValueError("seed validation check schema is malformed")
        check_id = row["id"]
        if row["command"] != command_for(expected[check_id]) or \
                row["semantic_ok"] is not True or \
                not isinstance(row["output"], str) or \
                row["canonical_output_sha256"] != hashlib.sha256(
                    canonical_output(row["output"]).encode("utf-8")).hexdigest() or \
                not semantic_ok(check_id, row["output"], row["exit_code"]):
            raise ValueError("seed validation check command/result is not derived")
        replay = run_check(root, check_id, expected[check_id])
        if replay["exit_code"] != row["exit_code"] or \
                replay["canonical_output_sha256"] != \
                row["canonical_output_sha256"] or \
                replay["semantic_ok"] is not True:
            raise ValueError(
                f"seed validation check does not reproduce: {check_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tested-root", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        doc = capture(args.tested_root.resolve(), args.candidate)
    except (OSError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        doc = {
            "schema": SCHEMA,
            "candidate_commit": args.candidate,
            "checks": [],
            "complete": False,
            "errors": [str(exc)],
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    if not doc["complete"]:
        for error in doc["errors"]:
            print(f"FAIL: {error}")
        return 1
    print("PASS: fixed seed validation checks captured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
