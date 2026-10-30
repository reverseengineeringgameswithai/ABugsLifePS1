#!/usr/bin/env python3
"""Capsule-first runtime evidence for F01's two unevidenced gaps + the table.

The census blocker IMAGE_CENSUS_INCOMPLETE stands on resident gap bytes with no
evidence; its two largest pieces are `0x8007B63C..0x8007D5C0` (8,068 B) and
`0x80075930..0x800769A8` (4,216 B). Per the standing runtime rules, retained
trace capsules are queried BEFORE any live replay. This tool is that query,
run over the ENTIRE retained capsule corpus (never a sample), and its receipt
records four measurements:

  1. gap EXECUTION   -- basic-block starts inside either gap, every frame of
                        every capsule. Zero is a bounded non-observation; it is
                        made meaningful by the static boundary-edge census
                        (zero direct edges enter any gap), so linear overrun
                        into a gap from a preceding block is statically
                        excluded and block STARTS are the right runtime probe.
  2. gap WRITES      -- RAM delta-runs intersecting either gap, excluding each
                        capsule's initial-anchor snapshot frame.
  3. anchor CONTENT  -- the gap bytes at each capsule's anchor compared to the
                        pristine disc image: identical means nothing observably
                        modified them between COLD BOOT and that anchor either.
  4. table VALUES    -- every non-anchor RAM delta intersecting the actor
                        pointer table window [0x80090748, 0x8009084C), each
                        aligned u32 classified null / pool-lattice
                        (0x8009FD80 + k*0x84, k < 64) / OTHER. An OTHER value
                        is the writer-value falsifier FIRING. This corroborates
                        the machine-proved writer value domain at runtime; it
                        is VALUE-level evidence and says nothing about writer
                        PCs or exhaustiveness.

A hit is positive evidence. Absence is a bounded non-observation for the
captured runs only -- NEVER proof that a region is padding, unused, or
semantically owned. This receipt does not change the census, the registry, or
any blocker.

Inputs live in the EXTERNAL evidence store (copyright policy: never commit):
the capsule corpus and the pinned offline reader. Integrity per capsule: the
manifest sha256 is checked against the central preservation index, and the
reader itself re-applies every RAM delta and verifies the per-frame sha256 of
the fully reconstructed 2 MiB image.

Usage:
  tools/phase4_f01_capsule_gap_query.py \
      --output analysis/phase4_f01_capsule_gap_query.json [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "analysis/phase4_trace_capsule_set.json"
CENSUS_PATH = ROOT / "analysis/phase4_frontier_static_census.json"
IMAGE_PATH = ROOT / "REBUILD/files/SCUS_942.88"
IMAGE_BASE = 0x8000F800
RAM_BASE = 0x80000000
SCHEMA = "abl-phase4-f01-capsule-gap-query/1"

GAPS = {
    "gap_8007B63C": (0x8007B63C, 0x8007D5C0),
    "gap_80075930": (0x80075930, 0x800769A8),
}
TABLE_LO, TABLE_HI = 0x80090748, 0x8009084C
POOL_LO, POOL_HI, POOL_STRIDE = 0x8009FD80, 0x800A1E80, 0x84


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_reader(path: Path):
    spec = importlib.util.spec_from_file_location("trace_capsule_query", path)
    module = importlib.util.module_from_spec(spec)
    # Python 3.12+ dataclasses resolve annotations through sys.modules; an
    # unregistered exec'd module makes @dataclass fail during import.
    sys.modules["trace_capsule_query"] = module
    spec.loader.exec_module(module)
    return module


def verify_gap_bounds() -> None:
    """The queried ranges must BE the census's unevidenced gaps, not a memory."""
    census = json.loads(CENSUS_PATH.read_bytes())
    resident = next(row for row in census["image_census"]["images"]
                    if row["id"] == "SCUS_942_88")
    gaps = {(int(g["start"], 16), int(g["end"], 16)): g
            for g in resident["gap_ownership"]}
    for name, span in GAPS.items():
        gap = gaps.get(span)
        if gap is None or gap["disposition"] != "none":
            raise SystemExit(f"{name} {span} is not a disposition-none census gap; "
                             "re-derive the targets before querying")


