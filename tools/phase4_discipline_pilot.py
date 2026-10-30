#!/usr/bin/env python3
"""Run the frozen Phase-4 discipline-proof pilot and bank a reviewed NO-GO.

The pilot selection comes from the committed Stage-0 freeze.  Two independent
compiled-C analyzers own instruction decoding and reaching-definition probes;
the existing compiled region analyzer measures the writer residual for the
shared D3 dispatch cell across all 21 pristine images.  Python owns only input
identity, policy application, exact-set checks, and deterministic rendering.

This driver deliberately stops at NO-GO.  It does not mutate the gate, index,
closure chain, mechanics baseline, or any F01 status surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_discipline_pilot.json"
ASSIGNMENT = ROOT / "analysis/phase4_discipline_assignment.json"
FREEZE = ROOT / "analysis/phase4_target_exclusion_freeze.json"
INDEX = ROOT / "analysis/phase4_static_frontier_index.json"
TUPLES = ROOT / "analysis/phase4_f01_jr_tuple_capture.json"
TYPED_STATE = ROOT / "analysis/phase4_f01_typed_state.json"
GAP_SEMANTICS = ROOT / "analysis/phase4_f01_gap_semantics.json"
FUNCTIONS_RESIDENT = ROOT / "analysis/functions_resident.txt"
WORK_ORDER = ROOT / "engineering-specs/phase4-discipline-proof-work-order.md"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"
PRIMARY_C = ROOT / "tools/phase4_target_exclusion_prover.c"
CROSSCHECK_C = ROOT / "tools/phase4_target_exclusion_crosscheck.c"
REGION_C = ROOT / "tools/region_provenance.c"

SPEC_COMMIT = "e096b7be6f6e5f788700804fbcb0a2184a21571d"
ASSIGNMENT_COMMIT = "02338883b291c529e7380156572b9fa56ec44271"
SHARED_SCOPE_COMMIT = "2954faa2ac8af"
CROSS_ROW_CORRECTION_COMMIT = "c7e6b1398474eaa683e72119a540f961af0a2a25"
WORK_ORDER_COMMIT = "efec6057586b1035bcde6839d252143404177f9b"
SCHEMA = "abl-phase4-discipline-pilot/1"
DISCIPLINES = ("D1_return", "D2_switch_computed", "D3_pointer_dispatch")
SHARED_D3_CELL = 0x8007FBC4


class PilotError(RuntimeError):
    """A pinned identity, proof-policy, or exact-set check failed."""


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
        raise PilotError(
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
        raise PilotError(f"HEAD is not descended from required commit {commit}")


def _compile(source: Path, output: Path, flags: list[str]) -> tuple[bytes, bytes]:
    proc = subprocess.run(
        ["cc", *flags, "-o", str(output), str(source.relative_to(ROOT))],
        cwd=ROOT, capture_output=True, check=False,
    )
    if proc.returncode:
        raise PilotError(
            f"C compile failed ({source.name}): "
            + proc.stderr.decode(errors="replace").strip())
    return output.read_bytes(), proc.stderr


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise PilotError(
            f"command failed ({' '.join(command)}): {proc.stderr.strip()}")
    return proc


def _run_json(command: list[str]) -> tuple[dict, bytes, bytes]:
    proc = _run(command)
    try:
        return json.loads(proc.stdout), proc.stdout.encode(), proc.stderr.encode()
    except json.JSONDecodeError as exc:
        raise PilotError(f"non-JSON C output from {command[0]}") from exc


def _record_extent(row: dict) -> tuple[int, int]:
    if row.get("entry") is not None and row.get("end") is not None:
        return _int(row["entry"]), _int(row["end"])
    extent = row.get("extent")
    if isinstance(extent, list) and len(extent) == 2:
        return _int(extent[0]), _int(extent[1])
    raise PilotError(f"record lacks extent: {row.get('image_id')} {row.get('name')}")


def _image_map(index: dict) -> tuple[bytes, list[dict]]:
    lines: list[str] = []
    identities: list[dict] = []
    images = index.get("images") or []
    if len(images) != 21 or len({row["image_id"] for row in images}) != 21:
        raise PilotError("static image universe is not 21 unique images")
    for row in images:
        path = ROOT / row["path"]
        raw = path.read_bytes()
        if (row.get("identity_verified") is not True
                or len(raw) != int(row["size"])
                or _sha(raw) != row["sha256"]):
            raise PilotError(f"pristine image identity failed: {row['image_id']}")
        lines.append(f"{row['image_id']} {row['path']} {row['file_va_base']}")
        identities.append({
            "image": row["image_id"], "path": row["path"],
            "file_va_base": row["file_va_base"], "size": len(raw),
            "sha256": _sha(raw), "identity_verified": True,
        })
    return ("\n".join(lines) + "\n").encode(), identities


def _query_specs(assignment: dict) -> tuple[list[str], dict[str, dict]]:
    sites = {row["id"]: row for row in assignment["assignments"]["sites"]}
    pilot = assignment["pilot_selection"]["site_ids"]
    if len(pilot) != 39 or len(set(pilot)) != 39:
        raise PilotError("frozen pilot is not 39 unique sites")
    specs = []
    for site_id in pilot:
        row = sites[site_id]
        owner = row["owner"]
        specs.append(":".join((
            owner["image"], owner["entry"], owner["end"],
            row["decoded_register"], row["pc"],
        )))
    return specs, sites


def _runtime_tuples(doc: dict) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for source in (doc["results"]["tuples"], doc["behavior_library_sweep"]["tuples"]):
        for site_id, targets in source.items():
            merged[site_id].update(str(value).lower() for value in targets)
    for site_id, target in doc["hundred_percent_corpus_sweep"][
            "new_targets_at_known_sites"]:
        merged[site_id].add(str(target).lower())
    return {key: sorted(value) for key, value in sorted(merged.items())}


def _functions_for_image(index: dict, image_id: str) -> bytes:
    entries: dict[int, tuple[int, str]] = {}
    for row in index["records"]:
        if row.get("image_id") != image_id or row.get("range_type") not in {"code", "thunk"}:
            continue
        lo, hi = _record_extent(row)
        if hi <= lo:
            raise PilotError(f"empty code extent at {image_id}:0x{lo:08x}")
        name = re.sub(r"[^A-Za-z0-9_.$-]+", "_", row.get("name") or f"anon_{lo:08x}")
        current = entries.get(lo)
        candidate = (hi - lo, name)
        if current is None or candidate < current:
            entries[lo] = candidate
    if not entries:
        raise PilotError(f"no code/thunk entries for {image_id}")
    return "".join(
        f"0x{address:08X} {size} {name}\n"
        for address, (size, name) in sorted(entries.items())
    ).encode()


def _region_writer_scan(binary: Path, index: dict, functions_resident_raw: bytes,
                        temp: Path) -> dict:
    image_rows = {row["image_id"]: row for row in index["images"]}
    per_image = []
    all_writes: list[str] = []
    all_full: list[str] = []
    for image_id in sorted(image_rows):
        image = image_rows[image_id]
        funcs = temp / f"functions-{image_id}.txt"
        funcs.write_bytes(
            functions_resident_raw if image_id == "SCUS_942_88"
            else _functions_for_image(index, image_id))
        output = temp / f"region-{image_id}.json"
        command = [
            str(binary), image["path"], str(funcs), f"0x{SHARED_D3_CELL:08x}", "4",
            "--block", f"0x{SHARED_D3_CELL:08x}", f"0x{SHARED_D3_CELL + 4:08x}",
            "--json", str(output),
        ]
        if image_id != "SCUS_942_88":
            command += ["--raw", image["file_va_base"]]
        proc = _run(command)
        if "WARNING:" in proc.stderr:
            raise PilotError(f"region scan truncated for {image_id}: {proc.stderr}")
        doc = json.loads(output.read_text())
        if doc["unresolved_after_region"] != len(doc["unresolved_all"]):
            raise PilotError(f"region unresolved count mismatch for {image_id}")
        writes = [row for row in doc["unresolved_all"] if row["kind"] == "write"]
        full = [row for row in writes if int(row["width"]) == 4]
        write_ids = [f"{image_id}:{row['pc'].lower()}:{row['width']}" for row in writes]
        full_ids = [f"{image_id}:{row['pc'].lower()}:{row['width']}" for row in full]
        if len(write_ids) != len(set(write_ids)):
            raise PilotError(f"duplicate unresolved writer identity for {image_id}")
        all_writes.extend(write_ids)
        all_full.extend(full_ids)
        per_image.append({
            "image": image_id,
            "function_list_sha256": _sha(funcs.read_bytes()),
            "hit_count": doc["hits"],
            "direct_hit_pcs": doc["hit_pcs"],
            "unresolved_access_count": doc["unresolved_after_region"],
            "unresolved_write_count": len(writes),
            "full_width_unresolved_write_count": len(full),
            "unresolved_writer_identity_sha256": _sha(("\n".join(write_ids) + "\n").encode()),
            "unresolved_writer_first_16": write_ids[:16],
            "full_width_writer_identity_sha256": _sha(("\n".join(full_ids) + "\n").encode()),
            "full_width_writer_first_16": full_ids[:16],
            "indirect_unresolved": doc["indirect_unresolved"],
            "exclusions_total": doc["exclusions_total"],
            "run_stderr_sha256": _sha(
                proc.stderr.replace(str(temp), "$TMP").encode()),
            "truncated": False,
        })
    if len(all_writes) != 4266 or len(all_full) != 2244:
        raise PilotError(
            f"shared-cell writer residual drifted from 4266/2244: "
            f"{len(all_writes)}/{len(all_full)}")
    return {
        "question": "can any unresolved store in the 21-image census write [0x8007fbc4,0x8007fbc8)",
        "target_region": {"start": "0x8007fbc4", "end": "0x8007fbc8", "width": 4},
        "image_count": len(per_image),
        "unresolved_write_count": len(all_writes),
        "full_width_unresolved_write_count": len(all_full),
        "unresolved_writer_identity_sha256": _sha(("\n".join(all_writes) + "\n").encode()),
        "full_width_writer_identity_sha256": _sha(("\n".join(all_full) + "\n").encode()),
        "writer_universe_closed": False,
        "meaning": (
            "4266 unresolved store sites, including 2244 full-width stores, remain possible "
            "writers of the dispatch cell; direct hits are a lower bound, not a census"),
        "per_image": per_image,
    }


def _owner_subsystem(name: str) -> str:
    """Name-based pilot bucket; deliberately approximate, counts exact."""
    if name == "vm_motion_apply_chase":
        return "E07/E08 props, movers, event VM"
    if name == "overlay_flush_cache":
        return "E16 streaming, loaders, overlays"
    if name in {"icache_flush_glue", "icache_flush_glue_68ac", "call_via_ptr_80086aa8"}:
        return "unnamed / other"
    return "E01/E03/E11 render + geometry"


def _summarize_query(row: dict) -> dict:
    return {
        "site_pc": row["site_pc"], "site_word": row["site_word"],
        "delay_slot_pc": row.get("delay_slot_pc"),
        "delay_slot_word": row.get("delay_slot_word"),
        "entry_scoped_verdict": row["verdict"],
        "entry_scoped_targets": row["targets"],
        "scope": row["scope"],
        "breaking_instruction": row["breaking_instruction"],
        "derivations": row["derivations"],
    }


def _summarize_cross(row: dict) -> dict:
    return {
        "site_pc": row["site_pc"], "site_word": row["site_word"],
        "entry_reached": row["entry_reached"],
        "entry_scoped_domain_complete": row["full_target_domain_complete"],
        "entry_scoped_targets": row["targets"],
        "unknown_reasons": row["unknown_reasons"],
        "algorithm": row["algorithm"],
    }


def _outcomes(assignment: dict, freeze: dict, primary: dict, cross: dict,
              runtime: dict[str, list[str]], region: dict) -> tuple[list[dict], list[dict]]:
    pilot = assignment["pilot_selection"]["site_ids"]
    sites = {row["id"]: row for row in assignment["assignments"]["sites"]}
    prior = {row["id"]: row for row in freeze["stage_1_classification"]["sites"]}
    primary_rows = {row["site_pc"].lower(): row for row in primary["queries"]}
    cross_rows = {row["site_pc"].lower(): row for row in cross["queries"]}
    if len(primary_rows) != 39 or len(cross_rows) != 39:
        raise PilotError("C query outputs do not cover 39 distinct pilot PCs")

    d1_runtime_bad = {
        row["site"]: row["observed_targets_not_call_successors"]
        for row in assignment["runtime_crosscheck"]["disagreements"][
            "D1_strict_return_discipline"]
    }
    outcomes = []
    local_candidates = []
    shared_cell_sites = {
        site_id for site_id in assignment["pilot_selection"]["D3"]["table_backed_site_ids"]
    } | set(assignment["pilot_selection"]["D3"]["next_site_ids"][-2:])
    for site_id in pilot:
        site = sites[site_id]
        discipline = site["discipline"]
        pc_key = site["pc"].lower()
        p = primary_rows[pc_key]
        x = cross_rows[pc_key]
        if (p["image"] != site["image"] or p["register"] != site["decoded_register"]
                or p["site_word"].lower() != site["word"].lower()
                or x["image"] != site["image"] or x["register"] != site["decoded_register"]
                or x["site_word"].lower() != site["word"].lower()):
            raise PilotError(f"compiled-C instruction identity mismatch at {site_id}")
        if (bool(p["verdict"]) != bool(x["full_target_domain_complete"])
                or sorted(p["targets"]) != sorted(x["targets"])):
            raise PilotError(f"primary/cross entry-scoped disagreement at {site_id}")
        if p["verdict"]:
            local_candidates.append({
                "site": site_id, "targets": p["targets"],
                "primary_and_independent_crosscheck_agree": True,
                "accepted_as_discipline_proof": False,
            })

        shape: str
        reason: str
        wall: dict
        if discipline == "D1_return":
            if p["verdict"]:
                raise PilotError(f"unexpected D1 entry-scoped proof at {site_id}")
            observable = [row for row in prior[site_id]["reaching_definition_evidence"][
                "definitions"] if row.get("observable") is True]
            if site_id in d1_runtime_bad:
                shape = "structure-shaped"
                reason = "runtime_falsified_call_link_only_return"
                wall = {
                    "register": "ra", "pc": p["breaking_instruction"]["pc"],
                    "word": p["breaking_instruction"]["word"],
                    "static_reason": p["breaking_instruction"]["reason"],
                    "observed_non_call_successor_targets": d1_runtime_bad[site_id],
                    "runtime_role": "falsification only",
                }
            elif observable:
                shape = "structure-shaped"
                reason = "non_call_non_frame_ra_definition"
                witness = observable[0]
                wall = {
                    "register": "ra", "pc": witness["pc"], "word": witness["word"],
                    "definition_class": witness["class"],
                    "provenance_root_or_address": (
                        witness.get("from") or witness.get("address") or witness.get("base")),
                    "strict_D1_violation": (
                        "the reaching ra definition is neither call-link semantics nor a balanced "
                        "stack-frame restore"),
                }
            else:
                shape = "technique-shaped"
                reason = "incoming_ra_or_owner_entry_provenance_not_closed"
                wall = {
                    "register": "ra", "pc": p["breaking_instruction"]["pc"],
                    "word": p["breaking_instruction"]["word"],
                    "static_reason": p["breaking_instruction"]["reason"],
                }
        elif discipline == "D2_switch_computed":
            shape = "structure-shaped"
            observable = [row for row in prior[site_id]["reaching_definition_evidence"][
                "definitions"] if row.get("observable") is True]
            materialized = [row for row in observable
                            if row.get("class") == "materialised_constant"]
            if materialized and len(materialized) == len(observable):
                reason = "materialized_continuation_set_is_not_a_bounds_checked_indexed_table"
                wall = {
                    "register": site["decoded_register"],
                    "pc": materialized[0]["pc"],
                    "word": materialized[0]["word"],
                    "predecessor_candidate_values": sorted({
                        row["value"] for row in materialized}),
                    "gate_failure": "external interior-entry universe remains open",
                }
                if p["verdict"]:
                    wall["entry_scoped_candidate_targets"] = p["targets"]
                else:
                    wall["primary_static_reason"] = p["breaking_instruction"]["reason"]
                if site_id == "SCUS_942_88:0x80018cbc:jr:s6":
                    wall["runtime_falsification"] = {
                        "observed_target": "0x8001961c",
                        "outside_candidate": "0x8001961c" not in p["targets"],
                    }
            elif site_id == "SCUS_942_88:0x80066818:jr:t1":
                reason = "single_cell_thunk_is_not_a_bounds_checked_indexed_table"
                wall = {
                    "register": "t1", "cell": "0x80086aa8",
                    "pc": p["breaking_instruction"]["pc"],
                    "word": p["breaking_instruction"]["word"],
                    "static_reason": p["breaking_instruction"]["reason"],
                }
            else:
                reason = "computed_continuation_has_no_gate_grade_table_locality_proof"
                wall = {
                    "register": site["decoded_register"],
                    "pc": p["breaking_instruction"]["pc"],
                    "word": p["breaking_instruction"]["word"],
                    "static_reason": p["breaking_instruction"]["reason"],
                }
        else:
            shape = "technique-shaped"
            if site_id in shared_cell_sites:
                reason = "dispatch_cell_writer_universe_open"
                wall = {
                    "register": site["decoded_register"], "cell": "0x8007fbc4",
                    "pc": p["breaking_instruction"]["pc"],
                    "word": p["breaking_instruction"]["word"],
                    "unresolved_writers": region["unresolved_write_count"],
                    "full_width_unresolved_writers": region[
                        "full_width_unresolved_write_count"],
                    "writer_universe_closed": False,
                }
            elif site_id == "SCUS_942_88:0x8004d1e8:jalr:v0":
                reason = "object_field_membership_and_writer_invariant_open"
                wall = {
                    "register": "v0", "object_field_offset": "0x7c",
                    "pc": p["breaking_instruction"]["pc"],
                    "word": p["breaking_instruction"]["word"],
                    "independent_reason": x["unknown_reasons"],
                }
            elif site_id == "SCUS_942_88:0x80060c78:jalr:t2":
                reason = "entry_scoped_bios_constant_lacks_ingress_and_named_exception_contract"
                wall = {
                    "register": "t2", "pc": p["derivations"][0]["definition_pc"],
                    "word": p["derivations"][0]["definition_word"],
                    "entry_scoped_candidate_targets": p["targets"],
                    "named_candidate": "PS1 BIOS B0 vector",
                    "gate_failure": (
                        "both C implementations start at the declared owner entry and therefore "
                        "do not exclude an external transfer directly to or after the definition"),
                }
            else:
                raise PilotError(f"unclassified D3 pilot site {site_id}")

        outcomes.append({
            "site": site_id, "discipline": discipline,
            "owner_subsystem": _owner_subsystem(site["owner"]["name"]),
            "owner": site["owner"],
            "outcome": "NAMED_WALL", "gate_grade_proved": False,
            "proof_kind": None, "wall_shape": shape,
            "wall_reason": reason, "wall": wall,
            "site_instruction": {
                "pc": site["pc"], "word": site["word"],
                "delay_slot_pc": site["delay_slot_pc"],
                "delay_slot_word": site["delay_slot_word"],
            },
            "primary_c_probe": _summarize_query(p),
            "independent_c_probe": _summarize_cross(x),
            "observed_targets": runtime.get(site_id, []),
            "runtime_authority": "corroboration/falsification only; never proof",
        })
    return outcomes, local_candidates


def build() -> dict:
    for commit in (SPEC_COMMIT, ASSIGNMENT_COMMIT, SHARED_SCOPE_COMMIT,
                   CROSS_ROW_CORRECTION_COMMIT, WORK_ORDER_COMMIT):
        _require_ancestor(commit)

    assignment, assignment_raw = _git_json(ASSIGNMENT_COMMIT, ASSIGNMENT)
    freeze, freeze_raw = _git_json(SPEC_COMMIT, FREEZE)
    index, index_raw = _git_json(SPEC_COMMIT, INDEX)
    tuples_doc, tuples_raw = _git_json(SPEC_COMMIT, TUPLES)
    typed_state, typed_state_raw = _git_json(SPEC_COMMIT, TYPED_STATE)
    gap_semantics, gap_raw = _git_json(SPEC_COMMIT, GAP_SEMANTICS)
    functions_resident_raw = _git_show(SPEC_COMMIT, FUNCTIONS_RESIDENT)
    work_order_raw = _git_show(WORK_ORDER_COMMIT, WORK_ORDER)
    if WORK_ORDER.read_bytes() != work_order_raw:
        raise PilotError("working-tree work order differs from the pinned corrected order")
    if assignment.get("schema") != "abl-phase4-discipline-assignment/1":
        raise PilotError("unexpected Stage-0 assignment schema")
    if freeze.get("schema") != "abl-phase4-target-exclusion-freeze/1":
        raise PilotError("unexpected frozen-universe schema")
    if assignment["inputs"]["derived_input_snapshot_commit"] != SPEC_COMMIT:
        raise PilotError("Stage-0 derived-input pin drifted")
    if assignment["pilot_selection"]["frozen_before_outcomes"] is not True:
        raise PilotError("pilot was not frozen before outcomes")
    if set(assignment["outcome_barrier"].values()) != {False}:
        raise PilotError("Stage-0 freeze contains an outcome")
    if len(freeze["protected_set"]["combined_ids"]) != 128:
        raise PilotError("protected set is not 128 unique image/PC members")
    writer_attestations = [
        row["attestation"]["table_writer_universe"]
        for row in typed_state["bindings"]
        if (row.get("attestation") or {}).get("table_writer_universe")
    ]
    if (not writer_attestations
            or {row["corpus_undecided_stores"] for row in writer_attestations} != {5012}):
        raise PilotError("pinned general corpus undecided-store count is not 5012")
    direct_cell_accesses = [
        row for row in gap_semantics["library_workarea_partition"]["probe"]["sites"]
        if str(row.get("target", "")).lower() == "0x8007fbc4"
    ]
    if not any(row["kind"] == "store" and row["pc"].lower() == "0x80060fe8"
               for row in direct_cell_accesses):
        raise PilotError("pinned gap semantics lacks SetDumpFnt direct cell writer")

    image_map, identities = _image_map(index)
    query_specs, sites = _query_specs(assignment)
    with tempfile.TemporaryDirectory(prefix="phase4-discipline-pilot-") as tmp_text:
        temp = Path(tmp_text)
        image_map_path = temp / "images.txt"
        image_map_path.write_bytes(image_map)

        primary_bin = temp / "primary"
        cross_bin = temp / "cross"
        region_bin = temp / "region"
        primary_raw, primary_compile_stderr = _compile(
            PRIMARY_C, primary_bin,
            ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror"])
        cross_raw, cross_compile_stderr = _compile(
            CROSSCHECK_C, cross_bin,
            ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror"])
        region_raw, region_compile_stderr = _compile(
            REGION_C, region_bin, ["-std=gnu11", "-O2", "-Wall", "-Wextra"])
        if primary_compile_stderr or cross_compile_stderr:
            raise PilotError("Werror analyzers emitted compile diagnostics")

        primary_self, primary_self_raw, _ = _run_json([str(primary_bin), "--self-test"])
        cross_self, cross_self_raw, _ = _run_json([str(cross_bin), "--self-test"])
        if primary_self != {"tool": "phase4_target_exclusion_prover", "passed": 9,
                            "total": 9, "verdict": True}:
            raise PilotError("primary C self-test drifted")
        if cross_self != {"tool": "phase4_target_exclusion_crosscheck", "passed": 8,
                          "total": 8, "verdict": True}:
            raise PilotError("independent C self-test drifted")
        primary, primary_stdout, primary_stderr = _run_json(
            [str(primary_bin), str(image_map_path), *query_specs])
        cross, cross_stdout, cross_stderr = _run_json(
            [str(cross_bin), str(image_map_path), *query_specs])
        if primary.get("query_count") != 39 or cross.get("query_count") != 39:
            raise PilotError("compiled analyzers did not process all 39 sites")
        region = _region_writer_scan(region_bin, index, functions_resident_raw, temp)

    runtime = _runtime_tuples(tuples_doc)
    outcomes, local_candidates = _outcomes(
        assignment, freeze, primary, cross, runtime, region)
    if len(outcomes) != 39 or {row["site"] for row in outcomes} != set(
            assignment["pilot_selection"]["site_ids"]):
        raise PilotError("per-site outcomes do not tile the frozen pilot")
    proved = [row for row in outcomes if row["gate_grade_proved"]]
    if proved:
        raise PilotError("pilot policy unexpectedly accepted a gate-grade proof")
    if len(local_candidates) != 5:
        raise PilotError("entry-scoped candidate fact count drifted from five")

    candidate_violations = []
    for candidate in local_candidates:
        outside = sorted(set(runtime.get(candidate["site"], [])) - set(candidate["targets"]))
        if outside:
            candidate_violations.append({
                "site": candidate["site"], "candidate_targets": candidate["targets"],
                "observed_targets_outside_candidate": outside,
                "finding": "runtime falsifies promotion of the entry-scoped C result",
            })
    if candidate_violations != [{
            "site": "SCUS_942_88:0x80018cbc:jr:s6",
            "candidate_targets": ["0x80018cc4", "0x80018f4c", "0x80019244"],
            "observed_targets_outside_candidate": ["0x8001961c"],
            "finding": "runtime falsifies promotion of the entry-scoped C result"}]:
        raise PilotError(f"candidate runtime violations drifted: {candidate_violations}")

    counts = {
        discipline: {
            "sampled": sum(row["discipline"] == discipline for row in outcomes),
            "proved": sum(row["discipline"] == discipline and row["gate_grade_proved"]
                          for row in outcomes),
            "named_walls": sum(row["discipline"] == discipline
                               and row["outcome"] == "NAMED_WALL" for row in outcomes),
        }
        for discipline in DISCIPLINES
    }
    if counts != {
            "D1_return": {"sampled": 19, "proved": 0, "named_walls": 19},
            "D2_switch_computed": {"sampled": 8, "proved": 0, "named_walls": 8},
            "D3_pointer_dispatch": {"sampled": 12, "proved": 0, "named_walls": 12}}:
        raise PilotError(f"pilot outcome counts drifted: {counts}")

    shape_tallies: dict[str, Counter] = defaultdict(Counter)
    reason_tallies: dict[str, Counter] = defaultdict(Counter)
    subsystem: dict[str, dict[str, Counter]] = defaultdict(
        lambda: defaultdict(Counter))
    for row in outcomes:
        shape_tallies[row["discipline"]][row["wall_shape"]] += 1
        reason_tallies[row["discipline"]][row["wall_reason"]] += 1
        subsystem[row["owner_subsystem"]][row["discipline"]]["sampled"] += 1
        subsystem[row["owner_subsystem"]][row["discipline"]]["proved"] += int(
            row["gate_grade_proved"])
    subsystem_rows = []
    for name in sorted(subsystem):
        by_discipline = {
            discipline: {
                "sampled": subsystem[name][discipline]["sampled"],
                "proved": subsystem[name][discipline]["proved"],
            }
            for discipline in DISCIPLINES
        }
        subsystem_rows.append({
            "subsystem": name,
            "mapping_authority": "name-based approximate bucket; counts exact",
            "sampled": sum(row["sampled"] for row in by_discipline.values()),
            "proved": sum(row["proved"] for row in by_discipline.values()),
            "by_discipline": by_discipline,
        })
    if {row["subsystem"]: row["sampled"] for row in subsystem_rows} != {
            "E01/E03/E11 render + geometry": 34,
            "E07/E08 props, movers, event VM": 1,
            "E16 streaming, loaders, overlays": 1,
            "unnamed / other": 3}:
        raise PilotError("pilot owner-subsystem counts drifted")

    d1_required = math.ceil(0.60 * 19)
    decision = {
        "verdict": "NO-GO",
        "explicit_sentence": (
            "NO-GO: D1 landed 0/19 (requires at least 12) and D3 landed 0/12 "
            "(requires at least one gate-grade membership invariant); no nonempty "
            "proved-site runtime cross-check exists."),
        "conditions": {
            "D1_at_least_60_percent": {
                "required": d1_required, "actual": counts["D1_return"]["proved"],
                "satisfied": False},
            "D3_at_least_one_membership_invariant": {
                "required": 1, "actual": counts["D3_pointer_dispatch"]["proved"],
                "satisfied": False},
            "runtime_crosscheck_clean_for_nonempty_proved_set": {
                "proved_site_count": 0, "satisfied": False,
                "result": "NOT_ESTABLISHED_EMPTY_PROOF_SET"},
        },
        "candidate_soundness_halt": {
            "triggered": True, "accepted_proof_affected": False,
            "violations": candidate_violations,
            "meaning": (
                "the 0x80018cbc entry-scoped candidate must not be promoted; it was "
                "rejected before the accepted proof set was formed"),
        },
        "full_pass_authorized": False,
        "stage_2_consumption_performed": False,
    }

    return {
        "_comment": (
            "Reviewed negative for the frozen 39-site discipline pilot. Per-site outcomes "
            "precede the decision in the experiment log; no gate or status surface moved."),
        "schema": SCHEMA,
        "inputs": {
            "issued_work_order_commit": SPEC_COMMIT,
            "stage0_assignment_commit": ASSIGNMENT_COMMIT,
            "shared_scope_commit": SHARED_SCOPE_COMMIT,
            "cross_row_correction_commit": CROSS_ROW_CORRECTION_COMMIT,
            "corrected_work_order_commit": WORK_ORDER_COMMIT,
            "work_order_sha256": _sha(work_order_raw),
            "assignment_sha256": _sha(assignment_raw),
            "frozen_universe_sha256": _sha(freeze_raw),
            "static_index_sha256": _sha(index_raw),
            "runtime_tuple_artifact_sha256": _sha(tuples_raw),
            "typed_state_sha256": _sha(typed_state_raw),
            "gap_semantics_sha256": _sha(gap_raw),
            "resident_function_list_sha256": _sha(functions_resident_raw),
            "image_manifest_sha256": _sha(image_map),
            "image_identities": identities,
        },
        "c_control": {
            "instruction_decoding_in_python": False,
            "primary": {
                "source": str(PRIMARY_C.relative_to(ROOT)),
                "source_sha256": _sha(PRIMARY_C.read_bytes()),
                "compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
                "binary_sha256": _sha(primary_raw),
                "selftest": primary_self,
                "selftest_stdout_sha256": _sha(primary_self_raw),
                "pilot_stdout_sha256": _sha(primary_stdout),
                "pilot_stderr_sha256": _sha(primary_stderr),
            },
            "independent": {
                "source": str(CROSSCHECK_C.relative_to(ROOT)),
                "source_sha256": _sha(CROSSCHECK_C.read_bytes()),
                "compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
                "binary_sha256": _sha(cross_raw),
                "selftest": cross_self,
                "selftest_stdout_sha256": _sha(cross_self_raw),
                "pilot_stdout_sha256": _sha(cross_stdout),
                "pilot_stderr_sha256": _sha(cross_stderr),
            },
            "region_writer_probe": {
                "source": str(REGION_C.relative_to(ROOT)),
                "source_sha256": _sha(REGION_C.read_bytes()),
                "compile_flags": "-std=gnu11 -O2 -Wall -Wextra",
                "binary_sha256": _sha(region_raw),
                "compile_warning_count": region_compile_stderr.count(b"warning:"),
                "compile_stderr_sha256": _sha(region_compile_stderr),
                "warnings_are_preexisting_and_retained": True,
            },
        },
        "universes": {
            "frozen_indirect_site_universe": {
                "count": 179,
                "site_ids": assignment["universe"]["site_ids"],
                "assignment_exact_both_directions": True,
            },
            "pilot": {
                "count": 39, "site_ids": assignment["pilot_selection"]["site_ids"],
                "sample_is_not_universe": True,
                "frozen_before_outcomes": True,
            },
            "protected_set": freeze["protected_set"],
        },
        "per_site_outcomes": outcomes,
        "counts": counts,
        "wall_tallies": {
            discipline: {
                "by_shape": dict(sorted(shape_tallies[discipline].items())),
                "by_reason": dict(sorted(reason_tallies[discipline].items())),
            }
            for discipline in DISCIPLINES
        },
        "discipline_wall_assessment": {
            "D1_return": (
                "structure-shaped as a route to the threshold: 17/19 sampled owners have "
                "a non-frame ra source or an observed non-call-successor target; the other "
                "two retain technique-shaped entry-provenance walls"),
            "D2_switch_computed": (
                "structure-shaped: all eight sampled sites are materialized continuation "
                "jumps or a single-cell thunk, not bounds-checked indexed tables"),
            "D3_pointer_dispatch": (
                "technique/contract-shaped: stronger alias and typed-state writer closure, "
                "object-field typing, or an ingress/BIOS exception contract could clear them"),
        },
        "entry_scoped_candidate_facts_not_proofs": local_candidates,
        "runtime_crosscheck": {
            "authority": "retained runtime evidence; corroboration/falsification only",
            "landed_proof_site_count": 0,
            "landed_proof_result": "NOT_ESTABLISHED_EMPTY_PROOF_SET",
            "candidate_violations": candidate_violations,
            "level07_residency_contaminated_site": {
                "site": "LEVEL07_LEVEL1:0x800b3fcc:jr:v0",
                "used": False,
                "reason": "overlay tuples are residency-contaminated",
            },
            "live_or_instrumented_replay_performed": False,
        },
        "D3_shared_cell_writer_probe": region,
        "corpus_undecided_stores": {
            "general_F01_typed_state_table_0x80090748": 5012,
            "D3_shared_dispatch_cell_0x8007fbc4": 4266,
            "D3_shared_dispatch_cell_full_width": 2244,
            "counts_are_for_distinct_questions": True,
        },
        "known_direct_D3_cell_fact": {
            "cell": "0x8007fbc4",
            "direct_writer": {"pc": "0x80060fe8", "owner": "SetDumpFnt"},
            "authority": "lower-bound facts only; 4266 unresolved stores forbid census status",
        },
        "independent_crosscheck": {
            "landed_proof_count": 0,
            "obligation_status": "NOT_APPLICABLE_EMPTY_LANDED_SET",
            "called_clean": False,
            "entry_scoped_candidate_count_rederived": len(local_candidates),
            "candidate_results_do_not_promote_gate_grade": True,
        },
        "owner_subsystem_progress": {
            "universe_buckets_from_corrected_work_order": {
                "unnamed / other": 62, "E14 frontend, save, pad": 48,
                "E01/E03/E11 render + geometry": 38,
                "E16 streaming, loaders, overlays": 17, "E12 audio": 7,
                "E02/E06 collision + contact": 4,
                "E07/E08 props, movers, event VM": 3,
            },
            "transfer_caveat": (
                "ownership is shared; direct benefit is verified only for the corrected "
                "frontier-shaped rows, and reachability for other rows remains a hypothesis"),
            "pilot": subsystem_rows,
        },
        "decision": decision,
        "residual": {
            "before": 179, "after": 179, "proved_site_delta": 0,
            "scale_changed": False,
            "operator_item2_bar_effect": (
                "none: the result does not reduce the 179-site indirect-control-flow residual"),
        },
        "protected_state": {
            "f01_status": "partial", "item_2": "not_met",
            "item2_ready_for_review": False,
            "review_blockers": ["IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"],
            "gate_or_closure_mutated": False, "full_chain_regenerated": False,
            "runtime_replay_performed": False, "instrumented_run_performed": False,
        },
    }


def _render(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    raw = _render(build())
    if args.check:
        if not output.is_file() or output.read_bytes() != raw:
            print(f"discipline pilot differs: {output}")
            return 1
        print(f"discipline pilot current: {output}")
        return 0
    output.write_bytes(raw)
    print(f"wrote {output} ({len(raw)} bytes, sha256={_sha(raw)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
