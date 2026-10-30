#!/usr/bin/env python3
"""Freeze the target-exclusion denominator, strata, and pilot before outcomes.

The predecessor receipt and static corpus are read from the work-order commit,
not from mutable working-tree copies.  C owns all image-byte and MIPS facts;
this driver owns Git identities, exact-set arithmetic, outcome-blind selection,
and deterministic JSON.

This program deliberately contains no Stage-2 proof or GO/NO-GO logic.  Its
output is the auditable barrier that must be committed before those outcomes
are allowed to exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_target_exclusion_freeze.json"
INDEX = ROOT / "analysis/phase4_static_frontier_index.json"
PREDECESSOR = ROOT / "analysis/phase4_address_taken_pilot.json"
CALLER_PILOT = ROOT / "analysis/phase4_caller_domain_pilot.json"
FRONTIER_RESOLVE = ROOT / "analysis/phase4_f01_frontier_resolve.json"
FRONTIER_RESULT = ROOT / "analysis/phase4_f01_frontier_result.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"
WORK_ORDER = ROOT / "engineering-specs/phase4-target-exclusion-work-order.md"
ERRATUM = ROOT / "engineering-specs/phase4-address-taken-universe-work-order.md"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"
KNOWN_WRITER_SOURCE = ROOT / "tools/phase4_f01_frontier_resolve.c"
SHARED_C = ROOT / "tools/phase4_typed_state_provenance.c"
STAGE1_C = ROOT / "tools/phase4_target_exclusion_stage1.c"

BASELINE_COMMIT = "2a617486b30fce115933900e307c233ddb121f56"
ERRATUM_COMMIT = "7658e79f674d18102e3f25f6b3dd7eb5989d331a"
SPEC_COMMIT = "d4c60047fb2d1419f7691f6e2b6a628eea2fdb42"
SCHEMA = "abl-phase4-target-exclusion-freeze/1"
FREEZE_MARKER = "target-exclusion pilot frozen (PRE-OUTCOME record)"

ROOT_KEYS = (
    "LEVEL02_LEVEL1:0x800b3f08",
    "LEVEL08_LEVEL1:0x800b4084",
    "LEVEL05_LEVEL:0x800b3d80",
    "SCUS_942_88:0x8005c58c",
)

STRATA = (
    "table_backed",
    "computed",
    "register_provenance",
    "return_like",
    "return_like_unproved_incoming_ra",
    "unclassified_opaque_definition",
    "mixed_reaching_definitions",
)


class FreezeError(RuntimeError):
    """An identity, universe, or fail-closed classification invariant failed."""


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
        raise FreezeError(
            f"cannot read pinned object {commit}:{rel}: "
            + proc.stderr.decode(errors="replace").strip())
    return proc.stdout


def _git_json(commit: str, path: Path) -> tuple[dict, bytes]:
    raw = _git_show(commit, path)
    return json.loads(raw), raw


def _verify_ancestry() -> None:
    for ancestor in (BASELINE_COMMIT, ERRATUM_COMMIT):
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, SPEC_COMMIT],
            cwd=ROOT, check=False,
        )
        if proc.returncode:
            raise FreezeError(f"{ancestor} is not an ancestor of {SPEC_COMMIT}")


def _record_extent(row: dict) -> tuple[int, int]:
    if row.get("entry") is not None and row.get("end") is not None:
        return _int(row["entry"]), _int(row["end"])
    extent = row.get("extent")
    if isinstance(extent, list) and len(extent) == 2:
        return _int(extent[0]), _int(extent[1])
    raise FreezeError(f"record lacks extent: {row.get('image_id')} {row.get('name')}")


def _site_sort(site_id: str) -> tuple[int, str, str]:
    image, pc, kind, register = site_id.split(":")
    return int(pc, 16), image, f"{kind}:{register}"


def _parse_site_id(site_id: str) -> tuple[str, int, str, str]:
    bits = site_id.split(":")
    if len(bits) != 4 or bits[2] not in {"jr", "jalr"}:
        raise FreezeError(f"malformed indirect-site id: {site_id}")
    return bits[0], int(bits[1], 16), bits[2], bits[3]


def _verify_images(index: dict) -> tuple[bytes, list[dict]]:
    rows = []
    manifest = []
    images = index.get("images") or []
    if len(images) != 21 or len({row.get("image_id") for row in images}) != 21:
        raise FreezeError("static image universe is not 21 unique images")
    for image in images:
        path = ROOT / image["path"]
        raw = path.read_bytes()
        if (image.get("identity_verified") is not True
                or len(raw) != int(image["size"])
                or _sha(raw) != image["sha256"]):
            raise FreezeError(f"image identity failed: {image['image_id']}")
        manifest.append(
            f"{image['image_id']} {image['path']} {image['file_va_base']}")
        rows.append({
            "image": image["image_id"],
            "path": image["path"],
            "size": len(raw),
            "sha256": _sha(raw),
            "file_va_base": image["file_va_base"],
            "identity_verified": True,
        })
    return ("\n".join(manifest) + "\n").encode(), rows


def _compile(source: Path, output: Path) -> bytes:
    proc = subprocess.run(
        ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
         "-o", str(output), str(source)],
        cwd=ROOT, capture_output=True, text=True,
    )
    if proc.returncode:
        raise FreezeError(f"C compile failed ({source.name}): {proc.stderr.strip()}")
    return output.read_bytes()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise FreezeError(
            f"command failed ({' '.join(command)}): {proc.stderr.strip()}")
    return proc


def _run_json(command: list[str]) -> dict:
    proc = _run(command)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise FreezeError(f"non-JSON C output: {proc.stdout[:500]!r}") from exc


def _derive_union(predecessor: dict, index: dict) -> tuple[list[dict], dict]:
    universe = predecessor["stage_b_pilot"]["indirect_transfer_universe"]
    all_code = universe.get("code_only_sites") or []
    unproved = [row for row in all_code if row.get("existing_proved_site") is False]
    by_id = {row["id"]: row for row in unproved}
    if (len(all_code), universe.get("existing_proved_site_count"), len(unproved)) != (266, 87, 179):
        raise FreezeError("predecessor code/proved/unproved universe is not 266/87/179")
    if len(by_id) != 179:
        raise FreezeError("predecessor unproved code-only ids are not unique")

    movements = predecessor.get("corrected_indirect_universe_movement") or []
    if [row.get("root") for row in movements] != list(ROOT_KEYS):
        raise FreezeError("corrected movement roots/order differ from the authoritative receipt")
    corrected_by_root: dict[str, set[str]] = {}
    old_by_root: dict[str, set[str]] = {}
    removed_reason_by_id: dict[str, set[str]] = defaultdict(set)
    movement_rows = []
    for row in movements:
        new = set(row.get("unchanged_ids") or []) | set(row.get("added_ids") or [])
        old = set(row.get("unchanged_ids") or []) | set(row.get("removed_ids") or [])
        if len(new) != row["corrected_code_only_unproved_indirect_count"]:
            raise FreezeError(f"corrected exact set/count mismatch for {row['root']}")
        if len(old) != row["prior_unproved_indirect_count"]:
            raise FreezeError(f"prior exact set/count mismatch for {row['root']}")
        if row.get("added_ids") != []:
            raise FreezeError(f"masking unexpectedly added sites for {row['root']}")
        corrected_by_root[row["root"]] = new
        old_by_root[row["root"]] = old
        for site_id in row.get("removed_ids") or []:
            removed_reason_by_id[site_id].add(row["root"])
        movement_rows.append({
            "root": row["root"],
            "before_count": len(old),
            "after_count": len(new),
            "removed_ids": sorted(old - new, key=_site_sort),
            "added_ids": sorted(new - old, key=_site_sort),
            "unchanged_ids": sorted(old & new, key=_site_sort),
        })

    corrected_union = set().union(*corrected_by_root.values())
    old_union = set().union(*old_by_root.values())
    if corrected_union != set(by_id) or len(corrected_union) != 179:
        raise FreezeError("corrected per-root union differs from the 179 code-only sites")
    if len(old_union) != 261 or len(old_union - corrected_union) != 82:
        raise FreezeError("pre-mask union is not 261 with exactly 82 removals")

    ranges: dict[str, list[tuple[int, int, str, str]]] = defaultdict(list)
    for record in index.get("records") or []:
        lo, hi = _record_extent(record)
        ranges[record["image_id"]].append(
            (lo, hi, record.get("range_type") or "", str(record.get("name") or "")))
    masked = []
    for site_id in sorted(old_union - corrected_union, key=_site_sort):
        image, pc, _kind, _reg = _parse_site_id(site_id)
        containing = [
            {"lo": f"0x{lo:08x}", "hi": f"0x{hi:08x}", "type": kind, "name": name}
            for lo, hi, kind, name in ranges[image] if lo <= pc < hi
        ]
        if not containing or {row["type"] for row in containing} != {"data"}:
            raise FreezeError(f"masked site is not exclusively inside pinned data: {site_id}")
        masked.append({
            "id": site_id,
            "reason": "pinned_data_record_false_decode",
            "containing_ranges": containing,
            "removed_from_root_supersets": sorted(removed_reason_by_id[site_id]),
        })

    rows = []
    for site_id in sorted(corrected_union, key=_site_sort):
        source = by_id[site_id]
        rows.append({
            "id": site_id,
            "image": source["image"],
            "pc": source["pc"].lower(),
            "kind": source["kind"],
            "register": source["register"],
            "owner_range_from_predecessor": source.get("owner_range"),
            "root_obligations": [
                root for root in ROOT_KEYS if site_id in corrected_by_root[root]
            ],
        })
    movement = {
        "comparison": "exact site-id sets in both directions",
        "pre_mask_union_count": len(old_union),
        "corrected_union_count": len(corrected_union),
        "masked_out_count": len(masked),
        "added_by_masking_count": 0,
        "corrected_sites_in": [row["id"] for row in rows],
        "masked_sites_out": masked,
        "unexpected_added_ids": [],
        "per_root_supersets": movement_rows,
    }
    return rows, movement


def _owner_for_site(index: dict, site: dict) -> dict:
    pc = _int(site["pc"])
    candidates = []
    for row in index["records"]:
        if row.get("image_id") != site["image"] or row.get("range_type") not in {"code", "thunk"}:
            continue
        lo, hi = _record_extent(row)
        if lo <= pc < hi:
            candidates.append(row)
    if not candidates:
        raise FreezeError(f"no code owner for {site['id']}")
    wanted = str(site.get("owner_range_from_predecessor") or "").casefold()
    named = [r for r in candidates if str(r.get("name") or "").casefold() == wanted]
    selected = min(named or candidates,
                   key=lambda r: (_record_extent(r)[1] - _record_extent(r)[0],
                                  _record_extent(r)[0], str(r.get("name") or "")))
    lo, hi = _record_extent(selected)
    return {
        "image": selected["image_id"],
        "entry": f"0x{lo:08x}",
        "end": f"0x{hi:08x}",
        "name": selected.get("name") or f"anon_0x{lo:08x}",
        "range_type": selected["range_type"],
        "predecessor_name_matched": bool(named),
    }


def _classify(site: dict, query: dict, guarded_memory: dict | None) -> tuple[str, dict]:
    definitions = query.get("definitions") or []
    observable = [row for row in definitions if row.get("observable") is True]
    classes = {str(row.get("class")) for row in observable}

    if guarded_memory is not None:
        return "table_backed", {
            "basis": "predecessor_C_guarded_table_extent_plus_current_C_reaching_defs",
            "pointer_regions": [guarded_memory["table_extent"]],
            "candidate_only_not_a_stage2_invariant": True,
        }
    if observable and (
            (query.get("every_observable_def_loads_one_address") is True
             and query.get("loaded_from"))
            or classes <= {"global_load", "table_address"}):
        addresses = sorted({
            str(row["address"]).lower() for row in observable if row.get("address")
        })
        return "table_backed", {
            "basis": "C-classified_global_or_table_load_reaching_definitions",
            "pointer_regions": [
                {"lo": address, "hi": f"0x{int(address, 16) + 4:08x}",
                 "extent_basis": "single recovered load cell; width is conservative word"}
                for address in addresses
            ],
            "candidate_only_not_a_stage2_invariant": True,
        }
    if (site["kind"] == "jr" and site["register"] == "ra" and not observable
            and query.get("targets_all_hold_incoming") is True):
        return "return_like_unproved_incoming_ra", {
            "basis": "C proves incoming ra reaches the site, not that every entry is a call link",
            "why_not_return_like": "caller/entry target universe remains OPEN",
        }
    if observable and classes <= {"register_copy", "frame_reload"}:
        return "register_provenance", {
            "basis": "C-classified register copy/frame reload",
            "source_register_proof_complete": False,
        }
    if observable and classes <= {"materialised_constant", "self_adjust"}:
        return "computed", {
            "basis": "C-classified materialised constants/self-adjustments",
            "stage2_target_set_not_yet_evaluated": True,
        }
    if observable and classes == {"opaque"}:
        return "unclassified_opaque_definition", {
            "basis": "every observable reaching definition is C-classified opaque",
            "fail_closed": True,
        }
    return "mixed_reaching_definitions", {
        "basis": "multiple or unsupported C reaching-definition classes",
        "observable_classes": sorted(classes),
        "fail_closed": True,
    }


def _known_writers(raw: bytes) -> list[str]:
    text = raw.decode("utf-8")
    try:
        body = text.split("static const KnownWriter KNOWN_WRITERS[] = {", 1)[1].split("};", 1)[0]
    except IndexError as exc:
        raise FreezeError("cannot locate KNOWN_WRITERS in pinned C source") from exc
    out = []
    for image, pc in re.findall(r'\{\s*"([^"]+)",\s*0x([0-9a-fA-F]+)\s*\}', body):
        image = "SCUS_942_88" if image == "SCUS" else image
        out.append(f"{image}:0x{int(pc, 16):08x}")
    if len(out) != 58 or len(set(out)) != 58:
        raise FreezeError(f"KNOWN_WRITERS is not 58 unique image:pc ids: {len(out)}")
    return sorted(out)


def _protected_set(resolve: dict, writers: list[str]) -> dict:
    window_sites = []
    for row in resolve.get("resolved_hits") or []:
        image = "SCUS_942_88" if row["image"] == "SCUS" else row["image"]
        window_sites.append(f"{image}:{str(row['pc']).lower()}")
    if len(window_sites) != 124 or len(set(window_sites)) != 124:
        raise FreezeError("resolved window-site universe is not 124 unique sites")
    writer_set = set(writers)
    window_set = set(window_sites)
    if not writer_set <= window_set:
        raise FreezeError("58 KNOWN_WRITERS are not a subset of the 124 resolved window sites")
    combined = writer_set | window_set | set(ROOT_KEYS)
    return {
        "definition": ("58 source-pinned KNOWN_WRITERS, all 124 resolved window-touching "
                       "instruction sites, and four closure-root entries"),
        "known_writer_count": 58,
        "known_writer_ids": writers,
        "window_site_count": 124,
        "window_site_ids": sorted(window_set),
        "closure_root_count": 4,
        "closure_root_ids": list(ROOT_KEYS),
        "combined_unique_image_pc_count": len(combined),
        "combined_ids": sorted(combined),
    }


def _writer_cone_candidates(index: dict, sites: list[dict], writers: list[str]) -> dict:
    """Traverse pinned static-index edges without decoding instructions in Python.

    Resident direct transfers may enter any overlay record at the named address;
    overlay transfers may enter their own image or resident code.  This is a
    conservative coexistence expansion.  Complete resident jr target maps are
    included, while unresolved indirect transfers add no invented edges.
    """
    records: dict[tuple[str, int], dict] = {}
    for row in index["records"]:
        if row.get("range_type") not in {"code", "thunk"}:
            continue
        lo, hi = _record_extent(row)
        records[(row["image_id"], lo)] = {"row": row, "lo": lo, "hi": hi}

    def resolve(source_image: str, target: int) -> set[tuple[str, int]]:
        found = set()
        for key, wrapped in records.items():
            target_image = key[0]
            if not wrapped["lo"] <= target < wrapped["hi"]:
                continue
            if (source_image == "SCUS_942_88"
                    or target_image in {source_image, "SCUS_942_88"}):
                found.add(key)
        return found

    edges: dict[tuple[str, int], set[tuple[str, int]]] = defaultdict(set)
    for key, wrapped in records.items():
        row = wrapped["row"]
        for transfer in (row.get("direct_calls") or []) + (row.get("direct_jumps") or []):
            edges[key].update(resolve(key[0], _int(transfer["target"])))
    complete_targets: dict[int, set[int]] = defaultdict(set)
    for field in ("indirect_jump_targets", "indirect_jump_targets_from_gate"):
        for pc, targets in ((index.get(field) or {}).get("site_targets") or {}).items():
            complete_targets[_int(pc)].update(_int(target) for target in targets)
    for pc, targets in complete_targets.items():
        owners = [
            key for key, wrapped in records.items()
            if key[0] == "SCUS_942_88" and wrapped["lo"] <= pc < wrapped["hi"]
        ]
        for owner in owners:
            for target in targets:
                edges[owner].update(resolve(owner[0], target))

    writer_nodes = set()
    for writer in writers:
        image, pc_text = writer.split(":")
        pc = int(pc_text, 16)
        writer_nodes.update(
            key for key, wrapped in records.items()
            if key[0] == image and wrapped["lo"] <= pc < wrapped["hi"])
    if not writer_nodes:
        raise FreezeError("no KNOWN_WRITERS map into static-index code records")

    rows = []
    for site in sites:
        if site["image"] != "SCUS_942_88":
            continue
        pc = _int(site["pc"])
        starts = {
            key for key, wrapped in records.items()
            if key[0] == "SCUS_942_88" and wrapped["lo"] <= pc < wrapped["hi"]
        }
        seen = set(starts)
        queue = deque(starts)
        while queue:
            node = queue.popleft()
            for nxt in edges[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        hits = seen & writer_nodes
        if hits:
            rows.append({
                "site": site["id"],
                "reachable_known_writer_owner_nodes": [
                    f"{image}:0x{entry:08x}" for image, entry in sorted(hits)
                ],
            })
    return {
        "edge_basis": "pinned direct_calls/direct_jumps plus complete resident proved-jr maps",
        "coexistence_rule": "resident-to-any-image; overlay-to-same-image-or-resident",
        "unresolved_indirect_edges_invented": False,
        "candidate_count": len(rows),
        "candidates": rows,
    }


def _verify_freeze_note(expected_pilot: list[str], histogram: dict[str, int]) -> bytes:
    raw = EXPERIMENT.read_bytes()
    text = raw.decode("utf-8")
    if FREEZE_MARKER not in text:
        raise FreezeError(f"experiment log lacks marker: {FREEZE_MARKER}")
    section = text.split(FREEZE_MARKER, 1)[1].split("\n## ", 1)[0]
    listed = re.findall(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|", section)
    if listed != expected_pilot:
        raise FreezeError(f"experiment freeze pilot differs: {listed!r}")
    for name, count in histogram.items():
        if f"`{name}` = **{count}**" not in section:
            raise FreezeError(f"experiment freeze lacks histogram count {name}={count}")
    required = (
        "No Stage-2 target-domain proof",
        "No exclusion/disjointness outcome",
        "No GO/NO-GO decision",
    )
    if any(phrase not in section for phrase in required):
        raise FreezeError("experiment freeze does not explicitly exclude outcomes")
    # Pin only this immutable section.  Stage-2 is required to append its
    # outcome to the same experiment log after the freeze commit; hashing the
    # whole file here would make that legitimate append invalidate Stage 0/1.
    return (FREEZE_MARKER + section.rstrip() + "\n").encode("utf-8")


def build() -> dict:
    _verify_ancestry()
    index, index_raw = _git_json(SPEC_COMMIT, INDEX)
    predecessor, predecessor_raw = _git_json(SPEC_COMMIT, PREDECESSOR)
    caller, caller_raw = _git_json(SPEC_COMMIT, CALLER_PILOT)
    resolve, resolve_raw = _git_json(SPEC_COMMIT, FRONTIER_RESOLVE)
    frontier, frontier_raw = _git_json(SPEC_COMMIT, FRONTIER_RESULT)
    capsules, capsules_raw = _git_json(SPEC_COMMIT, CAPSULES)
    work_raw = _git_show(SPEC_COMMIT, WORK_ORDER)
    erratum_raw = _git_show(SPEC_COMMIT, ERRATUM)
    writer_source_raw = _git_show(SPEC_COMMIT, KNOWN_WRITER_SOURCE)
    shared_c_raw = _git_show(SPEC_COMMIT, SHARED_C)
    stage1_c_raw = STAGE1_C.read_bytes()

    if predecessor.get("decision", {}).get("verdict") != "NO-GO":
        raise FreezeError("authoritative predecessor is not the accepted NO-GO")
    if "relevant_unproved_indirect_edges[0]" not in json.dumps(
            predecessor.get("prior_receipt_witness_semantics")):
        raise FreezeError("predecessor witness semantics/erratum are not present")
    if caller.get("decision", {}).get("verdict") != "NO-GO":
        raise FreezeError("caller-domain predecessor is not NO-GO")

    sites, movement = _derive_union(predecessor, index)
    image_map, image_identities = _verify_images(index)
    owners = {site["id"]: _owner_for_site(index, site) for site in sites}
    writers = _known_writers(writer_source_raw)
    protected = _protected_set(resolve, writers)

    guarded_rows = predecessor["stage_b_pilot"].get("guarded_table_proofs") or []
    guarded = {
        f"{row['site']}:jr:v0": row for row in guarded_rows
        if row.get("status") == "PROVED_LOCAL_ADDRESS_DOMAIN"
    }

    with tempfile.TemporaryDirectory(prefix="phase4-target-exclusion-freeze-") as temp_text:
        temp = Path(temp_text)
        map_path = temp / "images.txt"
        map_path.write_bytes(image_map)
        stage1_bin = temp / "stage1"
        stage1_binary = _compile(STAGE1_C, stage1_bin)
        stage1_selftest = _run_json([str(stage1_bin), "--self-test"])
        if stage1_selftest != {
                "tool": "phase4_target_exclusion_stage1", "passed": 6,
                "total": 6, "verdict": True}:
            raise FreezeError(f"Stage1 C self-test drifted: {stage1_selftest!r}")
        byte_facts = _run_json(
            [str(stage1_bin), str(map_path), *[site["id"] for site in sites]])
        if byte_facts.get("site_count") != 179:
            raise FreezeError("Stage1 C did not attest all 179 sites")

        pinned_shared = temp / "phase4_typed_state_provenance.c"
        pinned_shared.write_bytes(shared_c_raw)
        shared_bin = temp / "shared_provenance"
        shared_binary = _compile(pinned_shared, shared_bin)
        shared_selftest_proc = _run([str(shared_bin), "--self-test"])
        selftest_lines = [line for line in shared_selftest_proc.stdout.splitlines() if line.strip()]
        if len(selftest_lines) != 41 or any(" ok " not in f" {line} " for line in selftest_lines):
            raise FreezeError("shared C self-test is not 41/41")
        queries = []
        for site in sites:
            owner = owners[site["id"]]
            queries.append(
                f"defsat@{site['image']}:{owner['entry']}:{owner['end']}:"
                f"{site['register']}:{site['pc']}")
        query_rows = []
        for start in range(0, len(queries), 48):
            result = _run_json(
                [str(shared_bin), str(map_path), *queries[start:start + 48]])
            query_rows.extend(result.get("queries") or [])
        if len(query_rows) != 179:
            raise FreezeError("shared C did not return all 179 reaching-definition queries")

    byte_by_id = {row["id"]: row for row in byte_facts["sites"]}
    if set(byte_by_id) != {site["id"] for site in sites}:
        raise FreezeError("Stage1 byte attestation ids differ from the corrected union")

    classified = []
    counts: Counter[str] = Counter()
    for site, query in zip(sites, query_rows):
        if (query.get("image") != site["image"]
                or _int(query.get("function")) != _int(owners[site["id"]]["entry"])
                or query.get("register") != site["register"]
                or query.get("targeted_sites") != 1):
            raise FreezeError(f"shared C query identity mismatch at {site['id']}")
        stratum, evidence = _classify(site, query, guarded.get(site["id"]))
        counts[stratum] += 1
        classified.append({
            **site,
            "owner": owners[site["id"]],
            "stratum": stratum,
            "classification_evidence": evidence,
            "instruction_evidence": byte_by_id[site["id"]],
            "reaching_definition_evidence": query,
        })
    histogram = {name: counts.get(name, 0) for name in STRATA}
    if sum(histogram.values()) != 179:
        raise FreezeError(f"stratum histogram does not cover union: {histogram!r}")

    writer_cones = _writer_cone_candidates(index, sites, writers)
    root_candidates = [site["id"] for site in sites if site["root_obligations"]]
    writer_candidates = [row["site"] for row in writer_cones["candidates"]]
    candidate_union = sorted(set(root_candidates) | set(writer_candidates), key=_site_sort)
    pilot = candidate_union[:12]
    if len(pilot) > 12:
        raise FreezeError("pilot exceeds 12 sites")
    pilot_rows = []
    class_by_id = {row["id"]: row for row in classified}
    writer_set = set(writer_candidates)
    for rank, site_id in enumerate(pilot, 1):
        row = class_by_id[site_id]
        pilot_rows.append({
            "rank": rank,
            "id": site_id,
            "stratum": row["stratum"],
            "root_obligations": row["root_obligations"],
            "writer_cone_candidate": site_id in writer_set,
        })
    experiment_raw = _verify_freeze_note(pilot, histogram)

    frontier_verdicts = frontier.get("verdicts") or {}
    if (frontier_verdicts.get("dimension_promoted") is not False
            or frontier_verdicts.get("item2_ready_for_review") is not False
            or frontier_verdicts.get("review_blockers") != [
                "IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"]):
        raise FreezeError("protected F01 verdict surface differs from accepted partial state")
    capsule_rows = capsules.get("capsules") or []
    if (capsules.get("complete") is not True or capsules.get("errors") != []
            or capsules.get("capsule_count") != 50 or len(capsule_rows) != 50
            or any(row.get("control_match") is not True for row in capsule_rows)):
        raise FreezeError("pinned 50-capsule universe is incomplete or divergent")

    return {
        "_comment": ("Mandatory Stage-0/1 pre-outcome freeze. This artifact contains "
                     "classification candidates only: no target-domain proof, exclusion "
                     "proof, runtime comparison outcome, or GO/NO-GO decision."),
        "schema": SCHEMA,
        "inputs": {
            "issued_baseline_commit": BASELINE_COMMIT,
            "erratum_commit": ERRATUM_COMMIT,
            "work_order_commit": SPEC_COMMIT,
            "derived_input_snapshot_commit": SPEC_COMMIT,
            "work_order": str(WORK_ORDER.relative_to(ROOT)),
            "work_order_sha256": _sha(work_raw),
            "erratum_source": str(ERRATUM.relative_to(ROOT)),
            "erratum_source_sha256": _sha(erratum_raw),
            "predecessor_receipt": str(PREDECESSOR.relative_to(ROOT)),
            "predecessor_receipt_sha256": _sha(predecessor_raw),
            "caller_pilot_sha256": _sha(caller_raw),
            "static_index_sha256": _sha(index_raw),
            "frontier_resolve_sha256": _sha(resolve_raw),
            "frontier_result_sha256": _sha(frontier_raw),
            "capsule_set_sha256": _sha(capsules_raw),
            "known_writer_source_sha256": _sha(writer_source_raw),
            "shared_C_snapshot_sha256": _sha(shared_c_raw),
            "stage1_C_sha256": _sha(stage1_c_raw),
            "experiment_pre_outcome_record_sha256": _sha(experiment_raw),
            "image_map_sha256": _sha(image_map),
            "image_identities": image_identities,
        },
        "c_controls": {
            "stage1_source": str(STAGE1_C.relative_to(ROOT)),
            "stage1_compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
            "stage1_binary_sha256": _sha(stage1_binary),
            "stage1_selftest": stage1_selftest,
            "shared_source": str(SHARED_C.relative_to(ROOT)),
            "shared_source_snapshot_commit": SPEC_COMMIT,
            "shared_compile_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
            "shared_binary_sha256": _sha(shared_binary),
            "shared_selftest": {
                "passed": 41, "total": 41, "verdict": True,
                "stdout_sha256": _sha(shared_selftest_proc.stdout.encode()),
            },
            "instruction_decoding_in_python": False,
        },
        "stage_0_union": {
            "universe_name": "corrected code-only unproved jr/jalr UNION across four predecessor supersets",
            "site_id_schema": "image:pc:kind:register",
            "movement": movement,
            "image_counts": dict(sorted(Counter(row["image"] for row in sites).items())),
        },
        "protected_set": protected,
        "stage_1_classification": {
            "universe_count": 179,
            "histogram": histogram,
            "proof_status": "CLASSIFICATION_ONLY_NOT_STAGE2_PROOF",
            "sites": classified,
        },
        "pilot_selection": {
            "selection_is_pre_outcome": True,
            "query": ("From the corrected per-root exact sets, select each union site with "
                      "one or more unresolved edge-to-root obligations; union SCUS sites "
                      "whose pinned static reachable cone contains a KNOWN_WRITERS owner; "
                      "sort by numeric pc, then image/id; take the first 12."),
            "root_candidate_semantics": ("membership in a predecessor root's corrected "
                                         "relevant_unproved_indirect_edges superset; an "
                                         "exclusion closes that site-to-root obligation, "
                                         "not the other root obligations"),
            "root_candidate_count": len(root_candidates),
            "root_candidate_ids": root_candidates,
            "writer_cone": writer_cones,
            "candidate_union_count": len(candidate_union),
            "candidate_union_ids": candidate_union,
            "truncation_limit": 12,
            "truncated_count": len(candidate_union) - len(pilot),
            "pilot_count": len(pilot),
            "pilot_ids": pilot,
            "pilot": pilot_rows,
        },
        "outcome_barrier": {
            "stage_2_target_domain_proofs_present": False,
            "stage_2_exclusion_proofs_present": False,
            "runtime_crosscheck_outcome_present": False,
            "go_no_go_decision_present": False,
            "f01_status_moved": False,
            "full_pass_authorized": False,
        },
        "protected_state": {
            "f01_status": "partial",
            "item_2": "not_met",
            "dimension_promoted": False,
            "item2_ready_for_review": False,
            "review_blockers": ["IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"],
            "mechanics_baseline_modified": False,
            "runtime_replay_performed": False,
            "instrumented_run_performed": False,
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
            print(f"target-exclusion freeze differs: {output}")
            return 1
        print(f"target-exclusion freeze current: {output}")
        return 0
    output.write_bytes(raw)
    print(f"wrote {output} ({len(raw)} bytes, sha256={_sha(raw)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
