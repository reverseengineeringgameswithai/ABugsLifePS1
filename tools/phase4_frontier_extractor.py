#!/usr/bin/env python3
"""Prepopulate a semantic-frontier query from the retained static index.

`tools/phase4_semantic_frontier.py` is a CHECKER: it validates a fully declared
Item-2 query and solves the affine access intersections.  Authoring that query by
hand is the step that has kept rows away from it -- the mechanical bulk already
exists in `analysis/phase4_static_frontier_index.json` and only needs projecting
into the checker's schema.

This tool does the mechanical half and REFUSES to invent the judgement half.

Identity
--------
Functions, edges and lookups are keyed by ``(image_id, entry)``, never by address
alone.  16 entry addresses in the index are shared by more than one overlay --
every level overlay entry sits at 0x800B39A4 -- so an address-keyed map silently
discards 42 of 1,190 records and can attribute an edge to the wrong image.  Ids
are emitted image-qualified for the same reason.

Callers
-------
Callers are recovered by inverting the whole call graph and are emitted as
ROOTS, not merely as declared functions.  The checker only credits
``consumer_categories`` for functions its walk reaches, so a caller that is not a
root contributes nothing; that is what left the ``callers`` category empty.

Mechanical blockers
-------------------
Two things a census cannot silently drop are preserved and reported:

* direct call edges whose target is outside the selected closure, and
* every access whose effective address is not statically decidable.

Both land in ``mechanical_blockers``.  While any are present the summary reports
``mechanically_complete: false``: the emitted query describes only the resolvable
subset, so an ``item2_ready`` verdict on it would understate the frontier.

Determinism
-----------
The summary binds the exact seed and index bytes it was produced from, and
``--check`` re-derives both outputs and fails if the retained bytes drift.

Usage
  tools/phase4_frontier_extractor.py SEED.yaml --output config/QUERY.yaml \
      --summary analysis/EXTRACTION.json [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "analysis/phase4_static_frontier_index.json"
QUERY_SCHEMA = "abl-phase4-semantic-frontier-query/2"
SEED_SCHEMA = "abl-phase4-frontier-seed/1"
SUMMARY_SCHEMA = "abl-phase4-frontier-extraction/2"
CENSUS_SCHEMA = "abl-phase4-frontier-static-census/1"
GATE_SCHEMA = "phase4-static-asm-prerequisites/1"
GP_VALUE = 0x80081D98

REQUIRED_CATEGORIES = ("callers", "callees", "callbacks", "indirect_tables",
                       "overlays", "readers", "writers", "downstream_consumers")
AUTHORITY = {
    "changes_campaign_registry": False,
    "promotes_dimension": False,
    "runtime_silence_proves_absence": False,
    "frame_capsule_proves_exact_causality": False,
    "unknown_is_disjoint": False,
    "fresh_verifier_required": True,
}
ACCESS_KIND = {"read": "read", "write": "write", "read_write": "read_write"}


class ExtractError(RuntimeError):
    """Extraction failed closed."""


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text, 16 if text.lower().startswith("0x") else 10)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_index() -> tuple[dict[str, Any], str]:
    if not INDEX_PATH.is_file():
        raise ExtractError(f"missing static index: {INDEX_PATH}")
    raw = INDEX_PATH.read_bytes()
    index = json.loads(raw)
    if not index.get("valid"):
        raise ExtractError("static index reports valid=false; regenerate it first")
    if index.get("errors"):
        raise ExtractError(f"static index carries {len(index['errors'])} errors")
    return index, _sha256_bytes(raw)


def load_seed(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    seed = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(seed, dict) or seed.get("schema") != SEED_SCHEMA:
        raise ExtractError(f"seed must use {SEED_SCHEMA}")
    missing = {"target", "roots", "windows", "categories", "boundary_owners",
               "residuals", "evidence_receipts"} - set(seed)
    if missing:
        raise ExtractError(f"seed is missing required sections: {sorted(missing)}")
    if not seed["roots"]:
        raise ExtractError("seed.roots must be non-empty")
    if not seed["windows"]:
        raise ExtractError("seed.windows must be non-empty")
    if {c["id"] for c in seed["categories"]} != set(REQUIRED_CATEGORIES):
        raise ExtractError("seed.categories must dispose of every Item-2 category exactly once")
    for root in seed["roots"]:
        if not isinstance(root, dict) or set(root) != {"image", "entry"}:
            raise ExtractError("each seed.roots entry must be {image, entry} -- an address "
                               "alone is ambiguous across overlays")
    if "census_complete" in seed:
        raise ExtractError(
            "seed.census_complete is no longer accepted: per-image census completeness "
            "is DERIVED from the static-census receipt, because a seed that simply "
            "asserts it left twenty of twenty-one images false by default with nobody "
            "having decided them")
    return seed, _sha256_bytes(raw)


def load_receipt(seed: dict[str, Any], name: str, schema: str) -> dict[str, Any]:
    """Load an evidence receipt the seed pins by path AND sha256.

    The extractor's attestation covers the seed, so a receipt the seed pins by
    hash is transitively attested: swapping the receipt changes its hash, the
    hash check fails here, and the query cannot regenerate.  Pinning it anywhere
    else would let the receipt drift underneath a query that still validates.
    """
    receipts = seed.get("evidence_receipts") or {}
    entry = receipts.get(name)
    if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
        raise ExtractError(
            f"seed.evidence_receipts.{name} must be {{path, sha256}}")
    relative = Path(str(entry["path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise ExtractError(f"evidence_receipts.{name}.path must be repo-relative")
    source = ROOT / relative
    if not source.is_file():
        raise ExtractError(f"evidence receipt missing: {entry['path']}")
    raw = source.read_bytes()
    if _sha256_bytes(raw) != entry["sha256"]:
        raise ExtractError(
            f"evidence_receipts.{name}.sha256 does not match {entry['path']}")
    document = json.loads(raw)
    if document.get("schema") != schema:
        raise ExtractError(f"{entry['path']} must use {schema}")
    return document


def resolve_access(access: dict[str, Any]) -> int | None:
    """Effective address when statically decidable, else None (an UNKNOWN)."""
    if access.get("address"):
        try:
            return _int(access["address"])
        except (TypeError, ValueError):
            return None
    if access.get("base_register") == "gp":
        return (GP_VALUE + int(access.get("offset", 0))) & 0xFFFFFFFF
    return None


def _image_extent(image: dict[str, Any]) -> tuple[int, int]:
    base = _int(image["file_va_base"])
    return base, base + int(image["expected_size"])


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def _query_digest(query: dict[str, Any]) -> str:
    """Digest of everything except `attested_by` itself.

    Excluding only the attestation -- not the whole mechanical_completeness block
    -- means the ledger path, ledger hash, completeness flag and blocker counts
    are all COVERED, so none of them can be swapped after the fact.
    """
    stripped = {k: v for k, v in query.items() if k != "mechanical_completeness"}
    mechanical = {k: v for k, v in query["mechanical_completeness"].items()
                  if k != "attested_by"}
    stripped["mechanical_completeness"] = mechanical
    return _sha256_bytes(_canonical(stripped))


def _render_query(query: dict[str, Any]) -> bytes:
    return yaml.safe_dump(query, sort_keys=False, width=100,
                          default_flow_style=False).encode("utf-8")


def _render_summary(summary: dict[str, Any]) -> bytes:
    return (json.dumps(summary, indent=1, sort_keys=True) + "\n").encode("utf-8")


LOAD_OPS = {0x20: ("lb", 1, "read"), 0x21: ("lh", 2, "read"), 0x23: ("lw", 4, "read"),
            0x24: ("lbu", 1, "read"), 0x25: ("lhu", 2, "read")}
STORE_OPS = {0x28: ("sb", 1, "write"), 0x29: ("sh", 2, "write"), 0x2b: ("sw", 4, "write")}


def binary_supplement(image_path: Path, base: int, skip: int,
                      windows: list[tuple[int, int]],
                      gp: int = GP_VALUE) -> list[dict]:
    """Independently prove window accesses straight from the image bytes.

    The static index only records accesses inside CFG-reachable blocks, so a
    function whose CFG it could not recover contributes nothing -- that is how
    nine already-known F01 accesses went missing. A linear scan does not depend
    on reachability.

    This is a POSITIVE-ONLY finder. It reports sites whose base it can prove --
    a $gp displacement, or a lui in the IMMEDIATELY PRECEDING word (enforced) -- and says
    nothing about the sites it walks past. It is not a census and its silence is
    not evidence. The unanalysed-extent ledger, not this function, is what
    accounts for regions whose accesses nobody has decided.
    """
    data = image_path.read_bytes()[skip:]
    words = len(data) // 4
    proven: list[dict] = []
    hi: dict[int, tuple[int, int]] = {}   # register -> (value, defining pc)
    for i in range(words):
        pc = base + i * 4
        word = int.from_bytes(data[i * 4:i * 4 + 4], "little")
        op, rs, rt = word >> 26, (word >> 21) & 31, (word >> 16) & 31
        simm = (word & 0xFFFF) - (0x10000 if word & 0x8000 else 0)
        if op == 0x0F:                      # lui
            hi[rt] = ((word & 0xFFFF) << 16, pc)
            continue
        spec = LOAD_OPS.get(op) or STORE_OPS.get(op)
        effective = provenance = None
        if spec is not None:
            if rs == 28:                    # $gp-relative: proven constant
                effective, provenance = (gp + simm) & 0xFFFFFFFF, "gp_relative"
            elif rs in hi and hi[rs][1] == pc - 4:
                # ADJACENCY IS REQUIRED. Tracking clobbers across a gap means
                # modelling every GPR write -- jalr, mfc0 and lwl all defeated an
                # earlier attempt. Requiring the lui in the immediately preceding
                # word needs no such model and is what the docstring promises.
                # Every non-$gp positive on the retained F01 frontier already
                # satisfies it, so this costs nothing and removes a whole class
                # of false proofs.
                effective, provenance = ((hi[rs][0] + simm) & 0xFFFFFFFF,
                                         f"lui@{hi[rs][1]:#010x}")

        # Kill pending lui state AFTER the access is evaluated: the standard
        # idiom `lui v0,X / lh v0,ofs(v0)` has rs == rt, so clobbering first
        # would discard the very base being used. Without any kill,
        # `lui at,X / addiu at,zero,0 / sh ...,ofs(at)` would be mis-reported.
        if op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E) or op in LOAD_OPS:
            hi.pop(rt, None)
        elif op == 0x00:
            hi.pop((word >> 11) & 31, None)   # SPECIAL writes rd
        elif op == 0x03:                      # jal clobbers the caller-saved set
            for reg in list(hi):
                if reg in (1, 2, 3) or 4 <= reg <= 15 or reg in (24, 25, 31):
                    hi.pop(reg, None)
        elif op == 0x02:                      # unconditional j: new basic block
            hi.clear()

        if spec is None or effective is None:
            continue
        mnemonic, width, kind = spec
        if not any(low <= effective < high for low, high in windows):
            continue
        row = {"pc": pc, "address": effective, "mnemonic": mnemonic, "width": width,
               "kind": kind, "provenance": provenance}
        proven.append(row)
    return proven


def extract(seed: dict[str, Any], index: dict[str, Any], census: dict[str, Any],
            gate: dict[str, Any], seed_sha: str,
            index_sha: str) -> tuple[dict[str, Any], dict[str, Any]]:
    images = {i["image_id"]: i for i in index["images"]}
    extents = {iid: _image_extent(i) for iid, i in images.items()}
    resident = next((iid for iid in images if iid.startswith("SCUS")), None)
    if resident is None:
        raise ExtractError("no resident image in the static index")

    # ---- (image, entry) keyed record map: address alone collides ------------
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for record in index["records"]:
        if not record.get("entry"):
            continue
        records[(record["image_id"], _int(record["entry"]))] = record

    def resolve_target(source_image: str, target: Any) -> tuple[str, int] | None:
        """An address resolves inside its own image first, then the resident one."""
        address = _int(target)
        for candidate in (source_image, resident):
            low, high = extents[candidate]
            if low <= address < high and (candidate, address) in records:
                return (candidate, address)
        return None

    # A jump often lands INSIDE a function, not on its entry, so jump targets
    # must resolve by containing extent -- resolving by entry alone reports zero
    # incoming jumps even where they demonstrably exist.
    extents_by_image: dict[str, list[tuple[int, int, tuple[str, int]]]] = {}
    for key, record in records.items():
        extents_by_image.setdefault(key[0], []).append(
            (_int(record["entry"]), _int(record["end"]), key))
    for rows in extents_by_image.values():
        rows.sort()

    def resolve_containing(source_image: str, target: Any) -> tuple[str, int] | None:
        address = _int(target)
        for candidate in (source_image, resident):
            for low, high, key in extents_by_image.get(candidate, ()):
                if low <= address < high:
                    return key
        return None

    # ---- inverted call graph, over qualified keys ---------------------------
    callers: dict[tuple[str, int], set[tuple[str, int]]] = {}
    for key, record in records.items():
        for edge in record.get("direct_calls") or []:
            target = resolve_target(key[0], edge["target"])
            if target is not None:
                callers.setdefault(target, set()).add(key)

    # ---- the shared static-ASM gate's typed indirect inventory --------------
    # Resident-only by construction, so its scope is carried on every row it
    # touches rather than left for a reader to assume.
    gate_resident = gate["scope"]["image"]
    gate_jr: dict[tuple[str, int], dict[str, Any]] = {}
    gate_jalr: dict[tuple[str, int], dict[str, Any]] = {}
    for row in gate["indirect_control"]["jr_sites"]:
        resolution = row.get("resolution") or {}
        gate_jr[(gate_resident, _int(row["pc"]))] = {
            "complete": bool(resolution.get("target_set_complete")),
            "count": resolution.get("count")}
    for row in gate["indirect_control"]["jalr_sites"]:
        gate_jalr[(gate_resident, _int(row["pc"]))] = {
            "complete": bool(row.get("target_set_complete")), "count": None}

    windows_early = [(_int(w["start"]), _int(w["end"])) for w in seed["windows"]]

    def hits_window(record: dict[str, Any]) -> bool:
        for access in record.get("memory_accesses") or []:
            effective = resolve_access(access)
            if effective is not None and any(lo <= effective < hi for lo, hi in windows_early):
                return True
        return False

    # Reachability from a chosen root has NOTHING to do with whether code touches
    # the window. Scan the entire image universe for resolved intersections and
    # seed every hit-bearing function as a root before expanding the graph.
    access_seeded = {key for key, record in records.items() if hits_window(record)}
    universe_hits = [
        (key, str(access["pc"]).lower())
        for key, record in records.items()
        for access in (record.get("memory_accesses") or [])
        if (lambda e: e is not None and any(lo <= e < hi for lo, hi in windows_early))(
            resolve_access(access))]

    roots: list[tuple[str, int]] = []
    for root in seed["roots"]:
        key = (str(root["image"]), _int(root["entry"]))
        if key not in records:
            raise ExtractError(f"root {key[0]}:{key[1]:#x} is not present in the static index")
        roots.append(key)

    # ---- callback surface, from the derived function-pointer census ---------
    # A function whose address is registered somewhere is reachable through that
    # registration, so it is seeded exactly like an access hit: the closure must
    # not depend on someone remembering to name it.
    callback_groups: list[dict[str, Any]] = []
    callback_seeded: set[tuple[str, int]] = set()
    for group in census["function_pointer_census"]["registration_groups"]:
        targets: list[tuple[str, int]] = []
        for target in group["targets"]:
            image_id, address = target.split(":")
            key = (image_id, _int(address))
            if key not in records:
                raise ExtractError(
                    f"callback census names an unindexed function {target}")
            targets.append(key)
            callback_seeded.add(key)
        callback_groups.append({"id": group["id"], "consumer": group["consumer"],
                                "sites": group["sites"], "target_keys": targets})

    # ---- target-root islands: seeded, never silently out of scope ----------
    # An island's only established entry is a PROVED indirect-jump target, so
    # the callee closure structurally cannot reach it -- no direct call names
    # it. Leaving it out kept its register-based stores invisible to this
    # ledger, which is the fail-open direction: an undecided store nobody can
    # see is indistinguishable from a decided one. Islands are therefore seeded
    # like access and callback hits, and their undecided accesses land in
    # `unresolved_accesses` where they belong.
    #
    # ⚠️ DECLARED SCOPE: this seeding is WHOLE-IMAGE, not row-relevant -- every
    # island in the index joins every extraction's closure, making the closure
    # a conservative SUPERSET of the row's reachable surface. With one island
    # that is exact in practice (it falls through into vm_motion_apply_chase,
    # a closure member, so it is connected to this frontier by real control
    # flow in both directions), but a future unrelated island would inflate a
    # row's residual rather than hide from it. If that starts costing real
    # blocker counts, replace this with seeding through proved row-relevant
    # control-flow edges; until then the superset direction is the safe one
    # and is declared in the summary rather than left for a reader to infer.
    island_seeded = {key for key, record in records.items()
                     if record.get("source") == "target_root_island"}

    # ---- callee closure, then one caller layer -----------------------------
    closure: set[tuple[str, int]] = set()
    queue = (list(roots) + sorted(access_seeded) + sorted(callback_seeded)
             + sorted(island_seeded))
    while queue:
        key = queue.pop()
        if key in closure:
            continue
        closure.add(key)
        for edge in records[key].get("direct_calls") or []:
            target = resolve_target(key[0], edge["target"])
            if target is not None:
                queue.append(target)
    caller_keys = {c for k in closure for c in callers.get(k, set())} - closure
    selected = closure | caller_keys
    # The caller surface is ONE layer deep by construction. The next layer is not
    # silently dropped: every incoming edge from outside `selected` is retained.
    omitted_incoming_callers = sorted(
        {(caller, target) for target in selected
         for caller in callers.get(target, set()) if caller not in selected})

    # Jump edges are a whole class the closure ignores. They are NOT solved here
    # (general jump-table recovery is deliberately out of scope); they are
    # accounted for so no source category can disappear silently.
    jumps_out, incoming_jumps, indirect_jumps, unanalysed = [], [], [], []
    for key, record in records.items():
        inside = key in selected
        for edge in record.get("direct_jumps") or []:
            target = resolve_containing(key[0], edge.get("target"))
            if inside and (target is None or target not in selected):
                jumps_out.append({
                    "id": f"direct_jump_out:{key[0]}:{key[1]:#010x}@{edge.get('pc')}",
                    "function": f"{key[0]}:{key[1]:#010x}", "site": str(edge.get("pc")),
                    "target": str(edge.get("target")),
                    "resolved": target is not None})
            elif not inside and target is not None and target in selected:
                incoming_jumps.append({
                    "id": f"incoming_jump:{key[0]}:{key[1]:#010x}@{edge.get('pc')}",
                    "from_function": f"{key[0]}:{key[1]:#010x}", "site": str(edge.get("pc")),
                    "into": f"{target[0]}:{target[1]:#010x}"})
        # Unanalysed extents are recorded for EVERY record, not only selected
        # ones: an extent the index could not analyse may contain accesses to the
        # windows regardless of whether its function is in the closure.
        unreachable = int(record.get("unreachable_instruction_count") or 0)
        if unreachable:
            unanalysed.append({
                "id": f"unanalysed_extent:{key[0]}:{key[1]:#010x}",
                "function": f"{key[0]}:{key[1]:#010x}",
                "selected": inside,
                "analysed_instructions": int(record.get("instruction_count") or 0),
                "unreachable_instructions": unreachable,
                "extent_instructions": int(record.get("extent_instruction_count") or 0),
                "meaning": ("the static index recovered no CFG for this extent, so its "
                            "accesses and edges are absent from the index entirely")})
        if inside:
            for edge in record.get("indirect_jumps") or []:
                site = _int(edge.get("pc"))
                gate = gate_jr.get((key[0], site))
                indirect_jumps.append({
                    "id": f"indirect_jump:{key[0]}:{key[1]:#010x}@{edge.get('pc')}",
                    "function": f"{key[0]}:{key[1]:#010x}", "site": str(edge.get("pc")),
                    # Annotated from the shared static-ASM gate, never resolved
                    # here.  A row whose target set the gate DOES bound is still
                    # retained as a blocker: bounding the targets is not the same
                    # as disposing of where they go.
                    "gate_scope": "resident_only" if key[0] == gate_resident else "out_of_gate_scope",
                    "gate_target_set_complete": bool(gate and gate["complete"]),
                    "gate_target_count": (gate or {}).get("count")})


    windows = [{"id": w["id"], "start": _int(w["start"]), "end": _int(w["end"])}
               for w in seed["windows"]]

    def fid(key: tuple[str, int]) -> str:
        name = records[key].get("name") or "fn"
        return f"{key[0]}:{name}@{key[1]:#010x}"

    overrides: dict[tuple[str, int], list[str]] = {}
    for row in seed.get("consumer_category_overrides") or []:
        key = (str(row["image"]), _int(row["entry"]))
        if key not in records:
            raise ExtractError(f"consumer_category_overrides names an unindexed function {key}")
        bad = [c for c in row["categories"] if c not in REQUIRED_CATEGORIES]
        if bad:
            raise ExtractError(f"consumer_category_overrides has invalid categories {bad}")
        overrides[key] = list(row["categories"])
    unused_overrides = sorted(f"{k[0]}:{k[1]:#010x}" for k in overrides if k not in selected)

    # ---- binary supplement: proven accesses the index's CFG never saw --------
    binary_proven: dict[tuple[str, int], dict[str, Any]] = {}
    binary_unscanned: list[dict[str, Any]] = []
    images_scanned: list[str] = []
    win_pairs = [(w["start"], w["end"]) for w in windows]
    for image_id, image in images.items():
        path = ROOT / image["path"]
        if not path.is_file():
            binary_unscanned.append({
                "id": f"binary_scan_unscanned:{image_id}",
                "image": image_id, "reason": "image file absent; not scanned"})
            continue
        raw = path.read_bytes()
        if len(raw) != int(image["expected_size"]):
            binary_unscanned.append({
                "id": f"binary_scan_unscanned:{image_id}", "image": image_id,
                "reason": f"size {len(raw)} != expected {image['expected_size']}"})
            continue
        if _sha256_bytes(raw) != image["expected_sha256"]:
            binary_unscanned.append({
                "id": f"binary_scan_unscanned:{image_id}", "image": image_id,
                "reason": "sha256 does not match the index's pinned hash"})
            continue
        images_scanned.append(image_id)
        for row in binary_supplement(path, _int(image["file_va_base"]), 0, win_pairs):
            binary_proven[(image_id, row["pc"])] = dict(row, image=image_id)

    functions: list[dict[str, Any]] = []
    accesses: list[dict[str, Any]] = []
    tables: dict[str, dict[str, Any]] = {}
    omitted_edges: list[dict[str, Any]] = []
    unresolvable_edges: list[dict[str, Any]] = []
    unresolved_accesses: list[dict[str, Any]] = []
    resolved_outside = 0

    for key in sorted(selected):
        record = records[key]
        this_id = fid(key)
        direct = []
        for edge in record.get("direct_calls") or []:
            target = resolve_target(key[0], edge["target"])
            if target is None:
                unresolvable_edges.append({"function": this_id, "site": str(edge["pc"]),
                                           "target": str(edge["target"]),
                                           "reason": "target address matches no indexed record"})
                continue
            if target not in selected:
                omitted_edges.append({"function": this_id, "site": str(edge["pc"]),
                                      "target": f"{target[0]}:{target[1]:#010x}",
                                      "reason": "callee outside the selected closure"})
                continue
            direct.append({"site": _int(edge["pc"]), "target": fid(target)})
        indirect = []
        for edge in record.get("indirect_calls") or []:
            table_id = f"indirect_{key[0]}_{_int(edge['pc']):#010x}"
            tables[table_id] = {
                "id": table_id, "targets": [], "complete": False,
                "evidence": (f"Indirect call site {edge['pc']} in {this_id}; target set NOT "
                             "enumerated by extraction. Enumerate it, or hand it to a "
                             "boundary owner."),
            }
            indirect.append({"site": _int(edge["pc"]), "table": table_id})
        categories = overrides.get(key) or (
            ["callers"] if key in caller_keys else ["callees"])
        functions.append({
            "id": this_id, "image": key[0],
            "start": _int(record["entry"]), "end": _int(record["end"]),
            "direct_calls": direct, "indirect_calls": indirect,
            "consumer_categories": categories,
        })

        for access in record.get("memory_accesses") or []:
            effective = resolve_access(access)
            if effective is None:
                unresolved_accesses.append({
                    "function": this_id, "pc": str(access.get("pc")),
                    "base_register": access.get("base_register"),
                    "offset": access.get("offset"), "mnemonic": access.get("mnemonic")})
                continue
            hit = next((w for w in windows if w["start"] <= effective < w["end"]), None)
            if hit is None:
                resolved_outside += 1
                continue
            accesses.append({
                "id": f"{this_id}_{_int(access['pc']):#010x}", "image": key[0],
                "pc": _int(access["pc"]),
                "kind": ACCESS_KIND.get(access.get("access") or "", "read"),
                "width": int(access.get("width") or 4),
                # A resolved access is a SINGLE address: a one-element bounded
                # index. index=null reads as an unbounded domain and makes every
                # access "unknown".
                "expression": {
                    "base": effective, "offset": 0, "scale": 1,
                    "index": {"minimum": 0, "maximum_exclusive": 1,
                              "congruence_modulus": None, "congruence_remainder": None,
                              "signedness": "unsigned",
                              "evidence": "statically resolved single effective address"},
                    "arithmetic": "no_wrap"},
                "evidence": (f"static index memory_access at {access['pc']} in {this_id}; "
                             f"base_register={access.get('base_register')} "
                             f"offset={access.get('offset')}"),
            })

    # UNION: emitted = CFG-index accesses  U  independently proven binary-scan
    emitted_keys = {(a["image"], a["pc"]) for a in accesses}
    index_only = len(accesses)
    for key, row in sorted(binary_proven.items()):
        if key in emitted_keys:
            continue
        image_id, pc = key
        accesses.append({
            "id": f"binaryscan:{image_id}:{pc:#010x}", "image": image_id, "pc": pc,
            "kind": row["kind"], "width": row["width"],
            "expression": {
                "base": row["address"], "offset": 0, "scale": 1,
                "index": {"minimum": 0, "maximum_exclusive": 1,
                          "congruence_modulus": None, "congruence_remainder": None,
                          "signedness": "unsigned",
                          "evidence": "statically resolved single effective address"},
                "arithmetic": "no_wrap"},
            "evidence": (f"independent binary scan of {image_id} at {pc:#010x}: "
                         f"{row['mnemonic']} with base proven by {row['provenance']}; "
                         "this site is NOT present in the static index's CFG-reachable set"),
        })
    binary_supplied = len(accesses) - index_only
    universe_union = {(k[0], _int(pc)) for k, pc in universe_hits} | set(binary_proven)
    unemitted = len(universe_union - {(a["image"], a["pc"]) for a in accesses})

    # ---- boundary owners: an owner must name an edge that EXISTS ------------
    # Every direct-call edge this extractor emits targets a function inside the
    # query, so the only edge identity a boundary owner could ever match is one
    # emitted with an out-of-universe target -- of which there are none.  The
    # retained seed nonetheless carried two owners keyed by CATEGORY NAMES
    # ("unresolved_register_based_accesses"), strings no edge identity can equal.
    # They were structurally unusable and lit UNUSED_BOUNDARY_OWNER forever.
    # Rejecting an owner whose edge is not emitted makes that class impossible
    # rather than merely fixed once.
    emitted_boundary_edges = {
        f"{function['id']}@0x{edge['site']:08X}->{edge['target']}"
        for function in functions for edge in function["direct_calls"]
        if edge["target"] not in {row["id"] for row in functions}}
    boundary_owners = list(seed["boundary_owners"])
    unmatched_owners = [row["edge"] for row in boundary_owners
                        if row["edge"] not in emitted_boundary_edges]
    if unmatched_owners:
        raise ExtractError(
            f"boundary_owners name edges this query does not emit: {unmatched_owners}. "
            "A boundary owner is keyed by an EDGE IDENTITY (source@0xSITE->target); "
            "a category name can never match one, so such an entry can only ever be "
            "reported as unused.")

    # ---- callbacks: derived groups, deliberately INCOMPLETE ----------------
    # The census that produced these is positive-only, so every group says so.
    # An incomplete group is an enumerated UNKNOWN in the checker's graph, which
    # is the honest shape: the registration SITES are enumerated, the target SET
    # is not bounded.
    callbacks: list[dict[str, Any]] = []
    for group in callback_groups:
        callbacks.append({
            "id": group["id"],
            "targets": [fid(key) for key in sorted(set(group["target_keys"]))],
            "complete": False,
            "evidence": (
                f"{len(group['sites'])} registration site(s) at "
                f"{', '.join(group['sites'])} recovered by "
                "tools/phase4_callback_probe.c and retained in "
                "analysis/phase4_frontier_static_census.json. The probe is "
                "POSITIVE-ONLY -- it follows a code address only from an adjacent "
                "lui/addiu or lui/ori pair, inside one basic block, across the "
                "delay slot -- so the target set is NOT bounded and this group "
                "stays incomplete."),
        })

    # ---- residual coverage: GENERATED, never hand-typed ---------------------
    # The retained seed listed each residual's `covered_ids` by hand, and every
    # one of them named the residual itself rather than a boundary the checker
    # emits -- so the 58 real unknowns stayed uncovered while the coverage list
    # looked populated.  A hand-typed list of generated identities can only ever
    # be right by accident and go short by default.  The seed now declares a
    # RULE and the extractor expands it, then reconciles the union against the
    # exact set of unknowns the query will produce.  Aggregate agreement is not
    # accepted: the sets must be equal.
    unknown_ids: dict[str, str] = {}
    for function in functions:
        for edge in function["indirect_calls"]:
            if not tables[edge["table"]]["complete"]:
                unknown_ids[f"{function['id']}@0x{edge['site']:08X}->{edge['table']}"] = \
                    "indirect_call_tables"
    for group in callbacks:
        if not group["complete"]:
            unknown_ids[f"callback:{group['id']}"] = "incomplete_callbacks"
    for access in accesses:
        if access["expression"]["index"] is None:
            unknown_ids[access["id"]] = "unknown_accesses"

    residuals: list[dict[str, Any]] = []
    covered: dict[str, str] = {}
    for residual in seed["residuals"]:
        row = dict(residual)
        rules = row.pop("covers", None)
        if not isinstance(rules, list) or not rules:
            raise ExtractError(
                f"residual {row.get('id')!r} must declare a non-empty `covers` rule "
                "list; a hand-typed covered_ids list cannot track generated identities")
        unknown_rules = sorted(set(rules) - {"indirect_call_tables",
                                             "incomplete_callbacks",
                                             "unknown_accesses"})
        if unknown_rules:
            raise ExtractError(f"residual {row['id']!r} names unknown covers rules "
                               f"{unknown_rules}")
        row["covered_ids"] = sorted(identity for identity, rule in unknown_ids.items()
                                    if rule in rules)
        if not row["covered_ids"]:
            raise ExtractError(
                f"residual {row['id']!r} covers nothing: its rules {sorted(rules)} "
                "expand to an empty set, which is a declaration that can never be "
                "checked")
        for identity in row["covered_ids"]:
            if identity in covered:
                raise ExtractError(
                    f"{identity} is covered by both {covered[identity]} and {row['id']}")
            covered[identity] = row["id"]
        residuals.append(row)
    if set(covered) != set(unknown_ids):
        missing = sorted(set(unknown_ids) - set(covered))
        raise ExtractError(
            f"{len(missing)} emitted unknown(s) are covered by no residual, "
            f"starting with {missing[:3]}")

    # ---- indirect control: EXACT-SET reconciliation against the gate --------
    # ⚠️ Aggregate agreement is explicitly not sufficient here.  A wrong extent
    # set once passed this project's review on equal counts alone, so the sets
    # are differenced both ways and a site this frontier sees that the gate's
    # typed candidate universe does not is a hard failure, not a warning.
    query_calls = {(function["image"], edge["site"]) for function in functions
                   for edge in function["indirect_calls"]}
    ledger_jumps = {(row["function"].split(":")[0], _int(row["site"]))
                    for row in indirect_jumps}
    resident_calls = {key for key in query_calls if key[0] == gate_resident}
    resident_jumps = {key for key in ledger_jumps if key[0] == gate_resident}
    calls_outside_gate = sorted(resident_calls - set(gate_jalr))
    jumps_outside_gate = sorted(resident_jumps - set(gate_jr))
    if calls_outside_gate or jumps_outside_gate:
        raise ExtractError(
            "resident indirect sites absent from the gate's typed candidate universe: "
            f"calls {[f'{i}:{p:#010x}' for i, p in calls_outside_gate]} "
            f"jumps {[f'{i}:{p:#010x}' for i, p in jumps_outside_gate]}")
    indirect_reconciliation = {
        "gate_receipt": "analysis/phase4_static_asm_prerequisites.json",
        "gate_scope_image": gate_resident,
        "gate_typed_candidate_sites": len(gate_jr) + len(gate_jalr),
        "gate_jr_sites": len(gate_jr),
        "gate_jalr_sites": len(gate_jalr),
        "reconciliation": "exact_set_both_directions",
        "resident_indirect_call_sites_in_query": len(resident_calls),
        "resident_indirect_call_sites_absent_from_gate": [],
        "resident_indirect_jump_sites_in_ledger": len(resident_jumps),
        "resident_indirect_jump_sites_absent_from_gate": [],
        "gate_jalr_sites_outside_this_frontier": len(set(gate_jalr) - resident_calls),
        "gate_jr_sites_outside_this_frontier": len(set(gate_jr) - resident_jumps),
        # What the gate actually decides for this row, measured rather than assumed.
        "query_call_sites_with_a_gate_bounded_target_set": sum(
            1 for key in resident_calls if gate_jalr[key]["complete"]),
        "ledger_jump_sites_with_a_gate_bounded_target_set": sum(
            1 for key in resident_jumps if gate_jr[key]["complete"]),
        "out_of_gate_scope_sites": sorted(
            f"{image}:{pc:#010x}"
            for image, pc in (query_calls | ledger_jumps) if image != gate_resident),
        "meaning": (
            "The gate bounds the target set of every resident indirect JUMP this "
            "frontier retains, and of none of its indirect CALLS -- all 87 of its "
            "resolved target sets are jr switch islands. A bounded target set is "
            "still retained as a blocker: knowing where a jump can go is not the "
            "same as disposing of what it reaches."),
    }

    census_images = {row["id"]: row for row in census["image_census"]["images"]}
    missing_census = sorted(set(images) - set(census_images))
    if missing_census:
        raise ExtractError(
            f"static census does not cover {missing_census}; census_complete cannot "
            "be derived for an image nobody swept")

    query = {
        "schema": QUERY_SCHEMA,
        "target": seed["target"],
        "universe": {
            "images": [{"id": iid, "sha256": images[iid]["expected_sha256"],
                        "base": extents[iid][0], "end": extents[iid][1],
                        # DERIVED, never declared: byte partition complete AND
                        # every memory reference in every gap decided AND none
                        # of them reaching a window.
                        "census_complete": bool(census_images[iid]["census_complete"])}
                       for iid in sorted(images)],
            "categories": seed["categories"],
        },
        "windows": windows,
        "functions": functions,
        # Callers are roots: the checker only credits consumer_categories for
        # functions its walk reaches.
        "roots": [fid(k) for k in sorted(selected)],
        "callbacks": callbacks,
        "indirect_tables": sorted(tables.values(), key=lambda t: t["id"]),
        "boundary_owners": boundary_owners,
        "accesses": accesses,
        "residuals": residuals,
        "mechanical_completeness": {
            "complete": False,
            "evidence": "placeholder replaced below once the ledger hash is known",
            "ledger_sha256": None,
            "unemitted_resolved_accesses": unemitted,
            "ledger_path": None,     # filled in main()
            "attested_by": {"tool": "tools/phase4_frontier_extractor.py",
                            "tool_sha256": "0" * 64,
                            "seed_path": "", "seed_sha256": seed_sha,
                            "source_index_path": "analysis/phase4_static_frontier_index.json",
                            "source_index_sha256": index_sha,
                            "query_digest": "0" * 64},   # all filled in main()
            "retained_blockers": 0,  # filled in main() from the complete ledger
        },
        "authority": AUTHORITY,
    }

    by_register: dict[str, int] = {}
    for item in unresolved_accesses:
        name = str(item["base_register"])
        by_register[name] = by_register.get(name, 0) + 1
    incoming = [{"id": f"incoming_caller:{c[0]}:{c[1]:#010x}->{t[0]}:{t[1]:#010x}",
                 "caller": f"{c[0]}:{c[1]:#010x}", "target": fid(t)}
                for c, t in omitted_incoming_callers]
    for position, entry in enumerate(omitted_edges):
        entry["id"] = f"omitted_edge:{entry['function']}@{entry['site']}->{entry['target']}"
    for position, entry in enumerate(unresolvable_edges):
        entry["id"] = f"unresolvable_edge:{entry['function']}@{entry['site']}"
    for position, entry in enumerate(unresolved_accesses):
        entry["id"] = f"unresolved_access:{entry['function']}@{entry['pc']}"
    full_blockers = {
        "schema": "abl-phase4-frontier-blockers/1",
        "omitted_direct_edges": omitted_edges,
        "unresolvable_direct_edges": unresolvable_edges,
        "omitted_incoming_callers": incoming,
        "unresolved_accesses": unresolved_accesses,
        "direct_jumps_out": jumps_out,
        "indirect_jumps": indirect_jumps,
        "incoming_jumps": incoming_jumps,
        "unanalysed_extents": unanalysed,
        "binary_scan_unscanned_images": binary_unscanned,
    }
    # Stable ids must be UNIQUE: a repeated id makes a blocker uncoverable.
    seen_ids: dict[str, int] = {}
    for category, rows in full_blockers.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            base_id = row["id"]
            count = seen_ids.get(base_id, 0)
            seen_ids[base_id] = count + 1
            if count:
                row["id"] = f"{base_id}#{count}"
    blockers = {
        "omitted_direct_edges": {
            "count": len(omitted_edges),
            "meaning": "a real call edge whose callee is outside the selected closure",
            "sample": omitted_edges[:20]},
        "unresolvable_direct_edges": {
            "count": len(unresolvable_edges),
            "meaning": "a call whose target address matches no indexed record",
            "sample": unresolvable_edges[:20]},
        "omitted_incoming_callers": {
            "count": len(incoming),
            "meaning": ("the caller surface is one layer deep; these incoming edges come "
                        "from outside the selected set and are retained, not dropped"),
            "sample": incoming[:20]},
        "direct_jumps_out": {"count": len(jumps_out), "sample": jumps_out[:20],
            "meaning": "tail/direct jump leaving the selected closure"},
        "indirect_jumps": {"count": len(indirect_jumps), "sample": indirect_jumps[:20],
            "meaning": "indirect jump inside the closure; targets not enumerated"},
        "incoming_jumps": {"count": len(incoming_jumps), "sample": incoming_jumps[:20],
            "meaning": "jump from outside INTO the closure -- a real caller path"},
        "unanalysed_extents": {"count": len(unanalysed), "sample": unanalysed[:20],
            "meaning": "index recovered no CFG for this extent; its accesses are absent upstream"},
        "binary_scan_unscanned_images": {"count": len(binary_unscanned), "sample": binary_unscanned,
            "meaning": ("image absent or failing its pinned size/sha256, so its bytes were "
                        "never scanned at all")},
        "unresolved_accesses": {
            "count": len(unresolved_accesses),
            "by_base_register": dict(sorted(by_register.items())),
            "stack_relative": by_register.get("sp", 0),
            "non_stack": len(unresolved_accesses) - by_register.get("sp", 0),
            "meaning": ("effective address not statically decidable; NOT emitted into the "
                        "query, so the checker cannot count it as an unknown"),
            "sample": unresolved_accesses[:20]},
    }
    mechanically_complete = (all(entry["count"] == 0 for entry in blockers.values())
                             and unemitted == 0)
    summary = {
        "schema": SUMMARY_SCHEMA,
        "source_seed_sha256": seed_sha,
        "source_index_sha256": index_sha,
        "index_generated": index.get("generated"),
        "query_sha256": None,   # bound to the FINAL query bytes in main()
        "roots_declared_in_seed": [f"{r['image']}:{r['entry']}" for r in seed["roots"]],
        "root_provenance": {
            "seed_declared": len(roots),
            "access_seeded_whole_universe": len(access_seeded),
            "target_root_island_seeded": len(island_seeded),
            "target_root_island_seeding_scope": (
                "whole-image conservative superset: EVERY island in the index "
                "is seeded into EVERY extraction, regardless of row relevance. "
                "An unrelated island therefore inflates this closure rather "
                "than hiding from it -- the fail-closed direction for a "
                "blocker ledger."),
            "caller_surface": len(caller_keys),
            "note": ("Every declared function is emitted as a root so the checker credits its "
                     "categories. 'reached == declared' is therefore an ACCOUNTING identity, "
                     "not an independently established runtime-reachability result."),
        },
        "consumer_category_overrides_applied": len(overrides) - len(unused_overrides),
        "consumer_category_overrides_unused": unused_overrides,
        "accesses_from_static_index": index_only,
        "accesses_from_binary_supplement": binary_supplied,
        "accesses_from_static_index_only": len(universe_hits),
        "whole_universe_accesses_into_windows": len(universe_union),
        "accesses_emitted_from_selected": len(accesses),
        "whole_universe_accesses_not_emitted": unemitted,
        "functions_from_callee_closure": len(closure),
        "functions_added_as_callers": len(caller_keys),
        "functions_total": len(functions),
        "callback_groups_emitted_incomplete": len(callbacks),
        "indirect_control_reconciliation": indirect_reconciliation,
        "callback_target_functions_seeded": len(callback_seeded),
        "residual_covered_unknowns": len(covered),
        "images_census_complete": sorted(
            iid for iid in images if census_images[iid]["census_complete"]),
        "images_census_incomplete": sorted(
            iid for iid in images if not census_images[iid]["census_complete"]),
        "accesses_into_windows": len(accesses),
        "accesses_resolved_outside_windows": resolved_outside,
        "indirect_tables_emitted_incomplete": len(tables),
        "mechanically_complete": mechanically_complete,
        "mechanical_blockers": blockers,
        "completeness_warning": (
            "While mechanically_complete is false the emitted query describes only the "
            "statically resolvable subset of the frontier. An item2_ready verdict on it "
            "would understate the frontier."),
        "authoring_still_required": [
            "dispose of every emitted indirect table",
            "cover or own every mechanical blocker",
            "decide the images the static census leaves census-incomplete",
        ],
    }
    return query, summary, full_blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("seed", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--blockers", type=Path, required=True,
                        help="complete, stable-id blocker ledger (the summary keeps a sample)")
    parser.add_argument("--check", action="store_true",
                        help="require the retained outputs to equal regenerated bytes")
    args = parser.parse_args()
    for path in (args.output, args.summary, args.blockers):
        if ROOT not in path.resolve().parents:
            raise ExtractError("outputs must stay inside the repository")
    index, index_sha = load_index()
    seed, seed_sha = load_seed(args.seed)
    census = load_receipt(seed, "static_census", CENSUS_SCHEMA)
    if census["inputs"]["static_index_sha256"] != index_sha:
        raise ExtractError(
            "the static census was built against a different static index; "
            "regenerate tools/phase4_frontier_static_census.py first")
    gate = load_receipt(seed, "static_asm_gate", GATE_SCHEMA)
    query, summary, full_blockers = extract(seed, index, census, gate, seed_sha,
                                            index_sha)
    blocker_bytes = _render_summary(full_blockers)
    total_blockers = sum(len(v) for k, v in full_blockers.items() if isinstance(v, list))
    # Build the FINAL completeness block first, attach it, and only then compute
    # the digest -- digesting while the placeholder is still attached would bind
    # the attestation to a document that never existed.
    query["mechanical_completeness"] = {
        "complete": bool(summary["mechanically_complete"]),
        "evidence": (f"{total_blockers} mechanical blockers retained with stable ids in "
                     f"the ledger; {summary['whole_universe_accesses_not_emitted']} "
                     "statically resolved window accesses were not emitted into this query"),
        "ledger_sha256": _sha256_bytes(blocker_bytes),
        "ledger_path": str(args.blockers.resolve().relative_to(ROOT)),
        "unemitted_resolved_accesses": summary["whole_universe_accesses_not_emitted"],
        "retained_blockers": total_blockers,
        "attested_by": {
            "tool": "tools/phase4_frontier_extractor.py",
            "tool_sha256": _sha256_bytes(Path(__file__).read_bytes()),
            "seed_path": str(args.seed.resolve().relative_to(ROOT)),
            "seed_sha256": seed_sha,
            "source_index_path": "analysis/phase4_static_frontier_index.json",
            "source_index_sha256": index_sha,
            "query_path": str(args.output.resolve().relative_to(ROOT)),
            "summary_path": str(args.summary.resolve().relative_to(ROOT)),
            "query_digest": "0" * 64,
        },
    }
    query["mechanical_completeness"]["attested_by"]["query_digest"] = _query_digest(query)
    summary["blockers_ledger"] = {"path": str(args.blockers.resolve().relative_to(ROOT)),
                                  "sha256": _sha256_bytes(blocker_bytes)}
    query_bytes = _render_query(query)
    summary["query_sha256"] = _sha256_bytes(query_bytes)   # the FINAL query, not a placeholder
    summary_bytes = _render_summary(summary)
    if args.check:
        for path, fresh in ((args.output, query_bytes), (args.summary, summary_bytes),
                            (args.blockers, blocker_bytes)):
            if not path.is_file():
                raise ExtractError(f"retained output missing: {path}")
            if path.read_bytes() != fresh:
                raise ExtractError(f"retained output is stale: {path}")
        print("[phase4-frontier-extractor] retained outputs are fresh")
        return 0
    args.output.write_bytes(query_bytes)
    args.summary.write_bytes(summary_bytes)
    args.blockers.write_bytes(blocker_bytes)
    blockers = summary["mechanical_blockers"]
    print(f"[phase4-frontier-extractor] wrote {args.output}")
    print(f"[phase4-frontier-extractor] wrote {args.summary}")
    print(f"  functions {summary['functions_total']} "
          f"(callees {summary['functions_from_callee_closure']}, "
          f"+callers {summary['functions_added_as_callers']}) | "
          f"accesses into windows {summary['accesses_into_windows']}")
    print(f"  whole-universe window accesses {summary['whole_universe_accesses_into_windows']} | "
          f"emitted {summary['accesses_emitted_from_selected']} | "
          f"NOT emitted {summary['whole_universe_accesses_not_emitted']}")
    print(f"  mechanically_complete={summary['mechanically_complete']} | "
          f"omitted edges {blockers['omitted_direct_edges']['count']} | "
          f"omitted incoming callers {blockers['omitted_incoming_callers']['count']} | "
          f"unresolved accesses {blockers['unresolved_accesses']['count']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExtractError as exc:
        raise SystemExit(f"[phase4-frontier-extractor] ERROR: {exc}") from exc
