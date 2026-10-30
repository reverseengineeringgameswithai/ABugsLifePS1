#!/usr/bin/env python3
"""Recompute the exact four-predicate Phase-4 exit gate from low-level evidence."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import build_identity
import phase3_gate_audit
import phase4_common as common
import phase4_coverage
import phase4_inventory
import phase4_priority

OUTPUT = common.ROOT / "analysis/phase4_gate.json"


def stable_generated(path: Path | None = None) -> str:
    """Preserve the retained audit date so --write is checkout-stable."""
    path = path or OUTPUT
    if path.is_file():
        try:
            value = json.loads(path.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def _fresh(rel: str, computed: dict) -> bool:
    path = common.ROOT / rel
    if not path.is_file():
        return False
    retained = json.loads(path.read_text())
    return common.semantic_without_generated(retained) == \
        common.semantic_without_generated(computed)


def phase3_handoff_gate() -> dict:
    bullets = {}
    for name, function in phase3_gate_audit.BULLETS:
        met, detail = function()
        bullets[name] = {"met": met, "detail": detail}
    coverage_met, coverage = phase3_gate_audit.coverage_matrix_status()
    inventory_met, inventory = phase3_gate_audit.evidence_inventory_status()
    rpc_met, rpc = phase3_gate_audit.debugger_api_documentation_status()
    decisive_met, decisive = phase3_gate_audit.decisive_evidence_status()
    upstream_met, upstream = phase3_gate_audit.upstream_durability_status()
    checks = {
        "coverage_matrix": coverage_met,
        "evidence_inventory": inventory_met,
        "debugger_api_documentation": rpc_met,
        "decisive_evidence": decisive_met,
        "upstream_durability": upstream_met,
        **{f"bullet_{name}": row["met"] for name, row in bullets.items()},
    }
    return {
        "met": all(checks.values()),
        "checks": checks,
        "bullets": bullets,
        "coverage": coverage,
        "inventory": inventory,
        "rpc": rpc,
        "decisive": decisive,
        "upstream": upstream,
    }


def pristine_identity_gate() -> dict:
    checks = {"staged_tree": False, "mounted_source_media": False}
    gaps = []
    try:
        build_identity.verify_tree()
        checks["staged_tree"] = True
    except SystemExit as exc:
        gaps.append(str(exc))
    baselines = build_identity.load_baselines()
    cue_names = sorted(
        name for name in (baselines.get("pristine_media") or {})
        if name.lower().endswith(".cue"))
    if len(cue_names) != 1:
        gaps.append(f"expected exactly one pristine CUE pin, found {cue_names}")
    else:
        try:
            verification = build_identity.verify_pristine_media_path(
                common.ROOT / cue_names[0], baselines)
            checks["mounted_source_media"] = (
                verification.get("pristine_verified") is True
                and all(row.get("matches_pin") is True
                        for row in verification.get("files", {}).values()))
        except SystemExit as exc:
            gaps.append(str(exc))
            verification = None
    # Absolute checkout paths are environmental metadata, not evidence. Retain
    # the verified component names and hashes with an explicit canonical root so
    # clean clones reproduce this artifact byte-for-byte.
    if verification:
        verification["mounted_path"] = f"<checkout>/{Path(verification['mounted_path']).name}"
        for name, row in verification.get("files", {}).items():
            row["path"] = f"<checkout>/{name}"
    return {
        "met": all(checks.values()),
        "checks": checks,
        "gaps": gaps,
        "verification": verification if len(cue_names) == 1 else None,
    }


def build(registry: dict | None = None, mechanics: dict | None = None,
          findings_doc: dict | None = None) -> dict:
    registry = registry or common.load_yaml(common.REGISTRY_PATH)
    mechanics = mechanics or common.load_yaml(common.BASELINE_PATH)
    findings_doc = findings_doc or common.load_yaml(common.FINDINGS_PATH)
    priority = phase4_priority.build(registry, mechanics)
    coverage = phase4_coverage.build(registry, mechanics, findings_doc)
    fixture = phase4_inventory.build_fixture_audit(mechanics, registry)
    knowledge = phase4_inventory.build_knowledge_audit(
        registry, mechanics, findings_doc)
    inventory = phase4_inventory.build_campaign_inventory(fixture, knowledge)
    handoff = common.handoff_constraints(mechanics)

    counts = coverage["counts"]
    all_rows_complete = (
        counts["complete_total"] == counts["baseline_rows"]
        and counts["baseline_rows"] == len(common.baseline_rows(mechanics)))
    all_families_complete = all(
        family["derived_status"] == "complete"
        for family in coverage["families"].values())
    predicate_1 = (
        all_rows_complete and all_families_complete
        and not coverage["registry_gaps"]
        and not coverage["duplicate_completed_owners"])

    completed_audit_rows = [
        row for row in coverage["campaign_audits"].values()
        if row["declared_status"] == "completed"]
    predicate_2 = (
        predicate_1 and bool(completed_audit_rows)
        and all(row["completed_from_low_level_evidence"]
                for row in completed_audit_rows)
        and not knowledge["gaps"]["findings"]
        and not knowledge["gaps"]["completed_campaigns"])

    breadth_packages = all(
        coverage["work_packages"][name]["met"]
        for name in ("WP3", "WP4", "WP5"))
    predicate_3 = predicate_1 and predicate_2 and breadth_packages

    completed_campaigns = [
        campaign for campaign in registry.get("child_campaigns") or []
        if campaign.get("status") == "completed"]
    intersecting_residuals = sorted(
        f"{campaign.get('id')}:{residual.get('boundary')}"
        for campaign in completed_campaigns
        for residual in campaign.get("bounded_residuals") or []
        if residual.get("intersects_behavior") is not False)
    predicate_4 = (
        predicate_1 and predicate_2 and not intersecting_residuals
        and handoff["preserved"])

    freshness = {
        "priority": _fresh("analysis/phase4_priority.json", priority),
        "coverage": _fresh("analysis/phase4_coverage_matrix.json", coverage),
        "fixture_audit": _fresh("analysis/phase4_fixture_audit.json", fixture),
        "knowledge_audit": _fresh("analysis/phase4_knowledge_audit.json", knowledge),
        "campaign_inventory": _fresh(
            "analysis/phase4_campaign_inventory.json", inventory),
    }
    phase3 = phase3_handoff_gate()
    pristine = pristine_identity_gate()
    prerequisites = {
        "priority_work_package": priority["work_package_1_met"],
        "all_six_work_packages": all(
            package["met"] for package in coverage["work_packages"].values()),
        "fixture_audit_structural": fixture["structural_ready"],
        "knowledge_audit_structural": knowledge["structural_ready"],
        "inventory_structural": inventory["structural_ready"],
        "retained_artifacts_fresh": (
            all(freshness.values())
            and inventory["artifact_source_dependencies_fresh"]),
        "phase3_gate_recomputed": phase3["met"],
        "phase3_confidence_handoff_preserved": handoff["preserved"],
        "pristine_build_identity": pristine["met"],
    }
    predicates = {
        "1_complete_campaign_coverage": {
            "met": predicate_1,
            "baseline_rows": counts["baseline_rows"],
            "complete_rows": counts["complete_total"],
            "complete_families": sum(
                family["derived_status"] == "complete"
                for family in coverage["families"].values()),
        },
        "2_subsystem_definition_of_done": {
            "met": predicate_2,
            "declared_completed_campaigns": len(completed_audit_rows),
            "audited_completed_campaigns": sum(
                row["completed_from_low_level_evidence"]
                for row in completed_audit_rows),
        },
        "3_breadth_and_generalization": {
            "met": predicate_3,
            "breadth_work_packages_met": breadth_packages,
            "missing_individual_subjects": coverage["work_packages"]["WP4"][
                "missing_subjects"],
        },
        "4_bounded_intersections": {
            "met": predicate_4,
            "intersecting_residuals": intersecting_residuals,
            "phase3_handoff": handoff,
        },
    }
    gate_met = all(row["met"] for row in predicates.values()) \
        and all(prerequisites.values())
    return {
        "_comment": "Exact Phase-4 exit gate. The four binding predicates and "
                    "global prerequisites are recomputed from baseline rows, "
                    "low-level evidence leaves, central fixture pins, current "
                    "pristine bytes, and the Phase-3 gate functions. High-level "
                    "campaign passes/complete/solved/gate flags are never accepted "
                    "as evidence. Regenerate: python3 tools/phase4_gate.py",
        "generated": stable_generated(),
        "gate_met": gate_met,
        "predicates": predicates,
        "prerequisites": prerequisites,
        "freshness": freshness,
        "phase3_recomputed": phase3,
        "pristine_identity": pristine,
        "coverage_counts": counts,
        "open_rows": [
            row_id for row_id, row in coverage["rows"].items()
            if row["state"] == "open"],
        "work_packages": coverage["work_packages"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = json.dumps(document, indent=1) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            print("[phase4-gate] retained artifact is missing or stale")
            return 2
        print("[phase4-gate] retained artifact reproduces byte-for-byte")
        return 0
    OUTPUT.write_text(rendered)
    print(f"[phase4-gate] {'MET' if document['gate_met'] else 'OPEN'}")
    for name, row in document["predicates"].items():
        print(f"  {'MET ' if row['met'] else 'OPEN'} {name}")
    for name, met in document["prerequisites"].items():
        if not met:
            print(f"  prerequisite OPEN: {name}")
    print(
        f"  rows={document['coverage_counts']['complete_total']}/"
        f"{document['coverage_counts']['baseline_rows']} "
        f"open={document['coverage_counts']['open']}")
    return 0 if document["gate_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
