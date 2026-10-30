---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Fixtures/Fixture - g30 openground.md
aliases:
  - "Fixture - g30 openground"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Fixtures/Fixture - g30 openground.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Fixture - g30 openground
type: fixture
fixture_id: x1
confidence: CONFIRMED
tags: [fixture, g30, terrain, collision, r6]
---

# Fixture — g30 openground

> The primary working state for all of **[[G30 - Terrain render source]]** and the collision work of **[[G29 - Collision source]]**.

| Field | Value |
|-------|-------|
| **Path** | `~/.local/share/duckstation/savestates/SCUS-94288_g30_openground.sav` |
| **Fixture id** | `x1` (in findings store) |
| **Game serial** | SCUS-94288 |
| **Frame** | 0 (start) |

## Game state
Flik standing on an **open, flat, fence-free walkable dirt** area in LEVEL01. This is the "R6 spot" used for localized terrain-edit tests. The player sector here is **sec186** (origin `(20608, 0, -40416)`), record at `0x800aa128` — see [[MEM - Collision sector table 800A7E48]].

## Why this fixture exists / expected outcome
- A clean, obstruction-free patch of ground where both the **visual** floor ([[MEM - Terrain vertex buffer 8012C1D0]], rendered by [[FUNC_800172DC]]) and the **collision** floor ([[MEM - Collision sector table 800A7E48]]) can be edited and observed.
- Camera-lock + uniform texture make a *uniform* lower invisible; use **MOVE / RECOLOR / localized** edits, not neutralize. See [[Finding - Visual is not collision]].

## Recommended APIs
[[API - loadState]] → settle 1 frame → [[API - addWatch]] / [[API - accessLog]] · [[API - execTrace]] at [[FUNC_800172DC]] · [[API - readArray]] (reads all 223 sector records in one call) · [[API - gpu.readVramRect]] · [[API - memoryScan]].

## Related
- Findings: [[Finding - Visible terrain renderer]] · [[Finding - Terrain on-disk source is chunk 35]] · [[Finding - Collision sector table]] · [[Finding - Collision lever sector186]] · [[Finding - Visual is not collision]]
- Experiments: [[Experiment - G30 localized terrain edit]] · [[Experiment - G29 collision lever validation]]
- Save catalog: [[Save States Index]]
