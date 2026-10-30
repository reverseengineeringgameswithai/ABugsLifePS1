---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Assumptions Register.md
aliases:
  - "Assumptions Register"
migration_action: archive
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Assumptions Register.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Assumptions Register
type: dashboard
updated: 2026-06-18
tags: [dashboard, blockers, assumptions, due-diligence]
---

# Assumptions Register

> The **load-bearing assumptions** the project currently relies on — things treated as true that are not independently proven. Each names what it rests on and what breaks if it is wrong. This complements **[[Hypotheses]]** (which tracks *stated, under-test beliefs*); the items here are mostly *unstated* premises baked into tooling, offsets, and conclusions. An assumption turning out false typically promotes a linked **[[Blockers|blocker]]**.

| # | Assumption (treated as true) | Rests on | If wrong → | Linked |
|---|------------------------------|----------|-----------|--------|
| A1 | The master `Disney-Pixar A Bug's Life (v1.0).bin` is a faithful, unmodified retail dump | A 2012-dated file; boot-EXE + LEVEL01-DAT SHA-1s recorded; ISO volume strings look right | **Every static offset and rebuild could be subtly wrong**; preservation invalid | [[Blocker - Disc provenance is unverified|B12]] |
| A2 | The DuckStation fork's "bit-exact RAM/registers" contract holds and is stable across the build used | The [[API - determinism]] rubric; observed re-run agreement | The basis of *every* `CONFIRMED` dynamic finding weakens; results non-reproducible | [[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]] |
| A3 | r2 auto-derived function boundaries + `anal.gp=0x80081d98` are correct | r2 analysis recorded only in code comments; no persisted DB | Mis-attributed code/data; wrong `[gp+off]` globals; cascading naming errors | [[Blocker - Function boundaries and overlays evade the static call graph|B17]] · [[Blocker - Symbol recovery has no authoritative map|B15]] |
| A4 | ✅ **RESOLVED** — the literal recompressor's output IS accepted by the game | G32 seed-disc operator-booted; the game decompressed the spliced chunk off disc | N/A — confirmed working for modding (byte-exact *original* still needs a PROPACK encoder) | [[Blocker - Recompressor cannot reproduce original compression|B14]] |
| A5 | ✅ **RESOLVED** — the decoder is validated for **all 69** RAW chunks | (1) Live `execTrace` on `0x8001a1dc` from pre-load state: the decompressor loop hits **all 69 chunk-starts (0–68)** at exactly my offline parser's offsets; (2) offline decode is **length-exact (word0) on all 69**; (3) **byte-exact** on chunk0 (oracle) + chunk35 (live) | N/A — segmentation live-confirmed + length-exact for every chunk + byte-exact on samples | [[Blocker - Recompressor cannot reproduce original compression|B14]] · [[Blocker - LEVEL.RAW chunk inventory is mostly unidentified|B9]] |
| A6 | ✅ **VALIDATED (architecture)** — LEVEL01 model generalizes to other levels | **Runtime-confirmed on LEVEL02/03/04/05** (2026-06-18): engine structures at **fixed** addresses every level (collision `0x800a7e48`, player `0x800a6504`, mesh `0x8012c1cc`); data same FORMAT, **per-level** address/count (DATbase + chunk count vary; rec0 = type-0x3f pickups in *all*). Codec/DAT/collision/render all generalize | Only LEVEL01-specific *hardcoded addresses/indices* (DATbase `0x801607f8`, chunk `31/32/35`) are non-portable — re-read per level, don't hardcode | [[Blocker - RE depth is LEVEL01-only|B8]] |
| A7 | Candidate A is *the walkable* visual surface (not a co-planar/adjacent visual chunk) | G28 operator visual test + projection band; **M7 (2026-06-21): spawn floor = DAT/`fcn.80010000` ([[Gap Audit\|GAP-0011]] Verified) + G29 Pass-3 counterfactual ([[Gap Audit\|GAP-0038]] Verified)** | Reduced — visible floor = DAT confirmed; Candidate A is one payload of the DAT floor stratum; full-game generality open ([[Gap Audit\|GAP-0039]]) | [[Blocker - Headline results rest on single-source evidence|B3]] · [[Hypotheses\|H-A]] |
| A8 | ❌ **DISPROVEN (M7, 2026-06-21)** — was: "`fcn.800172dc` / chunk 35 is the visible terrain surface" | §20.1 VRAM-diff = ~99 % occluded + M7 [[Gap Audit\|GAP-0011]] Verified | N/A — refuted; chunk-35/`fcn.800172dc` = occluded shared-mesh layer; the visible floor is LEVEL.DAT/`fcn.80010000` (f13) | [[Blocker - Headline results rest on single-source evidence|B3]] · [[Finding - Visible terrain renderer]] |
| A9 | Collision source = LEVEL.RAW chunk 32, independent of the visual mesh | Sector-table live-edit chain (G29) **+ byte-exact match: live plane `0x800D10E8` = offline chunk32 @ `0xfa60`, linear base `0x800C1688`** (2026-06-18) | Largely confirmed; only the G29 Pass-3 visual≠collision differential remains un-run | [[Blocker - Collision internals are partly undecoded|B18]] · [[Finding - Collision on-disk source is chunk 32]] |
| A10 | ✅ **RESOLVED** — was: "mkpsxiso rebuilds are good enough because the image boots" | Now a measured **whole-image diff** vs the master | N/A — rebuild confirmed **byte-exact** (0/313,897 sectors differ, incl. EDC/ECC, gaps, XA) on 2026-06-18 | [[Finding - Disc rebuild is byte-exact]] |
| A11 | The decompiled C correctly models the binary's behavior | Hand-reading + a few runtime experiments; no compile/link/diff | Undetectable regressions; jump-table "helper functions" are interpretations, not real boundaries | [[Blocker - Decompilation has no build or symbol substrate|B1]] |
| A12 | The untracked critical inputs (findings YAML, `raw_chunk0_*.bin` oracles, save states, the fork) will remain available | They live outside git on one machine, under `~/...` | Loss of any → reproducibility/verification collapses; "byte-exact" becomes unverifiable | [[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]] |
| A13 | The custom LEVEL.RAW LZ is unrelated to a known packer | Independent LZSS RE; no lineage recorded | It is **RNC/PROPACK 2.29** (per the on-disc build log) — a known, documented family; reinventing the encoder was avoidable, and a public decoder may validate it | [[Blocker - Original toolchain ground-truth is unmined|B13]] |

## See also
[[Blockers]] · [[Risk Matrix]] · [[Hypotheses]] · [[Open Questions]] · [[API - determinism]]
