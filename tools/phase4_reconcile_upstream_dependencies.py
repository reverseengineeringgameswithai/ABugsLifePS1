#!/usr/bin/env python3
"""Reconcile dependency identities without rewriting retained live payloads."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import yaml

import phase4_common as common


OUTPUT = common.ROOT / "analysis/phase4_upstream_dependency_reconciliation.json"
LIVE_ESCALATION_CONFIG = common.ROOT / "config/phase4_live_escalations.yaml"
TARGETS = (
    ("analysis/phase4_checkpoint_respawn.json", {
        "analysis/phase0_2_external_fixture_set.json"}),
    ("analysis/phase4_respawn_row_provenance.json", {
        "analysis/phase4_checkpoint_respawn.json"}),
    ("analysis/phase4_respawn_writer_catalog.json", {
        "analysis/phase4_checkpoint_respawn.json"}),
    ("analysis/phase4_e08_hazard_outcomes.json", {
        "analysis/phase4_respawn_writer_catalog.json"}),
    ("analysis/phase4_lives_death_breadth.json", {
        "analysis/phase4_e08_hazard_outcomes.json"}),
    ("analysis/phase4_c16_bonus_death.json", {
        "analysis/phase0_2_external_fixture_set.json",
        "analysis/phase2_row_coverage.json"}),
    ("analysis/phase4_c16_thumper_death.json", {
        "analysis/phase2_row_coverage.json",
        "tools/phase4_c16_bonus_death.py"}),
    ("analysis/phase4_c16_flight_death.json", {
        "analysis/phase0_2_external_fixture_set.json",
        "analysis/phase4_respawn_writer_catalog.json",
        "tools/phase4_c16_bonus_death.py"}),
    ("analysis/phase4_thud_defeat.json", {
        "tools/phase4_c16_bonus_death.py"}),
    ("analysis/phase4_thud_arena.json", {
        "analysis/phase0_2_external_fixture_set.json",
        "analysis/phase4_thud_defeat.json"}),
    ("analysis/phase4_thud_completion.json", {
        "analysis/phase0_2_external_fixture_set.json",
        "analysis/phase4_thud_arena.json",
        "analysis/phase4_thud_defeat.json"}),
    ("analysis/phase4_thud_volley.json", {
        "analysis/phase0_2_external_fixture_set.json",
        "analysis/phase4_thud_defeat.json"}),
    ("analysis/phase4_c16_thud_boulder_death.json", {
        "analysis/phase4_thud_arena.json",
        "tools/phase4_c16_bonus_death.py"}),
    ("analysis/phase4_respawn_status_policy.json", {
        "analysis/phase0_2_external_fixture_set.json",
        "analysis/phase4_checkpoint_respawn.json"}),
    ("analysis/phase4_offline_fmv_batch.json", {
        "analysis/phase4_trace_capsule_set.json",
        "config/phase4_fmv.yaml"}),
    ("analysis/phase4_offline_bonus_objectives_batch.json", {
        "analysis/phase4_trace_capsule_set.json"}),
    ("analysis/phase4_offline_collectibles_batch.json", {
        "analysis/phase4_trace_capsule_set.json",
        "config/semantic_state.yaml"}),
    ("analysis/phase4_offline_contact_batch.json", {
        "analysis/phase4_trace_capsule_set.json"}),
    ("analysis/phase4_offline_e08_batch.json", {
        "analysis/phase4_e08_hazard_outcomes.json",
        "analysis/phase4_offline_contact_batch.json",
        "analysis/phase4_trace_capsule_set.json"}),
    ("analysis/phase4_offline_plant_power_batch.json", {
        "analysis/phase4_trace_capsule_set.json"}),
    ("analysis/phase4_offline_plant_weapon_batch.json", {
        "analysis/phase4_trace_capsule_set.json"}),
    ("analysis/phase4_offline_seed_actions_batch.json", {
        "analysis/phase4_trace_capsule_set.json"}),
    ("analysis/phase4_offline_seed_lifecycle_batch.json", {
        "analysis/phase4_trace_capsule_set.json"}),
    ("analysis/phase4_offline_traversal_plants_batch.json", {
        "analysis/phase4_trace_capsule_set.json"}),
    ("analysis/phase4_fmv.json", {
        "src_re/fmv_player_streaming.c"}),
    ("analysis/phase4_fmv_levelb_reachability.json", {
        "analysis/phase4_fmv_interface_frontier.json",
        "analysis/phase4_fmv_static_owners.json"}),
    ("analysis/phase4_fmv_levelb_first_call.json", {
        "analysis/phase4_fmv_levelb_reachability.json",
        "analysis/phase4_fmv_static_owners.json"}),
    ("analysis/phase4_fmv_finale_route_probe.json", {
        "analysis/phase4_fmv_static_owners.json"}),
    ("analysis/phase4_fmv_c16_selector_control_result.json", {
        "tools/phase4_duckstation_batch.py"}),
    ("analysis/phase4_fmv_cd_event_exit_result.json", {
        "analysis/phase4_fmv_lifecycle_continuations.json",
        "tools/phase4_duckstation_batch.py"}),
    ("analysis/phase4_fmv_decoded_record_control_result.json", {
        "tools/phase4_duckstation_batch.py"}),
    ("analysis/phase4_fmv_decoded_record_retention_result.json", {
        "analysis/phase4_fmv_decoded_record_control_result.json",
        "tools/phase4_duckstation_batch.py"}),
    ("analysis/phase4_fmv_menu_owner_coverage.json", {
        "tools/phase4_duckstation_batch.py"}),
    ("analysis/phase4_fmv_menu_phase_neutral_live.json", {
        "tools/phase4_duckstation_batch.py"}),
    ("analysis/phase4_fmv_levelb_region_b_dma_attempt.json", {
        "analysis/phase3_duckstation_rpc_manifest.json",
        "tools/phase4_duckstation_batch.py"}),
    ("analysis/phase4_fmv_resident_identity.json", {
        "analysis/phase3_duckstation_rpc_manifest.json",
        "analysis/phase4_fmv_c16_selector_control_result.json",
        "config/phase4_live_escalations.yaml",
        "tools/phase4_duckstation_batch.py"}),
)

# This field is consumed as the identity of the current low-level validator,
# while the command/debugger/media/timing/cleanup receipts alongside it remain
# the historical live-run provenance.  Refreshing it is therefore bounded
# metadata reconciliation, not a claim that the retained run was replayed.
CURRENT_GENERATOR_METADATA = {
    "analysis/phase4_c16_bonus_death.json":
        "tools/phase4_c16_bonus_death.py",
    "analysis/phase4_respawn_row_provenance.json":
        "tools/phase4_respawn_row_provenance.py",
    "analysis/phase4_respawn_writer_catalog.json":
        "tools/phase4_respawn_writer_catalog.py",
}

# The trace-capsule contract can promote a serial-only movie lead to pristine
# only after two hash-identical replays verify mounted media.  Reconcile that
# central classification without rewriting the retained C16 live payload.
CURRENT_FIXTURE_METADATA = {
    "analysis/phase4_c16_bonus_death.json": {
        "fixture": "movies/Bonus_Level_03.movie.json",
        "document_path": ("fixture_census", "movie", "media_class"),
    },
}


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_sha(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def artifact_rendered(document: dict) -> bytes:
    if str(document.get("schema") or "").startswith("abl-phase4-offline-"):
        return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()
    if document.get("schema") == \
            "abl-phase4-fmv-levelb-region-b-dma-attempt/1":
        return (json.dumps(
            document, indent=2, sort_keys=True
        ) + "\n").encode()
    if document.get("schema") in {
            "abl-phase4-fmv-menu-owner-coverage/1",
            "abl-phase4-fmv-menu-phase-neutral-live/1",
            "abl-phase4-fmv-levelb-reachability/2",
            "abl-phase4-fmv-levelb-first-call/1",
            "abl-phase4-fmv-finale-route-probe/1",
            "abl-phase4-fmv-c16-selector-control-result/3",
            "abl-phase4-fmv-cd-event-exit-result/1",
            "abl-phase4-fmv-resident-identity/1"}:
        return (json.dumps(document, indent=2) + "\n").encode()
    return (json.dumps(document, indent=1) + "\n").encode()


def report_rendered(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def stable_generated(previous: dict) -> str:
    value = previous.get("generated")
    return value if isinstance(value, str) and value else date.today().isoformat()


def reconciled_live_escalation_config(
        previous: dict | None = None,
        artifact_hashes: dict[str, str] | None = None) -> tuple[bytes, list[dict]]:
    """Refresh bounded retained-analysis SHA leaves in the live ledger source."""
    previous = previous or {}
    artifact_hashes = artifact_hashes or {}
    prior_rows = {
        row["entry_id"]: row
        for row in previous.get("joined_live_escalation_pins") or []
    }
    original_bytes = LIVE_ESCALATION_CONFIG.read_bytes()
    original_text = original_bytes.decode()
    document = common.load_yaml(LIVE_ESCALATION_CONFIG)
    normalized_before = common.load_yaml(LIVE_ESCALATION_CONFIG)
    replacements: dict[tuple[str, str], str] = {}
    rows = []
    allowed_offline_artifacts = {
        "analysis/phase4_offline_seed_actions_batch.json",
        "analysis/phase4_offline_bonus_objectives_batch.json",
    }
    allowed_controlled_artifacts = {
        "analysis/phase4_fmv_levelb_first_call.json",
        "analysis/phase4_fmv_menu_owner_coverage.json",
        "analysis/phase4_fmv_menu_phase_neutral_live.json",
        "analysis/phase4_fmv_levelb_reachability.json",
        "analysis/phase4_fmv_c16_selector_control_result.json",
        "analysis/phase4_fmv_cd_event_exit_result.json",
        "analysis/phase4_fmv_decoded_record_control_result.json",
        "analysis/phase4_fmv_decoded_record_retention_result.json",
        "analysis/phase4_fmv_present_rect_height_function_trace_result.json",
        "analysis/phase4_fmv_levelb_region_b_dma_attempt.json",
        "analysis/phase4_fmv_finale_route_probe.json",
    }
    for entry in document.get("entries") or []:
        entry_id = entry.get("id")
        execution = entry.get("execution_result") or {}
        if not execution:
            # A predeclared escalation is scheduling input, not retained
            # evidence.  It has no banked/offline analysis identity to
            # reconcile until the run is executed and its receipt is joined.
            continue
        if execution.get("execution_kind") in {
                "atomic_batch_control", "phase_neutral_movie_control",
                "v2_receipt_set"}:
            joined = execution.get("banked_analysis") or {}
            relative = joined.get("path")
            if relative not in allowed_controlled_artifacts:
                # Other controlled artifacts did not change in this bounded
                # source refresh and remain under their dedicated validators.
                continue
            pin_kind = "controlled_banked_analysis"
        else:
            joined = execution.get("offline_analysis") or {}
            relative = joined.get("path")
            if relative not in allowed_offline_artifacts:
                raise ValueError(
                    f"{entry_id}: live-escalation offline analysis is outside "
                    "the bounded set")
            pin_kind = "capsule_offline_analysis"
        before = joined.get("sha256")
        if relative not in allowed_offline_artifacts | allowed_controlled_artifacts:
            raise ValueError(
                f"{entry_id}: live-escalation analysis is outside the bounded set")
        # The upstream artifacts are written after this config is rendered.
        # Use their projected post-reconciliation identities so one --write
        # pass cannot leave the joined live ledger one generation behind.
        after = artifact_hashes.get(relative, file_sha(common.ROOT / relative))
        replacements[(relative, before)] = after
        prior = prior_rows.get(entry_id) or {}
        rows.append({
            "entry_id": entry_id,
            "pin_kind": pin_kind,
            "path": relative,
            "sha256_before": prior.get("sha256_before") or before,
            "sha256_after": after,
            "behavioral_payload_preserved": True,
        })
        before_entry = next(
            row for row in normalized_before.get("entries") or []
            if row.get("id") == entry_id)
        before_joined = before_entry["execution_result"][
            "banked_analysis" if pin_kind == "controlled_banked_analysis"
            else "offline_analysis"]
        before_joined["sha256"] = "<current-analysis-identity>"

    rendered = original_text
    for (relative, before), after in replacements.items():
        needle = f"sha256: {before}"
        actual = rendered.count(needle)
        if actual == 0 and before == after:
            continue
        if actual == 0:
            raise ValueError(
                f"{relative}: bounded SHA leaf was not found")
        rendered = rendered.replace(needle, f"sha256: {after}")

    rendered_document = yaml.safe_load(rendered)
    for entry in rendered_document.get("entries") or []:
        execution = entry.get("execution_result") or {}
        if not execution:
            continue
        if (execution.get("banked_analysis") or {}).get("path") in \
                allowed_controlled_artifacts:
            execution["banked_analysis"]["sha256"] = \
                "<current-analysis-identity>"
        elif execution.get("execution_kind") not in {
                "atomic_batch_control", "phase_neutral_movie_control",
                "v2_receipt_set"}:
            execution["offline_analysis"]["sha256"] = \
                "<current-analysis-identity>"
    if object_sha(normalized_before) != object_sha(rendered_document):
        raise ValueError("live-escalation config changed beyond offline-analysis SHA leaves")
    return rendered.encode(), rows


def replace_dependency_identity(node, replacements: dict[str, str], *, key=None):
    """Refresh joined artifact identities but preserve historical run receipts."""
    if key == "run_provenance":
        return node
    if isinstance(node, str):
        return replacements.get(node, node)
    if isinstance(node, dict):
        return {name: replace_dependency_identity(value, replacements, key=name)
                for name, value in node.items()}
    if isinstance(node, list):
        return [replace_dependency_identity(value, replacements)
                for value in node]
    return node


def normalized_payload(document: dict, dependency_hashes: set[str], *,
                       normalize_current_generator: bool = False,
                       generator_top_level: bool = False,
                       normalize_current_fixture: bool = False) -> dict:
    """Hash behavior while excluding dependency metadata and joined identities."""
    payload = {key: value for key, value in document.items()
               if key != "source_dependencies"}
    placeholders = {value: "<current-dependency-identity>"
                    for value in dependency_hashes}
    payload = replace_dependency_identity(payload, placeholders)
    if normalize_current_generator:
        if generator_top_level and "generator_sha256" in payload:
            payload["generator_sha256"] = "<current-generator-identity>"
        else:
            run = payload.get("run_provenance")
            if not isinstance(run, dict) or "generator_sha256" not in run:
                raise ValueError("current generator identity field is absent")
            run = dict(run)
            payload["run_provenance"] = run
            run["generator_sha256"] = "<current-generator-identity>"
    if normalize_current_fixture:
        payload["fixture_census"]["movie"]["media_class"] = \
            "<current-central-fixture-classification>"
    return payload


def build() -> tuple[list[tuple[Path, dict]], dict]:
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.is_file() else {}
    previous_rows = {row["path"]: row for row in previous.get("artifacts") or []}
    updates: list[tuple[Path, dict]] = []
    rows = []
    virtual_hashes: dict[str, str] = {}
    for relative, allowed_dependencies in TARGETS:
        path = common.ROOT / relative
        document = json.loads(path.read_text())
        dependencies = document.get("source_dependencies")
        if not isinstance(dependencies, dict):
            raise ValueError(f"{relative}: source_dependencies is not a mapping")
        fixture_spec = CURRENT_FIXTURE_METADATA.get(relative)
        permitted_new_dependencies = (
            {"analysis/phase0_2_external_fixture_set.json"}
            if fixture_spec else set())
        missing = sorted(
            allowed_dependencies - set(dependencies) - permitted_new_dependencies)
        if missing:
            raise ValueError(f"{relative}: declared reconciliation inputs absent: {missing}")

        prior = previous_rows.get(relative) or {}
        before_hashes = {
            name: dependencies.get(name, "<absent>")
            for name in allowed_dependencies
        }
        after_hashes = {
            name: virtual_hashes.get(name, file_sha(common.ROOT / name))
            for name in allowed_dependencies}
        replacements = {
            before_hashes[name]: after_hashes[name]
            for name in allowed_dependencies
            if before_hashes[name] != after_hashes[name]
        }
        all_dependency_hashes = set(before_hashes.values()) | set(after_hashes.values())
        generator_path = CURRENT_GENERATOR_METADATA.get(relative)
        generator_top_level = relative == "analysis/phase4_respawn_writer_catalog.json"
        old_generator_sha = (
            document.get("generator_sha256") if generator_path and generator_top_level
            else ((document.get("run_provenance") or {}).get("generator_sha256")
                  if generator_path else None))
        original_generator_sha = (
            ((prior.get("current_generator_metadata") or {}).get("sha256_before"))
            or old_generator_sha)
        before_payload = object_sha(normalized_payload(
            document, all_dependency_hashes,
            normalize_current_generator=bool(generator_path),
            generator_top_level=generator_top_level,
            normalize_current_fixture=bool(fixture_spec)))
        original_artifact_sha = prior.get("artifact_sha256_before") or file_sha(path)
        original_dependency_hashes = prior.get("dependency_sha256_before") or before_hashes

        document = replace_dependency_identity(document, replacements)
        for name, digest in after_hashes.items():
            document["source_dependencies"][name] = digest
        current_generator_sha = None
        if generator_path:
            current_generator_sha = file_sha(common.ROOT / generator_path)
            if generator_top_level:
                document["generator_sha256"] = current_generator_sha
            else:
                document["run_provenance"]["generator_sha256"] = current_generator_sha
        fixture_metadata = None
        if fixture_spec:
            central = json.loads((
                common.ROOT / "analysis/phase0_2_external_fixture_set.json"
            ).read_text())
            current_class = central["entries"][fixture_spec["fixture"]]["media_class"]
            cursor = document
            *parents, leaf = fixture_spec["document_path"]
            for parent in parents:
                cursor = cursor[parent]
            previous_class = cursor[leaf]
            original_class = (
                ((prior.get("current_fixture_metadata") or {}).get("before"))
                or previous_class)
            cursor[leaf] = current_class
            fixture_metadata = {
                "fixture": fixture_spec["fixture"],
                "field": ".".join(fixture_spec["document_path"]),
                "before": original_class,
                "after": current_class,
            }
        after_payload = object_sha(normalized_payload(
            document, all_dependency_hashes,
            normalize_current_generator=bool(generator_path),
            generator_top_level=generator_top_level,
            normalize_current_fixture=bool(fixture_spec)))
        if before_payload != after_payload:
            raise ValueError(f"{relative}: non-dependency payload changed")
        artifact_after = hashlib.sha256(artifact_rendered(document)).hexdigest()
        virtual_hashes[relative] = artifact_after
        updates.append((path, document))
        rows.append({
            "path": relative,
            "allowed_dependencies": sorted(allowed_dependencies),
            "dependency_sha256_before": original_dependency_hashes,
            "dependency_sha256_after": after_hashes,
            "artifact_sha256_before": original_artifact_sha,
            "artifact_sha256_after": artifact_after,
            "normalized_runtime_payload_sha256": after_payload,
            "only_dependency_metadata_or_joined_identity_changed":
                fixture_metadata is None,
            "only_reconciled_metadata_or_joined_identity_changed": True,
            "historical_run_provenance_preserved": True,
            "current_generator_metadata": ({
                "path": generator_path,
                "sha256_before": original_generator_sha,
                "sha256_after": current_generator_sha,
            } if generator_path else None),
            "current_fixture_metadata": fixture_metadata,
        })

    live_config_bytes, live_config_rows = reconciled_live_escalation_config(
        previous, artifact_hashes=virtual_hashes)
    report = {
        "_comment": (
            "Generated dependency-identity reconciliation after the A10/A11 "
            "baseline, fixture-set and capsule-index refresh. Runtime/control payloads "
            "and historical run provenance are preserved; only declared dependency "
            "metadata, joined artifact identities, current generator identity, and "
            "a centrally promoted fixture classification may change."),
        "schema": "abl-phase4-upstream-dependency-reconciliation/1",
        "generated": stable_generated(previous),
        "generator": "python3 tools/phase4_reconcile_upstream_dependencies.py --write",
        "source_dependencies": {
            "analysis/phase0_2_external_fixture_set.json": file_sha(
                common.ROOT / "analysis/phase0_2_external_fixture_set.json"),
            "analysis/phase2_row_coverage.json": file_sha(
                common.ROOT / "analysis/phase2_row_coverage.json"),
            "tools/phase4_reconcile_upstream_dependencies.py": file_sha(Path(__file__)),
        },
        "artifacts": rows,
        "joined_live_escalation_config": "config/phase4_live_escalations.yaml",
        "joined_live_escalation_config_sha256_after":
            hashlib.sha256(live_config_bytes).hexdigest(),
        "joined_live_escalation_pins": live_config_rows,
        "joined_live_escalation_only_sha_leaves_changed": True,
        "errors": [],
        "valid": True,
    }
    return updates, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        updates, report = build()
        projected_hashes = {
            row["path"]: row["artifact_sha256_after"]
            for row in report.get("artifacts") or []
        }
        live_config_bytes, _ = reconciled_live_escalation_config(
            report, artifact_hashes=projected_hashes)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.write:
        for path, document in updates:
            path.write_bytes(artifact_rendered(document))
        LIVE_ESCALATION_CONFIG.write_bytes(live_config_bytes)
        OUTPUT.write_bytes(report_rendered(report))
    elif args.check:
        if any(path.read_bytes() != artifact_rendered(document)
               for path, document in updates):
            print("Phase-4 upstream dependency metadata is stale", file=sys.stderr)
            return 1
        if LIVE_ESCALATION_CONFIG.read_bytes() != live_config_bytes:
            print("Phase-4 joined live-escalation pins are stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != report_rendered(report):
            print("Phase-4 upstream reconciliation report is stale", file=sys.stderr)
            return 1
    else:
        print(report_rendered(report).decode(), end="")
    print(f"PASS: {len(TARGETS)} artifacts retain normalized runtime/control payloads",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
