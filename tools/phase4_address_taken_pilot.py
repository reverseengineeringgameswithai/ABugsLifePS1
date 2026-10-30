#!/usr/bin/env python3
"""Build the mandatory four-root address-taken / indirect-universe pilot.

All MIPS decoding and binary occurrence scanning is performed by two compiled
C implementations.  This driver owns immutable Git-object inputs, image hash
verification, exact-set comparison, decision policy, and deterministic JSON.

The pilot is a hard gate.  On NO-GO it banks only the reviewed negative and
does not run the corpus Stage A/B/C pass or re-arm the caller-domain pilot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_address_taken_pilot.json"
INDEX = ROOT / "analysis/phase4_static_frontier_index.json"
CALLER_PILOT = ROOT / "analysis/phase4_caller_domain_pilot.json"
JR_TABLES = ROOT / "analysis/phase3_jr_tables.json"
GATE = ROOT / "analysis/phase3_gate_audit.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"
F01_RESULT = ROOT / "analysis/phase4_f01_frontier_result.json"
MECHANICS = ROOT / "analysis/mechanics_baseline.yaml"
E16_SCORE = ROOT / "analysis/phase4_e16_dod_scorecard.json"
E16_CONSUMERS = ROOT / "tools/phase4_e16_table_consumers.c"
GAP_SCAN = ROOT / "tools/phase4_f01_gap_semantics.c"
LIBRARY_SCAN = ROOT / "tools/phase4_f01_library_partition.c"
WORK_ORDER = ROOT / "engineering-specs/phase4-address-taken-universe-work-order.md"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"
PRIMARY_C = ROOT / "tools/phase4_address_taken_pilot.c"
CROSSCHECK_C = ROOT / "tools/phase4_address_taken_crosscheck.c"
DRIVER = Path(__file__).resolve()

BASELINE_COMMIT = "f8d41264ff865b86a676e2fac536a80c474c4264"
SPEC_COMMIT = "5b78caa2ad624584d123ecad2939f60fbc53ef1c"
FREEZE_COMMIT = "607f3928397f"
CALLER_RECEIPT_SHA256 = "b31b7493ca47e990b2ba0760eade1ed3c41ce1e688d41d6101d6794455265f89"
SCHEMA = "abl-phase4-address-taken-pilot/1"

TARGETS = (
    ("LEVEL02_LEVEL1", 0x800B3F08, "MEMORY", 0x800B970C),
    ("LEVEL08_LEVEL1", 0x800B4084, "MEMORY", 0x800B970C),
    ("LEVEL05_LEVEL", 0x800B3D80, "LEVEL05_LEVEL", 0x800B4228),
    ("SCUS_942_88", 0x8005C58C, "LEVEL03_LEVEL", 0x800B4B38),
)

E16_POINTER_TABLE_RANGES = (
    ("0x30..0x57", 0x8009B4E8, 0x8009B588),
    ("0x28..0x2F", 0x8009C170, 0x8009C190),
    ("0x58..0x5F", 0x800A6450, 0x800A6470),
)


class PilotError(RuntimeError):
    """Fail-closed construction or verification error."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text, 16 if text.lower().startswith("0x") else 10)


def _git_show(commit: str, path: Path | str) -> bytes:
    rel = str(path.relative_to(ROOT) if isinstance(path, Path) else path)
    proc = subprocess.run(
        ["git", "show", f"{commit}:{rel}"], cwd=ROOT,
        capture_output=True, check=False,
    )
    if proc.returncode:
        raise PilotError(
            f"cannot read pinned Git object {commit}:{rel}: "
            + proc.stderr.decode(errors="replace").strip())
    return proc.stdout


def _load_git_json(commit: str, path: Path) -> tuple[dict, bytes]:
    raw = _git_show(commit, path)
    return json.loads(raw), raw


