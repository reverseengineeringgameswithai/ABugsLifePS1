---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Purple seed plant behaviors.md
aliases:
  - "Purple seed plant behaviors"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Purple seed plant behaviors.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Purple_seed_plant_behaviors.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Purple seed plant behaviors
type: system
updated: 2026-07-03
confidence: CONFIRMED (deterministic movie; all four equip transitions observed)
tags: [system, seed, plant, purple, berry, gold, homing, mega, gameplay]
---

# Purple seed plant behaviors — solved (the berry-grant map CLOSED)

> [!warning] Canon routing
> Current seed/plant Canon is [[SYS_seed_plant_behaviors]]. Berry descriptor/color safety is [[SYS_berry_pickup_render_descriptors]] and [[HOOK_forbidden_patch_ranges]]. Do not use Blackberry descriptor edits as evidence that native purple/mega/homing seed visuals can share `0x80082030..0x8008203C`.

> Decoded 2026-07-03 from the operator's **`purple_seed_levels.movie.json`** (windows 133250–133571 ·
> 133796–134109 · 134350–134769 · 135000–135406). **Closes the long-open HRE-004/RCG-004 residual
> "purple ctor → berry-kind map."** RE source: `src_re/purple_seed_plants.c`.

## Crack + shape
Identical **X-butt-slam crack**. All four tiers grow **plant type 6** (the berry-carrier) with a per-tier `extra`; its handler `0x8005C6F0` spawns **one** berry-grant contact object (`ctor = (extra>>12)+0x1F`, one-shot via slot bit3) which Flik collects to arm a berry (`equip 0x800a6597`).

## The map (live: plant → grant object → equip transition)
| Tier | extra | grant type | walker action | **equips** | retail |
|---|---|---|---|---|---|
| 1 | `0x4000` | 35 | 35 | **1 blue/super** (@133396) | Blue/Super Berry |
| 2 | `0x2000` | 33 | 33 | **2 homing** (@133921) | Green/Homing Berry |
| 3 | `0x1000` | 32 | 36 | **4 MEGA** (@134488) | "stronger homing" |
| 4 | `0x3000` | 34 | 34 | **3 GOLD** (@135205) | Gold Berry |

Observed equip walk across the movie: `0 → 1 → 2 → 4 → 3`. Matches the retail matrix row-for-row (tier-3's "purple/stronger homing" = the **mega** berry).

## Unification — grant objects vs. gold-drop glyph
These are the **same contact-object grant types 32–35** cataloged in `src_re/enemy_drops.c`: a purple-4 plant produces the literal **type-34 gold-berry pickup** that arms/equips gold, and blue count-3's bubble shield is the `extra 0` case (ctor `0x1F`) of the same handler. The [[Gold-berry drop on non-gold kills]] mod is intentionally different: it uses the same contact-object allocator, but spawns a **type-120 spinning gold-kill glyph** and a walk-over hook that credits the tagged enemy without equipping gold.

## Lifetimes
Standard wilt chain ([[Blue seed plant behaviors]] §expiry): ~300–378 frames across the four plants.

## Residuals
- None purple-specific. (Yellow lane = the last one; needs a level where its shooter/mine models load.)

## Related
[[Seed plant output binding]] (residual closed) · [[Brown seed plant behaviors]] · [[Blue seed plant behaviors]] · [[Green seed plant behaviors]] · [[Gold-berry drop on non-gold kills]] · `src_re/purple_seed_plants.c`
