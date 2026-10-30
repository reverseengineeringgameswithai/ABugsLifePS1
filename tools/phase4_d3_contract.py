#!/usr/bin/env python3
"""Assess the four frozen Phase-4 D3 contracts without promoting F01.

The driver consumes the exact pre-outcome sample freeze, hash-verified image
bytes, the retained runtime corpus, and the existing typed-state/region
machinery.  Compiled C owns instruction decoding.  Runtime observations may
falsify or corroborate a candidate, but never establish a universal domain.

This is intentionally a fail-closed pilot: a candidate target set is not a
membership invariant, and a known writer is not a writer census.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import phase4_discipline_pilot as precedent

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_d3_contract.json"
WORK_ORDER = ROOT / "engineering-specs/phase4-d3-contract-work-order.md"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"
ASSIGNMENT = ROOT / "analysis/phase4_discipline_assignment.json"
DISCIPLINE_PILOT = ROOT / "analysis/phase4_discipline_pilot.json"
FREEZE = ROOT / "analysis/phase4_target_exclusion_freeze.json"
INDEX = ROOT / "analysis/phase4_static_frontier_index.json"
TUPLES = ROOT / "analysis/phase4_f01_jr_tuple_capture.json"
TYPED_STATE = ROOT / "analysis/phase4_f01_typed_state.json"
ABI_LEDGER = ROOT / "analysis/phase4_f01_abi_ledger.json"
FN_PTR_FIELDS = ROOT / "analysis/phase3_fn_ptr_fields.json"
GAP_SEMANTICS = ROOT / "analysis/phase4_f01_gap_semantics.json"
ADDRESS_TAKEN = ROOT / "analysis/phase4_address_taken_pilot.json"
HOISTED = ROOT / "analysis/hoisted_load_idiom_scan.json"
FMV_STATIC = ROOT / "analysis/phase4_fmv_static_owners.json"
FUNCTIONS_RESIDENT = ROOT / "analysis/functions_resident.txt"
MECHANICS_BASELINE = ROOT / "analysis/mechanics_baseline.yaml"

PRIMARY_C = ROOT / "tools/phase4_target_exclusion_prover.c"
CROSS_C = ROOT / "tools/phase4_target_exclusion_crosscheck.c"
REGION_C = ROOT / "tools/region_provenance.c"
WORDS_C = ROOT / "tools/phase4_d3_contract_words.c"

INPUT_COMMIT = "b9bbd591233c4"
SAMPLE_FREEZE_COMMIT = "3381f0dcd4a7f"
SCHEMA = "abl-phase4-d3-contract/1"
FREEZE_MARKER = "D3 contract pilot FREEZE (pre-outcome)"
SHARED_CELL = "0x8007fbc4"
DYNAMIC_SITE = "MEMORY:0x800b970c:jr:v0"


class ContractError(RuntimeError):
    """A pinned identity, exact-set, or fail-closed policy check failed."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    return int(str(value), 0)


def _git_show(commit: str, path: Path) -> bytes:
    rel = str(path.relative_to(ROOT))
    proc = subprocess.run(
        ["git", "show", f"{commit}:{rel}"], cwd=ROOT,
        capture_output=True, check=False,
    )
    if proc.returncode:
        raise ContractError(
            f"cannot read pinned object {commit}:{rel}: "
            + proc.stderr.decode(errors="replace").strip())
    return proc.stdout


def _git_json(commit: str, path: Path) -> tuple[dict, bytes]:
    raw = _git_show(commit, path)
    return json.loads(raw), raw


def _require_ancestor(commit: str) -> None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT, check=False,
    )
    if proc.returncode:
        raise ContractError(f"HEAD does not descend from {commit}")


def _require_worktree_matches(commit: str, paths: list[Path]) -> dict[str, str]:
    hashes = {}
    for path in paths:
        pinned = _git_show(commit, path)
        current = path.read_bytes()
        if current != pinned:
            raise ContractError(
                f"working-tree input differs from {commit}: {path.relative_to(ROOT)}")
        hashes[str(path.relative_to(ROOT))] = _sha(pinned)
    return hashes


def _extract_freeze(raw: bytes, expected: list[str]) -> bytes:
    text = raw.decode()
    marker = f"## 2026-08-10 — {FREEZE_MARKER}"
    if marker not in text:
        raise ContractError("pre-outcome experiment freeze marker is absent")
    section = marker + text.split(marker, 1)[1].split("\n## ", 1)[0]
    listed = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped[:1].isdigit() and ". `" in stripped and stripped.endswith("`"):
            listed.append(stripped.split("`", 2)[1])
    if listed != expected:
        raise ContractError("pre-outcome experiment sample differs from assignment")
    forbidden = ("contract established", "per-site outcome", "PILOT DECISION")
    if any(value in section for value in forbidden):
        raise ContractError("sample freeze contains an outcome")
    return (section.rstrip() + "\n").encode()


