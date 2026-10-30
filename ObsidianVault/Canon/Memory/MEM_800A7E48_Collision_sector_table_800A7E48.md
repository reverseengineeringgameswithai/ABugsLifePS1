---
kind: memory
id: MEM_800A7E48
aliases: [MEM_800A7E48, 0x800a7e48, "MEM - Collision sector table 800A7E48", "MEM - Collision sector table", MEM_-_Collision_sector_table_800A7E48]
address: 0x800A7E48
name: Collision_sector_table_800A7E48
status: static_seen
confidence: confirmed
source_state: original_game
system: []
read_by: []
written_by: []
related_structs: []
evidence: []
src_paths: []
patch_policy: unknown
---

# MEM_800A7E48 - Collision sector table 800A7E48

## Purpose

The **collision/floor** source — independent of the visual terrain buffer. This is what Flik actually stands on.

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - Collision sector table 800A7E48
type: memory-structure
address: 0x800A7E48
confidence: CONFIRMED
tags: [memory, collision, g29, g30]
---

# MEM — Collision sector table `0x800A7E48`

> The **collision/floor** source — independent of the visual terrain buffer. This is what Flik actually stands on.

| Field | Value |
|-------|-------|
| **Base** | `0x800A7E48` |
| **Count** | 223 records (count at `[gp+0x508]`; start index `[gp+0x6cc]`=191) |
| **Stride** | `0x30` |
| **Built by** | converter `0x80030F60` (caller `0x800314CC`), scaled `<<5` from decompressed src `0x800F7BF8` |
| **On-disk source** | LEVEL01/LEVEL.RAW **chunk 32** — [[Finding - Collision on-disk source is chunk 32]] |
| **On-disk record (G33)** | src array @ **global decomp `0xcd248`** (chunk-32 local `0x36570`), **stride `0x4c`**, record `i` ↔ sector `i`; origin (X,Y,Z)≫5 at **`+0x8/+0xc/+0x10`**. **Origin-Y lever on disk = record `+0xc`, value `≪5`** (converter copies, doesn't recompute; planes are relative → origin-only edit shifts floor 1:1). See [[Experiment - G29 collision lever validation]]. |

## Sector record layout (0x30, CONFIRMED — G29)
| Offset | Meaning |
|--------|---------|
| +0x00 / +0x04 / +0x08 | origin X / **Y** / Z |
| +0x10 | block ptr → 32-byte collision plane records (`~0x800D0xxx`) |
| +0x14 / +0x1c | AABB min |
| +0x24 / +0x28 | extent |
| +0x2c | flag |

## Edit lever (CONFIRMED)
- Subtract origin **Y (+4)** → lowers the floor; ungrounded Flik falls ~1:1.
- **Localized:** the openground player sector = **sec186**, origin `(20608, 0, -40416)`, record at `0x800A7E48 + 186*0x30 = 0x800AA128` — see [[Finding - Collision lever sector186]]. Lowering only sec186 by −3000 + jump dropped Flik −512 (resolver clamps neighbors; full localized lower needs sec186 + adjacent).
- All 223 lowered together → Flik falls ~1:1.
- Read all 223 in one call with [[API - readArray]] (`base=0x800A7E48, count=223, stride=0x30`).

## Consumed by
[[FUNC_8003633C]] (per-frame movement + collision integrator) resolves floor Y and commits to player Y `0x800A6504` at PC `0x80036cec`. Chain: sector table → `[sector+0x10]` plane records → candidate list `0x8009C230` → resolve helpers → commit.

## Finding Flik's floor sector + clamp set (G33)
The resolver **runs even when Flik is idle** (~3 hits/5 frames at `0x80036cec`), so `0x8009C230` is readable
without movement. **`0x8009C230` = the candidate-plane list** for Flik's current position (≈44 ptrs, dup'd).
Map each plane → owning sector via the sector `+0x10` block ranges (largest `blkptr ≤ plane_addr`).
- **Flik's floor sector** = the candidate sector with origin-Y nearest *below* Flik (spawn spot → **sec124**).
- **Neighbor-clamp set** = ALL candidate sectors (spawn → `{87,89,96,97,105,106,124,126,171}`). A localized
  edit must move the whole set together (origin-Y) or the resolver dilutes it. See
  [[Experiment - G29 collision lever validation]] (the controlled collision lever).

