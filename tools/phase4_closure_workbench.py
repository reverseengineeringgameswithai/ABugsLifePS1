#!/usr/bin/env python3
"""Compile review-safe Phase-4 work packets for all nine subsystem dimensions.

This joins the authoritative 107-row registry, retained debt, campaign evidence,
standalone scorecards, the static-frontier pilots, findings, fixtures, capsules,
and preservation state.  It does not trust prose status words and it never edits
the campaign registry or debt ledger.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

import phase4_common as common


ROOT = common.ROOT
POLICY_PATH = ROOT / "config/phase4_closure_workbench.yaml"
DEBT_PATH = ROOT / "analysis/phase4_closure_debt.json"
STATIC_PILOTS_PATH = ROOT / "analysis/phase4_static_frontier_pilots.json"
CAPSULE_SET_PATH = ROOT / "analysis/phase4_trace_capsule_set.json"
QUEUE_PATH = ROOT / "analysis/phase4_offline_opportunity_queue.json"
FIXTURE_AUDIT_PATH = ROOT / "analysis/phase4_fixture_audit.json"
INVENTORY_PATH = ROOT / "analysis/phase4_campaign_inventory.json"
PHASE2_COVERAGE_PATH = ROOT / "analysis/phase2_row_coverage.json"
PHASE3_OWNERSHIP_PATH = ROOT / "analysis/phase3_ownership_graph.json"
FUNCTION_CENSUS_PATH = ROOT / "analysis/functions.json"
OUTPUT_PATH = ROOT / "analysis/phase4_closure_workbench.json"
POLICY_SCHEMA = "abl-phase4-closure-workbench-policy/1"
OUTPUT_SCHEMA = "abl-phase4-closure-workbench/1"
DIMENSIONS = (
    "original_oracle", "complete_frontier", "typed_state", "lifecycle",
    "original_interfaces", "campaign_breadth", "cross_system_behavior",
    "source_closure", "durable_evidence",
)
AUTHORITY = {
    "changes_campaign_registry": False,
    "changes_debt_ledger": False,
    "promotes_row_or_dimension": False,
    "writes_external_evidence": False,
    "launches_emulator": False,
    "strongest_verdict": "ready_for_fresh_verifier",
    "fresh_verifier_required": True,
}


class WorkbenchError(RuntimeError):
    """A policy, retained input, or work-packet contract failed closed."""


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _retained_receipt_status(document: dict[str, Any],
                             expected_inputs: dict[str, Path]) -> dict[str, Any]:
    """Recompute a retained audit's source receipt before trusting its green bit."""
    declared = document.get("inputs")
    errors = []
    if type(declared) is not dict:
        declared = {}
        errors.append("INPUT_RECEIPT_MISSING")
    if set(declared) != set(expected_inputs):
        errors.append("INPUT_RECEIPT_KEY_DRIFT")
    comparisons = {}
    for key, path in expected_inputs.items():
        actual = sha256(path) if path.is_file() else None
        expected = declared.get(key)
        matches = actual is not None and expected == actual
        comparisons[key] = {
            "expected_sha256": expected, "actual_sha256": actual,
            "matches": matches,
        }
        if not matches:
            errors.append(f"INPUT_HASH_DRIFT:{key}")
    declared_ready = document.get("structural_ready") is True
    if not declared_ready:
        errors.append("DECLARED_STRUCTURAL_GAPS")
    return {
        "declared_structural_ready": declared_ready,
        "inputs_fresh": all(row["matches"] for row in comparisons.values()) and
                        set(declared) == set(expected_inputs),
        "ready": not errors,
        "inputs": comparisons,
        "errors": sorted(set(errors)),
    }


