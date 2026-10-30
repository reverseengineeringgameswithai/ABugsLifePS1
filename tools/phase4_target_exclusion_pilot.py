#!/usr/bin/env python3
"""Run the frozen Phase-4 target-domain/exclusion pilot.

The pilot list and all derived analysis inputs come from the committed
pre-outcome freeze.  A standalone C verifier proves exact domains; a separate
C implementation re-derives classifications and domains by forward dataflow
from the image bytes.  Python owns identities, exact-set comparisons, the
immutable decision policy, and deterministic JSON.

This driver stops at NO-GO.  It does not mutate the gate/index, re-run the
caller-domain sample, or move any F01 status surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_target_exclusion_pilot.json"
FREEZE_ARTIFACT = ROOT / "analysis/phase4_target_exclusion_freeze.json"
INDEX = ROOT / "analysis/phase4_static_frontier_index.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"
FRONTIER_RESULT = ROOT / "analysis/phase4_f01_frontier_result.json"
MECHANICS = ROOT / "analysis/mechanics_baseline.yaml"
U3_EVIDENCE = ROOT / "analysis/traces/u3_evidence.json"
U3_SOURCE = ROOT / "tools/trace_name_candidates.py"
TYPED_STATE_PY = ROOT / "tools/phase4_typed_state.py"
WORK_ORDER = ROOT / "engineering-specs/phase4-target-exclusion-work-order.md"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"
PRIMARY_C = ROOT / "tools/phase4_target_exclusion_prover.c"
CROSSCHECK_C = ROOT / "tools/phase4_target_exclusion_crosscheck.c"

BASELINE_COMMIT = "2a617486b30fce115933900e307c233ddb121f56"
SPEC_COMMIT = "d4c60047fb2d1419f7691f6e2b6a628eea2fdb42"
FREEZE_COMMIT = "2e67ac74498c96989a858e08918983aaf5bdf73a"
FREEZE_SHA256 = "8b6cb83f9d2b95b099606f87e3b0f76b8520e391bdebfc5629f0bf45e1864ad2"
SCHEMA = "abl-phase4-target-exclusion-pilot/1"

EXPECTED_PILOT = (
    "SCUS_942_88:0x80011128:jr:ra",
    "SCUS_942_88:0x800163d8:jr:ra",
    "SCUS_942_88:0x800172d4:jr:ra",
    "SCUS_942_88:0x8001897c:jr:ra",
    "SCUS_942_88:0x80018a4c:jr:s6",
    "SCUS_942_88:0x80018b1c:jr:s6",
    "SCUS_942_88:0x80018bec:jr:s6",
    "SCUS_942_88:0x80018cbc:jr:s6",
    "SCUS_942_88:0x80018f44:jr:ra",
    "SCUS_942_88:0x8001923c:jr:ra",
    "SCUS_942_88:0x80019614:jr:ra",
    "SCUS_942_88:0x80019b3c:jr:ra",
)


class PilotError(RuntimeError):
    """A frozen identity, proof, cross-check, or decision invariant failed."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    return int(str(value), 0)


def _git_show(commit: str, path: Path | str) -> bytes:
    rel = str(path.relative_to(ROOT) if isinstance(path, Path) else path)
    proc = subprocess.run(
        ["git", "show", f"{commit}:{rel}"], cwd=ROOT,
        capture_output=True, check=False,
    )
    if proc.returncode:
        raise PilotError(
            f"cannot read pinned object {commit}:{rel}: "
            + proc.stderr.decode(errors="replace").strip())
    return proc.stdout


def _git_json(commit: str, path: Path) -> tuple[dict, bytes]:
    raw = _git_show(commit, path)
    return json.loads(raw), raw


def _compile(source: Path, output: Path) -> bytes:
    proc = subprocess.run(
        ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
         "-o", str(output), str(source)],
        cwd=ROOT, capture_output=True, text=True,
    )
    if proc.returncode:
        raise PilotError(f"C compile failed ({source.name}): {proc.stderr.strip()}")
    return output.read_bytes()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise PilotError(f"command failed ({' '.join(command)}): {proc.stderr.strip()}")
    return proc


