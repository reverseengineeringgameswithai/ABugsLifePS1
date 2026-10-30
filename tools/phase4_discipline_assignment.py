#!/usr/bin/env python3
"""Freeze the 179-site Phase-4 discipline assignment and pilot sample.

Instruction decoding belongs exclusively to the compiled C probe.  This
driver pins repository inputs, verifies pristine image identity, performs
exact-set arithmetic, checks the retained runtime corpus for contradictions,
and emits deterministic JSON with a byte-for-byte ``--check`` mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_discipline_assignment.json"
C_SOURCE = ROOT / "tools/phase4_discipline_assignment.c"
FREEZE = ROOT / "analysis/phase4_target_exclusion_freeze.json"
INDEX = ROOT / "analysis/phase4_static_frontier_index.json"
JR_TABLES = ROOT / "analysis/phase3_jr_tables.json"
JALR_CALLBACKS = ROOT / "analysis/phase3_jalr_callbacks.json"
TUPLES = ROOT / "analysis/phase4_f01_jr_tuple_capture.json"
WORK_ORDER = ROOT / "engineering-specs/phase4-discipline-proof-work-order.md"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"

SPEC_COMMIT = "e096b7be6f6e5f788700804fbcb0a2184a21571d"
FREEZE_COMMIT = "02338883b291c529e7380156572b9fa56ec44271"
SCHEMA = "abl-phase4-discipline-assignment/1"
MARKER = "discipline-proof pilot frozen (PRE-OUTCOME record)"
DISCIPLINES = ("D1_return", "D2_switch_computed", "D3_pointer_dispatch")


class AssignmentError(RuntimeError):
    """A pinned identity, exact-set, or fail-closed assignment check failed."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    return int(str(value), 0)


def _site_sort(site_id: str) -> tuple[int, str, str]:
    image, pc, kind, register = site_id.split(":")
    return int(pc, 16), image, f"{kind}:{register}"