def _exact_keys(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        actual = sorted(value) if type(value) is dict else type(value).__name__
        raise WorkbenchError(f"{field} fields differ: {actual!r}")
    return value


def _nonempty(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise WorkbenchError(f"{field} must be a non-empty string")
    return value


def _strict_int(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise WorkbenchError(f"{field} must be an integer >= {minimum}")
    return value


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WorkbenchError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    if type(value) is not dict:
        raise WorkbenchError(f"{path.relative_to(ROOT)} must contain a mapping")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkbenchError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    if type(value) is not dict:
        raise WorkbenchError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def validate_policy(policy: Any) -> dict[str, Any]:
    policy = _exact_keys(policy, {
        "schema", "description", "dimensions", "frontier_policy", "pilot_rows",
        "standalone_scorecards", "live_escalation", "authority",
    }, "policy")
    if policy["schema"] != POLICY_SCHEMA:
        raise WorkbenchError(f"policy must use {POLICY_SCHEMA}")
    _nonempty(policy["description"], "policy.description")
    if type(policy["dimensions"]) is not list or len(policy["dimensions"]) != 9:
        raise WorkbenchError("policy.dimensions must contain exactly nine rows")
    observed_ids = []
    for index, dimension in enumerate(policy["dimensions"]):
        _exact_keys(dimension, {
            "id", "ordinal", "title", "required_layers", "default_lane",
            "accelerator", "completion_question", "next_action",
        }, f"dimension[{index}]")
        observed_ids.append(dimension["id"])
        if dimension["ordinal"] != index + 1 or type(dimension["ordinal"]) is not int:
            raise WorkbenchError(f"dimension[{index}].ordinal drifted")
        for key in ("id", "title", "accelerator", "completion_question", "next_action"):
            _nonempty(dimension[key], f"dimension[{index}].{key}")
        layers = dimension["required_layers"]
        if type(layers) is not list or not layers or len(set(layers)) != len(layers) or any(
                type(value) is not str or not value for value in layers):
            raise WorkbenchError(f"dimension[{index}].required_layers is invalid")
        if dimension["default_lane"] not in {"offline", "static", "live", "bank"}:
            raise WorkbenchError(f"dimension[{index}].default_lane is invalid")
    if observed_ids != list(DIMENSIONS):
        raise WorkbenchError(f"dimension order drifted: {observed_ids}")
    frontier = _exact_keys(policy["frontier_policy"], {
        "required_categories", "allowed_proof_bases",
        "weak_bases_requiring_independent_falsifier", "unknown_is_disjoint",
        "runtime_silence_proves_absence", "strict_compiler_closure_equals_item2",
        "require_scope_statement", "require_image_census",
        "require_counterexample_on_intersection",
    }, "frontier_policy")
    expected_categories = [
        "callers", "callees", "callbacks", "indirect_tables", "overlays",
        "readers", "writers", "downstream_consumers",
    ]
    if frontier["required_categories"] != expected_categories:
        raise WorkbenchError("frontier required-category contract drifted")
    if type(frontier["allowed_proof_bases"]) is not list or not frontier[
            "allowed_proof_bases"]:
        raise WorkbenchError("frontier proof-basis catalog is empty")
    if not set(frontier["weak_bases_requiring_independent_falsifier"]).issubset(
            frontier["allowed_proof_bases"]):
        raise WorkbenchError("weak frontier bases are not a subset of allowed bases")
    expected_flags = {
        "unknown_is_disjoint": False,
        "runtime_silence_proves_absence": False,
        "strict_compiler_closure_equals_item2": False,
        "require_scope_statement": True,
        "require_image_census": True,
        "require_counterexample_on_intersection": True,
    }
    for key, expected in expected_flags.items():
        if frontier[key] is not expected:
            raise WorkbenchError(f"frontier_policy.{key} drifted")
    if type(policy["pilot_rows"]) is not list or not policy["pilot_rows"]:
        raise WorkbenchError("pilot_rows must be a non-empty list")
    pilot_ids: set[str] = set()
    for index, pilot in enumerate(policy["pilot_rows"]):
        _exact_keys(pilot, {"row_id", "dimension", "adapter", "artifacts",
                            "expected_scope"}, f"pilot[{index}]")
        row_id = _nonempty(pilot["row_id"], f"pilot[{index}].row_id")
        if row_id in pilot_ids:
            raise WorkbenchError(f"duplicate pilot row {row_id}")
        pilot_ids.add(row_id)
        if pilot["dimension"] not in DIMENSIONS:
            raise WorkbenchError(f"pilot[{index}].dimension is invalid")
        _nonempty(pilot["adapter"], f"pilot[{index}].adapter")
        _nonempty(pilot["expected_scope"], f"pilot[{index}].expected_scope")
        if type(pilot["artifacts"]) is not list or not pilot["artifacts"]:
            raise WorkbenchError(f"pilot[{index}].artifacts is empty")
        for rel in pilot["artifacts"]:
            if type(rel) is not str or Path(rel).is_absolute() or ".." in Path(rel).parts:
                raise WorkbenchError(f"pilot[{index}] has an unsafe artifact")
    if type(policy["standalone_scorecards"]) is not list:
        raise WorkbenchError("standalone_scorecards must be a list")
    for index, scorecard in enumerate(policy["standalone_scorecards"]):
        _exact_keys(scorecard, {"row_id", "path", "schema_kind"},
                    f"scorecard[{index}]")
        if scorecard["schema_kind"] != "numbered_items":
            raise WorkbenchError(f"scorecard[{index}] has an unsupported schema kind")
    live = _exact_keys(policy["live_escalation"], {
        "required_preconditions", "accepted_reasons", "capsule_is_frame_boundary_only",
        "API_change_requires_contract_gap", "current_contract_surfaces",
    }, "live_escalation")
    if type(live["required_preconditions"]) is not list or not live[
            "required_preconditions"]:
        raise WorkbenchError("live preconditions are empty")
    if type(live["accepted_reasons"]) is not list or not live["accepted_reasons"]:
        raise WorkbenchError("live accepted reasons are empty")
    if live["capsule_is_frame_boundary_only"] is not True or \
            live["API_change_requires_contract_gap"] is not True:
        raise WorkbenchError("live evidence/API authority boundary drifted")
    if policy["authority"] != AUTHORITY:
        raise WorkbenchError("workbench authority differs from the non-promotion contract")
    return policy


def _artifact_paths(campaign: dict[str, Any]) -> list[str]:
    paths: set[str] = set()
    for assertions in (campaign.get("evidence") or {}).values():
        if isinstance(assertions, list):
            for assertion in assertions:
                if isinstance(assertion, dict) and isinstance(assertion.get("artifact"), str):
                    paths.add(assertion["artifact"])
    for claim in (campaign.get("dimension_claims") or {}).values():
        for assertion in (claim or {}).get("evidence") or []:
            if isinstance(assertion, dict) and isinstance(assertion.get("artifact"), str):
                paths.add(assertion["artifact"])
        paths.update(value for value in (claim or {}).get("authoritative_paths") or []
                     if isinstance(value, str))
    return sorted(paths)


def _has_assertions(campaign: dict[str, Any], group: str) -> bool:
    return bool((campaign.get("evidence") or {}).get(group))


def _controls(campaign: dict[str, Any]) -> tuple[bool, bool]:
    controls = campaign.get("controls") or {}
    return bool(controls.get("positive")), bool(controls.get("negative"))


def layer_presence(campaign: dict[str, Any] | None, dimension: str,
                   required_layers: list[str]) -> dict[str, str]:
    """Report declaration presence; this is deliberately not a satisfaction verdict."""
    if campaign is None:
        return {layer: "missing" for layer in required_layers}
    evidence = campaign.get("evidence") or {}
    frontier = campaign.get("frontier") or {}
    lifecycle = campaign.get("lifecycle") or {}
    breadth = campaign.get("breadth") or {}
    source = campaign.get("source_status") or {}
    positive, negative = _controls(campaign)
    claims = campaign.get("dimension_claims") or {}
    claim = claims.get(dimension) or {}
    has_claim_evidence = bool(claim.get("evidence"))
    values: dict[str, bool] = {}
    if dimension == "original_oracle":
        values = {
            "oracle_fixtures": bool(campaign.get("oracle_fixtures")),
            "oracle_assertions": bool(evidence.get("oracle") or has_claim_evidence),
            "positive_control": positive,
            "negative_control": negative,
            "provenance": bool(_artifact_paths(campaign)),
        }
    elif dimension == "complete_frontier":
        values = {
            "scope_universe": bool(campaign.get("scope") and campaign.get("non_scope")),
            "function_roots": bool(frontier.get("functions")),
            "callers_callees": bool(frontier.get("functions") and evidence.get("frontier")),
            "callbacks_indirects": bool(frontier.get("dispatch")),
            "readers_writers": bool(frontier.get("readers") and frontier.get("writers")),
            "overlays_assets": bool(frontier.get("overlays") and frontier.get("assets")),
            "bounded_residuals": isinstance(claim.get("residuals"), list) or
                                 isinstance(campaign.get("bounded_residuals"), list),
        }
    elif dimension == "typed_state":
        text = str(frontier.get("typed_state") or "")
        values = {
            "field_catalog": bool(text), "widths_signedness": bool(text),
            "ownership": bool(text), "domains": bool(text),
            "initialization_reset": bool(lifecycle.get("initialization") and lifecycle.get("reset")),
            "evidence_confidence": bool(evidence.get("frontier") or has_claim_evidence),
        }
    elif dimension == "lifecycle":
        values = {
            "creation": bool(lifecycle.get("initialization")),
            "repeated_use": bool(lifecycle.get("allocation_reuse")),
            "retirement": bool(lifecycle.get("retirement")),
            "death_respawn": bool(lifecycle.get("death_respawn")),
            "pause": bool(lifecycle.get("pause") or "pause" in str(lifecycle).lower()),
            "transition_reload": bool(lifecycle.get("unload_transition") and lifecycle.get("reset")),
            "persistence": bool(lifecycle.get("persistence")),
        }
    elif dimension == "original_interfaces":
        functions = bool(frontier.get("functions"))
        values = {
            "call_return": functions, "live_registers": bool(evidence.get("frontier")),
            "stack_ra": functions, "hi_lo": functions,
            "gte_delay_slots": functions, "memory_effects": bool(frontier.get("readers") and frontier.get("writers")),
            "callback_overlay_asset_abi": bool(frontier.get("dispatch") and frontier.get("overlays") and frontier.get("assets")),
        }
    elif dimension == "campaign_breadth":
        values = {
            "applicability_universe": bool(breadth), "stages": bool(breadth.get("stages")),
            "variants": bool(breadth.get("variants")), "modes": bool(breadth.get("lifecycles")),
            "exceptional_paths": bool(breadth.get("exceptional_paths")),
            "coverage_controls": bool(evidence.get("breadth") and positive and negative),
        }
    elif dimension == "cross_system_behavior":
        dependencies = bool(evidence.get("dependencies"))
        values = {
            "interaction_universe": dependencies,
            "player_physics": dependencies, "render_animation": dependencies,
            "audio_hud": dependencies, "objectives_save": dependencies,
            "transitions": bool(lifecycle.get("unload_transition")),
            "matched_controls": bool(positive and negative and
                                     (evidence.get("controls") or has_claim_evidence)),
        }
    elif dimension == "source_closure":
        values = {
            "source_extent": bool(frontier.get("functions")),
            "asm_identity": bool(source.get("asm")),
            "semantic_or_matching_source": bool(source.get("matching_c") or source.get("semantic_c")),
            "schema_layout": bool(source.get("schemas")),
            "mismatch_ledger": bool(source.get("matching_c") and source.get("semantic_c")),
            "executable_guards": bool(evidence.get("source") or has_claim_evidence),
        }
    elif dimension == "durable_evidence":
        note = str(campaign.get("note") or "")
        values = {
            "canon": any(path.startswith("ObsidianVault/Canon/") for path in _artifact_paths(campaign)),
            "experiments": any(path.startswith("ObsidianVault/Experiments/") for path in _artifact_paths(campaign)) or bool(note),
            "mods_disposition": bool(campaign.get("mods_disposition")),
            "fixture_pins": bool(campaign.get("oracle_fixtures")),
            "regeneration": bool(_artifact_paths(campaign)),
            "executable_guard": bool(campaign.get("findings") or evidence.get("exit_gate") or has_claim_evidence),
            "supersession": bool(campaign.get("findings")),
            "clean_checkout": bool(claim.get("authoritative_paths") or campaign.get("findings")),
        }
    else:  # pragma: no cover - policy validation fixes the universe
        raise KeyError(dimension)
    if set(values) != set(required_layers):
        raise WorkbenchError(f"internal layer mapping drifted for {dimension}")
    return {key: "declared" if values[key] else "missing" for key in required_layers}


def _numbered_scorecard(path: Path, row_id: str) -> dict[str, Any]:
    document = load_json(path)
    if document.get("row_id") != row_id:
        raise WorkbenchError(f"{path.relative_to(ROOT)} row identity drifted")
    items = document.get("items")
    if type(items) is not list or len(items) != 9:
        raise WorkbenchError(f"{path.relative_to(ROOT)} must contain nine scorecard items")
    result: dict[str, Any] = {}
    for index, item in enumerate(items, start=1):
        if type(item) is not dict or item.get("n") != index or item.get("id") != DIMENSIONS[index - 1]:
            raise WorkbenchError(f"{path.relative_to(ROOT)} scorecard order drifted")
        for key in ("requirement", "state", "scope", "established", "missing",
                    "next_experiment"):
            _nonempty(item.get(key), f"{path.relative_to(ROOT)}.items[{index}].{key}")
        if type(item.get("evidence")) is not list:
            raise WorkbenchError(f"{path.relative_to(ROOT)}.items[{index}].evidence is invalid")
        result[item["id"]] = {
            "state": item["state"], "scope": item["scope"],
            "missing": item["missing"], "next_experiment": item["next_experiment"],
            "evidence": item["evidence"],
        }
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path),
            "dimensions": result}


def _residual_errors(rows: Any) -> list[str]:
    if type(rows) is not list:
        return ["residual list is absent"]
    errors = []
    for index, row in enumerate(rows):
        if type(row) is not dict:
            errors.append(f"residual {index} is not an object")
            continue
        for key in ("boundary", "evidence", "next_experiment"):
            if type(row.get(key)) is not str or not row[key].strip():
                errors.append(f"residual {index} lacks {key}")
        intersects = row.get("intersects_dimension", row.get("intersects_behavior"))
        if intersects is not False:
            errors.append(f"residual {index} still intersects the dimension")
    return errors


def _campaign_index(registry: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    campaigns = {row["id"]: row for row in registry.get("child_campaigns") or []}
    row_to_campaign: dict[str, str] = {}
    for campaign_id, campaign in campaigns.items():
        for row_id in campaign.get("rows") or []:
            if row_id in row_to_campaign:
                raise WorkbenchError(f"row {row_id} belongs to multiple child campaigns")
            row_to_campaign[row_id] = campaign_id
    return campaigns, row_to_campaign


def _stable_rows(value: Any, identity: str) -> list[Any]:
    if type(value) is not list:
        return []
    return sorted(value, key=lambda row: (
        str(row.get(identity) or "") if isinstance(row, dict) else str(row),
        json.dumps(row, sort_keys=True) if isinstance(row, (dict, list)) else str(row),
    ))


def _movie_refs(value: Any) -> list[dict[str, Any]]:
    rows = []
    for row in value if isinstance(value, list) else []:
        if not isinstance(row, dict):
            continue
        rows.append({key: row.get(key) for key in (
            "path", "sha256", "bytes", "media_class", "declared_start_state",
            "central_pin_current")})
    return _stable_rows(rows, "path")


def _capsule_refs(value: Any) -> list[dict[str, Any]]:
    rows = []
    for row in value if isinstance(value, list) else []:
        if not isinstance(row, dict):
            continue
        rows.append({
            "movie": row.get("movie"), "movie_sha256": row.get("movie_sha256"),
            "capsule_manifest_sha256": row.get("capsule_manifest_sha256"),
            "capsule_tree_sha256": row.get("capsule_tree_sha256"),
            "control_match": row.get("control_match"), "frames": row.get("frames"),
            "domains": sorted(row.get("domains") or []),
            "start_state": row.get("start_state"),
        })
    return _stable_rows(rows, "movie")


def _claim_index(registry: dict[str, Any], debt_by_row: dict[str, dict[str, Any]],
                 scorecards: dict[str, dict[str, Any]], findings: dict[str, Any]) -> dict[str, Any]:
    campaigns, _ = _campaign_index(registry)
    claims = []
    for campaign_id, campaign in sorted(campaigns.items()):
        for dimension, claim in sorted((campaign.get("dimension_claims") or {}).items()):
            for row_id in campaign.get("rows") or []:
                debt_state = (((debt_by_row.get(row_id) or {}).get("dimensions") or {}).get(
                    dimension) or {}).get("state")
                claims.append({
                    "id": f"campaign:{campaign_id}:{row_id}:{dimension}",
                    "source_kind": "campaign_dimension_claim",
                    "source": str(common.REGISTRY_PATH.relative_to(ROOT)),
                    "campaign_id": campaign_id, "row_id": row_id, "dimension": dimension,
                    "scope": "campaign_row", "claim": claim.get("claim"),
                    "confidence": claim.get("confidence"), "debt_state": debt_state,
                    "assertions": len(claim.get("evidence") or []),
                    "authoritative_paths": sorted(claim.get("authoritative_paths") or []),
                    "residuals": len(claim.get("residuals") or []),
                })
    for row_id, scorecard in sorted(scorecards.items()):
        for dimension, item in scorecard["dimensions"].items():
            claims.append({
                "id": f"scorecard:{row_id}:{dimension}",
                "source_kind": "standalone_scorecard", "source": scorecard["path"],
                "campaign_id": None, "row_id": row_id, "dimension": dimension,
                "scope": item["scope"], "claim": item["state"], "confidence": None,
                "debt_state": (((debt_by_row.get(row_id) or {}).get("dimensions") or {}).get(
                    dimension) or {}).get("state"),
                "assertions": len(item["evidence"]),
                "authoritative_paths": sorted(item["evidence"]), "residuals": None,
            })
    finding_rows = []
    finding_ids: set[str] = set()
    for index, finding in enumerate(findings.get("findings") or []):
        finding_id = _nonempty(finding.get("id"), f"finding[{index}].id")
        if finding_id in finding_ids:
            raise WorkbenchError(f"duplicate finding {finding_id}")
        finding_ids.add(finding_id)
        supersedes = finding.get("supersedes")
        if type(supersedes) is not list:
            raise WorkbenchError(f"finding {finding_id} has no explicit supersession list")
        finding_rows.append({
            "id": finding_id, "confidence": finding.get("confidence"),
            "guard": finding.get("guard"), "machine": sorted(finding.get("machine") or []),
            "knowledge": finding.get("knowledge"),
            "supersedes": supersedes,
            "supersession_statement_sha256": [
                hashlib.sha256(str(value).encode()).hexdigest() for value in supersedes],
        })
    conflicts = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        grouped[(claim["row_id"], claim["dimension"])].append(claim)
    for (row_id, dimension), rows in sorted(grouped.items()):
        states = {row["claim"] for row in rows}
        if len(states) > 1:
            conflicts.append({"row_id": row_id, "dimension": dimension,
                              "claim_ids": [row["id"] for row in rows],
                              "states": sorted(str(value) for value in states)})
    return {
        "claims": sorted(claims, key=lambda row: row["id"]),
        "findings": finding_rows,
        "conflicts": conflicts,
        "counts": {"claims": len(claims), "findings": len(finding_rows),
                   "conflicts": len(conflicts)},
    }


def _pilot_b06(document: dict[str, Any], registered: bool) -> dict[str, Any]:
    errors = []
    if document.get("row_id") != "B06_invincibility" or document.get("dimension") != 2:
        errors.append("pilot identity drifted")
    ledger = document.get("ledger") or {}
    sites = ledger.get("sites")
    if type(sites) is not int or sites < 1 or ledger.get("classified") != sites:
        errors.append("ledger does not classify every candidate site")
    if ledger.get("unexplained") != 0 or ledger.get("sites_without_a_proof") != 0:
        errors.append("ledger retains unexplained or proofless sites")
    errors.extend(_residual_errors(document.get("bounded_residuals")))
    linter = document.get("linter_result") or {}
    if linter.get("rejections") != []:
        errors.append("retained residual linter has rejections")
    ready = not errors
    return {
        "facts": {"candidate_sites": sites, "classified": ledger.get("classified"),
                  "unexplained": ledger.get("unexplained"),
                  "residual_entries": len(document.get("bounded_residuals") or [])},
        "errors": errors,
        "disposition": ("ready_for_fresh_verifier" if ready and registered else
                        "review_ready_but_unregistered" if ready else "not_ready"),
        "dimension_promoted": False,
    }


def _pilot_e16(scorecard: dict[str, Any], residuals: dict[str, Any],
               materialization: dict[str, Any], registered: bool) -> dict[str, Any]:
    errors = []
    item = next((row for row in scorecard.get("items") or [] if row.get("n") == 2), None)
    if not item or item.get("id") != "complete_frontier" or item.get("state") != "met_in_scope":
        errors.append("scorecard does not retain Item 2 as met_in_scope")
    if "whole" not in str((scorecard.get("scope_caveat") or "")).lower() and \
            "sub-area" not in str(scorecard.get("scope_caveat") or "").lower():
        errors.append("scorecard lacks an explicit row-wide scope caveat")
    errors.extend(_residual_errors(residuals.get("bounded_residuals")))
    if (residuals.get("linter_result") or {}).get("rejections") != []:
        errors.append("residual linter has rejections")
    if materialization.get("sites_inside") != 5 or materialization.get("bare_address_takes") != 2 \
            or materialization.get("direct_accesses") != 3:
        errors.append("materialization census drifted from 5 = 2 address takes + 3 accesses")
    ready = not errors
    return {
        "facts": {"scope": item.get("scope") if item else None,
                  "materialization_sites": materialization.get("sites_inside"),
                  "residual_entries": len(residuals.get("bounded_residuals") or []),
                  "row_wide": False},
        "errors": errors,
        "disposition": ("scope_limited_ready_for_fresh_verifier" if ready and registered else
                        "scope_limited_review_ready_but_unregistered" if ready else "not_ready"),
        "dimension_promoted": False,
    }


def _pilot_static(row_id: str, entry: dict[str, Any], registered: bool,
                  debt_state: str | None) -> dict[str, Any]:
    errors = []
    if row_id == "E15_fmv":
        if entry.get("actual") != entry.get("expected"):
            errors.append("benchmark counts differ")
        for key in ("all_cross_joins_verified", "all_instruction_words_verified",
                    "code_hash_verified", "field_domain_verified"):
            if entry.get(key) is not True:
                errors.append(f"{key} is not true")
        if (entry.get("actual") or {}).get("unclassified_xrefs") != 0:
            errors.append("FMV retains unclassified xrefs")
        desired = "ready_for_fresh_verifier"
    elif row_id == "E08_props_movers_gates":
        if entry.get("actual") != entry.get("expected"):
            errors.append("application counts differ")
        callbacks = entry.get("callback_joins") or []
        missing_sources = [row.get("start") for row in callbacks
                           if row.get("source_verified") is not True]
        if missing_sources:
            errors.append(f"callback source verification missing: {missing_sources}")
        if entry.get("program_joins_verified") is not True:
            errors.append("program joins are not verified")
        if (entry.get("frontier") or {}).get("summary", {}).get(
                "unresolved_boundaries", 0):
            errors.append("application frontier retains unresolved boundaries")
        desired = "localization_ready_not_promotion"
    else:
        if entry.get("missing_roots") != []:
            errors.append("static roots are missing")
        if entry.get("slice_hashes_verified") is not True:
            errors.append("slice hashes are not verified")
        if type(entry.get("open_boundaries")) is not list:
            errors.append("open boundaries are not explicit")
        desired = "localization_ready_not_promotion"
    return {
        "facts": {"retained_valid_field": entry.get("valid"),
                  "debt_state": debt_state, "registered": registered},
        "errors": errors,
        "disposition": desired if not errors else "not_ready",
        "dimension_promoted": False,
    }


def _pilot_results(policy: dict[str, Any], row_to_campaign: dict[str, str],
                   debt_by_row: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cache = {str(STATIC_PILOTS_PATH.relative_to(ROOT)): load_json(STATIC_PILOTS_PATH)}
    results = []
    for pilot in policy["pilot_rows"]:
        artifacts = []
        documents = []
        for rel in pilot["artifacts"]:
            path = ROOT / rel
            if not path.is_file():
                raise WorkbenchError(f"pilot artifact is missing: {rel}")
            document = cache.get(rel) or load_json(path)
            cache[rel] = document
            documents.append(document)
            artifacts.append({"path": rel, "sha256": sha256(path)})
        row_id = pilot["row_id"]
        registered = row_id in row_to_campaign
        debt_state = ((((debt_by_row.get(row_id) or {}).get("dimensions") or {}).get(
            pilot["dimension"]) or {}).get("state"))
        if pilot["adapter"] == "b06_residual_ledger":
            evaluated = _pilot_b06(documents[0], registered)
        elif pilot["adapter"] == "e16_scoped_scorecard":
            evaluated = _pilot_e16(documents[0], documents[1], documents[2], registered)
        elif pilot["adapter"] in {"accepted_static_pilot", "e08_static_application",
                                  "c13_static_application"}:
            entry = documents[0].get(row_id)
            if type(entry) is not dict:
                raise WorkbenchError(f"static pilot lacks {row_id}")
            evaluated = _pilot_static(row_id, entry, registered, debt_state)
        else:  # pragma: no cover - policy is repository controlled
            raise WorkbenchError(f"unknown pilot adapter {pilot['adapter']}")
        results.append({
            "row_id": row_id, "dimension": pilot["dimension"],
            "expected_scope": pilot["expected_scope"], "adapter": pilot["adapter"],
            "artifacts": artifacts, **evaluated,
        })
    return results


def _capsule_status(capsules: dict[str, Any]) -> dict[str, Any]:
    rows = capsules.get("capsules")
    errors = []
    if capsules.get("schema") not in {
            "abl-phase4-trace-capsule-set-v1", "abl-phase4-trace-capsule-set-v2"}:
        errors.append("unsupported capsule-set schema")
    if capsules.get("complete") is not True or capsules.get("errors") != []:
        errors.append("capsule set is incomplete or has errors")
    if type(rows) is not list or capsules.get("capsule_count") != len(rows or []):
        errors.append("capsule count differs from rows")
    if any(row.get("control_match") is not True for row in rows or []):
        errors.append("one or more capsule controls do not match")
    comparison = capsules.get("reproducibility_comparison") or {}
    if comparison.get("mismatches") != [] or comparison.get(
            "frame_chunks_byte_identical") is not True:
        errors.append("capsule reproducibility comparison failed")
    return {"schema": capsules.get("schema"), "capsules": len(rows or []),
            "valid": not errors, "errors": errors}


def build() -> dict[str, Any]:
    policy = validate_policy(load_yaml(POLICY_PATH))
    registry = load_yaml(ROOT / common.REGISTRY_PATH)
    mechanics = load_yaml(ROOT / common.BASELINE_PATH)
    debt = load_json(DEBT_PATH)
    queue = load_json(QUEUE_PATH)
    findings = load_yaml(ROOT / common.FINDINGS_PATH)
    capsules = load_json(CAPSULE_SET_PATH)
    fixture_audit = load_json(FIXTURE_AUDIT_PATH)
    inventory = load_json(INVENTORY_PATH)
    if debt.get("valid") is not True or debt.get("errors") != []:
        raise WorkbenchError("retained closure debt is invalid")
    baseline_by_id = common.baseline_rows(mechanics)
    baseline_rows = list(baseline_by_id.values())
    if len(baseline_rows) != 107:
        raise WorkbenchError(f"authoritative baseline row count drifted: {len(baseline_rows)}")
    if debt.get("dimension_order") != list(DIMENSIONS):
        raise WorkbenchError("debt dimension order differs from the roadmap")
    debt_by_row = {row["row_id"]: row for row in debt.get("rows") or []}
    if set(debt_by_row) != set(baseline_by_id):
        raise WorkbenchError("debt and baseline row universes differ")
    campaigns, row_to_campaign = _campaign_index(registry)
    scorecards: dict[str, dict[str, Any]] = {}
    for spec in policy["standalone_scorecards"]:
        scorecards[spec["row_id"]] = _numbered_scorecard(ROOT / spec["path"], spec["row_id"])
    queue_by_row = {row["row_id"]: row for row in queue.get("rows") or []}
    dimensions_by_id = {row["id"]: row for row in policy["dimensions"]}
    rows_output = []
    state_counts = Counter()
    missing_layer_counts = Counter()
    for baseline in baseline_rows:
        row_id = baseline["id"]
        debt_row = debt_by_row[row_id]
        campaign_id = row_to_campaign.get(row_id)
        campaign = campaigns.get(campaign_id) if campaign_id else None
        scorecard = scorecards.get(row_id)
        obligations = []
        for dimension_id in DIMENSIONS:
            dimension = dimensions_by_id[dimension_id]
            retained = (debt_row["dimensions"][dimension_id]).get("state")
            layers = layer_presence(campaign, dimension_id, dimension["required_layers"])
            missing = [key for key, value in layers.items() if value == "missing"]
            for layer in missing:
                missing_layer_counts[f"{dimension_id}:{layer}"] += 1
            standalone = (scorecard or {}).get("dimensions", {}).get(dimension_id)
            if retained in {"met", "not_applicable"}:
                review_state = f"retained_{retained}"
            elif standalone and standalone["state"] in {"met", "met_in_scope"}:
                review_state = "unregistered_scoped_claim"
            elif not missing:
                review_state = "declared_evidence_unpromoted"
            else:
                review_state = "evidence_gaps"
            state_counts[review_state] += 1
            action = standalone["next_experiment"] if standalone and retained not in {
                "met", "not_applicable"} else dimension["next_action"]
            obligations.append({
                "id": dimension_id, "ordinal": dimension["ordinal"],
                "title": dimension["title"], "retained_state": retained,
                "review_state": review_state, "declared_layers": layers,
                "missing_layers": missing, "completion_question": dimension[
                    "completion_question"], "accelerator": dimension["accelerator"],
                "recommended_lane": debt_row.get("next_lane") or dimension["default_lane"],
                "recommended_action": action,
                "standalone_scorecard": standalone,
            })
        queue_row = queue_by_row.get(row_id) or {}
        rows_output.append({
            "row_id": row_id, "name": baseline.get("name"),
            "campaign_id": campaign_id, "campaign_registered": campaign is not None,
            "completion_state": debt_row.get("completion_state"),
            "retained_counts": debt_row.get("counts"),
            "retained_evidence_artifacts": _artifact_paths(campaign or {}),
            "capsule_opportunity": {
                "classification": queue_row.get("classification"),
                "movies": _movie_refs(queue_row.get("relevant_movies")),
                "capsules": _capsule_refs(queue_row.get("relevant_capsules")),
                "available_domains": sorted(queue_row.get("available_domains") or []),
                "prior_offline_analysis": _stable_rows(
                    queue_row.get("prior_offline_analysis"), "artifact"),
            },
            "obligations": obligations,
        })
    pilot_results = _pilot_results(policy, row_to_campaign, debt_by_row)
    claim_index = _claim_index(registry, debt_by_row, scorecards, findings)
    fixture_status = _retained_receipt_status(fixture_audit, {
        "mechanics_sha256": common.BASELINE_PATH,
        "fixture_set_sha256": common.FIXTURE_SET_PATH,
        "phase2_row_coverage_sha256": PHASE2_COVERAGE_PATH,
    })
    inventory_status = _retained_receipt_status(inventory, {
        "mechanics_sha256": common.BASELINE_PATH,
        "campaign_registry_sha256": common.REGISTRY_PATH,
        "inventory_declaration_sha256": common.INVENTORY_CONFIG_PATH,
        "phase3_ownership_sha256": PHASE3_OWNERSHIP_PATH,
        "function_census_sha256": FUNCTION_CENSUS_PATH,
    })
    errors = []
    if claim_index["conflicts"]:
        errors.append("claim index has campaign/standalone state conflicts requiring review")
    capsule_status = _capsule_status(capsules)
    if not capsule_status["valid"]:
        errors.append("retained capsule set is invalid")
    if not fixture_status["ready"]:
        errors.append("retained fixture audit is stale or structurally open")
    if not inventory_status["ready"]:
        errors.append("retained campaign inventory is stale or structurally open")
    return {
        "schema": OUTPUT_SCHEMA,
        "inputs": {
            str(path.relative_to(ROOT)): sha256(path) for path in (
                POLICY_PATH, ROOT / common.BASELINE_PATH, ROOT / common.REGISTRY_PATH,
                ROOT / common.FINDINGS_PATH, DEBT_PATH, STATIC_PILOTS_PATH,
                CAPSULE_SET_PATH, QUEUE_PATH, FIXTURE_AUDIT_PATH, INVENTORY_PATH,
                Path(__file__),
            )
        },
        "authority": AUTHORITY,
        "dimensions": policy["dimensions"],
        "rows": rows_output,
        "pilots": pilot_results,
        "claim_index": claim_index,
        "shared_services": {
            "capsules": capsule_status,
            "fixture_audit_valid": fixture_status["ready"],
            "inventory_structural_ready": inventory_status["ready"],
            "retained_receipts": {
                "fixture_audit": fixture_status,
                "campaign_inventory": inventory_status,
            },
            "frontier_policy": policy["frontier_policy"],
            "live_escalation": policy["live_escalation"],
        },
        "summary": {
            "baseline_rows": len(rows_output), "dimensions_per_row": 9,
            "obligations": len(rows_output) * 9,
            "registered_rows": sum(row["campaign_registered"] for row in rows_output),
            "unregistered_rows": sum(not row["campaign_registered"] for row in rows_output),
            "review_states": dict(sorted(state_counts.items())),
            "missing_layer_occurrences": sum(missing_layer_counts.values()),
            "pilot_dispositions": dict(sorted(Counter(
                row["disposition"] for row in pilot_results).items())),
        },
        "errors": errors,
        "valid": not errors,
    }


def row_packet(report: dict[str, Any], row_id: str,
               dimension: str | None = None) -> dict[str, Any]:
    row = next((value for value in report["rows"] if value["row_id"] == row_id), None)
    if row is None:
        raise WorkbenchError(f"unknown Phase-4 row {row_id!r}")
    obligations = row["obligations"]
    if dimension is not None:
        if dimension not in DIMENSIONS:
            raise WorkbenchError(f"unknown dimension {dimension!r}")
        obligations = [value for value in obligations if value["id"] == dimension]
    pilots = [value for value in report["pilots"] if value["row_id"] == row_id and
              (dimension is None or value["dimension"] == dimension)]
    return {
        "schema": "abl-phase4-work-packet/1", "row_id": row_id,
        "campaign_id": row["campaign_id"], "campaign_registered": row[
            "campaign_registered"], "completion_state": row["completion_state"],
        "capsule_opportunity": row["capsule_opportunity"],
        "retained_evidence_artifacts": row["retained_evidence_artifacts"],
        "obligations": obligations, "pilots": pilots,
        "authority": AUTHORITY,
    }


def live_plan(report: dict[str, Any], row_id: str, dimension: str,
              reason: str, missing_domain: str, positive_control: str,
              negative_control: str, api_contract_gap: str | None) -> dict[str, Any]:
    packet = row_packet(report, row_id, dimension)
    policy = report["shared_services"]["live_escalation"]
    errors = []
    if reason not in policy["accepted_reasons"]:
        errors.append("LIVE_REASON_INVALID")
    if not missing_domain.strip():
        errors.append("MISSING_DOMAIN_UNNAMED")
    if not positive_control.strip() or not negative_control.strip():
        errors.append("MATCHED_CONTROLS_MISSING")
    capsules = report["shared_services"]["capsules"]
    if not capsules["valid"]:
        errors.append("CAPSULE_SET_INVALID")
    opportunity = packet["capsule_opportunity"]
    relevant = opportunity["capsules"] or opportunity["movies"]
    if not relevant and reason != "missing_or_invalid_capsule":
        errors.append("RELEVANT_CAPSULE_QUERY_MISSING")
    prior = opportunity["prior_offline_analysis"]
    if relevant and not prior and reason not in {"missing_domain", "missing_or_invalid_capsule"}:
        errors.append("OFFLINE_QUERY_NOT_CONSUMED")
    if api_contract_gap:
        if api_contract_gap in policy["current_contract_surfaces"]:
            errors.append("API_SURFACE_ALREADY_AVAILABLE")
    return {
        "schema": "abl-phase4-live-preflight/1", "row_id": row_id,
        "dimension": dimension, "reason": reason, "named_missing_domain": missing_domain,
        "positive_control": positive_control, "negative_control": negative_control,
        "capsule_query": {"relevant": relevant, "prior_offline_analysis": prior,
                          "available_domains": opportunity["available_domains"]},
        "current_debugger_contract": policy["current_contract_surfaces"],
        "api_contract_gap": api_contract_gap,
        "duckstation_api_change_allowed": bool(api_contract_gap and not errors),
        "ready_for_isolated_live_design": not errors,
        "errors": errors,
        "authority": {**AUTHORITY, "launches_emulator": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    sub.add_parser("check")
    packet_parser = sub.add_parser("packet")
    packet_parser.add_argument("--row", required=True)
    packet_parser.add_argument("--dimension", choices=DIMENSIONS)
    live_parser = sub.add_parser("prepare-live")
    live_parser.add_argument("--row", required=True)
    live_parser.add_argument("--dimension", choices=DIMENSIONS, required=True)
    live_parser.add_argument("--reason", required=True)
    live_parser.add_argument("--missing-domain", required=True)
    live_parser.add_argument("--positive-control", required=True)
    live_parser.add_argument("--negative-control", required=True)
    live_parser.add_argument("--api-contract-gap")
    args = parser.parse_args()
    report = build()
    payload = canonical_json(report)
    if args.command == "build":
        output = args.output.resolve(strict=False)
        try:
            output.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise WorkbenchError("retained workbench output must stay inside repository") from exc
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
        print(f"[phase4-workbench] wrote {output.relative_to(ROOT)}")
        return 0
    if args.command == "check":
        if OUTPUT_PATH.read_bytes() != payload:
            raise WorkbenchError("retained closure workbench is stale")
        if not report["valid"]:
            raise WorkbenchError(
                "retained closure workbench is fresh but reports integration errors")
        print("[phase4-workbench] retained report is fresh")
        return 0
    if args.command == "packet":
        print(canonical_json(row_packet(report, args.row, args.dimension)).decode(), end="")
        return 0
    plan = live_plan(report, args.row, args.dimension, args.reason,
                     args.missing_domain, args.positive_control,
                     args.negative_control, args.api_contract_gap)
    print(canonical_json(plan).decode(), end="")
    return 0 if plan["ready_for_isolated_live_design"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (WorkbenchError, OSError) as exc:
        raise SystemExit(f"[phase4-workbench] ERROR: {exc}") from exc
