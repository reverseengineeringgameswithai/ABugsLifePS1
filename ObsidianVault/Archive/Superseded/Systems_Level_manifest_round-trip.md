---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Level manifest round-trip.md
aliases:
  - "Level manifest round-trip"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Level manifest round-trip.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Level_manifest_round-trip.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Level manifest round-trip
type: system
updated: 2026-07-03
confidence: PROVEN (byte-identical DAT; cold-boot 8/8 spot checks)
tags: [system, tier3, blender, manifest, pipeline, props, actors, dot, pickups]
---

# Level manifest round-trip — LEVEL01 re-created from JSON

> The Tier-3/Blender pipeline's backbone, built + proven 2026-07-03:
> **`tools/extract_level_manifest.py`** (level → JSON) and **`mod/build_tier3_level.py`**
> (JSON → disc). An unedited manifest reproduces LEVEL01 exactly; any manifest edit =
> a modified level. This is "re-create LEVEL01 with its props" — done.

## What the manifest carries (LEVEL01 numbers)
| Lane | Count | Source | World-unit conversion |
|---|---|---|---|
| `props_pass1` | **484** records | DAT pass-1 table (base `0x1504`) | stored×32; extent/flags/**payload** preserved |
| `props_pass3` | **140** records | DAT `0x3AEC` (cull-anchored decor) | same shape |
| `dot_route` | **104** waypoints | DAT `@+0x468` | stored×32; builder tail-pads short routes (Dot parks at the goal) |
| `pickups` | **70** type-0x3f entries | DAT `@+0x8` | stored×32 + kind byte |
| `actors` | **32** records (enemies + seeds) | LEVEL.RAW chunk 31 | stored×32 + type_word + params |

## Round-trip proof
1. extract → build (unedited): **LEVEL.DAT byte-identical**; **chunk-31 decompressed identical**
   (compressed bytes differ ~1.002×, expected — our encoder).
2. Disc `REBUILD/ABL_L01_ROUNDTRIP.cue` **cold-boots**: **8/8 RAM spot checks** (pass-1 records
   #0/#100/#214/#300/#483 · Dot wp 50 · pickup count · actor slot 0), 4 live damageable actors,
   `ENEMIES-REMAINING = 21` (pristine), Flik at the native spawn.

## Design choices (why it's robust)
- The builder **patches pristine files field-by-field** — never re-serializes whole tables — so
  identity is trivial and every write lands on an already-proven edit class (pass-1 XYZ/payload ·
  pass-3 · Dot waypoints · pickup XYZ/kind · chunk-31 records incl. ADD into free slots).
- Coordinates are world units in JSON; the builder enforces the ×32 grid (hard error otherwise).
- Guardrails: pickup count must match (add/delete stays with `apply_level_placements`); pass-table
  record counts must match the level; actor slots bounds-checked.

## How to edit LEVEL01 now
`extract → edit build/level01_manifest.json → build`. Everything proven this week applies per record:
move/re-skin props (payload from `build/pass1_palette/`), move/add/re-type enemies, reroute Dot,
move pickups. Blender glue (import the manifest as `T3_*` collections + export back) is the next
increment ([[Tier 3 - Blender Pipeline Plan]] §3.4).

## Residuals
- Blender import/export operators for the manifest (JSON ↔ collections).
- Count-changing edits (pickup add/delete → integrate `apply_level_placements`; pass-1 table grow).
- TIER3.RND custom-geometry lanes are orthogonal (already built) — a combined custom-world +
  manifest disc is the Playground v1 target.

## Related
[[Tier 3 - Blender Pipeline Plan]] · [[Prop and foliage catalog]] · [[Dot guide NPC]] · [[Enemy spawn architecture]] · `tools/extract_level_manifest.py` · `mod/build_tier3_level.py` · `mod/tier3_level_schema.json`
