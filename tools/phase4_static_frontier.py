#!/usr/bin/env python3
"""Deterministic resident/overlay static frontier and proof-pilot generator.

The tracked outputs contain bytes-free structural metadata. Retail bytes and raw
Ghidra output remain external. The built-in R3000 decoder is the fail-closed path for
every census record; the independent Ghidra exporter provides the high-p-code audit
and never becomes the naming or behavioral authority.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/phase4_static_analysis.yaml"
FUNCTIONS_PATH = ROOT / "analysis/functions.json"
SEMANTIC_PATH = ROOT / "config/semantic_state.yaml"
RECORD_TYPES_PATH = ROOT / "config/record_types.yaml"
BUILD_BASELINES_PATH = ROOT / "tools/build_baselines.json"
SEGMENTS_PATH = ROOT / "config/segments.yml"
OVERLAYS_PATH = ROOT / "config/overlays.yml"
FMV_PATH = ROOT / "analysis/phase4_fmv_static_owners.json"
E08_PATH = ROOT / "analysis/phase4_e08_class_frontier.json"
EVENT_VM_PATH = ROOT / "analysis/phase4_event_vm.json"
C13_PATH = ROOT / "analysis/phase4_collectibles_frontier.json"
INDEX_OUTPUT = ROOT / "analysis/phase4_static_frontier_index.json"
OVERLAY_OUTPUT = ROOT / "analysis/phase4_overlay_semantic_index.json"
PILOT_OUTPUT = ROOT / "analysis/phase4_static_frontier_pilots.json"
TOOLCHAIN_OUTPUT = ROOT / "analysis/phase4_ghidra_toolchain.json"
SOURCE_MANIFEST_PATH = ROOT / "tools/repro_inputs.sha256"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REG_NAMES = [
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra",
]

LOADS = {
    0x20: ("lb", "read", 1, "signed"),
    0x21: ("lh", "read", 2, "signed"),
    0x22: ("lwl", "read", 4, "word_unknown"),
    0x23: ("lw", "read", 4, "word_unknown"),
    0x24: ("lbu", "read", 1, "unsigned"),
    0x25: ("lhu", "read", 2, "unsigned"),
    0x26: ("lwr", "read", 4, "word_unknown"),
    0x32: ("lwc2", "read", 4, "cop2"),
}
STORES = {
    0x28: ("sb", "write", 1, None),
    0x29: ("sh", "write", 2, None),
    0x2A: ("swl", "write", 4, None),
    0x2B: ("sw", "write", 4, None),
    0x2E: ("swr", "write", 4, None),
    0x3A: ("swc2", "write", 4, "cop2"),
}
BRANCH_OPS = {0x01, 0x04, 0x05, 0x06, 0x07}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def load_repro_manifest_pins(path: Path | None = None) -> dict[str, str]:
    """Parse the central input manifest without silently accepting ambiguity.

    The manifest is also the repository-safe identity receipt for external derived
    assembly which preservation policy intentionally keeps out of Git.  It does not
    establish that those source bytes are present, and callers must report that fact
    separately.
    """
    path = SOURCE_MANIFEST_PATH if path is None else path
    pins: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2 or not SHA256_RE.fullmatch(parts[0]):
            raise ValueError(
                f"invalid reproducibility manifest row {line_number}: {raw!r}")
        digest, source = parts
        source_path = Path(source)
        if source_path.is_absolute() or ".." in source_path.parts:
            raise ValueError(
                f"unsafe reproducibility manifest path at row {line_number}: {source!r}")
        if source in pins:
            raise ValueError(
                f"duplicate reproducibility manifest path at row {line_number}: {source}")
        pins[source] = digest
    return pins


def verify_callback_source(callback: dict, manifest_pins: dict[str, str]) -> dict:
    """Verify a callback source through its appropriate preservation contract."""
    source = callback["source"]
    expected = callback["source_sha256"]
    source_path = ROOT / source
    source_bytes_present = source_path.is_file()
    direct_hash_verified = (
        source_bytes_present and sha256_path(source_path) == expected)
    manifest_hash_verified = manifest_pins.get(source) == expected
    external_assembly = source.startswith("asm/hand_written/")

    if external_assembly:
        source_verified = manifest_hash_verified and (
            direct_hash_verified if source_bytes_present else True)
        verification_method = (
            "external_file_and_repro_manifest_sha256"
            if source_bytes_present else "repro_manifest_sha256")
    else:
        source_verified = direct_hash_verified
        verification_method = "tracked_file_sha256"

    return {
        "source": source,
        # ⚠️ NOT a property of the commit for external assembly, so it is not
        # emitted as one. `asm/hand_written/` is deliberately outside git, so
        # whether its bytes sit on this disk changed the retained artifact from
        # checkout to checkout and made it irreproducible -- the same defect
        # class as analysis/phase4_evidence_dag.json. `null` means "this
        # document does not assert local presence"; the identity contract that
        # IS a property of the commit is source_manifest_pinned.
        "source_bytes_present": None if external_assembly else source_bytes_present,
        "source_manifest_pinned": manifest_hash_verified,
        "source_verification_method": ("repro_manifest_sha256" if external_assembly
                                       else verification_method),
        # Compatibility field: verified means the source identity contract passed,
        # not that external source bytes were present in this checkout.
        "source_verified": source_verified,
    }


def as_int(value: int | str) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def hx(value: int) -> str:
    return f"0x{value:08X}"


def sign16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def render(doc: dict) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode()


def image_path(overlay: str | None, config: dict) -> tuple[str, Path, int]:
    if overlay is None:
        row = config["resident"]
        return row["image_id"], ROOT / row["path"], as_int(row["file_va_base"])
    if overlay == "MEMORY":
        return overlay, ROOT / config["overlays"]["memory_path"], as_int(
            config["overlays"]["region_b_base"])
    parts = overlay.split("_", 1)
    if len(parts) != 2 or not parts[0].startswith("LEVEL"):
        raise ValueError(f"cannot map overlay image {overlay!r}")
    directory, filename = parts
    return overlay, ROOT / "REBUILD/files" / directory / f"{filename}.BIN", as_int(
        config["overlays"]["region_a_base"])


def semantic_address_map() -> dict[int, list[dict]]:
    result: dict[int, list[dict]] = defaultdict(list)
    for row in load_yaml(SEMANTIC_PATH).get("entries") or []:
        address = row.get("address")
        if address is not None:
            result[as_int(address)].append({
                "id": row["id"], "width": row.get("width"),
                "owner": row.get("owner"), "confidence": row.get("confidence"),
            })
    for record in load_yaml(RECORD_TYPES_PATH).get("records") or []:
        base = record.get("base")
        if base is None:
            continue
        base_i = as_int(base)
        for field in record.get("fields") or []:
            if "offset" not in field:
                continue
            result[base_i + as_int(field["offset"])].append({
                "id": f"record.{record['id']}.{field.get('name', 'unknown')}",
                "width": field.get("width"), "owner": record.get("owner"),
                "confidence": field.get("confidence"),
            })
    return result


def structural_word(word: int) -> int:
    op = word >> 26
    if op in {2, 3}:
        return op << 26
    if op == 0:
        return word & 0xFC1FFFFF
    return word & 0xFFFF0000


def function_bytes(blob: bytes, file_base: int, start: int, end: int) -> bytes:
    lo, hi = start - file_base, end - file_base
    if lo < 0 or hi < lo or hi > len(blob):
        raise ValueError(
            f"function {hx(start)}..{hx(end)} maps outside image base {hx(file_base)}")
    return blob[lo:hi]


def written_register(word: int) -> int | None:
    op = word >> 26
    rt = (word >> 16) & 31
    rd = (word >> 11) & 31
    if op == 0:
        funct = word & 0x3F
        if funct in {8, 9, 12, 13}:
            return 31 if funct == 9 and rd == 0 else (rd if funct == 9 else None)
        return rd if rd else None
    if op in LOADS or op in {0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F}:
        return rt if rt else None
    if op == 3:
        return 31
    return None


CALLER_SAVED = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                24, 25, 26, 27, 31}


def control_flow(word: int, pc: int) -> tuple[str | None, int | None]:
    op = word >> 26
    if op == 3:
        return "call", ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
    if op == 2:
        return "jump", ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
    if op in BRANCH_OPS:
        return "branch", pc + 4 + (sign16(word & 0xFFFF) << 2)
    if op == 0 and (word & 0x3F) == 8:
        rs = (word >> 21) & 31
        return ("return" if rs == 31 else "indirect_jump"), None
    if op == 0 and (word & 0x3F) == 9:
        return "indirect_call", None
    return None, None


def branch_successors(word: int, pc: int, target: int) -> list[int]:
    op = word >> 26
    rs, rt = (word >> 21) & 31, (word >> 16) & 31
    if op == 0x04 and rs == rt:  # beq r,r is unconditional
        return [target]
    if op == 0x05 and rs == rt:  # bne r,r is never taken
        return [pc + 8]
    if op == 0x06 and rs == 0:  # blez zero
        return [target]
    if op == 0x07 and rs == 0:  # bgtz zero
        return [pc + 8]
    return [target, pc + 8]


# Resolved indirect-jump targets, keyed by jr pc. Empty unless load_jr_targets()
# has verified the artifact against the image actually being analysed -- an
# unverified target set would invent reachability, which is worse than having none.
JR_TARGETS: dict[int, list[int]] = {}
JR_PROVENANCE: dict[str, object] = {"source": None, "verified": False,
                                    "sites": 0, "targets": 0}
JR_ARTIFACT_PATH = ROOT / "analysis/phase3_jr_tables.json"
GATE_ARTIFACT_PATH = ROOT / "analysis/phase4_static_asm_prerequisites.json"
GAP_SEMANTICS_ARTIFACT_PATH = ROOT / "analysis/phase4_f01_gap_semantics.json"
F01_HARD_TRUTH_PATH = ROOT / "analysis/phase4_f01_static_hard_truth.json"
# Islands recovered from proved indirect-jump targets that land in unclaimed
# bytes. Each decoded island IS promoted to a first-class census record, so
# there is exactly ONE authoritative executable universe (`records`); this list
# retains the DISCOVERY PROVENANCE -- the proved root, the stopping proof, the
# gap it was carved from -- and never a second copy of the code facts. The
# pinned expected-census identity is intentionally re-pinned when an island is
# established: the pin is a change detector, not a reason to hide real
# executable code from per-record consumers (that hid two unresolved stores
# from the F01 ledger and the writer-census resolver until 2026-08-06). An
# island extent still never widens a neighbouring extent.
TARGET_ROOT_ISLANDS: list[dict] = []


def load_f01_range_evidence(path: Path, image_sha256: str) -> dict:
    """Load the C-proved trig reader ranges, or fail closed with no ranges.

    Exact constants alone cannot resolve an address whose masked index is
    dynamic.  The F01 C probe proves a bounded effective-address interval for
    each named reader and independently verifies the complete table contents.
    This loader accepts that evidence only when the image, C source, content
    verdict, and exact reader-PC identity all agree.
    """
    report: dict[str, Any] = {
        "source": str(path.relative_to(ROOT)), "verified": False,
        "artifact_sha256": None, "reason": None, "readers": {},
        "reader_count": 0, "reader_identity_sha256": None,
    }
    if not path.is_file():
        report["reason"] = "artifact absent"
        return report
    report["artifact_sha256"] = sha256_path(path)
    document = json.loads(path.read_bytes())
    inputs = document.get("inputs") or {}
    if inputs.get("pristine_image_sha256") != image_sha256:
        report["reason"] = "artifact pins a different resident image"
        return report
    c_source = ROOT / str(inputs.get("c_source") or "")
    if not c_source.is_file() or sha256_path(c_source) != inputs.get("c_source_sha256"):
        report["reason"] = "artifact's C source hash is stale"
        return report
    verdicts = document.get("verdicts") or {}
    if not verdicts.get("trig_semantic_disposition_supported"):
        report["reason"] = "content-plus-reader semantic verdict is false"
        return report
    c_probe = document.get("c_probe") or {}
    readers: dict[tuple[str, int], dict] = {}
    for table in c_probe.get("trigonometric_tables") or []:
        if (table.get("content_comparison") or {}).get("mismatched_entries") != 0:
            report["reason"] = f"{table.get('id')}: full content comparison failed"
            return report
        if (table.get("gap") or {}).get("mismatched_entries") != 0:
            report["reason"] = f"{table.get('id')}: gap content comparison failed"
            return report
        image = str(table.get("image"))
        for row in table.get("readers") or []:
            pc = as_int(row["pc"])
            key = (image, pc)
            if key in readers:
                report["reason"] = f"duplicate reader identity {image}:{hx(pc)}"
                return report
            lo, hi = map(as_int, row["effective_address_range"])
            if hi <= lo:
                report["reason"] = f"empty reader range {image}:{hx(pc)}"
                return report
            readers[key] = {
                "table": table["id"], "function": row["function"],
                "pc": row["pc"], "mnemonic": row["mnemonic"],
                "width": int(row["width"]),
                "effective_address_range": [hx(lo), hx(hi)],
                "range_semantics": row["range_semantics"],
                "instruction_derivation": row["instruction_derivation"],
            }
    identities = {
        f"{image}:{hx(pc)}": readers[(image, pc)]["effective_address_range"]
        for image, pc in sorted(readers)
    }
    report.update({
        "verified": True,
        "reason": "image/source hashes and zero-mismatch content verdict agree",
        "readers": readers,
        "reader_count": len(readers),
        "reader_identity_sha256": sha256_bytes(
            json.dumps(identities, sort_keys=True).encode()),
        "reader_identities": identities,
    })
    return report


def load_jr_targets(path: Path, image_sha256: str) -> None:
    """Consume the jump tables `tools/phase3_jr_tables.py` already recovered.

    Without this the CFG walk stops dead at every `jr`, and 869 targets recovered
    in 2026-07 sit unused on disk while 57 index records report `analysis_status:
    ok` over extents that are mostly unreachable. `scene_flow_dispatcher` reaches
    8 of its 393 instructions that way.

    FAILS CLOSED. The artifact pins the sha256 of the image it was derived from;
    if that does not match the image being analysed, no targets are loaded and the
    walk behaves exactly as before. Reachability asserted from a stale table would
    be indistinguishable from reachability that is real.
    """
    JR_TARGETS.clear()
    # REPO-RELATIVE. An absolute path makes the index differ by checkout location,
    # so it stops reproducing for an independent verifier -- the same defect that
    # hit the typed-state image map, and the third time this exact shape has
    # appeared. Record what the artifact IS, not where this machine keeps it.
    try:
        source = str(path.relative_to(ROOT))
    except ValueError:
        source = str(path)
    JR_PROVENANCE.update({"source": source, "verified": False, "sites": 0,
                          "targets": 0, "reason": None, "artifact_sha256": None,
                          "identity_digest": None, "site_targets": {}})
    if not path.is_file():
        JR_PROVENANCE["reason"] = "artifact absent"
        return
    JR_PROVENANCE["artifact_sha256"] = sha256_path(path)
    doc = json.loads(path.read_bytes())
    pinned = doc.get("fixture_sha256") or {}
    if image_sha256 not in set(pinned.values()):
        JR_PROVENANCE["reason"] = (
            "artifact pins a different image; refusing to import targets")
        return
    for jr_pc, site in (doc.get("decoded") or {}).items():
        targets = sorted({int(str(t["target"]), 16) for t in site.get("targets") or []})
        if targets:
            JR_TARGETS[int(jr_pc, 16)] = targets
    # ⚠️ Counts are not an identity. "36 sites, 408 targets" is satisfied by any
    # wrong table with the same shape, and this project has already had a wrong
    # 37-extent set pass review on equal counts alone. The exact (site, target)
    # map is retained so a verifier can DIFFERENCE it, and a digest over the
    # canonical form is carried alongside so a single moved target changes a
    # visible value.
    identities = {hx(site): [hx(target) for target in targets]
                  for site, targets in sorted(JR_TARGETS.items())}
    JR_PROVENANCE.update({
        "verified": True, "sites": len(JR_TARGETS),
        "targets": sum(len(v) for v in JR_TARGETS.values()),
        "reason": "fixture_sha256 matches the analysed image",
        "artifact_sha256": sha256_path(path),
        "identity_digest": sha256_bytes(
            json.dumps(identities, sort_keys=True).encode()),
        "site_targets": identities,
    })


def image_direct_cfg(word_at: dict[int, int], entries: list[int]
                     ) -> tuple[set[int], set[int], dict[int, set[int]]]:
    """Whole-IMAGE fixed point over direct edges PLUS the verified jr targets.

    NOT the shared gate's algorithm: the gate follows direct edges only
    (`indirect_edges_followed: false`), while this walk additionally follows
    every hash-verified jr target the two pinned artifacts supply. The retained
    `cfg_universe` string is the authoritative description; this docstring must
    agree with it.

    A per-function walk starting at that function's own entry is not the same
    universe as the program's direct control flow, and the difference is not
    academic.  `scene_flow_dispatcher` runs eight instructions and then
    `j 0x8004fb3c`, which leaves its own extent, so an isolated walk stops with
    385 of 393 words unreachable and `analysis_status: ok`.  The remaining words
    are entered from OUTSIDE -- five `j 0x8004fcc0` sites plus two branches -- and
    a per-extent walk can never see them.

    Seeds are the typed code/thunk extent entries; edges are direct branch, jump
    and call targets, the fall-through after a call, and any `jr` target the
    verified jump-table import supplied.  Nothing is seeded from an UNREACHABLE
    source: taking every incoming edge regardless of whether its source can run
    would invent reachability, which is the failure `load_jr_targets` already
    refuses.

    ⚠️ THIS UNIVERSE IS NOT THE GATE'S.  `analysis/phase4_static_asm_prerequisites.json`
    reports `indirect_edges_followed: false` and follows direct edges only; this
    walk additionally follows the hash-verified `jr` table targets, so it is
    "direct edges PLUS verified jr targets".  The two must not be quoted as the
    same universe, and the extra targets are pinned by artifact hash and exact
    (site, target) identity in `indirect_jump_targets` rather than by count.
    """
    reachable: set[int] = set()
    block_starts: set[int] = set(entries)
    # target -> the REACHABLE source pcs that can enter it. Only edges taken from
    # an instruction the walk actually reached are recorded, so an incoming edge
    # sitting in dead code never confers reachability or an entry state.
    incoming: dict[int, set[int]] = {}
    queue = list(entries)
    while queue:
        pc = queue.pop()
        while pc in word_at and pc not in reachable:
            reachable.add(pc)
            kind, target = control_flow(word_at[pc], pc)
            if kind is None:
                pc += 4
                continue
            if pc + 4 in word_at:
                reachable.add(pc + 4)
            successors: list[int] = []
            if kind == "branch":
                successors = branch_successors(word_at[pc], pc, target)
            elif kind == "jump":
                successors = [target]
            elif kind == "call":
                # both the callee and the return point
                successors = [target, pc + 8]
            elif kind == "indirect_call":
                successors = [pc + 8]
            elif kind == "indirect_jump" and pc in JR_TARGETS:
                successors = list(JR_TARGETS[pc])
            for successor in successors:
                if successor is not None and successor in word_at:
                    block_starts.add(successor)
                    incoming.setdefault(successor, set()).add(pc)
                    if successor not in reachable:
                        queue.append(successor)
            break
    return reachable, block_starts, incoming


def cross_extent_entries(incoming: dict[int, set[int]], start: int,
                         end: int) -> set[int]:
    """Addresses in [start, end) that some REACHABLE instruction outside enters.

    Only these may be given the stateless entry condition.  Handing it to every
    block start inside the extent -- including the ones the function's own walk
    reaches, and the `jr` island targets it already follows -- would meet
    `{zero, gp}` into blocks that have no external predecessor at all and
    withdraw address resolutions that were perfectly sound.  Measured on the
    resident image, that mistake cost 1,024 resolutions in one pass.
    """
    return {target for target, sources in incoming.items()
            if start <= target < end and any(not (start <= src < end)
                                             for src in sources)}


def load_gate_jr_targets(path: Path, image_sha256: str) -> dict:
    """Merge the shared gate's resolved `jr` target sets into the CFG input.

    The gate resolves 87 `jr` sites where `analysis/phase3_jr_tables.json`
    decodes 36, and the 36 are a strict subset -- so consuming only the phase3
    artifact left 51 proved target sets unused and a region such as
    `0x8004C898` unreachable in the index while the gate could name its owner.

    FAILS CLOSED the same way the phase3 loader does: the gate must have probed
    the image being analysed. Provenance is retained PER SITE, and the phase3
    subset relation is checked rather than assumed -- a gate that had dropped a
    phase3 site would be a disagreement, not a silent merge.
    """
    report = {"source": None, "verified": False, "sites": 0, "targets": 0,
              "sites_added": 0, "artifact_sha256": None, "reason": None,
              "phase3_sites_not_in_gate": [], "site_targets": {}}
    try:
        report["source"] = str(path.relative_to(ROOT))
    except ValueError:
        report["source"] = str(path)
    if not path.is_file():
        report["reason"] = "artifact absent"
        return report
    report["artifact_sha256"] = sha256_path(path)
    document = json.loads(path.read_bytes())
    probed = (document.get("inputs") or {}).get("sha256") or {}
    image = (document.get("inputs") or {}).get("paths", {}).get("image")
    if probed.get(image) != image_sha256:
        report["reason"] = "gate probed a different image; refusing to import targets"
        return report
    added: dict[int, list[int]] = {}
    for site in document["indirect_control"]["jr_sites"]:
        resolution = site.get("resolution") or {}
        if not resolution.get("target_set_complete"):
            continue
        # ⚠️ jump islands are stored under `entries`, every other kind under
        # `targets`. Reading one and not the other saw 38 of 450 targets.
        values = {as_int(value) for value in (resolution.get("targets") or [])}
        values |= {as_int(entry["target"]) for entry in (resolution.get("entries") or [])}
        if values:
            added[as_int(site["pc"])] = sorted(values)
    report["phase3_sites_not_in_gate"] = sorted(
        hx(pc) for pc in JR_TARGETS if pc not in added)
    before = set(JR_TARGETS)
    for pc, targets in added.items():
        JR_TARGETS[pc] = sorted(set(JR_TARGETS.get(pc, [])) | set(targets))
    report.update({
        "verified": True, "reason": "gate probed the analysed image",
        "sites": len(added), "targets": sum(len(v) for v in added.values()),
        "sites_added": len(set(added) - before),
        "site_targets": {hx(pc): [hx(t) for t in targets]
                         for pc, targets in sorted(added.items())},
    })
    return report


def decode_target_root_island(word_at: dict[int, int], blob: bytes, base: int,
                              root: int, gap: tuple[int, int],
                              extent_entries: set[int]) -> dict | None:
    """Bound an executable island starting at a PROVED indirect-jump target.

    ⚠️ The CFG word map is built only from claimed extents, so a proved target
    landing in unclaimed bytes is discarded before the walk sees it. Importing
    more `jr` identities cannot fix that on its own -- the bytes have to become a
    separately evidenced island, and NOT by widening a neighbouring extent, which
    is the shortcut the shared gate explicitly refused.

    The extent is DERIVED with an explicit stopping proof, one of:

    * an unconditional `j`/`jr` inside the gap, whose delay slot ends the island; or
    * fallthrough that reaches the gap end exactly, where the gap end is the
      ENTRY of a claimed executable extent -- the island joins it.

    Anything else -- running past the gap, a branch leaving the island to
    somewhere that is neither the island nor a claimed entry -- returns None. A
    boundary that cannot be proved is not a boundary that gets picked.
    """
    gap_start, gap_end = gap
    if not (gap_start <= root < gap_end) or (root - gap_start) % 4:
        return None
    pc = root
    proof = None
    while pc < gap_end:
        word = int.from_bytes(blob[pc - base:pc - base + 4], "little")
        kind, target = control_flow(word, pc)
        if kind in {"jump", "return", "indirect_jump"}:
            if pc + 4 >= gap_end:          # delay slot must be inside the island
                return None
            pc += 8
            proof = f"unconditional {kind} at {hx(pc - 8)} ends the island"
            break
        if kind == "branch":
            for successor in branch_successors(word, pc, target):
                if successor is None:
                    continue
                inside = root <= successor < gap_end
                if not inside and successor not in extent_entries:
                    return None
            pc += 8
            continue
        if kind in {"call", "indirect_call"}:
            if target is not None and target not in extent_entries:
                return None
            pc += 8
            continue
        pc += 4
    else:
        if gap_end not in extent_entries:
            return None
        proof = (f"fallthrough reaches the gap end {hx(gap_end)}, which is the "
                 "entry of a claimed executable extent")
    if pc != gap_end:
        return None
    return {"start": hx(root), "end": hx(gap_end),
            "instruction_count": (gap_end - root) // 4, "stopping_proof": proof}


def discover_cfg(words: list[int], start: int,
                 seeds: set[int] | None = None) -> tuple[dict[int, dict], set[int], set[int]]:
    """Discover reachable blocks while treating each MIPS delay slot explicitly.

    `seeds` carries the addresses inside this extent that the whole-image direct
    walk proved enterable from elsewhere.  Without them the walk sees only what
    the function's own entry reaches.
    """
    end = start + len(words) * 4
    word_at = {start + index * 4: word for index, word in enumerate(words)}
    reachable: set[int] = set()
    block_starts = {start}
    queue = [start]
    for seed in sorted(seeds or ()):
        if start <= seed < end:
            block_starts.add(seed)
            queue.append(seed)
    while queue:
        pc = queue.pop()
        while pc in word_at and pc not in reachable:
            reachable.add(pc)
            kind, target = control_flow(word_at[pc], pc)
            if kind is None:
                pc += 4
                continue
            delay = pc + 4
            if delay in word_at:
                reachable.add(delay)
            successors: list[int] = []
            if kind == "branch":
                successors = branch_successors(word_at[pc], pc, target)
            elif kind == "jump":
                successors = [target]
            elif kind in {"call", "indirect_call"}:
                successors = [pc + 8]
            elif kind == "indirect_jump" and pc in JR_TARGETS:
                successors = list(JR_TARGETS[pc])
            for successor in successors:
                if successor is not None and start <= successor < end:
                    block_starts.add(successor)
                    if successor not in reachable:
                        queue.append(successor)
            break

    blocks: dict[int, dict] = {}
    for block_start in sorted(block_starts & reachable):
        pcs: list[int] = []
        successors: list[int] = []
        call_boundary = False
        pc = block_start
        while pc in reachable:
            if pc != block_start and pc in block_starts:
                successors = [pc]
                break
            pcs.append(pc)
            kind, target = control_flow(word_at[pc], pc)
            if kind is None:
                pc += 4
                continue
            delay = pc + 4
            if delay in reachable and delay not in pcs:
                pcs.append(delay)
            if kind == "branch":
                successors = [value for value in branch_successors(word_at[pc], pc, target)
                              if value is not None and value in block_starts]
            elif kind == "jump":
                successors = [target] if target in block_starts else []
            elif kind in {"call", "indirect_call"}:
                successors = [pc + 8] if pc + 8 in block_starts else []
                call_boundary = True
            elif kind == "indirect_jump" and pc in JR_TARGETS:
                successors = [t for t in JR_TARGETS[pc] if t in block_starts]
            break
        blocks[block_start] = {
            "pcs": pcs, "successors": sorted(set(successors)),
            "call_boundary": call_boundary,
        }
    return blocks, reachable, block_starts


def merge_constants(current: dict[int, int] | None,
                    incoming: dict[int, int]) -> dict[int, int]:
    if current is None:
        return dict(incoming)
    return {register: value for register, value in current.items()
            if incoming.get(register) == value}


def transfer_constants(constants: dict[int, int], word: int, pc: int) -> None:
    op = word >> 26
    rs, rt, rd = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
    imm = word & 0xFFFF
    if op == 0x0F and rt:  # lui
        constants[rt] = (imm << 16) & 0xFFFFFFFF
    elif op in {0x08, 0x09} and rt:  # addi/addiu
        if rs in constants:
            constants[rt] = (constants[rs] + sign16(imm)) & 0xFFFFFFFF
        else:
            constants.pop(rt, None)
    elif op == 0x0D and rt:  # ori
        if rs in constants:
            constants[rt] = constants[rs] | imm
        else:
            constants.pop(rt, None)
    elif op == 0x0C and rt:  # andi
        if rs in constants:
            constants[rt] = constants[rs] & imm
        else:
            constants.pop(rt, None)
    elif op == 0 and (word & 0x3F) in {0x21, 0x25} and rd:  # addu/or
        if rs in constants and rt in constants:
            constants[rd] = ((constants[rs] + constants[rt])
                             if (word & 0x3F) == 0x21
                             else (constants[rs] | constants[rt])) & 0xFFFFFFFF
        else:
            constants.pop(rd, None)
    elif op == 0 and (word & 0x3F) == 0 and rd:  # sll
        if rt in constants:
            constants[rd] = (constants[rt] << ((word >> 6) & 31)) & 0xFFFFFFFF
        else:
            constants.pop(rd, None)
    else:
        destination = written_register(word)
        if destination is not None:
            constants.pop(destination, None)
    if op == 3:
        constants[31] = (pc + 8) & 0xFFFFFFFF
    constants[0] = 0


def analyze_code(data: bytes, start: int, image_id: str,
                 state_map: dict[int, list[dict]], runtime_gp: int,
                 seeds: set[int] | None = None) -> dict:
    words = [struct.unpack_from("<I", data, offset)[0]
             for offset in range(0, len(data) - 3, 4)]
    word_at = {start + index * 4: word for index, word in enumerate(words)}
    blocks, reachable, block_starts = discover_cfg(words, start, seeds)
    basic_blocks = []
    branches = []
    for block_start, block in sorted(blocks.items()):
        terminator = None
        for pc in block["pcs"]:
            kind, target = control_flow(word_at[pc], pc)
            if kind is not None:
                terminator = {
                    "pc": hx(pc), "kind": kind,
                    "target": hx(target) if target is not None else None,
                    "delay_slot": hx(pc + 4) if pc + 4 in block["pcs"] else None,
                }
                if kind == "branch":
                    branches.append({
                        **terminator,
                        "successors": [hx(value) for value in branch_successors(
                            word_at[pc], pc, target)],
                    })
                break
        basic_blocks.append({
            "start": hx(block_start), "instruction_count": len(block["pcs"]),
            "successors": [hx(value) for value in block["successors"]],
            "terminator": terminator,
        })
    # A block entered from OUTSIDE this function has no predecessor here, so
    # nothing local is known about its registers on entry.  The conservative
    # state is the architecturally invariant pair -- `$zero` and the proven
    # constant `$gp` -- which is exactly what the call boundary below already
    # restores after every `jal`.  Nothing stronger may be assumed.
    #
    # ⚠️ This can only WEAKEN the analysis, never strengthen it: `merge_constants`
    # is a meet, so an externally entered block that is also reachable locally
    # ends up with the intersection, and an access that used to resolve may stop
    # resolving.  That direction is sound; the opposite would invent addresses.
    external_entries = sorted(
        block for block in blocks
        if seeds and block in seeds and block != start)
    entry_states: dict[int, dict[int, int]] = {start: {0: 0, 28: runtime_gp}}
    for block_start in external_entries:
        entry_states.setdefault(block_start, {0: 0, 28: runtime_gp})
    queue = [start, *external_entries]
    while queue:
        block_start = queue.pop(0)
        constants = dict(entry_states[block_start])
        block = blocks[block_start]
        for pc in block["pcs"]:
            transfer_constants(constants, word_at[pc], pc)
        if block["call_boundary"]:
            for register in CALLER_SAVED:
                constants.pop(register, None)
            constants[0], constants[28] = 0, runtime_gp
        for successor in block["successors"]:
            merged = merge_constants(entry_states.get(successor), constants)
            if merged != entry_states.get(successor):
                entry_states[successor] = merged
                queue.append(successor)

    direct_calls: list[dict] = []
    direct_jumps: list[dict] = []
    indirect_calls: list[dict] = []
    indirect_jumps: list[dict] = []
    memory: list[dict] = []
    returns = 0
    signed_ops = 0
    for block_start, block in sorted(blocks.items()):
        constants = dict(entry_states[block_start])
        for pc in block["pcs"]:
            word = word_at[pc]
            op = word >> 26
            rs, rt = (word >> 21) & 31, (word >> 16) & 31
            imm = word & 0xFFFF
            kind, target = control_flow(word, pc)
            if kind == "call":
                direct_calls.append({"pc": hx(pc), "target": hx(target)})
            elif kind == "jump":
                direct_jumps.append({"pc": hx(pc), "target": hx(target)})
            elif kind == "return":
                returns += 1
            elif kind == "indirect_call":
                indirect_calls.append({"pc": hx(pc), "register": REG_NAMES[rs]})
            elif kind == "indirect_jump":
                indirect_jumps.append({"pc": hx(pc), "register": REG_NAMES[rs]})

            mem_spec = LOADS.get(op) or STORES.get(op)
            if mem_spec:
                mnemonic, access, width, signedness = mem_spec
                base_value = constants.get(rs)
                address = None if base_value is None else (base_value + sign16(imm)) & 0xFFFFFFFF
                memory.append({
                    "pc": hx(pc), "mnemonic": mnemonic, "access": access,
                    "width": width, "signedness": signedness,
                    "base_register": REG_NAMES[rs], "offset": sign16(imm),
                    "address": hx(address) if address is not None else None,
                    "state_joins": state_map.get(address, []) if address is not None else [],
                })
            if op in {0x0A} or (op == 0 and (word & 0x3F) in {0x1A, 0x1B, 0x2A}):
                signed_ops += 1
            transfer_constants(constants, word, pc)

    exact = sha256_bytes(data)
    structural = sha256_bytes(b"".join(struct.pack("<I", structural_word(w)) for w in words))
    state_accesses = sum(1 for row in memory if row["state_joins"])
    return {
        "analysis_method": "static_mips_r3000",
        "analysis_status": "ok",
        "exact_fingerprint": exact,
        "structural_fingerprint": structural,
        "instruction_count": len(reachable),
        "extent_instruction_count": len(words),
        "unreachable_instruction_count": len(words) - len(reachable),
        "basic_block_count": len(blocks),
        "basic_blocks": basic_blocks,
        "branches": sorted(branches, key=lambda row: row["pc"]),
        "direct_calls": sorted(direct_calls, key=lambda row: row["pc"]),
        "direct_jumps": sorted(direct_jumps, key=lambda row: row["pc"]),
        "indirect_calls": sorted(indirect_calls, key=lambda row: row["pc"]),
        "indirect_jumps": sorted(indirect_jumps, key=lambda row: row["pc"]),
        "return_count": returns,
        "memory_accesses": memory,
        "resolved_state_accesses": state_accesses,
        "signed_operation_count": signed_ops,
        "unresolved_boundaries": [
            {"kind": "indirect_call", **row} for row in indirect_calls
        ] + [
            {"kind": "indirect_jump", **row} for row in indirect_jumps
        ] + [
            {"kind": "unresolved_memory", "pc": row["pc"],
             "base_register": row["base_register"], "offset": row["offset"]}
            for row in memory if row["address"] is None
        ],
        "cfg_dataflow": "reachable_blocks_intersection_merge_call_clobber",
        "image_id": image_id,
    }


def build_index() -> dict:
    config = load_yaml(CONFIG_PATH)
    census = load_json(FUNCTIONS_PATH)
    baseline_inputs = load_json(BUILD_BASELINES_PATH).get("staged_inputs") or {}
    segments = load_yaml(SEGMENTS_PATH)
    overlay_config = load_yaml(OVERLAYS_PATH)
    state_map = semantic_address_map()
    blob_cache: dict[str, bytes] = {}
    image_meta: dict[str, dict] = {}
    records: list[dict] = []
    errors: list[str] = []
    expected_resident_base = as_int(segments["load_va"]) - as_int(segments["header_bytes"])
    independent_bindings = {
        "runtime_gp": (as_int(config["runtime_gp"]), as_int(segments["gp"])),
        "resident.file_va_base": (as_int(config["resident"]["file_va_base"]),
                                  expected_resident_base),
        "resident.text_start": (as_int(config["resident"]["text_start"]),
                                as_int(segments["load_va"])),
        "resident.text_end": (as_int(config["resident"]["text_end"]),
                              as_int(segments["load_va"]) + as_int(segments["text_size"])),
        "overlays.region_a_base": (as_int(config["overlays"]["region_a_base"]),
                                   as_int(overlay_config["region_a"])),
        "overlays.region_b_base": (as_int(config["overlays"]["region_b_base"]),
                                   as_int(overlay_config["region_b"])),
        "overlays.region_a_code_offset": (
            as_int(config["overlays"]["region_a_code_offset"]), 4),
        "overlays.gp": (as_int(config["runtime_gp"]), as_int(overlay_config["gp"])),
        "fmv.base": (as_int(config["fmv"]["base"]), as_int(overlay_config["region_b"])),
    }
    for label, (actual, expected) in independent_bindings.items():
        if actual != expected:
            errors.append(f"independent address binding drift {label}: {hx(actual)} != {hx(expected)}")
    # Import the jump tables recovered by tools/phase3_jr_tables.py, so the CFG
    # walk continues through `jr` dispatches instead of stopping at them. The
    # loader verifies the artifact's pinned image hash against the resident
    # executable and imports nothing on a mismatch.
    resident_exe = ROOT / "REBUILD/files/SCUS_942.88"
    resident_sha = sha256_path(resident_exe) if resident_exe.is_file() else ""
    load_jr_targets(JR_ARTIFACT_PATH, resident_sha)
    gate_jr = load_gate_jr_targets(GATE_ARTIFACT_PATH, resident_sha)
    f01_ranges = load_f01_range_evidence(F01_HARD_TRUTH_PATH, resident_sha)
    if not f01_ranges["verified"]:
        errors.append(f"F01 static range evidence unavailable: {f01_ranges['reason']}")
    TARGET_ROOT_ISLANDS.clear()

    seen: set[tuple[str, str]] = set()
    duplicate_count = 0
    pending: list[tuple] = []
    for source in census.get("functions") or []:
        overlay = source.get("overlay") if source.get("space") == "overlay" else None
        try:
            image_id, path, file_base = image_path(overlay, config)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        rel = str(path.relative_to(ROOT))
        if rel not in blob_cache:
            if not path.is_file():
                errors.append(f"missing image {rel}")
                continue
            blob_cache[rel] = path.read_bytes()
            staged_rel = rel.removeprefix("REBUILD/files/")
            expected_identity = baseline_inputs.get(staged_rel)
            actual_hash = sha256_path(path)
            actual_size = path.stat().st_size
            identity_verified = bool(expected_identity
                                     and actual_hash == expected_identity.get("sha256")
                                     and actual_size == expected_identity.get("size"))
            if not identity_verified:
                errors.append(f"unverified staged image identity {rel}")
            role = "resident" if overlay is None else (
                "region_b_memory" if overlay == "MEMORY" else "region_a_level")
            header_value = None
            expected_header_value = None
            # ⚠️ DERIVED, not assumed. The resident image is a PS-X EXE with a
            # 2,048-byte header; emitting `bytes: 0` for it said the file began
            # with loadable text, which is false and which a downstream census
            # had to contradict from the bytes to get its own universe right.
            blob = blob_cache[rel]
            if blob[:8] == b"PS-X EXE":
                header_rule = {"bytes": 0x800, "code_entry": "base_plus_header"}
            elif role == "region_a_level":
                header_rule = {"bytes": 4, "code_entry": "base_plus_header"}
            else:
                header_rule = {"bytes": 0, "code_entry": "base"}
            if role == "region_a_level":
                directory, filename = overlay.split("_", 1)
                level_number = int(directory.removeprefix("LEVEL"))
                expected_header_value = level_number + (14 if filename == "LEVEL1" else 4)
                header_value = struct.unpack_from("<I", blob_cache[rel], 0)[0]
                if header_value != expected_header_value:
                    errors.append(
                        f"invalid Region-A overlay ordinal {rel}: "
                        f"{header_value} != {expected_header_value}")
            image_meta[image_id] = {
                "image_id": image_id, "path": rel, "sha256": actual_hash,
                "size": actual_size, "file_va_base": hx(file_base),
                "runtime_gp": hx(as_int(config["runtime_gp"])),
                "expected_sha256": (expected_identity or {}).get("sha256"),
                "expected_size": (expected_identity or {}).get("size"),
                "identity_verified": identity_verified,
                "role": role,
                "lifetime": {
                    "resident": "resident_process",
                    "region_b_memory": "exclusive_region_b_memory",
                    "region_a_level": "swapped_region_a_level",
                }[role],
                "header_rule": header_rule,
                "header_value": header_value,
                "expected_header_value": expected_header_value,
            }
        start, end = as_int(source["start"]), as_int(source["end"])
        if source.get("range_type") not in {"code", "data", "thunk"}:
            errors.append(f"unknown range type {image_id}:{hx(start)}:{source.get('range_type')}")
        if int(source.get("size", -1)) != end - start:
            errors.append(
                f"census size mismatch {image_id}:{hx(start)}: "
                f"{source.get('size')} != {end - start}")
        key = (image_id, hx(start))
        if key in seen:
            errors.append(f"duplicate census key {image_id}:{hx(start)}")
            duplicate_count += 1
            continue
        seen.add(key)
        base = {
            "image_id": image_id, "entry": hx(start), "end": hx(end),
            "size": int(source["size"]), "name": source.get("name") or None,
            "space": source.get("space"), "overlay": overlay,
            "range_type": source.get("range_type"),
            "classification": source.get("classification"),
            "confidence": source.get("confidence"), "match": source.get("match"),
            "source": source.get("source"), "discovery": source.get("discovery") or [],
        }
        if source.get("range_type") == "data":
            base.update({"analysis_method": "not_code", "analysis_status": "not_applicable",
                         "unresolved_boundaries": []})
        else:
            # Deferred: an extent cannot be analysed until the WHOLE-IMAGE direct
            # walk has decided which of its addresses other code can enter.
            pending.append((base, rel, file_base, start, end, image_id))
        records.append(base)

    # ---- pass 2: whole-image direct-edge fixed point, then per-extent analysis --
    # The per-function walk starting at that function's own entry is not the same
    # universe as the program's direct control flow. `scene_flow_dispatcher` ran 8
    # of its 393 instructions and reported `analysis_status: ok`, because its
    # eighth instruction is `j 0x8004fb3c` -- out of its own extent -- and the rest
    # is entered from five `j 0x8004fcc0` sites elsewhere. The walk covers the
    # index's full declared universe (direct edges plus verified jr targets --
    # see `cfg_universe`; NOT the gate's direct-only algorithm) rather than one
    # row's subset.
    by_image: dict[str, list[tuple]] = {}
    for item in pending:
        by_image.setdefault(item[5], []).append(item)
    for image_id, items in sorted(by_image.items()):
        word_at: dict[int, int] = {}
        entries: list[int] = []
        for _, rel, file_base, start, end, _ in items:
            entries.append(start)
            blob = blob_cache[rel]
            for pc in range(start, end, 4):
                offset = pc - file_base
                if 0 <= offset + 4 <= len(blob):
                    word_at[pc] = struct.unpack_from("<I", blob, offset)[0]
        # ---- target-root islands, before the walk ------------------------
        # A proved indirect-jump target in unclaimed bytes is invisible to a walk
        # whose word map is built from claimed extents only. Islands are decoded
        # with an explicit stopping proof and their words joined to the map, so
        # the target becomes reachable WITHOUT widening any extent.
        claimed = sorted((start, end) for _, _, _, start, end, _ in items)
        extent_entries = {start for start, _ in claimed}
        blob_for = {rel: blob_cache[rel] for _, rel, _, _, _, _ in items}
        rel0, file_base0 = items[0][1], items[0][2]
        limit_low = min(start for start, _ in claimed)
        limit_high = max(end for _, end in claimed)
        occupied: list[tuple[int, int]] = []
        cursor = limit_low
        for start, end in claimed:
            if start > cursor:
                occupied.append((cursor, start))
            cursor = max(cursor, end)
        for target in sorted({t for values in JR_TARGETS.values() for t in values}):
            if target in word_at or not (limit_low <= target < limit_high):
                continue
            gap = next((row for row in occupied if row[0] <= target < row[1]), None)
            if gap is None:
                continue
            island = decode_target_root_island(
                word_at, blob_for[rel0], file_base0, target, gap, extent_entries)
            if island is None:
                continue
            island.update({"image": image_id, "gap_start": hx(gap[0]),
                           "gap_end": hx(gap[1]),
                           "reached_by": sorted(hx(pc) for pc, values
                                                in JR_TARGETS.items()
                                                if target in values),
                           "widened_an_existing_extent": False,
                           "is_a_census_record": True,
                           "census_record": f"{image_id}:{island['start']}"})
            for pc in range(as_int(island["start"]), as_int(island["end"]), 4):
                word_at[pc] = int.from_bytes(
                    blob_for[rel0][pc - file_base0:pc - file_base0 + 4], "little")
            island["note"] = (
                "promoted to a first-class census record so per-record consumers "
                "(the F01 blocker ledger, the writer-census resolver, the typed-"
                "state compiler) see its accesses; this entry retains only the "
                "discovery provenance and stopping proof, never a second copy of "
                "the code facts.")
            # ---- promotion: the island IS a census record -------------------
            # Hiding it in a side list kept its two register-based stores out of
            # every per-record consumer, which made "the writer falsifier ran
            # over the island" unbankable. The record is analysed by the same
            # analyze_code path as every other extent; the expected census
            # counts are re-pinned intentionally and exact-set verified below.
            role = image_meta[image_id]["role"]
            island_key = (image_id, island["start"])
            if island_key in seen:
                errors.append(f"target-root island collides with census key "
                              f"{image_id}:{island['start']}")
                continue
            seen.add(island_key)
            island_record = {
                "image_id": image_id, "entry": island["start"],
                "end": island["end"],
                "size": as_int(island["end"]) - as_int(island["start"]),
                "name": f"jr_target_island_{as_int(island['start']):08x}",
                "space": "resident" if role == "resident" else "overlay",
                "overlay": None if role == "resident" else image_id,
                "range_type": "code",
                "classification": "game",
                "confidence": "derived",
                "match": None,
                "source": "target_root_island",
                "discovery": ["proved_jr_target_root"],
                "island_provenance": {
                    "reached_by": island["reached_by"],
                    "stopping_proof": island["stopping_proof"],
                    "gap_start": island["gap_start"],
                    "gap_end": island["gap_end"],
                    "widened_an_existing_extent": False,
                },
            }
            records.append(island_record)
            items.append((island_record, rel0, file_base0,
                          as_int(island["start"]), as_int(island["end"]),
                          image_id))
            entries.append(as_int(island["start"]))
            TARGET_ROOT_ISLANDS.append(island)

        _, _, incoming = image_direct_cfg(word_at, sorted(entries))
        for base, rel, file_base, start, end, _ in items:
            try:
                data = function_bytes(blob_cache[rel], file_base, start, end)
                base.update(analyze_code(
                    data, start, image_id, state_map, as_int(config["runtime_gp"]),
                    seeds=cross_extent_entries(incoming, start, end)))
            except (ValueError, struct.error) as exc:
                base.update({"analysis_method": "none", "analysis_status": "fatal",
                             "unresolved_boundaries": [{"kind": "fatal", "error": str(exc)}]})
                errors.append(f"{image_id}:{hx(start)}: {exc}")

    # Reconcile the C receipt against the index's ACTUAL memory-access rows in
    # both directions.  A reader receipt that names a PC the CFG did not decode,
    # or an index access whose mnemonic/width disagrees, is stale evidence and
    # invalidates the index.  The exact address remains dynamic; the half-open
    # range is the proved result and is never collapsed into a representative
    # point address.
    expected_range_readers = set(f01_ranges.get("readers") or {})
    seen_range_readers: set[tuple[str, int]] = set()
    for record in records:
        for access in record.get("memory_accesses") or []:
            key = (record["image_id"], as_int(access["pc"]))
            evidence = (f01_ranges.get("readers") or {}).get(key)
            if evidence is None:
                continue
            seen_range_readers.add(key)
            if (str(access.get("mnemonic")) != evidence["mnemonic"] or
                    int(access.get("width") or 0) != evidence["width"]):
                errors.append(
                    f"F01 range reader decode drift {key[0]}:{hx(key[1])}: "
                    f"index {access.get('mnemonic')}/{access.get('width')} != "
                    f"receipt {evidence['mnemonic']}/{evidence['width']}")
                continue
            access["resolved_address_range"] = {
                "start": evidence["effective_address_range"][0],
                "end": evidence["effective_address_range"][1],
                "semantics": evidence["range_semantics"],
                "table": evidence["table"],
                "basis": "content-verified C instruction range proof",
                "source": str(F01_HARD_TRUTH_PATH.relative_to(ROOT)),
                "source_sha256": f01_ranges["artifact_sha256"],
            }
            access["address_resolution"] = "bounded_static_range"
        if record.get("unresolved_boundaries"):
            record["unresolved_boundaries"] = [
                row for row in record["unresolved_boundaries"]
                if not (row.get("kind") == "unresolved_memory" and
                        (record["image_id"], as_int(row["pc"])) in seen_range_readers)
            ]
    if expected_range_readers != seen_range_readers:
        errors.append(
            "F01 range reader identities and indexed accesses differ as sets: "
            f"receipt-only {sorted((i, hx(p)) for i, p in expected_range_readers - seen_range_readers)}, "
            f"index-only {sorted((i, hx(p)) for i, p in seen_range_readers - expected_range_readers)}")
    f01_range_provenance = {
        key: value for key, value in f01_ranges.items() if key != "readers"
    }
    f01_range_provenance.update({
        "comparison": "exact (image,pc) set in both directions",
        "receipt_only": sorted(f"{image}:{hx(pc)}"
                               for image, pc in expected_range_readers - seen_range_readers),
        "index_only": sorted(f"{image}:{hx(pc)}"
                             for image, pc in seen_range_readers - expected_range_readers),
        "indexed_reader_count": len(seen_range_readers),
    })
    records.sort(key=lambda row: (row["space"], row["image_id"], row["entry"]))
    expected_total = int(config["expected_census"]["records"])
    resident = [row for row in records if row["space"] == "resident"]
    overlay_code = [row for row in records
                    if row["space"] == "overlay" and row["range_type"] == "code"]
    data_rows = [row for row in records if row["range_type"] == "data"]
    thunk_rows = [row for row in records if row["range_type"] == "thunk"]
    resident_code = [row for row in resident if row["range_type"] == "code"]
    fatal = [row for row in records if row["analysis_status"] == "fatal"]
    for image_id in sorted({row["image_id"] for row in records}):
        image_rows = sorted((row for row in records if row["image_id"] == image_id),
                            key=lambda row: as_int(row["entry"]))
        for left, right in zip(image_rows, image_rows[1:]):
            if as_int(left["end"]) > as_int(right["entry"]):
                errors.append(
                    f"overlapping census extents {image_id}:{left['entry']}..{left['end']} "
                    f"and {right['entry']}..{right['end']}")
    for image_id, meta in image_meta.items():
        if meta["role"] != "region_a_level":
            continue
        first_entry = min(as_int(row["entry"]) for row in records
                          if row["image_id"] == image_id)
        expected_entry = as_int(meta["file_va_base"]) + 4
        if first_entry != expected_entry:
            errors.append(
                f"Region-A census entry rule drift {image_id}: "
                f"{hx(first_entry)} != {hx(expected_entry)}")
    expected = config["expected_census"]
    actual_counts = {
        "records": len(records), "resident_records": len(resident),
        "resident_code": len(resident_code), "overlay_code": len(overlay_code),
        "data": len(data_rows), "thunks": len(thunk_rows),
        "canonical_source_records": len(census.get("functions") or []),
        "target_root_island_records": len(TARGET_ROOT_ISLANDS),
    }
    # `records` is the ONE authoritative executable/data universe: the canonical
    # census source PLUS every promoted target-root island. The three counts are
    # pinned separately so a moved canonical census and a moved island set are
    # distinguishable, and the island records are exact-set verified against the
    # decoded islands in both directions -- aggregate equality is not identity.
    island_record_keys = {(row["image_id"], row["entry"], row["end"])
                          for row in records
                          if row.get("source") == "target_root_island"}
    island_decode_keys = {(row["image"], row["start"], row["end"])
                          for row in TARGET_ROOT_ISLANDS}
    if island_record_keys != island_decode_keys:
        errors.append(
            "target-root island records and decoded islands differ as sets: "
            f"record-only {sorted(island_record_keys - island_decode_keys)}, "
            f"decode-only {sorted(island_decode_keys - island_record_keys)}")
    for label, expected_count in expected.items():
        if actual_counts[label] != int(expected_count):
            errors.append(f"{label} census {actual_counts[label]} != {expected_count}")
    return {
        "_comment": "Bytes-free static index. Regenerate with tools/phase4_static_frontier.py --refresh.",
        "schema": "abl-phase4-static-frontier-index/1",
        "generated": str(config["generated"]),
        "source_dependencies": {
            str(path.relative_to(ROOT)): sha256_path(path)
            # Every artifact that feeds reachability belongs here: a CFG
            # universe consuming an unpinned input is an unpinned index. That
            # includes BOTH indirect-target sources -- the phase3 jump tables
            # AND the shared static-ASM gate receipt, whose gate-only jr sites
            # and target-root islands this index consumes.
            for path in (CONFIG_PATH, FUNCTIONS_PATH, SEMANTIC_PATH,
                         RECORD_TYPES_PATH, BUILD_BASELINES_PATH,
                         SEGMENTS_PATH, OVERLAYS_PATH, JR_ARTIFACT_PATH,
                         GATE_ARTIFACT_PATH, F01_HARD_TRUTH_PATH,
                         GAP_SEMANTICS_ARTIFACT_PATH)
            if path.is_file()
        },
        "cfg_universe": ("Four constituents, none substituted for another: "
                         "(1) typed code/thunk extent entries plus decoded "
                         "target-root island records, closed over direct "
                         "branch/jump/call edges and the post-call "
                         "fall-through; (2) the hash-verified phase3 jr-table "
                         "targets recorded in indirect_jump_targets; (3) the "
                         "gate-only jr target sets imported under "
                         "indirect_jump_targets_from_gate, with "
                         "phase3_sites_not_in_gate measured, not assumed; "
                         "(4) target-root code islands decoded from proved jr "
                         "targets landing in unclaimed bytes, each a census "
                         "record with its own stopping proof. This is NOT the "
                         "static-ASM gate's algorithm or universe: the gate "
                         "itself reports indirect_edges_followed: false and "
                         "follows direct edges only."),
        "images": sorted(image_meta.values(), key=lambda row: row["image_id"]),
        "indirect_jump_targets": dict(JR_PROVENANCE),
        "indirect_jump_targets_from_gate": gate_jr,
        "f01_content_verified_reader_ranges": f01_range_provenance,
        "target_root_islands": sorted(TARGET_ROOT_ISLANDS,
                                      key=lambda row: (row["image"], row["start"])),
        "summary": {
            "census_records": len(records), "expected_census_records": expected_total,
            "canonical_source_records": len(census.get("functions") or []),
            "target_root_island_records": len(TARGET_ROOT_ISLANDS),
            "content_verified_range_accesses": len(seen_range_readers),
            "resident_records": len(resident), "resident_code_records": len(resident_code),
            "overlay_code_functions": len(overlay_code),
            "data_records": len(data_rows), "thunk_records": len(thunk_rows),
            "fatal_analysis_errors": len(fatal),
            "duplicate_keys": duplicate_count,
        },
        "records": records, "errors": sorted(set(errors)), "valid": not errors,
    }


def build_overlay_index(index: dict) -> dict:
    config = load_yaml(CONFIG_PATH)
    rows = [row for row in index["records"]
            if row["space"] == "overlay" and row["range_type"] == "code"]
    exact: dict[str, list[str]] = defaultdict(list)
    structural: dict[str, list[str]] = defaultdict(list)
    by_image: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        key = f"{row['image_id']}:{row['entry']}"
        exact[row["exact_fingerprint"]].append(key)
        structural[row["structural_fingerprint"]].append(key)
        resident_calls = [call for call in row["direct_calls"]
                          if 0x80010000 <= as_int(call["target"]) < 0x80082800]
        by_image[row["image_id"]].append({
            "entry": row["entry"], "end": row["end"], "name": row["name"],
            "match": row["match"], "exact_fingerprint": row["exact_fingerprint"],
            "structural_fingerprint": row["structural_fingerprint"],
            "resident_callees": resident_calls,
            "overlay_local_accesses": [access for access in row["memory_accesses"]
                if access["address"] and 0x800B39A0 <= as_int(access["address"]) < 0x80200000],
            "unresolved_boundaries": row["unresolved_boundaries"],
            "semantic_owner": None,
        })
    image_meta = {row["image_id"]: row for row in index["images"]}
    images = []
    for image_id in sorted(by_image):
        meta = image_meta[image_id]
        header_rule = ({
            "bytes": as_int(config["overlays"]["region_a_code_offset"]),
            "code_entry": "base_plus_header",
        } if meta["role"] == "region_a_level" else {
            "bytes": 0, "code_entry": "base",
        })
        images.append({**meta, "header_rule": header_rule,
                       "functions": sorted(by_image[image_id], key=lambda row: row["entry"])})
    exact_clusters = [values for values in exact.values() if len(values) > 1]
    structural_clusters = [values for values in structural.values() if len(values) > 1]
    fmv_path = ROOT / config["fmv"]["path"]
    baseline = load_json(BUILD_BASELINES_PATH)["staged_inputs"][
        str(fmv_path.relative_to(ROOT / "REBUILD/files"))]
    fmv_source = load_json(FMV_PATH)
    fmv_module = {
        "image_id": config["fmv"]["image_id"], "role": "region_b_fmv",
        "path": config["fmv"]["path"], "file_va_base": hx(as_int(config["fmv"]["base"])),
        "runtime_gp": hx(as_int(config["runtime_gp"])), "sha256": sha256_path(fmv_path),
        "size": fmv_path.stat().st_size,
        "identity_verified": (sha256_path(fmv_path) == baseline["sha256"]
                              and fmv_path.stat().st_size == baseline["size"]),
        "lifetime": "exclusive_region_b_fmv",
        "canonical_function_census": "separate_retained_e15_boundary",
        "typed_address_rows": len(fmv_source["player_typed_state"]["fields"]),
        "exact_xrefs": sum(len(row.get("xrefs") or [])
                           for row in fmv_source["player_typed_state"]["fields"]),
        "semantic_owner": None,
    }
    return {
        "schema": "abl-phase4-overlay-semantic-index/1",
        "generated": index["generated"],
        "source_index_sha256": sha256_bytes(render(index)),
        "summary": {
            "overlay_images": len(images), "overlay_code_functions": len(rows),
            "additional_region_b_modules": 1,
            "unique_function_keys": len({f"{row['image_id']}:{row['entry']}" for row in rows}),
            "exact_multi_image_clusters": len(exact_clusters),
            "structural_candidate_clusters": len(structural_clusters),
            "automatic_owner_promotions": 0,
        },
        "images": images,
        "additional_region_b_modules": [fmv_module],
        "exact_clusters": sorted(exact_clusters),
        "structural_candidate_clusters": sorted(structural_clusters),
        "claim_boundary": {
            "candidate_only": True, "semantic_owner_promotions": 0,
            "reason": "Fingerprints nominate comparisons; residency/state/lifecycle differences remain open.",
        },
        "errors": [], "valid": len(rows) == 158 and fmv_module["identity_verified"],
    }


def verify_word(path: Path, base: int, pc: int, expected_word: str) -> bool:
    blob = path.read_bytes()
    offset = pc - base
    if offset < 0 or offset + 4 > len(blob):
        return False
    return struct.unpack_from("<I", blob, offset)[0] == as_int(expected_word)


def build_claim_frontier(index: dict, target_id: str, root_entries: list[str],
                         state_addresses: list[str]) -> dict:
    """Walk the complete resident direct-edge closure for declared roots."""
    resident = [row for row in index["records"]
                if row["space"] == "resident" and row["range_type"] != "data"]
    by_entry = {as_int(row["entry"]): row for row in resident}

    def resolve_function(address: int) -> tuple[dict | None, int]:
        exact = by_entry.get(address)
        if exact is not None:
            return exact, 1
        matches = [row for row in resident
                   if as_int(row["entry"]) < address < as_int(row["end"])]
        return (matches[0] if len(matches) == 1 else None), len(matches)

    roots = []
    errors = []
    for root in root_entries:
        address = as_int(root)
        resolved, match_count = resolve_function(address)
        if resolved is None:
            errors.append(f"root {hx(address)} resolves {match_count} times")
        else:
            roots.append(resolved)
    queue = sorted({as_int(row["entry"]) for row in roots})
    visited: set[int] = set()
    internal_edges = []
    boundaries = []
    state_intersections = []
    state_set = {as_int(value) for value in state_addresses}
    resident_lo = as_int(load_yaml(CONFIG_PATH)["resident"]["text_start"])
    resident_hi = as_int(load_yaml(CONFIG_PATH)["resident"]["text_end"])
    while queue:
        entry = queue.pop(0)
        if entry in visited:
            continue
        visited.add(entry)
        row = by_entry[entry]
        source_key = f"{row['image_id']}:{row['entry']}"
        direct_edges = [
            ("direct_call", edge) for edge in (row.get("direct_calls") or [])
        ] + [
            ("direct_tail_jump", edge) for edge in (row.get("direct_jumps") or [])
        ]
        for edge_kind, call in direct_edges:
            destination = as_int(call["target"])
            target_row, target_count = resolve_function(destination)
            if target_row is not None:
                internal_edges.append({
                    "source": source_key, "pc": call["pc"],
                    "target": f"{target_row['image_id']}:{target_row['entry']}",
                    "kind": edge_kind,
                })
                target_entry = as_int(target_row["entry"])
                if target_entry not in visited:
                    queue.append(target_entry)
            else:
                inside = resident_lo <= destination < resident_hi
                boundaries.append({
                    "source": source_key, "pc": call["pc"], "target": call["target"],
                    "kind": edge_kind,
                    "owner": ("canonical_census_gap" if inside
                              else "declared_out_of_scope"),
                    "reason": (("ambiguous_canonical_resident_extent"
                                if target_count > 1 else "missing_canonical_resident_extent") if inside
                               else "target_outside_resident_census"),
                    "unresolved": inside,
                })
        for edge in row.get("indirect_calls") or []:
            boundaries.append({
                "source": source_key, "pc": edge["pc"], "target": None,
                "kind": "indirect_call", "owner": "indirect_control_flow_unresolved",
                "reason": f"unbounded_register_{edge['register']}", "unresolved": True,
            })
        for edge in row.get("indirect_jumps") or []:
            boundaries.append({
                "source": source_key, "pc": edge["pc"], "target": None,
                "kind": "indirect_jump", "owner": "indirect_control_flow_unresolved",
                "reason": f"unbounded_register_{edge['register']}", "unresolved": True,
            })
        for access in row.get("memory_accesses") or []:
            if access["address"] and as_int(access["address"]) in state_set:
                state_intersections.append({
                    "source": source_key, "pc": access["pc"],
                    "address": access["address"], "access": access["access"],
                    "width": access["width"], "signedness": access["signedness"],
                    "state_joins": access["state_joins"],
                })
        queue.sort()
    boundary_key = lambda row: (row["source"], row["pc"], row["kind"], row["target"] or "")
    return {
        "target_id": target_id,
        "root_function_keys": sorted({f"{row['image_id']}:{row['entry']}" for row in roots}),
        "visited_function_keys": [f"{by_entry[entry]['image_id']}:{by_entry[entry]['entry']}"
                                  for entry in sorted(visited)],
        "internal_edges": sorted(internal_edges,
                                 key=lambda row: (row["source"], row["pc"], row["target"],
                                                  row["kind"])),
        "boundary_edges": sorted(boundaries, key=boundary_key),
        "state_intersections": sorted(
            state_intersections,
            key=lambda row: (row["source"], row["pc"], row["address"])),
        "summary": {
            "roots": len(roots), "visited_functions": len(visited),
            "internal_edges": len(internal_edges), "boundary_edges": len(boundaries),
            "unresolved_boundaries": sum(row["unresolved"] for row in boundaries),
            "state_intersections": len(state_intersections),
        },
        "closure_claimed": False,
        "errors": errors,
        "valid": not errors,
    }


def build_pilots(index: dict) -> dict:
    config = load_yaml(CONFIG_PATH)
    fmv = load_json(FMV_PATH)
    e08 = load_json(E08_PATH)
    event_vm = load_json(EVENT_VM_PATH)
    c13 = load_json(C13_PATH)
    fmv_path = ROOT / config["fmv"]["path"]
    fmv_base = as_int(config["fmv"]["base"])
    fields = fmv["player_typed_state"]["fields"]
    code_scope = fmv["player_typed_state"]["code_scope"]
    player_function = fmv["player_typed_state"]["player_function"]
    code_start, code_end = as_int(code_scope["start"]), as_int(code_scope["end"])
    player_start, player_end = as_int(player_function["start"]), as_int(player_function["end"])
    fmv_blob = fmv_path.read_bytes()
    code_hash_verified = sha256_bytes(function_bytes(
        fmv_blob, fmv_base, code_start, code_end)) == code_scope["sha256"]
    field_addresses = [as_int(field["address"]) for field in fields]
    field_domain_verified = (len(field_addresses) == len(set(field_addresses))
                             and all(code_end <= address < fmv_base + len(fmv_blob)
                                     for address in field_addresses))
    verified_xrefs = []
    for field in fields:
        field_address = as_int(field["address"])
        for xref in field.get("xrefs") or []:
            ins = xref["instruction"]
            pc = as_int(ins["pc"])
            offset = pc - fmv_base
            actual_word = (struct.unpack_from("<I", fmv_blob, offset)[0]
                           if 0 <= offset <= len(fmv_blob) - 4 else None)
            op = (actual_word >> 26) if actual_word is not None else None
            operation = (LOADS.get(op) or STORES.get(op)) if op is not None else None
            expected_width = int(str(xref["width"])[1:]) // 8
            scope_verified = ((xref["scope"] == "player")
                              == (player_start <= pc < player_end))
            verified_xrefs.append({
                "address": field["address"], "pc": ins["pc"], "scope": xref["scope"],
                "word_verified": actual_word == as_int(ins["word"]),
                "field_immediate_verified": (actual_word is not None
                                             and (actual_word & 0xFFFF)
                                             == (field_address & 0xFFFF)),
                "access_contract_verified": bool(
                    operation and operation[1] == xref["access"]
                    and operation[2] == expected_width),
                "code_scope_verified": code_start <= pc < code_end,
                "scope_verified": scope_verified,
            })
    expected_e15 = config["targets"]["E15_fmv"]["expected"]
    e15_actual = {
        "region_b_address_rows": len(fields),
        "absolute_xrefs": len(verified_xrefs),
        "player_xrefs": sum(1 for row in verified_xrefs if row["scope"] == "player"),
        "unclassified_xrefs": sum(1 for row in verified_xrefs if row["scope"] not in {
            "player", "other_fmv_code", "pointer_alias"}),
    }
    e15_valid = (e15_actual == expected_e15 and code_hash_verified
                 and field_domain_verified
                 and all(field.get("xref_count") == len(field.get("xrefs") or [])
                         for field in fields)
                 and len({(row["address"], row["pc"]) for row in verified_xrefs})
                 == len(verified_xrefs)
                 and all(all(row[key] for key in (
                     "word_verified", "field_immediate_verified",
                     "access_contract_verified", "code_scope_verified", "scope_verified"))
                         for row in verified_xrefs))

    e08_frontier = e08["frontier"]
    top = e08_frontier[:5]
    selector_entries = event_vm["static_census"]["vm"]["selector_entries"]
    selector_domain = [row["selector"] for row in selector_entries]
    selector_map = {row["selector"]: row["entry"].upper() for row in selector_entries}
    resident_by_entry = {row["entry"].upper(): row for row in index["records"]
                         if row["space"] == "resident"}
    try:
        manifest_pins = load_repro_manifest_pins()
        source_manifest_valid = True
    except (OSError, ValueError):
        manifest_pins = {}
        source_manifest_valid = False
    callback_joins = []
    for callback in e08["callback_census"]:
        indexed = resident_by_entry.get(callback["start"].upper())
        callback_joins.append({
            "start": callback["start"].upper(),
            "extent_verified": bool(indexed
                                    and indexed["end"].upper() == callback["end"].upper()
                                    and indexed["size"] == callback["size"]),
            **verify_callback_source(callback, manifest_pins),
        })
    program_joins_verified = all(
        selector_map.get(row["program_selector"]) == row["program"]["entry"].upper()
        and row["program"].get("decode_complete") is True
        for row in e08_frontier)
    all_owners_unassigned = all(row["semantic_owner"] is None for row in e08_frontier)
    e08_actual = {
        "uncontrolled_classes": len(e08_frontier),
        "selectors": len(set(selector_domain)),
        "callbacks": len(e08["callback_census"]),
        "priority_slices": len(top),
        "automatic_owner_promotions": sum(
            row["semantic_owner"] is not None for row in e08_frontier),
    }
    expected_e08 = config["targets"]["E08_props_movers_gates"]["expected"]
    e08_valid = (e08_actual == expected_e08
                 and sorted(selector_domain) == list(range(40))
                 and program_joins_verified and all_owners_unassigned
                 and source_manifest_valid
                 and all(row["extent_verified"] and row["source_verified"]
                         for row in callback_joins)
                 and e08["claim_boundary"]["complete_frontier_met"] is False)

    resident_rows = [row for row in index["records"] if row["space"] == "resident"
                     and row["range_type"] != "data"]
    roots = []
    missing_roots = []
    for start, end in config["targets"]["C13_grain_harvester"]["function_roots"]:
        start_i, end_i = as_int(start), as_int(end)
        key = (hx(start_i), hx(end_i))
        intersecting = sorted(
            (row for row in resident_rows
             if as_int(row["end"]) > start_i and as_int(row["entry"]) < end_i),
            key=lambda item: as_int(item["entry"]),
        )
        coverage = start_i
        gaps = []
        covered_rows = []
        for row in intersecting:
            row_start = max(start_i, as_int(row["entry"]))
            row_end = min(end_i, as_int(row["end"]))
            if row_start > coverage:
                gaps.append({"start": hx(coverage), "end": hx(row_start)})
            if row_end > coverage:
                coverage = row_end
            covered_rows.append(row)
        if coverage < end_i:
            gaps.append({"start": hx(coverage), "end": key[1]})
        if gaps or not covered_rows:
            missing_roots.append({"start": key[0], "end": key[1], "coverage_gaps": gaps})
            continue
        roots.append({
            "declared_slice": {"start": key[0], "end": key[1]},
            "census_functions": [{
                "entry": row["entry"], "end": row["end"], "name": row["name"],
            } for row in covered_rows],
            "direct_calls": [call for row in covered_rows
                             for call in row.get("direct_calls", [])],
            "state_accesses": [access for row in covered_rows
                               for access in row.get("memory_accesses", [])
                               if access["state_joins"]],
            "unresolved_boundaries": [boundary for row in covered_rows
                                      for boundary in row.get("unresolved_boundaries", [])],
        })
    residuals = {row["boundary"] for row in c13["named_residuals"]
                 if row.get("intersects_dimension") is True}
    expected_residuals = set(config["targets"]["C13_grain_harvester"][
        "required_open_boundaries"])
    declared_slices = [(as_int(row["start"]), as_int(row["end"]), row["sha256"])
                       for row in c13["static_frontier"]["executable_slices"]]
    configured_slices = [(as_int(start), as_int(end)) for start, end in config[
        "targets"]["C13_grain_harvester"]["function_roots"]]
    resident_path = ROOT / config["resident"]["path"]
    resident_blob = resident_path.read_bytes()
    slice_hashes_verified = (
        [(start, end) for start, end, _ in declared_slices] == configured_slices
        and all(sha256_bytes(function_bytes(
            resident_blob, as_int(config["resident"]["file_va_base"]), start, end)) == digest
                for start, end, digest in declared_slices))
    expected_state_roots = {
        as_int(c13["static_frontier"]["equip_and_follow"]["powerup_flag"]["address"]),
        as_int(c13["static_frontier"]["fifty_grain_reward"]["reachable_health_store"]["address"]),
    }
    configured_state_roots = {as_int(value) for value in config[
        "targets"]["C13_grain_harvester"]["state_roots"]}
    c13_valid = (not missing_roots and residuals == expected_residuals
                 and slice_hashes_verified
                 and configured_state_roots == expected_state_roots
                 and c13["closure_boundary"]["dimension_promoted"] is False)
    root_accesses = [access for root in roots for access in root["state_accesses"]]
    powerup_accesses = [access for access in root_accesses
                        if access["address"] == "0x800A6590"]
    selected_writers = [access for access in powerup_accesses
                        if access["access"] == "write" and access["pc"] == "0x80051EB0"]
    health_accesses = [access for access in root_accesses
                       if access["address"] == "0x800A6594"]
    health_writers = [access for access in health_accesses
                      if access["access"] == "write" and access["pc"] == "0x80055124"]
    state_contract = {
        "powerup_flags": {
            "address": "0x800A6590",
            "reader_signedness": sorted({access["signedness"] for access in powerup_accesses
                                         if access["access"] == "read"}),
            "selected_writer": selected_writers[0] if len(selected_writers) == 1 else None,
        },
        "health_true": {
            "address": "0x800A6594",
            "reader_signedness": sorted({access["signedness"] for access in health_accesses
                                         if access["access"] == "read"}),
            "selected_writer": health_writers[0] if len(health_writers) == 1 else None,
        },
    }
    c13_valid = c13_valid and state_contract["powerup_flags"]["reader_signedness"] == [
        "unsigned"] and state_contract["powerup_flags"]["selected_writer"] is not None \
        and state_contract["health_true"]["reader_signedness"] == ["signed"] \
        and state_contract["health_true"]["selected_writer"] is not None
    e08_claim_frontier = build_claim_frontier(
        index, "E08_props_movers_gates",
        [row["start"] for row in e08["callback_census"]], [])
    c13_claim_frontier = build_claim_frontier(
        index, "C13_grain_harvester",
        [row["census_functions"][0]["entry"] for row in roots],
        [hx(value) for value in sorted(configured_state_roots)])
    e08_valid = e08_valid and e08_claim_frontier["valid"]
    c13_valid = c13_valid and c13_claim_frontier["valid"]
    errors = []
    if not e15_valid:
        errors.append("E15 benchmark mismatch")
    if not e08_valid:
        errors.append("E08 bounded application mismatch")
    if not c13_valid:
        errors.append("C13 bounded application mismatch")
    return {
        "schema": "abl-phase4-static-frontier-pilots/1",
        "generated": str(config["generated"]),
        "source_index_sha256": sha256_bytes(render(index)),
        "source_manifest_sha256": (
            sha256_path(SOURCE_MANIFEST_PATH) if SOURCE_MANIFEST_PATH.is_file() else None),
        "E15_fmv": {
            "expected": expected_e15, "actual": e15_actual,
            "code_hash_verified": code_hash_verified,
            "field_domain_verified": field_domain_verified,
            "all_instruction_words_verified": all(row["word_verified"] for row in verified_xrefs),
            "all_cross_joins_verified": all(all(row[key] for key in (
                "word_verified", "field_immediate_verified", "access_contract_verified",
                "code_scope_verified", "scope_verified")) for row in verified_xrefs),
            "frontier": {
                "root": player_function,
                "code_scope": code_scope,
                "typed_addresses": sorted({row["address"] for row in verified_xrefs}),
                "boundary_owner": "retained_fmv_player_analysis",
                "closure_claimed": False,
            },
            "verified_xrefs": verified_xrefs, "valid": e15_valid,
        },
        "E08_props_movers_gates": {
            "expected": expected_e08, "actual": e08_actual,
            "program_joins_verified": program_joins_verified,
            "callback_joins": callback_joins,
            "priority_slices": [{
                "priority_rank": row["priority_rank"], "type_word": row["type_word"],
                "program_entry": row["program"]["entry"],
                "callbacks": row["callbacks"], "semantic_owner": row["semantic_owner"],
                "next_action": row["next_action"],
            } for row in top],
            "frontier": e08_claim_frontier,
            "dimension_promoted": False, "valid": e08_valid,
        },
        "C13_grain_harvester": {
            "function_roots": roots, "missing_roots": missing_roots,
            "state_roots": [hx(as_int(value)) for value in config["targets"][
                "C13_grain_harvester"]["state_roots"]],
            "state_contract": state_contract,
            "slice_hashes_verified": slice_hashes_verified,
            "frontier": c13_claim_frontier,
            "open_boundaries": sorted(residuals), "dimension_promoted": False,
            "valid": c13_valid,
        },
        "errors": errors, "valid": not errors,
    }


def build_toolchain_manifest() -> dict:
    config = load_yaml(CONFIG_PATH)
    tool = config["toolchain"]
    exporter = ROOT / tool["exporter"]
    return {
        "schema": "abl-phase4-ghidra-toolchain/1",
        "generated": str(config["generated"]),
        "mode": tool["mode"], "app_id": tool["app_id"],
        "version": tool["version"], "flatpak_commit": tool["flatpak_commit"],
        "psx_loader_release": str(tool["psx_loader_release"]),
        "exporter": tool["exporter"],
        "exporter_sha256": sha256_path(exporter) if exporter.is_file() else None,
        "raw_output_policy": "external_only",
        "tracked_output_policy": "bounded_metadata_and_hashes_only",
    }


def build_all() -> tuple[dict, dict, dict, dict]:
    index = build_index()
    overlay = build_overlay_index(index)
    pilots = build_pilots(index)
    toolchain = build_toolchain_manifest()
    return index, overlay, pilots, toolchain


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--query-target", choices=(
        "E15_fmv", "E08_props_movers_gates", "C13_grain_harvester"))
    args = parser.parse_args()
    docs = build_all()
    if args.query_target:
        print(json.dumps(docs[2][args.query_target]["frontier"], indent=2, sort_keys=True))
        return 0 if docs[2][args.query_target]["valid"] else 1
    outputs = (INDEX_OUTPUT, OVERLAY_OUTPUT, PILOT_OUTPUT, TOOLCHAIN_OUTPUT)
    if args.check:
        failures = []
        for path, doc in zip(outputs, docs):
            if not path.is_file() or path.read_bytes() != render(doc):
                failures.append(str(path.relative_to(ROOT)))
        if failures:
            print("[phase4-static-frontier] stale: " + ", ".join(failures), file=sys.stderr)
            return 1
        if not docs[0]["valid"] or not docs[1]["valid"] or not docs[2]["valid"]:
            print("[phase4-static-frontier] retained outputs report invalid", file=sys.stderr)
            return 1
        print("[phase4-static-frontier] PASS: retained indexes reproduce byte-identically")
        return 0
    for path, doc in zip(outputs, docs):
        path.write_bytes(render(doc))
        print(f"[phase4-static-frontier] wrote {path.relative_to(ROOT)}")
    return 0 if docs[0]["valid"] and docs[1]["valid"] and docs[2]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
