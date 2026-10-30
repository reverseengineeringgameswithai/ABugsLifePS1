#!/usr/bin/env python3
"""Classify candidate changes that require a fresh Phase-4 trial root."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import subprocess


SCHEMA = "abl-phase4-trial-boundary/1"
CRITICAL_EXACT = {
    "AGENTS.md",
    "analysis/phase4_method_legacy_live_index.json",
    "config/phase4_closure_policy.yaml",
    "config/phase4_movie_priority.yaml",
    "engineering-specs/phase4-closure.md",
    "ObsidianVault/Playbooks/Game Solving Roadmap/"
    "Phase 4 - Reverse Engineering Operating Method.md",
    "tools/build_identity.py",
    "tools/flik_phase4_method_ratchet.sh",
    "tools/phase4_movie_priority.py",
    "tools/provision_clean_checkout_inputs.py",
    "tools/ratchet_reseed_guard.py",
    "tools/phase4_trial_boundary.py",
}
CRITICAL_PATTERNS = (
    "tools/phase4_method_*.py",
    "tools/phase4_seed_*.py",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def critical_path(path: str) -> bool:
    return path in CRITICAL_EXACT or any(
        fnmatch.fnmatchcase(path, pattern) for pattern in CRITICAL_PATTERNS
    )


def _blob(repo: Path, commit: str, path: str) -> bytes | None:
    run = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if run.returncode == 0:
        return run.stdout
    return None


def build(repo: Path, base: str, candidate: str) -> dict:
    changed = subprocess.check_output([
        "git", "-C", str(repo), "diff", "--name-only", "-z",
        f"{base}..{candidate}",
    ]).decode("utf-8").split("\0")
    changed = sorted(path for path in changed if path)
    critical = [path for path in changed if critical_path(path)]
    identities = {}
    for path in critical:
        before = _blob(repo, base, path)
        after = _blob(repo, candidate, path)
        identities[path] = {
            "base_sha256": None if before is None else sha256_bytes(before),
            "candidate_sha256": None if after is None else sha256_bytes(after),
        }
    return {
        "schema": SCHEMA,
        "base_commit": base,
        "candidate_commit": candidate,
        "changed_paths": changed,
        "trial_critical_paths": critical,
        "critical_identities": identities,
        "reseed_required": bool(critical),
        "complete": True,
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        doc = build(args.repo.resolve(), args.base, args.candidate)
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        doc = {
            "schema": SCHEMA,
            "base_commit": args.base,
            "candidate_commit": args.candidate,
            "changed_paths": [],
            "trial_critical_paths": [],
            "critical_identities": {},
            "reseed_required": False,
            "complete": False,
            "errors": [str(exc)],
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if not doc["complete"]:
        print(f"FAIL: trial-boundary classification failed: {doc['errors']}")
        return 1
    state = "RESEED" if doc["reseed_required"] else "STABLE"
    print(
        f"PASS: trial boundary {state}; changed={len(doc['changed_paths'])} "
        f"critical={len(doc['trial_critical_paths'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
