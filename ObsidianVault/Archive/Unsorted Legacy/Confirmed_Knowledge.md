---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Confirmed Knowledge/Confirmed Knowledge.md
aliases:
  - "Confirmed Knowledge"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Confirmed Knowledge/Confirmed Knowledge.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Confirmed Knowledge
type: dashboard
updated: 2026-06-17
tags: [dashboard, confirmed]
---

# Confirmed Knowledge

> The settled facts — each is CONFIRMED (built+observed, or multi-evidence per the [[API - determinism|determinism rubric]]). Every row links to its finding. History/dead-ends live in [[Hypotheses]] and `docs/EXPERIMENT_LOG.md`.

## Geometry: visual vs. collision (the headline)
- **Visible terrain ≠ collision.** Different files, RAM, and code. → [[Finding - Visual is not collision]]
- **Chunk-35 terrain layer** ([[FUNC_800172DC]] from buffer [[MEM - Terrain vertex buffer 8012C1D0]]) is **fully occluded** in all tested scenes (0 visible px, 2026-06-18) — *not* the surface you see. The **visible walkable floor = LEVEL.DAT / [[FUNC_80010000]]** (next line). → [[Finding - Visible terrain renderer]] · [[Experiment - Visible floor renderer neutralize]] · [[Finding - Terrain on-disk source is chunk 35]]
- **Bulk foreground floor** under Flik is drawn by [[FUNC_80010000]] from LEVEL.DAT objects via [[FUNC_80019934]]; **Candidate A** (DAT `0x188cc`) is an editable visual terrain payload. → [[Finding - Visible ground from DAT verts]] · [[Finding - Candidate A is DAT-backed visual terrain]]
- **Collision floor** = sector table [[MEM - Collision sector table 800A7E48]] + [[MEM - Collision plane record|plane records]] (LEVEL.RAW **chunk 32**), resolved by [[FUNC_8003633C]] (writer) via [[FUNC_800345CC]]. The floor is a set of **planes**, not a scalar height. → [[Finding - Collision sector table]] · [[Finding - Collision is planes not scalar]] · [[Finding - Player Y writer FUNC_3633C]] · [[Finding - Collision on-disk source is chunk 32]]
- **Collision edits move Flik's footing ~1:1** (RAM/save-state). → [[Finding - Collision RAM edit moves footing 1to1]] · [[Finding - Collision lever sector186]]

## Geometry: render pipeline & format
- Render path: [[FUNC_800224EC]] driver → [[FUNC_800140A0]] cull → [[FUNC_8001EA6C]]/[[FUNC_800206E8]] builders → [[FUNC_80010000]] emitter. → [[Geometry pipeline]]
- Mesh payload format `{u32 count; Vertex[stride 0xc]; cmd stream}`. → [[Finding - fcn.80010000 payload format]]
- Payload-vertex edits visibly deform geometry. → [[Finding - Payload vertex edits are visible]]
- Trail flag `DAT+0x1526` gates terrain render (render/collision separation, first evidence). → [[Finding - Trail flag gates terrain render]]

## Assets & loading
- **LEVEL.RAW is compressed** (LZSS/LZ77, [[FUNC_8001A1DC]]); it's the geometry+collision resource, loaded by [[FUNC_8003A318]]. → [[Finding - LEVEL.RAW is compressed]] · [[Finding - Floor resource is LEVEL.RAW]]
- DAT parser [[FUNC_8001CDC0]] runs once per load and relocates 1248 baked offsets.
- **Toolchain/provenance** *(2026-06-18)*: built by **Traveller's Tales** (PsyQ + SN PsyMake 1.11); `LEVEL.RAW`/`GFX/*.RAW` use **RNC PROPACK 2.29** (decoder byte-exact); LEVEL.RAW = 69 PROPACK frames in 3 regions. Disc = hash-verified **USA V1.0**. → [[Finding - Build toolchain and PROPACK provenance]] · [[MEM - LEVEL.RAW chunk inventory]]

## Sky
- Sky = GP0 0x02 **background fill** (not an image), built by [[FUNC_800639CC]] from cache [[MEM - Sky DRAWENV color cache 800771BC]]; on-disk in chunk 32. → [[Finding - Sky is a GP0 background fill]] · [[Finding - Sky color on-disk table]]
- Arbitrary GPU primitives can be injected into a frame. → [[Finding - GPU primitive injection]]

## Pickups / LEVEL.DAT (shipped in-game)
- Type-0x3f pickups are **coordinate-moddable** (runtime = file `<<5`). → [[Finding - Type-0x3f pickups are coordinate-moddable]]
- **New entries can be injected** with the relocation-aware tool. → [[Finding - Relocation-aware DAT append]]
- Pipeline: [[FUNC_8001CDC0]] → [[FUNC_80053814]] → [[FUNC_80059E44]] → [[FUNC_800586B0]] → [[FUNC_800526F4]]. → [[LEVEL.DAT object pipeline]]

## Method / tooling
- The static collision search was a true negative — collision reaches data via a non-global pointer chain. → [[Finding - No static collision consumer]]
- CONFIRMED requires reproducibility + causality. → [[API - determinism]]
- Live RAM can be read via `/proc/<pid>/mem`. → [[Finding - Live RAM probe via proc mem]]

## See also
[[Open Questions]] · [[Hypotheses]] · [[Blockers]] · [[Findings Index]] · [[Home]]
