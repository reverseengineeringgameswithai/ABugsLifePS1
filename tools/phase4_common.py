#!/usr/bin/env python3
"""Shared fail-closed primitives for the Phase-4 campaign ratchet."""
from __future__ import annotations

import hashlib
import json
import operator
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "analysis/mechanics_baseline.yaml"
REGISTRY_PATH = ROOT / "config/phase4_campaigns.yaml"
FINDINGS_PATH = ROOT / "config/phase4_findings.yaml"
INVENTORY_CONFIG_PATH = ROOT / "config/phase4_inventory.yaml"
FIXTURE_SET_PATH = ROOT / "analysis/phase0_2_external_fixture_set.json"
BUILD_BASELINES_PATH = ROOT / "tools/build_baselines.json"
KNOWLEDGE_MATRIX_PATH = ROOT / "analysis/phase0_2_knowledge_closure.yaml"
ARCHIVE_TRACKED_MANIFEST = ROOT / ".abl_archive_tracked_manifest.json"

FAMILY_IDS = (
    "input_player_actions",
    "player_lifecycle",
    "movement_world_physics",
    "rendering_camera_animation",
    "seeds_plants_traversal_powers",
    "collectibles_equipment_rewards",
    "objects_events_hazards",
    "enemies_combat",
    "bosses_special_objectives",
    "hud_frontend_persistence",
    "audio_cinematics",
    "loading_overlays_resources",
)
CORE_FAMILIES = {
    "input_player_actions", "player_lifecycle", "movement_world_physics",
    "rendering_camera_animation", "objects_events_hazards",
    "audio_cinematics", "loading_overlays_resources",
}
CONFIDENCE = {"confirmed", "partial", "inferred", "disproven", "blocked"}
SELF_CERTIFYING_KEYS = {
    "pass", "passes", "passed", "complete", "completed", "solved", "status",
    "met", "gate_met", "overall_met", "closure_ready", "verified", "success",
}
EVIDENCE_GROUPS = (
    "oracle", "frontier", "lifecycle", "controls", "breadth",
    "dependencies", "source", "residuals", "exit_gate",
)


def load_yaml(path: Path | str) -> dict:
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return yaml.safe_load(path.read_text())


def load_json(path: Path | str) -> dict:
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def centrally_declared_external_paths() -> set[str]:
    """Return provisioned paths that remain external in a Git archive.

    An archive has no index, while the clean-checkout workflow intentionally
    adds hash-verified external files afterward.  Filesystem existence alone is
    therefore insufficient to decide whether a path was tracked.
    """
    external: set[str] = set()
    if BUILD_BASELINES_PATH.is_file():
        baselines = load_json(BUILD_BASELINES_PATH)
        external.update((baselines.get("pristine_media") or {}).keys())
        external.update(
            f"REBUILD/files/{rel}"
            for rel in (baselines.get("staged_inputs") or {}))
    if FIXTURE_SET_PATH.is_file():
        external.update((load_json(FIXTURE_SET_PATH).get("entries") or {}).keys())
    if KNOWLEDGE_MATRIX_PATH.is_file():
        matrix = load_yaml(KNOWLEDGE_MATRIX_PATH)
        external.update(
            row["path"] for key in (
                "external_local_media_inputs", "external_operator_fixture_inputs")
            for row in (matrix.get(key) or []))
    return external


@lru_cache(maxsize=1)
def archive_tracked_paths() -> frozenset[str] | None:
    if not ARCHIVE_TRACKED_MANIFEST.is_file():
        return None
    document = load_json(ARCHIVE_TRACKED_MANIFEST)
    if document.get("schema") != "abl-archive-tracked-manifest/1" or not isinstance(
            document.get("files"), dict):
        raise ValueError(f"invalid archive tracked manifest: {ARCHIVE_TRACKED_MANIFEST}")
    return frozenset(document["files"])


def git_tracked(rel: str) -> bool:
    indexed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if indexed.returncode == 0:
        return True
    repository = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if repository.returncode == 0:
        return False
    archive_paths = archive_tracked_paths()
    if archive_paths is not None:
        return rel in archive_paths
    # `git archive` contains only tracked paths before provisioning.  After the
    # declared external set is copied in, exclude those targets explicitly.
    return (ROOT / rel).is_file() and rel not in centrally_declared_external_paths()


def baseline_rows(doc: dict | None = None) -> dict[str, dict]:
    source = doc or load_yaml(BASELINE_PATH)
    return {row["id"]: row for row in source.get("rows") or []}