def _run_json(command: list[str]) -> dict:
    proc = _run(command)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PilotError(f"non-JSON C output: {proc.stdout[:500]!r}") from exc


def _verify_history() -> tuple[dict, bytes, bytes]:
    for ancestor in (BASELINE_COMMIT, SPEC_COMMIT, FREEZE_COMMIT):
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, "HEAD"],
            cwd=ROOT, check=False,
        )
        if proc.returncode:
            raise PilotError(f"current HEAD is not descended from {ancestor}")
    freeze, raw = _git_json(FREEZE_COMMIT, FREEZE_ARTIFACT)
    if _sha(raw) != FREEZE_SHA256:
        raise PilotError("pre-outcome freeze artifact identity drifted")
    if freeze.get("schema") != "abl-phase4-target-exclusion-freeze/1":
        raise PilotError("unexpected freeze schema")
    if tuple(freeze["pilot_selection"]["pilot_ids"]) != EXPECTED_PILOT:
        raise PilotError("frozen pilot ids/order differ")
    if freeze["outcome_barrier"] != {
            "f01_status_moved": False,
            "full_pass_authorized": False,
            "go_no_go_decision_present": False,
            "runtime_crosscheck_outcome_present": False,
            "stage_2_exclusion_proofs_present": False,
            "stage_2_target_domain_proofs_present": False}:
        raise PilotError("freeze contains an outcome")
    note_raw = _git_show(FREEZE_COMMIT, EXPERIMENT)
    text = note_raw.decode("utf-8")
    marker = "target-exclusion pilot frozen (PRE-OUTCOME record)"
    if marker not in text:
        raise PilotError("freeze commit lacks experiment pre-outcome marker")
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    positions = [section.find(f"`{site}`") for site in EXPECTED_PILOT]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise PilotError("experiment pre-outcome pilot differs")
    if ("No Stage-2 target-domain proof" not in section
            or "No GO/NO-GO decision" not in section):
        raise PilotError("freeze note does not exclude outcomes")
    return freeze, raw, note_raw


def _image_map(index: dict) -> tuple[bytes, list[dict]]:
    lines = []
    identities = []
    images = index.get("images") or []
    if len(images) != 21 or len({row["image_id"] for row in images}) != 21:
        raise PilotError("static image universe is not 21 unique images")
    for image in images:
        path = ROOT / image["path"]
        raw = path.read_bytes()
        if (image.get("identity_verified") is not True
                or len(raw) != int(image["size"])
                or _sha(raw) != image["sha256"]):
            raise PilotError(f"image identity failed: {image['image_id']}")
        lines.append(f"{image['image_id']} {image['path']} {image['file_va_base']}")
        identities.append({
            "image": image["image_id"], "path": image["path"],
            "size": len(raw), "sha256": _sha(raw), "identity_verified": True,
        })
    return ("\n".join(lines) + "\n").encode(), identities


def _record_extent(row: dict) -> tuple[int, int]:
    if row.get("entry") is not None and row.get("end") is not None:
        return _int(row["entry"]), _int(row["end"])
    extent = row.get("extent")
    if isinstance(extent, list) and len(extent) == 2:
        return _int(extent[0]), _int(extent[1])
    raise PilotError(f"record lacks extent: {row.get('image_id')} {row.get('name')}")


def _proved_edge_universe(index: dict) -> tuple[set[str], set[str]]:
    sites = set()
    edges = set()
    for field in ("indirect_jump_targets", "indirect_jump_targets_from_gate"):
        for pc, targets in ((index.get(field) or {}).get("site_targets") or {}).items():
            site = f"SCUS_942_88:{str(pc).lower()}"
            sites.add(site)
            for target in targets:
                edges.add(f"{site}->SCUS_942_88:{str(target).lower()}")
    if len(sites) != 87 or len(edges) != 492:
        raise PilotError(f"proved baseline is not 87 sites / 492 edges: {len(sites)}/{len(edges)}")
    return sites, edges


