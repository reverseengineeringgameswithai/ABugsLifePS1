#!/usr/bin/env python3
"""Capture fixed, machine-readable validation reports for one method iteration."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def fixed_report_commands(
        python: str = sys.executable,
) -> dict[str, list[tuple[list[str], set[int]]]]:
    """Return the closed command contract independently checked by the metrics tool."""
    return {
        "abl-phase4-validation-report/1": [
            ([python, "tools/phase4_closure_debt.py", "--check"], {0}),
            ([python, "tools/phase4_offline_queue.py", "--check"], {0}),
            ([python, "tools/phase4_derived_index.py", "--check"], {0}),
            ([
                python, "-m", "pytest", "-q",
                "tests/test_phase4_closure_debt.py",
                "tests/test_phase4_offline_queue.py",
                "tests/test_phase4_derived_index.py",
                "tests/test_phase4_gate.py",
                "tests/test_phase4_method_metrics.py",
            ], {0}),
        ],
        "abl-phase4-knowledge-report/1": [
            ([
                python, "tools/phase4_reconcile_assertion_pins.py", "--check",
            ], {0}),
            ([
                python, "-m", "pytest", "-q",
                "tests/test_phase4_registry.py",
                "tests/test_knowledge_closure.py",
            ], {0}),
        ],
        "abl-phase4-vault-report/1": [
            ([python, "tools/validate_vault.py", "--check"], {0}),
        ],
        "abl-phase4-clean-checkout-report/1": [
            ([python, "tools/build_identity.py", "--verify"], {0}),
            ([python, "tools/phase4_gate.py"], {0, 1}),
        ],
    }


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    run = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if run.returncode:
        raise RuntimeError(run.stderr.strip())
    return run.stdout


def run_check(command: list[str], *, accepted_codes: set[int] = {0}) -> dict[str, Any]:
    started = now()
    run = subprocess.run(
        command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    finished = now()
    output = run.stdout
    decoded = output.decode("utf-8", errors="replace")
    return {
        "command": command,
        "started_at": started,
        "finished_at": finished,
        "exit_code": run.returncode,
        "accepted_exit_codes": sorted(accepted_codes),
        "ok": run.returncode in accepted_codes,
        "output_sha256": sha256_bytes(decoded.encode("utf-8")),
        "output": decoded,
        "output_tail": decoded[-4000:],
    }


def report(schema: str, commit: str, checks: list[dict[str, Any]],
           **extra: Any) -> dict[str, Any]:
    errors = [
        f"{' '.join(item['command'])}: exit {item['exit_code']}"
        for item in checks if not item["ok"]
    ]
    return {
        "schema": schema,
        "tested_commit": commit,
        "generated_at": now(),
        "complete": not errors,
        "errors": errors,
        "checks": checks,
        **extra,
    }


def write(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--executor-log", type=Path, required=True)
    parser.add_argument("--verifier-log", type=Path)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    commit = git("rev-parse", "HEAD").strip()
    status_before = git("status", "--porcelain=v1", "--untracked-files=all")

    fixed_commands = fixed_report_commands()
    validation_checks = [
        run_check(command, accepted_codes=accepted)
        for command, accepted
        in fixed_commands["abl-phase4-validation-report/1"]
    ]
    knowledge_checks = [
        run_check(command, accepted_codes=accepted)
        for command, accepted
        in fixed_commands["abl-phase4-knowledge-report/1"]
    ]
    vault_checks = [
        run_check(command, accepted_codes=accepted)
        for command, accepted
        in fixed_commands["abl-phase4-vault-report/1"]
    ]
    # Phase 4 is expected to remain OPEN during a campaign trial.  The gate must
    # run and reject closure, so both 0 (eventual closure) and 1 (honest open) are
    # legitimate command outcomes.  The report records the exact exit code.
    clean_checks = [
        run_check(command, accepted_codes=accepted)
        for command, accepted
        in fixed_commands["abl-phase4-clean-checkout-report/1"]
    ]

    log_entries = []
    run_root = args.out_dir.parent
    for role, path in (
        ("executor", args.executor_log),
        ("verifier", args.verifier_log),
    ):
        if path is None:
            continue
        if not path.is_file():
            log_entries.append({
                "role": role, "artifact": None, "size": None,
            })
            continue
        data = path.read_bytes()
        resolved = path.resolve()
        try:
            rel = resolved.relative_to(run_root.resolve()).as_posix()
        except ValueError as exc:
            raise SystemExit(
                f"{role} log is outside retained run root: {resolved}") from exc
        log_entries.append({
            "role": role,
            "artifact": {
                "scope": "run", "path": rel, "sha256": sha256_bytes(data),
            },
            "size": len(data),
        })
    log_errors = [
        f"{entry['role']} log is missing" for entry in log_entries
        if entry["artifact"] is None
    ]
    command_doc = {
        "schema": "abl-phase4-command-log/1",
        "tested_commit": commit,
        "generated_at": now(),
        "complete": not log_errors,
        "errors": log_errors,
        "checks": [],
        "logs": log_entries,
    }
    validation_doc = report(
        "abl-phase4-validation-report/1", commit, validation_checks)
    knowledge_doc = report(
        "abl-phase4-knowledge-report/1", commit, knowledge_checks,
        joined=all(check["ok"] for check in knowledge_checks))
    vault_doc = report(
        "abl-phase4-vault-report/1", commit, vault_checks)

    status_after = git("status", "--porcelain=v1", "--untracked-files=all")
    clean_doc = report(
        "abl-phase4-clean-checkout-report/1", commit, clean_checks,
        status_before=status_before.splitlines(),
        status_after=status_after.splitlines(),
    )

    write(args.out_dir / "command-log.json", command_doc)
    write(args.out_dir / "validation-report.json", validation_doc)
    write(args.out_dir / "knowledge-report.json", knowledge_doc)
    write(args.out_dir / "vault-report.json", vault_doc)
    write(args.out_dir / "clean-checkout-report.json", clean_doc)
    docs = (command_doc, validation_doc, knowledge_doc, vault_doc, clean_doc)
    if not all(doc["complete"] for doc in docs) or status_before or status_after:
        print("FAIL: one or more method reports are incomplete", file=sys.stderr)
        return 1
    print(f"PASS: fixed iteration reports captured at {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