def _runtime_counts(doc: dict) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for source in (doc["results"]["tuples"], doc["behavior_library_sweep"]["tuples"]):
        for site_id, targets in source.items():
            for target, count in targets.items():
                counts[site_id][str(target).lower()] += int(count)
    for site_id, target in doc["hundred_percent_corpus_sweep"][
            "new_targets_at_known_sites"]:
        # That list preserves target discovery, not a hit multiplicity.  Keep
        # it in the domain without inventing a count.
        counts[site_id].setdefault(str(target).lower(), 0)
    return counts


def _record_extent(row: dict) -> tuple[int, int]:
    if row.get("entry") is not None and row.get("end") is not None:
        return _int(row["entry"]), _int(row["end"])
    extent = row.get("extent")
    if isinstance(extent, list) and len(extent) == 2:
        return _int(extent[0]), _int(extent[1])
    raise ContractError("static-index record lacks an extent")


def _query_spec(site: dict) -> str:
    owner = site["owner"]
    return ":".join((
        owner["image"], owner["entry"], owner["end"],
        site["decoded_register"], site["pc"],
    ))


def _probe_rows(doc: dict) -> dict[str, dict]:
    return {row["site_pc"].lower(): row for row in doc["queries"]}


def _summarize_primary(row: dict) -> dict:
    return {
        "site_pc": row["site_pc"],
        "site_word": row["site_word"],
        "entry_scoped_verdict": row["verdict"],
        "entry_scoped_targets": row["targets"],
        "scope": row["scope"],
        "breaking_instruction": row["breaking_instruction"],
        "derivations": row["derivations"],
    }


def _summarize_cross(row: dict) -> dict:
    return {
        "site_pc": row["site_pc"],
        "site_word": row["site_word"],
        "entry_scoped_verdict": row["full_target_domain_complete"],
        "entry_scoped_targets": row["targets"],
        "entry_reached": row["entry_reached"],
        "unknown_reasons": row["unknown_reasons"],
        "algorithm": row["algorithm"],
    }


