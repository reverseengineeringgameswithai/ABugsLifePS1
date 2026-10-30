---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Yellow seed plant behaviors.md
aliases:
  - "Yellow seed plant behaviors"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Yellow seed plant behaviors.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Yellow_seed_plant_behaviors.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Yellow seed plant behaviors
type: system
updated: 2026-07-03
confidence: CONFIRMED (replayed movie; permanence gate caught at the mine detonation)
tags: [system, seed, plant, yellow, shooter, mine, permanence, gameplay]
---

# Yellow seed plant behaviors — solved (shooters + the MINE; seed system COMPLETE)

> [!warning] Canon routing
> Current seed/plant Canon is [[SYS_seed_plant_behaviors]]. Berry projectile facts route through [[SYS_berry_projectile_and_homing]], while descriptor/color safety routes through [[SYS_berry_pickup_render_descriptors]] and [[HOOK_forbidden_patch_ranges]].

> Decoded 2026-07-03 from the operator's **`yellow_seed_levels.movie.json`** (windows 262500–263213 ·
> 263462–263927 · 264100–265000; yellow count-4 duplicates count-3, so three windows cover the lane).
> The operator flagged a Y3 desync — in this replay **all three windows in fact played** (shooters
> spawned + fired, both mines grew, the kill landed), so no redo was needed.
> **Completes the seed system: all five lanes solved.** RE: `src_re/yellow_seed_plants.c`.

## Crack + spawns
Identical **X-butt-slam crack**. Y1 **type 14** @262520 (~666f) · Y2 **type 13** @263495 (~432f) · Y3 **type 11 ×2** @264134/@264410.

## The shooters (types 14 / 13)
Both fire **class-2 berry projectiles** (the same class as Flik's thrown berries):
- **type 14** ("blue berry shooter", handler `0x8005CA7C`): projectile model `+0x24 = 110` (basic/blue).
- **type 13** ("purple homing shooter", `0x8005CA24`): projectile model `+0x24 = 124` (**the MEGA model**).
Their projectiles carry `+0x27 = 0` → **shooter kills are NOT permanent**. Firing is intermittent (trigger law = residual).

## The MINE (type 11, handler `0x8005C918`) — enemy-proximity bomb, PERMANENT
- Mine #1: planted, then **exploded ~90f later when an enemy approached** — the mine slot is **consumed by its own detonation**.
- Mine #2: only Flik nearby → never exploded, wilted normally at ~480f ⇒ **the fuse is enemy-proximity; Flik-safe** (carrying/standing by it is harmless).
- **The kill is PERMANENT**: `G_ENEMIES_REMAINING` 15 → 14 at detonation.
- **Mechanism, caught at the gate** ([[Enemy death and permanence]]):
  `explosion hit-record: class=2000, +0x24=0, `**`+0x27 = 6`**` → s7|=2 → 999-hit → destroy → quota−1`.

> [!success] RCG-022 closure — the second permanent-kill lane CONFIRMED
> The `+0x27==6` lane hypothesized in [[Enemy death and permanence]] ("LIKELY the Mine Plant") is now proven. ABL has exactly **two permanent-kill sources**: the **GOLD berry** (`+0x24==11`) and the **MINE plant** (`+0x27==6`).

## Residuals
- Shooter firing-trigger law (periodic vs proximity) + projectile aiming.
- Mine fuse radius; the explosion class-2000 record's construction site.

## Related
[[Enemy death and permanence]] (lane 2 closed) · [[Seed plant output binding]] · [[Brown seed plant behaviors]] · [[Blue seed plant behaviors]] · [[Green seed plant behaviors]] · [[Purple seed plant behaviors]] · `src_re/yellow_seed_plants.c`
