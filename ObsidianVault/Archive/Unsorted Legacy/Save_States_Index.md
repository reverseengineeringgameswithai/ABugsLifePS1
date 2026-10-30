---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Save States/Save States Index.md
aliases:
  - "Save States Index"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Save States/Save States Index.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Save States Index
type: index
updated: 2026-06-17
tags: [index, savestate, fixture]
---

# Save States Index

All DuckStation save states live in `~/.local/share/duckstation/savestates/`. Game serial **SCUS-94288**. Load with the [[API - loadState]] command (and **settle a frame before `addWatch`** — see [[API - addWatch]]).

A *fixture* is a save state with a documented, reproducible purpose — see **[[Fixtures Index]]**. Numbered slots (`_1` … `_7`) are working/manual saves with no formally documented purpose; treat them as scratch unless a note says otherwise.

| Save state                              |     Size | Last modified    | Purpose                                                                                                                                                            | Fixture note                         |
| --------------------------------------- | -------: | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------ |
| `SCUS-94288_g30_openground.sav`         |  1.89 MB | 2026-06-16 13:06 | Flik on open flat fence-free walkable **dirt**; G30 working state + R6 edit spot                                                                                   | [[Fixture - g30 openground]]         |
| `SCUS-94288_g30_openfloor.sav`          |  1.98 MB | 2026-06-17 01:59 | Flik on big open unobstructed **pebbled floor** (Z≈217790); good visible-ground-edit view. ⚠️ walking forward spawns an enemy+fence                                | [[Fixture - g30 openfloor]]          |
| `SCUS-94288_night_starry.sav`           |  1.93 MB | 2026-06-17 04:41 | Result: daytime sky recolored to **starry night** (frozen-frame overlay)                                                                                           | [[Fixture - night starry]]           |
| `SCUS-94288_night_live.sav`             |  1.93 MB | 2026-06-17 13:43 | **Persistent playable night** — per-frame hook draws a big moon + stars into the back buffer, haze removed; flicker-free, survives gameplay                        | [[Fixture - night live]]             |
| `SCUS-94288_starry_night_workbench.sav` |  1.92 MB | 2026-06-17 03:40 | Working bench for the starry-night GPU-injection experiment                                                                                                        | [[Fixture - starry night workbench]] |
| `SCUS-94288_fence_wall.sav`             |  2.04 MB | 2026-06-18       | Flik pressed against the **openfloor fence** — fires the **wall/ledge collision** `fcn.80025084` when ↑ held; B18 wall-math fixture (5 enemy models also resident) | [[FUNC_80025084]]                    |
| `SCUS-94288_resume.sav`                 |  1.95 MB | 2026-06-16 19:38 | General resume point                                                                                                                                               | —                                    |
| `SCUS-94288_1.sav` (+`_copy`)           | ~1.95 MB | 2026-06-17 02:34 | Scratch slot                                                                                                                                                       | —                                    |
| `SCUS-94288_2.sav` (+`_copy`)           |  0.92 MB | 2026-06-15 22:30 | Scratch slot — referenced as source for chunk-32/35 disk-provenance traces (f2/f10/f11)                                                                            | —                                    |
| `SCUS-94288_3.sav` (+`_copy`)           |  1.99 MB | 2026-06-16 00:01 | Scratch slot                                                                                                                                                       | —                                    |
| `SCUS-94288_5.sav`                      |  1.98 MB | 2026-06-16 00:19 | Scratch slot                                                                                                                                                       | —                                    |
| `SCUS-94288_6.sav`                      |  1.89 MB | 2026-06-16 00:34 | Scratch slot                                                                                                                                                       | —                                    |
| `SCUS-94288_7.sav`                      |  1.92 MB | 2026-06-17 02:39 | Scratch slot                                                                                                                                                       | —                                    |

> [!note] `_copy` files are manual backups of the matching slot. The `_2` slot is the smallest (0.92 MB) — likely captured at a different load phase.

## Related
- [[Fixtures Index]] · [[Home]] · [[API - loadState]] · [[API - saveState]]
- Source-of-truth: the `fixtures:` block in `src_re_geometry/re_findings_backup.yaml`.
