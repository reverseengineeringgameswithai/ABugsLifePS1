---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - RE depth is LEVEL01-only.md
aliases:
  - "Blocker - RE depth is LEVEL01-only"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - RE depth is LEVEL01-only.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - RE depth is LEVEL01-only
type: blocker
id: B8
severity: LOW
category: disc-layout / runtime
confidence: CONFIRMED
tags: [blocker, major, levels, streaming, generality]
updated: 2026-06-22
---

# 🟠 B8 — Deep RE is LEVEL01-only; streaming/caching and other levels unmodeled

> Almost every geometry/collision/pickup finding — chunk indices, RAM addresses, the 1248-site relocation count, the pickup-kind maps — is validated on **LEVEL01 alone**. The disc has **10 level dirs and 15 stage variants**, plus a streaming/caching loader the project never modeled.

> [!check] Update (2026-06-18, B8 offline) — **formats generalize; content is per-level.** Walked all 10 levels offline (no emulator): the LEVEL.RAW PROPACK chunk container + the LEVEL.DAT parser run unchanged on every level (LEVEL01 = 69 chunks ✓). **Every level has type-0x3f pickups** (47–77, no 70-cap); the 33548-frame texture format recurs everywhere. But **chunk indices and record-type sets are per-level** (chunk count 45–73; record types vary widely) — LEVEL01's `31/32/35` + `records 1–10 = paths` maps are not portable, re-identify by content/type. → [[Finding - Level formats generalize, content is per-level]]. **Residual:** per-level role re-identification + runtime spot-checks. The **level-warp mechanism is now mapped** (lever `[0x80082504]` = target stage; full load chain; 15-stage→dir map) → [[Finding - Level-warp mechanism]] — but a **verified live warp is not yet executed** (`npc` unsettable blocks a direct call; needs the SM-substate trigger or an instruction-patch stub). **Severity → Medium.**

> [!check] **Update (2026-06-18, B8 RUNTIME) — architecture validated live across 5 levels.** Loaded operator start-saves for **LEVEL02/03/04/05** (internal stages 3/2/6/10) and confirmed the LEVEL01 model holds at runtime, with a clean **fixed-engine vs per-level-data** split:
> - **Engine structures = FIXED addresses, populated every level** (LEVEL01 findings transfer directly): collision sector table **`0x800a7e48`**, player-Y/state **`0x800a6504`**, mesh/render buffer **`0x8012c1cc`** ([[FUNC_800172DC]]).
> - **Data = same FORMAT, per-level address/count** (read at runtime, never hardcode): **`DATbase` varies** (`0x8015e22c / 0x80125c44 / 0x801430d8 / 0x8015baac`, vs LEVEL01 `0x801607f8`); DAT **record count varies** (6/2/1/7 vs 11) — but **rec0 = type-0x3f pickups in *every* level** ⇒ pickup format generalizes; LEVEL.RAW **chunk count varies** (45/55/65/63 vs 69) with the **same container** (decoder walks all).
> - **Models generalize** — each level loads its own cast identically (GRUB/GGRASSH, THUMPER, BBIRD/DRAGFLY, HSPIDER/FLY/WASP) → [[Finding - Character ALL model format]].
> ⇒ **A6 validated**: the LEVEL01 architecture generalizes; only the LEVEL01-specific *hardcoded addresses/indices* are non-portable (re-read per level). Residual is now just the warp execution + per-level chunk-index re-identification. **Severity → Low.**

> [!check] **Extended to the WHOLE GAME (2026-06-18).** Operator start-saves now cover **12 stages** (`level02`–`level13` = internal stages 2,3,4,5,6,7,9,0xb,0xc,0xd,0xe + LEVEL01). Every one confirms the same model: **fixed engine addresses** (`0x800a7e48` collision, `0x8012c1cc` mesh — populated in all) + **per-level data** (`DATbase` ranges `0x80106b34`–`0x8015e22c`; each loads its own cast). ⇒ B8 generality is **comprehensively confirmed across all stages**, not just a sample. Only on-demand per-level *chunk-index* re-identification (done when editing a given level) + the niche warp execution remain. **Effectively resolved.**

