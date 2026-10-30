---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Systems.md
aliases:
  - "Systems"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Systems.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Systems.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Systems
type: hub
tags: [hub, systems, executable, overlays]
---

# Systems — Map of Content

> The engine scaffolding: boot executable, scene/state machine, overlays, and the object pipeline. Detail in `docs/EXECUTABLE_AND_OVERLAYS.md`.

## Boot & memory
- `SCUS_942.88` (PS-X EXE, PsyQ): load `0x80010000`, entry `0x8005F690`, `$gp=0x80081d98`, resident `0x80010000`–`0x800827FF`. Map + globals in [[Symbols Index]].
- Anything `≥ 0x80082800` is not file-backed (`.bss`/heap/overlays).

## Scene / state machine
- Main shell `fcn.8004fa40`; gameplay state `fcn.8004ecd4` (calls HUD [[FUNC_800526F4]], walker [[FUNC_800586B0]], pickup pass [[FUNC_80053814]], render driver [[FUNC_800224EC]]).
- Master state `0x800823a0`; main-shell substate `0x8008243c` (mod 6); current scene id `0x80082504`.

## Overlays
Two swap regions — Region A `0x800b39a0` (per-level `LEVEL.BIN`), Region B `0x800b5788` (`MEMORY.BIN`/FMV). See [[Asset - LEVEL.BIN and overlays]].

## Object pipeline
[[LEVEL.DAT object pipeline]] — type-0x3f placements → parser → constructor → contact walker → handlers → HUD.

## Level editor
[[ABL Level Editor]] — standalone Java desktop GUI scaffold in `level_editor/`. It reads DAT files, visualizes type-`0x3f` placements, queues move/append specs, and exports YAML for the existing placement tools without mutating DAT/BIN/CUE files.
[[LEVEL01 Level-Edit Punchlist]] — the consolidated, honest gap/blocker list for fully editing LEVEL01 (ground + collision + every placement: enemies, berries, tokens, grains, FLIK letters, telescopes, spawn, exit). Worked one item at a time.
[[Retail Gameplay Completeness Gap Audit]] — player-facing audit of what is still missing before the RE/editor work looks and behaves like the retail PS1 game across mechanics, objects, levels, power-ups, enemies, and presentation.
[[Campaign Level Coverage Matrix]] — campaign-wide static profile for `RCG-001`: 15 stages → 10 retail level directories/overlay stems, plus every level directory's DAT/RAW/type-0x3f/sidecar inventory.
[[Editor Visual Fidelity Baseline]] — `RCG-002` closure note: live DuckStation is the 1:1 editor verifier; Blender/offline GL are authoring previews with explicit residuals.
[[Level Goal and Exit Trigger Matrix]] — `RCG-003` runtime-save-state baseline: scans `0x800A7E48` sector region codes across the supplied level saves, re-confirms LEVEL01's code-2 exit, and catalogs exposed code-1/3/4 goal/transition sectors for follow-up.
[[Actor model binding catalog]] — `RCG-005` closure note: binds `.ALL`/`.ANM` model families to Flik, seeds/planters, plant type numbers, type-`0x3f` pickup/object kinds, regular enemy families, bosses, harvester variant, and cast/NPC actor families.

## Front-end & HUD
[[Menu and HUD structure]] — title → vine/leaf main menu (Options/Load-Save/Movie Clips/Training/Anthill/levels), pause→exit flow, and the **SELECT status icons** (FLIK letters, health leaf, seed power, lives, grain). HUD draw = [[FUNC_800526F4]]; counters in [[MEM - Player state 800A6500]]. Menu logic/render = un-RE'd (overlay; image-baked text).

## Collectibles & rewards
[[Grain emblem and HUD total mod]] — collect every grain → the **grain emblem** medal + Flik health refill; the gate (`grain == level total`) lives in [[FUNC_80054EAC]] (`0x80055008`), the HUD "collected/total" readout in [[FUNC_800526F4]]. Includes the mod that makes both track the level's real grain total (LEVEL01 → 30, disc `build/ABL_GRAIN30`).

## Seed planting system
[[Seed planting system]] — the plantable **seeds** (carry / recolor with seed tokens / jump-on to grow plants) are a **separate** placement system from the type-0x3f pickups. Per-seed runtime base struct = the live-move handle (`+0x4/0x8/0xc` = XYZ, `+0x40` = rooted/can't-carry flag, `+0x50` = grown sentinel); spawner ctors 0x7d–0x80 (caller `0x8004753c`), loader `0x80049c40`. On-disk placement is in **LEVEL.RAW (compressed, chunk 31)** → a GUI editor needs the [[Finding - LEVEL.RAW is compressed|LZ codec]].

## Resource loading
[[FUNC_8003CF2C]] (resource dispatcher) → [[FUNC_80046330]] (file loader) → [[FUNC_8001CDC0]] (DAT parse) / [[FUNC_8003A318]] (LEVEL.RAW). See [[Asset - LEVEL.DAT]] / [[Asset - LEVEL.RAW]].

## Sub-hubs
[[Geometry]] · [[Rendering]] · [[Collision]] · [[Physics]] · [[Camera]] · [[Assets]]

## Source docs
`docs/EXECUTABLE_AND_OVERLAYS.md`, `docs/LEVEL_OBJECT_PIPELINE.md`, `docs/DECOMPILATION_PLAN.md`.