def sweep(index: dict, reader) -> dict:
    image = IMAGE_PATH.read_bytes()
    capsules = []
    totals = {
        "frames": 0,
        "gap_exec_hits": 0,
        "gap_runtime_write_runs": 0,
        "anchors_identical_to_disc": 0,
        "table_events": 0, "table_values": 0,
        "table_null": 0, "table_lattice": 0,
        "table_values_outside_domain": [],
    }
    for entry in index["capsules"]:
        directory = Path(entry["capsule_directory"])
        manifest_sha = _sha((directory / "manifest.json").read_bytes())
        if manifest_sha != entry["capsule_manifest_sha256"]:
            raise SystemExit(f"{directory.name}: manifest sha mismatch vs the "
                             "preservation index; refusing to use the capsule")
        capsule = reader.Capsule(directory)
        row = {"capsule": directory.name, "movie": entry["movie"],
               "movie_sha256": entry["movie_sha256"], "frames": 0,
               "gap_exec_hits": {}, "gap_runtime_write_runs": 0,
               "table_events": 0}
        first = True
        for item in capsule.frames():
            row["frames"] += 1
            if first:
                first = False
                row["anchor_frame"] = item.frame
                identical = all(
                    bytes(item.state["ram"][lo - RAM_BASE:hi - RAM_BASE])
                    == image[lo - IMAGE_BASE:hi - IMAGE_BASE]
                    for lo, hi in GAPS.values())
                row["anchor_gaps_identical_to_disc"] = identical
                if identical:
                    totals["anchors_identical_to_disc"] += 1
            for pc, count, _ in item.flow:
                for name, (lo, hi) in GAPS.items():
                    if lo <= pc < hi:
                        key = f"0x{pc:08x}"
                        row["gap_exec_hits"][key] = \
                            row["gap_exec_hits"].get(key, 0) + count
                        totals["gap_exec_hits"] += count
            if item.initial:
                continue
            for offset, data in item.changes.get("ram", ()):
                lo_va, hi_va = RAM_BASE + offset, RAM_BASE + offset + len(data)
                for name, (glo, ghi) in GAPS.items():
                    if lo_va < ghi and hi_va > glo:
                        row["gap_runtime_write_runs"] += 1
                        totals["gap_runtime_write_runs"] += 1
                if lo_va < TABLE_HI and hi_va > TABLE_LO:
                    a, b = max(lo_va, TABLE_LO), min(hi_va, TABLE_HI)
                    chunk = data[a - lo_va:b - lo_va]
                    row["table_events"] += 1
                    totals["table_events"] += 1
                    lead = (4 - ((a - TABLE_LO) % 4)) % 4
                    for i in range(lead, len(chunk) - 3, 4):
                        value = struct.unpack_from("<I", chunk, i)[0]
                        totals["table_values"] += 1
                        if value == 0:
                            totals["table_null"] += 1
                        elif (POOL_LO <= value < POOL_HI
                              and (value - POOL_LO) % POOL_STRIDE == 0):
                            totals["table_lattice"] += 1
                        else:
                            totals["table_values_outside_domain"].append({
                                "capsule": directory.name, "frame": item.frame,
                                "va": f"0x{a + i:08x}", "value": f"0x{value:08x}"})
        totals["frames"] += row["frames"]
        capsules.append(row)
    return {"capsules": capsules, "totals": totals}


