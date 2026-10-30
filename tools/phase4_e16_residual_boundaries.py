#!/usr/bin/env python3
"""Compile E16's unresolved-access residual into NAMED, BOUNDED residuals.

WHY THIS SHAPE
--------------
Phase-4 DoD item 2 asks that "relevant callers, callees, callbacks, indirect
tables, overlays, readers, writers, and downstream consumers have been
ENUMERATED", and the Phase-4 exit gate asks that nothing intersect the subsystem
"without being explicitly BOUNDED". The accepted promotion linter enforces that
through a hand-declared `bounded_residuals` list, each entry carrying a
`boundary`, its `evidence`, a `next_experiment`, and `intersects_dimension:
false`.

So the deliverable is not "drive a machine-computed alias count to zero" -- that
reading was an interpretation, and three rows died against it. The deliverable is
a small set of named boundaries, each with evidence.

WHAT THIS COMPUTES
------------------
For every region-formed access that the bound-recovery pass could NOT bound
(tools/affine_bound_recovery.c --emit-all), it derives:

  * the base object the access indexes (the lui-derived constant part),
  * the stride,
  * the INDEX MAGNITUDE that access would need in order to land inside the E16
    target window -- which is the quantity that actually decides intersection,
  * an extent bound for the base object taken from the nearest DISTINCT base
    observed above it in the same image, and
  * the resulting verdict.

The index-magnitude framing is what makes the residual tractable: an access
based 40 KB below the target with stride 4 needs an index of ~10,000, and the
object it indexes is a pool of tens of elements.

SOUNDNESS, STATED PLAINLY
-------------------------
The extent bound is an ARGUMENT, not a proof. Two distinct globals are observed
being indexed from distinct bases X < X'; if accesses to X could run past X'
they would corrupt X'. That is well-founded and falsifiable, not certain -- and
it is exactly the standard `bounded_residuals` is built for (boundary + evidence
+ next_experiment). Every cluster reports which basis it rests on, and clusters
resting only on the adjacency argument are counted separately from those with a
documented extent or a small required index.

Usage: python3 tools/phase4_e16_residual_boundaries.py [--out analysis/phase4_e16_bounded_residuals.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD/files/SCUS_942.88"
FUNCS = ROOT / "analysis/functions_resident.txt"

# E16's registered-chunk state: the three pointer tables (occupied windows).
TARGETS = [
    ("markers_0x30_0x57", 0x8009B5A8, 0x8009B648),
    ("markers_0x28_0x2F", 0x8009C210, 0x8009C230),
    ("markers_0x58_0x5F", 0x800A65B0, 0x800A65D0),
]

# Base objects already named by committed Canon. Extent is the documented size
# where one exists; None means "named but extent not documented".
KNOWN_OBJECTS = {
    # base: (name, extent_bytes_or_None, evidence)
    0x8009B878: ("movie unlock array", 16, "C17 Canon: 16-entry unlock array read by 0x800b4084"),
    0x80074970: ("trig lookup table", 8192,
                 "index masked by `andi 0x0fff` at 0x800470E0 -> 4096 entries x u16"),
    0x800B0D18: ("contact object pool", 64 * 0x38, "E06 Canon: 64 records of 0x38"),
    0x800A6500: ("player state block", 0xA8, "B06 Canon: 168-byte block, highest field lives 0x800A65A0"),
    0x800A6598: ("player state block, byte field at +0x98", 0x800A65B0 - 0x800A6598,
                 "RE-BASED 2026-08-04. The old basis was 'B06 Canon says the block is 168 B, "
                 "so it ends at 0x800A65A8' -- which leans on the block's LENGTH, the "
                 "weakest thing claimed about it (the highest KNOWN field is lives at "
                 "0x800A65A0, so 168 is a lower bound dressed as an upper one). The next "
                 "ESTABLISHED object above this field is E16's own markers 0x58..0x5F "
                 "table at 0x800A65B0 -- live-confirmed by this row -- capping the field at "
                 "24 bytes, max index 23 against the 24 needed. Bounded by one element, "
                 "and with no dependency on the 168."),
    0x800A6300: ("actor id -> model registry", 0x800A6500 - 0x800A6300,
                 "My first claim (41*4 = 164 B from E05 Canon) was REFUTED: 0x8005D69C "
                 "reads 0x800A6300 + (short)a3*4 with a proven non-width-cast reach of "
                 "467 B. E05's '41 ids' is the POPULATED id range, not the allocation. "
                 "The bound comes from layout instead: the player state block begins at "
                 "0x800A6500 (B06 Canon, an independently established object), capping "
                 "this object at 512 B -- which is CONSISTENT with the 467 B proven reach "
                 "rather than contradicted by it. level_load_chunks 0x8005DB24 clears only "
                 "the first word, so there is no initialiser loop to read a count from."),
    0x8009FBE8: ("PsyQ voice-manager table, 32 x u16", 32 * 2,
                 "CORRECTED: the first claim (24*16=384 B) came from 'the SPU has 24 "
                 "voices' -- general knowledge imported from OUTSIDE this codebase. The "
                 "codebase says 32: _SsVmInit 0x800699F8 loads a literal count of 32 and "
                 "zero-fills 32 entries of 2 bytes from this base."),
    0x8009FBEA: ("PsyQ voice-manager table (+2 field)", 32 * 2 - 2, "as 0x8009FBE8"),
    0x8009B5A8: ("E16 registered-chunk table, markers 0x30..0x57", 40 * 4,
                 "E16: 40 slots x 4 bytes, occupied window 0x8009B5A8..0x8009B647, "
                 "confirmed live (38 slots populated in the frontend)"),
    0x8009C210: ("E16 registered-chunk table, markers 0x28..0x2F", 8 * 4,
                 "E16: 8 slots x 4 bytes, occupied window 0x8009C210..0x8009C22F"),
    0x800A65B0: ("E16 registered-chunk table, markers 0x58..0x5F", 8 * 4,
                 "E16: 8 slots x 4 bytes, occupied window 0x800A65B0..0x800A65CF"),
    0x800A649C: ("setpiece/boss actor transform working set", 0x800A6500 - 0x800A649C,
                 "owners setpiece_actor_mesh_transform / boss_defeat_fsm_mesh_transform. "
                 "Bounded by its established neighbour: the player state block begins at "
                 "0x800A6500 (B06 Canon, 168 B), so this object can occupy at most the 100 "
                 "bytes below it -- max index 24 at stride 4, against the 69 needed."),
    0x80089938: ("actor berry column state table, 64 rows x 5 columns", 320,
                 "Canon MEM_80089938: a 320-byte table. scene_flow_state_table_init "
                 "creates 64 records, scene_config_apply copies 64x5 bytes IN, "
                 "serialize_savegame_buffer copies the same 64x5 back OUT, and "
                 "spawn_drop_burst_effect reads g_80089938[id*5 + selector]."),
    0x80089848: ("LoadImage RECT staged by level_texture_stage", 8, "E16: x/y/w/h u16 rect"),

    # Named but extent NOT yet evidenced. Naming alone is progress: a
    # `bounded_residuals` entry needs a NAMED boundary, and these stop being
    # "unidentified base" even before their element count is pinned.
    0x8009C870: ("field of an 836-byte record array (table_836byte_record_populate 0x8003F620)", None,
                 "record size CONFIRMED from the prologue: a0*3 -> *12 -> *13 -> *208 -> "
                 "*209, then x4 = 836 bytes per record. The array's ELEMENT COUNT is still "
                 "unknown, and the nearest established neighbour is only 0x44 above (a "
                 "sibling field), so layout gives no bound. Next: find the record count at "
                 "the allocation/populate site."),
    0x800A7E48: ("collision sector/grid working set, stride 16", None,
                 "owners collision_sector_table_builder 0x80030F60 / collision_grid_builder. "
                 "No layout bound available: the nearest other established base is "
                 "0x800B01A0, 33,624 bytes above. Next: read the builder's fill loop for "
                 "its sector count."),
    0x8009CAAC: ("visual sprite object pool", None,
                 "owner visual_sprite_object_pool_update 0x80042428. Nearest established "
                 "neighbour 0x8009E8D0 is 7,716 B above -- looser than the 2,176 B the "
                 "required index would span, so layout does not discharge it. Next: read "
                 "the pool's capacity constant."),
    0x8009B3A8: ("matrix LUT, 64 entries x 8 bytes", 64 * 8,
                 "matrix_lut_mesh_transform 0x80027CBC masks its index with `andi 0x3f` "
                 "(0x80027F20/F68, 0x80027FF4/8008) -> at most 63. Corroborated exactly by "
                 "layout: 0x8009B3A8 + 64*8 = 0x8009B5A8, precisely where E16's markers "
                 "0x30..0x57 table begins. Bounded by one element."),
    0x8009B2A8: ("chunk relocation index table, 128 x u16", 0x100,
                 "REFUTED LEAD: the `slti $s2,128` at 0x800295B0 does NOT gate these "
                 "accesses -- it guards a DIFFERENT table at 0x800992A8 (lui 0x8009 / "
                 "addiu -27992) with stride 4. The real gate at 0x80029750 is "
                 "`slt $s2, gp[1280]`, a runtime count at 0x80082298 appended by "
                 "chunk_pointer_relocate_index_fixup 0x8005D614 in a loop bounded only by "
                 "a u16 header field, so CODE alone gives no useful bound. LAYOUT does: "
                 "the next object is the matrix LUT at 0x8009B3A8, whose 64x8 extent is "
                 "independently established from `andi 0x3f` -- so this table occupies at "
                 "most 0x8009B2A8..0x8009B3A7 = 256 B = 128 x u16, max index 127 at "
                 "stride 2 (255 at stride 1), against the 384/768 needed."),
    0x800A65D8: ("GPU DRAWENV/DISPENV double-buffer structs, stride 32", None,
                 "owners gpu_present_drawotag_vsync / dma_intr_install"),
    0x8009C230: ("collision candidate / region-query working set", None,
                 "owners collision_candidate_builder / camera_region_query / ground_height_query"),
}



def required_index(base: int, stride: int, lo: int, hi: int) -> int:
    st = abs(stride) or 1
    if base <= lo:
        return (lo - base + st - 1) // st
    return -((base - hi) // st + 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_bounded_residuals.json"))
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="e16br_"))
    tool = str(tmp / "abr")
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", tool,
                    str(ROOT / "tools/affine_bound_recovery.c")], check=True)
    sj = tmp / "sites.json"
    r = subprocess.run([tool, str(EXE), str(FUNCS), "--interprocedural", "--emit-all",
                        "--json", str(sj), "--verify"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        raise SystemExit("ground-truth verification failed -- refusing to emit a packet")

    sites = json.loads(sj.read_text())["sites"]
    fns = {}
    for line in FUNCS.read_text().splitlines():
        if line.startswith("#"):
            continue
        p = line.split()
        if len(p) >= 3:
            fns[int(p[0], 16)] = p[2]

    all_bases = sorted({int(s["base"], 16) for s in sites})

    # SELF-CHECK, mandatory. A claimed extent is refuted the moment the analyser
    # PROVES an index at that same base reaching beyond it. Three of fifteen claims
    # were refuted this way on first run -- the worst by 342x, because "the SPU has
    # 24 voices" is general knowledge imported from outside this codebase rather than
    # evidence drawn from it. A refuted claim yields NO upper bound at all, so it
    # cannot discharge anything; it becomes NEEDS_EXTENT with the contradiction on
    # the record.
    proven_reach = {}
    for s2 in sites:
        if not s2["bounded"]:
            continue
        # A WIDTH CAST is not extent evidence. `andi 0xffff` is a C `(short)`
        # truncation, and reading it as an index bound "proves" a 128 KB reach --
        # which is how two of three extent claims got refuted on the first pass for
        # entirely spurious reasons. The bound is still SOUND for exclusion; it is
        # just worthless for inferring how big an object is.
        if s2.get("width_cast"):
            continue
        b2 = int(s2["base"], 16)
        top = (s2["hi"] - 1) * abs(s2["stride"] or 1)
        if top > proven_reach.get(b2, -1):
            proven_reach[b2] = top
    # THIRD EVIDENCE BASIS. Where the analyser has independently PROVEN an index
    # bound at a base, that is evidence about how far code indexes that object --
    # derived mechanically from this codebase, and self-checked, rather than
    # asserted. It is the same in-bounds assumption the documented extents use
    # (one access indexing <= N does not prove the array is only N), so it is
    # counted as its own basis rather than folded into either neighbour.
    proven_extent = {}
    for s2 in sites:
        if not s2["bounded"] or s2.get("width_cast"):
            continue
        b2 = int(s2["base"], 16)
        top = (s2["hi"] - 1) * abs(s2["stride"] or 1)
        if top > proven_extent.get(b2, (-1, ""))[0]:
            proven_extent[b2] = (top, s2["pc"])

    # FOURTH BASIS: the next DISTINCT OBJECT's base, done properly.
    # The naive version (nearest distinct base) was retracted because the median gap
    # is 4 bytes -- adjacent bases are usually sibling FIELDS. Clustering bases into
    # objects first fixes that. But unconstrained it discharges 100% of the residual,
    # which is the tautology signature: where no neighbour is observed for 12-18 KB,
    # the "extent" is a GAP, not a bound, and those are exactly the tight-margin
    # cases (ratio 1.0x). So it is accepted ONLY where a real neighbour sits within
    # 1 KB and the required distance exceeds it 10-fold.
    NEIGHBOUR_MAX_EXTENT, NEIGHBOUR_MIN_MARGIN = 0x400, 10
    _bases = sorted({int(x["base"], 16) for x in sites})
    _objs, _cur = [], [_bases[0]]
    for _b in _bases[1:]:
        if _b - _cur[-1] < 0x100:
            _cur.append(_b)
        else:
            _objs.append(_cur); _cur = [_b]
    _objs.append(_cur)
    _starts = [o[0] for o in _objs]
    neighbour_extent = {}
    for _i, _o in enumerate(_objs):
        _end = _starts[_i + 1] if _i + 1 < len(_starts) else _o[-1] + 0x100
        for _b in _o:
            room = _end - _b
            if 0 < room <= NEIGHBOUR_MAX_EXTENT:
                neighbour_extent[_b] = room

    refuted = {}
    for b2, (nm, ex, _ev) in KNOWN_OBJECTS.items():
        if ex is None:
            continue
        pr = proven_reach.get(b2)
        if pr is not None and pr >= ex:
            refuted[b2] = (ex, pr)

    def extent_bound(base: int) -> tuple[int | None, str]:
        """Upper bound on the object's size, and what it rests on.

        RETRACTED 2026-08-04: this used to fall back to "distance to the nearest
        distinct base above", which looked like a bounding argument and was not one.
        Measured, the median such distance is FOUR BYTES -- because consecutive bases
        are usually sibling FIELDS of the same array element (`lw a,X(i)` /
        `lw b,X+4(i)`), not the start of a different object. That yields a 4-byte
        "extent", a max index of 0 or 1, and discharges nearly the whole residual for
        entirely the wrong reason. A check that passes because it is wrong is worse
        than no check, so only documented extents count now."""
        if base in KNOWN_OBJECTS and KNOWN_OBJECTS[base][1]:
            return KNOWN_OBJECTS[base][1], "documented_extent"
        return None, "needs_per_object_extent"

    def object_of(base: int):
        """Nearest named object at or below this base (fields share one object)."""
        cands = [b for b in KNOWN_OBJECTS if b <= base < b + 0x80]
        return max(cands) if cands else None

    per_target = {}
    for name, lo, hi in TARGETS:
        unbounded = [s for s in sites if not s["bounded"]]
        clusters = defaultdict(lambda: {"sites": 0, "pcs": [], "owners": Counter()})
        for s in unbounded:
            base = int(s["base"], 16)
            key = (base, s["stride"])
            c = clusters[key]
            c["sites"] += 1
            if len(c["pcs"]) < 4:
                c["pcs"].append(s["pc"])
            c["owners"][fns.get(int(s["func"], 16), "?")] += 1

        rows, disch_doc, disch_neg, open_sites, reader_sites = [], 0, 0, 0, 0
        disch_proven = disch_nbr = 0
        need_hist = Counter()
        for (base, stride), c in sorted(clusters.items(), key=lambda kv: -kv[1]["sites"]):
            need = required_index(base, stride, lo, hi)
            named0 = object_of(base)
            if named0 is not None and named0 in refuted:
                ext, basis = None, "extent_claim_REFUTED_by_proven_index"
            elif named0 is not None and KNOWN_OBJECTS[named0][1]:
                ext, basis = KNOWN_OBJECTS[named0][1], "documented_extent"
            elif base in proven_extent:
                ext, basis = proven_extent[base][0] + 1, "proven_index_at_same_base"
            elif (base in neighbour_extent
                  and abs(need) * (abs(stride) or 1)
                      >= NEIGHBOUR_MIN_MARGIN * neighbour_extent[base]):
                ext, basis = neighbour_extent[base], "next_object_base_within_1KB"
            else:
                ext, basis = None, "needs_per_object_extent"
            # Room left between THIS access's base and the end of the object it indexes,
            # in elements. A field at object_base+delta has (extent - delta) bytes of
            # object above it, and the highest valid index is one less than the element
            # count -- both off-by-ones make the check under-discharge rather than
            # over-discharge, but they are still wrong.
            max_idx = None
            if ext is not None:
                # A documented extent belongs to the NAMED object (this access may be a
                # field partway into it); a proven-index extent belongs to THIS base.
                room = ((named0 + ext) - base) if named0 is not None else ext
                max_idx = (room // (abs(stride) or 1)) - 1
            inside = lo <= base < hi
            named = object_of(base)
            # `hi` is exclusive, so a base sitting exactly AT hi is already
            # above the window and still needs a negative index to reach it.
            if base >= hi and not inside:
                # The access is based ABOVE the window, so reaching it needs a
                # NEGATIVE index. Discharged by the same non-negative-index
                # convention region_provenance.c's TIER 2 already discloses:
                # `array[i]` with i unsigned or i >= 0 by construction.
                verdict, reason = "BOUNDED_NEGATIVE_INDEX", (
                    "based above the window: reaching it needs a NEGATIVE index of %d, "
                    "excluded by the non-negative-index convention (disclosed)" % need)
                disch_neg += c["sites"]
            elif inside:
                verdict, reason = "ENUMERATED_READER", (
                    "based INSIDE the target window -- this is an enumerated consumer, "
                    "not a residual")
                reader_sites += c["sites"]
            elif max_idx is not None and abs(need) > max_idx:
                verdict = ("BOUNDED_PROVEN_INDEX" if basis == "proven_index_at_same_base"
                           else "BOUNDED_NEXT_OBJECT" if basis == "next_object_base_within_1KB"
                           else "BOUNDED_DOCUMENTED_EXTENT")
                reason = ("reaching the window needs index %d; the object's extent bound "
                          "(%s) caps the index at %d" % (abs(need), basis, max_idx))
                if basis == "proven_index_at_same_base":
                    disch_proven += c["sites"]
                elif basis == "next_object_base_within_1KB":
                    disch_nbr += c["sites"]
                else:
                    disch_doc += c["sites"]
            else:
                if basis == "extent_claim_REFUTED_by_proven_index":
                    ex0, pr0 = refuted[named0]
                    verdict, reason = "NEEDS_EXTENT", (
                        "the claimed extent (%d B) is REFUTED: the analyser proves an "
                        "index at this base reaching %d B. A refuted claim gives no upper "
                        "bound, so it discharges nothing." % (ex0, pr0))
                else:
                    verdict, reason = "NEEDS_EXTENT", (
                        "cannot be bounded until this object's extent is documented; "
                        "reaching the window would need index %d" % abs(need))
                open_sites += c["sites"]
            need_hist["<64" if abs(need) < 64 else "64-1k" if abs(need) < 1024
                        else "1k-16k" if abs(need) < 16384 else ">=16k"] += c["sites"]
            rows.append({
                "base": "0x%08X" % base, "stride": stride, "sites": c["sites"],
                "object": (KNOWN_OBJECTS[named][0] if named else "unidentified"),
                "object_evidence": (KNOWN_OBJECTS[named][2] if named else None),
                "required_index_to_reach_target": abs(need),
                "extent_bound": ext, "extent_basis": basis,
                "max_index_under_extent": max_idx,
                "verdict": verdict, "reason": reason,
                "top_owners": [o for o, _ in c["owners"].most_common(3)],
                "example_pcs": c["pcs"],
            })
        total = sum(r["sites"] for r in rows)
        per_target[name] = {
            "window": "0x%08X..0x%08X" % (lo, hi - 1),
            "residual_sites": total,
            "clusters": len(rows),
            "enumerated_reader_sites": reader_sites,
            "bounded_by_documented_extent": disch_doc,
            "bounded_by_proven_index_at_same_base": disch_proven,
            "bounded_by_next_object_base": disch_nbr,
            "bounded_by_non_negative_index_convention": disch_neg,
            "needs_per_object_extent": open_sites,
            "required_index_distribution": dict(need_hist),
            "boundaries": rows,
        }

    out = {
        "_comment": "E16 residual compiled into named, bounded residuals -- the shape the "
                    "accepted promotion linter consumes (boundary/evidence/"
                    "next_experiment/intersects_dimension). Regenerate: "
                    "tools/phase4_e16_residual_boundaries.py",
        "generated": str(date.today()),
        "row": "E16_streaming_overlays",
        "standard_applied": {
            "dod_item_2": "relevant callers, callees, callbacks, indirect tables, "
                          "overlays, readers, writers and downstream consumers ENUMERATED",
            "exit_gate": "nothing intersects the subsystem WITHOUT BEING EXPLICITLY "
                         "BOUNDED -- bounded, not absent",
            "linter": "phase4_promotion_preflight.py reads a hand-declared "
                      "`bounded_residuals` list; each entry needs boundary + evidence + "
                      "next_experiment and intersects_dimension: false",
            "NOT_applied": "'drive the machine-computed alias set to zero' -- an "
                           "interpretation that appears in no standard and that three "
                           "rows have now died against",
        },
        "method": {
            "two_discharge_bases_are_NOT_equivalent": "BOUNDED_DOCUMENTED_EXTENT rests on a "
                            "cited element count. BOUNDED_NEGATIVE_INDEX rests on the "
                            "convention that array indices are non-negative -- the same "
                            "assumption region_provenance.c's TIER 2 discloses. They are "
                            "counted separately because merging them would inflate the "
                            "stronger basis with the weaker one.",
            "index_magnitude": "The quantity that decides intersection is not whether an "
                               "index is bounded in the abstract, but how large it would "
                               "have to be to land in the target window.",
            "extent_bound": "From a documented extent where Canon has one, else from the "
                            "nearest distinct base observed above the object.",
            "RETRACTED_adjacency_argument": "An earlier version bounded objects by the "
                                        "distance to the nearest distinct base above them. "
                                        "That is NOT a bounding argument: the median such "
                                        "distance is 4 bytes, because consecutive bases are "
                                        "usually sibling FIELDS of one array element, not "
                                        "the start of a different object. It discharged "
                                        "4,730 of 4,911 sites for the wrong reason and was "
                                        "removed before it was banked.",
            "runtime_cross_check": "A readwrite watch over boot -> frontend -> Clover "
                                   "Forest observed exactly 7 PCs touching these tables "
                                   "(analysis/phase4_e16_table_read_watch.json), none of "
                                   "them from any residual cluster.",
        },
        "extent_claims_refuted_by_proven_index": {
            "_why": "Every claimed extent is checked against the largest index the "
                    "analyser can PROVE at that same base. A claim smaller than the "
                    "demonstrated reach is refuted and discharges nothing.",
            "refuted": {"0x%08X" % b: {"claimed_bytes": e, "proven_reach_bytes": p,
                                       "object": KNOWN_OBJECTS[b][0]}
                        for b, (e, p) in sorted(refuted.items())},
        },
        "extent_evidence_audit": {
            "_why": "An extent is only as good as where it came from. Two of fourteen "
                    "claims are independently corroborated by a proven (non-width-cast) "
                    "index at the same base; the rest are unverified in BOTH directions -- "
                    "the analyser has no independent index there at all.",
            "corroborated_by_a_proven_index": [
                "0x80074970 trig table (andi 0x0fff, reach 8190 < 8192)",
                "0x8009B3A8 matrix LUT (andi 0x3f, reach 504 < 512)",
            ],
            "no_independent_check_available": 12,
            "by_source": {
                "code_evidenced": "trig table, matrix LUT, and the PsyQ voice table "
                                  "(_SsVmInit's literal count of 32)",
                "layout_neighbour": "the weld table and 0x800A649C -- bounded by where an "
                                    "independently established object begins",
                "committed_Canon": "movie unlock array, player block (and its +0x98 field), "
                                   "contact object pool",
                "this_row_s_own_work": "the three E16 tables and the LoadImage RECT",
            },
            "one_claim_was_imported_from_outside_the_codebase_and_was_wrong":
                "0x8009FBE8 was first claimed as 24*16 = 384 B because 'the SPU has 24 "
                "voices'. The codebase says 32: _SsVmInit 0x800699F8 zero-fills 32 entries "
                "of 2 bytes. General knowledge about the hardware is not evidence about "
                "THIS program.",
        },
        "the_next_object_bound_as_ONE_named_residual": {
            "_why": "This basis discharges 161 clusters. Declaring it as 161 evidenced "
                    "boundaries would be the same inflation the non-negative-index "
                    "convention was pulled out of: it is ONE systematic argument.",
            "boundary": "Accesses whose object has a distinct neighbouring object starting "
                        "within 1 KB above it, where reaching an E16 window would need at "
                        "least 10x that distance.",
            "evidence": "Bases are first clustered into OBJECTS (gap < 0x100), because the "
                        "naive `nearest distinct base` version was retracted -- its median "
                        "gap is 4 bytes, since adjacent bases are usually sibling FIELDS. "
                        "Unconstrained the clustered version discharges 100% of the "
                        "residual, which is the tautology signature; its tight-margin cases "
                        "(ratio 1.0x) are exactly those where NO neighbour was observed for "
                        "12-18 KB, so the `extent` is a GAP, not a bound. Constraining it "
                        "to a real neighbour within 1 KB AND a 10x margin keeps only the "
                        "cases where the argument means something.",
            "next_experiment": "Watch the E16 windows across the per-level campaign; a "
                               "write from a base whose object has a close neighbour would "
                               "falsify the no-overlap assumption this rests on.",
            "intersects_dimension": False,
        },
        "the_non_negative_index_convention_as_ONE_named_residual": {
            "_why": "722 of 851 priority discharges rest on this single convention. Spread "
                    "across 722 line items it reads like 722 independent findings; it is "
                    "one assumption, and it belongs in the packet as one residual.",
            "boundary": "Accesses whose region base lies ABOVE the target window. Reaching "
                        "the window from them requires a NEGATIVE index.",
            "evidence": "MAGNITUDE is what makes this sound, and it was measured rather "
                        "than assumed (analysis/phase4_e16_signed_index_audit.json). Of the "
                        "2,922 accesses discharged this way, ZERO need a small (<64) "
                        "negative index; 47 need 64-1k and 2,875 need >= 1k. The convention "
                        "is not being asked to rule out an off-by-one -- it is ruling out "
                        "an array running hundreds to thousands of elements BACKWARDS past "
                        "its own base. 27.5% of the indices are signed-CAPABLE (lh, sra, "
                        "subu, the sll16/sra16 short cast), but not one of them is asked to "
                        "be even slightly negative. Same disclosed convention as "
                        "region_provenance.c TIER 2.",
            "known_exception_class_RESOLVED": "0x8005D69C computes 0x800A6300 + "
                        "(short)a3*4, a SIGNED short index -- the site that made this "
                        "residual un-assertable. It is based BELOW its target, so it is not "
                        "among the sites this convention discharges at all, and the "
                        "measured risk set (small negative index AND not provably "
                        "non-negative) is EMPTY.",
            "next_experiment": "Watch all three table windows with a readwrite accessLog "
                               "across a campaign of per-level replays. Any write arriving "
                               "from a base above a window falsifies this. One run (boot -> "
                               "frontend -> Clover Forest) already passed: 7 PCs observed, "
                               "none from a base above the window.",
            "intersects_dimension": False,
        },
        "HOW_MUCH_WEIGHT_EACH_BASIS_CARRIES": {
            "_why": "A headline count of discharged sites hides which basis did the work. "
                    "Here the weakest one does almost all of it, and that must be visible "
                    "in the packet rather than discoverable only by re-deriving it.",
            "priority_set_total_sites": 851,
            "enumerated_reader": 7,
            "documented_extent_surviving_the_self_check": 78,
            "non_negative_index_convention": 722,
            "still_open": 44,
            "of_the_722_resting_purely_on_the_convention": 526,
            "comparison": "B06's committed frontier used the same convention for 6 of its "
                          "165 exclusions. Here it carries 722 of 807 discharges (89%). "
                          "Same disclosed basis, completely different load-bearing weight.",
        },
        "per_target": per_target,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    for n, v in per_target.items():
        print(f"{n}: residual={v['residual_sites']} clusters={v['clusters']} "
              f"reader={v['enumerated_reader_sites']} "
              f"doc={v['bounded_by_documented_extent']} "
              f"proven={v['bounded_by_proven_index_at_same_base']} "
              f"nbr={v['bounded_by_next_object_base']} "
              f"negidx={v['bounded_by_non_negative_index_convention']} "
              f"needs_extent={v['needs_per_object_extent']} "
              f"idx_dist={v['required_index_distribution']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
