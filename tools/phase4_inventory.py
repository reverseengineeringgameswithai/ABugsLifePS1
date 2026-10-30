#!/usr/bin/env python3
"""Inventory Phase-4 campaigns, evidence, fixtures, knowledge, and source surfaces."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import phase4_common as common
import phase4_coverage
import phase4_priority

CAMPAIGN_OUTPUT = common.ROOT / "analysis/phase4_campaign_inventory.json"

# These generated artifacts consume this inventory (directly or through the
# queue) and are guarded by their own semantic recomputation tests. Recording
# their byte hashes here would create a self-invalidating hash cycle.
SEMANTIC_OUTPUTS = {
    "analysis/phase4_campaign_inventory.json",
    # The evidence-DAG receipt consumes the campaign inventory identity. Hashing
    # it back into that inventory would create a false self-invalidating cycle.
    "analysis/phase4_evidence_dag.json",
    "analysis/phase4_gate.json",
    "analysis/phase4_movie_priority_queue.json",
    "analysis/phase4_offline_opportunity_queue.json",
    "analysis/phase4_live_escalations.json",
}
FIXTURE_OUTPUT = common.ROOT / "analysis/phase4_fixture_audit.json"
KNOWLEDGE_OUTPUT = common.ROOT / "analysis/phase4_knowledge_audit.json"


def _source_maps() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    pattern = re.compile(r"(?:^|_)([0-9a-fA-F]{8})(?:_|\.|$)")
    c_map: dict[str, list[str]] = {}
    asm_map: dict[str, list[str]] = {}
    for base, suffix, destination in (
        (common.ROOT / "src_re", ".c", c_map),
        (common.ROOT / "src", ".c", c_map),
        (common.ROOT / "asm", ".s", asm_map),
    ):
        if not base.exists():
            continue
        for path in base.rglob(f"*{suffix}"):
            match = pattern.search(path.name)
            if match:
                address = "0x" + match.group(1).lower()
                destination.setdefault(address, []).append(
                    str(path.relative_to(common.ROOT)))
    return c_map, asm_map


def _artifact_source_dependency_gaps(outputs: set[str]) -> list[str]:
    """Recompute retained artifact source pins instead of trusting prose/gates."""
    gaps: list[str] = []
    for artifact_rel in sorted(outputs):
        artifact = common.ROOT / artifact_rel
        if artifact.suffix != ".json" or not artifact.is_file():
            continue
        try:
            document = json.loads(artifact.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            gaps.append(f"{artifact_rel}: cannot audit JSON source dependencies: {exc}")
            continue
        dependencies = document.get("source_dependencies")
        if dependencies is None:
            continue
        if not isinstance(dependencies, dict):
            gaps.append(f"{artifact_rel}: source_dependencies is not a mapping")
            continue
        for source_rel, expected in sorted(
                dependencies.items(), key=lambda item: str(item[0])):
            if not isinstance(source_rel, str) or Path(source_rel).is_absolute():
                gaps.append(
                    f"{artifact_rel}: invalid source dependency path {source_rel!r}")
                continue
            source = common.ROOT / source_rel
            try:
                source.resolve().relative_to(common.ROOT.resolve())
            except ValueError:
                gaps.append(
                    f"{artifact_rel}: source dependency escapes repository: "
                    f"{source_rel!r}")
                continue
            actual = common.sha256(source) if source.is_file() else None
            if actual != expected:
                gaps.append(
                    f"{artifact_rel}: {source_rel}: expected {expected}, "
                    f"observed {actual or 'missing'}")
    return gaps


def build_fixture_audit(mechanics: dict | None = None,
                        registry: dict | None = None) -> dict:
    mechanics = mechanics or common.load_yaml(common.BASELINE_PATH)
    registry = registry or common.load_yaml(common.REGISTRY_PATH)
    external = common.load_json(common.FIXTURE_SET_PATH).get("entries") or {}
    phase2 = common.load_json("analysis/phase2_row_coverage.json")
    rows = common.baseline_rows(mechanics)
    fixture_rows: dict[str, dict] = {}
    missing_pins: list[str] = []
    missing_bytes: list[str] = []
    hash_mismatches: list[str] = []
    missing_consumers: list[str] = []
    row_reports: dict[str, dict] = {}

    for row_id, row in rows.items():
        references = row.get("fixture_have") or []
        eligible, ineligible, tracked_evidence = [], [], []
        for rel in references:
            pin = external.get(rel)
            path = common.ROOT / rel
            tracked = common.git_tracked(rel)
            key = rel
            if pin:
                actual_hash = common.sha256(path) if path.is_file() else None
                hash_ok = actual_hash == pin.get("sha256")
                size_ok = path.is_file() and path.stat().st_size == pin.get("size")
                consumer = f"mechanics:{row_id}"
                consumer_ok = consumer in (pin.get("consumers") or [])
                fixture_rows.setdefault(key, {
                    "media_class": pin.get("media_class"),
                    "sha256": pin.get("sha256"),
                    "size": pin.get("size"),
                    "present": path.is_file(),
                    "hash_matches": hash_ok,
                    "size_matches": size_ok,
                    "rows": [],
                })["rows"].append(row_id)
                if not path.is_file():
                    missing_bytes.append(rel)
                elif not hash_ok or not size_ok:
                    hash_mismatches.append(rel)
                if not consumer_ok:
                    missing_consumers.append(f"{rel}: {consumer}")
                if pin.get("media_class") in {"pristine", "pristine_serial"}:
                    eligible.append(rel)
                else:
                    ineligible.append(rel)
            elif tracked:
                tracked_evidence.append(rel)
                fixture_rows.setdefault(key, {
                    "media_class": "tracked_derived_evidence",
                    "sha256": common.sha256(path) if path.is_file() else None,
                    "size": path.stat().st_size if path.is_file() else None,
                    "present": path.is_file(),
                    "hash_matches": path.is_file(),
                    "size_matches": path.is_file(),
                    "rows": [],
                })["rows"].append(row_id)
                if not path.is_file():
                    missing_bytes.append(rel)
            else:
                missing_pins.append(f"{row_id}: {rel}")
        phase2_row = (phase2.get("rows") or {}).get(row_id)
        row_reports[row_id] = {
            "references": references,
            "pristine_eligible_references": eligible,
            "non_pristine_references": ineligible,
            "tracked_derived_evidence": tracked_evidence,
            "phase2_low_level_status": phase2_row,
            "has_phase2_pristine_trigger": (
                isinstance(phase2_row, dict)
                and phase2_row.get("status") == "pristine_trigger"),
        }

    embedded_unpinned: list[str] = []
    for proof in registry.get("reviewed_absence") or []:
        for fixture_id in proof.get("oracle_fixtures") or []:
            if fixture_id not in external:
                embedded_unpinned.append(f"absence:{proof.get('row_id')}:{fixture_id}")
    for campaign in registry.get("child_campaigns") or []:
        for fixture_id in campaign.get("oracle_fixtures") or []:
            if fixture_id not in external:
                embedded_unpinned.append(f"campaign:{campaign.get('id')}:{fixture_id}")

    phase2_rows = set(phase2.get("rows") or {})
    phase2_coverage_gaps = sorted(set(rows) ^ phase2_rows)
    structural_gaps = {
        "missing_central_pins": sorted(set(missing_pins)),
        "missing_declared_bytes": sorted(set(missing_bytes)),
        "hash_or_size_mismatches": sorted(set(hash_mismatches)),
        "missing_mechanic_consumers": sorted(set(missing_consumers)),
        "embedded_fixture_ids_without_central_pin": sorted(set(embedded_unpinned)),
        "phase2_row_set_mismatch": phase2_coverage_gaps,
    }
    return {
        "_comment": "Phase-4 fixture audit joins every baseline fixture reference "
                    "to the central preservation set and current bytes. Non-pristine "
                    "leads remain visible but cannot satisfy campaign oracle evidence. "
                    "Regenerate: python3 tools/phase4_inventory.py",
        "generated": date.today().isoformat(),
        "inputs": {
            "mechanics_sha256": common.sha256(common.BASELINE_PATH),
            "fixture_set_sha256": common.sha256(common.FIXTURE_SET_PATH),
            "phase2_row_coverage_sha256": common.sha256(
                common.ROOT / "analysis/phase2_row_coverage.json"),
        },
        "rows": row_reports,
        "fixtures": dict(sorted(fixture_rows.items())),
        "counts": {
            "baseline_rows": len(rows),
            "unique_fixture_references": len(fixture_rows),
            "rows_with_phase2_pristine_trigger": sum(
                report["has_phase2_pristine_trigger"] for report in row_reports.values()),
            "rows_with_phase2_blocker": sum(
                (report.get("phase2_low_level_status") or {}).get("status") == "blocked"
                for report in row_reports.values()),
        },
        "structural_gaps": structural_gaps,
        "structural_ready": not any(structural_gaps.values()),
    }


def build_knowledge_audit(registry: dict | None = None,
                          mechanics: dict | None = None,
                          findings_doc: dict | None = None) -> dict:
    registry = registry or common.load_yaml(common.REGISTRY_PATH)
    mechanics = mechanics or common.load_yaml(common.BASELINE_PATH)
    findings_doc = findings_doc or common.load_yaml(common.FINDINGS_PATH)
    inventory_config = common.load_yaml(common.INVENTORY_CONFIG_PATH)
    registry_gaps = common.validate_registry(registry, mechanics)
    findings = common.finding_index(findings_doc)
    finding_gaps = {
        finding_id: common.audit_finding(finding)
        for finding_id, finding in findings.items()
    }
    campaign_gaps = {
        campaign.get("id", "<missing>"): common.audit_campaign(
            campaign, registry, findings)
        for campaign in registry.get("child_campaigns") or []
        if campaign.get("status") == "completed"
    }
    absence_gaps = {
        proof.get("row_id", "<missing>"): common.audit_absence(proof)
        for proof in registry.get("reviewed_absence") or []
    }
    note_gaps = []
    for rel in inventory_config.get("notes") or []:
        if not (common.ROOT / rel).is_file():
            note_gaps.append(f"missing note: {rel}")
        elif not common.git_tracked(rel):
            note_gaps.append(f"untracked note: {rel}")
    phase4_note = common.ROOT / (
        "ObsidianVault/Playbooks/Game Solving Roadmap/"
        "Phase 4 - Solve Every Gameplay and Engine Subsystem.md")
    prose_gaps = []
    phase4_text = phase4_note.read_text()
    if re.search(r"(?mi)^status:\s*(complete|closed|solved)\s*$", phase4_text):
        prose_gaps.append("Phase-4 note frontmatter claims closure before the machine gate")
    checked_packages = re.findall(r"(?m)^- \[[xX]\] (.+)$", phase4_text)
    package_prefixes = {
        "WP1": "Prioritize campaigns by dependency centrality",
        "WP2": "Solve core player/input/lifecycle",
        "WP3": "Run collectible, plant, enemy, and objective campaigns",
        "WP4": "Complete each regular enemy family and boss individually",
        "WP5": "Complete special-stage mechanics and exceptional overlay paths",
        "WP6": "Update [[Whole-Game Mechanics Baseline]] only",
    }
    coverage = phase4_coverage.build(registry, mechanics, findings_doc)
    expected_checked = [
        package_prefixes[name]
        for name, row in coverage["work_packages"].items() if row["met"]]
    observed_checked = []
    for text in checked_packages:
        match = next((prefix for prefix in package_prefixes.values()
                      if text.startswith(prefix)), None)
        observed_checked.append(match or text)
    if observed_checked != expected_checked:
        prose_gaps.append(
            "Phase-4 checked work packages differ from machine derivation: "
            f"observed={observed_checked} expected={expected_checked}")
    handoff = common.handoff_constraints(mechanics)
    gaps = {
        "registry": registry_gaps,
        "findings": {key: value for key, value in finding_gaps.items() if value},
        "completed_campaigns": {
            key: value for key, value in campaign_gaps.items() if value},
        "reviewed_absence": {
            key: value for key, value in absence_gaps.items() if value},
        "notes": note_gaps,
        "prose_stronger_than_machine": prose_gaps,
        "phase3_handoff": [] if handoff["preserved"] else [
            key for key, value in handoff["checks"].items() if not value],
    }
    return {
        "_comment": "Phase-4 knowledge audit applies the inherited eight-part "
                    "finding contract, child-campaign evidence contract, vault "
                    "placement, and Phase-3 confidence carry. Regenerate: python3 "
                    "tools/phase4_inventory.py",
        "generated": date.today().isoformat(),
        "findings": finding_gaps,
        "completed_campaigns": campaign_gaps,
        "reviewed_absence": absence_gaps,
        "phase3_handoff": handoff,
        "gaps": gaps,
        "structural_ready": not any(gaps.values()),
    }


def build_campaign_inventory(fixture_audit: dict | None = None,
                             knowledge_audit: dict | None = None) -> dict:
    fixture_audit = fixture_audit or build_fixture_audit()
    knowledge_audit = knowledge_audit or build_knowledge_audit()
    registry = common.load_yaml(common.REGISTRY_PATH)
    mechanics = common.load_yaml(common.BASELINE_PATH)
    declaration = common.load_yaml(common.INVENTORY_CONFIG_PATH)
    ownership = common.load_json("analysis/phase3_ownership_graph.json")
    phase2 = common.load_json("analysis/phase2_row_coverage.json")
    functions_doc = common.load_json("analysis/functions.json")
    census = {row["start"].lower(): row for row in functions_doc.get("functions") or []}
    c_map, asm_map = _source_maps()
    owners, _ = common.primary_owners(registry)

    declared_generators = {
        row["path"]: row for row in declaration.get("generators") or []}
    declared_outputs = {
        output for row in declared_generators.values()
        for output in row.get("outputs") or []
    }
    artifact_source_dependency_gaps = _artifact_source_dependency_gaps(
        declared_outputs)
    discovered_generators = {
        str(path.relative_to(common.ROOT))
        for path in (common.ROOT / "tools").glob("phase4_*.py")}
    discovered_outputs = {
        str(path.relative_to(common.ROOT))
        for path in (common.ROOT / "analysis").glob("phase4_*.json")}
    discovered_tests = {
        str(path.relative_to(common.ROOT))
        for path in (common.ROOT / "tests").glob("test_phase4_*.py")}
    discovered_schemas = {
        str(path.relative_to(common.ROOT))
        for path in (common.ROOT / "config").glob("phase4_*.yaml")}
    discovered_schemas |= {
        str(path.relative_to(common.ROOT))
        for path in (common.ROOT / "schemas" / "phase4").glob("*.ksy")}
    declared_tests = set(declaration.get("tests") or [])
    declared_schemas = set(declaration.get("schemas") or [])

    generator_rows: dict[str, dict] = {}
    missing_outputs, untracked_paths = [], []
    for rel, spec in sorted(declared_generators.items()):
        path = common.ROOT / rel
        if not common.git_tracked(rel):
            untracked_paths.append(rel)
        outputs = []
        for output in spec.get("outputs") or []:
            output_path = common.ROOT / output
            exists = output_path.is_file()
            tracked = common.git_tracked(output)
            if not exists:
                missing_outputs.append(output)
            if exists and not tracked:
                untracked_paths.append(output)
            outputs.append({
                "path": output,
                "exists": exists,
                "tracked": tracked,
                "sha256": (common.sha256(output_path)
                           if exists and output not in SEMANTIC_OUTPUTS else None),
                "comparison": ("semantic_recompute"
                               if output in SEMANTIC_OUTPUTS else "byte_exact"),
            })
        generator_rows[rel] = {
            "classification": spec["classification"],
            "tracked": common.git_tracked(rel),
            "sha256": common.sha256(path) if path.is_file() else None,
            "outputs": outputs,
        }

    for rel in sorted(declared_tests | declared_schemas | set(declaration.get("notes") or [])):
        if not common.git_tracked(rel):
            untracked_paths.append(rel)

    source_gaps: list[str] = []
    row_inventory: dict[str, dict] = {}
    ownership_rows = ownership.get("rows") or {}
    for row_id, mechanic in common.baseline_rows(mechanics).items():
        frontier = ownership_rows.get(row_id, {})
        source_surfaces = []
        for function in frontier.get("functions") or []:
            address = str(function.get("function_start") or function.get("address") or "").lower()
            census_row = census.get(address, {})
            c_paths = sorted(c_map.get(address, []))
            asm_paths = sorted(asm_map.get(address, []))
            match = census_row.get("match")
            if match == "c" and not c_paths:
                source_gaps.append(f"{row_id}:{address}: census says C but source is absent")
            if match == "asm" and not asm_paths:
                source_gaps.append(f"{row_id}:{address}: census says ASM but source is absent")
            source_surfaces.append({
                "address": address,
                "name": function.get("name") or census_row.get("name"),
                "classification": function.get("classification") or census_row.get("classification"),
                "decompilation_status": match or "missing",
                "semantic_c": c_paths,
                "asm": asm_paths,
            })
        row_inventory[row_id] = {
            "family": owners.get(row_id),
            "dependency_of": sorted(
                family["id"] for family in registry.get("families") or []
                if row_id in (family.get("dependency_rows") or [])),
            "name": mechanic.get("name"),
            "baseline_status": mechanic.get("status"),
            "baseline_evidence_classes": mechanic.get("evidence") or [],
            "phase2_oracle": (phase2.get("rows") or {}).get(row_id),
            "frontier": {
                key: frontier.get(key) or [] for key in (
                    "functions", "state", "assets", "overlay", "readers",
                    "writers", "lifecycle")},
            "frontier_blockers": frontier.get("frontier_blockers") or {},
            "source_surfaces": source_surfaces,
            "downstream_consumers": {
                "reader_groups": len(frontier.get("readers") or []),
                "writer_groups": len(frontier.get("writers") or []),
            },
            "fixtures": (fixture_audit.get("rows") or {}).get(row_id),
        }

    gaps = {
        "missing_generator_declarations": sorted(
            discovered_generators - set(declared_generators)),
        "stale_generator_declarations": sorted(
            set(declared_generators) - discovered_generators),
        "orphan_artifacts": sorted(discovered_outputs - declared_outputs),
        "missing_declared_outputs": sorted(set(missing_outputs)),
        "missing_test_declarations": sorted(discovered_tests - declared_tests),
        "stale_test_declarations": sorted(declared_tests - discovered_tests),
        "missing_schema_declarations": sorted(discovered_schemas - declared_schemas),
        "stale_schema_declarations": sorted(declared_schemas - discovered_schemas),
        "untracked_phase4_dependencies": sorted(set(untracked_paths)),
        "source_surface_mismatches": sorted(set(source_gaps)),
        "artifact_source_dependency_mismatches":
            artifact_source_dependency_gaps,
        "registry": common.validate_registry(registry, mechanics),
        "fixture_audit": [] if fixture_audit["structural_ready"] else [
            key for key, value in fixture_audit["structural_gaps"].items() if value],
        "knowledge_audit": [] if knowledge_audit["structural_ready"] else [
            key for key, value in knowledge_audit["gaps"].items() if value],
    }
    phase3_findings = common.load_yaml("config/phase3_findings.yaml").get("findings") or []
    phase4_findings = common.load_yaml(common.FINDINGS_PATH).get("findings") or []
    structural_gap_keys = set(gaps) - {"artifact_source_dependency_mismatches"}
    structural_ready = not any(gaps[key] for key in structural_gap_keys)
    artifact_source_dependencies_fresh = not artifact_source_dependency_gaps
    return {
        "_comment": "Complete Phase-4 inventory of twelve families, all runtime-"
                    "enumerated baseline rows, evidence/frontier/source surfaces, "
                    "fixtures, generators, artifacts, tests, schemas, findings, "
                    "notes, and downstream reader/writer consumers. Regenerate: "
                    "python3 tools/phase4_inventory.py",
        "generated": date.today().isoformat(),
        "inputs": {
            "mechanics_sha256": common.sha256(common.BASELINE_PATH),
            "campaign_registry_sha256": common.sha256(common.REGISTRY_PATH),
            "inventory_declaration_sha256": common.sha256(common.INVENTORY_CONFIG_PATH),
            "phase3_ownership_sha256": common.sha256(
                common.ROOT / "analysis/phase3_ownership_graph.json"),
            "function_census_sha256": common.sha256(
                common.ROOT / "analysis/functions.json"),
        },
        "families": registry.get("families") or [],
        "rows": row_inventory,
        "findings": {
            "phase3_handoff": [{
                "id": finding.get("id"),
                "confidence": finding.get("confidence"),
                "residuals": finding.get("residuals"),
            } for finding in phase3_findings],
            "phase4": phase4_findings,
        },
        "schemas": sorted(declared_schemas),
        "generators": generator_rows,
        "tests": sorted(declared_tests),
        "notes": declaration.get("notes") or [],
        "fixture_audit": "analysis/phase4_fixture_audit.json",
        "knowledge_audit": "analysis/phase4_knowledge_audit.json",
        "summary": {
            "families": len(registry.get("families") or []),
            "baseline_rows": len(row_inventory),
            "phase3_handoff_findings": len(phase3_findings),
            "phase4_findings": len(phase4_findings),
            "generators_declared": len(declared_generators),
            "generators_discovered": len(discovered_generators),
            "artifacts_declared": len(declared_outputs),
            "artifacts_discovered": len(discovered_outputs),
        },
        "gaps": gaps,
        "structural_ready": structural_ready,
        "artifact_source_dependencies_fresh":
            artifact_source_dependencies_fresh,
        "closure_ready": structural_ready and artifact_source_dependencies_fresh,
    }


def main() -> int:
    fixture = build_fixture_audit()
    knowledge = build_knowledge_audit()
    FIXTURE_OUTPUT.write_text(json.dumps(fixture, indent=1) + "\n")
    KNOWLEDGE_OUTPUT.write_text(json.dumps(knowledge, indent=1) + "\n")
    campaign = build_campaign_inventory(fixture, knowledge)
    CAMPAIGN_OUTPUT.write_text(json.dumps(campaign, indent=1) + "\n")
    print(
        f"[phase4-inventory] {campaign['summary']['baseline_rows']} rows, "
        f"{campaign['summary']['families']} families, "
        f"{campaign['summary']['generators_declared']}/"
        f"{campaign['summary']['generators_discovered']} generators; "
        f"{'CLOSURE-READY' if campaign['closure_ready'] else 'OPEN'}")
    for key, value in campaign["gaps"].items():
        if value:
            print(f"  {key}: {value[:8] if isinstance(value, list) else value}")
    return 0 if campaign["closure_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
