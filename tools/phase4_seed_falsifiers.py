#!/usr/bin/env python3
"""Run immutable, bounded falsifiers for the pre-Phase-4 seed repair."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase3_evidence_inventory  # noqa: E402
import phase4_gate  # noqa: E402


TARGETS = {
    "live-helper-drift": ROOT / "tools" / "live_session_provenance.py",
    "retained-artifact-drift":
        ROOT / "analysis" / "phase3_render_descriptors.json",
}


def status() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain=v1",
         "--untracked-files=all"],
        text=True,
    )


def run(kind: str) -> dict:
    target = TARGETS[kind]
    before_status = status()
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"\n")
        inventory = phase3_evidence_inventory.build_inventory()
        if inventory["closure_ready"] is not False:
            raise RuntimeError("Phase-3 inventory stayed closure-ready after mutation")
        if kind == "live-helper-drift":
            rejected = bool(
                inventory["summary"][
                    "live_artifact_source_dependency_mismatches"])
        else:
            rejected = str(target.relative_to(ROOT)) in \
                inventory["summary"]["tracked_input_mutations"]
            gate = phase4_gate.build()
            rejected = rejected and \
                gate["prerequisites"]["phase3_gate_recomputed"] is False
        if not rejected:
            raise RuntimeError(f"{kind} did not turn its downstream guard red")
    finally:
        target.write_bytes(original)
    if status() != before_status:
        raise RuntimeError("falsifier did not restore the exact checkout state")
    return {
        "schema": "abl-phase4-seed-falsifier-result/1",
        "kind": kind,
        "mutation_target": str(target.relative_to(ROOT)),
        "guard_rejected": True,
        "restored": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=sorted(TARGETS), required=True)
    args = parser.parse_args()
    try:
        result = run(args.kind)
    except (OSError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True))
    print(f"PASS: bounded seed falsifier survived: {args.kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
