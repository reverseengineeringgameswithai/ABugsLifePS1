---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - Collision sector table 800A7E48.md
aliases:
  - "MEM - Collision sector table 800A7E48"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - Collision sector table 800A7E48.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_Collision_sector_table_800A7E48.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

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
| **On-disk record (G33)** | src array @ **global decomp `0xcd248`** (chunk-32 local `0x36570`), **stride `0x4c`**, record `i` ↔ sector `i`; origin (X,Y,Z)≫5 at **`+0x8/+0xc/+0x10`**. **Origin-Y lever on disk = record `+0xc`, value `≪5`** (converter copies, doesn't recompute; planes are relative → origin-only edit shifts floor 1:1). See [[Plan - Terrain+collision matched bump (Option B)]]. |

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
  [[Plan - Terrain+collision matched bump (Option B)]] (blockers #3/#4).

## Related
- Findings: [[Finding - Collision sector table]] · [[Finding - Collision lever sector186]] · [[Finding - Collision on-disk source is chunk 32]] · [[Finding - Visual is not collision]]
- Functions: [[FUNC_8003633C]] · [[FUNC_8001A1DC]] · [[FUNC_8003A318]]
- Fixture: [[Fixture - g30 openground]] · Findings store ids: f6, f11, f12
