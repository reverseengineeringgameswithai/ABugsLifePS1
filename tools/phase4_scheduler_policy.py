#!/usr/bin/env python3
"""Reviewed Phase-4 cooldown, expected-value, and fixture-cover policy."""

from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any
import zlib

import phase4_common as common


POLICY_PATH = common.ROOT / "config/phase4_scheduler_policy.yaml"
SCHEMA = "abl-phase4-scheduler-policy/1"
PACKET_SCHEMA = "abl-phase4-movie-ready-packet/4"
PROGRESS_SCHEMA = "abl-ratchet-phase4-progress/2"
HEX64 = set("0123456789abcdef")
EXPECTED_TOP_LEVEL = (
    "schema", "description", "cooldown", "expected_value", "fixture_cover",
    "authority",
)
EXPECTED_COOLDOWN = (
    "consecutive_no_reduction_threshold", "rotate_after_first_no_reduction",
    "scope", "release", "exhaustion", "max_retained_attempts",
)
EXPECTED_BENEFITS = (
    "dependency_unlock", "candidate_reducible_dimension",
    "retained_evidence_point", "static_readiness_point",
    "control_readiness_point", "bounded_frontier_point",
)
EXPECTED_COSTS = ("remaining_dimension", "prior_no_reduction_overlap")
EXPECTED_LANES = ("offline", "static", "live", "unknown")
EXPECTED_DIMENSIONS = (
    "original_oracle", "typed_state", "original_interfaces", "lifecycle",
    "cross_system_behavior", "campaign_breadth", "complete_frontier",
    "source_closure", "durable_evidence",
)
EXPECTED_READINESS = {
    "static": ("typed_state", "original_interfaces", "complete_frontier",
               "source_closure"),
    "offline": ("original_oracle", "lifecycle", "cross_system_behavior",
                "campaign_breadth"),
    "durability": ("durable_evidence",),
}
EXPECTED_REQUIREMENT_WEIGHTS = (
    "row", "family", "domain", "independent_control",
)
EXPECTED_AUTHORITY = (
    "ranking_only", "authored_success_forbidden", "closure_promotion_forbidden",
    "live_authorization_forbidden", "deterministic_ties_by_identifier",
)
ATTEMPT_CORE_KEYS = (
    "previous_attempt_sha256", "packet_sha256", "progress_sha256",
    "debt_before_sha256", "debt_after_sha256", "iteration", "batch_id",
    "rows", "debt_reduced", "row_transition_count",
    "dimension_transition_count", "evidence_sha256",
)
ATTEMPT_KEYS = ATTEMPT_CORE_KEYS + ("attempt_sha256",)
ATTEMPT_EVIDENCE_KEYS = (
    "queue_zlib_base64", "progress", "debt_before_zlib_base64",
    "debt_after_zlib_base64",
)
GENESIS_SHA256 = "0" * 64
DEBT_SCHEMA = "abl-phase4-closure-debt/1"
COMPLETE_ROW_STATES = {"campaign_complete", "reviewed_absent"}
OPEN_ROW_STATES = {"open"}
DIMENSION_STATES = {"gap", "partial", "met"}
QUEUE_ROW_KEYS = {
    "campaign_id", "capsule_availability",
    "completion_state_informational_only", "dependency_unlock_count",
    "derived_indexes", "derived_remaining", "dimension_states", "eligibility",
    "expected_value", "family", "frontier_blocker_domains", "movie_anchors",
    "name", "next_action", "next_lane", "prior_offline_analysis", "rank",
    "reported_remaining_informational_only", "row_id", "score", "selection",
    "static_ownership",
}
BATCH_KEYS = {
    "rank", "batch_id", "rows", "score_total", "coupling", "rationale",
    "expected_value", "fixture_cover",
}
QUEUE_INPUT_KEYS = {
    "generator_sha256", "common_helper_sha256", "policy_sha256",
    "scheduler_policy_sha256", "scheduler_helper_sha256", "mechanics_sha256",
    "closure_debt_sha256", "offline_queue_sha256", "fixture_audit_sha256",
    "fixture_set_sha256", "movie_inventory_sha256", "movie_tree_sha256",
    "capsule_catalog_sha256", "derived_index_sha256", "ownership_sha256",
}
QUEUE_TOP_KEYS = {
    "_comment", "schema", "generated", "selection_policy",
    "scheduler_policy_schema", "non_closure_meaning", "inputs",
    "source_snapshot", "score_component_order", "rows", "candidate_batches",
    "selected_batch", "counts", "errors", "valid",
}
PRIORITY_SCORE_COMPONENTS = (
    "retained_evidence", "static_ownership", "bounded_frontier",
    "control_quality", "remaining_debt", "dependency_leverage",
)
DEBT_ROW_KEYS = {
    "campaign_id", "capsule_count", "completion_state", "counts",
    "dependency_unlock_count", "dimensions", "family", "movie_count", "name",
    "next_action", "next_lane", "next_lane_reason",
    "prior_offline_analysis_count", "row_id",
}
_AUTHORITATIVE_QUEUE_CACHE: set[tuple[str, str, bool]] = set()
_HISTORY_EVIDENCE_CACHE: set[tuple[str, str]] = set()


def json_bytes(document: Any) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def document_sha256(document: Any) -> str:
    return hashlib.sha256(json_bytes(document)).hexdigest()


def _compress_evidence(raw: bytes) -> str:
    return base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")