## Related
- Findings: [[Finding - Collision sector table]] · [[Finding - Collision lever sector186]] · [[Finding - Collision on-disk source is chunk 32]] · [[Finding - Visual is not collision]]
- Functions: [[FUNC_8003633C]] · [[FUNC_8001A1DC]] · [[FUNC_8003A318]]
- Fixture: [[Fixture - g30 openground]] · Findings store ids: f6, f11, f12


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Collision sector table 800A7E48.md`
- Migration status: copy-first Canon seed.

## Region-code domain closed campaign-wide (E02, 2026-08-03)

An UNFILTERED census over all 16 level anchors (3,955 sectors, count taken
from the loader's own global `[0x800822A0]`, offline via the committed
save-state parser) proves the complete region-code (+0x2E) domain is
**{0, 1, 2, 3, 4}** — nothing outside the previously assumed 1..4 exists in
retail data. Per-level counts 46..634; disc-side cross-check agrees on
LEVEL01. Consumer binding for every code (player dispatch in 0x80048138,
checkpoint_save 0x80054C90 bails on code 4, mover update 0x8004B940 retires
objects on code 1; codes 2 and 3 share a byte-identical exit body):
`analysis/phase4_e02_consumer_binding.json` ·
[[EXP_2026-08-03_phase4_e02_region_codes]].

## All-level round trip + census (E02b, 2026-08-04)

An independent C reimplementation of the converter, diffed against actual save
RAM (`tools/phase4_e02_collision_roundtrip.c`), round-trips **all 16 scenes
exactly** and corrects/extends this page:

- **The table is authored prefix + runtime tail**: N source records convert
  verbatim (LEVEL01: 178), then runtime-REGISTERED slots follow (LEVEL01: 45,
  degenerate origins). Containers on disc hold ONLY the authored prefix. The
  count global `[0x800822A0]` counts both and is incremented by the
  registration loop at `0x800316C0` (151 times during the Clover load).
- **Two container families carry collision source**: `LEVEL*.RAW` chunk 32
  (compressed, blocks from container offset **8**) and the uncompressed
  `*.ALL` terrain containers — `TERRAIN.ALL` / `TERR1.ALL` — with blocks from
  offset **4**. Both parse with the same converter.
- **Flat sectors inherit the most recent geometry sector's block pointer**
  (base block until the first geometry sector) — not one shared base.
- **Field laws, campaign-proven**: runtime `+0x2E` (region code) ← src
  `+0x2C`; runtime `+0x2C` ← src `+0x14` (same field as runtime `+0x0C`) —
  this resolves the old +0x2C/+0x2E wording tension.
- **Census (16 scenes)**: 58,555 planes / 16,653 groups — 52,518 floors,
  5,686 ceilings, 351 vertical walls; all normals unit-length within authoring
  rounding; every block walk terminates exactly. Campaign split: 3,235 authored
  + 720 runtime-registered = 3,955 sectors.
- **Every scene resolves to a disc container** — there is no runtime-built
  case. Bug Bar is the extreme of the authored/runtime law rather than an
  exception: it authors **ONE** sector (`LEVEL04/LEVEL1.RAW`, decompressed
  offset 487,284) and registers the other 45 at runtime — the numeric
  signature of [[EXP_2026-08-02_phase4_e11_dynamic_geometry]]'s per-tick arena.

⚠️ **Corrections (same day, two rounds).** An earlier version claimed FOUR
scenes were "runtime-BUILT ... no disc-verbatim source in any RAW or DAT";
a later one claimed Bug Bar alone was.
That was wrong: the sweep never covered `.ALL` containers, and a bounds bug in
the tool rejected the right container even once in scope. Live instrumentation
of the operator's fresh-load movie showed the ordinary converter FUNC_80030F60
reading Clover Forest's source from `/LEVEL07/TERRAIN.ALL` at offset 119,628
(container base `0x8017A0A4`, source pointer `0x801973F0`). Writers of this
table during load: `0x80030F84..0x80030FF4` (converter; region code at
`0x80030F94`, block pointer at `0x80030FC4`) and `0x80031670..0x800316B0`
(parent broad-phase). Bug Bar fell the same way once the Thud-fight movie was
replayed: its source is filled by the LEVEL.RAW decompressor `fcn.8001a1dc`
from `LEVEL04/LEVEL1.RAW`; my candidate pre-filter had demanded four matching
records where only one is authored. See
[[EXP_2026-08-04_phase4_e02_collision_roundtrip]].
