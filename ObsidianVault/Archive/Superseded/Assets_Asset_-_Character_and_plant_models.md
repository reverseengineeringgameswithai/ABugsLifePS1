---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - Character and plant models.md
aliases:
  - "Asset - Character and plant models"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - Character and plant models.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_Character_and_plant_models.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - Character and plant models
type: asset
tags: [asset, models, all, anm, characters, plants]
updated: 2026-06-18
---

# Asset — Character / plant / prop models (`.ALL` + `.ANM`)

> The game's authored 3D actors ship as paired **`NAME.ALL`** (model) + **`NAME.ANM`** (animation), a single Traveller's Tales custom scheme used game-wide. Format decoded 2026-06-18 (live + offline) → [[Finding - Character ALL model format]]. Was [[Blocker - Character and plant model formats are unreversed|B7]] (Major, 0%).

## Inventory (disc)
- **78 `.ALL`** + **58 `.ANM`** under `REBUILD/files/`:
  - `CHARS/` (13) — FLICK, GYPSY, HEIM, MANNY, ROSIE, SLIM, DIM, FRAN, MOS, GRUB, WASP, FLY, BADBUG (+ `.ANM`)
  - `CHARS2/` (14), `CHARS3/` (14), `CHARS4/` (3) — ATTA, DOT, MOLT, BBIRD, FDIM, ACORN, ATTAFLIK, FLICKD/P, FLIKHARV, …
  - `PLANTS/` (11) + `PLANTS2/` (3) — PLANT01–14
  - `BITS/` (2) — `SEED.ALL`, `PLANTTER.ALL`
  - `LEVELxx/` (1–2 each) — terrain `.ALL` meshes (same container)
- `.ALL` sizes ~4.5–18 KB; `.ANM` 224 B–178 KB (FLICK, the hero, is largest = 40 animations).

## Format (summary — full decode in the Finding)
- **`.ALL`** — **position-independent** (loads ~verbatim, **0 relocations**). `word0` = offset to a **primitive list** = records of `[RGB colour + GP0 command byte (`0x3c` gouraud-quad)]` + **s16 vertex triples** (model-space). **Validated `word0` on 78/78 files.**
- **`.ANM`** — **relocatable pointer table** → per-animation **sub-blocks**; `hdr_u16[1]` = **animation count** (FLICK 40 / ATTAFLIK 4 / PLANT01 3 / FLY 2). Sub-block = frame count (`+2`, masked `0x7fff`), channel counts (`+4/+6/+8`), default values, frame-time table (stride 6), then **bitmask-compressed keyframes** (1 bit/channel selects which carry an `s16`). Validated on 55/58 (3 compact outliers: ACORN/BBIRD/FDIM).

## Runtime (LEVEL01, `operator_backup`)
- `FLICK.ALL` resident at **`0x8012c1cc`**; `FLICK.ANM` at **`0x800ff984`**.
- **Renderer** `fcn.800172dc` (`0x8001745c`+) draws the `.ALL` primitive list — a **general mesh renderer** over the shared `0x8012c` vertex buffer (⚠️ same buffer/renderer the G30 work attributed to terrain → [[Finding - Character ALL model format]] cross-finding).
- **Animator** core `0x8005ec94`–`0x8005f0f4` + pointer-table accessor `0x8001da94`–`0x8001dfa0`.
- Loader builds `chars\NAME` + `.all`/`.anm`; the `.ALL` is **not** PROPACK-compressed (loads verbatim) — distinct from [[Asset - LEVEL.RAW]].

## Edit relevance
- Models are **rip/inspect-ready** (verbatim, position-independent) — vertex/colour edits are direct byte edits in the `.ALL` primitive section; animations are addressable per the `.ANM` count.
- Residual for a full editor: `.ALL` index/UV grammar + `.ANM` channel→bone binding.

## Actor / editor binding status

**RCG-005 closed 2026-07-02:** [[Actor model binding catalog]] is the editor-facing binding layer. It connects this corpus to Flik, seed/planter props, plant output types (`type N -> PLANTNN.ALL`), type-`0x3f` pickup/object kinds, regular enemy families, Hopper, Thumper, Thud, bird/finale, harvester variant, and cast/NPC families. Format authority is [[Asset - ALL ANM Format Grammar]]; behavior residuals are intentionally routed to the narrower gameplay gaps.

## Sources
- corpus: `REBUILD/files/CHARS*/*.{ALL,ANM}`, `PLANTS*`, `BITS/*.ALL`, `LEVELxx/*.ALL`
- vault: [[Finding - Character ALL model format]] · [[Asset - ALL ANM Format Grammar]] · [[Actor model binding catalog]] · [[Blocker - Character and plant model formats are unreversed]] · [[FUNC_800172DC]] · [[Assets]]
