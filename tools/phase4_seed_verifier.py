#!/usr/bin/env python3
"""Validate a gap-free pre-trial verifier decision and its closed receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

try:
    import phase4_method_metrics as metrics
except ModuleNotFoundError:
    from tools import phase4_method_metrics as metrics

try:
    import phase4_seed_validation as seed_validation
except ModuleNotFoundError:
    from tools import phase4_seed_validation as seed_validation


EVIDENCE_PATHS = {
    "analysis/phase3_evidence_inventory.json",
    "analysis/phase3_gate_audit.json",
    "analysis/phase4_gate.json",
}
FALSIFIER_KINDS = {
    "live-helper-drift",
    "retained-artifact-drift",
}


def ref_parts(value: str) -> tuple[str, str]:
    match = re.fullmatch(r"(repo|run):([^@]+)@[0-9a-f]{64}", value)
    if match is None:
        raise metrics.MetricsError("seed verifier reference is malformed")
    return match.group(1), match.group(2)


def validate_evidence(
        refs: list[str], run_dir: Path, tested_root: Path,
) -> None:
    paths: dict[str, Path] = {}
    for index, ref in enumerate(refs):
        scope, rel = ref_parts(ref)
        if scope != "repo":
            raise metrics.MetricsError(
                "seed evidence must be an authoritative repo artifact")
        paths[rel] = metrics._decision_artifact(
            ref, run_dir, tested_root, f"seed evidence[{index}]")
    if set(paths) != EVIDENCE_PATHS or len(paths) != len(EVIDENCE_PATHS):
        raise metrics.MetricsError(
            "seed evidence must name the Phase-3 inventory/gate and Phase-4 gate")

    inventory = json.loads(
        paths["analysis/phase3_evidence_inventory.json"].read_text())
    summary = inventory.get("summary") or {}
    structural_gaps = (
        "missing_generator_declarations", "stale_generator_declarations",
        "orphan_artifacts", "missing_outputs",
        "live_artifacts_without_run_provenance",
        "live_artifact_environment_mismatches",
        "live_artifact_source_dependency_mismatches",
        "live_artifact_reproduction_guard_failures",
        "current_live_toolchain_gaps", "tracked_input_mutations",
    )
    if inventory.get("closure_ready") is not True or \
            inventory.get("retained_artifact_fresh") is not True or \
            any(summary.get(key) for key in structural_gaps):
        raise metrics.MetricsError(
            "Phase-3 evidence inventory is not semantically closure-ready")

    phase3 = json.loads(paths["analysis/phase3_gate_audit.json"].read_text())
    if phase3.get("gate_met") is not True or \
            (phase3.get("evidence_inventory") or {}).get("met") is not True or \
            (phase3.get("decisive_evidence") or {}).get("met") is not True or \
            any((not row.get("met"))
                for row in (phase3.get("bullets") or {}).values()):
        raise metrics.MetricsError(
            "Phase-3 gate evidence is not semantically MET")

    phase4 = json.loads(paths["analysis/phase4_gate.json"].read_text())
    prerequisite = phase4.get("prerequisites") or {}
    recomputed = phase4.get("phase3_recomputed") or {}
    recomputed_inventory = recomputed.get("inventory") or {}
    counts = phase4.get("coverage_counts") or {}
    if phase4.get("gate_met") is not False or \
            prerequisite.get("phase3_gate_recomputed") is not True or \
            prerequisite.get("pristine_build_identity") is not True or \
            recomputed.get("met") is not True or \
            recomputed_inventory.get("retained_artifact_fresh") is not True or \
            (recomputed_inventory.get("summary") or {}).get(
                "tracked_input_mutations") or \
            counts.get("baseline_rows") != 107:
        raise metrics.MetricsError(
            "Phase-4 gate does not retain the repaired Phase-3 prerequisite")


def expected_falsifier_command(kind: str) -> list[str]:
    return [
        sys.executable, "-B", "tools/phase4_seed_falsifiers.py",
        "--kind", kind,
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--tested-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        tested_root = args.tested_root.resolve()
        run_dir = args.run_dir.resolve()
        head = subprocess.check_output(
            ["git", "-C", str(tested_root), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        status_before = subprocess.check_output(
            ["git", "-C", str(tested_root), "status",
             "--porcelain=v1", "--untracked-files=all"],
            text=True,
        )
        if head != args.candidate or status_before:
            raise metrics.MetricsError(
                "seed verifier did not start at the exact clean candidate")
        doc = json.loads(args.decision.read_text(encoding="utf-8"))
        validated = metrics._validate_verifier_decision(
            doc,
            args.candidate,
            "seed-repair verifier",
            run_dir=run_dir,
            tested_root=tested_root,
        )
        if validated["status"] != "open_autonomous" or \
                validated["gaps"] or validated["gap_codes"] or \
                validated["required_input"] or \
                len(validated["falsifier_results"]) < 2:
            raise metrics.MetricsError(
                "seed-repair verifier is not a gap-free, independently "
                "falsified open_autonomous decision"
            )
        validate_evidence(validated["evidence"], run_dir, tested_root)
        if len(validated["validation"]) != 1:
            raise metrics.MetricsError(
                "seed verifier requires exactly one fixed validation report")
        validation_artifact = metrics._decision_artifact(
            validated["validation"][0], run_dir, tested_root,
            "seed validation report")
        if ref_parts(validated["validation"][0])[0] != "run":
            raise metrics.MetricsError(
                "seed validation report must be retained under the run root")
        seed_validation.validate_and_replay(
            validation_artifact, tested_root, args.candidate)
        seen_falsifiers: set[str] = set()
        for index, item in enumerate(validated["falsifier_results"]):
            artifact = metrics._decision_artifact(
                item["evidence"], run_dir, tested_root,
                f"seed-repair verifier falsifier[{index}]",
            )
            receipt = json.loads(artifact.read_text(encoding="utf-8"))
            command = receipt["command"]
            kind = receipt["id"]
            expected = expected_falsifier_command(kind) \
                if kind in FALSIFIER_KINDS else None
            normalized = list(command)
            if normalized and Path(normalized[0]).name in {"python", "python3"}:
                normalized[0] = sys.executable
            if expected is None or normalized != expected or \
                    kind in seen_falsifiers:
                raise metrics.MetricsError(
                    "seed falsifier is not a distinct immutable bounded mutation")
            seen_falsifiers.add(kind)
            replay = subprocess.run(
                normalized,
                cwd=tested_root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=300,
            )
            if replay.returncode != receipt["exit_code"] or \
                    replay.stdout != receipt["output"] or \
                    hashlib.sha256(replay.stdout.encode("utf-8")).hexdigest() != \
                    receipt["output_sha256"]:
                raise metrics.MetricsError(
                    f"seed falsifier[{index}] command does not reproduce its "
                    "retained result")
            if '"guard_rejected": true' not in replay.stdout or \
                    '"restored": true' not in replay.stdout:
                raise metrics.MetricsError(
                    f"seed falsifier[{index}] lacks a derived red/restored result")
        if seen_falsifiers != FALSIFIER_KINDS:
            raise metrics.MetricsError(
                "seed verifier did not run both immutable bounded falsifiers")
        status_after = subprocess.check_output(
            ["git", "-C", str(tested_root), "status",
             "--porcelain=v1", "--untracked-files=all"],
            text=True,
        )
        if status_after:
            raise metrics.MetricsError(
                "seed falsifier replay left candidate checkout dirty")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired,
            metrics.MetricsError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(
        "PASS: seed-repair verifier evidence and falsifier commands reproduce "
        "against the exact clean candidate"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
