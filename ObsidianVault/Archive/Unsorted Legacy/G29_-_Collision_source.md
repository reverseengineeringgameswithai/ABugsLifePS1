---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Geometry/G29 - Collision source.md
aliases:
  - "G29 - Collision source"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Geometry/G29 - Collision source.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: G29 - Collision source
type: milestone
gstep: G29
status: CONFIRMED (full disk→player-Y chain)
tags: [milestone, geometry, collision, g29]
---

# G29 — Collision / pathing source discovery

> After G28 proved the *visible* floor is editable but collision didn't follow, G29 traced the **actual** collision floor end-to-end, from disc to the player-Y write. See the arc map at [[Geometry pipeline]].

## Goal
Find the collision/floor source that is separate from the visual mesh, and the code that writes Flik's footing. Fixtures: gameplay `SCUS-94288_1.sav`, pre-load `SCUS-94288_2.sav`, working [[Fixture - g30 openground]].

## The chain (CONFIRMED)
LEVEL.RAW (compressed) → loaded by [[FUNC_8003A318]] → decompressed by [[FUNC_8001A1DC]] (**chunk 32**) → built (scaled `<<5`) into the [[MEM - Collision sector table 800A7E48|sector table]] by [[FUNC_80030F60]] → sector AABB select → per-frame candidate list `0x8009c230` → resolver [[FUNC_800345CC]] (swept plane-distance clamp + skin `−0xc0`) → commit by [[FUNC_8003633C]] at `0x80036cec` → player Y `0x800a6504`.

## Key results
- Player-Y writer = [[FUNC_8003633C]], **not** `fcn.8005b134` → [[Finding - Player Y writer FUNC_3633C]].
- The floor is a set of **planes**, not a scalar → [[Finding - Collision is planes not scalar]] · [[MEM - Collision plane record]].
- Collision source = LEVEL.RAW chunk 32 → [[Finding - Collision on-disk source is chunk 32]] · [[Finding - Collision sector table]].
- Sector-origin Y edit moves footing ~1:1 → [[Finding - Collision RAM edit moves footing 1to1]] · [[Finding - Collision lever sector186]].
- Vindicates the G5 static negative → [[Finding - No static collision consumer]].
- Definitively explains G28: visual (LEVEL.DAT / chunk 35) ≠ collision (chunk 32) → [[Finding - Visual is not collision]].

## Method (live debugger)
JSON-RPC debugger: WRITE-watch player Y ([[API - addWatch]]/[[API - accessLog]]) + [[API - controller input]] + [[API - frame capture]] + [[API - scatterWrite]] + [[API - readArray]].

## Experiments
[[Experiment - G29 collision lever validation]]

## Gates / next
Single-plane lever + record→Y math residuals ([[Open Questions]] P2); permanent disc patch needs the LZ codec.

## Source
`src_re_geometry/geometry_g29_collision_source_plan.md` · predecessor: [[Experiment - G28 Candidate A floor Y]] · successor: [[G30 - Terrain render source]]
