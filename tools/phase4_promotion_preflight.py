#!/usr/bin/env python3
"""Fail-closed preflight for Phase-4 dimension-promotion packets.

The strongest verdict is ``ready_for_fresh_verifier``.  This tool never edits
the campaign registry, debt ledger, findings, or Obsidian knowledge layers.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import operator
from pathlib import Path
from typing import Any, Callable

import yaml

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_promotion_packets.yaml"
DEBT_PATH = common.ROOT / "analysis/phase4_closure_debt.json"
OUTPUT_PATH = common.ROOT / "analysis/phase4_promotion_preflight.json"
SCHEMA = "abl-phase4-promotion-packets/1"
DIMENSION_ORDER = (
    "original_oracle", "complete_frontier", "typed_state", "lifecycle",
    "original_interfaces", "campaign_breadth", "cross_system_behavior",
    "source_closure", "durable_evidence",
)
DIMENSIONS = set(DIMENSION_ORDER)
POLICY_PATH = "config/phase4_closure_policy.yaml"
LAYER_IDS = (
    "oracle", "frontier", "typed_state", "interfaces", "lifecycle", "breadth",
    "controls", "source", "knowledge",
)
REQUIRED_LAYERS = {
    "original_oracle": {"oracle", "controls", "knowledge"},
    "complete_frontier": {"frontier", "source", "knowledge"},
    "typed_state": {"typed_state", "source", "knowledge"},
    "lifecycle": {"lifecycle", "controls", "source", "knowledge"},
    "original_interfaces": {"interfaces", "source", "knowledge"},
    "campaign_breadth": {"breadth", "controls", "knowledge"},
    "cross_system_behavior": {"interfaces", "controls", "knowledge"},
    "source_closure": {"source", "knowledge"},
    "durable_evidence": {"knowledge"},
}
OPS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": operator.eq,
    "ne": operator.ne,
    "contains": lambda left, right: right in left,
    "len_eq": lambda left, right: len(left) == right,
}
FAKE_SUCCESS_KEYS = {
    "success", "passed", "verified", "ready", "closure_ready", "complete",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def path_value(document: Any, dotted: str) -> Any:
    value = document
    for segment in dotted.split(".") if dotted else []:
        value = value[int(segment)] if isinstance(value, list) else value[segment]
    return value


def campaigns_by_id(registry: dict) -> dict[str, dict]:
    return {row.get("id"): row for row in registry.get("child_campaigns") or []}


def debt_by_row(debt: dict) -> dict[str, dict]:
    return {row.get("row_id"): row for row in debt.get("rows") or []}


def authored_boolean_fields(value: Any, path: str = "packet") -> list[str]:
    """Return every nested authored verdict-like boolean, with its exact path."""
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FAKE_SUCCESS_KEYS and isinstance(child, bool):
                found.append(child_path)
            found.extend(authored_boolean_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(authored_boolean_fields(child, f"{path}.{index}"))
    return found


def layer_present(layer: str, campaign: dict, claim: dict | None) -> bool:
    evidence = campaign.get("evidence") or {}
    frontier = campaign.get("frontier") or {}
    if layer == "oracle":
        return bool((campaign.get("oracle_fixtures") and evidence.get("oracle"))
                    or ((claim or {}).get("evidence")))
    if layer == "frontier":
        return bool(frontier and (evidence.get("frontier") or (claim or {}).get("evidence")))
    if layer == "typed_state":
        return bool(frontier.get("typed_state") and evidence.get("frontier"))
    if layer == "interfaces":
        return all(frontier.get(key) for key in ("functions", "readers", "writers"))
    if layer == "lifecycle":
        return bool(campaign.get("lifecycle") and evidence.get("lifecycle"))
    if layer == "breadth":
        return bool(campaign.get("breadth") and evidence.get("breadth"))
    if layer == "controls":
        controls = campaign.get("controls") or {}
        return bool(controls.get("positive") and controls.get("negative")
                    and (evidence.get("controls") or (claim or {}).get("evidence")))
    if layer == "source":
        return bool(campaign.get("source_status") and evidence.get("source"))
    if layer == "knowledge":
        return bool(campaign.get("note") and (campaign.get("findings")
                                               or (claim or {}).get("knowledge_bindings")
                                               or (claim or {}).get("authoritative_paths")))
    raise KeyError(layer)


def artifact_document(rel: str, overrides: dict[str, dict] | None) -> dict:
    if overrides and rel in overrides:
        return overrides[rel]
    return common.load_json(rel)


def packet_errors(packet: dict, *, config: dict, registry: dict, debt: dict,
                  overrides: dict[str, dict] | None = None,
                  tracked: Callable[[str], bool] = common.git_tracked) -> list[dict]:
    errors: list[dict] = []

    def reject(code: str, detail: str) -> None:
        errors.append({"code": code, "detail": detail})

    for path in authored_boolean_fields(packet):
        reject("FAKE_SUCCESS_FIELD", f"authored boolean {path!r} is forbidden")

    packet_id = str(packet.get("id") or "<missing>")
    if not packet.get("id") or not packet.get("row_id") or not packet.get("campaign_id"):
        reject("PACKET_IDENTITY_MISSING", "id, row_id, and campaign_id are mandatory")
    dimension = packet.get("dimension")
    dimension_key = dimension if isinstance(dimension, str) else ""
    if dimension_key not in DIMENSIONS:
        reject("DIMENSION_INVALID", f"unknown dimension {dimension!r}")
    if packet.get("proposed_transition") != "met":
        reject("TRANSITION_INVALID", "the only preflighted promotion transition is met")
    if packet.get("confidence") not in {"confirmed", "partial"}:
        reject("CONFIDENCE_INVALID", "promotion confidence must be confirmed or partial")
    if packet.get("claim_source") != "registry_dimension_claim":
        reject("CLAIM_SOURCE_INVALID", "claim source must be registry_dimension_claim")

    campaign = campaigns_by_id(registry).get(packet.get("campaign_id"))
    claim: dict | None = None
    if campaign is None:
        reject("CAMPAIGN_MISSING", f"campaign {packet.get('campaign_id')!r} is absent")
        campaign = {}
    elif packet.get("row_id") not in (campaign.get("rows") or []):
        reject("CAMPAIGN_ROW_MISMATCH", f"{packet.get('row_id')} is not owned by the campaign")
    else:
        claim = (campaign.get("dimension_claims") or {}).get(dimension_key)
        if claim is None:
            reject("CLAIM_MISSING", f"registry has no {dimension} claim for {packet_id}")
        else:
            if claim.get("claim") != "met":
                reject("CLAIM_NOT_MET", f"registry claim is {claim.get('claim')!r}")
            if claim.get("confidence") != packet.get("confidence"):
                reject("CONFIDENCE_DRIFT", "packet and retained claim confidence differ")
            assertions = claim.get("evidence") or []
            if not assertions:
                reject("ASSERTIONS_MISSING", "retained claim has no low-level assertions")
            for index, assertion in enumerate(assertions):
                for detail in common.audit_assertion(assertion):
                    reject("ASSERTION_INVALID", f"assertion {index}: {detail}")
            paths = claim.get("authoritative_paths") or []
            if not paths:
                reject("AUTHORITATIVE_PATHS_MISSING", "retained claim has no paths")
            for rel in paths:
                path = common.ROOT / str(rel)
                if Path(str(rel)).is_absolute() or ".." in Path(str(rel)).parts:
                    reject("AUTHORITATIVE_PATH_UNSAFE", str(rel))
                elif not path.is_file():
                    reject("AUTHORITATIVE_PATH_MISSING", str(rel))
                elif not tracked(str(rel)):
                    reject("AUTHORITATIVE_PATH_UNTRACKED", str(rel))

    debt_row = debt_by_row(debt).get(packet.get("row_id"))
    if debt_row is None:
        reject("DEBT_ROW_MISSING", f"debt has no row {packet.get('row_id')!r}")
    elif claim is not None and (debt_row.get("dimensions") or {}).get(
            dimension_key, {}).get("state") != "met":
        reject("DEBT_STATE_STALE", "retained claim and derived debt state disagree")

    dispositions = packet.get("layer_dispositions")
    if not isinstance(dispositions, dict) or set(dispositions) != set(LAYER_IDS):
        reject("LAYER_SET_INCOMPLETE", "every canonical layer needs one disposition")
    else:
        required = REQUIRED_LAYERS.get(dimension_key, set())
        for layer in LAYER_IDS:
            disposition = dispositions[layer]
            status = disposition.get("status") if isinstance(disposition, dict) else None
            if layer in required and status != "required":
                reject("REQUIRED_LAYER_NOT_REQUIRED",
                       f"{dimension} requires canonical layer {layer}")
            if status == "required":
                if not layer_present(layer, campaign, claim):
                    reject(f"LAYER_{layer.upper()}_MISSING", "required layer has no retained evidence")
            elif status == "not_applicable":
                if len(str(disposition.get("reason") or "").strip()) < 30:
                    reject("NOT_APPLICABLE_REASON_MISSING", f"{layer} needs a specific reason")
            else:
                reject("LAYER_DISPOSITION_INVALID", f"{layer}: {status!r}")

    frontier = packet.get("static_frontier") or {}
    if not isinstance(frontier, dict):
        reject("FRONTIER_SPEC_INVALID", "static_frontier must be a mapping")
        frontier = {}
    rel = str(frontier.get("artifact") or "")
    path = common.ROOT / rel
    if not rel or not path.is_file():
        reject("FRONTIER_ARTIFACT_MISSING", rel or "<missing>")
    else:
        expected_hash = str(frontier.get("sha256") or "")
        if overrides and rel in overrides:
            actual_hash = expected_hash
        else:
            actual_hash = sha256(path)
        if actual_hash != expected_hash:
            reject("FRONTIER_HASH_DRIFT", f"{rel}: {actual_hash}")
        if not tracked(rel):
            reject("FRONTIER_ARTIFACT_UNTRACKED", rel)
        document = artifact_document(rel, overrides)
        for guard in frontier.get("guards") or []:
            code = str(guard.get("code") or "FRONTIER_GUARD_INVALID")
            try:
                actual = path_value(document, str(guard.get("json_path") or ""))
                operation = OPS[guard.get("op")]
                if not operation(actual, guard.get("expected")):
                    reject(code, f"{guard.get('json_path')}: expected {guard.get('expected')!r}, observed {actual!r}")
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                reject(code, f"guard cannot be evaluated: {exc}")

    for rel in packet.get("clean_checkout_dependencies") or []:
        path = common.ROOT / str(rel)
        if not path.is_file():
            reject("CLEAN_DEPENDENCY_MISSING", str(rel))
        elif not tracked(str(rel)):
            reject("CLEAN_DEPENDENCY_UNTRACKED", str(rel))
    if not packet.get("clean_checkout_dependencies"):
        reject("CLEAN_DEPENDENCIES_MISSING", "packet has no clean-checkout dependency list")

    external = packet.get("external_dependencies") or {}
    if not isinstance(external, dict):
        reject("EXTERNAL_DISPOSITION_INVALID", "external_dependencies must be a mapping")
        external = {}
    external_status = external.get("status")
    if external_status == "campaign_oracle_fixtures":
        pins = common.load_json(common.FIXTURE_SET_PATH).get("entries") or {}
        fixtures = campaign.get("oracle_fixtures") or []
        if not fixtures:
            reject("EXTERNAL_FIXTURES_MISSING", "campaign has no oracle fixture list")
        for rel in fixtures:
            pin = pins.get(rel)
            path = common.ROOT / rel
            if pin is None:
                reject("EXTERNAL_PIN_MISSING", rel)
            elif not path.is_file():
                reject("EXTERNAL_BYTES_MISSING", rel)
            elif sha256(path) != pin.get("sha256"):
                reject("EXTERNAL_HASH_DRIFT", rel)
    elif external_status == "not_applicable":
        if len(str(external.get("reason") or "").strip()) < 30:
            reject("EXTERNAL_REASON_MISSING", "not_applicable needs a specific reason")
    else:
        reject("EXTERNAL_DISPOSITION_INVALID", str(external_status))

    residuals = (claim or {}).get("residuals") if claim is not None else None
    if residuals is None:
        residuals = campaign.get("bounded_residuals")
    if not isinstance(residuals, list):
        reject("RESIDUALS_MISSING", "packet has no explicit residual source")
    else:
        for residual in residuals:
            intersects = residual.get("intersects_dimension")
            if intersects is None:
                intersects = residual.get("intersects_behavior")
            if intersects is not False:
                reject("RESIDUAL_INTERSECTS", str(residual.get("boundary") or "<unnamed>"))
            if not all(str(residual.get(key) or "").strip()
                       for key in ("boundary", "evidence", "next_experiment")):
                reject("RESIDUAL_MALFORMED", str(residual.get("boundary") or "<unnamed>"))

    falsifier = packet.get("disposable_falsifier") or {}
    if not isinstance(falsifier, dict):
        reject("FALSIFIER_MISSING", "disposable_falsifier must be a mapping")
        falsifier = {}
    if len(str(falsifier.get("mutation") or "").strip()) < 30 or not str(
            falsifier.get("expected_code") or "").strip():
        reject("FALSIFIER_MISSING", "specific mutation and stable expected code are mandatory")

    return sorted(errors, key=lambda row: (row["code"], row["detail"]))


def build(*, config: dict | None = None, registry: dict | None = None,
          debt: dict | None = None, overrides: dict[str, dict] | None = None,
          tracked: Callable[[str], bool] = common.git_tracked) -> dict:
    config_from_disk = config is None
    config = copy.deepcopy(config or common.load_yaml(CONFIG_PATH))
    registry = copy.deepcopy(registry or common.load_yaml(common.REGISTRY_PATH))
    debt = copy.deepcopy(debt or common.load_json(DEBT_PATH))
    global_errors = []
    if config.get("schema") != SCHEMA:
        global_errors.append({"code": "CONFIG_SCHEMA_INVALID", "detail": str(config.get("schema"))})
    policy_rel = str(config.get("policy") or "")
    policy_path = common.ROOT / policy_rel
    if policy_rel != POLICY_PATH:
        global_errors.append({"code": "POLICY_PATH_INVALID", "detail": policy_rel})
    elif not policy_path.is_file():
        global_errors.append({"code": "POLICY_MISSING", "detail": policy_rel})
    else:
        if not tracked(policy_rel):
            global_errors.append({"code": "POLICY_UNTRACKED", "detail": policy_rel})
        actual_policy_hash = sha256(policy_path)
        if config.get("policy_sha256") != actual_policy_hash:
            global_errors.append({
                "code": "POLICY_HASH_STALE", "detail": actual_policy_hash})
        policy = common.load_yaml(policy_path)
        policy_dimensions = tuple(row.get("id") for row in policy.get("dimensions") or [])
        if policy.get("schema") != "abl-phase4-closure-policy/1" or \
                policy_dimensions != DIMENSION_ORDER:
            global_errors.append({
                "code": "POLICY_DIMENSIONS_INVALID", "detail": str(policy_dimensions)})
    if tuple(config.get("layer_ids") or []) != LAYER_IDS:
        global_errors.append({
            "code": "LAYER_POLICY_INVALID", "detail": str(config.get("layer_ids"))})
    debt_spec = config.get("debt_snapshot") or {}
    if debt_spec.get("path") != "analysis/phase4_closure_debt.json" or sha256(DEBT_PATH) != debt_spec.get("sha256"):
        global_errors.append({"code": "DEBT_HASH_STALE", "detail": str(debt_spec.get("sha256"))})
    ids = [row.get("id") for row in config.get("packets") or []]
    if len(ids) != len(set(ids)):
        global_errors.append({"code": "PACKET_ID_DUPLICATE", "detail": str(ids)})
    packets = []
    for packet in config.get("packets") or []:
        errors = packet_errors(packet, config=config, registry=registry, debt=debt,
                               overrides=overrides, tracked=tracked)
        packets.append({
            "id": packet.get("id"), "row_id": packet.get("row_id"),
            "campaign_id": packet.get("campaign_id"), "dimension": packet.get("dimension"),
            "verdict": "ready_for_fresh_verifier" if not errors else "not_ready",
            "errors": errors,
        })
    return {
        "schema": "abl-phase4-promotion-preflight/1",
        "generated": str(config.get("generated")),
        "inputs": {
            "packet_config_sha256": sha256(CONFIG_PATH) if config_from_disk else None,
            "campaign_registry_sha256": sha256(common.REGISTRY_PATH),
            "closure_debt_sha256": sha256(DEBT_PATH),
        },
        "global_errors": global_errors,
        "packets": packets,
        "summary": {
            "packets": len(packets),
            "ready_for_fresh_verifier": sum(row["verdict"] == "ready_for_fresh_verifier" for row in packets),
            "not_ready": sum(row["verdict"] == "not_ready" for row in packets),
        },
        "registry_mutated": False,
        "valid": not global_errors,
    }


def render(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare retained output byte-for-byte")
    args = parser.parse_args()
    document = build()
    rendered = render(document)
    if args.check:
        if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_text() != rendered:
            print("[phase4-promotion-preflight] FAIL: retained output is stale")
            return 1
        print("[phase4-promotion-preflight] PASS: retained output reproduces byte-identically")
        return 0
    OUTPUT_PATH.write_text(rendered)
    print(f"[phase4-promotion-preflight] wrote {OUTPUT_PATH.relative_to(common.ROOT)}: "
          f"{document['summary']['ready_for_fresh_verifier']} ready, "
          f"{document['summary']['not_ready']} not ready")
    return 0 if document["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
