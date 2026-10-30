#!/usr/bin/env python3
"""Refresh only Phase-4 assertion artifact/hash-join identities."""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

import yaml

import phase4_common as common


TARGETS = (common.REGISTRY_PATH, common.FINDINGS_PATH)
OUTPUT = common.ROOT / "analysis/phase4_assertion_pin_reconciliation.json"
IDENTITY_ARTIFACTS = (
    "tools/phase4_method_metrics.py",
    "analysis/phase4_method_legacy_live_index.json",
    "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json",
    "analysis/phase4_fmv_levelb_transition_relocalization.json",
    "config/phase4_fmv_levelb_two_pc_first_hit.yaml",
    "analysis/phase4_fmv_levelb_two_pc_first_hit.json",
    "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json",
    "analysis/phase4_fmv_levelb_pre15792_partition.json",
    "analysis/phase4_fmv_frame_sync_wait_ownership.json",
    "analysis/phase4_fmv_c16_selector_control_result.json",
    "analysis/phase4_fmv_resident_identity.json",
    "analysis/phase4_checkpoint_respawn.json",
    "analysis/phase4_respawn_row_provenance.json",
    "analysis/phase4_respawn_writer_catalog.json",
    "analysis/phase4_e08_hazard_outcomes.json",
    "analysis/phase4_lives_death_breadth.json",
    "analysis/phase4_c16_bonus_death.json",
    "analysis/phase4_c16_thumper_death.json",
    "analysis/phase4_c16_flight_death.json",
    "analysis/phase4_thud_defeat.json",
    "analysis/phase4_thud_arena.json",
    "analysis/phase4_thud_completion.json",
    "analysis/phase4_thud_volley.json",
    "analysis/phase4_c16_thud_boulder_death.json",
    "analysis/phase4_respawn_status_policy.json",
)
INITIAL_IDENTITY_SHA256 = {
    "tools/phase4_method_metrics.py":
        "14850af6870bf384ec2ce4676ed3265fe43d10414e333c065e7c184099771cde",
    # The legacy index predates the identity-artifact census.  Pin its exact
    # retained predecessor so the first bounded reconciliation can update the
    # sole C16 consumer without a free-form repository-wide hash replacement.
    "analysis/phase4_method_legacy_live_index.json":
        "7960b86c1034ddbba36ab62ce61625f8d5ea4ccdfa39ed1f59f722cdb9ac25d8",
    "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json":
        "f9d895346941c62ecc2ae62e1cd052c9a60d8f9484b3e9106e175d40015a6faa",
    "analysis/phase4_fmv_levelb_transition_relocalization.json":
        "77ae7273c33b62229c4d1cd2f6a95caa091993fa82e08bd74ff98d9f155d4b3e",
    "config/phase4_fmv_levelb_two_pc_first_hit.yaml":
        "d59698e9583732add2da3d013ba6b0f28cf386ae74cfe79481618847cd1e2399",
    "analysis/phase4_fmv_levelb_two_pc_first_hit.json":
        "59f042b0ee3415a7ea36452b6e0a507fa21290a4a0e7ba8a43e27ef815d77838",
    "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json":
        "dd5deba2b09fc4876f625675df0443057d58016f0d4509a5fd9ccd386268c329",
    "analysis/phase4_fmv_levelb_pre15792_partition.json":
        "522c58e8eb65b0ff56541cd2be59bee2839c8d3acd51d9ae4191c1332ba808f6",
    "analysis/phase4_fmv_frame_sync_wait_ownership.json":
        "32e7e3198a01ac65020b6239f1ace3da3ebc6e5066f1e1ff0639faf457cf3dc9",
    "analysis/phase4_fmv_c16_selector_control_result.json":
        "0a4a23b14875bf3db30ec70f7d0671121e8d42a06dff9817a7f3dd4e68ca7ba6",
    "analysis/phase4_fmv_resident_identity.json":
        "44e55377c9d65f8d6997b130cb4ad356008eaa2f3d56a5fb8f3810d83314eb40",
}
CONSUMER_GLOBS = (
    "config/phase4_*.yaml",
    "tests/test_phase4_*.py",
    "tools/phase4_*.py",
    "ObsidianVault/Playbooks/Game Solving Roadmap/*.md",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
INLINE_ARTIFACT_RE = re.compile(
    r"(?P<prefix>artifact:\s*(?P<artifact>[^,}\n]+),\s*sha256:\s*)"
    r"(?P<sha>[0-9a-f]{64})")
INLINE_EXPECTED_HASH_RE = re.compile(
    r"(?P<prefix>expected:\s*)(?P<quote>['\"]?)(?P<sha>[0-9a-f]{64})"
    r"(?P=quote)(?P<suffix>\s*})")
INLINE_PATH_RE = re.compile(r"json_path:\s*(?P<value>[^,}\n]+)")
INLINE_OP_RE = re.compile(r"op:\s*(?P<value>[^,}\n]+)")
BLOCK_ARTIFACT_RE = re.compile(
    r"^(?P<indent>\s*)- artifact:\s*(?P<artifact>\S+)\s*$")
BLOCK_FIELD_RE = re.compile(
    r"^(?P<indent>\s*)(?P<field>sha256|json_path|op|expected):\s*(?P<value>.*)$")


def stable_generated(path: Path | None = None) -> str:
    """Preserve retained receipt identity across calendar-day regeneration."""
    path = path or OUTPUT
    if path.is_file():
        try:
            value = json.loads(path.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def _assertions(node: Any):
    if isinstance(node, dict):
        if {"artifact", "sha256", "json_path", "op", "expected"} <= set(node):
            yield node
        for value in node.values():
            yield from _assertions(value)
    elif isinstance(node, list):
        for value in node:
            yield from _assertions(value)


def _resolved_value(artifact: str, json_path: str) -> Any:
    document = common.load_json(common.ROOT / artifact)
    value: Any = document
    for segment in json_path.split(".") if json_path else []:
        value = value[int(segment)] if isinstance(value, list) else value[segment]
    return value


def reconciled_document(document: dict) -> tuple[dict, list[dict]]:
    # YAML input contains only ordinary mappings/lists/scalars, so a JSON round
    # trip is a safe deep copy and cannot preserve aliases that hide updates.
    result = json.loads(json.dumps(document))
    changes: list[dict] = []
    for assertion in _assertions(result):
        artifact = str(assertion["artifact"])
        path = common.ROOT / artifact
        if not path.is_file() or not common.git_tracked(artifact):
            raise ValueError(f"assertion artifact is missing or untracked: {artifact}")
        current_hash = common.sha256(path)
        if assertion["sha256"] != current_hash:
            changes.append({
                "kind": "artifact_pin", "artifact": artifact,
                "before": assertion["sha256"], "after": current_hash,
            })
            assertion["sha256"] = current_hash
        if assertion.get("op") == "eq":
            actual = _resolved_value(artifact, str(assertion["json_path"]))
            expected = assertion.get("expected")
            if (isinstance(actual, str) and SHA256_RE.fullmatch(actual)
                    and isinstance(expected, str) and SHA256_RE.fullmatch(expected)
                    and actual != expected):
                changes.append({
                    "kind": "joined_hash_leaf", "artifact": artifact,
                    "json_path": assertion["json_path"],
                    "before": expected, "after": actual,
                })
                assertion["expected"] = actual
    return result, changes


def _key(artifact: str, json_path: str, op: str) -> tuple[str, str, str]:
    return artifact.strip(), json_path.strip(), op.strip()


def _rewrite_assertions(text: str, expected: dict) -> str:
    by_key: dict[tuple[str, str, str], deque[dict]] = defaultdict(deque)
    for assertion in _assertions(expected):
        by_key[_key(assertion["artifact"], assertion["json_path"],
                    assertion["op"])].append(assertion)

    lines = text.splitlines(keepends=True)
    consumed = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        if "{artifact:" in line:
            artifact_match = INLINE_ARTIFACT_RE.search(line)
            path_match = INLINE_PATH_RE.search(line)
            op_match = INLINE_OP_RE.search(line)
            if not artifact_match or not path_match or not op_match:
                raise ValueError(f"cannot safely parse inline assertion: {line.strip()}")
            key = _key(artifact_match.group("artifact"),
                       path_match.group("value"), op_match.group("value"))
            if not by_key[key]:
                raise ValueError(f"inline assertion is absent semantically: {key}")
            assertion = by_key[key].popleft()
            consumed += 1
            line = (line[:artifact_match.start("sha")] + assertion["sha256"]
                    + line[artifact_match.end("sha"):])
            actual_expected = assertion.get("expected")
            expected_match = INLINE_EXPECTED_HASH_RE.search(line)
            if (isinstance(actual_expected, str)
                    and SHA256_RE.fullmatch(actual_expected) and expected_match):
                line = (line[:expected_match.start("sha")] + actual_expected
                        + line[expected_match.end("sha"):])
            lines[index] = line
            index += 1
            continue

        block_match = BLOCK_ARTIFACT_RE.match(line.rstrip("\n"))
        if not block_match:
            index += 1
            continue
        fields: dict[str, tuple[int, re.Match]] = {}
        scan = index + 1
        while scan < len(lines):
            candidate = lines[scan].rstrip("\n")
            match = BLOCK_FIELD_RE.match(candidate)
            if match and len(match.group("indent")) > len(block_match.group("indent")):
                fields[match.group("field")] = (scan, match)
                scan += 1
                continue
            if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= len(
                    block_match.group("indent")):
                break
            scan += 1
        if not {"sha256", "json_path", "op", "expected"} <= fields.keys():
            raise ValueError(f"incomplete block assertion at line {index + 1}")
        key = _key(block_match.group("artifact"), fields["json_path"][1].group("value"),
                   fields["op"][1].group("value"))
        if not by_key[key]:
            raise ValueError(f"block assertion is absent semantically: {key}")
        assertion = by_key[key].popleft()
        consumed += 1
        sha_index, sha_match = fields["sha256"]
        ending = "\n" if lines[sha_index].endswith("\n") else ""
        lines[sha_index] = (f'{sha_match.group("indent")}sha256: '
                            f'{assertion["sha256"]}{ending}')
        actual_expected = assertion.get("expected")
        expected_index, expected_match = fields["expected"]
        current_expected = expected_match.group("value").strip("'\"")
        if (isinstance(actual_expected, str) and SHA256_RE.fullmatch(actual_expected)
                and SHA256_RE.fullmatch(current_expected)):
            ending = "\n" if lines[expected_index].endswith("\n") else ""
            lines[expected_index] = (f'{expected_match.group("indent")}expected: '
                                     f'{actual_expected}{ending}')
        index = scan

    remaining = sum(len(rows) for rows in by_key.values())
    if remaining:
        raise ValueError(
            f"only {consumed}/{consumed + remaining} semantic assertions were located")
    rendered = "".join(lines)
    if yaml.safe_load(rendered) != expected:
        raise ValueError("textual reconciliation changed more than assertion hash identities")
    return rendered


def _consumer_paths() -> list[Path]:
    paths = {path for pattern in CONSUMER_GLOBS
             for path in common.ROOT.glob(pattern)
             if path.is_file() and path.resolve() != Path(__file__).resolve()
             and common.git_tracked(path.relative_to(common.ROOT))}
    return sorted(paths)


def build() -> tuple[list[tuple[Path, str]], dict]:
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.is_file() else {}
    previous_artifacts = {
        row["path"]: row["sha256"]
        for row in previous.get("identity_artifacts", [])
        if isinstance(row, dict) and isinstance(row.get("path"), str)
        and isinstance(row.get("sha256"), str)
    }
    update_map: dict[Path, str] = {}
    rows = []
    for path in TARGETS:
        source = yaml.safe_load(path.read_text())
        expected, changes = reconciled_document(source)
        rendered = _rewrite_assertions(path.read_text(), expected)
        update_map[path] = rendered
        assertions = list(_assertions(expected))
        rows.append({
            "path": str(path.relative_to(common.ROOT)),
            "sha256_after": hashlib.sha256(rendered.encode()).hexdigest(),
            "assertions_checked": len(assertions),
            "artifact_pins_changed": sum(row["kind"] == "artifact_pin" for row in changes),
            "joined_hash_leaves_changed": sum(
                row["kind"] == "joined_hash_leaf" for row in changes),
            "changes": changes,
        })

    identity_rows = []
    consumer_changes = []
    consumers = _consumer_paths()
    for artifact in IDENTITY_ARTIFACTS:
        current = common.sha256(common.ROOT / artifact)
        prior = previous_artifacts.get(
            artifact, INITIAL_IDENTITY_SHA256.get(artifact))
        replacements = 0
        changed_paths = []
        if prior and prior != current:
            for path in consumers:
                text = update_map.get(path, path.read_text())
                count = text.count(prior)
                if not count:
                    continue
                update_map[path] = text.replace(prior, current)
                replacements += count
                changed_paths.append(str(path.relative_to(common.ROOT)))
        identity_rows.append({
            "path": artifact,
            "sha256": current,
            "prior_sha256": prior,
            "consumer_replacements": replacements,
            "consumer_paths_changed": changed_paths,
        })
        if replacements:
            consumer_changes.append({
                "artifact": artifact,
                "before": prior,
                "after": current,
                "replacements": replacements,
                "paths": changed_paths,
            })
    report = {
        "_comment": "Generated bounded reconciliation of assertion artifact pins and hash-valued joined leaves. Behavioral expectations and historical evidence payloads are not edited.",
        "schema": "abl-phase4-assertion-pin-reconciliation/2",
        "generated": stable_generated(),
        "generator_sha256": common.sha256(Path(__file__)),
        "targets": rows,
        "identity_artifacts": identity_rows,
        "consumer_changes": consumer_changes,
        "errors": [],
        "valid": True,
    }
    return sorted(update_map.items()), report


def render_report(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        updates, report = build()
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError,
            json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.write:
        for path, rendered in updates:
            path.write_text(rendered)
        # Seed the just-observed current identities before recomputing so the
        # retained report describes a stable no-delta state rather than the
        # one-time migration from its previous artifact generation.
        OUTPUT.write_text(render_report(report))
        # Recompute after writing so the retained report describes a stable
        # current state rather than a one-time migration delta.
        updates, report = build()
        OUTPUT.write_text(render_report(report))
    elif args.check:
        if any(path.read_text() != rendered for path, rendered in updates):
            print("Phase-4 assertion pins are stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_text() != render_report(report):
            print("Phase-4 assertion-pin reconciliation report is stale", file=sys.stderr)
            return 1
    else:
        print(render_report(report), end="")
    total = sum(row["assertions_checked"] for row in report["targets"])
    print(f"PASS: {total} assertion pins match current retained artifacts", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