def _git_show(commit: str, path: Path) -> bytes:
    rel = str(path.relative_to(ROOT))
    proc = subprocess.run(
        ["git", "show", f"{commit}:{rel}"], cwd=ROOT,
        capture_output=True, check=False,
    )
    if proc.returncode:
        raise AssignmentError(
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
        raise AssignmentError(f"C compile failed: {proc.stderr.strip()}")
    return output.read_bytes()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise AssignmentError(
            f"command failed ({' '.join(command)}): {proc.stderr.strip()}")
    return proc


def _image_manifest(index: dict) -> tuple[bytes, list[dict]]:
    lines, identities = [], []
    images = index.get("images") or []
    if len(images) != 21 or len({row.get("image_id") for row in images}) != 21:
        raise AssignmentError("static index does not pin 21 unique images")
    for row in images:
        path = ROOT / row["path"]
        raw = path.read_bytes()
        if (row.get("identity_verified") is not True
                or len(raw) != int(row["size"])
                or _sha(raw) != row["sha256"]):
            raise AssignmentError(f"pristine image identity failed: {row['image_id']}")
        lines.append(f"{row['image_id']} {row['path']} {row['file_va_base']}")
        identities.append({
            "image": row["image_id"], "path": row["path"],
            "file_va_base": row["file_va_base"], "size": len(raw),
            "sha256": _sha(raw), "identity_verified": True,
        })
    return ("\n".join(lines) + "\n").encode(), identities


def _freeze_section(expected: list[str], text: str) -> bytes:
    if MARKER not in text:
        raise AssignmentError(f"experiment log lacks {MARKER!r}")
    section = text.split(MARKER, 1)[1].split("\n## ", 1)[0]
    listed = re.findall(r"\|\s*(?:\d+|table \d+|next \d+)\s*\|\s*`([^`]+)`\s*\|", section)
    if listed != expected:
        raise AssignmentError("experiment pilot list differs from mechanical selection")
    required = (
        "No D1 return-discipline outcome", "D2 locality outcome",
        "D3 membership/writer", "GO/NO-GO",
    )
    if any(phrase not in section for phrase in required):
        raise AssignmentError("experiment freeze fails to exclude outcomes explicitly")
    return (MARKER + section.rstrip() + "\n").encode()


def _extent(row: dict) -> tuple[int, int]:
    if row.get("entry") is not None and row.get("end") is not None:
        return _int(row["entry"]), _int(row["end"])
    extent = row.get("extent")
    if isinstance(extent, list) and len(extent) == 2:
        return _int(extent[0]), _int(extent[1])
    raise AssignmentError("static-index code record lacks an extent")


def _runtime_tuples(doc: dict) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for source in (doc["results"]["tuples"], doc["behavior_library_sweep"]["tuples"]):
        for site_id, targets in source.items():
            merged[site_id].update(str(value).lower() for value in targets)
    for site_id, target in doc["hundred_percent_corpus_sweep"][
            "new_targets_at_known_sites"]:
        merged[site_id].add(str(target).lower())
    return {key: sorted(value) for key, value in sorted(merged.items())}


def _runtime_crosscheck(freeze: dict, index: dict, callbacks: dict,
                        tuples_doc: dict, assignment: dict[str, str]) -> dict:
    tuples = _runtime_tuples(tuples_doc)
    universe = set(assignment)
    silent = set(tuples_doc["hundred_percent_corpus_sweep"]["final_silent_site_ids"])
    if len(tuples) != 79 or len(silent) != 100 or set(tuples) | silent != universe:
        raise AssignmentError("retained runtime observed/silent sets do not tile 179 sites")

    # Direct-call facts are already instruction-decoded in the pinned static
    # index.  The callback census and current C-decoded D3 set supply jalr link
    # successors.  Set arithmetic here does not decode an instruction.
    call_successors: set[int] = set()
    for record in index["records"]:
        for edge in record.get("direct_calls") or []:
            call_successors.add(_int(edge["pc"]) + 8)
    for pc in callbacks.get("sites") or {}:
        call_successors.add(int(pc, 16) + 8)
    for site_id, discipline in assignment.items():
        if discipline == "D3_pointer_dispatch":
            call_successors.add(int(site_id.split(":")[1], 16) + 8)

    d1_bad = []
    for site_id, discipline in assignment.items():
        if discipline != "D1_return":
            continue
        bad = [target for target in tuples.get(site_id, [])
               if int(target, 16) not in call_successors]
        if bad:
            d1_bad.append({
                "site": site_id, "observed_targets_not_call_successors": bad,
                "finding": "observed behavior contradicts strict D1 call-link-only return discipline",
            })

    code_ranges = []
    for record in index["records"]:
        if record.get("range_type") in {"code", "thunk"}:
            lo, hi = _extent(record)
            code_ranges.append((record["image_id"], lo, hi))
    d2_external = []
    contaminated = "LEVEL07_LEVEL1:0x800b3fcc:jr:v0"
    for site_id, discipline in assignment.items():
        if discipline != "D2_switch_computed" or site_id == contaminated:
            continue
        outside = [target for target in tuples.get(site_id, [])
                   if not any(lo <= int(target, 16) < hi
                              for _image, lo, hi in code_ranges)]
        if outside:
            d2_external.append({
                "site": site_id, "observed_targets_outside_static_code_census": outside,
                "finding": "standard static switch locality cannot cover this site without a named loader/BIOS contract",
            })

    by_discipline = {}
    for name in DISCIPLINES:
        ids = {site_id for site_id, value in assignment.items() if value == name}
        observed = sorted(ids & set(tuples), key=_site_sort)
        by_discipline[name] = {
            "universe": len(ids), "observed": len(observed),
            "silent": len(ids - set(observed)), "observed_site_ids": observed,
        }
    if [(by_discipline[name]["observed"], by_discipline[name]["silent"])
            for name in DISCIPLINES] != [(15, 4), (15, 5), (49, 91)]:
        raise AssignmentError("runtime discipline coverage differs from 15/4, 15/5, 49/91")

    return {
        "authority": "runtime evidence only; assignment falsification/corroboration, never proof",
        "retained_tuple_artifact": str(TUPLES.relative_to(ROOT)),
        "observed_site_count": len(tuples), "silent_site_count": len(silent),
        "coverage": by_discipline,
        "disagreements": {
            "D1_strict_return_discipline": d1_bad,
            "D2_static_switch_locality": d2_external,
            "prior_entry_scoped_domain_falsification":
                tuples_doc["behavior_library_sweep"]["domain_violations"],
            "D3_encoding_assignment": [],
        },
        "overlay_caveat": {
            "site": contaminated, "trusted_for_assignment_crosscheck": False,
            "reason": tuples_doc["data_caveats"]["overlay_residency_contamination"],
        },
        "dynamic_loader_contract_residual": {
            "site": "MEMORY:0x800b970c:jr:v0",
            "targets": ["0x800cabe0", "0x800cabe4"],
            "status": "NAMED_NOT_PROVED",
        },
    }


def build() -> dict:
    freeze, freeze_raw = _git_json(SPEC_COMMIT, FREEZE)
    index, index_raw = _git_json(SPEC_COMMIT, INDEX)
    jr_tables, jr_tables_raw = _git_json(SPEC_COMMIT, JR_TABLES)
    callbacks, callbacks_raw = _git_json(SPEC_COMMIT, JALR_CALLBACKS)
    tuples_doc, tuples_raw = _git_json(SPEC_COMMIT, TUPLES)
    work_raw = _git_show(SPEC_COMMIT, WORK_ORDER)

    if freeze.get("schema") != "abl-phase4-target-exclusion-freeze/1":
        raise AssignmentError("wrong frozen-universe schema")
    universe = list(freeze["pilot_selection"]["candidate_union_ids"])
    if len(universe) != 179 or len(set(universe)) != 179:
        raise AssignmentError("frozen candidate_union_ids is not 179 unique sites")
    prior_rows = {row["id"]: row for row in freeze["stage_1_classification"]["sites"]}
    if set(prior_rows) != set(universe):
        raise AssignmentError("predecessor classification does not tile frozen universe")

    manifest, identities = _image_manifest(index)
    with tempfile.TemporaryDirectory(prefix="phase4-discipline-assignment-") as tmp_text:
        tmp = Path(tmp_text)
        manifest_path = tmp / "images.txt"
        manifest_path.write_bytes(manifest)
        binary_path = tmp / "assignment"
        binary_raw = _compile(C_SOURCE, binary_path)
        selftest_proc = _run([str(binary_path), "--self-test"])
        selftest = json.loads(selftest_proc.stdout)
        if selftest != {"tool": "phase4_discipline_assignment", "passed": 4,
                        "total": 4, "verdict": True}:
            raise AssignmentError(f"C self-test drifted: {selftest!r}")
        decoded = json.loads(_run(
            [str(binary_path), str(manifest_path), *universe]).stdout)

    rows = decoded.get("sites") or []
    if decoded.get("site_count") != 179 or len(rows) != 179:
        raise AssignmentError("compiled C did not decode all 179 sites")
    if [row["id"] for row in rows] != universe:
        raise AssignmentError("compiled C changed frozen universe ordering")
    assignment = {row["id"]: row["discipline"] for row in rows}
    by_discipline = {
        name: sorted((site_id for site_id, value in assignment.items() if value == name),
                     key=_site_sort)
        for name in DISCIPLINES
    }
    counts = {name: len(ids) for name, ids in by_discipline.items()}
    if counts != {"D1_return": 19, "D2_switch_computed": 20,
                  "D3_pointer_dispatch": 140}:
        raise AssignmentError(f"discipline counts differ from 19/20/140: {counts}")

    enriched = []
    for row in rows:
        prior = prior_rows[row["id"]]
        if (row["decoded_kind"] != prior["kind"]
                or row["decoded_register"] != prior["register"]
                or row["word"] != prior["instruction_evidence"]["word"]):
            raise AssignmentError(f"instruction evidence disagrees at {row['id']}")
        enriched.append(row | {"owner": prior["owner"]})

    owners: dict[tuple[str, str], dict] = {}
    owner_sites: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in enriched:
        owner = row["owner"]
        key = (owner["image"], owner["entry"])
        owners[key] = owner
        owner_sites[key].append(row["id"])
    if len(owners) != 110:
        raise AssignmentError(f"owner function universe is not 110: {len(owners)}")
    owner_rows = [owners[key] | {"site_ids": sorted(owner_sites[key], key=_site_sort)}
                  for key in sorted(owners)]

    decoded_table_addresses = {
        str(value["table"]).lower() for value in jr_tables["decoded"].values()
    }
    direct_d3_table_matches = sorted(
        (site_id for site_id in by_discipline["D3_pointer_dispatch"]
         if str(prior_rows[site_id]["reaching_definition_evidence"].get(
             "loaded_from") or "").lower() in decoded_table_addresses),
        key=_site_sort,
    )
    if direct_d3_table_matches:
        raise AssignmentError("D3 load cells unexpectedly match phase3 jr table extents")
    table_candidates = sorted(
        (site_id for site_id in by_discipline["D3_pointer_dispatch"]
         if prior_rows[site_id]["stratum"] == "table_backed"), key=_site_sort)
    d3_table = table_candidates[:8]
    d3_next = sorted(
        (site_id for site_id in by_discipline["D3_pointer_dispatch"]
         if site_id not in set(d3_table)), key=_site_sort)[:4]
    pilot = by_discipline["D1_return"] + by_discipline["D2_switch_computed"][:8] + d3_table + d3_next
    if len(pilot) != 39 or len(set(pilot)) != 39:
        raise AssignmentError("mechanical pilot is not 39 unique sites")
    experiment_raw = _freeze_section(
        pilot, _git_show(FREEZE_COMMIT, EXPERIMENT).decode("utf-8"))
    runtime = _runtime_crosscheck(freeze, index, callbacks, tuples_doc, assignment)

    return {
        "_comment": ("Stage-0 discipline assignment and pre-outcome pilot freeze. "
                     "This artifact contains no discipline proof or GO/NO-GO decision."),
        "schema": SCHEMA,
        "inputs": {
            "work_order_commit": SPEC_COMMIT,
            "derived_input_snapshot_commit": SPEC_COMMIT,
            "work_order": str(WORK_ORDER.relative_to(ROOT)),
            "work_order_sha256": _sha(work_raw),
            "frozen_universe": str(FREEZE.relative_to(ROOT)),
            "frozen_universe_sha256": _sha(freeze_raw),
            "static_index_sha256": _sha(index_raw),
            "phase3_jr_tables_sha256": _sha(jr_tables_raw),
            "phase3_jalr_callbacks_sha256": _sha(callbacks_raw),
            "runtime_tuple_artifact_sha256": _sha(tuples_raw),
            "experiment_pre_outcome_section_sha256": _sha(experiment_raw),
            "image_manifest_sha256": _sha(manifest),
            "image_identities": identities,
        },
        "c_control": {
            "source": str(C_SOURCE.relative_to(ROOT)),
            "source_sha256": _sha(C_SOURCE.read_bytes()),
            "compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
            "binary_sha256": _sha(binary_raw),
            "selftest": selftest | {
                "stdout_sha256": _sha(selftest_proc.stdout.encode())},
            "instruction_decoding_in_python": False,
        },
        "universe": {
            "name": "phase4_target_exclusion_freeze.pilot_selection.candidate_union_ids",
            "count": 179, "site_ids": universe,
            "exact_both_directions": True,
            "assignment_count": len(assignment),
            "unassigned_residual_count": 0,
            "unassigned_residual_site_ids": [],
        },
        "assignments": {
            "counts": counts,
            "by_discipline": by_discipline,
            "sites": enriched,
        },
        "owner_functions": {"count": len(owner_rows), "owners": owner_rows},
        "pilot_selection": {
            "frozen_before_outcomes": True,
            "total_count": len(pilot), "site_ids": pilot,
            "D1": {"query": "all D1, ascending pc then image/id",
                   "count": 19, "site_ids": by_discipline["D1_return"]},
            "D2": {"query": "first 8 D2, ascending pc then image/id",
                   "count": 8, "site_ids": by_discipline["D2_switch_computed"][:8]},
            "D3": {
                "query": ("first 8 predecessor compiled-C table_backed D3 sites, then "
                          "first 4 still-unselected D3 sites; ascending pc then image/id "
                          "within each tranche"),
                "work_order_wording_resolution": (
                    "phase3_jr_tables contains no jalr site/load-cell match; table_backed "
                    "is the frozen fail-closed operational proxy"),
                "direct_phase3_jr_table_match_count": len(direct_d3_table_matches),
                "direct_phase3_jr_table_match_site_ids": direct_d3_table_matches,
                "table_backed_count": len(d3_table), "table_backed_site_ids": d3_table,
                "next_count": len(d3_next), "next_site_ids": d3_next,
            },
        },
        "runtime_crosscheck": runtime,
        "outcome_barrier": {
            "D1_proof_attempted": False, "D2_proof_attempted": False,
            "D3_proof_attempted": False, "protected_set_decided": False,
            "go_no_go_decided": False, "gate_or_closure_mutated": False,
        },
        "protected_state": {
            "f01_status": "partial", "item_2": "not_met",
            "item2_ready_for_review": False,
            "review_blockers": ["IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"],
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
            print(f"discipline assignment differs: {output}")
            return 1
        print(f"discipline assignment current: {output}")
        return 0
    output.write_bytes(raw)
    print(f"wrote {output} ({len(raw)} bytes, sha256={_sha(raw)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
