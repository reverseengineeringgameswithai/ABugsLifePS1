#!/usr/bin/env python3
"""Compile a matched positive/control witness without overstating its authority.

The input is a path-free, hash-bound summary of two independently retained run
receipts.  The compiler requires an identical start fingerprint, an exact
perturbation-key universe, explicit assertions for every observed difference,
and clean non-truncated controls.  It does not launch DuckStation, inspect raw
tokens, or promote a campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "abl-phase4-differential-witness/1"
OUTPUT_SCHEMA = "abl-phase4-differential-witness-result/1"
DIMENSIONS = {
    "original_oracle", "complete_frontier", "typed_state", "lifecycle",
    "original_interfaces", "campaign_breadth", "cross_system_behavior",
    "source_closure", "durable_evidence",
}
OPS = {"eq", "ne", "changed", "unchanged", "delta_eq"}
AUTHORITY = {
    "runtime_silence_proves_absence": False,
    "frame_boundary_proves_exact_instruction": False,
    "promotes_row_or_dimension": False,
    "changes_campaign_registry": False,
    "requires_fresh_verifier": True,
}


class WitnessError(RuntimeError):
    """A witness contract failed closed."""


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def _exact(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        actual = sorted(value) if type(value) is dict else type(value).__name__
        raise WitnessError(f"{field} fields differ: {actual!r}")
    return value


def _string(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise WitnessError(f"{field} must be a non-empty string")
    return value


def _hash(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or len(value) != 64 or any(
            char not in "0123456789abcdef" for char in value):
        raise WitnessError(f"{field} must be a lowercase SHA-256")
    return value


def _safe_value(value: Any, field: str) -> None:
    if value is None or type(value) in {str, int, float, bool}:
        return
    if type(value) is list:
        for index, child in enumerate(value):
            _safe_value(child, f"{field}[{index}]")
        return
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str or not key:
                raise WitnessError(f"{field} has an invalid key")
            _safe_value(child, f"{field}.{key}")
        return
    raise WitnessError(f"{field} has unsupported type {type(value).__name__}")


def load(path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WitnessError(f"cannot load witness: {exc}") from exc
    validate(document)
    return document


def validate(document: Any) -> dict[str, Any]:
    document = _exact(document, {
        "schema", "identity", "claim", "arms", "expected_perturbation_keys",
        "assertions", "authority",
    }, "witness")
    if document["schema"] != SCHEMA:
        raise WitnessError(f"witness must use {SCHEMA}")
    identity = _exact(document["identity"], {
        "row_id", "dimension", "scope", "media_sha256", "executable_sha256",
        "overlay_sha256", "fixture_sha256", "anchor_class", "execution_mode",
        "debugger_binary_sha256", "debugger_source_revision",
    }, "identity")
    for key in ("row_id", "scope", "anchor_class", "execution_mode",
                "debugger_source_revision"):
        _string(identity[key], f"identity.{key}")
    if identity["dimension"] not in DIMENSIONS:
        raise WitnessError("identity.dimension is invalid")
    for key in ("media_sha256", "executable_sha256", "fixture_sha256",
                "debugger_binary_sha256"):
        _hash(identity[key], f"identity.{key}")
    _hash(identity["overlay_sha256"], "identity.overlay_sha256", nullable=True)
    if identity["anchor_class"] not in {"cold_boot", "validated_save_state"}:
        raise WitnessError("identity.anchor_class is invalid")
    if identity["execution_mode"] != "Interpreter":
        raise WitnessError("identity.execution_mode must be Interpreter")
    claim = _exact(document["claim"], {"id", "statement", "observation_scope"},
                   "claim")
    for key in claim:
        _string(claim[key], f"claim.{key}")
    arms = _exact(document["arms"], {"positive", "control"}, "arms")
    arm_keys = {
        "receipt_sha256", "input_sha256", "start_state_sha256",
        "start_fingerprint", "end_fingerprint", "perturbations", "observations",
        "control_checks", "errors", "truncated",
    }
    for name, arm in arms.items():
        arm = _exact(arm, arm_keys, f"arms.{name}")
        for key in ("receipt_sha256", "input_sha256", "start_fingerprint",
                    "end_fingerprint"):
            _hash(arm[key], f"arms.{name}.{key}")
        _hash(arm["start_state_sha256"], f"arms.{name}.start_state_sha256",
              nullable=True)
        if identity["anchor_class"] == "cold_boot" and arm["start_state_sha256"] is not None:
            raise WitnessError(f"arms.{name} cold boot may not name a start state")
        if identity["anchor_class"] == "validated_save_state" and arm[
                "start_state_sha256"] is None:
            raise WitnessError(f"arms.{name} validated state must be hash-bound")
        if type(arm["perturbations"]) is not dict:
            raise WitnessError(f"arms.{name}.perturbations must be a mapping")
        if type(arm["observations"]) is not dict or not arm["observations"]:
            raise WitnessError(f"arms.{name}.observations must be a non-empty mapping")
        _safe_value(arm["perturbations"], f"arms.{name}.perturbations")
        _safe_value(arm["observations"], f"arms.{name}.observations")
        checks = arm["control_checks"]
        if type(checks) is not dict or not checks or any(
                type(key) is not str or not key or value is not True
                for key, value in checks.items()):
            raise WitnessError(f"arms.{name}.control_checks must be non-empty and true")
        if arm["errors"] != []:
            raise WitnessError(f"arms.{name}.errors must be exactly []")
        if arm["truncated"] is not False:
            raise WitnessError(f"arms.{name}.truncated must be false")
    expected_keys = document["expected_perturbation_keys"]
    if type(expected_keys) is not list or len(set(expected_keys)) != len(expected_keys) or any(
            type(value) is not str or not value for value in expected_keys):
        raise WitnessError("expected_perturbation_keys is invalid")
    if type(document["assertions"]) is not list or not document["assertions"]:
        raise WitnessError("assertions must be a non-empty list")
    assertion_ids: set[str] = set()
    for index, assertion in enumerate(document["assertions"]):
        _exact(assertion, {"id", "path", "op", "positive_expected",
                           "control_expected", "delta_expected"},
               f"assertion[{index}]")
        assertion_id = _string(assertion["id"], f"assertion[{index}].id")
        if assertion_id in assertion_ids:
            raise WitnessError(f"duplicate assertion {assertion_id!r}")
        assertion_ids.add(assertion_id)
        _string(assertion["path"], f"assertion[{index}].path")
        if assertion["op"] not in OPS:
            raise WitnessError(f"assertion[{index}].op is invalid")
        for key in ("positive_expected", "control_expected", "delta_expected"):
            _safe_value(assertion[key], f"assertion[{index}].{key}")
        if assertion["op"] == "delta_eq" and type(assertion["delta_expected"]) not in {
                int, float}:
            raise WitnessError(f"assertion[{index}].delta_expected must be numeric")
    if document["authority"] != AUTHORITY:
        raise WitnessError("witness authority differs from the non-promotion contract")
    return document


def _value(document: Any, dotted: str) -> Any:
    current = document
    for segment in dotted.split("."):
        if type(current) is dict:
            current = current[segment]
        elif type(current) is list:
            current = current[int(segment)]
        else:
            raise KeyError(segment)
    return current


def _leaf_differences(positive: Any, control: Any, path: str = "") -> list[str]:
    if type(positive) is not type(control):
        return [path]
    if type(positive) is dict:
        differences = []
        for key in sorted(set(positive) | set(control)):
            child = f"{path}.{key}" if path else key
            if key not in positive or key not in control:
                differences.append(child)
            else:
                differences.extend(_leaf_differences(positive[key], control[key], child))
        return differences
    if type(positive) is list:
        if len(positive) != len(control):
            return [path]
        differences = []
        for index, (left, right) in enumerate(zip(positive, control)):
            child = f"{path}.{index}" if path else str(index)
            differences.extend(_leaf_differences(left, right, child))
        return differences
    return [] if positive == control else [path]


def compile_witness(document: dict[str, Any]) -> dict[str, Any]:
    validate(document)
    positive = document["arms"]["positive"]
    control = document["arms"]["control"]
    errors = []
    if positive["start_fingerprint"] != control["start_fingerprint"]:
        errors.append("START_FINGERPRINT_MISMATCH")
    if positive["start_state_sha256"] != control["start_state_sha256"]:
        errors.append("START_STATE_MISMATCH")
    positive_keys = set(positive["perturbations"])
    control_keys = set(control["perturbations"])
    perturbation_keys = sorted(positive_keys | control_keys)
    expected_perturbation_keys = set(document["expected_perturbation_keys"])
    changed_perturbations = sorted(
        key for key in perturbation_keys
        if key not in positive_keys or key not in control_keys or
        positive["perturbations"][key] != control["perturbations"][key])
    if (positive_keys != expected_perturbation_keys or
            control_keys != expected_perturbation_keys or
            set(changed_perturbations) != expected_perturbation_keys):
        errors.append("PERTURBATION_UNIVERSE_DRIFT")
    differences = _leaf_differences(positive["observations"], control["observations"])
    assertion_results = []
    asserted_paths = set()
    for assertion in document["assertions"]:
        path = assertion["path"]
        asserted_paths.add(path)
        try:
            left = _value(positive["observations"], path)
            right = _value(control["observations"], path)
            op = assertion["op"]
            passed = (
                (op == "eq" and left == assertion["positive_expected"] and
                 right == assertion["control_expected"]) or
                (op == "ne" and left != right and
                 (assertion["positive_expected"] is None or
                  left == assertion["positive_expected"]) and
                 (assertion["control_expected"] is None or
                  right == assertion["control_expected"])) or
                (op == "changed" and left != right) or
                (op == "unchanged" and left == right) or
                (op == "delta_eq" and type(left) in {int, float} and
                 type(right) in {int, float} and
                 left - right == assertion["delta_expected"])
            )
            detail = None
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            left = right = None
            passed = False
            detail = str(exc)
        if not passed:
            errors.append(f"ASSERTION_FAILED:{assertion['id']}")
        assertion_results.append({
            "id": assertion["id"], "path": path, "op": assertion["op"],
            "positive": left, "control": right, "passed": passed, "detail": detail,
        })
    unasserted = sorted(set(differences) - asserted_paths)
    if unasserted:
        errors.append("UNASSERTED_OBSERVATION_DIFFERENCE")
    return {
        "schema": OUTPUT_SCHEMA, "identity": document["identity"],
        "claim": document["claim"],
        "source_witness_sha256": hashlib.sha256(canonical_json(document)).hexdigest(),
        "matched_origin": positive["start_fingerprint"] == control["start_fingerprint"],
        "perturbations": {"changed_keys": changed_perturbations,
                          "expected_keys": sorted(document["expected_perturbation_keys"])},
        "observations": {"differing_leaf_paths": differences,
                         "unasserted_differing_paths": unasserted},
        "assertions": assertion_results,
        "receipts": {name: arm["receipt_sha256"] for name, arm in document["arms"].items()},
        "verdict": "witness_ready_for_fresh_verifier" if not errors else "not_ready",
        "errors": errors, "authority": AUTHORITY,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("witness", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true",
                        help="require --output to already equal regenerated bytes")
    args = parser.parse_args()
    if args.check and args.output is None:
        raise WitnessError("--check requires --output")
    report = compile_witness(load(args.witness))
    payload = canonical_json(report)
    if args.output is None:
        print(payload.decode(), end="")
    else:
        output = args.output.resolve(strict=False)
        try:
            output.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise WitnessError("tracked witness summary must stay inside repository") from exc
        if args.check:
            try:
                current = output.read_bytes()
            except OSError as exc:
                raise WitnessError(f"cannot read retained witness summary: {exc}") from exc
            if current != payload:
                raise WitnessError("retained witness summary is stale")
            print(f"[phase4-witness] {output.relative_to(ROOT)}: fresh")
            return 0
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
        print(f"[phase4-witness] wrote {output.relative_to(ROOT)}")
    return 0 if report["verdict"] == "witness_ready_for_fresh_verifier" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WitnessError as exc:
        raise SystemExit(f"[phase4-witness] ERROR: {exc}") from exc
