#!/usr/bin/env python3
"""Phase-3 WP1-WP9 coverage matrix.

This is the binding work-package acceptance surface.  It deliberately rejects
"representative" evidence when the roadmap requires an exhaustive census.  A
record-layout finding is not an audio record, a state xref report is not a call
graph, and naming an off-table scene route is not the same as mapping it.

The matrix recomputes finding closure with ``phase3_knowledge_audit.audit_one``;
it never trusts the retained audit's ``finished`` booleans.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import phase3_knowledge_audit as knowledge_audit  # noqa: E402
import phase3_native_domains as native_domains  # noqa: E402

REQUIRED_FRONTIER_FIELDS = (
    "functions", "state", "assets", "overlay", "readers", "writers", "lifecycle"
)
REQUIRED_STATE_SCOPES = {
    "global_scene": {"original_game.scene_flow"},
    "player": {"original_game.player", "original_game.player_actions"},
    "object": {"original_game.level_actors", "original_game.scenery"},
    "contact": {"original_game.contact_pool"},
    "enemy": {"original_game.enemies", "original_game.bosses"},
    "projectile": {"original_game.projectiles"},
    "plant": {"original_game.plants"},
    "camera": {"original_game.camera"},
    "render": {"original_game.render"},
    "audio": {"original_game.audio"},
    "objective": {"original_game.objectives", "original_game.bonus_unlock"},
    "frontend": {"original_game.frontend", "original_game.bonus_unlock_hud"},
    "save": {"original_game.save"},
}
REQUIRED_RECORD_FAMILIES = (
    "object", "contact", "enemy", "projectile", "seed", "plant", "player",
    "camera", "render", "audio", "objective", "frontend",
)
DEFAULT_RECORD_FAMILY = {
    "player_block": "player",
    "contact_record": "contact",
    "actor_record": "object",
    "plant_slot": "plant",
    "camera_record": "camera",
}
OWNERSHIP_MODEL_FIELDS = (
    "capacity", "slot_reuse", "ownership_transfer", "retirement", "reset"
)


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def load_yaml(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text())


def optional_json(rel: str) -> dict | None:
    path = ROOT / rel
    return json.loads(path.read_text()) if path.exists() else None


def optional_yaml(rel: str) -> dict | None:
    path = ROOT / rel
    return yaml.safe_load(path.read_text()) if path.exists() else None


def finding_index() -> tuple[dict[str, dict], dict[str, dict]]:
    findings = {f["id"]: f for f in load_yaml("config/phase3_findings.yaml")["findings"]}
    rows = {}
    for fid, finding in findings.items():
        gaps = knowledge_audit.audit_one(finding)
        rows[fid] = {"finished": not gaps, "gaps": gaps}
    return findings, rows


def finding_status(ids: list[str], rows: dict[str, dict]) -> tuple[bool, list[str]]:
    unfinished = [fid for fid in ids if not rows.get(fid, {}).get("finished")]
    return not unfinished, unfinished


def record_families(record_cfg: dict) -> dict[str, list[str]]:
    represented: dict[str, list[str]] = {family: [] for family in REQUIRED_RECORD_FAMILIES}
    for record in record_cfg["records"]:
        families = record.get("families") or []
        if isinstance(families, str):
            families = [families]
        if not families and record["id"] in DEFAULT_RECORD_FAMILY:
            families = [DEFAULT_RECORD_FAMILY[record["id"]]]
        for family in families:
            evidence = (record.get("family_evidence") or {}).get(family) or []
            if family in represented and evidence:
                represented[family].append(record["id"])
    return represented


def _structured_blocker(value: object) -> bool:
    return isinstance(value, dict) and all(
        str(value.get(key) or "").strip()
        for key in ("missing_link", "evidence", "next_experiment")
    )


def _ownership_fact(value: object) -> bool:
    return isinstance(value, dict) and all(
        str(value.get(key) or "").strip()
        for key in ("rule", "evidence", "confidence")
    ) and value.get("confidence") in {
        "hypothesized", "static_seen", "runtime_seen", "confirmed"
    }


def _frontier_facet_bounded(row: dict, field: str) -> bool:
    """A facet is useful evidence or an explicit three-part blocker.

    Merely adding an empty key must not satisfy WP1.  This guard is intentionally
    shared with tests so the coverage matrix remains falsifiable.
    """
    value = row.get(field)
    if isinstance(value, list) and value:
        return True
    return _structured_blocker((row.get("frontier_blockers") or {}).get(field))


def build_matrix() -> dict:
    findings, audit_rows = finding_index()
    ownership = load_json("analysis/phase3_ownership_graph.json")
    dispatch = load_json("analysis/phase3_dispatch_map.json")
    jr = load_json("analysis/phase3_jr_tables.json")
    jalr = load_json("analysis/phase3_jalr_callbacks.json")
    overlay = load_json("analysis/phase3_overlay_map.json")
    lifetime = load_json("analysis/phase3_semantic_lifetime.json")
    scene_graph = load_json("analysis/phase3_scene_asset_graph.json")
    xrefs = load_json("analysis/phase3_xrefs.json")
    records = load_json("analysis/phase3_record_types.json")
    record_cfg = load_yaml("config/record_types.yaml")
    record_probe = load_json("analysis/phase3_record_probe.json")
    transition = load_json("analysis/phase3_transition_reset.json")
    mechanics = {row["id"]: row for row in load_yaml("analysis/mechanics_baseline.yaml")["rows"]}
    semantic_entries = {
        e["id"]: e for e in load_yaml("config/semantic_state.yaml")["entries"]
        if isinstance(e.get("address"), int)
    }

    # WP1: an address-only ownership row is not a semantic frontier.  Every row
    # must carry each required facet, even when the facet is an explicit bounded
    # unknown/not-applicable entry.
    wp1_findings = [
        "mechanic_ownership_frontier", "spin_move_bounded_negative",
        "bug_bar_thud_boss_bound",
    ]
    wp1_findings_ok, wp1_unfinished = finding_status(wp1_findings, audit_rows)
    frontier_gaps = {}
    for rid, row in ownership["rows"].items():
        missing = [field for field in REQUIRED_FRONTIER_FIELDS
                   if not _frontier_facet_bounded(row, field)]
        existing = list(row.get("gaps") or [])
        if missing or existing:
            frontier_gaps[rid] = {
                "missing_facets": missing,
                "declared_gaps": existing,
            }
    wp1 = {
        "description": "Mechanic frontier",
        "met": not frontier_gaps and wp1_findings_ok,
        "findings": wp1_findings,
        "unfinished_findings": wp1_unfinished,
        "mechanics": ownership["totals"]["mechanics"],
        "address_bound": ownership["totals"]["bound"],
        "required_facets": list(REQUIRED_FRONTIER_FIELDS),
        "rows_with_open_frontier": frontier_gaps,
    }

    # WP2: presence of a few representative entries cannot prove that every
    # active subsystem campaign's state is in scope.  The explicit campaign
    # manifest is the future exhaustive boundary and must account for all listed
    # state IDs or carry evidence-backed blockers.
    wp2_findings = [
        "mechanic_ownership_frontier", "semantic_lifetime_complete",
        "camera_is_a_derived_output", "render_descriptors_are_loader_patched",
        "sfx_dispatch_interface",
    ]
    wp2_findings_ok, wp2_unfinished = finding_status(wp2_findings, audit_rows)
    owners = {e.get("owner") for e in semantic_entries.values() if e.get("owner")}
    missing_scope_groups = sorted(
        scope for scope, accepted in REQUIRED_STATE_SCOPES.items()
        if owners.isdisjoint(accepted)
    )
    scope_manifest_path = "config/phase3_campaign_state_scope.yaml"
    scope_manifest = optional_yaml(scope_manifest_path)
    scope_manifest_gaps = []
    if not scope_manifest:
        scope_manifest_gaps.append(f"missing exhaustive scope manifest: {scope_manifest_path}")
    else:
        campaigns = scope_manifest.get("campaigns") or []
        declared_ids = {sid for row in campaigns for sid in row.get("state_ids", [])}
        unknown_ids = sorted(declared_ids - set(semantic_entries))
        unbounded = sorted(
            row.get("id", "<unnamed>") for row in campaigns
            if not row.get("state_ids") and not _structured_blocker(row.get("blocker"))
        )
        if unknown_ids:
            scope_manifest_gaps.append(f"unknown state IDs: {unknown_ids}")
        if unbounded:
            scope_manifest_gaps.append(f"campaigns without state or blocker: {unbounded}")
        if not scope_manifest.get("exhaustive"):
            scope_manifest_gaps.append("scope manifest does not declare exhaustive: true")
    lifetime_missing = sorted(set(semantic_entries) - set(lifetime["entries"]))
    wp2 = {
        "description": "Semantic-state registry",
        "met": not missing_scope_groups and not scope_manifest_gaps
        and not lifetime_missing and wp2_findings_ok,
        "findings": wp2_findings,
        "unfinished_findings": wp2_unfinished,
        "addressed_entries": len(semantic_entries),
        "lifetime_entries": len(lifetime["entries"]),
        "required_scope_groups": sorted(REQUIRED_STATE_SCOPES),
        "missing_scope_groups": missing_scope_groups,
        "scope_manifest": scope_manifest_path,
        "scope_manifest_gaps": scope_manifest_gaps,
        "lifetime_missing": lifetime_missing,
    }

    # WP3: the three decoded dispatch tables are useful but are not an exhaustive
    # census of every native selector domain and all consumers.
    wp3_findings = [
        "player_and_contact_integrators", "render_descriptors_are_loader_patched",
        "sfx_dispatch_interface", "indirect_dispatch_map",
    ]
    wp3_findings_ok, wp3_unfinished = finding_status(wp3_findings, audit_rows)
    domain_path = "analysis/phase3_native_domains.json"
    retained_domains = optional_json(domain_path)
    domains = native_domains.build() if retained_domains else None
    domain_gaps = []
    if not domains:
        domain_gaps.append(f"missing exhaustive domain/consumer census: {domain_path}")
        domain_rows = []
    else:
        retained_cmp = dict(retained_domains)
        computed_cmp = dict(domains)
        retained_cmp.pop("generated", None)
        computed_cmp.pop("generated", None)
        if retained_cmp != computed_cmp:
            domain_gaps.append("retained domain census is stale")
        domain_rows = domains.get("domains") or []
        for row in domain_rows:
            missing = [key for key in ("id", "width", "domain", "consumers", "evidence")
                       if not row.get(key)]
            if missing:
                domain_gaps.append(f"{row.get('id', '<unnamed>')}: missing {missing}")
            if row.get("status") != "resolved" and not _structured_blocker(row.get("blocker")):
                domain_gaps.append(
                    f"{row.get('id', '<unnamed>')}: unresolved without bounded blocker")
        if not domains.get("exhaustive"):
            domain_gaps.append("domain census does not declare exhaustive: true")
        domain_gaps.extend(domains.get("independent_universe_errors") or [])
    wp3 = {
        "description": "Fixed-width native domains and consumers",
        "met": not domain_gaps and wp3_findings_ok,
        "findings": wp3_findings,
        "unfinished_findings": wp3_unfinished,
        "domain_census": domain_path,
        "domain_rows": len(domain_rows),
        "domain_gaps": domain_gaps,
        "independent_universe": domains.get("counts") if domains else {},
        "decoded_dispatch_tables": sorted(dispatch["tables"]),
    }

    # WP4 allows explicit unresolved/refused entries.  Verify those reasons from
    # low-level rows rather than merely summing headline counters.
    wp4_findings = [
        "indirect_dispatch_map", "jr_dispatch_frontier_resolved",
        "jalr_callback_slots", "actor_event_callback_field", "overlay_boundary_map",
    ]
    wp4_findings_ok, wp4_unfinished = finding_status(wp4_findings, audit_rows)
    jr_classified = (
        jr["classification"]["table_dispatch"]
        + jr["classification"]["computed_code_jump"]
        + jr["classification"]["unresolved"]
    ) == jr["jr_sites"]
    jr_unresolved = jr.get("failed") or {}
    jr_reasons_complete = (
        len(jr_unresolved) == jr["classification"]["unresolved"]
        and all(str(row.get("reason") or "").strip() for row in jr_unresolved.values())
    )
    jalr_sites = jalr.get("sites") or {}
    jalr_unresolved = [row for row in jalr_sites.values() if row.get("class") == "unresolved"]
    jalr_classified = sum(jalr["classification"].values()) == jalr["jalr_sites"]
    jalr_reasons_complete = (
        len(jalr_unresolved) == jalr["classification"]["unresolved"]
        and all(str(row.get("why") or "").strip() for row in jalr_unresolved)
    )
    dynamic_program_bound = (
        "mover_vm_opcodes" in dispatch["tables"]
        and "original.mover_vm_program_bank" in semantic_entries
    )
    overlay_bound = overlay.get("overlays") == len(overlay.get("map") or {})
    wp4 = {
        "description": "Indirect dispatch, callbacks, overlays",
        "met": jr_classified and jr_reasons_complete and jalr_classified
        and jalr_reasons_complete and dynamic_program_bound and overlay_bound
        and wp4_findings_ok,
        "findings": wp4_findings,
        "unfinished_findings": wp4_unfinished,
        "indirect_sites_total": dispatch["indirect_sites"]["total"],
        "jr_sites": jr["jr_sites"],
        "jalr_sites": jalr["jalr_sites"],
        "jr_classified": jr_classified,
        "jr_unresolved_reasons_complete": jr_reasons_complete,
        "jalr_classified": jalr_classified,
        "jalr_unresolved_reasons_complete": jalr_reasons_complete,
        "dynamic_program_selection_bound": dynamic_program_bound,
        "overlays": overlay.get("overlays"),
        "overlay_rows": len(overlay.get("map") or {}),
    }

    # WP5 names twelve distinct record families.  A generic actor record may be
    # the substrate for later family-specific views, but it does not silently
    # stand in for enemy/projectile/seed layouts without an explicit declaration.
    wp5_findings = [
        "player_and_contact_integrators", "actor_motion_and_y_disproof",
        "camera_is_a_derived_output", "render_descriptors_are_loader_patched",
        "sfx_dispatch_interface",
    ]
    wp5_findings_ok, wp5_unfinished = finding_status(wp5_findings, audit_rows)
    represented = record_families(record_cfg)
    missing_record_families = sorted(f for f, ids in represented.items() if not ids)
    record_unknowns_visible = all(
        rec["unknown_bytes"] >= 0 and (rec["unknown_bytes"] == 0 or rec["unknown_spans"])
        for rec in records["records"].values()
    )
    wp5 = {
        "description": "Typed records without hidden unknowns",
        "met": not missing_record_families and record_unknowns_visible and wp5_findings_ok,
        "findings": wp5_findings,
        "unfinished_findings": wp5_unfinished,
        "required_record_families": list(REQUIRED_RECORD_FAMILIES),
        "represented_by": represented,
        "missing_record_families": missing_record_families,
        "record_unknowns_visible": record_unknowns_visible,
        "declared_records": sorted(records["records"]),
        "known_bytes": records["totals"]["known_bytes"],
        "total_bytes": records["totals"]["bytes"],
    }

    # WP6 needs a per-family ownership model (or the exit bullet's explicit,
    # evidence-backed blocker), not one contact-pool headroom measurement.
    wp6_findings = [
        "contact_pool_ttl_retirement", "transition_ownership_and_load_gap",
        "semantic_lifetime_complete", "bug_bar_thud_boss_bound",
    ]
    wp6_findings_ok, wp6_unfinished = finding_status(wp6_findings, audit_rows)
    ownership_model_gaps = {}
    cfg_by_id = {row["id"]: row for row in record_cfg["records"]}
    for family, record_ids in represented.items():
        if not record_ids:
            ownership_model_gaps[family] = ["record family is not represented"]
            continue
        family_ok = False
        family_reasons = []
        for rid in record_ids:
            row = cfg_by_id[rid]
            model = row.get("ownership_model") or {}
            missing = [key for key in OWNERSHIP_MODEL_FIELDS
                       if not _ownership_fact(model.get(key))]
            if not missing or _structured_blocker(row.get("ownership_blocker")):
                family_ok = True
                break
            family_reasons.append(f"{rid}: missing ownership_model fields {missing}")
        if not family_ok:
            ownership_model_gaps[family] = family_reasons
    occupancy = record_probe["records"]["contact_record"]["occupancy"]
    wp6 = {
        "description": "Allocation capacity, reuse, transfer, retirement, reset",
        "met": not ownership_model_gaps and wp6_findings_ok,
        "findings": wp6_findings,
        "unfinished_findings": wp6_unfinished,
        "required_model_fields": list(OWNERSHIP_MODEL_FIELDS),
        "ownership_model_gaps": ownership_model_gaps,
        "contact_capacity": occupancy["capacity"],
        "contact_peak_alloc_occupied": occupancy["alloc_occupied_max"],
        "anchors_used": record_probe["anchors_used"],
        "transition_laws": sorted(transition["laws"]),
    }

    # WP7 requires the exceptional/off-table paths themselves plus unload
    # ownership.  A prose gap naming Training is retained evidence of work still
    # open, not a reason to pass.
    wp7_findings = ["scene_asset_load_graph", "overlay_boundary_map"]
    wp7_findings_ok, wp7_unfinished = finding_status(wp7_findings, audit_rows)
    scene_gaps = list(scene_graph.get("gaps") or [])
    exceptional_routes = scene_graph.get("exceptional_routes") or []
    unload_graph = scene_graph.get("unload_graph") or {}
    exceptional_complete = bool(exceptional_routes) and all(
        row.get("scene") is not None and row.get("owner") and row.get("route")
        and row.get("evidence") for row in exceptional_routes
    )
    unload_complete = bool(unload_graph) and all(
        key in unload_graph for key in ("entry", "exit", "overwrite", "exceptions")
    )
    wp7 = {
        "description": "Scene, overlay, and resource load/unload graph",
        "met": not scene_gaps and exceptional_complete and unload_complete
        and wp7_findings_ok,
        "findings": wp7_findings,
        "unfinished_findings": wp7_unfinished,
        "table_scenes": len(scene_graph["scenes"]),
        "overlays": overlay["overlays"],
        "gaps": scene_gaps,
        "exceptional_routes_complete": exceptional_complete,
        "unload_graph_complete": unload_complete,
    }

    # WP8 explicitly calls for caller/callee and asset-provenance reports.  The
    # current xref report supplies reader/writer data only.
    wp8_findings = [
        "static_reader_writer_xrefs", "scene_asset_load_graph",
        "mechanic_ownership_frontier", "overlay_boundary_map",
    ]
    wp8_findings_ok, wp8_unfinished = finding_status(wp8_findings, audit_rows)
    call_report_path = "analysis/phase3_call_graph.json"
    asset_report_path = "analysis/phase3_asset_provenance.json"
    call_report = optional_json(call_report_path)
    asset_report = optional_json(asset_report_path)
    call_report_ok = bool(call_report) and bool(call_report.get("callers")) \
        and bool(call_report.get("callees")) and call_report.get("exhaustive") is True
    asset_report_ok = bool(asset_report) and bool(asset_report.get("assets")) \
        and asset_report.get("exhaustive") is True
    reader_writer_ok = (
        xrefs["entries_owned"] == len(semantic_entries)
        and not xrefs["declared_writer_contradictions"]
    )
    wp8 = {
        "description": "Machine-readable xrefs and asset provenance",
        "met": reader_writer_ok and call_report_ok and asset_report_ok
        and wp8_findings_ok,
        "findings": wp8_findings,
        "unfinished_findings": wp8_unfinished,
        "reader_writer_report_complete": reader_writer_ok,
        "entries_without_static_xrefs": xrefs["entries_without_static_xrefs"],
        "caller_callee_report": call_report_path,
        "caller_callee_report_complete": call_report_ok,
        "asset_provenance_report": asset_report_path,
        "asset_provenance_report_complete": asset_report_ok,
    }

    # WP9 requires a contradiction ledger and reconciled downstream prose.  A
    # COMPLETE label is valid only when the hub row names the binding WP1-WP9
    # closure and retains A07 as an external lead rather than an absolute disproof.
    wp9_findings = ["spin_move_bounded_negative", "bug_bar_thud_boss_bound"]
    wp9_findings_ok, wp9_unfinished = finding_status(wp9_findings, audit_rows)
    contradiction_path = "analysis/phase3_contradictions.json"
    contradictions = optional_json(contradiction_path)
    contradiction_gaps = []
    if not contradictions:
        contradiction_gaps.append(f"missing contradiction ledger: {contradiction_path}")
    else:
        open_rows = [row.get("id", "<unnamed>") for row in contradictions.get("contradictions", [])
                     if row.get("status") not in ("reconciled", "bounded")]
        if open_rows:
            contradiction_gaps.append(f"unreconciled rows: {open_rows}")
        if not contradictions.get("sources_checked"):
            contradiction_gaps.append("ledger does not enumerate checked sources")
    hub = (ROOT / "ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md").read_text()
    phase_note = (ROOT / "ObsidianVault/Playbooks/Game Solving Roadmap/Phase 3 - Reconstruct Semantic Architecture and State Ownership.md").read_text()
    documentation_contradictions = []
    if "A07 spin DISPROVEN" in hub or "A07_spin — DISPROVEN" in phase_note:
        documentation_contradictions.append("roadmap still calls A07 disproven")
    phase3_hub_row = next(
        (line for line in hub.splitlines() if line.startswith("| 3 | [[Phase 3")), ""
    )
    if "WP1-WP9" not in phase3_hub_row or "external_lead" not in phase3_hub_row:
        documentation_contradictions.append(
            "hub Phase 3 row lacks WP1-WP9 closure and the bounded A07 status"
        )
    if "- [ ]" in phase_note:
        documentation_contradictions.append("Phase 3 work packages remain unchecked")
    if "Still owed:" in phase_note or "WP8/WP9" in phase_note:
        documentation_contradictions.append("Phase note still names binding work as owed")
    spin_row = mechanics["A07_spin"]
    machine_status_ok = (
        spin_row["status"] == "external_lead"
        and mechanics["F09_bug_bar"]["status"] == "partial"
        and mechanics["D18_thud"]["status"] == "partial"
        and findings["spin_move_bounded_negative"]["confidence"] == "partial"
    )
    wp9 = {
        "description": "Contradictions reconciled and superseded",
        "met": machine_status_ok and not contradiction_gaps
        and not documentation_contradictions and wp9_findings_ok,
        "findings": wp9_findings,
        "unfinished_findings": wp9_unfinished,
        "machine_statuses_reconciled": machine_status_ok,
        "contradiction_ledger": contradiction_path,
        "contradiction_gaps": contradiction_gaps,
        "documentation_contradictions": documentation_contradictions,
        "a07_status": spin_row["status"],
        "f09_status": mechanics["F09_bug_bar"]["status"],
        "d18_status": mechanics["D18_thud"]["status"],
    }

    packages = {
        "WP1": wp1, "WP2": wp2, "WP3": wp3, "WP4": wp4, "WP5": wp5,
        "WP6": wp6, "WP7": wp7, "WP8": wp8, "WP9": wp9,
    }
    return {
        "_comment": "Phase-3 WP1-WP9 coverage computed from low-level evidence. "
                    "No roadmap checkbox, finding-audit verdict, or representative "
                    "sample can silently satisfy an exhaustive work package. "
                    "Regenerate: python3 tools/phase3_coverage_matrix.py",
        "generated": date.today().isoformat(),
        "overall_met": all(pkg["met"] for pkg in packages.values()),
        "work_packages": packages,
    }


def main() -> int:
    doc = build_matrix()
    out = ROOT / "analysis/phase3_coverage_matrix.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[phase3-coverage] {'MET' if doc['overall_met'] else 'OPEN'}")
    for key, pkg in doc["work_packages"].items():
        print(f"  {'MET ' if pkg['met'] else 'OPEN'} {key}: {pkg['description']}")
    return 0 if doc["overall_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