def _decompress_evidence(value: Any, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be non-empty canonical zlib/base64")
    try:
        compressed = base64.b64decode(value, validate=True)
        raw = zlib.decompress(compressed)
    except (ValueError, zlib.error) as exc:
        raise ValueError(f"{label} is not valid zlib/base64") from exc
    if _compress_evidence(raw) != value:
        raise ValueError(f"{label} is not canonical zlib/base64")
    return raw


def _exact_keys(value: Any, expected: tuple[str, ...], label: str,
                errors: list[str]) -> dict:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    if tuple(value) != expected:
        errors.append(f"{label} keys/order must be exactly {list(expected)}")
    return value


def _strict_int(value: Any, label: str, errors: list[str], minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        errors.append(f"{label} must be an integer >= {minimum}")
        return 0
    return value


def _ranking_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _queue_row_errors(row: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(row, dict):
        return ["queue row must be an object"]
    row_id = row.get("row_id")
    label = row_id if isinstance(row_id, str) and row_id else "<invalid-row>"
    if set(row) != QUEUE_ROW_KEYS:
        errors.append(f"{label}: queue row fields are not exact")
    for key in ("row_id", "name", "family", "next_action"):
        if not isinstance(row.get(key), str) or not row[key]:
            errors.append(f"{label}: {key} must be a non-empty string")
    if row.get("campaign_id") is not None and (
            not isinstance(row.get("campaign_id"), str)
            or not row["campaign_id"]):
        errors.append(f"{label}: campaign_id is invalid")
    if row.get("next_lane") not in {"offline", "static", "bank"}:
        errors.append(f"{label}: next_lane is invalid")
    for key in ("dependency_unlock_count", "derived_remaining",
                "reported_remaining_informational_only"):
        if type(row.get(key)) is not int or row[key] < 0:
            errors.append(f"{label}: {key} must be a non-negative integer")
    dimensions = row.get("dimension_states")
    if not isinstance(dimensions, dict) or \
            set(dimensions) != set(EXPECTED_DIMENSIONS) or \
            any(state not in DIMENSION_STATES for state in dimensions.values()):
        errors.append(f"{label}: dimension_states is not the exact typed universe")
    elif type(row.get("derived_remaining")) is int and \
            row["derived_remaining"] != sum(
                state in {"gap", "partial"} for state in dimensions.values()):
        errors.append(f"{label}: derived_remaining disagrees with dimension states")
    for key in ("capsule_availability", "derived_indexes",
                "prior_offline_analysis", "movie_anchors"):
        values = row.get(key)
        if not isinstance(values, list) or not all(
                isinstance(item, dict) for item in values):
            errors.append(f"{label}: {key} must be a list of objects")
    anchors = row.get("movie_anchors") if isinstance(
        row.get("movie_anchors"), list) else []
    if any(anchor.get("verified") not in {True, False}
           or type(anchor.get("verified")) is not bool for anchor in anchors):
        errors.append(f"{label}: movie anchor verified flags are not Boolean")
    anchor_capsules = [anchor.get("capsule") for anchor in anchors
                       if anchor.get("capsule") is not None]
    availability = row.get("capsule_availability")
    if isinstance(availability, list) and \
            json_bytes(availability) != json_bytes(anchor_capsules):
        errors.append(
            f"{label}: capsule availability does not exactly match anchors")
    for key in ("derived_indexes", "prior_offline_analysis",
                "capsule_availability"):
        values = row.get(key)
        if isinstance(values, list) and any(
                type(item.get("preservation_verified")) is not bool
                for item in values if "preservation_verified" in item):
            errors.append(f"{label}: {key} preservation flag is not Boolean")
    blockers = row.get("frontier_blocker_domains")
    if not isinstance(blockers, list) or not all(
            isinstance(item, str) for item in blockers):
        errors.append(f"{label}: frontier blocker domains are invalid")
    static = row.get("static_ownership")
    if not isinstance(static, dict):
        errors.append(f"{label}: static_ownership must be an object")
    else:
        for key in ("function_count", "typed_state_count", "reader_group_count",
                    "writer_group_count", "overlay_count", "asset_count"):
            if type(static.get(key)) is not int or static[key] < 0:
                errors.append(f"{label}: static_ownership.{key} is invalid")
    eligibility = row.get("eligibility")
    selection = row.get("selection")
    eligible = eligibility.get("eligible") if isinstance(eligibility, dict) else None
    selectable = selection.get("selectable") if isinstance(selection, dict) else None
    deferred = selection.get("deferred") if isinstance(selection, dict) else None
    if type(eligible) is not bool:
        errors.append(f"{label}: eligibility.eligible is not Boolean")
    if type(selectable) is not bool or type(deferred) is not bool:
        errors.append(f"{label}: selection flags are not Boolean")
    if selectable and deferred:
        errors.append(f"{label}: row cannot be selectable and deferred")
    if not eligible and (selectable or deferred):
        errors.append(f"{label}: ineligible row cannot be selected/deferred")
    if eligible:
        if not anchors or any(anchor.get("verified") is not True for anchor in anchors):
            errors.append(f"{label}: eligible row lacks exact verified anchors")
        if not isinstance(row.get("score"), dict) or \
                not isinstance(row.get("expected_value"), dict):
            errors.append(f"{label}: eligible row lacks score/expected value")
    else:
        if row.get("score") is not None or row.get("expected_value") is not None or \
                row.get("rank") is not None:
            errors.append(f"{label}: ineligible row carries ranking authority")
    rank = row.get("rank")
    if selectable and (type(rank) is not int or rank < 1):
        errors.append(f"{label}: selectable row rank is invalid")
    if not selectable and rank is not None:
        errors.append(f"{label}: non-selectable row rank must be null")
    score = row.get("score")
    if isinstance(score, dict):
        components = score.get("components")
        if not isinstance(components, dict) or \
                set(components) != set(PRIORITY_SCORE_COMPONENTS):
            errors.append(f"{label}: score components are not exact")
        else:
            for name, component in components.items():
                if not isinstance(component, dict) or \
                        type(component.get("points")) is not int or \
                        component["points"] < 0 or \
                        type(component.get("maximum")) is not int or \
                        component["maximum"] < 0 or \
                        component["points"] > component["maximum"]:
                    errors.append(f"{label}: score component {name} is invalid")
        if type(score.get("total")) is not int or score.get("total", -1) < 0:
            errors.append(f"{label}: score total is invalid")
        elif isinstance(components, dict) and all(
                isinstance(value, dict) and type(value.get("points")) is int
                for value in components.values()) and score["total"] != sum(
                    value["points"] for value in components.values()):
            errors.append(f"{label}: score total disagrees with components")
    return sorted(set(errors))


def validate_policy(policy: Any) -> list[str]:
    errors: list[str] = []
    top = _exact_keys(policy, EXPECTED_TOP_LEVEL, "policy", errors)
    if top.get("schema") != SCHEMA:
        errors.append("policy schema is invalid")
    if not isinstance(top.get("description"), str) or not top["description"].strip():
        errors.append("policy description must be a non-empty string")

    cooldown = _exact_keys(top.get("cooldown"), EXPECTED_COOLDOWN,
                           "cooldown", errors)
    if _strict_int(cooldown.get("consecutive_no_reduction_threshold"),
                   "cooldown threshold", errors, 2) != 2:
        errors.append("cooldown threshold must be exactly two")
    if cooldown.get("rotate_after_first_no_reduction") is not True:
        errors.append("single no-reduction rotation must be enabled")
    expected_cooldown_scalars = {
        "scope": "selected_rows_union",
        "release": "completed_disjoint_iteration_or_any_debt_reduction",
        "exhaustion": "fail_closed",
    }
    for key, expected in expected_cooldown_scalars.items():
        if cooldown.get(key) != expected:
            errors.append(f"cooldown {key} must be {expected!r}")
    if _strict_int(cooldown.get("max_retained_attempts"),
                   "max retained attempts", errors, 2) != 32:
        errors.append("max retained attempts must be exactly 32")

    expected_value = _exact_keys(
        top.get("expected_value"),
        ("benefit_weights", "cost_weights", "lane_base_cost",
         "dimension_readiness"),
        "expected_value", errors)
    benefits = _exact_keys(expected_value.get("benefit_weights"),
                           EXPECTED_BENEFITS, "benefit_weights", errors)
    costs = _exact_keys(expected_value.get("cost_weights"), EXPECTED_COSTS,
                        "cost_weights", errors)
    lanes = _exact_keys(expected_value.get("lane_base_cost"), EXPECTED_LANES,
                        "lane_base_cost", errors)
    for group, label in ((benefits, "benefit"), (costs, "cost"),
                         (lanes, "lane cost")):
        for key, value in group.items():
            _strict_int(value, f"{label} {key}", errors, 1)
    readiness = _exact_keys(
        expected_value.get("dimension_readiness"),
        ("static", "offline", "durability"), "dimension_readiness", errors)
    flattened: list[str] = []
    for key in ("static", "offline", "durability"):
        values = readiness.get(key)
        if not isinstance(values, list) or not values or not all(
                isinstance(item, str) for item in values):
            errors.append(f"dimension_readiness.{key} must be a non-empty string list")
            continue
        if len(values) != len(set(values)):
            errors.append(f"dimension_readiness.{key} contains duplicates")
        if tuple(values) != EXPECTED_READINESS[key]:
            errors.append(
                f"dimension_readiness.{key} values/order are invalid")
        flattened.extend(values)
    if len(flattened) != len(set(flattened)) or set(flattened) != set(
            EXPECTED_DIMENSIONS):
        errors.append("dimension readiness must partition the exact nine dimensions")

    cover = _exact_keys(
        top.get("fixture_cover"),
        ("algorithm", "base_cost", "frames_per_cost_unit",
         "missing_capsule_penalty", "requirement_weights", "capsule_domains"),
        "fixture_cover", errors)
    if cover.get("algorithm") != "deterministic_weighted_greedy_set_cover":
        errors.append("fixture-cover algorithm is invalid")
    for key in ("base_cost", "frames_per_cost_unit", "missing_capsule_penalty"):
        _strict_int(cover.get(key), f"fixture_cover.{key}", errors, 1)
    requirement_weights = _exact_keys(
        cover.get("requirement_weights"), EXPECTED_REQUIREMENT_WEIGHTS,
        "fixture requirement weights", errors)
    for key, value in requirement_weights.items():
        _strict_int(value, f"fixture weight {key}", errors, 1)
    domains = cover.get("capsule_domains")
    if not isinstance(domains, list) or tuple(domains) != (
            "registers", "ram", "vram", "spu_ram", "block_flow",
            "run_local_full_state_checkpoints"):
        errors.append("fixture capsule domains/order are invalid")

    authority = _exact_keys(top.get("authority"), EXPECTED_AUTHORITY,
                            "authority", errors)
    for key in EXPECTED_AUTHORITY:
        if authority.get(key) is not True:
            errors.append(f"authority.{key} must be literal true")
    return sorted(set(errors))


def candidate_reducible_dimensions(row: dict, policy: dict) -> list[str]:
    """Return ranking candidates only; never claim a dimension transition."""
    dimensions = row.get("dimension_states") or {}
    readiness = policy["expected_value"]["dimension_readiness"]
    static_ready = bool(
        (row.get("static_ownership") or {}).get("function_count")
        or (row.get("static_ownership") or {}).get("typed_state_count")
        or (row.get("static_ownership") or {}).get("reader_group_count")
        or (row.get("static_ownership") or {}).get("writer_group_count"))
    offline_ready = bool(
        row.get("capsule_availability") or row.get("derived_indexes")
        or row.get("prior_offline_analysis"))
    durable_ready = bool(
        row.get("movie_anchors")
        and all(item.get("verified") is True for item in row["movie_anchors"]))
    candidates: set[str] = set()
    if static_ready:
        candidates.update(readiness["static"])
    if offline_ready:
        candidates.update(readiness["offline"])
    if durable_ready and (static_ready or offline_ready):
        candidates.update(readiness["durability"])
    return [name for name in EXPECTED_DIMENSIONS
            if name in candidates and dimensions.get(name) in {"gap", "partial"}]


def expected_value(row: dict, policy: dict,
                   prior_no_reduction_overlaps: int = 0) -> dict:
    if type(prior_no_reduction_overlaps) is not int or \
            prior_no_reduction_overlaps < 0:
        raise ValueError("historical overlap count must be a non-negative integer")
    dimensions = row.get("dimension_states")
    if not isinstance(dimensions, dict) or \
            set(dimensions) != set(EXPECTED_DIMENSIONS) or \
            any(state not in DIMENSION_STATES for state in dimensions.values()):
        raise ValueError("dimension_states must be the exact typed universe")
    for key in ("capsule_availability", "derived_indexes",
                "prior_offline_analysis", "movie_anchors"):
        values = row.get(key)
        if not isinstance(values, list) or not all(
                isinstance(item, dict) for item in values):
            raise ValueError(f"{key} must be a list of objects")
    static = row.get("static_ownership") or {}
    for key in ("function_count", "typed_state_count", "reader_group_count",
                "writer_group_count"):
        _ranking_int(static.get(key), f"static_ownership.{key}")
    candidates = candidate_reducible_dimensions(row, policy)
    components = (row.get("score") or {}).get("components") or {}
    benefit_weights = policy["expected_value"]["benefit_weights"]
    benefit_inputs = {
        "dependency_unlock_count": _ranking_int(
            row.get("dependency_unlock_count"), "dependency_unlock_count"),
        "candidate_reducible_dimensions": candidates,
        "retained_evidence_points": _ranking_int(
            (components.get("retained_evidence") or {}).get("points"),
            "retained_evidence.points"),
        "static_readiness_points": _ranking_int(
            (components.get("static_ownership") or {}).get("points"),
            "static_ownership.points"),
        "control_readiness_points": _ranking_int(
            (components.get("control_quality") or {}).get("points"),
            "control_quality.points"),
        "bounded_frontier_points": _ranking_int(
            (components.get("bounded_frontier") or {}).get("points"),
            "bounded_frontier.points"),
    }
    numerator = (
        benefit_inputs["dependency_unlock_count"]
        * benefit_weights["dependency_unlock"]
        + len(candidates) * benefit_weights["candidate_reducible_dimension"]
        + benefit_inputs["retained_evidence_points"]
        * benefit_weights["retained_evidence_point"]
        + benefit_inputs["static_readiness_points"]
        * benefit_weights["static_readiness_point"]
        + benefit_inputs["control_readiness_points"]
        * benefit_weights["control_readiness_point"]
        + benefit_inputs["bounded_frontier_points"]
        * benefit_weights["bounded_frontier_point"]
    )
    lane = row.get("next_lane")
    lane_key = lane if lane in {"offline", "static", "live"} else "unknown"
    cost_weights = policy["expected_value"]["cost_weights"]
    cost_inputs = {
        "lane": lane_key,
        "lane_base_cost": policy["expected_value"]["lane_base_cost"][lane_key],
        "remaining_dimensions": _ranking_int(
            row.get("derived_remaining"), "derived_remaining"),
        "prior_no_reduction_overlaps": prior_no_reduction_overlaps,
    }
    denominator = (
        cost_inputs["lane_base_cost"]
        + cost_inputs["remaining_dimensions"]
        * cost_weights["remaining_dimension"]
        + prior_no_reduction_overlaps
        * cost_weights["prior_no_reduction_overlap"]
    )
    if numerator <= 0 or denominator <= 0:
        raise ValueError("expected-value benefit and cost must be positive")
    return {
        "benefit_units": numerator,
        "cost_units": denominator,
        "score_per_1000": numerator * 1000 // denominator,
        "benefit_inputs": benefit_inputs,
        "cost_inputs": cost_inputs,
        "ranking_only": True,
        "rationale": (
            "Integer benefit/cost rank from dependency unlock, currently available "
            "dimension surfaces, retained/static/control readiness, remaining debt, "
            "lane cost, and prior overlapping no-reduction attempts; it is not a "
            "probability or closure claim."),
    }


def _ratio_better(left: tuple[int, int, str],
                  right: tuple[int, int, str] | None) -> bool:
    if right is None:
        return True
    left_num, left_den, left_id = left
    right_num, right_den, right_id = right
    cross_left = left_num * right_den
    cross_right = right_num * left_den
    return cross_left > cross_right or (
        cross_left == cross_right and left_id < right_id)


def weighted_fixture_cover(rows: list[dict], policy: dict) -> dict:
    policy_errors = validate_policy(policy)
    if policy_errors:
        raise ValueError("scheduler policy is invalid: " + "; ".join(policy_errors))
    if not isinstance(rows, list) or not rows:
        raise ValueError("fixture cover requires a non-empty row list")
    cover_policy = policy["fixture_cover"]
    weights = cover_policy["requirement_weights"]
    candidates: dict[str, dict] = {}
    path_identities: dict[str, str] = {}
    universe: dict[str, int] = {}
    for row in sorted(rows, key=lambda item: item["row_id"]):
        row_id = row.get("row_id")
        family = row.get("family")
        if not isinstance(row_id, str) or not row_id or \
                not isinstance(family, str) or not family:
            raise ValueError("fixture-cover rows require non-empty row/family IDs")
        row_key = f"row:{row_id}"
        family_key = f"family:{family}"
        universe[row_key] = weights["row"]
        universe[family_key] = weights["family"]
        anchors = row.get("movie_anchors")
        if not isinstance(anchors, list):
            raise ValueError(f"{row_id}: movie_anchors must be a list")
        anchor_capsules = [anchor.get("capsule") for anchor in anchors
                           if isinstance(anchor, dict)
                           and anchor.get("capsule") is not None]
        if "capsule_availability" in row:
            availability = row.get("capsule_availability")
            if not isinstance(availability, list) or not all(
                    isinstance(item, dict) for item in availability):
                raise ValueError(
                    f"{row_id}: capsule_availability must be a list of objects")
            if json_bytes(availability) != json_bytes(anchor_capsules):
                raise ValueError(
                    f"{row_id}: capsule availability does not match anchors")
        for anchor in anchors:
            if not isinstance(anchor, dict) or anchor.get("verified") is not True:
                raise ValueError(f"{row_id}: fixture anchor is not verified")
            movie = anchor.get("movie") or {}
            start_state = anchor.get("start_state") or {}
            path = movie.get("path")
            if not isinstance(path, str) or not path:
                raise ValueError(f"{row_id}: fixture movie path is invalid")
            identity_document = {
                "movie": movie,
                "start_state": start_state,
                "capsule": anchor.get("capsule"),
            }
            identity = document_sha256(identity_document)
            prior_identity = path_identities.setdefault(path, identity)
            if prior_identity != identity:
                raise ValueError(
                    f"{path}: conflicting movie/start-state/capsule identity alias")
            item = candidates.setdefault(path, {
                "movie": deepcopy(movie),
                "start_state": deepcopy(start_state),
                "capsule": deepcopy(anchor.get("capsule")),
                "identity_sha256": identity,
                "covers": set(),
            })
            item["covers"].update((row_key, family_key))
            capsule = anchor.get("capsule")
            if capsule is not None:
                if not isinstance(capsule, dict):
                    raise ValueError(f"{row_id}: capsule identity must be an object")
                domains = capsule.get("verified_domains")
                verified_domains = set(domains) if isinstance(domains, list) \
                    and all(isinstance(value, str) for value in domains) else set()
                for domain in cover_policy["capsule_domains"]:
                    requirement = f"row:{row_id}:domain:{domain}"
                    universe[requirement] = weights["domain"]
                    if domain in verified_domains and \
                            capsule.get("preservation_verified") is True:
                        item["covers"].add(requirement)
                requirement = f"row:{row_id}:independent_control"
                universe[requirement] = weights["independent_control"]
                if capsule.get("independent_control_verified") is True and \
                        capsule.get("preservation_verified") is True:
                    item["covers"].add(requirement)
    for path, item in candidates.items():
        capsule = item.get("capsule") or {}
        frames = capsule.get("frames")
        if type(frames) is not int or frames < 0:
            frames = item["movie"].get("frame_count")
        if type(frames) is not int or frames < 0:
            frames = 0
        cost = (
            cover_policy["base_cost"]
            + (frames + cover_policy["frames_per_cost_unit"] - 1)
            // cover_policy["frames_per_cost_unit"]
            + (0 if item.get("capsule") else
               cover_policy["missing_capsule_penalty"])
        )
        item["cost_units"] = cost
        item["frames"] = frames

    uncovered = set(universe)
    chosen: list[dict] = []
    steps: list[dict] = []
    while uncovered:
        best_path = None
        best_ratio = None
        best_new: set[str] = set()
        for path, item in candidates.items():
            if any(row["movie"]["path"] == path for row in chosen):
                continue
            new = item["covers"] & uncovered
            weight = sum(universe[key] for key in new)
            if not new:
                continue
            ratio = (weight, item["cost_units"], path)
            if _ratio_better(ratio, best_ratio):
                best_path, best_ratio, best_new = path, ratio, new
        if best_path is None:
            break
        source = candidates[best_path]
        chosen_item = {
            "movie": source["movie"],
            "start_state": source["start_state"],
            "capsule": source["capsule"],
            "identity_sha256": source["identity_sha256"],
            "frames": source["frames"],
            "cost_units": source["cost_units"],
            "covers": sorted(source["covers"]),
        }
        chosen.append(chosen_item)
        steps.append({
            "movie": best_path,
            "new_requirements": sorted(best_new),
            "new_weight": sum(universe[key] for key in best_new),
            "cost_units": source["cost_units"],
        })
        uncovered -= best_new
    return {
        "algorithm": cover_policy["algorithm"],
        "requirement_weights": deepcopy(weights),
        "universe": [{"id": key, "weight": universe[key]}
                     for key in sorted(universe)],
        "chosen_fixtures": chosen,
        "steps": steps,
        "covered_weight": sum(
            weight for key, weight in universe.items() if key not in uncovered),
        "total_weight": sum(universe.values()),
        "total_cost_units": sum(item["cost_units"] for item in chosen),
        "uncovered": sorted(uncovered),
        "complete": not uncovered,
        "ranking_only": True,
    }


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX64


def _history_errors(history: Any, maximum: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(history, list):
        return ["attempt history must be a list"]
    if len(history) > maximum:
        errors.append("attempt history exceeds the reviewed retention maximum")
    previous = GENESIS_SHA256
    for index, value in enumerate(history):
        label = f"attempt_history[{index}]"
        if not isinstance(value, dict):
            errors.append(f"{label} must be an object")
            row = {}
        else:
            row = value
            if set(row) != set(ATTEMPT_KEYS):
                errors.append(f"{label} fields are not exact")
        if row.get("previous_attempt_sha256") != previous:
            errors.append(f"{label} breaks genesis/continuity hash chain")
        for key in ("packet_sha256", "progress_sha256", "debt_before_sha256",
                    "debt_after_sha256", "evidence_sha256",
                    "attempt_sha256"):
            if not _valid_hash(row.get(key)):
                errors.append(f"{label}.{key} is not SHA-256")
        iteration = row.get("iteration")
        if type(iteration) is not int or iteration != index + 1:
            errors.append(f"{label}.iteration is not continuous")
        batch_id = row.get("batch_id")
        rows = row.get("rows")
        if not isinstance(batch_id, str) or not batch_id:
            errors.append(f"{label}.batch_id is invalid")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 3 or \
                not all(isinstance(item, str) and item for item in rows) or \
                len(rows) != len(set(rows)):
            errors.append(f"{label}.rows is invalid")
        for key in ("row_transition_count", "dimension_transition_count"):
            if type(row.get(key)) is not int or row.get(key) < 0:
                errors.append(f"{label}.{key} is not a non-negative integer")
        reduced = row.get("debt_reduced")
        if type(reduced) is not bool:
            errors.append(f"{label}.debt_reduced is not a Boolean")
        elif type(row.get("row_transition_count")) is int and \
                type(row.get("dimension_transition_count")) is int and \
                reduced != bool(row["row_transition_count"] or
                                row["dimension_transition_count"]):
            errors.append(f"{label}.debt_reduced disagrees with transition counts")
        core = {key: row.get(key) for key in ATTEMPT_CORE_KEYS}
        if row.get("attempt_sha256") != document_sha256(core):
            errors.append(f"{label}.attempt_sha256 does not authenticate the entry")
        previous = row.get("attempt_sha256")
    return errors


def _decode_snapshot(raw: bytes, label: str) -> dict:
    if not isinstance(raw, bytes):
        raise ValueError(f"{label} must be exact raw bytes")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be one JSON object")
    return document


def _debt_rows(document: dict, label: str) -> dict[str, dict]:
    errors: list[str] = []
    if document.get("schema") != DEBT_SCHEMA or document.get("valid") is not True \
            or document.get("errors") != []:
        errors.append(f"{label} is not a valid, error-free closure-debt ledger")
    rows = document.get("rows")
    if not isinstance(rows, list) or len(rows) != 107:
        errors.append(f"{label} must contain exactly 107 rows")
        rows = []
    result: dict[str, dict] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{label}.rows[{index}] is not an object")
            continue
        row_id = row.get("row_id")
        if not isinstance(row_id, str) or not row_id or row_id in result:
            errors.append(f"{label}.rows[{index}] has an invalid/duplicate row_id")
            continue
        if set(row) != DEBT_ROW_KEYS:
            errors.append(f"{label}.{row_id} fields are not exact")
        for key in ("family", "name", "next_action", "next_lane",
                    "next_lane_reason"):
            if not isinstance(row.get(key), str) or not row[key]:
                errors.append(f"{label}.{row_id}.{key} is invalid")
        if row.get("campaign_id") is not None and (
                not isinstance(row.get("campaign_id"), str)
                or not row["campaign_id"]):
            errors.append(f"{label}.{row_id}.campaign_id is invalid")
        for key in ("capsule_count", "dependency_unlock_count", "movie_count",
                    "prior_offline_analysis_count"):
            if type(row.get(key)) is not int or row[key] < 0:
                errors.append(f"{label}.{row_id}.{key} is not an integer")
        completion = row.get("completion_state")
        if completion not in COMPLETE_ROW_STATES | OPEN_ROW_STATES:
            errors.append(f"{label}.{row_id} completion_state is invalid")
        dimensions = row.get("dimensions")
        if not isinstance(dimensions, dict) or \
                set(dimensions) != set(EXPECTED_DIMENSIONS):
            errors.append(f"{label}.{row_id} dimension universe is invalid")
        else:
            state_counts = {"gap": 0, "partial": 0, "met": 0}
            for dimension, detail in dimensions.items():
                if not isinstance(detail, dict) or set(detail) != {
                        "basis", "errors", "state"} or \
                        detail.get("state") not in DIMENSION_STATES or \
                        not isinstance(detail.get("basis"), str) or \
                        not detail["basis"] or not isinstance(
                            detail.get("errors"), list) or not all(
                                isinstance(value, str)
                                for value in detail.get("errors") or []):
                    errors.append(
                        f"{label}.{row_id}.{dimension} detail is invalid")
                else:
                    state_counts[detail["state"]] += 1
            counts = row.get("counts")
            expected_counts = {
                "met": state_counts["met"],
                "not_applicable": 0,
                "remaining": state_counts["gap"] + state_counts["partial"],
            }
            if not isinstance(counts, dict) or \
                    json_bytes(counts) != json_bytes(expected_counts):
                errors.append(f"{label}.{row_id} counts disagree with dimensions")
            if completion in COMPLETE_ROW_STATES and expected_counts["remaining"] != 0:
                errors.append(f"{label}.{row_id} complete row retains debt")
            if completion in OPEN_ROW_STATES and expected_counts["remaining"] == 0:
                errors.append(f"{label}.{row_id} open row has no debt")
        result[row_id] = row
    if len(result) != 107:
        errors.append(f"{label} row IDs are not exactly unique")
    canonical_rows = set(common.baseline_rows())
    if set(result) != canonical_rows or len(canonical_rows) != 107:
        errors.append(f"{label} row IDs are not the canonical 107-row universe")
    if len(result) == 107:
        dimension_counts = {"gap": 0, "partial": 0, "met": 0}
        for row in result.values():
            for detail in (row.get("dimensions") or {}).values():
                if isinstance(detail, dict) and detail.get("state") in dimension_counts:
                    dimension_counts[detail["state"]] += 1
        top_counts = document.get("counts")
        expected_top = {
            "complete_rows": sum(
                row.get("completion_state") in COMPLETE_ROW_STATES
                for row in result.values()),
            "dimensions": dimension_counts,
            "open_next_lanes": dict(sorted({
                lane: sum(row.get("completion_state") == "open" and
                          row.get("next_lane") == lane for row in result.values())
                for lane in {row.get("next_lane") for row in result.values()
                             if row.get("completion_state") == "open"}
            }.items())),
            "open_rows": sum(row.get("completion_state") == "open"
                             for row in result.values()),
            "rows": 107,
        }
        if not isinstance(top_counts, dict) or \
                json_bytes(top_counts) != json_bytes(expected_top):
            errors.append(f"{label} top-level counts are not internally exact")
    if errors:
        raise ValueError("; ".join(sorted(set(errors))))
    return result


def derive_progress(before_raw: bytes, after_raw: bytes,
                    iteration: int) -> dict:
    """Independently derive the only admissible progress record from ledgers."""
    if type(iteration) is not int or iteration < 1:
        raise ValueError("progress iteration must be a positive integer")
    before = _decode_snapshot(before_raw, "debt-before snapshot")
    after = _decode_snapshot(after_raw, "debt-after snapshot")
    old_rows = _debt_rows(before, "debt-before snapshot")
    new_rows = _debt_rows(after, "debt-after snapshot")
    if set(old_rows) != set(new_rows):
        raise ValueError("Phase-4 row universe changed inside an iteration")
    selected = (before.get("scheduler") or {}).get("selected_campaigns")
    if not isinstance(selected, list) or len(selected) != 1 or \
            not isinstance(selected[0], dict):
        raise ValueError("debt-before snapshot must select exactly one campaign")
    selected_row = selected[0]
    campaign_id = selected_row.get("campaign_id")
    selected_rows = selected_row.get("rows")
    if not isinstance(campaign_id, str) or not campaign_id or \
            not isinstance(selected_rows, list) or \
            not 1 <= len(selected_rows) <= 3 or \
            not all(isinstance(row_id, str) and row_id in old_rows
                    for row_id in selected_rows) or \
            len(selected_rows) != len(set(selected_rows)):
        raise ValueError("debt-before selected campaign identity is invalid")

    row_transitions: list[list[str]] = []
    dimension_transitions: list[list[str]] = []
    demotions: list[list[str]] = []
    dimension_rank = {"gap": 0, "partial": 1, "met": 2}
    for row_id in sorted(old_rows):
        old, new = old_rows[row_id], new_rows[row_id]
        old_state = old["completion_state"]
        new_state = new["completion_state"]
        old_complete = old_state in COMPLETE_ROW_STATES
        new_complete = new_state in COMPLETE_ROW_STATES
        if not old_complete and new_complete:
            row_transitions.append([row_id, old_state, new_state])
        elif old_complete and not new_complete:
            demotions.append([row_id, "row", old_state, new_state])
        old_dimensions = old["dimensions"]
        new_dimensions = new["dimensions"]
        for dimension in sorted(EXPECTED_DIMENSIONS):
            old_dimension = old_dimensions[dimension]["state"]
            new_dimension = new_dimensions[dimension]["state"]
            if dimension_rank[new_dimension] > dimension_rank[old_dimension]:
                dimension_transitions.append(
                    [row_id, dimension, old_dimension, new_dimension])
            elif dimension_rank[new_dimension] < dimension_rank[old_dimension]:
                demotions.append(
                    [row_id, dimension, old_dimension, new_dimension])
    return {
        "schema": PROGRESS_SCHEMA,
        "iteration": iteration,
        "campaign_id": campaign_id,
        "row_ids": deepcopy(selected_rows),
        "debt_before_sha256": hashlib.sha256(before_raw).hexdigest(),
        "debt_after_sha256": hashlib.sha256(after_raw).hexdigest(),
        "row_transitions": row_transitions,
        "dimension_transitions": dimension_transitions,
        "demotions": demotions,
    }


def _row_coupling(left: dict, right: dict) -> tuple[int, list[str]]:
    reasons: list[str] = []
    left_movies = {anchor["movie"]["sha256"]
                   for anchor in left["movie_anchors"]}
    right_movies = {anchor["movie"]["sha256"]
                    for anchor in right["movie_anchors"]}
    shared_movies = sorted(left_movies & right_movies)
    if shared_movies:
        reasons.append("shared exact movie SHA-256: " + ", ".join(shared_movies))
    left_indexes = {item["external_index_sha256"]
                    for item in left["derived_indexes"]}
    right_indexes = {item["external_index_sha256"]
                     for item in right["derived_indexes"]}
    shared_indexes = sorted(left_indexes & right_indexes)
    if shared_indexes:
        reasons.append(
            "shared retained derived-index SHA-256: " +
            ", ".join(shared_indexes))
    shared_campaign = bool(
        left.get("campaign_id")
        and left.get("campaign_id") == right.get("campaign_id"))
    if shared_campaign:
        reasons.append(f"shared active campaign: {left['campaign_id']}")
    return (len(shared_movies) * 4 + len(shared_indexes) * 3
            + (2 if shared_campaign else 0), reasons)


def _expected_batches(ranked: list[dict], policy: dict) -> list[dict]:
    remaining = list(ranked)
    batches: list[dict] = []
    while remaining:
        seed = remaining.pop(0)
        selected = [seed]
        coupling: list[dict] = []
        while len(selected) < 3 and remaining:
            candidates: list[tuple[int, int, dict, list[str]]] = []
            for index, candidate in enumerate(remaining):
                best_strength = 0
                best_reasons: list[str] = []
                best_peer = None
                for peer in selected:
                    strength, reasons = _row_coupling(peer, candidate)
                    if strength > best_strength:
                        best_strength = strength
                        best_reasons = reasons
                        best_peer = peer["row_id"]
                if best_strength:
                    candidates.append((
                        -best_strength, index, candidate,
                        [f"{best_peer} -> {candidate['row_id']}: {reason}"
                         for reason in best_reasons],
                    ))
            if not candidates:
                break
            _, index, candidate, reasons = min(candidates)
            selected.append(candidate)
            coupling.append({"row_id": candidate["row_id"], "reasons": reasons})
            remaining.pop(index)
        row_ids = [row["row_id"] for row in selected]
        benefit = sum(row["expected_value"]["benefit_units"] for row in selected)
        cost = sum(row["expected_value"]["cost_units"] for row in selected)
        batches.append({
            "rank": 0,
            "batch_id": "movie-ready:" + "+".join(row_ids),
            "rows": row_ids,
            "score_total": sum(row["score"]["total"] for row in selected),
            "coupling": coupling or [{
                "row_id": seed["row_id"],
                "reasons": [
                    "single-row campaign packet; no unrelated movie row was forced in"],
            }],
            "rationale": (
                "Highest remaining ranked seed plus at most two rows joined by an "
                "exact movie, retained derived index, or active campaign."),
            "expected_value": {
                "benefit_units": benefit,
                "cost_units": cost,
                "score_per_1000": benefit * 1000 // cost,
            },
            "fixture_cover": weighted_fixture_cover(selected, policy),
        })
    batches.sort(key=lambda batch: (
        -Fraction(batch["expected_value"]["benefit_units"],
                  batch["expected_value"]["cost_units"]),
        batch["batch_id"],
    ))
    for rank, batch in enumerate(batches, 1):
        batch["rank"] = rank
    return batches


def _validate_queue(queue: Any, policy: dict,
                    authority_cache: dict[str, bool] | None = None,
                    require_current_sources: bool = True) -> None:
    if not isinstance(queue, dict) or queue.get("schema") != \
            "abl-phase4-movie-priority-queue/2" or \
            queue.get("selection_policy") != "movie-ready" or \
            queue.get("valid") is not True or queue.get("errors") != []:
        raise ValueError("movie-ready priority queue contract is invalid")
    if set(queue) != QUEUE_TOP_KEYS:
        raise ValueError("movie-ready priority queue fields are not exact")
    if not isinstance(queue.get("generated"), str) or not queue["generated"] or \
            queue.get("scheduler_policy_schema") != SCHEMA or \
            tuple(queue.get("score_component_order") or []) != \
            PRIORITY_SCORE_COMPONENTS or \
            not isinstance(queue.get("non_closure_meaning"), str) or \
            not queue["non_closure_meaning"]:
        raise ValueError("movie-ready priority queue metadata is invalid")
    inputs = queue.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != QUEUE_INPUT_KEYS or any(
            not _valid_hash(value) for value in inputs.values()):
        raise ValueError("movie-ready priority queue provenance is invalid")
    static_input_paths = {
        "generator_sha256": common.ROOT / "tools/phase4_movie_priority.py",
        "common_helper_sha256": common.ROOT / "tools/phase4_common.py",
        "scheduler_helper_sha256": Path(__file__).resolve(),
        "mechanics_sha256": common.BASELINE_PATH,
    }
    for key, path in static_input_paths.items():
        if inputs.get(key) != common.sha256(path):
            raise ValueError(f"movie-ready queue provenance {key} is stale")
    rows = queue.get("rows")
    batches = queue.get("candidate_batches")
    if not isinstance(rows, list) or len(rows) != 107 or \
            not isinstance(batches, list) or not batches:
        raise ValueError("movie-ready queue row/batch universe is invalid")
    row_map: dict[str, dict] = {}
    for row in rows:
        row_id = row.get("row_id") if isinstance(row, dict) else None
        if not isinstance(row_id, str) or not row_id or row_id in row_map:
            raise ValueError("movie-ready queue row IDs are invalid/duplicated")
        row_errors = _queue_row_errors(row)
        if row_errors:
            raise ValueError("; ".join(row_errors))
        if row.get("expected_value") is not None:
            expected = expected_value(row, policy)
            if json_bytes(row.get("expected_value")) != json_bytes(expected):
                raise ValueError(
                    f"{row_id}: retained expected value is not reproducible")
        row_map[row_id] = row
    canonical_rows = set(common.baseline_rows())
    if set(row_map) != canonical_rows or len(canonical_rows) != 107:
        raise ValueError("movie-ready queue does not use the canonical 107 rows")
    ranked = sorted(
        (row for row in rows if row["selection"]["selectable"] is True),
        key=lambda row: (
            -Fraction(row["expected_value"]["benefit_units"],
                      row["expected_value"]["cost_units"]),
            -row["dependency_unlock_count"], row["derived_remaining"],
            row["row_id"],
        ),
    )
    for rank, row in enumerate(ranked, 1):
        if row["rank"] != rank:
            raise ValueError(f"{row['row_id']}: row rank is not reproducible")
    expected_batches = _expected_batches(ranked, policy)
    if json_bytes(batches) != json_bytes(expected_batches):
        raise ValueError("movie-ready candidate batches are not fully reproducible")
    if json_bytes(queue.get("selected_batch")) != json_bytes(expected_batches[0]):
        raise ValueError("movie-ready selected batch is not the exact first batch")
    expected_counts = {
        "candidate_batches": len(expected_batches),
        "deferred": sum(row["selection"]["deferred"] for row in rows),
        "eligible": sum(row["eligibility"]["eligible"] for row in rows),
        "ineligible": sum(not row["eligibility"]["eligible"] for row in rows),
        "rows": 107,
        "selectable": len(ranked),
    }
    if json_bytes(queue.get("counts")) != json_bytes(expected_counts):
        raise ValueError("movie-ready queue counts are not exactly derived")
    # Internal consistency is necessary but not authoritative: coordinated score,
    # EV, rank, and batch edits can all agree with one another.  Rebuild from the
    # exact current source documents and payload bytes before accepting a queue.
    import phase4_movie_priority as priority
    try:
        generated, source_raw, documents = priority.decode_source_snapshot(
            queue.get("source_snapshot"))
    except ValueError as exc:
        raise ValueError(f"movie-ready queue source snapshot is invalid: {exc}") \
            from exc
    if generated != queue.get("generated") or documents["scheduler"] != policy:
        raise ValueError("movie-ready queue source snapshot identity is inconsistent")
    for name in priority.SOURCE_KEYS:
        input_key = priority.SOURCE_INPUT_KEYS[name]
        if hashlib.sha256(source_raw[name]).hexdigest() != inputs.get(input_key):
            raise ValueError(
                f"movie-ready queue source {name} does not match provenance")
        if require_current_sources and source_raw[name] != \
                priority.SOURCE_PATHS[name].read_bytes():
            raise ValueError(
                f"movie-ready current queue source {name} is stale")
    runtime_fingerprint = priority.authority_runtime_fingerprint(
        documents["fixture_set"], documents["movie_inventory"],
        documents["capsule"], documents["derived"])
    queue_sha256 = document_sha256(queue)
    cache_key = (queue_sha256, runtime_fingerprint, require_current_sources)
    if cache_key not in _AUTHORITATIVE_QUEUE_CACHE:
        authoritative = priority.build(
            policy=documents["policy"], scheduler=documents["scheduler"],
            debt=documents["debt"], offline=documents["offline"],
            fixture_audit=documents["fixture_audit"],
            fixture_set=documents["fixture_set"],
            movie_inventory=documents["movie_inventory"],
            capsule=documents["capsule"], derived=documents["derived"],
            ownership=documents["ownership"], _source_raw=source_raw,
            _generated=generated)
        if json_bytes(queue) != json_bytes(authoritative):
            raise ValueError(
                "movie-ready queue is not the exact authoritative source regeneration")
        _AUTHORITATIVE_QUEUE_CACHE.add(cache_key)
    if authority_cache is not None:
        authority_cache[queue_sha256] = True


def _packet_document(queue: dict, policy: dict, history: list[dict],
                     evidence: list[dict]) -> dict:
    batches = queue.get("candidate_batches") or []
    consecutive: list[dict] = []
    for attempt in reversed(history):
        if attempt.get("debt_reduced") is True:
            break
        consecutive.append(attempt)
    consecutive.reverse()
    threshold = policy["cooldown"]["consecutive_no_reduction_threshold"]
    cooldown_rows: set[str] = set()
    if len(consecutive) >= threshold:
        for attempt in consecutive[-threshold:]:
            cooldown_rows.update(attempt.get("rows") or [])
    rotation_rows: set[str] = set()
    if consecutive and policy["cooldown"]["rotate_after_first_no_reduction"]:
        rotation_rows.update(consecutive[-1].get("rows") or [])
    excluded_rows = cooldown_rows | rotation_rows

    row_map = {row["row_id"]: row for row in queue.get("rows") or []}
    dynamic: list[dict] = []
    for batch in batches:
        batch_rows = set(batch.get("rows") or [])
        overlaps = sum(
            bool(batch_rows & set(attempt.get("rows") or []))
            for attempt in history if attempt.get("debt_reduced") is False)
        row_values = [expected_value(row_map[row_id], policy, overlaps)
                      for row_id in batch["rows"]]
        benefit = sum(item["benefit_units"] for item in row_values)
        cost = sum(item["cost_units"] for item in row_values)
        dynamic.append({
            "batch": batch,
            "benefit_units": benefit,
            "cost_units": cost,
            "score_per_1000": benefit * 1000 // cost,
            "prior_no_reduction_overlap_count": overlaps,
            "excluded_by_rotation_or_cooldown": bool(batch_rows & excluded_rows),
        })
    eligible = [item for item in dynamic
                if not item["excluded_by_rotation_or_cooldown"]]
    if not eligible:
        raise ValueError("scheduler cooldown required but no disjoint batch remains")
    selected_dynamic: dict | None = None
    selected_ratio: tuple[int, int, str] | None = None
    for item in eligible:
        ratio = (item["benefit_units"], item["cost_units"],
                 item["batch"]["batch_id"])
        if _ratio_better(ratio, selected_ratio):
            selected_dynamic, selected_ratio = item, ratio
    assert selected_dynamic is not None
    selected = deepcopy(selected_dynamic["batch"])
    selected_rows = [deepcopy(row_map[row_id]) for row_id in selected["rows"]]
    return {
        "schema": PACKET_SCHEMA,
        "phase": 4,
        "selection_policy": "movie-ready",
        "source_queue_sha256": document_sha256(queue),
        "scheduler_policy": {
            "path": "config/phase4_scheduler_policy.yaml",
            "sha256": common.sha256(POLICY_PATH),
            "schema": SCHEMA,
        },
        "selected_batch": selected,
        "selected_rows": selected_rows,
        "selected_fixture_cover": deepcopy(selected["fixture_cover"]),
        "attempt_history": deepcopy(history),
        "attempt_history_sha256": document_sha256(history),
        "attempt_evidence": deepcopy(evidence),
        "attempt_evidence_sha256": document_sha256(evidence),
        "selection_diagnostics": {
            "consecutive_no_reduction_attempts": len(consecutive),
            "rotation_rows": sorted(rotation_rows),
            "cooldown_active": bool(cooldown_rows),
            "cooldown_rows": sorted(cooldown_rows),
            "eligible_batch_ids": [item["batch"]["batch_id"] for item in eligible],
            "dynamic_expected_value": [{
                key: value for key, value in item.items() if key != "batch"
            } | {"batch_id": item["batch"]["batch_id"]} for item in dynamic],
        },
        "rotation": {
            "required": bool(rotation_rows),
            "applied": bool(rotation_rows),
            "reason": (
                "Previous completed executor iteration reduced no row or dimension "
                "debt; reviewed policy rotates to a disjoint batch."
                if rotation_rows else "No no-reduction rotation is due."),
        },
        "cooldown": {
            "threshold": threshold,
            "active": bool(cooldown_rows),
            "excluded_rows": sorted(cooldown_rows),
            "release": policy["cooldown"]["release"],
        },
        "method_order": [
            "validate/query retained capsule or derived index",
            "reconstruct static ownership/interfaces",
            "run live only for a predeclared named missing domain",
            "bank authoritative machine layers and guards",
        ],
        "non_closure_meaning": queue["non_closure_meaning"],
    }


def _validate_history_evidence(
        history: list[dict], evidence: Any, policy: dict,
        authority_cache: dict[str, bool]) -> None:
    if not isinstance(evidence, list) or len(evidence) != len(history):
        raise ValueError(
            "attempt evidence must exactly cover every retained attempt")
    import phase4_movie_priority as priority
    decoded_queues: list[dict] = []
    runtime_facts: dict[str, str] = {}
    for index, (attempt, item) in enumerate(zip(history, evidence)):
        label = f"attempt_evidence[{index}]"
        if not isinstance(item, dict) or set(item) != set(ATTEMPT_EVIDENCE_KEYS):
            raise ValueError(f"{label} fields are not exact")
        if attempt.get("evidence_sha256") != document_sha256(item):
            raise ValueError(
                f"attempt_history[{index}] does not bind its exact evidence")
        queue_raw = _decompress_evidence(
            item.get("queue_zlib_base64"), f"{label}.queue")
        queue = _decode_snapshot(queue_raw, f"{label}.queue")
        if queue_raw != json_bytes(queue):
            raise ValueError(f"{label}.queue is not canonical exact JSON")
        decoded_queues.append(queue)
        queue_sha = document_sha256(queue)
        if queue_sha not in runtime_facts:
            _, _, sources = priority.decode_source_snapshot(
                queue.get("source_snapshot"))
            runtime_facts[queue_sha] = priority.authority_runtime_fingerprint(
                sources["fixture_set"], sources["movie_inventory"],
                sources["capsule"], sources["derived"])
    runtime_fingerprint = hashlib.sha256(json.dumps(
        runtime_facts, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    start = 0
    for index in range(len(history) - 1, -1, -1):
        if (history[index]["attempt_sha256"], runtime_fingerprint) in \
                _HISTORY_EVIDENCE_CACHE:
            start = index + 1
            break
    for index in range(start, len(history)):
        attempt = history[index]
        item = evidence[index]
        label = f"attempt_evidence[{index}]"
        progress = item.get("progress")
        if not isinstance(progress, dict):
            raise ValueError(f"{label} has invalid evidence types")
        before_raw = _decompress_evidence(
            item.get("debt_before_zlib_base64"), f"{label}.debt_before")
        after_raw = _decompress_evidence(
            item.get("debt_after_zlib_base64"), f"{label}.debt_after")
        queue = decoded_queues[index]
        _validate_queue(
            queue, policy, authority_cache, require_current_sources=False)
        exact_packet = _packet_document(
            queue, policy, history[:index], evidence[:index])
        exact_progress = derive_progress(before_raw, after_raw, index + 1)
        selected = exact_packet["selected_batch"]
        expected_core = {
            "previous_attempt_sha256": (
                history[index - 1]["attempt_sha256"]
                if index else GENESIS_SHA256),
            "packet_sha256": document_sha256(exact_packet),
            "progress_sha256": document_sha256(exact_progress),
            "debt_before_sha256": exact_progress["debt_before_sha256"],
            "debt_after_sha256": exact_progress["debt_after_sha256"],
            "iteration": index + 1,
            "batch_id": selected["batch_id"],
            "rows": deepcopy(selected["rows"]),
            "debt_reduced": bool(
                exact_progress["row_transitions"]
                or exact_progress["dimension_transitions"]),
            "row_transition_count": len(exact_progress["row_transitions"]),
            "dimension_transition_count": len(
                exact_progress["dimension_transitions"]),
            "evidence_sha256": document_sha256(item),
        }
        if json_bytes(progress) != json_bytes(exact_progress):
            raise ValueError(f"{label}.progress is not exactly derived")
        if exact_progress["campaign_id"] != selected["batch_id"] or \
                exact_progress["row_ids"] != selected["rows"]:
            raise ValueError(
                f"{label} debt campaign does not match its attempted packet")
        if exact_progress["demotions"]:
            raise ValueError(f"{label} contains debt demotions")
        expected_attempt = expected_core | {
            "attempt_sha256": document_sha256(expected_core),
        }
        if json_bytes(attempt) != json_bytes(expected_attempt):
            raise ValueError(
                f"attempt_history[{index}] is not authenticated by exact evidence")
        _HISTORY_EVIDENCE_CACHE.add(
            (attempt["attempt_sha256"], runtime_fingerprint))


def _packet_from_history(queue: dict, policy: dict, history: list[dict],
                         evidence: list[dict] | None = None,
                         authority_cache: dict[str, bool] | None = None,
                         require_current_sources: bool = True) -> dict:
    cache = authority_cache if authority_cache is not None else {}
    _validate_queue(queue, policy, cache, require_current_sources)
    maximum = policy["cooldown"]["max_retained_attempts"]
    history_errors = _history_errors(history, maximum)
    if history_errors:
        raise ValueError("; ".join(sorted(set(history_errors))))
    exact_evidence = [] if evidence is None and not history else evidence
    _validate_history_evidence(history, exact_evidence, policy, cache)
    assert isinstance(exact_evidence, list)
    return _packet_document(queue, policy, history, exact_evidence)


def packet(queue: dict, policy: dict, previous_packet: dict | None = None,
           previous_progress: dict | None = None,
           previous_queue: dict | None = None,
           previous_debt_before: bytes | None = None,
           previous_debt_after: bytes | None = None) -> dict:
    policy_errors = validate_policy(policy)
    if policy_errors:
        raise ValueError("scheduler policy is invalid: " + "; ".join(policy_errors))
    supplied = (
        previous_packet, previous_progress, previous_queue,
        previous_debt_before, previous_debt_after,
    )
    if not any(value is not None for value in supplied):
        return _packet_from_history(queue, policy, [])
    if not all(value is not None for value in supplied):
        raise ValueError(
            "previous packet/progress/queue/debt-before/debt-after are all required")
    assert previous_packet is not None
    assert previous_progress is not None
    assert previous_queue is not None
    assert previous_debt_before is not None
    assert previous_debt_after is not None
    if not isinstance(previous_packet, dict):
        raise ValueError("previous packet must be an object")
    history = previous_packet.get("attempt_history")
    evidence = previous_packet.get("attempt_evidence")
    maximum = policy["cooldown"]["max_retained_attempts"]
    history_errors = _history_errors(history, maximum)
    if history_errors:
        raise ValueError("; ".join(sorted(set(history_errors))))
    assert isinstance(history, list)
    if previous_packet.get("attempt_history_sha256") != document_sha256(history):
        raise ValueError("previous packet attempt-history hash is invalid")
    if previous_packet.get("attempt_evidence_sha256") != \
            document_sha256(evidence):
        raise ValueError("previous packet attempt-evidence hash is invalid")
    authority_cache: dict[str, bool] = {}
    exact_previous = _packet_from_history(
        previous_queue, policy, history, evidence, authority_cache,
        require_current_sources=False)
    if json_bytes(previous_packet) != json_bytes(exact_previous):
        raise ValueError(
            "previous packet does not exactly reproduce from its queue/policy/history")
    expected_progress = derive_progress(
        previous_debt_before, previous_debt_after, len(history) + 1)
    if json_bytes(previous_progress) != json_bytes(expected_progress):
        raise ValueError(
            "previous progress does not exactly derive from the supplied debt snapshots")
    selected = previous_packet["selected_batch"]
    if expected_progress["campaign_id"] != selected["batch_id"] or \
            expected_progress["row_ids"] != selected["rows"]:
        raise ValueError(
            "debt-before campaign does not match the exact attempted packet")
    if expected_progress["demotions"]:
        raise ValueError("a packet cannot rank from progress containing debt demotions")
    if len(history) >= maximum:
        raise ValueError(
            "reviewed attempt-history capacity exhausted; explicit re-review required")
    evidence_item = {
        "queue_zlib_base64": _compress_evidence(json_bytes(previous_queue)),
        "progress": deepcopy(previous_progress),
        "debt_before_zlib_base64": _compress_evidence(previous_debt_before),
        "debt_after_zlib_base64": _compress_evidence(previous_debt_after),
    }
    core = {
        "previous_attempt_sha256": (
            history[-1]["attempt_sha256"] if history else GENESIS_SHA256),
        "packet_sha256": document_sha256(previous_packet),
        "progress_sha256": document_sha256(previous_progress),
        "debt_before_sha256": expected_progress["debt_before_sha256"],
        "debt_after_sha256": expected_progress["debt_after_sha256"],
        "iteration": expected_progress["iteration"],
        "batch_id": selected["batch_id"],
        "rows": deepcopy(selected["rows"]),
        "debt_reduced": bool(expected_progress["row_transitions"] or
                             expected_progress["dimension_transitions"]),
        "row_transition_count": len(expected_progress["row_transitions"]),
        "dimension_transition_count": len(
            expected_progress["dimension_transitions"]),
        "evidence_sha256": document_sha256(evidence_item),
    }
    history = deepcopy(history) + [core | {
        "attempt_sha256": document_sha256(core),
    }]
    assert isinstance(evidence, list)
    evidence = deepcopy(evidence) + [evidence_item]
    return _packet_from_history(
        queue, policy, history, evidence, authority_cache)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--derive-progress", action="store_true")
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--iteration", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not args.derive_progress or None in (
            args.before, args.after, args.iteration, args.out):
        parser.error(
            "--derive-progress requires --before, --after, --iteration, and --out")
    try:
        document = derive_progress(
            args.before.read_bytes(), args.after.read_bytes(), args.iteration)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(json_bytes(document))
    print(
        f"PASS: iteration={args.iteration} rows={len(document['row_transitions'])} "
        f"dimensions={len(document['dimension_transitions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