def build(reader_path: Path) -> dict:
    verify_gap_bounds()
    index_raw = INDEX_PATH.read_bytes()
    index = json.loads(index_raw)
    pinned_reader = index["offline_reader_snapshot"]
    reader_sha = _sha(reader_path.read_bytes())
    if reader_sha != pinned_reader["sha256"]:
        raise SystemExit("offline reader does not match the preservation-index pin")
    reader = load_reader(reader_path)
    swept = sweep(index, reader)
    totals = swept["totals"]
    return {
        "schema": SCHEMA,
        "question": ("Do the retained trace capsules carry any evidence for "
                     "the two largest unevidenced census gaps, and do the "
                     "observed actor-table writes stay inside the machine-"
                     "proved value domain?"),
        "inputs": {
            "capsule_index": str(INDEX_PATH.relative_to(ROOT)),
            "capsule_index_sha256": _sha(index_raw),
            "capsule_count": len(index["capsules"]),
            "offline_reader": str(reader_path),
            "offline_reader_sha256": reader_sha,
            "census": str(CENSUS_PATH.relative_to(ROOT)),
            "census_sha256": _sha(CENSUS_PATH.read_bytes()),
            "image_sha256": _sha(IMAGE_PATH.read_bytes()),
        },
        "domains": {
            **{name: [f"0x{lo:08x}", f"0x{hi:08x}"] for name, (lo, hi) in GAPS.items()},
            "table": [f"0x{TABLE_LO:08x}", f"0x{TABLE_HI:08x}"],
            "pool_lattice": {"base": f"0x{POOL_LO:08x}",
                             "stride": POOL_STRIDE, "slots": 64},
        },
        "integrity": ("per-capsule manifest sha256 checked against the central "
                      "preservation index; the reader re-applies every RAM "
                      "delta and verifies the per-frame sha256 of the full "
                      "reconstructed image, so a corrupted capsule fails the "
                      "sweep rather than passing quietly"),
        "results": swept,
        "verdicts": {
            "gap_execution_observed": totals["gap_exec_hits"] > 0,
            "gap_runtime_writes_observed": totals["gap_runtime_write_runs"] > 0,
            "anchors_with_both_gaps_identical_to_disc":
                f"{totals['anchors_identical_to_disc']}/{len(swept['capsules'])}",
            "table_values_outside_proved_domain":
                len(totals["table_values_outside_domain"]),
            "writer_value_falsifier_fired":
                bool(totals["table_values_outside_domain"]),
        },
        "meaning": {
            "what_a_zero_is": (
                "a BOUNDED NON-OBSERVATION over the captured universe -- "
                f"{len(swept['capsules'])} capsules, {totals['frames']} frames, "
                "plus boot-to-anchor content evidence -- never proof that the "
                "bytes are padding, unused, or semantically owned. The census "
                "gaps remain unevidenced and IMAGE_CENSUS_INCOMPLETE stands."),
            "block_start_caveat": (
                "runtime execution is probed at basic-block STARTS; linear "
                "overrun into a gap from a preceding block is excluded "
                "STATICALLY by the boundary-edge census (zero direct edges "
                "enter any gap, all seven successor kinds), so the two "
                "evidence classes close each other's blind spot"),
            "table_result_is_not_exhaustiveness": (
                "value-level corroboration of the proved writer domain over "
                "captured runs only; no writer PCs are observed and the "
                "writer-universe exhaustiveness gate is untouched"),
            "named_missing_domains": [
                "reads of any queried range (capsules record execution flow "
                "and RAM deltas, not loads)",
                "writer PCs for observed table writes",
                "jalr caller identity for the dispatched handlers",
            ],
            "escalation": ("the named missing domains justify a live "
                           "isolated Interpreter-movie replay with accessLog "
                           "watches and a positive control, per the standing "
                           "runtime rules"),
        },
        "authority": {
            "changes_campaign_registry": False,
            "changes_census_or_blockers": False,
            "promotes_dimension": False,
        },
    }


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    index = json.loads(INDEX_PATH.read_bytes())
    reader_path = Path(index["offline_reader_snapshot"]["absolute_path"])
    if not reader_path.is_file():
        print("[capsule-gap-query] external evidence store unavailable "
              f"({reader_path}); cannot regenerate", file=sys.stderr)
        return 2
    payload = render(build(reader_path))
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != payload:
            print(f"[capsule-gap-query] STALE: {args.output}", file=sys.stderr)
            return 1
        print(f"[capsule-gap-query] {args.output}: fresh")
        return 0
    args.output.write_bytes(payload)
    document = json.loads(payload)
    verdicts = document["verdicts"]
    totals = document["results"]["totals"]
    print(f"[capsule-gap-query] wrote {args.output}")
    print(f"  capsules {len(document['results']['capsules'])} | frames {totals['frames']}")
    print(f"  gap exec hits {totals['gap_exec_hits']} | gap runtime write runs "
          f"{totals['gap_runtime_write_runs']} | anchors identical "
          f"{verdicts['anchors_with_both_gaps_identical_to_disc']}")
    print(f"  table: {totals['table_events']} events / {totals['table_values']} values "
          f"({totals['table_null']} null, {totals['table_lattice']} lattice, "
          f"{verdicts['table_values_outside_proved_domain']} OUTSIDE)")
    print(f"  writer-value falsifier fired: {verdicts['writer_value_falsifier_fired']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