def _full_commit(short: str) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", f"{short}^{{commit}}"], cwd=ROOT,
        capture_output=True, text=True, check=False,
    )
    if proc.returncode:
        raise PilotError(f"cannot resolve commit {short}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _target_key(row: tuple[str, int, str, int]) -> str:
    return f"{row[0]}:0x{row[1]:08x}"


def _witness_key(row: tuple[str, int, str, int]) -> str:
    return f"{row[2]}:0x{row[3]:08x}"


def _verify_freeze() -> tuple[bytes, list[dict[str, str]]]:
    full_freeze = _full_commit(FREEZE_COMMIT)
    raw = _git_show(full_freeze, EXPERIMENT)
    text = raw.decode("utf-8")
    marker = "address-taken universe pilot frozen (PRE-OUTCOME record)"
    if marker not in text:
        raise PilotError("freeze commit lacks the address-taken pre-outcome marker")
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"\| `([^`]+)` \| data word `([^`]+)` \|", section)
    expected = [(_target_key(row), _witness_key(row)) for row in TARGETS]
    if [(root.lower(), witness.lower()) for root, witness in rows] != [
            (root.lower(), witness.lower()) for root, witness in expected]:
        raise PilotError(f"frozen root/witness order differs: {rows!r}")
    if "No address-taken sweep" not in section or "GO/NO-GO decision" not in section:
        raise PilotError("freeze section does not attest that outcomes were absent")
    for ancestor in (BASELINE_COMMIT, SPEC_COMMIT):
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, full_freeze],
            cwd=ROOT, check=False,
        )
        if proc.returncode:
            raise PilotError(f"{ancestor} is not an ancestor of the freeze commit")
    return raw, [
        {"root": root, "witness": witness} for root, witness in expected
    ]


def _record_extent(row: dict) -> tuple[int, int]:
    if row.get("entry") is not None and row.get("end") is not None:
        return _int(row["entry"]), _int(row["end"])
    extent = row.get("extent")
    if isinstance(extent, list) and len(extent) == 2:
        return _int(extent[0]), _int(extent[1])
    raise PilotError(f"record lacks an extent: {row.get('image_id')} {row.get('name')}")


def _manifest(index: dict, jr: dict) -> bytes:
    lines = ["VERSION 1"]
    images = index.get("images") or []
    if len(images) != 21 or len({row["image_id"] for row in images}) != 21:
        raise PilotError("static index image universe is not 21 unique images")
    image_ids = {row["image_id"] for row in images}
    for image in images:
        path = ROOT / image["path"]
        raw = path.read_bytes()
        if (len(raw) != int(image["size"]) or _sha(raw) != image["sha256"]
                or image.get("identity_verified") is not True):
            raise PilotError(f"image identity failed: {image['image_id']}")
        lines.append(
            f"IMAGE {image['image_id']} {image['path']} "
            f"{_int(image['file_va_base']):08x} {len(raw)} {image['role']}")

    records = index.get("records") or []
    if len(records) != 1191:
        raise PilotError(f"static range universe drifted: {len(records)} != 1191")
    kinds: dict[str, int] = defaultdict(int)
    for row in records:
        image = row["image_id"]
        kind = str(row.get("range_type") or "")
        if image not in image_ids or kind not in {"code", "data", "thunk"}:
            raise PilotError(f"unsupported range record: {image} {kind}")
        lo, hi = _record_extent(row)
        name = re.sub(r"[^A-Za-z0-9_.:+-]", "_", str(row.get("name") or f"anon_0x{lo:08x}"))
        lines.append(f"RANGE {image} {lo:08x} {hi:08x} {kind} {name}")
        kinds[kind] += 1
    if kinds != {"code": 1059, "data": 78, "thunk": 54}:
        raise PilotError(f"range type partition drifted: {dict(kinds)!r}")

    tables: set[tuple[int, int]] = set()
    for item in (jr.get("decoded") or {}).values():
        lo = _int(item["table"])
        tables.add((lo, lo + int(item["entries"]) * 4))
    if len(tables) != 36 or jr.get("total_entries_decoded") != 869:
        raise PilotError("phase3 jr table universe is not the pinned 36/869")
    for lo, hi in sorted(tables):
        lines.append(f"TABLE SCUS_942_88 {lo:08x} {hi:08x} phase3_jr_tables")

    proved: set[tuple[int, int]] = set()
    for field in ("indirect_jump_targets", "indirect_jump_targets_from_gate"):
        for pc, targets in ((index.get(field) or {}).get("site_targets") or {}).items():
            for target in targets:
                proved.add((_int(pc), _int(target)))
    if len(proved) != 492:
        raise PilotError(f"proved per-edge target universe drifted: {len(proved)} != 492")
    for pc, target in sorted(proved):
        lines.append(f"PROVED SCUS_942_88 {pc:08x} {target:08x}")

    for image, entry, witness_image, witness in TARGETS:
        lines.append(f"ROOT {image} {entry:08x} {witness_image} {witness:08x}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _compile(source: Path, output: Path) -> bytes:
    proc = subprocess.run(
        ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
         "-o", str(output), str(source)],
        cwd=ROOT, capture_output=True, text=True,
    )
    if proc.returncode:
        raise PilotError(f"C compile failed ({source.name}): {proc.stderr.strip()}")
    return output.read_bytes()