**Severity:** ~~Major~~ → **Low** (formats + engine structures runtime-validated across 5 levels) · **Impact:** Medium · **Likelihood:** Low · **Confidence:** CONFIRMED · **Difficulty:** Medium

## Audit reconciliation (2026-06-22)
**TRUE STATUS = PARTIALLY ADDRESSED (substantially).** Cross-level generality is now verified well beyond the offline format walk:
- **Visible-floor model proven per-pixel on a second level.** [[Experiment - LEVEL02 floor source]] confirms the fcn.80010000 visible-floor model on LEVEL02 (= on-disc LEVEL03) with **4 dynamic methods**, replayable via `tools/trace_level02_floor.py`.
- **GAP-0039 ✅** — floor format generalized **11/11 levels** + a deep collision map on LEVEL02 (sector table `0x800a7e48`, 602×0x30 records, **motion-validated**).
- **GAP-0034** — enemy AI decoded cross-level (scenes 1/3/4/5/6/10).

Frontmatter `severity` reconciled to **LOW** to match the body. **Not fully closed** — named OPEN residuals: streaming/caching loader (`0x8003a388 → ~0x801cc390`, `fcn.8005d654`, `TERRAIN.ALL`) **UNMODELED**; **no LIVE non-LEVEL01 visual-edit counterfactual**; deep chunk map beyond LEVEL02 not done; reloc flag-`0x20` path never exercised; verified live warp not done. **Keep OPEN.**

## What is known (evidence)
- Disc has `LEVEL00`–`LEVEL10` (LEVEL00 = dev/test stage — it ships the leaked build log, [[Blocker - Original toolchain ground-truth is unmined|B13]]). The EXE maps **15 stage variants (1A…5C)** onto the 10 dirs (`level01\level1a`, `level03\level1b`, …).
- Only `REBUILD/files/LEVEL01/LEVEL.DAT` is staged/modified (with a `.orig`); doc subject-mention counts: LEVEL01 = 48 files, LEVEL02 = 5, LEVEL03–10 = 7 combined. A non-mutating `phase6_cross_level` sweep validated only the DAT *decoder* across levels — no deep RE.
- LEVEL01-specific facts that may not generalize: RAW chunk indices **31/32/35**, the **1248** relocation sites ([[FUNC_8001CDC0]]), and the reloc **flag-`0x20`** path that LEVEL01 *never sets* (so sites C/E are **never exercised** — [[Finding - Relocation-aware DAT append]]).
- Streaming/caching is unmodeled: an unanalyzed high-heap **streamed** load (`0x8003a388 → ~0x801cc390`) and a cached-terrain skip (`fcn.8005d654`) were noted in G20 and never resolved; the `TERRAIN.ALL` cache path got **0 EXEC hits** and was dropped.

## Why it matters
- Generality of the entire model is unproven; a full level editor or full RE must cover all 10/15 levels. The untested reloc flag-`0x20` path is a concrete latent bug surface for the DAT-append tool on other levels.

## Dependencies
- **Gates the generality of:** [[Blocker - LEVEL.RAW chunk inventory is mostly unidentified|B9]] · [[Blocker - LEVEL.DAT non-pickup records are undecoded|B10]] · [[Blocker - Collision internals are partly undecoded|B18]], and the hardcoded constants in the DAT-edit pipeline. **Related assumption:** A6.

## Research opportunity (direction only)
- Re-running the existing LEVEL01 toolchain (catalogs, RAW codec, chunk walk) across LEVEL02–10 would test generality directly; decoding the EXE's stage-variant table would map 1A–5C → dirs; tracing the streamed loader and the `.all` cache path would show whether they carry geometry the LEVEL01 analysis missed. (Direction only.)

## Evidence & sources
- vault: [[Asset - LEVEL.DAT]] · [[Finding - Relocation-aware DAT append]] · [[FUNC_8001CDC0]] · [[Asset - Disc image and rebuild]]
- corpus: `DAT/phase6_cross_level.md`, `src_re_geometry/geometry_g20_sidecar_loader_trace.md`, `geometry_g21_file_read_caller_map.md`, EXE stage-variant table
- See also: [[Blockers]] · [[Risk Matrix]]
