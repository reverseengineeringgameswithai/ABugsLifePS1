#!/usr/bin/env python3
"""Compute the twelve-family Phase-4 scorecard from low-level campaign evidence."""
from __future__ import annotations

import json
from datetime import date

import phase4_common as common
import phase4_priority

OUTPUT = common.ROOT / "analysis/phase4_coverage_matrix.json"

INDIVIDUAL_SUBJECTS = (
    "grasshopper", "mosquito", "flies", "cockroaches", "spiders", "mites",
    "grubs", "centipedes", "earthworms", "armored_beetles", "wasps",
    "dragonflies", "daddy_long_legs", "thumper", "bird", "thud", "molt",
    "hopper",
)


def build(registry: dict | None = None, mechanics: dict | None = None,
          findings_doc: dict | None = None) -> dict:
    registry = registry or common.load_yaml(common.REGISTRY_PATH)
    mechanics = mechanics or common.load_yaml(common.BASELINE_PATH)
    findings_doc = findings_doc or common.load_yaml(common.FINDINGS_PATH)
    rows = common.baseline_rows(mechanics)
    findings = common.finding_index(findings_doc)
    owners, _ = common.primary_owners(registry)
    registry_gaps = common.validate_registry(registry, mechanics)

    campaign_audits: dict[str, dict] = {}
    completed_campaigns: dict[str, dict] = {}
    for campaign in registry.get("child_campaigns") or []:
        gaps = common.audit_campaign(campaign, registry, findings)
        cid = campaign.get("id", "<missing>")
        campaign_audits[cid] = {
            "family": campaign.get("family"),
            "declared_status": campaign.get("status"),
            "gaps": gaps,
            "completed_from_low_level_evidence": not gaps,
        }
        if not gaps:
            completed_campaigns[cid] = campaign

    absence_audits: dict[str, dict] = {}
    completed_absence: dict[str, dict] = {}
    for proof in registry.get("reviewed_absence") or []:
        gaps = common.audit_absence(proof)
        row_id = proof.get("row_id", "<missing>")
        absence_audits[row_id] = {
            "gaps": gaps,
            "reviewed_from_low_level_evidence": not gaps,
        }
        if not gaps:
            completed_absence[row_id] = proof

    row_coverage: dict[str, dict] = {}
    duplicate_completion: dict[str, list[str]] = {}
    for row_id, row in rows.items():
        campaigns = sorted(
            cid for cid, campaign in completed_campaigns.items()
            if row_id in (campaign.get("rows") or []))
        if len(campaigns) > 1:
            duplicate_completion[row_id] = campaigns
        absence = row_id in completed_absence
        state = "campaign_complete" if len(campaigns) == 1 else \
            "reviewed_absent" if absence else "open"
        if campaigns and absence:
            state = "conflicting_completion"
        row_coverage[row_id] = {
            "family": owners.get(row_id),
            "name": row.get("name"),
            "baseline_status": row.get("status"),
            "completed_campaigns": campaigns,
            "reviewed_absence": absence,
            "state": state,
        }

    family_rows = {family["id"]: family for family in registry.get("families") or []}
    scorecard: dict[str, dict] = {}
    for family_id, family in family_rows.items():
        primary = family.get("primary_rows") or []
        complete = [row_id for row_id in primary
                    if row_coverage.get(row_id, {}).get("state") in {
                        "campaign_complete", "reviewed_absent"}]
        active = sorted(
            campaign.get("id", "<missing>")
            for campaign in registry.get("child_campaigns") or []
            if campaign.get("family") == family_id)
        derived_status = "complete" if len(complete) == len(primary) else \
            "active" if active else "pending"
        scorecard[family_id] = {
            "number": family["number"],
            "title": family["title"],
            "primary_rows": len(primary),
            "completed_rows": len(complete),
            "open_rows": sorted(set(primary) - set(complete)),
            "active_child_campaigns": active,
            "derived_status": derived_status,
        }

    priority = phase4_priority.build(registry, mechanics)
    wp1 = priority["work_package_1_met"]
    core_complete = all(
        scorecard.get(family_id, {}).get("derived_status") == "complete"
        for family_id in common.CORE_FAMILIES)
    wp2 = core_complete
    breadth_families = {
        "seeds_plants_traversal_powers", "collectibles_equipment_rewards",
        "enemies_combat", "bosses_special_objectives",
    }
    wp3 = all(scorecard[family_id]["derived_status"] == "complete"
              for family_id in breadth_families)
    subjects_seen = {
        subject for campaign in completed_campaigns.values()
        for subject in campaign.get("individual_subjects") or []
    }
    missing_subjects = sorted(set(INDIVIDUAL_SUBJECTS) - subjects_seen)
    wp4 = not missing_subjects
    wp5 = all(scorecard[family_id]["derived_status"] == "complete" for family_id in (
        "bosses_special_objectives", "loading_overlays_resources"))

    baseline_consistency_gaps: list[str] = []
    for row_id, coverage in row_coverage.items():
        status = coverage["baseline_status"]
        if coverage["state"] == "campaign_complete" and status != "solved":
            baseline_consistency_gaps.append(
                f"{row_id}: completed campaign is not reflected as baseline solved")
        elif coverage["state"] == "reviewed_absent" and status not in {
                "not_applicable", "disproven"}:
            baseline_consistency_gaps.append(
                f"{row_id}: reviewed absence is not reflected in baseline status")
        elif status == "solved" and coverage["state"] != "campaign_complete":
            baseline_consistency_gaps.append(
                f"{row_id}: baseline claims solved without a completed campaign")
        elif status in {"not_applicable", "disproven"} and \
                coverage["state"] != "reviewed_absent":
            # A20 is a Phase-1 classification, not yet a Phase-4 absence proof.
            baseline_consistency_gaps.append(
                f"{row_id}: baseline absence status lacks a Phase-4 reviewed proof")
    wp6 = not baseline_consistency_gaps

    work_packages = {
        "WP1": {
            "description": "Dependency-centrality and pristine-gap priority",
            "met": wp1,
            "priority_order": priority["priority_order"],
            "low_level_checks": priority["low_level_checks"],
        },
        "WP2": {
            "description": "Core player/input/lifecycle and shared object/render/audio substrates first",
            "met": wp2,
            "core_family_status": {
                family_id: scorecard[family_id]["derived_status"]
                for family_id in sorted(common.CORE_FAMILIES)},
        },
        "WP3": {
            "description": "Collectible, plant, enemy, and objective breadth across applicable levels",
            "met": wp3,
            "family_status": {
                family_id: scorecard[family_id]["derived_status"]
                for family_id in sorted(breadth_families)},
        },
        "WP4": {
            "description": "Every regular enemy family and boss completed individually",
            "met": wp4,
            "required_subjects": list(INDIVIDUAL_SUBJECTS),
            "missing_subjects": missing_subjects,
        },
        "WP5": {
            "description": "Special-stage mechanics and exceptional overlay paths",
            "met": wp5,
            "family_status": {
                family_id: scorecard[family_id]["derived_status"]
                for family_id in (
                    "bosses_special_objectives", "loading_overlays_resources")},
        },
        "WP6": {
            "description": "Baseline changes are derived from completed evidence",
            "met": wp6,
            "gaps": baseline_consistency_gaps,
        },
    }
    complete_rows = sum(
        coverage["state"] in {"campaign_complete", "reviewed_absent"}
        for coverage in row_coverage.values())
    return {
        "_comment": "Phase-4 twelve-family scorecard recomputed from child-campaign "
                    "evidence assertions and reviewed pristine-absence proofs. No "
                    "campaign passes/complete/gate flag is trusted. Regenerate: "
                    "python3 tools/phase4_coverage.py",
        "generated": date.today().isoformat(),
        "inputs": {
            "mechanics_sha256": common.sha256(common.BASELINE_PATH),
            "registry_sha256": common.sha256(common.REGISTRY_PATH),
            "findings_sha256": common.sha256(common.FINDINGS_PATH),
        },
        "registry_gaps": registry_gaps,
        "campaign_audits": campaign_audits,
        "absence_audits": absence_audits,
        "duplicate_completed_owners": duplicate_completion,
        "rows": row_coverage,
        "families": scorecard,
        "counts": {
            "baseline_rows": len(rows),
            "campaign_complete": sum(
                row["state"] == "campaign_complete" for row in row_coverage.values()),
            "reviewed_absent": sum(
                row["state"] == "reviewed_absent" for row in row_coverage.values()),
            "complete_total": complete_rows,
            "open": len(rows) - complete_rows,
        },
        "work_packages": work_packages,
        "overall_met": (
            not registry_gaps and not duplicate_completion
            and all(package["met"] for package in work_packages.values())
            and complete_rows == len(rows)
        ),
    }


def main() -> int:
    document = build()
    OUTPUT.write_text(json.dumps(document, indent=1) + "\n")
    counts = document["counts"]
    print(
        f"[phase4-coverage] rows complete={counts['complete_total']}/"
        f"{counts['baseline_rows']} open={counts['open']}; "
        f"families complete={sum(row['derived_status'] == 'complete' for row in document['families'].values())}/12")
    for name, package in document["work_packages"].items():
        print(f"  {name}: {'MET' if package['met'] else 'OPEN'} — {package['description']}")
    return 0 if document["overall_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