def _target_owner(index: dict, image: str, target: int) -> dict:
    candidates = []
    for row in index["records"]:
        if row.get("image_id") != image or row.get("range_type") not in {"code", "thunk"}:
            continue
        lo, hi = _record_extent(row)
        if lo == target:
            candidates.append((hi - lo, row, lo, hi))
    if not candidates:
        raise PilotError(f"proved target is not a censused code/thunk entry: {image}:0x{target:08x}")
    _, row, lo, hi = min(candidates, key=lambda item: (item[0], item[2]))
    return {
        "image": image, "entry": f"0x{lo:08x}", "end": f"0x{hi:08x}",
        "name": row.get("name") or f"anon_0x{lo:08x}",
        "range_type": row["range_type"],
    }


def _runtime_crosscheck(capsules: dict, u3: dict, u3_raw: bytes,
                        u3_source_raw: bytes, local_basis_ids: list[str]) -> dict:
    rows = capsules.get("capsules") or []
    if (capsules.get("complete") is not True or capsules.get("errors") != []
            or capsules.get("capsule_count") != 50 or len(rows) != 50
            or any(row.get("control_match") is not True for row in rows)):
        raise PilotError("pinned 50-capsule universe is incomplete or control-divergent")
    entry_addresses = ("0x80018cc4", "0x80018f4c", "0x80019244", "0x8001961c")
    entry_rows = []
    for address in entry_addresses:
        row = u3.get(address)
        if not isinstance(row, dict):
            raise PilotError(f"preserved u3 evidence lacks {address}")
        entry_rows.append({
            "entry": address,
            "save": row.get("save"),
            "level": row.get("level"),
            "hits_capped_at_60": row.get("hits"),
            "recorded_callers": row.get("callers") or [],
            "semantics": "entry-PC watch; does not identify the indirect source site",
        })
    return {
        "status": "UNAVAILABLE_SITE_TIME_INDIRECT_TARGETS",
        "capsule_universe": 50,
        "capsule_site_time_target_records": 0,
        "preserved_u3_sha256": _sha(u3_raw),
        "preserved_u3_source_sha256": _sha(u3_source_raw),
        "preserved_u3_source_semantics": (
            "execTrace watches candidate entry PCs and captures registers at the entry; "
            "it does not retain the originating jr PC/target tuple"),
        "preserved_entry_observations": entry_rows,
        "locally_decided_but_not_gate_grade_site_ids": local_basis_ids,
        "site_time_observations": [],
        "all_observed_targets_within_proved_sets": None,
        "soundness_violation": False,
        "clean_for_go": False,
        "reason": ("neither frame-boundary capsules nor the preserved entry-PC watches "
                   "contain a source-site/indirect-target tuple; zero tuples cannot "
                   "satisfy the mandatory clean cross-check"),
        "live_or_instrumented_replay_performed": False,
    }


