#!/usr/bin/env python3
"""E16 measured against the roadmap's nine-item Definition of Done.

WHY THIS EXISTS
---------------
Phase 4's standard is documented, and it is not the promotion tool. From
`Game Solving Roadmap - From Reconstruction to Reliable Modding.md`:

    A subsystem is not called solved until every item below is satisfied.
    1 original oracle · 2 complete frontier · 3 typed state · 4 lifecycle
    5 original interfaces · 6 campaign breadth · 7 cross-system behavior
    8 source closure · 9 durable evidence

and the Phase-4 exit gate adds: *no unresolved field, dispatch, asset or overlay
intersects the subsystem's behavior without being explicitly bounded*.

`tools/phase4_promotion_preflight.py` encodes exactly these nine (1:1, same
order) and wraps them in registry/debt/packet scaffolding the standard never
asks for. When that scaffolding turned out to be unavailable on master I treated
the tool as the bar and went chasing it. The bar is this document, judged by
review. Hence a scorecard.

THE SCOPE TRAP THIS TOOL REFUSES
--------------------------------
E16 is "scene flow, level/MEMORY/FMV overlays, streaming, loader fixups, asset
residency, unload, and failure paths". Nearly all the evidence covers ONE
sub-area: the three registered-chunk pointer tables. Reporting "item 2 met"
without that qualifier would be the row-level overclaim this row has already had
to retract once. Every entry therefore carries an explicit `scope`, and the
summary counts a scoped pass separately from a row-wide one.

Every cited artifact is checked to exist; a missing one is an error, not a
footnote, because a scorecard citing evidence that is not there is worse than no
scorecard.

Usage: python3 tools/phase4_e16_dod_scorecard.py
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TABLES_SCOPE = "the three registered-chunk pointer tables (0x8009B5A8 / 0x8009C210 / 0x800A65B0)"
ROW_SCOPE = "the whole E16 row (scene flow, overlays, streaming, residency, unload, failure paths)"

ITEMS = [
    {
        "n": 1, "id": "original_oracle",
        "requirement": "original behavior has a deterministic cold-boot reproduction with "
                       "scene/media identity and observable assertions",
        "state": "partial",
        "scope": TABLES_SCOPE,
        "established": "movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json is "
                       "from_boot (5,562 frames) and drives boot -> frontend -> Clover "
                       "Forest. Observable assertions exist and are automated: table "
                       "occupancy must reach >= 30 slots and a loader clear or bulk zero "
                       "must fire as a positive control.",
        "evidence": ["movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json",
                     "analysis/phase4_e16_table_read_watch.json",
                     "analysis/phase4_e16_movie_validation.json",
                     "tools/phase4_e16_validate_movies.py"],
        "missing": "No cold-boot oracle for the overlay load path (MEMORY.BIN, FMV.BIN, "
                   "LEVEL*.BIN), for unload, or for any failure/retry path. The 16 "
                   "campaign movies are state-anchored, not cold-boot.",
        "next_experiment": "Record one from-boot movie that enters and LEAVES a level, so "
                           "unload has an oracle; assert overlay region A contents at both "
                           "boundaries.",
    },
    {
        "n": 2, "id": "complete_frontier",
        "requirement": "relevant callers, callees, callbacks, indirect tables, overlays, "
                       "readers, writers, and downstream consumers have been enumerated",
        "state": "met_in_scope",
        "scope": TABLES_SCOPE,
        "established": "Readers/writers enumerated and CLOSED by materialisation: only 5 "
                       "sites in the entire text segment can form a pointer into these "
                       "windows and all 5 are already enumerated, so no deliberate access "
                       "exists outside the known set. Incidental readers enumerated as a "
                       "family (22 hoisted-load sites). Overlay scope censused at true "
                       "load bases. 30 bounded_residuals, 0 rejections.",
        "evidence": ["analysis/phase4_e16_address_materialization.json",
                     "analysis/hoisted_load_idiom_scan.json",
                     "analysis/phase4_e16_overlay_census.json",
                     "analysis/phase4_e16_promotion_residuals.json",
                     "analysis/phase4_e16_campaign_verdict.json"],
        "missing": "Row-wide the frontier is NOT enumerated: the streaming table "
                   "0x8007EFE8, overlay region A and its 42 entries, the high heap "
                   "allocator, and the LEVEL.RAW/DAT/BIN asset families are unmeasured. "
                   "Item 2 is met for the tables, not for E16.",
        "next_experiment": "Run the materialisation census against 0x8007EFE8 and the "
                           "region-A base; if either yields sites outside a known set, "
                           "that is the next frontier to close.",
    },
    {
        "n": 3, "id": "typed_state",
        "requirement": "important fields have widths, signedness, ownership, valid domains, "
                       "initialization, reset rules, and confidence-backed evidence",
        "state": "partial",
        "scope": TABLES_SCOPE,
        "established": "Each table is a u32 pointer array indexed marker*4; occupied "
                       "windows and slot addressing are pinned in Canon; the marker domain "
                       "is fully mapped from the loader's own dispatch; initialization "
                       "(loader clears at 0x8003A3B8/BC) and the per-load reset rule are "
                       "code-confirmed.",
        "evidence": ["ObsidianVault/Canon/Memory/MEM_8009B4E8_registered_chunk_table_0x30_0x57.md",
                     "ObsidianVault/Canon/Memory/MEM_8009C170_registered_chunk_table_0x28_0x2F.md",
                     "ObsidianVault/Canon/Memory/MEM_800A6450_registered_chunk_table_0x58_0x5F.md",
                     "analysis/phase4_e16_chunk_census.json"],
        "missing": "Ownership is documented informally rather than as a typed-state record, "
                   "and nothing is typed for region A, the streaming table, or the high "
                   "heap. The player block's extent -- which decides whether the 0x58..0x5F "
                   "window is merely ADJACENT to it -- has never been formally bounded.",
        "next_experiment": "Bound the player state block's extent, then record widths/"
                           "ownership/reset for the streaming table 0x8007EFE8.",
    },
    {
        "n": 4, "id": "lifecycle",
        "requirement": "behavior is characterized through creation, repeated use, "
                       "retirement, death/respawn, pause, scene transition, and reload",
        "state": "partial",
        "scope": "one frontend -> gameplay transition",
        "established": "Creation and one transition are measured: two tables are cleared "
                       "per load and one is never cleared, leaving 36 pointers dangling "
                       "into reused high heap with 36/36 markers overwritten -- a hazard "
                       "the retail game never trips because nothing reads them after.",
        "evidence": ["analysis/phase4_e16_resource_lifetime.json",
                     "ObsidianVault/Experiments/EXP_2026-08-04_phase4_e16_resource_lifetime.md"],
        "missing": "Death/respawn, pause, level EXIT/unload, scene-to-scene reload and "
                   "repeated re-entry are all uncharacterised. The measured scope is a "
                   "single transition in a single direction.",
        "next_experiment": "Replay a movie that enters a level, dies, respawns and exits; "
                           "sample the three tables at each boundary.",
    },
    {
        "n": 5, "id": "original_interfaces",
        "requirement": "call/return, live state, stack/ra, hi/lo, GTE, delay-slot, "
                       "memory-effect, callback, overlay and asset-loading contracts are "
                       "known at every boundary the subsystem crosses",
        "state": "partial",
        "scope": "overlay entry ABI and the loader's own contract",
        "established": "Overlay ABI characterised and bracketed by two opposite-erring "
                       "detectors to 42/42 entry points; the loader's dispatch, header "
                       "layout and class split are code-confirmed from its own "
                       "instructions rather than inferred.",
        "evidence": ["analysis/phase4_e16_overlay_abi.json",
                     "analysis/phase4_e16_overlay_starts.json",
                     "asm/hand_written/8003a318_high_heap_loader.s"],
        "missing": "18 of the 42 entries are confirmed by only ONE of the two detectors, "
                   "and no runtime check has been made that a scene actually CALLS the "
                   "entries its overlay implements. Asset-loading contracts at failure "
                   "boundaries are untouched.",
        "next_experiment": "execTrace a range watch over region A during a level load and "
                           "record which of the 42 entries actually execute.",
    },
    {
        "n": 6, "id": "campaign_breadth",
        "requirement": "every applicable level, objective, enemy/actor variant, special "
                       "mode, and exceptional path is covered",
        "state": "partial",
        "scope": "all 16 campaign levels, for the three tables",
        "established": "16/16 campaign levels validated at 60 Hz plus the reference movie "
                       "(17/17 usable, 1,930 events), every event from an enumerated or "
                       "characterised PC. NOT FALSIFIED.",
        "evidence": ["analysis/phase4_e16_movie_validation.json",
                     "analysis/phase4_e16_campaign_verdict.json",
                     "ObsidianVault/Experiments/EXP_2026-08-04_phase4_e16_anypercent_campaign.md"],
        "missing": "Exceptional paths -- load failure, retry, disc error, unload -- are "
                   "uncovered. Breadth is across LEVELS, not across the row's modes: FMV "
                   "and MEMORY overlays are not exercised by these movies.",
        "next_experiment": "Cover the FMV and MEMORY overlay load paths, then an induced "
                           "load failure if one can be provoked safely.",
    },
    {
        "n": 7, "id": "cross_system_behavior",
        "requirement": "interactions with player state, physics, rendering, animation, "
                       "audio, HUD, objectives, save/load and scene transitions are "
                       "validated",
        "state": "open",
        "scope": "rendering hand-off only",
        "established": "The rendering interaction is characterised end to end: registered "
                       "chunks are frontend VRAM images uploaded on demand by "
                       "level_texture_stage / vram_upload_wait, 46/46 satisfying their "
                       "consumer-derived size law and visually confirmed by decoding. The "
                       "player-state relationship is bounded as ADJACENCY, not overlap.",
        "evidence": ["analysis/phase4_e16_registered_chunks.json",
                     "ObsidianVault/Experiments/EXP_2026-08-04_phase4_e16_registered_chunk_consumers.md",
                     "ObsidianVault/Canon/Functions/FUNC_8003C8BC_level_texture_stage.md"],
        "missing": "No validation against physics, animation, audio, HUD, objectives or "
                   "save/load. Scene transitions are touched only by the single lifecycle "
                   "sample. This is the least-served item and is honestly OPEN.",
        "next_experiment": "Pick the two interactions most likely to bite -- save/load "
                           "(does any registered pointer reach the save schema?) and scene "
                           "transition -- and validate those first.",
    },
    {
        "n": 8, "id": "source_closure",
        "requirement": "matching or reviewed semantic source represents the complete "
                       "behavior, and remaining byte/layout mismatches are explicitly "
                       "bounded",
        "state": "partial",
        "scope": "the loader and the two consumers",
        "established": "The loader exists as hand-written asm that assembles against "
                       "pristine, and both consumers are decompiled and reviewed in Canon "
                       "with their addresses pinned.",
        "evidence": ["asm/hand_written/8003a318_high_heap_loader.s",
                     "ObsidianVault/Canon/Functions/FUNC_8003C8BC_level_texture_stage.md",
                     "ObsidianVault/Canon/Functions/FUNC_8003C388_vram_upload_wait.md"],
        "missing": "No C for the loader -- hand asm is matching, not semantic source -- and "
                   "no enumeration of remaining byte/layout mismatches as bounded. Nothing "
                   "for region A or the streaming path.",
        "next_experiment": "Decompile 0x8003A318 to reviewable C via the existing "
                           "dc_m2c_seed pipeline and diff behavior against the hand asm.",
    },
    {
        "n": 9, "id": "durable_evidence",
        "requirement": "Canon describes confirmed original behavior, Experiments hold "
                       "reproductions and causal evidence, and Mods describe private state "
                       "and intended changes",
        "state": "met",
        "scope": ROW_SCOPE,
        "established": "Canon: one system note, three memory notes, two function notes, "
                       "all carrying the completeness argument and the incidental-reader "
                       "warning. Experiments: four, each with its reproduction and its "
                       "retractions recorded. The roadmap carries the row's history "
                       "including corrections.",
        "evidence": ["ObsidianVault/Canon/Systems/SYS_registered_chunk_image_resources.md",
                     "ObsidianVault/Canon/Memory/MEM_800A6450_registered_chunk_table_0x58_0x5F.md",
                     "ObsidianVault/Canon/Functions/FUNC_8003C388_vram_upload_wait.md",
                     "ObsidianVault/Experiments/EXP_2026-08-04_phase4_e16_chunk_roles.md",
                     "ObsidianVault/Experiments/EXP_2026-08-04_phase4_e16_anypercent_campaign.md"],
        "missing": "No Mods note -- correctly, since no E16 mod exists. That clause binds "
                   "only where private state or an intended change exists.",
        "next_experiment": "None required; refresh if an overlay/streaming mod is authored.",
    },
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_dod_scorecard.json"))
    args = ap.parse_args()

    missing_evidence = []
    for item in ITEMS:
        for rel in item["evidence"]:
            if not (ROOT / rel).exists():
                missing_evidence.append({"item": item["id"], "path": rel})

    states = [i["state"] for i in ITEMS]
    out = {
        "_comment": "E16 against the roadmap's nine-item Definition of Done. Regenerate: "
                    "tools/phase4_e16_dod_scorecard.py",
        "generated": str(date.today()),
        "row_id": "E16_streaming_overlays",
        "standard": "Game Solving Roadmap - From Reconstruction to Reliable Modding.md, "
                    "'Definition of Done for a solved subsystem' (9 items), plus the "
                    "Phase-4 exit gate's 'without being explicitly bounded'.",
        "why_not_the_promotion_tool": (
            "tools/phase4_promotion_preflight.py encodes these same nine dimensions 1:1 in "
            "the same order, but wraps them in campaign-registry, debt-ledger and packet "
            "scaffolding the written standard never requires. The standard is judged by "
            "review; the tool is one attempt to automate that judgement."),
        "row_scope": ROW_SCOPE,
        "scope_caveat": (
            "Almost all E16 evidence covers ONE sub-area -- the three registered-chunk "
            "pointer tables. A row-level 'met' would be an overclaim, so each item states "
            "its own scope and `met_in_scope` is counted separately from `met`."),
        "items": ITEMS,
        "summary": {
            "met": states.count("met"),
            "met_in_scope": states.count("met_in_scope"),
            "partial": states.count("partial"),
            "open": states.count("open"),
            "row_is_solved": all(s == "met" for s in states),
        },
        "evidence_missing_from_disk": missing_evidence,
        "verdict": None,
    }
    if missing_evidence:
        out["verdict"] = ("BROKEN SCORECARD -- %d cited artifact(s) do not exist. A "
                          "scorecard citing absent evidence is worse than none."
                          % len(missing_evidence))
    else:
        out["verdict"] = (
            "E16 is NOT solved by the Definition of Done. %d of 9 items met (%d met "
            "row-wide, %d met within a declared sub-area), %d partial, %d open. The "
            "strongest item is 2, complete frontier, which is CLOSED for the three pointer "
            "tables by an argument that does not depend on runtime silence. The weakest is "
            "7, cross-system behavior, which is honestly open. Item 2 being met is exactly "
            "what the roadmap asks -- 'enumerated', with the remainder explicitly bounded "
            "-- and not the empty-intersection-set bar quoted in the B06 note."
            % (states.count("met") + states.count("met_in_scope"), states.count("met"),
               states.count("met_in_scope"), states.count("partial"), states.count("open")))

    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    for i in ITEMS:
        print("  %d %-24s %-13s %s" % (i["n"], i["id"], i["state"], i["scope"][:52]))
    print("\n" + out["verdict"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