def primary_owners(registry: dict) -> tuple[dict[str, str], dict[str, list[str]]]:
    owners: dict[str, str] = {}
    duplicates: dict[str, list[str]] = {}
    for family in registry.get("families") or []:
        for row_id in family.get("primary_rows") or []:
            if row_id in owners:
                duplicates.setdefault(row_id, [owners[row_id]]).append(family["id"])
            else:
                owners[row_id] = family["id"]
    return owners, duplicates


def validate_registry(registry: dict | None = None,
                      mechanics: dict | None = None) -> list[str]:
    registry = registry or load_yaml(REGISTRY_PATH)
    mechanics = mechanics or load_yaml(BASELINE_PATH)
    errors: list[str] = []
    rows = baseline_rows(mechanics)
    families = registry.get("families") or []
    ids = [family.get("id") for family in families]
    numbers = [family.get("number") for family in families]
    if registry.get("schema") != "abl-phase4-campaigns/1":
        errors.append("wrong or missing campaign registry schema")
    if tuple(ids) != FAMILY_IDS:
        errors.append(f"family IDs/order differ from binding twelve families: {ids}")
    if numbers != list(range(1, 13)):
        errors.append(f"family numbers are not exactly 1..12: {numbers}")

    owners, duplicates = primary_owners(registry)
    for row_id, family_ids in sorted(duplicates.items()):
        errors.append(f"{row_id}: duplicated primary ownership {family_ids}")
    missing = sorted(set(rows) - set(owners))
    unknown = sorted(set(owners) - set(rows))
    if missing:
        errors.append(f"baseline rows without a primary family: {missing}")
    if unknown:
        errors.append(f"unknown primary row IDs: {unknown}")

    for family in families:
        fid = family.get("id", "<missing>")
        if family.get("priority_tier") not in {1, 2, 3}:
            errors.append(f"{fid}: invalid priority_tier")
        if len(str(family.get("title") or "").strip()) < 5:
            errors.append(f"{fid}: title is missing or too thin")
        for key in ("scope", "priority_basis"):
            if len(str(family.get(key) or "").strip()) < 20:
                errors.append(f"{fid}: {key} is missing or too thin")
        if not family.get("primary_rows"):
            errors.append(f"{fid}: no primary rows")
        for row_id in family.get("dependency_rows") or []:
            if row_id not in rows:
                errors.append(f"{fid}: unknown dependency row {row_id}")
            if row_id in (family.get("primary_rows") or []):
                errors.append(f"{fid}: {row_id} is both primary and dependency")

    campaigns = registry.get("child_campaigns")
    absence = registry.get("reviewed_absence")
    if not isinstance(campaigns, list):
        errors.append("child_campaigns must be a list")
        campaigns = []
    if not isinstance(absence, list):
        errors.append("reviewed_absence must be a list")
        absence = []
    seen_campaigns: set[str] = set()
    for campaign in campaigns:
        cid = campaign.get("id", "<missing>")
        if cid in seen_campaigns:
            errors.append(f"duplicate child campaign ID: {cid}")
        seen_campaigns.add(cid)
        fid = campaign.get("family")
        if fid not in FAMILY_IDS:
            errors.append(f"{cid}: unknown family {fid!r}")
        for row_id in campaign.get("rows") or []:
            if row_id not in rows:
                errors.append(f"{cid}: unknown row {row_id}")
            elif owners.get(row_id) != fid:
                errors.append(
                    f"{cid}: row {row_id} belongs to {owners.get(row_id)}, not {fid}")
    seen_absence: set[str] = set()
    for proof in absence:
        row_id = proof.get("row_id", "<missing>")
        if row_id in seen_absence:
            errors.append(f"duplicate reviewed-absence row: {row_id}")
        seen_absence.add(row_id)
        if row_id not in rows:
            errors.append(f"reviewed absence names unknown row: {row_id}")
    return errors


def _path_value(document: Any, path: str) -> Any:
    value = document
    for raw in path.split(".") if path else []:
        if isinstance(value, list):
            value = value[int(raw)]
        elif isinstance(value, dict):
            value = value[raw]
        else:
            raise KeyError(raw)
    return value