def build() -> dict:
    freeze, freeze_raw, freeze_note_raw = _verify_history()
    index, index_raw = _git_json(FREEZE_COMMIT, INDEX)
    capsules, capsules_raw = _git_json(FREEZE_COMMIT, CAPSULES)
    frontier, frontier_raw = _git_json(FREEZE_COMMIT, FRONTIER_RESULT)
    u3, u3_raw = _git_json(FREEZE_COMMIT, U3_EVIDENCE)
    u3_source_raw = _git_show(FREEZE_COMMIT, U3_SOURCE)
    typed_state_raw = _git_show(FREEZE_COMMIT, TYPED_STATE_PY)
    work_raw = _git_show(FREEZE_COMMIT, WORK_ORDER)
    mechanics_raw = _git_show(FREEZE_COMMIT, MECHANICS)
    if MECHANICS.read_bytes() != mechanics_raw:
        raise PilotError("analysis/mechanics_baseline.yaml differs from the frozen input")
    if TYPED_STATE_PY.read_bytes() != typed_state_raw:
        raise PilotError("accepted external-entry gate machinery differs from the freeze")

    # Import only after its exact frozen identity has been checked.  This is
    # set/provenance logic; both instruction-domain implementations remain C.
    import phase4_typed_state as typed_state

    image_map, image_identities = _image_map(index)
    site_rows = {row["id"]: row for row in freeze["stage_1_classification"]["sites"]}
    protected = {value.lower() for value in freeze["protected_set"]["combined_ids"]}
    baseline_sites, baseline_edges = _proved_edge_universe(index)

    with tempfile.TemporaryDirectory(prefix="phase4-target-exclusion-pilot-") as temp_text:
        temp = Path(temp_text)
        map_path = temp / "images.txt"
        map_path.write_bytes(image_map)
        primary_bin = temp / "target_prover"
        cross_bin = temp / "target_crosscheck"
        primary_binary = _compile(PRIMARY_C, primary_bin)
        cross_binary = _compile(CROSSCHECK_C, cross_bin)
        primary_selftest_proc = _run([str(primary_bin), "--self-test"])
        primary_selftest = json.loads(primary_selftest_proc.stdout)
        if primary_selftest != {
                "tool": "phase4_target_exclusion_prover",
                "passed": 9, "total": 9, "verdict": True}:
            raise PilotError(f"primary C self-test drifted: {primary_selftest!r}")
        cross_selftest = _run_json([str(cross_bin), "--self-test"])
        if cross_selftest != {
                "tool": "phase4_target_exclusion_crosscheck",
                "passed": 8, "total": 8, "verdict": True}:
            raise PilotError(f"independent C self-test drifted: {cross_selftest!r}")
        queries = []
        for site_id in EXPECTED_PILOT:
            row = site_rows[site_id]
            owner = row["owner"]
            queries.append(
                f"{row['image']}:{owner['entry']}:{owner['end']}:"
                f"{row['register']}:{row['pc']}")
        primary_doc = _run_json([str(primary_bin), str(map_path), *queries])
        cross_doc = _run_json([str(cross_bin), str(map_path), *queries])

    primary_rows = primary_doc.get("queries") or []
    cross_rows = cross_doc.get("queries") or []
    if len(primary_rows) != 12 or len(cross_rows) != 12:
        raise PilotError("C implementations did not return all 12 frozen sites")

    outcomes = []
    local_basis_ids = []
    local_candidate_edges = set()
    dead_definition_correction = []
    for site_id, primary, cross in zip(EXPECTED_PILOT, primary_rows, cross_rows):
        frozen = site_rows[site_id]
        if (primary.get("site_pc") != frozen["pc"]
                or primary.get("register") != frozen["register"]
                or cross.get("site_pc") != frozen["pc"]
                or cross.get("register") != frozen["register"]):
            raise PilotError(f"C query identity mismatch: {site_id}")
        if cross.get("classification") != frozen["stratum"]:
            raise PilotError(
                f"independent classification differs at {site_id}: "
                f"{cross.get('classification')} != {frozen['stratum']}")
        primary_complete = primary.get("full_target_domain_complete") is True
        cross_complete = cross.get("full_target_domain_complete") is True
        targets = [str(value).lower() for value in primary.get("targets") or []]
        cross_targets = [str(value).lower() for value in cross.get("targets") or []]
        if primary_complete != cross_complete:
            raise PilotError(f"implementations disagree on completeness at {site_id}")
        if primary_complete and targets != cross_targets:
            raise PilotError(f"implementations disagree on exact targets at {site_id}")
        excluded_defs = [
            row for row in primary.get("derivations") or []
            if row.get("excluded_from_domain") is True
        ]
        if excluded_defs:
            dead_definition_correction.append({
                "site": site_id,
                "excluded_definition_occurrences": excluded_defs,
            })
        if primary_complete:
            target_owners = []
            intersections = []
            for target_text in targets:
                target = int(target_text, 16)
                target_owners.append(_target_owner(index, frozen["image"], target))
                protected_id = f"{frozen['image']}:{target_text}".lower()
                if protected_id in protected:
                    intersections.append(protected_id)
                local_candidate_edges.add(f"{site_id}->SCUS_942_88:{target_text}")
            if intersections:
                raise PilotError(f"proved domain intersects protected set: {site_id} {intersections}")
            local_basis_ids.append(site_id)
            outcome = "LOCAL_FULL_TARGET_DOMAIN_BASIS"
            wall = None
        else:
            target_owners = []
            outcome = "NOT_LANDED"
            wall = primary.get("breaking_instruction")
            if not wall:
                raise PilotError(f"unproved site lacks exact breaking instruction: {site_id}")
        outcomes.append({
            "site": site_id,
            "frozen_rank": len(outcomes) + 1,
            "frozen_stratum": frozen["stratum"],
            "outcome": outcome,
            "proof_kind": None,
            "local_proof_basis_kind": (
                "entry_scoped_full_target_domain" if primary_complete else None),
            "targets": targets,
            "target_owner_entries": target_owners,
            "protected_set_intersection": [],
            "primary": primary,
            "independent": cross,
            "wall": wall,
            "register_or_cell_chain": {
                "target_register": frozen["register"],
                "cell": None,
                "primary_derivations": primary.get("derivations") or [],
            },
            "writer_recursion_cycle": [],
            "open_dependency": (
                "declared entry/caller value remains unproved"
                if not primary_complete and frozen["register"] == "ra" else None),
        })

    if local_basis_ids != list(EXPECTED_PILOT[4:8]):
        raise PilotError(f"local exact-domain set differs: {local_basis_ids!r}")
    expected_targets = ["0x80018cc4", "0x80018f4c", "0x80019244"]
    if any(row["targets"] != expected_targets for row in outcomes
           if row["local_proof_basis_kind"]):
        raise PilotError("local domains differ from the independently agreed exact set")
    if len(local_candidate_edges) != 12:
        raise PilotError(
            f"local per-edge proof-basis set is not 12: {len(local_candidate_edges)}")

    # Gate-grade full domains need more than entry-scoped register dataflow.
    # Reuse the accepted external-entry gate, then extend it with this work
    # order's stricter corrected 179-site universe (which deliberately retains
    # convention-only jr-ra sites).  Four locally exact internal transfers are
    # excluded from the unresolved source set; every other corrected site is a
    # possible edge into the owner until its target domain is proved disjoint.
    owner = site_rows[local_basis_ids[0]]["owner"]
    owner_image = owner["image"]
    owner_lo, owner_hi = _int(owner["entry"]), _int(owner["end"])
    if any(site_rows[site_id]["owner"] != owner for site_id in local_basis_ids):
        raise PilotError("local proof-basis sites do not share one owner extent")
    closure = typed_state._indirect_transfer_closure(index)
    accepted_gate_hits = typed_state._external_interior_entries(
        index, owner_image, owner_lo, owner_hi, closure)
    union_ids = freeze["stage_0_union"]["movement"]["corrected_sites_in"]
    key_to_site = {
        (row["image"], _int(row["pc"])): row["id"]
        for row in freeze["stage_1_classification"]["sites"]
    }
    helper_unknown_ids = set()
    helper_concrete_hits = []
    for hit in accepted_gate_hits:
        if hit.get("target_domain_complete") is False:
            key = (hit["image"], _int(hit["pc"]))
            if key not in key_to_site:
                raise PilotError(f"accepted gate unknown is outside corrected union: {key}")
            helper_unknown_ids.add(key_to_site[key])
        else:
            helper_concrete_hits.append(hit)
    if helper_concrete_hits:
        raise PilotError(
            f"unexpected concrete external interior entries: {helper_concrete_hits!r}")
    unresolved_entry_ids = []
    for site_id in union_ids:
        row = site_rows[site_id]
        if not typed_state._images_can_coexist(index, row["image"], owner_image):
            continue
        if site_id in local_basis_ids:
            continue
        unresolved_entry_ids.append(site_id)
    unresolved_entry_ids = sorted(unresolved_entry_ids)
    helper_unknown_ids = set(helper_unknown_ids)
    extra_entry_ids = sorted(set(unresolved_entry_ids) - helper_unknown_ids)
    if not helper_unknown_ids <= set(unresolved_entry_ids):
        raise PilotError("accepted external-entry gate exceeds corrected unresolved set")
    internal_entry_ids = sorted(
        site_id for site_id in unresolved_entry_ids
        if site_rows[site_id]["image"] == owner_image
        and owner_lo <= _int(site_rows[site_id]["pc"]) < owner_hi)
    external_entry_ids = sorted(set(unresolved_entry_ids) - set(internal_entry_ids))
    if (len(helper_unknown_ids), len(extra_entry_ids), len(unresolved_entry_ids),
            len(internal_entry_ids), len(external_entry_ids)) != (156, 19, 175, 1, 174):
        raise PilotError("gate-grade external-entry wall geometry drifted")
    first_entry = site_rows[unresolved_entry_ids[0]]
    entry_scope_set_id = "gte_quad_near_clip_dispatch:unresolved_entry_sources"
    for outcome in outcomes:
        if outcome["site"] not in local_basis_ids:
            continue
        outcome["outcome"] = "NOT_LANDED_EXTERNAL_INTERIOR_ENTRY_UNIVERSE"
        outcome["wall"] = {
            "pc": first_entry["pc"],
            "word": first_entry["instruction_evidence"]["word"],
            "reason": "blocked_external_interior_entry_universe",
            "entry_source_set_id": entry_scope_set_id,
            "entry_source_count": len(unresolved_entry_ids),
            "first_entry_source_site_id": first_entry["id"],
        }
        outcome["open_dependency"] = (
            "entry-scoped exact domain is not gate grade while 175 corrected "
            "unresolved transfer sites can still enter the owner interior")

    landed_ids: list[str] = []
    candidate_edges: set[str] = set()

    table_pilot_ids = [
        site_id for site_id in EXPECTED_PILOT if site_rows[site_id]["stratum"] == "table_backed"]
    if table_pilot_ids:
        raise PilotError(f"frozen pilot unexpectedly contains table candidates: {table_pilot_ids}")
    runtime = _runtime_crosscheck(
        capsules, u3, u3_raw, u3_source_raw, local_basis_ids)
    go_conditions = {
        "at_least_four_landed": len(landed_ids) >= 4,
        "at_least_one_whole_table_value_domain_invariant": False,
        "runtime_crosscheck_clean": runtime["clean_for_go"],
        "soundness_violation_absent": not runtime["soundness_violation"],
    }
    decision = "GO" if all(go_conditions.values()) else "NO-GO"
    if decision != "NO-GO":
        raise PilotError("pilot unexpectedly returned GO; cascade implementation is required")

    remaining = sorted(set(union_ids) - set(landed_ids))
    unattempted = sorted(set(union_ids) - set(EXPECTED_PILOT))
    attempted_unresolved = [site_id for site_id in EXPECTED_PILOT if site_id not in landed_ids]
    remaining_counts = Counter(
        row["stratum"] for row in freeze["stage_1_classification"]["sites"]
        if row["id"] in set(remaining))
    remaining_strata = {
        name: remaining_counts.get(name, 0)
        for name in freeze["stage_1_classification"]["histogram"]
    }
    item2_paragraph = (
        "The item-2 bar would have to accept exclusion for all 179 corrected code-only "
        "indirect sites that this increment does not prove at gate grade: twelve "
        "attempted pilot sites with named walls and 167 sites stopped by the mandatory "
        "pilot gate. Four attempted sites have exact domains only from their declared "
        "entry; 175 unresolved transfer sites can still enter that owner interior and "
        "bypass those definitions. The 179 include all 74 table/cell-backed candidates "
        "without a complete whole-table runtime-state invariant and 105 sites in the "
        "computed, register, incoming-ra, opaque, or mixed strata. The retained 50 "
        "frame-boundary capsules "
        "and preserved u3 entry watches contain zero source-site/indirect-target tuples "
        "for those sites. The u3 watches record entry hits of 0, 60, 60, and 60 at "
        "0x80018CC4, 0x80018F4C, 0x80019244, and the dead-lexical 0x8001961C value, "
        "respectively; those hits do not identify which indirect site supplied the "
        "target and therefore do not prove exclusion."
    )

    verdicts = frontier.get("verdicts") or {}
    if (verdicts.get("dimension_promoted") is not False
            or verdicts.get("item2_ready_for_review") is not False
            or verdicts.get("review_blockers") != [
                "IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"]):
        raise PilotError("protected F01 state differs from accepted partial baseline")

    return {
        "_comment": ("Mandatory target-domain/exclusion pilot, run only after freeze "
                     f"{FREEZE_COMMIT}. It is a strict NO-GO and stops before any "
                     "gate/index/caller-domain/full-pass mutation."),
        "schema": SCHEMA,
        "inputs": {
            "issued_baseline_commit": BASELINE_COMMIT,
            "work_order_commit": SPEC_COMMIT,
            "pre_outcome_freeze_commit": FREEZE_COMMIT,
            "derived_input_snapshot_commit": FREEZE_COMMIT,
            "freeze_artifact": str(FREEZE_ARTIFACT.relative_to(ROOT)),
            "freeze_artifact_sha256": _sha(freeze_raw),
            "freeze_note_sha256": _sha(freeze_note_raw),
            "static_index_sha256": _sha(index_raw),
            "capsule_set_sha256": _sha(capsules_raw),
            "frontier_result_sha256": _sha(frontier_raw),
            "work_order_sha256": _sha(work_raw),
            "mechanics_baseline_sha256": _sha(mechanics_raw),
            "u3_evidence_sha256": _sha(u3_raw),
            "u3_source_sha256": _sha(u3_source_raw),
            "accepted_external_entry_gate_sha256": _sha(typed_state_raw),
            "primary_C_sha256": _sha(PRIMARY_C.read_bytes()),
            "independent_C_sha256": _sha(CROSSCHECK_C.read_bytes()),
            "image_map_sha256": _sha(image_map),
            "image_identities": image_identities,
        },
        "configuration": {
            "pilot_frozen_before_outcomes": True,
            "pilot_budget_scope_only": True,
            "runtime_replay_performed": False,
            "instrumented_run_performed": False,
            "gate_artifact_mutated": False,
            "static_index_mutated": False,
            "caller_domain_rerun": False,
            "full_union_stage2_pass_run": False,
        },
        "c_controls": {
            "primary_source": str(PRIMARY_C.relative_to(ROOT)),
            "primary_algorithm": "backward reaching-definition proof from image bytes",
            "primary_query_form": "IMAGE:START:END:REG:PC",
            "primary_compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
            "primary_binary_sha256": _sha(primary_binary),
            "primary_selftest": primary_selftest | {
                "stdout_sha256": _sha(primary_selftest_proc.stdout.encode())},
            "independent_source": str(CROSSCHECK_C.relative_to(ROOT)),
            "independent_algorithm": "forward finite-set fixpoint from image bytes",
            "independent_compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
            "independent_binary_sha256": _sha(cross_binary),
            "independent_selftest": cross_selftest,
            "all_12_classifications_agree": True,
            "all_landed_exact_target_sets_agree": True,
            "instruction_decoding_in_python": False,
        },
        "stage_1_full_union_histogram": freeze["stage_1_classification"]["histogram"],
        "pilot": {
            "universe_name": "12 sites frozen before outcomes in the committed Stage-0/1 barrier",
            "site_ids": list(EXPECTED_PILOT),
            "attempted_count": 12,
            "outcomes": outcomes,
            "landed_count": len(landed_ids),
            "landed_site_ids": landed_ids,
            "local_domain_basis_count": len(local_basis_ids),
            "local_domain_basis_site_ids": local_basis_ids,
            "not_landed_count": len(attempted_unresolved),
            "not_landed_site_ids": attempted_unresolved,
            "whole_table_candidate_count": 0,
            "whole_table_candidate_ids": [],
            "whole_table_invariant_landed_count": 0,
            "dead_lexical_definition_correction": dead_definition_correction,
        },
        "gate_grade_entry_scope": {
            "set_id": entry_scope_set_id,
            "owner": owner,
            "definition": (
                "accepted proved-or-unknown external-entry gate, extended by the "
                "corrected convention-free 179-site work-order universe"),
            "accepted_gate_helper_unknown_count": len(helper_unknown_ids),
            "accepted_gate_helper_unknown_site_ids": sorted(helper_unknown_ids),
            "corrected_union_additional_count": len(extra_entry_ids),
            "corrected_union_additional_site_ids": extra_entry_ids,
            "locally_exact_internal_site_count": len(local_basis_ids),
            "locally_exact_internal_site_ids": local_basis_ids,
            "unresolved_entry_source_count": len(unresolved_entry_ids),
            "unresolved_entry_source_ids": unresolved_entry_ids,
            "unresolved_internal_source_count": len(internal_entry_ids),
            "unresolved_internal_source_ids": internal_entry_ids,
            "unresolved_external_source_count": len(external_entry_ids),
            "unresolved_external_source_ids": external_entry_ids,
            "concrete_external_interior_entries": helper_concrete_hits,
            "entry_scope_closed": False,
        },
        "per_edge_gate_movement": {
            "comparison": "exact site and site->target edge sets in both directions",
            "baseline_proved_site_count": len(baseline_sites),
            "baseline_proved_edge_count": len(baseline_edges),
            "local_proof_basis_site_ids": local_basis_ids,
            "local_proof_basis_edge_ids": sorted(local_candidate_edges),
            "local_proof_basis_site_count": 4,
            "local_proof_basis_edge_occurrence_count": 12,
            "candidate_gate_grade_site_ids": landed_ids,
            "candidate_gate_grade_edge_ids": sorted(candidate_edges),
            "candidate_gate_grade_site_count": 0,
            "candidate_gate_grade_edge_occurrence_count": 0,
            "applied_site_additions": [],
            "applied_edge_additions": [],
            "applied_site_removals": [],
            "applied_edge_removals": [],
            "current_proved_site_count": len(baseline_sites),
            "current_proved_edge_count": len(baseline_edges),
            "why_not_applied": "NO-GO stops before gate/index mutation",
        },
        "capsule_and_preserved_session_crosscheck": runtime,
        "decision": {
            "verdict": decision,
            "go_conditions": go_conditions,
            "landed_count": len(landed_ids),
            "local_domain_basis_count": len(local_basis_ids),
            "whole_table_invariant_landed_count": 0,
            "soundness_halt": False,
            "reason": ("four entry-scoped exact domains remain below gate grade because "
                       "the owner has 175 unresolved interior-entry sources; the frozen "
                       "pilot also has no table-backed site and retained evidence cannot "
                       "supply the mandatory site-time runtime cross-check"),
            "full_pass_authorized": False,
            "cascade_started": False,
            "queued_successor": None,
        },
        "no_go_report": {
            "full_union_count": 179,
            "full_union_histogram": freeze["stage_1_classification"]["histogram"],
            "proved_in_this_pilot_count": 0,
            "proved_in_this_pilot_ids": landed_ids,
            "local_domain_basis_count": 4,
            "local_domain_basis_ids": local_basis_ids,
            "remaining_without_this_proof_count": len(remaining),
            "remaining_without_this_proof_ids": remaining,
            "remaining_stratum_histogram": remaining_strata,
            "attempted_wall_count": len(attempted_unresolved),
            "attempted_wall_ids": attempted_unresolved,
            "unattempted_due_pilot_stop_count": len(unattempted),
            "unattempted_due_pilot_stop_ids": unattempted,
            "writer_recursion_cycle_count": 0,
            "writer_recursion_cycles": [],
            "per_attempted_site": outcomes,
            "item2_bar_facts_no_recommendation": item2_paragraph,
            "recommendation_to_lower_bar": None,
        },
        "protected_state": {
            "f01_status": "partial",
            "item_2": "not_met",
            "dimension_promoted": False,
            "item2_ready_for_review": False,
            "review_blockers": ["IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"],
            "mechanics_baseline_modified": False,
            "registry_modified": False,
            "gate_receipt_modified": False,
            "writer_universe_gate_modified": False,
            "value_domain_gate_modified": False,
        },
        "stage_c_not_run": {
            "closure_census_delta": None,
            "caller_domain_frozen_20_rerun": False,
            "typed_state_regenerated": False,
            "campaign_regenerated": False,
            "old_pins_replaced": [],
        },
    }


def _render(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    raw = _render(build())
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.check:
        if not output.is_file() or output.read_bytes() != raw:
            print(f"target-exclusion pilot differs: {output}")
            return 1
        print(f"target-exclusion pilot current: {output}")
        return 0
    output.write_bytes(raw)
    print(f"wrote {output} ({len(raw)} bytes, sha256={_sha(raw)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
