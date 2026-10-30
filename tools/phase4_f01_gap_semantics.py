#!/usr/bin/env python3
"""Build the F01 partial-gap semantics receipt.

The compiled C probe owns instruction decoding and content derivation; this
driver owns repository identities, input generation, and the honest split
between the three evidence tiers this campaign produced:

  content_verified   the sine-table TAIL overlapping the third census gap --
                     the already-established formula re-derived here, exact
                     to the last byte or refused.
  instruction_derived_extent
                     the ATAN table read by atan2_heading -- base, entry
                     width and index domain proved from the reader's own
                     instructions (all twelve words verified), while the
                     analytic content model is APPROXIMATE (a fixed 189-entry
                     subset sits exactly +1 over llround(atan); no uniform
                     multiplier fits, established by interval intersection)
                     and is carried as corroboration, never as the claim.
  entry_pointer_runs runs of >=3 consecutive words that are each exactly a
                     census code/thunk entry, with the false-positive model
                     stated.

Runtime reader attributions from the two replay sessions are carried as
LEADS with their preservation hashes -- they are not census evidence and are
marked so.

Usage:
  tools/phase4_f01_gap_semantics.py \
      --output analysis/phase4_f01_gap_semantics.json [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/phase4_f01_gap_semantics.c"
PARTITION_SOURCE = ROOT / "tools/phase4_f01_library_partition.c"
IMAGE = ROOT / "REBUILD/files/SCUS_942.88"
INDEX_PATH = ROOT / "analysis/phase4_static_frontier_index.json"
SYMBOLS_PATH = ROOT / "symbols/re_symbols.sym"
SCHEMA = "abl-phase4-f01-gap-semantics/2"

# gp-tail data zone for the library-partition annotation: the union span of
# the census gap at 0x8007E8B8 (which ends AT the proven $gp constant) and
# the SPU/file-path gap at 0x8008219C.
PARTITION_ZONE = (0x8007E8B8, 0x800822F0)
GP_VALUE = 0x80081D98  # proven constant (crt0 stup1 materializes it once)

# Named walls: why the remaining unevidenced zone bytes did NOT become a
# census class in this increment. Each names the exact obstruction; reopen
# on a falsifier for that wall, not on re-enthusiasm.
PARTITION_WALLS = [
    "pointer_indirection: libcd parks work-area pointers in variables "
    "(e.g. 0x80081B8C/0x80081B94/0x80081B98) and accesses fields through "
    "loads of those pointers; static constant tracking ends at the load",
    "caller_dependent_index_domain: the libpad port array 0x80081D48 "
    "(stride 4) is indexed by a caller-supplied port; bounding it needs "
    "the caller-domain proof class that blocked the local-base campaign",
    "no_materialized_clear_bounds: CD_init/_padInitSioMode initialize "
    "cells individually or through helpers (e.g. jal 0x8005F7DC with the "
    "area address as an argument); no memset-style loop materializes "
    "(base, end) as constants, so no atan-grade extent proof exists",
]

# The exact unevidenced ranges this campaign scanned for entry-pointer runs.
# PINNED HERE, not read from the census at build time: the census CONSUMES
# this receipt, so deriving the scan input from the census would make the two
# artifacts mutually recursive. The consumer clips every claimed interval to
# its own current gap set, so a stale range here can never widen anything.
SCANNED_RANGES = [
    (0x8001B0BC, 0x8001B1C0), (0x8001B384, 0x8001B3C4), (0x8001B3DC, 0x8001B3F0),
    (0x8001B828, 0x8001CA20), (0x80077080, 0x800771B0), (0x80077458, 0x8007745C),
    (0x80077A8C, 0x80077AF8), (0x80078D84, 0x8007941C), (0x80079DA0, 0x80079E30),
    (0x8007E8B8, 0x80081D98), (0x8008219C, 0x800822F0),
]

RUNTIME_LEADS = {
    "sessions": [
        {"movie": "movies/Phase4/Interpreter/Any% Runs/LEVEL01_AntHill.movie.json",
         "raw": "replay evidence preserved in the external store (gapread_L01.json)"},
        {"movie": "movies/Phase4/Interpreter/Any% Runs/LEVEL03_CouncilChamber.movie.json",
         "raw": "replay evidence preserved in the external store (gapread_L03.json)"},
    ],
    "attributions": {
        "0x8007E8B8_head": "atan2_heading (0x80060BA8/0x80060C34) -- drove the "
                           "instruction derivation above; also LoadImage reads "
                           "other runs of the same gap",
        "0x80077080": "gte_rotation_matrix_setup -- same consumer as the "
                      "verified sine table it extends",
        "0x80078D84": "results_screen_render + type_0x3f contact dispatch",
        "0x8001B0BC": "mover_vm_dispatch_next (the 16-entry dispatch table)",
        "0x800817D4_0x80081D48": "PsyQ libcd work RAM (CdControl/CD_sync/"
                                 "getintr) and libpad SIO state (_padSioRW) -- "
                                 "runtime BSS, not tables",
        "0x800821A2": "cd_audio_mix_control + SPU voice code",
        "silent_in_both_runs": ["0x8001B828 unevidenced runs", "0x80077458",
                                 "0x80077A8C", "0x80079DA0",
                                 "LEVEL03_LEVEL 0x800B4C18"],
    },
    "meaning": ("leads and bounded non-observations for the captured runs "
                "only; none of this section is census evidence"),
}


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_partition(temp: Path, extents: list[tuple[int, int, str]]) -> dict[str, Any]:
    binary = temp / "libpart"
    proc = subprocess.run(
        ["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
         "-o", str(binary), str(PARTITION_SOURCE)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"partition probe failed to build:\n{proc.stderr}")
    (temp / "extents.tsv").write_text(
        "".join(f"{a:08x} {b:08x} {n}\n" for a, b, n in extents))
    run = subprocess.run(
        [str(binary), str(IMAGE), "8000F800", str(temp / "extents.tsv"),
         f"{PARTITION_ZONE[0]:08X}", f"{PARTITION_ZONE[1]:08X}",
         f"{GP_VALUE:08X}"],
        capture_output=True, text=True, check=True)
    result = json.loads(run.stdout)
    result["probe_binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    # per-base aggregation with owner names, derived here from the site list
    bases: dict[str, dict[str, Any]] = {}
    for s in result["sites"]:
        tgt = s["target"]
        b = bases.setdefault(tgt, {"owners": set(), "kinds": set()})
        b["owners"].add(s["function"])
        b["kinds"].add(s["kind"])
    result["distinct_targets"] = {
        t: {"owners": sorted(v["owners"]), "kinds": sorted(v["kinds"])}
        for t, v in sorted(bases.items())}
    return result


def build() -> dict[str, Any]:
    index = json.loads(INDEX_PATH.read_bytes())
    entries = sorted(int(r["entry"], 16) for r in index["records"]
                     if r["image_id"] == "SCUS_942_88"
                     and r.get("range_type") in ("code", "thunk"))
    symbols: dict[int, str] = {}
    for line in SYMBOLS_PATH.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                symbols[int(parts[0], 16)] = parts[1]
            except ValueError:
                continue
    extents = sorted(
        (int(r["entry"], 16), int(r["end"], 16),
         symbols.get(int(r["entry"], 16), f"FUNC_{r['entry'][2:]}"))
        for r in index["records"]
        if r["image_id"] == "SCUS_942_88"
        and r.get("range_type") in ("code", "thunk"))
    # Pin the ENTRY LIST, not the whole index: the index pins THIS receipt in
    # its source_dependencies, so embedding the index sha here would make the
    # two files mutually recursive with no reachable fixed point. The entry
    # list is the receipt's actual input and is invariant under index
    # dependency re-pins.
    entries_text = "".join(f"{e:08x}\n" for e in entries)
    entries_sha = hashlib.sha256(entries_text.encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="gap-semantics-") as raw_temp:
        temp = Path(raw_temp)
        binary = temp / "gapsem"
        proc = subprocess.run(
            ["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
             "-o", str(binary), str(SOURCE), "-lm"],
            capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit(f"probe failed to build:\n{proc.stderr}")
        (temp / "entries.txt").write_text(entries_text)
        (temp / "ranges.txt").write_text(
            "".join(f"{lo:08x} {hi:08x}\n" for lo, hi in SCANNED_RANGES))
        run = subprocess.run(
            [str(binary), str(IMAGE), "8000F800",
             str(temp / "entries.txt"), str(temp / "ranges.txt")],
            capture_output=True, text=True, check=True)
        probe = json.loads(run.stdout)
        binary_sha = hashlib.sha256(binary.read_bytes()).hexdigest()
        partition = build_partition(temp, extents)

    atan = probe["atan_table"]
    sine = probe["sine_tail"]
    if not atan["all_instructions_verified"]:
        raise SystemExit("atan reader instructions failed verification")
    if not sine["content_model_exact"]:
        raise SystemExit("sine tail no longer derives exactly")
    if atan["deviation_histogram"]["other"] != 0:
        raise SystemExit("atan content deviates beyond the recorded +1 class")

    return {
        "schema": SCHEMA,
        "question": ("Which of the remaining unevidenced census gap bytes "
                     "carry instruction-derived or content-derived semantic "
                     "ownership, at which evidence tier?"),
        "inputs": {
            "image_sha256": sha256_path(IMAGE),
            "census_entry_list_sha256": entries_sha,
            "probe_source": str(SOURCE.relative_to(ROOT)),
            "probe_source_sha256": sha256_path(SOURCE),
            "probe_binary_sha256": binary_sha,
            "partition_probe_source": str(PARTITION_SOURCE.relative_to(ROOT)),
            "partition_probe_source_sha256": sha256_path(PARTITION_SOURCE),
            "symbols_sha256": sha256_path(SYMBOLS_PATH),
            "census_entries_supplied": len(entries),
            "scanned_ranges": [[f"0x{lo:08X}", f"0x{hi:08X}"]
                               for lo, hi in SCANNED_RANGES],
        },
        "probe": probe,
        "claims": {
            "content_verified_trig_tail": {
                "interval": sine["gap_overlap"],
                "basis": ("the established sine formula "
                          f"{sine['formula']} re-derived over the overlap; "
                          f"{sine['entries_checked']} entries, 0 mismatches"),
                "tier": "content_verified",
            },
            "reader_indexed_atan_table": {
                "interval": atan["extent"],
                "basis": ("all 12 indexing/fold instruction words of "
                          "atan2_heading verified; base+width+index domain "
                          "instruction-derived. Content model APPROXIMATE: "
                          f"{atan['deviation_histogram']} vs "
                          f"{atan['content_model']} -- the extent claim rests "
                          "on the instructions alone"),
                "tier": "instruction_derived_extent",
            },
            "function_entry_pointer_runs": {
                "intervals": [[r["start"], r["end"]]
                              for r in probe["entry_pointer_runs"]],
                "basis": probe["entry_pointer_model"],
                "tier": "structural_content",
            },
        },
        "runtime_leads": RUNTIME_LEADS,
        "library_workarea_partition": {
            "meaning": ("SEMANTIC ANNOTATION, NOT CENSUS EVIDENCE: the "
                        "machine-derived address-materialization census into "
                        "the gp-tail data zone. Every reported site is a fact "
                        "of the bytes (conservative linear tracker); a missed "
                        "site proves nothing. Moves ZERO census bytes -- the "
                        "walls below say exactly why, and each names its "
                        "reopening falsifier class."),
            "zone": [f"0x{PARTITION_ZONE[0]:08X}", f"0x{PARTITION_ZONE[1]:08X}"],
            "gp_value": f"0x{GP_VALUE:08X}",
            "probe": partition,
            "owners_below_gp": sorted({
                s["function"] for s in partition["sites"]
                if s["kind"] == "addr"
                and int(s["target"], 16) < GP_VALUE}),
            "owners_at_or_above_gp": sorted({
                s["function"] for s in partition["sites"]
                if s["kind"] == "addr"
                and int(s["target"], 16) > GP_VALUE}),
            "owner_lists_meaning": (
                "verbatim observed owner sets either side of the $gp "
                "constant; names come from the symbol table (naming "
                "provenance, not proof of SDK identity). The below-gp set is "
                "dominated by PsyQ API names (libcd/libpad/libspu/libsnd/"
                "libgpu/libapi) with some game-side glue; it is reported "
                "verbatim precisely so no categorical 'all library' claim "
                "is encoded"),
            "walls": PARTITION_WALLS,
            "census_effect": "none",
        },
        "verdicts": {
            "atan_instructions_verified": True,
            "atan_content_model_exact": False,
            "sine_tail_exact": True,
            "entry_pointer_run_bytes": probe["entry_pointer_run_bytes"],
        },
        "authority": {
            "changes_campaign_registry": False,
            "promotes_dimension": False,
            "closes_item_2": False,
            "consumer_must_clip_to_current_gaps": True,
        },
    }


def render(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = render(build())
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != payload:
            print(f"[gap-semantics] STALE: {args.output}", file=sys.stderr)
            return 1
        print(f"[gap-semantics] {args.output}: fresh")
        return 0
    args.output.write_bytes(payload)
    document = json.loads(payload)
    print(f"[gap-semantics] wrote {args.output}")
    for name, claim in document["claims"].items():
        spans = claim.get("intervals") or [claim["interval"]]
        total = sum(int(b, 16) - int(a, 16) for a, b in spans)
        print(f"  {name}: {total} B ({claim['tier']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