def audit_assertion(assertion: dict) -> list[str]:
    """Evaluate one low-level retained-evidence assertion.

    Campaigns cannot point at a convenient ``passes``/``complete``/``met``
    summary. They must name the exact retained leaf and pin the artifact bytes.
    """
    errors: list[str] = []
    if not isinstance(assertion, dict):
        return ["evidence assertion is not a mapping"]
    rel = str(assertion.get("artifact") or "")
    path_text = str(assertion.get("json_path") or "")
    expected_hash = str(assertion.get("sha256") or "")
    op_name = assertion.get("op")
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        return [f"unsafe or missing evidence artifact path: {rel!r}"]
    path = ROOT / rel
    if not path.is_file():
        return [f"evidence artifact missing: {rel}"]
    if not git_tracked(rel):
        errors.append(f"evidence artifact is not tracked: {rel}")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        errors.append(f"{rel}: assertion lacks an exact sha256 pin")
    elif sha256(path) != expected_hash:
        errors.append(f"{rel}: assertion sha256 does not match retained bytes")
    segments = {segment.lower() for segment in path_text.split(".") if segment}
    forbidden = sorted(segments & SELF_CERTIFYING_KEYS)
    if forbidden:
        errors.append(
            f"{rel}:{path_text}: self-certifying summary key(s) forbidden: {forbidden}")
    if path.suffix != ".json":
        errors.append(f"{rel}: low-level assertions currently require JSON evidence")
        return errors
    try:
        actual = _path_value(json.loads(path.read_text()), path_text)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        errors.append(f"{rel}:{path_text}: cannot resolve evidence leaf ({exc})")
        return errors
    expected = assertion.get("expected")
    ops = {
        "eq": operator.eq, "ne": operator.ne, "gt": operator.gt,
        "gte": operator.ge, "lt": operator.lt, "lte": operator.le,
        "contains": lambda left, right: right in left,
        "len_eq": lambda left, right: len(left) == right,
    }
    if op_name not in ops:
        errors.append(f"{rel}:{path_text}: unsupported assertion op {op_name!r}")
    else:
        try:
            if not ops[op_name](actual, expected):
                errors.append(
                    f"{rel}:{path_text}: {actual!r} does not satisfy "
                    f"{op_name} {expected!r}")
        except (TypeError, ValueError) as exc:
            errors.append(f"{rel}:{path_text}: assertion failed to evaluate ({exc})")
    return errors


def _strict_fixture_gaps(fixture_ids: list[str]) -> list[str]:
    fixtures = load_json(FIXTURE_SET_PATH).get("entries") or {}
    gaps: list[str] = []
    for fixture_id in fixture_ids:
        pin = fixtures.get(fixture_id)
        if not pin:
            gaps.append(f"fixture has no central declaration: {fixture_id}")
            continue
        if pin.get("media_class") not in {"pristine", "pristine_serial"}:
            gaps.append(
                f"fixture is not pristine-eligible: {fixture_id} "
                f"({pin.get('media_class')})")
    return gaps


def audit_finding(finding: dict) -> list[str]:
    errors: list[str] = []
    fid = finding.get("id", "<missing>")
    provenance = finding.get("provenance") or {}
    for key in (
        "media", "executable", "overlay", "assets", "trigger",
        "frame_or_cycle", "observation", "inference", "causal_confirmation",
    ):
        if not str(provenance.get(key) or "").strip():
            errors.append(f"{fid}: provenance.{key} missing")
    fixture_ids = provenance.get("fixtures") or []
    if not fixture_ids:
        errors.append(f"{fid}: provenance has no fixture IDs")
    errors.extend(f"{fid}: {gap}" for gap in _strict_fixture_gaps(fixture_ids))
    machine = finding.get("machine") or []
    if not machine:
        errors.append(f"{fid}: no authoritative machine representation")
    for rel in machine:
        if not (ROOT / rel).is_file() or not git_tracked(rel):
            errors.append(f"{fid}: machine path missing or untracked: {rel}")
    assertions = finding.get("evidence") or []
    if not assertions:
        errors.append(f"{fid}: no reproducible low-level evidence assertions")
    for assertion in assertions:
        errors.extend(f"{fid}: {gap}" for gap in audit_assertion(assertion))
    guard = str(finding.get("guard") or "")
    guard_file, _, guard_test = guard.partition("::")
    if not guard_file or not (ROOT / guard_file).is_file() or not git_tracked(guard_file):
        errors.append(f"{fid}: guard missing or untracked: {guard_file!r}")
    elif guard_test and f"def {guard_test}(" not in (ROOT / guard_file).read_text():
        errors.append(f"{fid}: named guard test is absent: {guard}")
    knowledge = finding.get("knowledge") or {}
    for placement, prefix in (
        ("canon", "ObsidianVault/Canon/"),
        ("experiment", "ObsidianVault/Experiments/"),
    ):
        rel = str(knowledge.get(placement) or "")
        if not rel.startswith(prefix) or not (ROOT / rel).is_file():
            errors.append(f"{fid}: invalid {placement} placement: {rel!r}")
    mods = knowledge.get("mods")
    if isinstance(mods, str):
        if not mods.startswith("ObsidianVault/Mods/") or not (ROOT / mods).is_file():
            errors.append(f"{fid}: invalid Mods placement: {mods!r}")
    elif not (isinstance(mods, dict) and mods.get("not_applicable") is True
              and str(mods.get("reason") or "").strip()):
        errors.append(f"{fid}: Mods placement needs a path or explicit not-applicable reason")
    contract = finding.get("mod_contract") or {}
    for key in (
        "owner", "readers", "writers", "valid_domains", "initialization",
        "reset", "retirement", "consumers", "capacity", "residency",
        "unsafe_assumptions",
    ):
        if not contract.get(key):
            errors.append(f"{fid}: mod_contract.{key} missing")
    if finding.get("confidence") not in CONFIDENCE:
        errors.append(f"{fid}: invalid confidence")
    if not str(finding.get("residuals") or "").strip():
        errors.append(f"{fid}: residuals/next experiment missing")
    if not isinstance(finding.get("supersedes"), list):
        errors.append(f"{fid}: supersedes must be an explicit list")
    return errors


