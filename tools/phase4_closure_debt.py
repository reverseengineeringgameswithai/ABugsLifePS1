#!/usr/bin/env python3
"""Derive Phase-4 closure debt and the next evidence lane for all 107 rows."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

import phase4_common as common


POLICY_PATH = common.ROOT / "config/phase4_closure_policy.yaml"
QUEUE_PATH = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
COVERAGE_PATH = common.ROOT / "analysis/phase4_coverage_matrix.json"
OUTPUT = common.ROOT / "analysis/phase4_closure_debt.json"
MOVIE_PRIORITY_PATH = common.ROOT / "analysis/phase4_movie_priority_queue.json"
CLAIM_STATES = {"met", "partial", "gap", "not_applicable"}


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = json.loads(OUTPUT.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def _tracked_paths(paths: list[str]) -> list[str]:
    errors: list[str] = []
    for rel in paths:
        path = common.ROOT / str(rel)
        if Path(str(rel)).is_absolute() or ".." in Path(str(rel)).parts:
            errors.append(f"unsafe authoritative path: {rel!r}")
        elif not path.is_file() or not common.git_tracked(str(rel)):
            errors.append(f"authoritative path missing or untracked: {rel}")
    return errors


def _claim_errors(campaign: dict, dimension: dict) -> tuple[list[str], bool]:
    """Validate an optional explicit dimension promotion.

    A promotion is not trusted merely because ``claim: met`` exists. It must
    carry fresh low-level assertions, tracked machine paths, confidence, and an
    explicit residual list. Completed campaigns remain governed by the stricter
    whole-campaign audit in phase4_common.audit_campaign().
    """
    claims = campaign.get("dimension_claims") or {}
    claim = claims.get(dimension["id"])
    if claim is None:
        return [], False
    errors: list[str] = []
    state = claim.get("claim")
    if state not in CLAIM_STATES:
        errors.append(f"invalid claim state {state!r}")
    if state in {"met", "not_applicable"}:
        assertions = claim.get("evidence") or []
        if not assertions:
            errors.append(f"{state} claim has no low-level evidence")
        for assertion in assertions:
            errors.extend(common.audit_assertion(assertion))
        paths = claim.get("authoritative_paths") or []
        if not paths:
            errors.append(f"{state} claim has no authoritative machine path")
        errors.extend(_tracked_paths(paths))
        allowed_confidence = {"confirmed"} if state == "not_applicable" \
            else {"confirmed", "partial"}
        if claim.get("confidence") not in allowed_confidence:
            errors.append(f"{state} claim lacks acceptable confidence")
        if not isinstance(claim.get("residuals"), list):
            errors.append(f"{state} claim lacks an explicit residual list")
        for residual in claim.get("residuals") or []:
            if residual.get("intersects_dimension") is not False:
                errors.append("met claim retains a residual intersecting the dimension")
            if not all(str(residual.get(key) or "").strip()
                       for key in ("boundary", "evidence", "next_experiment")):
                errors.append("met claim has a malformed residual")
    return errors, True


def _evidence_group(campaign: dict, group: str) -> tuple[bool, list[str]]:
    assertions = (campaign.get("evidence") or {}).get(group) or []
    errors: list[str] = []
    for assertion in assertions:
        errors.extend(common.audit_assertion(assertion))
    return bool(assertions), errors


def _structural_presence(campaign: dict, dimension_id: str) -> bool:
    evidence = campaign.get("evidence") or {}
    frontier = campaign.get("frontier") or {}
    lifecycle = campaign.get("lifecycle") or {}
    breadth = campaign.get("breadth") or {}
    source = campaign.get("source_status") or {}
    controls = campaign.get("controls") or {}
    if dimension_id == "original_oracle":
        return bool(campaign.get("oracle_fixtures") and evidence.get("oracle"))
    if dimension_id == "complete_frontier":
        return bool(frontier and evidence.get("frontier"))
    if dimension_id == "typed_state":
        return bool(frontier.get("typed_state") and evidence.get("frontier"))
    if dimension_id == "lifecycle":
        return bool(lifecycle and evidence.get("lifecycle"))
    if dimension_id == "original_interfaces":
        return bool(frontier.get("functions") and frontier.get("readers")
                    and frontier.get("writers"))
    if dimension_id == "campaign_breadth":
        return bool(breadth and evidence.get("breadth"))
    if dimension_id == "cross_system_behavior":
        return bool(controls.get("positive") and controls.get("negative")
                    and (evidence.get("controls") or evidence.get("dependencies")))
    if dimension_id == "source_closure":
        return bool(source and evidence.get("source"))
    if dimension_id == "durable_evidence":
        return bool(campaign.get("findings") or evidence.get("exit_gate"))
    raise KeyError(dimension_id)


def _dimension_state(campaign: dict | None, dimension: dict,
                     completed: bool, reviewed_absent: bool) -> dict:
    if completed or reviewed_absent:
        return {
            "state": "met",
            "basis": "whole-campaign low-level audit" if completed
                     else "reviewed-absence low-level audit",
            "errors": [],
        }
    if campaign is None:
        return {"state": "gap", "basis": "no active child campaign", "errors": []}
    claim_errors, has_claim = _claim_errors(campaign, dimension)
    claim = (campaign.get("dimension_claims") or {}).get(dimension["id"]) or {}
    if has_claim and claim.get("claim") == "met" and not claim_errors:
        return {"state": "met", "basis": "audited dimension promotion", "errors": []}
    if has_claim and claim.get("claim") == "not_applicable" and not claim_errors:
        return {
            "state": "not_applicable",
            "basis": "audited dimension non-applicability",
            "errors": [],
        }
    groups = dimension.get("evidence_groups") or []
    evidence_present = False
    evidence_errors: list[str] = []
    for group in groups:
        present, errors = _evidence_group(campaign, group)
        evidence_present |= present
        evidence_errors.extend(errors)
    partial = _structural_presence(campaign, dimension["id"]) or evidence_present
    errors = claim_errors + evidence_errors
    return {
        "state": "partial" if partial else "gap",
        "basis": "retained evidence exists but no audited promotion"
                 if partial else "required evidence is absent",
        "errors": sorted(set(errors)),
    }


def _next_action(row: dict, campaign: dict | None) -> str:
    for residual in (campaign or {}).get("bounded_residuals") or []:
        if residual.get("intersects_behavior") is not False:
            text = str(residual.get("next_experiment") or "").strip()
            if text:
                return text
    return str(row.get("next") or row.get("missing") or
               "Create a scoped child campaign and bind its first static frontier.").strip()


def _lane_override(campaign: dict | None) -> tuple[dict | None, list[str]]:
    override = (campaign or {}).get("next_lane_override")
    if override is None:
        return None, []
    errors: list[str] = []
    if not isinstance(override, dict):
        return None, ["next-lane override is not a mapping"]
    if override.get("lane") not in {"offline", "static", "live", "bank"}:
        errors.append("next-lane override has an invalid lane")
    if len(str(override.get("reason") or "").strip()) < 30:
        errors.append("next-lane override reason is too generic")
    assertions = override.get("evidence") or []
    if not assertions:
        errors.append("next-lane override has no low-level evidence")
    for assertion in assertions:
        errors.extend(common.audit_assertion(assertion))
    paths = override.get("authoritative_paths") or []
    if not paths:
        errors.append("next-lane override has no authoritative machine paths")
    errors.extend(_tracked_paths(paths))
    return override, sorted(set(errors))


def _next_lane(dimensions: dict[str, dict], queue_row: dict,
               campaign: dict | None) -> tuple[str, str]:
    override, override_errors = _lane_override(campaign)
    if override is not None and not override_errors:
        return override["lane"], str(override["reason"]).strip()
    open_dimensions = [key for key, value in dimensions.items()
                       if value["state"] not in {"met", "not_applicable"}]
    if not open_dimensions:
        return "bank", "all nine dimensions are promoted; reconcile and bank closure"
    if open_dimensions == ["durable_evidence"]:
        return "bank", "only durable knowledge/guard closure remains"
    first = open_dimensions[0]
    static_dimensions = {"complete_frontier", "typed_state", "source_closure"}
    if first in static_dimensions:
        return "static", f"{first} requires source/xref/schema closure before replay"
    prior_offline = bool(queue_row.get("prior_offline_analysis"))
    has_capsule = bool(queue_row.get("relevant_capsules"))
    has_movie = bool(queue_row.get("relevant_movies"))
    if first == "original_oracle" and has_capsule and not prior_offline:
        return "offline", "retained frame domains can establish the first oracle window"
    if first in {"lifecycle", "campaign_breadth", "cross_system_behavior"}:
        if has_capsule and not prior_offline:
            return "offline", f"retained capsules have not yet been consumed for {first}"
        if has_movie or has_capsule:
            return "live", f"offline evidence is consumed; {first} needs a named causal/control gap"
    if first == "original_interfaces":
        return "live", "frontier is present; interface attribution requires a bounded live control"
    if first == "durable_evidence":
        return "bank", "machine and evidence layers exist; finish reusable knowledge closure"
    if campaign is None:
        return "static", "no campaign exists; begin with the static semantic frontier"
    return "static", f"resolve {first} from source before authorizing more live work"


def build(registry: dict | None = None, mechanics: dict | None = None,
          findings: dict | None = None, coverage: dict | None = None,
          queue: dict | None = None, policy: dict | None = None) -> dict:
    registry = registry or common.load_yaml(common.REGISTRY_PATH)
    mechanics = mechanics or common.load_yaml(common.BASELINE_PATH)
    findings = findings or common.load_yaml(common.FINDINGS_PATH)
    coverage = coverage or common.load_json(COVERAGE_PATH)
    queue = queue or common.load_json(QUEUE_PATH)
    policy = policy or common.load_yaml(POLICY_PATH)
    errors = common.validate_registry(registry, mechanics)
    if policy.get("schema") != "abl-phase4-closure-policy/1":
        errors.append("closure policy schema is invalid")
    dimensions_cfg = policy.get("dimensions") or []
    dimension_ids = [row.get("id") for row in dimensions_cfg]
    expected_ids = [
        "original_oracle", "complete_frontier", "typed_state", "lifecycle",
        "original_interfaces", "campaign_breadth", "cross_system_behavior",
        "source_closure", "durable_evidence",
    ]
    if dimension_ids != expected_ids:
        errors.append(f"roadmap dimension order differs: {dimension_ids}")
    rows = common.baseline_rows(mechanics)
    queue_rows = {row["row_id"]: row for row in queue.get("rows") or []}
    coverage_rows = coverage.get("rows") or {}
    campaigns_by_row: dict[str, list[dict]] = defaultdict(list)
    for campaign in registry.get("child_campaigns") or []:
        _, override_errors = _lane_override(campaign)
        errors.extend(
            f"{campaign.get('id', '<missing>')}: {error}"
            for error in override_errors)
        for row_id in campaign.get("rows") or []:
            campaigns_by_row[row_id].append(campaign)
    if set(queue_rows) != set(rows):
        errors.append("offline queue does not contain exactly the current baseline rows")
    if set(coverage_rows) != set(rows):
        errors.append("coverage matrix does not contain exactly the current baseline rows")

    priority_order = common.load_json(
        common.ROOT / "analysis/phase4_priority.json")["priority_order"]
    family_order = {family_id: index for index, family_id in enumerate(priority_order)}
    family_tier = {
        family["id"]: int(family["priority_tier"])
        for family in registry.get("families") or []
    }
    focus = {campaign_id: index for index, campaign_id in enumerate(
        policy.get("active_campaign_focus") or [])}
    output_rows: list[dict] = []
    campaign_rollup: dict[str, dict] = {}
    for row_id, row in rows.items():
        owned_campaigns = campaigns_by_row.get(row_id, [])
        if len(owned_campaigns) > 1:
            errors.append(f"{row_id}: multiple child campaigns own the row")
        campaign = owned_campaigns[0] if owned_campaigns else None
        coverage_row = coverage_rows.get(row_id, {})
        completed = coverage_row.get("state") == "campaign_complete"
        absent = coverage_row.get("state") == "reviewed_absent"
        dimension_states = {
            dimension["id"]: _dimension_state(
                campaign, dimension, completed, absent)
            for dimension in dimensions_cfg
        }
        queue_row = queue_rows.get(row_id, {})
        lane, lane_reason = _next_lane(dimension_states, queue_row, campaign)
        unmet = [key for key, value in dimension_states.items()
                 if value["state"] not in {"met", "not_applicable"}]
        output_rows.append({
            "row_id": row_id,
            "name": row.get("name"),
            "family": coverage_row.get("family"),
            "campaign_id": campaign.get("id") if campaign else None,
            "completion_state": coverage_row.get("state"),
            "dimensions": dimension_states,
            "counts": {
                "met": sum(value["state"] == "met" for value in dimension_states.values()),
                "not_applicable": sum(value["state"] == "not_applicable"
                                      for value in dimension_states.values()),
                "remaining": len(unmet),
            },
            "next_lane": lane,
            "next_lane_reason": lane_reason,
            "next_action": _next_action(row, campaign),
            "capsule_count": len(queue_row.get("relevant_capsules") or []),
            "prior_offline_analysis_count": len(queue_row.get("prior_offline_analysis") or []),
            "movie_count": len(queue_row.get("relevant_movies") or []),
            "dependency_unlock_count": len(
                (queue_row.get("dependencies") or {}).get("dependent_families") or []),
        })
        if campaign:
            rollup = campaign_rollup.setdefault(campaign["id"], {
                "campaign_id": campaign["id"],
                "family": campaign.get("family"),
                "rows": [],
                "dimension_states": {key: [] for key in expected_ids},
            })
            rollup["rows"].append(row_id)
            for key, value in dimension_states.items():
                rollup["dimension_states"][key].append(value["state"])

    campaign_rows: list[dict] = []
    for campaign_id, rollup in campaign_rollup.items():
        states = {
            key: "met" if all(value in {"met", "not_applicable"} for value in values)
            else "partial" if any(value in {"met", "partial"} for value in values)
            else "gap"
            for key, values in rollup.pop("dimension_states").items()
        }
        remaining = sum(value != "met" for value in states.values())
        family = rollup["family"]
        queue_members = [row for row in output_rows if row["campaign_id"] == campaign_id]
        campaign_rows.append({
            **rollup,
            "dimensions": states,
            "counts": {"met": 9 - remaining, "remaining": remaining},
            "next_lane": queue_members[0]["next_lane"],
            "next_action": queue_members[0]["next_action"],
            "dependency_unlock_count": max(
                (row["dependency_unlock_count"] for row in queue_members), default=0),
            "selection_key": {
                "dependency_tier": family_tier.get(family, 99),
                "dependency_order": family_order.get(family, 99),
                "focus_order": focus.get(campaign_id, 999),
                "remaining_dimensions": remaining,
            },
        })
    active_campaigns = [row for row in campaign_rows if row["counts"]["remaining"]]
    active_campaigns.sort(key=lambda row: (
        row["selection_key"]["dependency_tier"],
        row["selection_key"]["focus_order"],
        row["selection_key"]["dependency_order"],
        row["counts"]["remaining"],
        -row["dependency_unlock_count"],
        row["campaign_id"],
    ))
    selected = active_campaigns[:int(policy.get("max_active_campaigns", 1))]
    if any(len(row["rows"]) > int(policy.get("max_rows_per_iteration", 3))
           for row in selected):
        errors.append("selected campaign exceeds the Phase-4 row WIP limit")
    dimension_counts = Counter(
        value["state"] for row in output_rows for value in row["dimensions"].values())
    lane_counts = Counter(row["next_lane"] for row in output_rows
                          if row["completion_state"] == "open")
    return {
        "_comment": "Generated Phase-4 closure debt. A dimension is met only by a fully audited campaign/absence proof or an explicit promotion backed by low-level assertions and tracked machine paths.",
        "schema": "abl-phase4-closure-debt/1",
        "generated": stable_generated(),
        "inputs": {
            "generator_sha256": common.sha256(Path(__file__)),
            "common_helper_sha256": common.sha256(common.ROOT / "tools/phase4_common.py"),
            "policy_sha256": common.sha256(POLICY_PATH),
            "mechanics_sha256": common.sha256(common.BASELINE_PATH),
            "campaign_registry_sha256": common.sha256(common.REGISTRY_PATH),
            "findings_sha256": common.sha256(common.FINDINGS_PATH),
            "coverage_sha256": common.sha256(COVERAGE_PATH),
            "offline_queue_sha256": common.sha256(QUEUE_PATH),
        },
        "dimension_order": expected_ids,
        "rows": output_rows,
        "campaigns": sorted(campaign_rows, key=lambda row: row["campaign_id"]),
        "scheduler": {
            "wip_limits": {
                "campaigns": int(policy.get("max_active_campaigns", 1)),
                "rows": int(policy.get("max_rows_per_iteration", 3)),
            },
            "stagnation_limit": int(policy.get("stagnation_limit", 2)),
            "campaign_verifier_interval": int(policy.get("campaign_verifier_interval", 3)),
            "selected_campaigns": selected,
        },
        "counts": {
            "rows": len(output_rows),
            "complete_rows": sum(row["completion_state"] in {
                "campaign_complete", "reviewed_absent"} for row in output_rows),
            "open_rows": sum(row["completion_state"] == "open" for row in output_rows),
            "dimensions": dict(sorted(dimension_counts.items())),
            "open_next_lanes": dict(sorted(lane_counts.items())),
        },
        "errors": sorted(set(errors + [
            error for row in output_rows for dimension in row["dimensions"].values()
            for error in dimension["errors"]
        ])),
        "valid": not errors and not any(
            dimension["errors"] for row in output_rows
            for dimension in row["dimensions"].values()),
    }


def apply_movie_ready_selection(document: dict, batch_id: str,
                                selected_rows: list[str],
                                priority: dict | None = None,
                                continuation: bool = False) -> dict:
    """Replace only the transient scheduler choice with a valid movie-ready batch.

    The row/dimension debt remains byte-for-byte derived by :func:`build`.
    Runtime debt snapshots use this projection so the existing method-metrics
    scope validator can enforce the alternate work order without treating the
    movie queue as a closure oracle.
    """
    priority = priority or common.load_json(MOVIE_PRIORITY_PATH)
    result = json.loads(json.dumps(document))
    errors = list(result.get("errors") or [])
    if priority.get("schema") != "abl-phase4-movie-priority-queue/2" or \
            priority.get("valid") is not True or priority.get("errors"):
        errors.append("movie-ready priority queue is invalid")
    batches = {
        row.get("batch_id"): row
        for row in priority.get("candidate_batches") or []
    }
    batch = batches.get(batch_id)
    exact_batch_id = "movie-ready:" + "+".join(selected_rows)
    if batch is None:
        if not continuation:
            errors.append(f"movie-ready batch is not current: {batch_id}")
    elif batch.get("rows") != selected_rows:
        errors.append("movie-ready selected rows differ from the named batch")
    if batch_id != exact_batch_id:
        errors.append("movie-ready batch ID does not exactly encode its rows")
    if not selected_rows or len(selected_rows) > 3 or \
            len(selected_rows) != len(set(selected_rows)):
        errors.append("movie-ready batch violates the one-to-three-row WIP limit")
    by_row = {row["row_id"]: row for row in result.get("rows") or []}
    members = [by_row.get(row_id) for row_id in selected_rows]
    if any(row is None for row in members):
        errors.append("movie-ready batch names an unknown closure-debt row")
    for row in members:
        if not continuation and row is not None and \
                int((row.get("counts") or {}).get("remaining") or 0) <= 0:
            errors.append(
                f"movie-ready batch re-entered zero-debt row {row['row_id']}")
    if not errors:
        dimension_states: dict[str, str] = {}
        for dimension in result["dimension_order"]:
            states = [row["dimensions"][dimension]["state"] for row in members]
            dimension_states[dimension] = (
                "met" if all(state in {"met", "not_applicable"} for state in states)
                else "partial" if any(state in {"met", "partial"} for state in states)
                else "gap"
            )
        remaining = sum(state != "met" for state in dimension_states.values())
        result["scheduler"]["selected_campaigns"] = [{
            "campaign_id": batch_id,
            "family": "movie_ready_work_order",
            "rows": list(selected_rows),
            "dimensions": dimension_states,
            "counts": {"met": 9 - remaining, "remaining": remaining},
            "next_lane": members[0]["next_lane"],
            "next_action": (
                ("Measure the just-completed generated movie-ready packet only; "
                 "this continuation is not a new work selection."
                 if continuation else
                 "Execute the exact generated movie-ready packet; movie anchors "
                 "localize work but do not prove closure.")),
            "dependency_unlock_count": max(
                int(row.get("dependency_unlock_count") or 0) for row in members),
            "selection_key": {
                "movie_ready_batch_rank": (
                    batch.get("rank") if batch is not None else None),
                "movie_ready_score_total": (
                    batch.get("score_total") if batch is not None else None),
            },
        }]
        result["inputs"]["movie_priority_queue_sha256"] = common.sha256(
            MOVIE_PRIORITY_PATH)
    result["errors"] = sorted(set(errors))
    result["valid"] = result.get("valid") is True and not errors
    return result


def render(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--snapshot", type=Path,
                        help="write a transient computed snapshot outside the tracked tree")
    parser.add_argument(
        "--selection-policy",
        choices=("closure-debt", "movie-ready"),
        default="closure-debt",
        help="scheduler projection; tracked artifact keeps closure-debt default",
    )
    parser.add_argument("--selected-batch-id")
    parser.add_argument("--selected-row", action="append", default=[])
    parser.add_argument(
        "--selection-continuation", action="store_true",
        help=(
            "reproduce the just-completed packet for debt-after measurement "
            "even if current debt made that prior batch ineligible"),
    )
    args = parser.parse_args()
    document = build()
    if args.selection_policy == "movie-ready":
        if not args.selected_batch_id or not args.selected_row:
            print(
                "ERROR: movie-ready selection requires --selected-batch-id "
                "and --selected-row", file=sys.stderr)
            return 2
        document = apply_movie_ready_selection(
            document, args.selected_batch_id, args.selected_row,
            continuation=args.selection_continuation)
    elif args.selected_batch_id or args.selected_row or \
            args.selection_continuation:
        print(
            "ERROR: selected movie-ready batch arguments require "
            "--selection-policy movie-ready", file=sys.stderr)
        return 2
    text = render(document)
    if document["errors"]:
        for error in document["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.snapshot:
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(text)
    elif args.write:
        OUTPUT.write_text(text)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != text:
            print("phase4 closure-debt artifact is missing or stale", file=sys.stderr)
            return 1
    else:
        print(text, end="")
    selected = document["scheduler"]["selected_campaigns"]
    target = selected[0]["campaign_id"] if selected else "none"
    print(
        f"PASS: rows={document['counts']['complete_rows']}/{document['counts']['rows']} "
        f"dimension_met={document['counts']['dimensions'].get('met', 0)} "
        f"selected={target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
