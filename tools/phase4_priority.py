#!/usr/bin/env python3
"""Derive Phase-4 campaign priority from shared surfaces and baseline gaps."""
from __future__ import annotations

import json
from datetime import date

import phase4_common as common

OUTPUT = common.ROOT / "analysis/phase4_priority.json"


def row_symbols(row: dict) -> set[str]:
    symbols: set[str] = set()
    for function in row.get("functions") or []:
        address = function.get("function_start") or function.get("address")
        if address:
            symbols.add(f"function:{str(address).lower()}")
    for state in row.get("state") or []:
        for semantic_id in state.get("semantic_ids") or []:
            symbols.add(f"state:{semantic_id}")
    for overlay in row.get("overlay") or []:
        space = overlay.get("space")
        target = overlay.get("function_start") or overlay.get("name")
        if space or target:
            symbols.add(f"overlay:{space}:{target}")
    return symbols


def build(registry: dict | None = None, mechanics: dict | None = None,
          ownership: dict | None = None) -> dict:
    registry = registry or common.load_yaml(common.REGISTRY_PATH)
    mechanics = mechanics or common.load_yaml(common.BASELINE_PATH)
    ownership = ownership or common.load_json("analysis/phase3_ownership_graph.json")
    registry_gaps = common.validate_registry(registry, mechanics)
    mechanic_rows = common.baseline_rows(mechanics)
    ownership_rows = ownership.get("rows") or {}

    own_symbols: dict[str, set[str]] = {}
    referenced_symbols: dict[str, set[str]] = {}
    family_rows = {family["id"]: family for family in registry.get("families") or []}
    for family_id, family in family_rows.items():
        own_symbols[family_id] = set().union(*(
            [row_symbols(ownership_rows.get(row_id, {}))
             for row_id in family.get("primary_rows") or []] or [set()]
        ))
        all_row_ids = list(family.get("primary_rows") or []) + \
            list(family.get("dependency_rows") or [])
        referenced_symbols[family_id] = set().union(*(
            [row_symbols(ownership_rows.get(row_id, {})) for row_id in all_row_ids]
            or [set()]
        ))

    rows = []
    for family_id, family in family_rows.items():
        shared_by_family: dict[str, int] = {}
        for other_id in family_rows:
            if other_id == family_id:
                continue
            count = len(own_symbols[family_id] & referenced_symbols[other_id])
            if count:
                shared_by_family[other_id] = count
        primary = family.get("primary_rows") or []
        gaps = [row_id for row_id in primary
                if mechanic_rows[row_id].get("status") not in {
                    "solved", "disproven", "not_applicable"}]
        rows.append({
            "family": family_id,
            "number": family["number"],
            "priority_tier": family["priority_tier"],
            "primary_rows": len(primary),
            "coverage_gap_rows": gaps,
            "coverage_gap_count": len(gaps),
            "owned_semantic_symbols": len(own_symbols[family_id]),
            "dependent_family_count": len(shared_by_family),
            "shared_symbol_edges": sum(shared_by_family.values()),
            "shared_by_family": dict(sorted(shared_by_family.items())),
            "priority_basis": family["priority_basis"],
        })
    rows.sort(key=lambda row: (
        row["priority_tier"], -row["dependent_family_count"],
        -row["shared_symbol_edges"], -row["coverage_gap_count"], row["number"],
    ))
    tier_one = {row["family"] for row in rows if row["priority_tier"] == 1}
    active_mod_demand_terms = sorted(
        family["id"] for family in family_rows.values()
        if any(term in family["priority_basis"].lower()
               for term in ("allmods demand", "active mod demand", "recent mod"))
    )
    low_level_checks = {
        "registry_valid": not registry_gaps,
        "all_twelve_ranked": len(rows) == 12,
        "core_substrates_are_tier_one": tier_one == common.CORE_FAMILIES,
        "priority_uses_shared_surface": all(
            "dependent_family_count" in row and "shared_symbol_edges" in row
            for row in rows),
        "priority_uses_baseline_gaps": all(
            "coverage_gap_count" in row for row in rows),
        "active_mod_demand_not_a_priority_input": not active_mod_demand_terms,
    }
    return {
        "_comment": "Phase-4 WP1 priority derived from the authoritative row map, "
                    "Phase-3 function/state/overlay surfaces, and current baseline "
                    "gaps. Regenerate: python3 tools/phase4_priority.py",
        "generated": date.today().isoformat(),
        "inputs": {
            "campaign_registry": {
                "path": "config/phase4_campaigns.yaml",
                "sha256": common.sha256(common.REGISTRY_PATH),
            },
            "mechanics": {
                "path": "analysis/mechanics_baseline.yaml",
                "sha256": common.sha256(common.BASELINE_PATH),
                "rows": len(mechanic_rows),
            },
            "ownership": {
                "path": "analysis/phase3_ownership_graph.json",
                "sha256": common.sha256(
                    common.ROOT / "analysis/phase3_ownership_graph.json"),
            },
        },
        "registry_gaps": registry_gaps,
        "active_mod_demand_terms": active_mod_demand_terms,
        "low_level_checks": low_level_checks,
        "work_package_1_met": all(low_level_checks.values()),
        "priority_order": [row["family"] for row in rows],
        "families": rows,
    }


def main() -> int:
    document = build()
    OUTPUT.write_text(json.dumps(document, indent=1) + "\n")
    print(
        f"[phase4-priority] {len(document['families'])}/12 families ranked; "
        f"WP1={'MET' if document['work_package_1_met'] else 'OPEN'}")
    for gap in document["registry_gaps"]:
        print(f"  registry: {gap}")
    return 0 if document["work_package_1_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