def _run_json(command: list[str]) -> dict:
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise PilotError(f"command failed ({' '.join(command)}): {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PilotError(f"non-JSON C output: {exc}: {proc.stdout[:500]!r}") from exc


def _occ_tuple(row: dict) -> tuple[str, str, str, str | None]:
    return (row["image"], row["va"], row["kind"], row.get("pair_end_pc"))


def _occ_id(root: str, row: dict) -> str:
    suffix = f":{row['pair_end_pc']}" if row.get("pair_end_pc") else ""
    return f"{root}@{row['image']}:{row['va']}:{row['kind']}{suffix}"


def _compare_stage_a(primary: dict, independent: dict) -> dict:
    aroots = primary.get("stage_a", {}).get("roots") or []
    broots = independent.get("roots") or []
    expected = [_target_key(row) for row in TARGETS]
    if [row.get("key") for row in aroots] != expected:
        raise PilotError("primary C root order differs from frozen targets")
    if [row.get("key") for row in broots] != expected:
        raise PilotError("independent C root order differs from frozen targets")
    disagreements = []
    exact_sets: dict[str, list[str]] = {}
    for a, b in zip(aroots, broots):
        aset = sorted({_occ_tuple(row) for row in a.get("occurrences") or []})
        bset = sorted({_occ_tuple(row) for row in b.get("occurrences") or []})
        if aset != bset or a.get("occurrence_count") != len(aset) or b.get("occurrence_count") != len(bset):
            disagreements.append({
                "root": a.get("key"),
                "primary_only": [list(row) for row in sorted(set(aset) - set(bset))],
                "independent_only": [list(row) for row in sorted(set(bset) - set(aset))],
                "primary_reported_count": a.get("occurrence_count"),
                "independent_reported_count": b.get("occurrence_count"),
            })
        exact_sets[a["key"]] = sorted(_occ_id(a["key"], row) for row in a["occurrences"])
    if disagreements:
        raise PilotError(f"independent Stage-A disagreement: {disagreements!r}")
    return {
        "all_exact_sets_agree": True,
        "disagreements": [],
        "per_function_occurrence_ids": exact_sets,
    }


def _coexists(source: str, root_image: str) -> bool:
    if root_image == "SCUS_942_88":
        return True
    if source in {"SCUS_942_88", "MEMORY"}:
        return True
    if source.startswith("LEVEL") and root_image.startswith("LEVEL"):
        return source == root_image
    return source == root_image


def _edge_id(row: dict) -> str:
    return f"{row['image']}:{row['pc']}:{row['kind']}:{row['register']}"


def _prior_witness_and_edge_deltas(caller: dict, primary: dict) -> tuple[list[dict], list[dict]]:
    prior_roots = {
        str(row["key"]).lower(): row
        for row in caller["stage_a_sample_caller_closure"]["closure_roots"]
    }
    code_sites = primary["indirect_transfer_universe"]["code_only_sites"]
    provenance = []
    deltas = []
    for target in TARGETS:
        key = _target_key(target)
        prior = prior_roots.get(key.lower())
        if prior is None:
            raise PilotError(f"accepted caller pilot lacks root {key}")
        old_rows = prior.get("relevant_unproved_indirect_edges") or []
        if not old_rows:
            raise PilotError(f"accepted caller pilot lacks openness witness for {key}")
        first = old_rows[0]
        first_key = f"{first['image']}:{first['pc']}"
        if first_key.lower() != _witness_key(target).lower():
            raise PilotError(f"first openness witness drifted for {key}: {first_key}")
        if prior.get("counts", {}).get("address_taken") != 0 or prior.get("address_taken_outside_proved_tables") != []:
            raise PilotError(f"prior pilot no longer says zero address occurrences for {key}")
        provenance.append({
            "root": key,
            "fixed_witness": _witness_key(target),
            "source_field": "stage_a_sample_caller_closure.closure_roots[].relevant_unproved_indirect_edges[0]",
            "source_semantics": "first unresolved indirect transfer in the coexisting-image superset",
            "was_recorded_as_address_taken_occurrence": False,
            "prior_address_taken_occurrence_count": 0,
        })
        old = {
            f"{row['image']}:{row['pc']}:{row['kind']}:{row['register']}"
            for row in old_rows
        }
        new = {
            _edge_id(row) for row in code_sites
            if not row["existing_proved_site"] and _coexists(row["image"], target[0])
        }
        deltas.append({
            "root": key,
            "prior_unproved_indirect_count": len(old),
            "corrected_code_only_unproved_indirect_count": len(new),
            "removed_ids": sorted(old - new),
            "added_ids": sorted(new - old),
            "unchanged_ids": sorted(old & new),
        })
    return provenance, deltas


def _data_region_members(primary: dict) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for root in primary["stage_a"]["roots"]:
        for occurrence in root["occurrences"]:
            region = occurrence.get("containing_range")
            table = occurrence.get("proved_table_membership")
            if region and region.get("type") == "data":
                key = f"{occurrence['image']}:{region['lo']}..{region['hi']}"
            elif table:
                # A phase3-proved jump-table extent is itself a data region,
                # even when the frontier index leaves the enclosing gap
                # otherwise unclassified.
                key = f"{occurrence['image']}:{table['lo']}..{table['hi']}"
            else:
                continue
            grouped[key].append(_occ_id(root["key"], occurrence))
    return {key: sorted(value) for key, value in sorted(grouped.items())}


def _removed_edge_range_audit(index: dict, deltas: list[dict]) -> list[dict]:
    by_image: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for row in index["records"]:
        lo, hi = _record_extent(row)
        by_image[row["image_id"]].append((lo, hi, row["range_type"]))
    out = []
    for delta in deltas:
        data_ids = []
        unexpected = []
        for edge_id in delta["removed_ids"]:
            image, pc_text, _kind, _reg = edge_id.split(":")
            pc = int(pc_text, 16)
            kinds = {
                kind for lo, hi, kind in by_image[image] if lo <= pc < hi
            }
            if kinds == {"data"}:
                data_ids.append(edge_id)
            else:
                unexpected.append({"id": edge_id, "containing_range_types": sorted(kinds)})
        if unexpected:
            raise PilotError(
                f"corrected edge delta removed a non-data site: {unexpected!r}")
        out.append({
            "root": delta["root"],
            "removed_false_data_decode_ids": sorted(data_ids),
            "removed_false_data_decode_count": len(data_ids),
            "unexpected_non_data_removed_ids": [],
        })
    return out


def _capsule_crosscheck(capsules: dict, closed_roots: list[str]) -> dict:
    rows = capsules.get("capsules") or []
    if (capsules.get("capsule_count") != 50 or len(rows) != 50
            or capsules.get("complete") is not True or capsules.get("errors") != []
            or any(row.get("control_match") is not True for row in rows)):
        raise PilotError("pinned 50-capsule universe is incomplete or control-divergent")
    if closed_roots:
        return {
            "status": "UNAVAILABLE_SITE_TIME_INDIRECT_TARGETS",
            "capsule_universe": 50,
            "closed_roots": closed_roots,
            "site_time_observations": 0,
            "all_observed_targets_within_proved_sets": None,
            "soundness_violation": False,
            "clean_for_go": False,
            "reason": ("frame-boundary count-mode capsules do not retain each indirect "
                       "target at the fixed transfer sites; zero observations is not clean"),
        }
    return {
        "status": "NOT_APPLICABLE_NO_CLOSED_ROOTS",
        "capsule_universe": 50,
        "closed_roots": [],
        "site_time_observations": 0,
        "all_observed_targets_within_proved_sets": True,
        "soundness_violation": False,
        "clean_for_go": False,
        "reason": "no proved-complete root target set exists to compare",
    }


def build() -> dict:
    freeze_raw, frozen_targets = _verify_freeze()
    freeze = _full_commit(FREEZE_COMMIT)
    index, index_raw = _load_git_json(freeze, INDEX)
    caller, caller_raw = _load_git_json(freeze, CALLER_PILOT)
    jr, jr_raw = _load_git_json(freeze, JR_TABLES)
    gate, gate_raw = _load_git_json(freeze, GATE)
    capsules, capsules_raw = _load_git_json(freeze, CAPSULES)
    f01, f01_raw = _load_git_json(freeze, F01_RESULT)
    e16, e16_raw = _load_git_json(freeze, E16_SCORE)
    mechanics_raw = _git_show(freeze, MECHANICS)
    work_raw = _git_show(freeze, WORK_ORDER)
    e16_consumers_raw = _git_show(freeze, E16_CONSUMERS)
    gap_scan_raw = _git_show(freeze, GAP_SCAN)
    library_scan_raw = _git_show(freeze, LIBRARY_SCAN)
    if _sha(caller_raw) != CALLER_RECEIPT_SHA256:
        raise PilotError("accepted caller-domain receipt identity drifted")
    if not str(e16.get("row_id") or "").startswith("E16"):
        raise PilotError("pinned E16 scope artifact is not E16")
    manifest = _manifest(index, jr)

    with tempfile.TemporaryDirectory(prefix="phase4-address-taken-") as tmp_text:
        tmp = Path(tmp_text)
        manifest_path = tmp / "pilot.manifest"
        manifest_path.write_bytes(manifest)
        primary_bin = tmp / "address_taken_primary"
        cross_bin = tmp / "address_taken_crosscheck"
        primary_binary = _compile(PRIMARY_C, primary_bin)
        cross_binary = _compile(CROSSCHECK_C, cross_bin)
        primary_selftest = _run_json([str(primary_bin), "--self-test"])
        cross_selftest = _run_json([str(cross_bin), "--self-test"])
        primary = _run_json([str(primary_bin), str(manifest_path)])
        independent = _run_json([str(cross_bin), str(manifest_path)])

    if primary_selftest.get("verdict") is not True or cross_selftest.get("verdict") is not True:
        raise PilotError("a C self-test failed")
    crosscheck = _compare_stage_a(primary, independent)
    prior_provenance, edge_deltas = _prior_witness_and_edge_deltas(caller, primary)

    witness_rows = primary.get("fixed_witnesses") or []
    if len(witness_rows) != 4:
        raise PilotError("primary C did not return all four fixed witnesses")
    witness_resolution = []
    for row in witness_rows:
        witness_resolution.append({
            **row,
            "work_order_data_word_label_confirmed":
                row["relationship"] == "literal_entry_occurrence"
                and row.get("containing_range", {}).get("type") == "data",
        })

    outcomes = primary.get("root_outcomes") or []
    expected_keys = [_target_key(row) for row in TARGETS]
    if [row.get("root") for row in outcomes] != expected_keys:
        raise PilotError("primary C outcome order differs from frozen roots")
    closed_roots = sorted(row["root"] for row in outcomes if row["classification"] == "CLOSED")
    open_roots = sorted(row["root"] for row in outcomes if row["classification"] == "OPEN")
    if len(closed_roots) + len(open_roots) != 4:
        raise PilotError("a root has neither OPEN nor CLOSED classification")
    capsule_gate = _capsule_crosscheck(capsules, closed_roots)
    if capsule_gate["soundness_violation"]:
        decision = "HALT_SOUNDNESS_BUG"
    elif len(closed_roots) >= 2 and capsule_gate["clean_for_go"]:
        decision = "GO"
    else:
        decision = "NO-GO"
    if decision == "GO":
        raise PilotError("pilot unexpectedly returned GO; full Stage A/B/C continuation is required")

    table_proofs = primary.get("guarded_table_proofs") or []
    memory_proof = next(
        (row for row in table_proofs if row.get("site") == "MEMORY:0x800b970c"), None)
    if not memory_proof or memory_proof.get("status") != "PROVED_LOCAL_ADDRESS_DOMAIN":
        raise PilotError("MEMORY guarded interval/table-address proof did not reproduce")
    if memory_proof.get("gate_grade_region_closure") is not False:
        raise PilotError("local MEMORY proof was incorrectly promoted to gate-grade closure")

    f01_verdicts = f01.get("verdicts") or {}
    if (f01_verdicts.get("dimension_promoted") is not False
            or f01_verdicts.get("item2_ready_for_review") is not False
            or f01_verdicts.get("review_blockers") != [
                "IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"]):
        raise PilotError("protected F01 state differs from the accepted partial baseline")

    no_go_reasons = []
    if len(closed_roots) <= 1:
        no_go_reasons.append("closed_root_count_at_or_below_1")
    if any(not row["work_order_data_word_label_confirmed"] for row in witness_resolution):
        no_go_reasons.append("fixed_witness_membership_premise_not_confirmed")
    if primary["indirect_transfer_universe"]["remaining_site_count"]:
        no_go_reasons.append("gate_grade_indirect_target_domain_universe_incomplete")
    if not capsule_gate["clean_for_go"]:
        no_go_reasons.append("runtime_crosscheck_not_clean_for_go")

    roots_to_occurrences = crosscheck["per_function_occurrence_ids"]
    data_to_members = _data_region_members(primary)
    return {
        "_comment": ("Mandatory four-root address-taken pilot frozen before outcomes in "
                     f"{freeze}. The result is a reviewed-negative candidate; it does not "
                     "run the full corpus pass or change F01."),
        "schema": SCHEMA,
        "inputs": {
            "work_order": str(WORK_ORDER.relative_to(ROOT)),
            "work_order_sha256": _sha(work_raw),
            "issued_baseline_commit": BASELINE_COMMIT,
            "work_order_commit": SPEC_COMMIT,
            "pre_outcome_freeze_commit": freeze,
            "derived_input_snapshot_commit": freeze,
            "pre_outcome_freeze_note_sha256": _sha(freeze_raw),
            "accepted_caller_pilot": str(CALLER_PILOT.relative_to(ROOT)),
            "accepted_caller_pilot_sha256": _sha(caller_raw),
            "static_index": str(INDEX.relative_to(ROOT)),
            "static_index_sha256": _sha(index_raw),
            "jr_tables": str(JR_TABLES.relative_to(ROOT)),
            "jr_tables_sha256": _sha(jr_raw),
            "gate": str(GATE.relative_to(ROOT)),
            "gate_sha256": _sha(gate_raw),
            "capsule_set": str(CAPSULES.relative_to(ROOT)),
            "capsule_set_sha256": _sha(capsules_raw),
            "f01_result": str(F01_RESULT.relative_to(ROOT)),
            "f01_result_sha256": _sha(f01_raw),
            "mechanics_baseline_sha256": _sha(mechanics_raw),
            "e16_scope_artifact": str(E16_SCORE.relative_to(ROOT)),
            "e16_scope_artifact_sha256": _sha(e16_raw),
            "e16_consumer_source_sha256": _sha(e16_consumers_raw),
            "gap_scan_source_sha256": _sha(gap_scan_raw),
            "library_materialization_source_sha256": _sha(library_scan_raw),
            "c_manifest_sha256": _sha(manifest),
            "driver": str(DRIVER.relative_to(ROOT)),
            "driver_sha256": _sha(DRIVER.read_bytes()),
            "primary_c": str(PRIMARY_C.relative_to(ROOT)),
            "primary_c_sha256": _sha(PRIMARY_C.read_bytes()),
            "primary_binary_sha256": _sha(primary_binary),
            "independent_c": str(CROSSCHECK_C.relative_to(ROOT)),
            "independent_c_sha256": _sha(CROSSCHECK_C.read_bytes()),
            "independent_binary_sha256": _sha(cross_binary),
        },
        "pilot_universe": {
            "definition": "the four root/witness pairs committed before outcomes",
            "targets": frozen_targets,
            "root_count": 4,
            "unique_witness_address_count": 3,
            "sample_is_not_full_function_corpus": True,
        },
        "reused_existing_machinery": {
            "phase3_recovered_jr_target_occurrences": 869,
            "phase3_table_ranges": 36,
            "gate_per_edge_target_records": 492,
            "gate_rule": "never generalize beyond a proved edge",
            "e16_pointer_table_ranges": [
                {"marker_range": marker, "lo": f"0x{lo:08x}", "hi": f"0x{hi:08x}"}
                for marker, lo, hi in E16_POINTER_TABLE_RANGES
            ],
            "e16_use_in_this_pilot": ("reused as already-mapped Stage-A data regions; "
                                       "none contains a fixed witness"),
            "address_scan_forms": ["aligned literal word", "lui/addiu", "lui/ori"],
            "mover_vm_occurrence_rule": "table slots are counted even when target values repeat",
            "hoisted_load_hazard_checked": True,
        },
        "prior_receipt_witness_semantics": prior_provenance,
        "stage_a": {
            "scope": "four fixed entries across all aligned words and code materialisations in 21 pinned images",
            "primary": primary["stage_a"],
            "exact_sets_both_directions": {
                "per_function_occurrence_ids": roots_to_occurrences,
                "per_data_region_member_ids": data_to_members,
            },
            "independent_crosscheck": {
                **crosscheck,
                "implementation": str(CROSSCHECK_C.relative_to(ROOT)),
                "primary_selftest": primary_selftest,
                "independent_selftest": cross_selftest,
            },
        },
        "fixed_witness_resolution": witness_resolution,
        "stage_b_pilot": {
            "guarded_table_proofs": table_proofs,
            "indirect_transfer_universe": primary["indirect_transfer_universe"],
            "root_outcomes": outcomes,
            "recursion_depths": {
                row["root"]: row["recursion_depth_reached"] for row in outcomes
            },
            "writer_recursion_started": False,
            "why": ("two witness addresses are data words unequal to their named roots; "
                    "MEMORY:0x800B970C is a code consumer, not a cell, and its local "
                    "interval proof does not exhaust the region writer/consumer universe"),
        },
        "corrected_indirect_universe_movement": edge_deltas,
        "removed_false_decode_audit": _removed_edge_range_audit(index, edge_deltas),
        "capsule_crosscheck": capsule_gate,
        "decision": {
            "verdict": decision,
            "go_threshold_closed_roots": 2,
            "closed_root_count": len(closed_roots),
            "closed_root_ids": closed_roots,
            "open_root_count": len(open_roots),
            "open_root_ids": open_roots,
            "reasons": no_go_reasons,
            "full_pass_authorized": False,
            "recommended_replacement_argument": (
                "Replace the proposed witness-cell closure argument with a complete "
                "per-site target-domain/exclusion proof over the corrected code-only "
                "jr/jalr universe, using whole-table value-domain invariants for "
                "table-backed sites."),
        },
        "stage_c_not_run": {
            "reason": "mandatory four-root pilot returned NO-GO",
            "caller_domain_frozen_20_rerun": False,
            "caller_roots_open_to_closed": [],
            "caller_roots_closed_to_open": [],
            "fixture_store_movement": {"gained_ids": [], "lost_ids": []},
            "ledger_movement": {"gained_ids": [], "lost_ids": []},
            "campaign_row_movement": {"gained_ids": [], "lost_ids": []},
            "old_pins_replaced": [],
        },
        "configuration": {
            "full_corpus_pass_performed": False,
            "runtime_replay_performed": False,
            "instrumented_run_performed": False,
            "preserved_session_consumed": False,
        },
        "protected_state": {
            "f01_status": "partial",
            "item_2": "not_met",
            "dimension_promoted": f01_verdicts["dimension_promoted"],
            "item2_ready_for_review": f01_verdicts["item2_ready_for_review"],
            "review_blockers": f01_verdicts["review_blockers"],
            "mechanics_baseline_modified": False,
            "caller_domain_receipt_modified": False,
            "phase3_jr_or_gate_artifact_modified": False,
            "canon_updated": False,
        },
        "authority": {
            "changes_campaign_registry": False,
            "promotes_dimension": False,
            "closes_item_2": False,
            "banks_f01_status": False,
            "fresh_detached_verifier_required_for_any_status_change": True,
        },
    }


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    out = args.output if args.output.is_absolute() else ROOT / args.output
    rendered = render(build())
    if args.check:
        if not out.is_file() or out.read_bytes() != rendered:
            print(f"stale: {out.relative_to(ROOT)}")
            return 1
        print(f"ok: {out.relative_to(ROOT)}")
        return 0
    out.write_bytes(rendered)
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