def audit_campaign(campaign: dict, registry: dict, findings: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    cid = campaign.get("id", "<missing>")
    if campaign.get("status") != "completed":
        return [f"{cid}: status is not completed"]
    for key in ("scope", "non_scope", "exit_decision"):
        if len(str(campaign.get(key) or "").strip()) < 30:
            errors.append(f"{cid}: {key} is missing or too thin")
    note = str(campaign.get("note") or "")
    if not note.startswith("ObsidianVault/Playbooks/Game Solving Roadmap/") \
            or not (ROOT / note).is_file() or not git_tracked(note):
        errors.append(f"{cid}: child note missing, misplaced, or untracked: {note!r}")
    rows = campaign.get("rows") or []
    if not rows:
        errors.append(f"{cid}: no Phase-1 rows")
    owners, _ = primary_owners(registry)
    for row_id in rows:
        if owners.get(row_id) != campaign.get("family"):
            errors.append(f"{cid}: row {row_id} is outside owning family")
    fixture_ids = campaign.get("oracle_fixtures") or []
    if not fixture_ids:
        errors.append(f"{cid}: no pristine oracle fixture IDs")
    errors.extend(f"{cid}: {gap}" for gap in _strict_fixture_gaps(fixture_ids))
    evidence = campaign.get("evidence") or {}
    for group in EVIDENCE_GROUPS:
        assertions = evidence.get(group) or []
        if not assertions:
            errors.append(f"{cid}: evidence.{group} has no low-level assertions")
        for assertion in assertions:
            errors.extend(f"{cid}: {group}: {gap}" for gap in audit_assertion(assertion))
    controls = campaign.get("controls") or {}
    if not controls.get("positive") or not controls.get("negative"):
        errors.append(f"{cid}: native positive and negative controls are both required")
    breadth = campaign.get("breadth") or {}
    for dimension in ("stages", "variants", "lifecycles", "exceptional_paths"):
        if not breadth.get(dimension):
            errors.append(f"{cid}: breadth.{dimension} is empty")
    frontier = campaign.get("frontier") or {}
    for key in (
        "functions", "dispatch", "assets", "overlays", "typed_state",
        "readers", "writers", "unknown_boundaries",
    ):
        if not frontier.get(key):
            errors.append(f"{cid}: frontier.{key} is empty")
    lifecycle = campaign.get("lifecycle") or {}
    for key in (
        "initialization", "capacity", "allocation_reuse", "reset",
        "retirement", "unload_transition", "death_respawn", "persistence",
    ):
        value = lifecycle.get(key)
        if not value:
            errors.append(f"{cid}: lifecycle.{key} is unbounded")
    source = campaign.get("source_status") or {}
    for key in ("matching_c", "semantic_c", "asm", "schemas", "registries"):
        if not source.get(key):
            errors.append(f"{cid}: source_status.{key} missing")
    finding_ids = campaign.get("findings") or []
    if not finding_ids:
        errors.append(f"{cid}: no machine-linked findings")
    for fid in finding_ids:
        finding = findings.get(fid)
        if not finding:
            errors.append(f"{cid}: unknown finding {fid}")
        else:
            errors.extend(audit_finding(finding))
    residuals = campaign.get("bounded_residuals")
    if not isinstance(residuals, list):
        errors.append(f"{cid}: bounded_residuals must be an explicit list")
    for residual in residuals or []:
        if not all(str(residual.get(key) or "").strip()
                   for key in ("boundary", "evidence", "next_experiment")):
            errors.append(f"{cid}: malformed bounded residual")
        if residual.get("intersects_behavior") is not False:
            errors.append(f"{cid}: residual still intersects subsystem behavior")
    return errors


def audit_absence(proof: dict) -> list[str]:
    errors: list[str] = []
    row_id = proof.get("row_id", "<missing>")
    if proof.get("status") != "reviewed_absent":
        errors.append(f"{row_id}: absence status is not reviewed_absent")
    if len(str(proof.get("reason") or "").strip()) < 40:
        errors.append(f"{row_id}: absence reason is missing or too thin")
    errors.extend(
        f"{row_id}: {gap}" for gap in _strict_fixture_gaps(
            proof.get("oracle_fixtures") or []))
    for group in ("static_census", "positive_control", "negative_control", "breadth"):
        assertions = (proof.get("evidence") or {}).get(group) or []
        if not assertions:
            errors.append(f"{row_id}: absence evidence.{group} is empty")
        for assertion in assertions:
            errors.extend(f"{row_id}: {group}: {gap}" for gap in audit_assertion(assertion))
    note = str(proof.get("canon") or "")
    if not note.startswith("ObsidianVault/Canon/") or not (ROOT / note).is_file():
        errors.append(f"{row_id}: absence proof lacks a Canon note")
    return errors


def finding_index(doc: dict | None = None) -> dict[str, dict]:
    source = doc or load_yaml(FINDINGS_PATH)
    return {finding["id"]: finding for finding in source.get("findings") or []}


def handoff_constraints(mechanics: dict | None = None) -> dict:
    rows = baseline_rows(mechanics)
    spin_path = ROOT / "analysis/phase4_spin_heading.json"
    spin = load_json(spin_path) if spin_path.is_file() else {}
    spin_static = spin.get("static_census") or {}
    spin_live = spin.get("live") or {}
    spin_controls = (spin_live.get("controls") or {}).get("summary") or {}
    spin_breadth = (spin_live.get("breadth") or {}).get("summary") or {}
    spin_cold = spin_live.get("cold_boot") or {}
    a07_phase4_resolved = (
        rows.get("A07_spin", {}).get("status") == "solved"
        and spin.get("classification") == "positive_directional_heading_behavior"
        and (spin_static.get("law") or {}).get("input_history_storage") is None
        and len(spin_controls.get("anchors_with_opposite_signed_turn") or []) == 3
        and len(spin_breadth.get("heading_responsive_labels") or []) == 19
        and len(spin_breadth.get(
            "source_matches_neutral_special_field_labels") or []) == 19
        and spin_cold.get("pre_edit_player_block_equal") is True
        and spin_cold.get("post_edit_heading_differs") is True
    )
    checks: dict[str, bool] = {
        "A07_frontier_preserved_or_phase4_resolved": (
            rows.get("A07_spin", {}).get("status") == "external_lead"
            or a07_phase4_resolved),
        "F09_partial": rows.get("F09_bug_bar", {}).get("status") == "partial",
        "D18_partial": rows.get("D18_thud", {}).get("status") == "partial",
        "LEVEL10_external_lead": rows.get("F10_clover_forest", {}).get("status") == "external_lead",
    }
    callbacks = load_json("analysis/phase3_jalr_callbacks.json")
    checks["callback_ABI_unresolved_4"] = (
        callbacks.get("classification", {}).get("unresolved") == 4)
    phase3_findings = {
        finding["id"]: finding for finding in
        load_yaml("config/phase3_findings.yaml").get("findings") or []
    }
    checks["actor_vertical_partial"] = (
        phase3_findings.get("actor_motion_and_y_disproof", {}).get("confidence") == "partial")
    record_cfg = load_yaml("config/record_types.yaml")
    frontend = next((record for record in record_cfg.get("records") or []
                     if record.get("id") == "frontend_progress_record"), {})
    blocker = frontend.get("ownership_blocker") or {}
    checks["frontend_lifecycle_blocked"] = all(
        str(blocker.get(key) or "").strip()
        for key in ("missing_link", "evidence", "next_experiment"))
    return {
        "checks": checks,
        "preserved": all(checks.values()),
        "source_artifacts": [
            "analysis/mechanics_baseline.yaml",
            "analysis/phase3_jalr_callbacks.json",
            "config/phase3_findings.yaml",
            "config/record_types.yaml",
        ],
    }


def semantic_without_generated(document: dict) -> dict:
    result = dict(document)
    result.pop("generated", None)
    return result