def _find_fmv_cabe0(node: Any, path: tuple[str, ...] = ()) -> list[dict]:
    found = []
    if isinstance(node, dict):
        values = {
            key: str(value).lower() for key, value in node.items()
            if key in {"address", "base", "player_boundary_base"}
        }
        if "0x800cabe0" in values.values():
            found.append({
                "json_path": ".".join(path),
                "name": node.get("name"),
                "address": node.get("address") or node.get("base")
                           or node.get("player_boundary_base"),
                "storage_type": node.get("storage_type"),
                "residency": node.get("residency"),
                "valid_domain": node.get("valid_domain"),
                "size": node.get("size"),
                "layout": node.get("layout"),
                "role": node.get("role"),
            })
        for key, value in node.items():
            found.extend(_find_fmv_cabe0(value, path + (str(key),)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_find_fmv_cabe0(value, path + (str(index),)))
    return found


def _protected_intersections(protected: set[str], image: str | None,
                             targets: list[str]) -> dict:
    targets = [target.lower() for target in targets]
    exact = [] if image is None else sorted(
        f"{image}:{target}" for target in targets
        if f"{image}:{target}" in protected)
    protected_pcs = {value.rsplit(":", 1)[1].lower() for value in protected}
    numeric = sorted(set(targets) & protected_pcs)
    return {
        "candidate_count": len(targets),
        "exact_image_pc_intersections": exact,
        "numeric_pc_intersections": numeric,
        "candidate_set_disjoint": not exact and not numeric,
        "authority": (
            "candidate/observed-set arithmetic only; this does not prove the "
            "dispatch membership set is complete"),
    }


def build() -> dict:
    _require_ancestor(INPUT_COMMIT)
    _require_ancestor(SAMPLE_FREEZE_COMMIT)
    pinned_paths = [
        WORK_ORDER, ASSIGNMENT, DISCIPLINE_PILOT, FREEZE, INDEX, TUPLES,
        TYPED_STATE, ABI_LEDGER, FN_PTR_FIELDS, GAP_SEMANTICS, ADDRESS_TAKEN,
        HOISTED, FMV_STATIC, FUNCTIONS_RESIDENT, MECHANICS_BASELINE,
        PRIMARY_C, CROSS_C, REGION_C,
    ]
    input_hashes = _require_worktree_matches(INPUT_COMMIT, pinned_paths)

    assignment, assignment_raw = _git_json(INPUT_COMMIT, ASSIGNMENT)
    discipline, discipline_raw = _git_json(INPUT_COMMIT, DISCIPLINE_PILOT)
    freeze, freeze_raw = _git_json(INPUT_COMMIT, FREEZE)
    index, index_raw = _git_json(INPUT_COMMIT, INDEX)
    tuples_doc, tuples_raw = _git_json(INPUT_COMMIT, TUPLES)
    typed_state, typed_raw = _git_json(INPUT_COMMIT, TYPED_STATE)
    abi, abi_raw = _git_json(INPUT_COMMIT, ABI_LEDGER)
    fields, fields_raw = _git_json(INPUT_COMMIT, FN_PTR_FIELDS)
    gaps, gaps_raw = _git_json(INPUT_COMMIT, GAP_SEMANTICS)
    address_taken, address_raw = _git_json(INPUT_COMMIT, ADDRESS_TAKEN)
    hoisted, hoisted_raw = _git_json(INPUT_COMMIT, HOISTED)
    fmv, fmv_raw = _git_json(INPUT_COMMIT, FMV_STATIC)
    work_order_raw = _git_show(INPUT_COMMIT, WORK_ORDER)
    functions_raw = _git_show(INPUT_COMMIT, FUNCTIONS_RESIDENT)

    if assignment.get("schema") != "abl-phase4-discipline-assignment/1":
        raise ContractError("unexpected discipline assignment schema")
    d3_universe = assignment["assignments"]["by_discipline"]["D3_pointer_dispatch"]
    if len(d3_universe) != 140 or len(set(d3_universe)) != 140:
        raise ContractError("D3 universe is not exactly 140 unique IDs")
    d3_selection = assignment["pilot_selection"]["D3"]
    sample = d3_selection["table_backed_site_ids"] + d3_selection["next_site_ids"]
    if len(sample) != 12 or len(set(sample)) != 12 or not set(sample) <= set(d3_universe):
        raise ContractError("D3 sample does not tile 12 unique universe members")
    freeze_raw_experiment = _git_show(SAMPLE_FREEZE_COMMIT, EXPERIMENT)
    freeze_section = _extract_freeze(freeze_raw_experiment, sample)
    protected = set(freeze["protected_set"]["combined_ids"])
    if len(protected) != 128:
        raise ContractError("protected set is not 128 unique image/PC IDs")

    sites = {row["id"]: row for row in assignment["assignments"]["sites"]}
    if set(sample) - set(sites):
        raise ContractError("sample site missing from assignment site rows")
    image_map, identities = precedent._image_map(index)
    image_rows = {row["image_id"]: row for row in index["images"]}

    with tempfile.TemporaryDirectory(prefix="phase4-d3-contract-") as tmp_text:
        temp = Path(tmp_text)
        map_path = temp / "images.txt"
        map_path.write_bytes(image_map)
        primary_bin = temp / "primary"
        cross_bin = temp / "cross"
        region_bin = temp / "region"
        words_bin = temp / "words"
        strict = ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror"]
        primary_binary, primary_compile = precedent._compile(PRIMARY_C, primary_bin, strict)
        cross_binary, cross_compile = precedent._compile(CROSS_C, cross_bin, strict)
        words_binary, words_compile = precedent._compile(WORDS_C, words_bin, strict)
        region_binary, region_compile = precedent._compile(
            REGION_C, region_bin, ["-std=gnu11", "-O2", "-Wall", "-Wextra"])
        if primary_compile or cross_compile or words_compile:
            raise ContractError("strict C probes emitted compiler diagnostics")

        primary_self, primary_self_raw, _ = precedent._run_json(
            [str(primary_bin), "--self-test"])
        cross_self, cross_self_raw, _ = precedent._run_json(
            [str(cross_bin), "--self-test"])
        words_self, words_self_raw, _ = precedent._run_json(
            [str(words_bin), "--self-test"])
        if primary_self.get("verdict") is not True or primary_self.get("passed") != 9:
            raise ContractError("primary C self-test drifted")
        if cross_self.get("verdict") is not True or cross_self.get("passed") != 8:
            raise ContractError("cross-check C self-test drifted")
        if words_self != {"tool": "phase4_d3_contract_words", "passed": 4,
                          "total": 4, "verdict": True}:
            raise ContractError("word-reader C self-test drifted")

        specs = [_query_spec(sites[site_id]) for site_id in sample]
        primary, primary_stdout, primary_stderr = precedent._run_json(
            [str(primary_bin), str(map_path), *specs])
        cross, cross_stdout, cross_stderr = precedent._run_json(
            [str(cross_bin), str(map_path), *specs])
        scus = image_rows["SCUS_942_88"]
        memory = image_rows["MEMORY"]
        words, words_stdout, words_stderr = precedent._run_json([
            str(words_bin), scus["path"], scus["file_va_base"],
            memory["path"], memory["file_va_base"],
        ])
        region = precedent._region_writer_scan(
            region_bin, index, functions_raw, temp)

    if primary.get("query_count") != 12 or cross.get("query_count") != 12:
        raise ContractError("compiled C probes did not process all 12 sample sites")
    if words.get("site_count") != 12:
        raise ContractError("independent word reader did not process all 12 sites")
    primary_rows = _probe_rows(primary)
    cross_rows = _probe_rows(cross)
    word_rows = {row["id"]: row for row in words["sites"]}
    if set(word_rows) != set(sample):
        raise ContractError("word-reader site set differs from frozen sample")

    for site_id in sample:
        site = sites[site_id]
        pc = site["pc"].lower()
        p = primary_rows[pc]
        x = cross_rows[pc]
        w = word_rows[site_id]
        if (bool(p["verdict"]) != bool(x["full_target_domain_complete"])
                or sorted(p["targets"]) != sorted(x["targets"])):
            raise ContractError(f"independent C domain disagreement at {site_id}")
        if (p["site_word"].lower() != site["word"].lower()
                or x["site_word"].lower() != site["word"].lower()
                or w["site_word"].lower() != site["word"].lower()
                or w["delay_word"].lower() != site["delay_slot_word"].lower()):
            raise ContractError(f"three-way site-byte disagreement at {site_id}")
    accepted_entry_scoped = [
        site_id for site_id in sample if primary_rows[sites[site_id]["pc"].lower()]["verdict"]]
    if accepted_entry_scoped != ["SCUS_942_88:0x80060c78:jalr:t2"]:
        raise ContractError(f"entry-scoped candidate set drifted: {accepted_entry_scoped}")
    bios_row = primary_rows["0x80060c78"]
    if bios_row["targets"] != ["0x000000b0"]:
        raise ContractError("BIOS entry-scoped target is not exactly B0")

    direct_cell = [
        row for row in gaps["library_workarea_partition"]["probe"]["sites"]
        if str(row.get("target", "")).lower() == SHARED_CELL]
    direct_writers = [row for row in direct_cell if row["kind"] == "store"]
    if [(row["pc"].lower(), int(row["width"])) for row in direct_writers] != [
            ("0x80060fe8", 4)]:
        raise ContractError("shared-cell known direct-writer lower bound drifted")
    known_writer = words["known_direct_writer"]
    if (known_writer["derived_address"] != SHARED_CELL
            or known_writer["derived_value"] != "0x80061668"):
        raise ContractError("independent C did not derive SetDumpFnt -> FntPrint")
    if (region["unresolved_write_count"] != 4266
            or region["full_width_unresolved_write_count"] != 2244):
        raise ContractError("shared-cell region residual drifted")

    actor_7c = fields["records"]["actor_record"]["+0x7C"]
    if (actor_7c["instances_seen"] != 1286 or actor_7c["distinct_handlers"] != 9
            or actor_7c["hit_rate"] != 0.608):
        raise ContractError("retained actor +0x7C observation drifted")
    abi_domains = abi["coverage"]["consumed_argument_domains_known"]
    if abi_domains["fraction"] != "1/867":
        raise ContractError("ABI domain wall is not 1/867")
    object_binding = next(
        row for row in typed_state["bindings"]
        if row.get("image") == "SCUS_942_88"
        and str(row.get("function", "")).lower() == "0x8004c898")
    if object_binding.get("accepted") is not False:
        raise ContractError("object owner binding unexpectedly became accepted")

    guarded = address_taken["stage_b_pilot"]["guarded_table_proofs"]
    if len(guarded) != 1 or guarded[0]["site"].lower() != "memory:0x800b970c":
        raise ContractError("retained frontend guarded-table proof drifted")
    frontend = words["frontend_dispatch"]
    c_slots = [
        {"index": row["index"], "slot_va": row["address"],
         "target": row["pristine_value"]}
        for row in frontend["slots"]]
    retained_slots = guarded[0]["slots"]
    if c_slots != retained_slots:
        raise ContractError("independent C frontend slots disagree with retained proof")
    if (frontend["table_start"] != "0x800b57b4"
            or frontend["table_end"] != "0x800b57d4"):
        raise ContractError("frontend table byte extent drifted")

    hoisted_pcs = {
        str(row[key]).lower() for row in hoisted["hits"]
        for key in ("load_pc", "logged_pc")}
    sample_source_pcs = {row["source_pc"].lower() for row in word_rows.values()}
    hoisted_intersection = sorted(sample_source_pcs & hoisted_pcs)
    if hoisted.get("sites") != 22 or hoisted_intersection:
        raise ContractError("sample intersects the 22-site hoisted-load control")

    runtime = _runtime_counts(tuples_doc)
    object_targets = sorted(runtime["SCUS_942_88:0x8004d1e8:jalr:v0"])
    bios_targets = sorted(runtime["SCUS_942_88:0x80060c78:jalr:t2"])
    if len(object_targets) != 10 or bios_targets != ["0x000000b0"]:
        raise ContractError("sample runtime target sets drifted")
    dynamic_targets = sorted(runtime[DYNAMIC_SITE])
    if "0x800cabe0" not in dynamic_targets or "0x800cabe4" not in dynamic_targets:
        raise ContractError("dynamic-module runtime witnesses are absent")

    code_ranges = [
        (row["image_id"], *_record_extent(row)) for row in index["records"]
        if row.get("range_type") in {"code", "thunk"}]
    dynamic_outside_static = [
        target for target in dynamic_targets
        if not any(lo <= int(target, 16) < hi for _image, lo, hi in code_ranges)]
    if "0x800cabe0" not in dynamic_outside_static or "0x800cabe4" not in dynamic_outside_static:
        raise ContractError("dynamic targets unexpectedly entered the static code census")
    tuple_text = tuples_raw.decode(errors="replace")
    retained_residency = "memory.getResidency" in tuple_text
    retained_transfer_log = "transferLog" in tuple_text
    if retained_residency or retained_transfer_log:
        raise ContractError("runtime artifact unexpectedly gained loader/residency identity")
    fmv_cabe0 = _find_fmv_cabe0(fmv)
    if not any(row["residency"] == "FMV.BIN Region B" for row in fmv_cabe0):
        raise ContractError("FMV residency alias at 0x800CABE0 is absent")

    shared_sites = [
        site_id for site_id in sample
        if word_rows[site_id]["source_kind"] == "shared_cell_load"]
    object_sites = [
        site_id for site_id in sample
        if word_rows[site_id]["source_kind"] == "object_field_load"]
    bios_sites = [
        site_id for site_id in sample
        if word_rows[site_id]["source_kind"] == "bios_immediate"]
    if [len(shared_sites), len(object_sites), len(bios_sites)] != [10, 1, 1]:
        raise ContractError("sample contract partition is not 10/1/1")

    shared_disjoint = _protected_intersections(
        protected, "SCUS_942_88", [known_writer["derived_value"]])
    object_disjoint = _protected_intersections(
        protected, "SCUS_942_88", object_targets)
    bios_disjoint = _protected_intersections(protected, None, bios_targets)
    dynamic_disjoint = _protected_intersections(protected, None, dynamic_targets)
    if not all(row["candidate_set_disjoint"] for row in (
            shared_disjoint, object_disjoint, bios_disjoint, dynamic_disjoint)):
        raise ContractError("candidate/observed target intersects the protected set")

    contracts = {
        "shared_dispatch_cell_0x8007fbc4": {
            "contract_established": False,
            "sample_site_count": len(shared_sites),
            "sample_site_ids": shared_sites,
            "byte_extent": {"start": SHARED_CELL, "end": "0x8007fbc8", "bytes": 4},
            "known_direct_writer_lower_bound": {
                **known_writer,
                "function": "SetDumpFnt",
                "derived_value_name": "FntPrint",
                "direct_writer_count_is_census": False,
            },
            "writer_set": region,
            "table_membership_invariant": {
                "proved": False,
                "reason": (
                    "4266 unresolved stores across 21 images, including 2244 full-width "
                    "stores, retain undecided effective addresses relative to the cell"),
            },
            "protected_set_disjointness": {
                **shared_disjoint,
                "proved_for_universal_membership_set": False,
                "known_writer_value_only": True,
            },
            "runtime": {
                "observed_sample_sites": 0,
                "silent_sample_sites": len(shared_sites),
                "meaning": "silence cannot close the writer or value universe",
            },
            "immunity_to_missing_reaching_definitions": (
                "No proof is accepted: the region writer residual is carried as part of "
                "the premise, so the known direct writer cannot be promoted to a census."),
            "wall_shape": "technique-shaped",
            "why_shape": (
                "a sound region-sensitive alias/writer engine could bound all 4266 stores "
                "away from the cell or prove their stored value domains"),
            "named_prerequisite": "complete shared-cell alias and writer-value closure",
        },
        "object_field_provenance": {
            "contract_established": False,
            "sample_site_count": len(object_sites),
            "sample_site_ids": object_sites,
            "byte_fact": word_rows[object_sites[0]],
            "retained_field_observation": actor_7c,
            "runtime_observed_targets": {
                "count": len(object_targets),
                "targets": object_targets,
                "hit_counts": dict(sorted(runtime[object_sites[0]].items())),
                "authority": "observation only; 1286 instances and 10 observed PCs are not a universal field domain",
            },
            "typed_state_owner_binding": {
                "function": object_binding["function"],
                "region": object_binding["region"],
                "accepted": object_binding["accepted"],
                "verdict": object_binding["verdict"],
                "pointer_table": object_binding["pointer_table"],
            },
            "shared_abi_cost": {
                "consumed_argument_domains_known": abi_domains,
                "progress_from_this_contract": 0,
            },
            "table_membership_invariant": {
                "proved": False,
                "reason": "no exhaustive actor +0x7C writer/type invariant exists",
            },
            "protected_set_disjointness": {
                **object_disjoint,
                "proved_for_universal_membership_set": False,
            },
            "immunity_to_missing_reaching_definitions": (
                "Observed handlers are not treated as the field domain; acceptance requires "
                "a type invariant and an exhaustive region writer bound."),
            "wall_shape": "technique-shaped",
            "why_shape": (
                "interprocedural object-region typing plus field-sensitive writer closure "
                "could prove the domain, but the retained ABI ledger knows only 1/867 "
                "consumed argument domains"),
            "named_prerequisite": "actor +0x7C field-sensitive typed writer closure",
        },
        "bios_ingress_exception": {
            "contract_established": False,
            "sample_site_count": len(bios_sites),
            "sample_site_ids": bios_sites,
            "byte_fact": word_rows[bios_sites[0]],
            "entry_scoped_candidate": {
                "targets": bios_row["targets"],
                "primary_and_independent_c_agree": True,
                "accepted_as_global_contract": False,
                "scope": bios_row["scope"],
            },
            "runtime": {
                "observed_targets": bios_targets,
                "hit_counts": dict(sorted(runtime[bios_sites[0]].items())),
                "candidate_violation": sorted(set(bios_targets) - set(bios_row["targets"])),
                "authority": "corroboration/falsification only",
            },
            "table_membership_or_named_exception_invariant": {
                "proved": False,
                "named_candidate_exception_set": ["0x000000b0"],
                "reason": (
                    "both C implementations begin at owner entry 0x80060C64; no global "
                    "ingress contract excludes an indirect transfer directly to 0x80060C78"),
            },
            "protected_set_disjointness": {
                **bios_disjoint,
                "proved_for_universal_membership_set": False,
            },
            "immunity_to_missing_reaching_definitions": (
                "The locally dominating immediate is explicitly not promoted across unknown "
                "interior ingress; a global vector/ingress bound is a separate premise."),
            "wall_shape": "technique-shaped",
            "why_shape": (
                "a sound whole-program ingress/vector contract could exclude interior entry "
                "and promote the already-agreed B0 exception, but that contract is absent"),
            "named_prerequisite": "complete indirect-ingress and BIOS/vector exception contract",
        },
        "dynamic_module_boundary": {
            "contract_established": False,
            "sample_site_count": 0,
            "sample_site_ids": [],
            "affected_non_sample_site": DYNAMIC_SITE,
            "why_required_despite_zero_sample_sites": (
                "the work order names the loader boundary as a separate D3-enabling contract; "
                "it is not credited toward the 12-site gate"),
            "independent_byte_probe": frontend,
            "retained_two_c_local_address_proof": {
                "status": guarded[0]["status"],
                "table_extent": guarded[0]["table_extent"],
                "slot_occurrence_count": guarded[0]["slot_occurrence_count"],
                "whole_region_consumer_universe_proved": guarded[0][
                    "whole_region_consumer_universe_proved"],
                "gate_grade_region_closure": guarded[0]["gate_grade_region_closure"],
            },
            "runtime": {
                "observed_targets": dynamic_targets,
                "hit_counts": dict(sorted(runtime[DYNAMIC_SITE].items())),
                "outside_static_code_census": dynamic_outside_static,
                "cabe0_space_observed": True,
                "memory_getResidency_retained_per_hit": retained_residency,
                "transferLog_retained_per_hit": retained_transfer_log,
            },
            "residency_alias_warning": {
                "same_virtual_address_has_pinned_fmv_data_role": True,
                "fmv_records": fmv_cabe0,
                "meaning": (
                    "0x800CABE0 is code-shaped under the frontend observation but data under "
                    "FMV.BIN residency; a raw address cannot identify the loaded module"),
            },
            "loader_membership_invariant": {
                "proved": False,
                "reason": (
                    "the retained corpus lacks per-hit residency and transfer provenance, "
                    "and no loader-byte contract binds the modules that may occupy the range"),
            },
            "protected_set_disjointness": {
                **dynamic_disjoint,
                "proved_for_universal_membership_set": False,
            },
            "immunity_to_missing_reaching_definitions": (
                "Runtime targets and pristine slots are not treated as the loaded-module "
                "universe; module identity and loader writes must be proved independently."),
            "wall_shape": "technique-shaped",
            "why_shape": (
                "a finite loader/module census joined to per-transfer residency semantics "
                "could establish the contract; the current retained tuple schema cannot"),
            "named_prerequisite": "loader byte contract plus retained residency/transfer identity",
        },
    }

    contract_for_site = {
        **{site_id: "shared_dispatch_cell_0x8007fbc4" for site_id in shared_sites},
        object_sites[0]: "object_field_provenance",
        bios_sites[0]: "bios_ingress_exception",
    }
    per_site = []
    merged_runtime = precedent._runtime_tuples(tuples_doc)
    for site_id in sample:
        site = sites[site_id]
        pc = site["pc"].lower()
        contract_name = contract_for_site[site_id]
        per_site.append({
            "site": site_id,
            "contract": contract_name,
            "site_instruction": {
                "pc": site["pc"], "word": site["word"],
                "delay_slot_pc": site["delay_slot_pc"],
                "delay_slot_word": site["delay_slot_word"],
            },
            "independent_word_probe": word_rows[site_id],
            "primary_c_probe": _summarize_primary(primary_rows[pc]),
            "independent_c_probe": _summarize_cross(cross_rows[pc]),
            "part_1_membership_invariant_proved": False,
            "part_2_protected_disjointness_proved_for_membership_set": False,
            "gate_grade_proved": False,
            "outcome": "NAMED_CONTRACT_WALL",
            "wall_shape": contracts[contract_name]["wall_shape"],
            "observed_targets": merged_runtime.get(site_id, []),
            "runtime_authority": "corroboration/falsification only; never proof",
            "hoisted_load_idiom_match": False,
        })
    if len(per_site) != 12 or any(row["gate_grade_proved"] for row in per_site):
        raise ContractError("per-site results do not retain the 0/12 reviewed negative")

    observed_sample = [row for row in per_site if row["observed_targets"]]
    if len(observed_sample) != 2:
        raise ContractError("D3 sample runtime coverage is not 2 observed / 10 silent")
    decision = {
        "verdict": "NO-GO",
        "explicit_sentence": (
            "NO-GO: 0/4 contracts are fully established and 0/12 frozen D3 sites "
            "clear both membership and protected-set disjointness; the GO thresholds "
            "require at least 1/4 and at least 3/12."),
        "fractions": {
            "contracts_fully_established": "0/4",
            "frozen_sites_gate_grade_proved": "0/12",
            "runtime_observed_frozen_sites": "2/12",
            "runtime_silent_frozen_sites": "10/12",
            "protected_set": "128/128 frozen IDs checked",
            "abi_consumed_argument_domains_known": abi_domains["fraction"],
        },
        "go_conditions": {
            "at_least_one_contract": {"required": 1, "actual": 0, "satisfied": False},
            "at_least_three_frozen_sites": {"required": 3, "actual": 0, "satisfied": False},
            "runtime_clean_for_every_proved_site": {
                "proved_site_count": 0,
                "violations": [],
                "satisfied": False,
                "result": "NOT_ESTABLISHED_EMPTY_PROOF_SET",
            },
        },
        "soundness_halt": {
            "triggered": False,
            "meaning": (
                "No accepted proof exists to falsify. Candidate/observed sets have zero "
                "protected intersections, but are not promoted as complete domains."),
        },
        "residual": {
            "before": 179,
            "after": 179,
            "movement": 0,
            "frozen_sample_behind_contract": {
                "shared_dispatch_cell_0x8007fbc4": 10,
                "object_field_provenance": 1,
                "bios_ingress_exception": 1,
                "dynamic_module_boundary": 0,
            },
            "dynamic_boundary_named_non_sample_residual": DYNAMIC_SITE,
        },
        "sixth_attempt_funding": {
            "complete_frontier_retains_a_technical_avenue": True,
            "plain_statement": (
                "A technical avenue remains only through new prerequisite engines: "
                "region-sensitive alias closure, field-sensitive object typing, a global "
                "ingress contract, or a loader/residency contract. Another target-enumeration "
                "campaign using the current machinery is not funded by this result."),
            "per_contract_wall_shapes": {
                name: contract["wall_shape"] for name, contract in contracts.items()},
        },
        "status_movement_authorized": False,
        "full_chain_regeneration_performed": False,
    }

    return {
        "_comment": (
            "Reviewed negative for the frozen 12-site D3 contract pilot. Candidate sets "
            "are retained as evidence, never promoted to universal membership invariants."),
        "schema": SCHEMA,
        "date": "2026-08-10",
        "inputs": {
            "issued_work_order_commit": INPUT_COMMIT,
            "sample_freeze_commit": SAMPLE_FREEZE_COMMIT,
            "work_order_sha256": _sha(work_order_raw),
            "sample_freeze_section_sha256": _sha(freeze_section),
            "assignment_sha256": _sha(assignment_raw),
            "discipline_pilot_sha256": _sha(discipline_raw),
            "protected_freeze_sha256": _sha(freeze_raw),
            "static_index_sha256": _sha(index_raw),
            "runtime_tuple_sha256": _sha(tuples_raw),
            "typed_state_sha256": _sha(typed_raw),
            "abi_ledger_sha256": _sha(abi_raw),
            "function_pointer_fields_sha256": _sha(fields_raw),
            "gap_semantics_sha256": _sha(gaps_raw),
            "address_taken_pilot_sha256": _sha(address_raw),
            "hoisted_load_scan_sha256": _sha(hoisted_raw),
            "fmv_static_owners_sha256": _sha(fmv_raw),
            "working_tree_inputs_equal_pinned_commit": True,
            "pinned_path_hashes": input_hashes,
            "image_manifest_sha256": _sha(image_map),
            "image_identities": identities,
        },
        "c_control": {
            "instruction_decoding_in_python": False,
            "primary_domain_probe": {
                "source": str(PRIMARY_C.relative_to(ROOT)),
                "source_sha256": _sha(PRIMARY_C.read_bytes()),
                "compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
                "binary_sha256": _sha(primary_binary),
                "selftest": primary_self,
                "selftest_stdout_sha256": _sha(primary_self_raw),
                "pilot_stdout_sha256": _sha(primary_stdout),
                "pilot_stderr_sha256": _sha(primary_stderr),
            },
            "independent_domain_probe": {
                "source": str(CROSS_C.relative_to(ROOT)),
                "source_sha256": _sha(CROSS_C.read_bytes()),
                "compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
                "binary_sha256": _sha(cross_binary),
                "selftest": cross_self,
                "selftest_stdout_sha256": _sha(cross_self_raw),
                "pilot_stdout_sha256": _sha(cross_stdout),
                "pilot_stderr_sha256": _sha(cross_stderr),
            },
            "independent_word_probe": {
                "source": str(WORDS_C.relative_to(ROOT)),
                "source_sha256": _sha(WORDS_C.read_bytes()),
                "compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
                "binary_sha256": _sha(words_binary),
                "selftest": words_self,
                "selftest_stdout_sha256": _sha(words_self_raw),
                "pilot_stdout_sha256": _sha(words_stdout),
                "pilot_stderr_sha256": _sha(words_stderr),
            },
            "region_writer_probe": {
                "source": str(REGION_C.relative_to(ROOT)),
                "source_sha256": _sha(REGION_C.read_bytes()),
                "compile_flags": "-std=gnu11 -O2 -Wall -Wextra",
                "binary_sha256": _sha(region_binary),
                "compile_warning_count": region_compile.count(b"warning:"),
                "compile_stderr_sha256": _sha(region_compile),
                "warnings_are_preexisting_and_retained": True,
            },
        },
        "universes": {
            "frozen_indirect_sites": {
                "count": 179,
                "site_ids": assignment["universe"]["site_ids"],
                "exact_both_directions": True,
            },
            "d3_pointer_dispatch": {
                "count": 140,
                "site_ids": d3_universe,
                "not_rederived": True,
            },
            "pilot": {
                "count": 12,
                "site_ids": sample,
                "selection_query": d3_selection["query"],
                "frozen_before_outcomes": True,
                "sample_is_not_universe": True,
            },
            "protected_set": freeze["protected_set"],
        },
        "hoisted_load_control": {
            "retained_universe_count": hoisted["sites"],
            "sample_source_pc_intersection_count": len(hoisted_intersection),
            "sample_source_pc_intersections": hoisted_intersection,
            "clean": True,
        },
        "contracts": contracts,
        "per_site_outcomes": per_site,
        "runtime_crosscheck": {
            "authority": "retained runtime evidence; corroboration/falsification only",
            "proved_site_count": 0,
            "observed_frozen_site_count": len(observed_sample),
            "silent_frozen_site_count": 12 - len(observed_sample),
            "proved_site_violations": [],
            "candidate_protected_intersection_count": 0,
            "dynamic_residency_identity_retained": False,
        },
        "decision": decision,
        "protected_state": {
            "f01_status": "partial",
            "item_2": "not_met",
            "mechanics_baseline_touched": False,
            "forbidden_runtime_artifact_touched": False,
            "instrumented_replay_performed": False,
            "analysis_chain_regenerated": False,
        },
    }


def render() -> bytes:
    return (json.dumps(build(), indent=1, sort_keys=False) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != raw:
            raise SystemExit(f"stale output: {OUTPUT.relative_to(ROOT)}")
        print(f"[phase4-d3-contract] check passed: {_sha(raw)}")
    else:
        OUTPUT.write_bytes(raw)
        print(f"[phase4-d3-contract] wrote {OUTPUT.relative_to(ROOT)}: {_sha(raw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
