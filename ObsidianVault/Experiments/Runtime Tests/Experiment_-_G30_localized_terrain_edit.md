---
kind: experiment
id: Experiment_-_G30_localized_terrain_edit
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G30 localized terrain edit.md
aliases:
  - "Experiment - G30 localized terrain edit"
---

# Experiment — G30 localized terrain edit

> Migrated from `ObsidianVault/Experiments/Experiment - G30 localized terrain edit.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G30 localized terrain edit

> Live-edit the shared-mesh renderer's chunk-35 buffer (and match it to the collision lever) — no disc build.

> [!warning] "VISIBLE terrain deform" SUPERSEDED (2026-06-18; reconciled M7 2026-06-21 · GAP-0009/0010/0011)
> A later patch-verified **7-scene neutralize** ([[Experiment - Visible floor renderer neutralize]]) found `fcn.800172dc`/chunk-35 contributes **~0 visible px (occluded)** — so the "terrain Y-rise / X-shear VISIBLE" result below is **superseded** (attributed to a function-address swap `0x80010000`↔`0x800172dc`). The **visible** walkable floor is LEVEL.DAT via [[FUNC_80010000]] (f13; spawn area Verified in M7, [[Gap Audit|GAP-0011]]). The edit-method, the matched visual+collision lower, and the **bulk-foreground DAT floor** edit (38090 px, via `0x80019xxx`) remain valid — only the chunk-35-buffer "visible" attribution is retracted.

| Field | Value |
|-------|-------|
| Fixture / save state | [[Fixture - g30 openground]] (`SCUS-94288_g30_openground.sav`), [[Fixture - g30 openfloor]], `SCUS-94288_6.sav` (lowerfloor) |
| Build image / tool | none — **live debugger only** (RAM/scatterWrite edits); `tools/abl_dbg.py`, `tools/parse_level_raw_chunks.py`, `tools/vramdiff.py` |
| Patch | terrain buffer `0x8012c1d0–0x8012e784` vertex Y / X shift; bulk-floor DAT object vert+0xa Y (via `0x80019xxx`); collision sector `0x800a7e48` (sec186) match |
| APIs used | [[API - execTrace]] (at [[FUNC_800172DC]] rtpt `0x80017464`), [[API - accessLog]], [[API - scatterWrite]], [[API - readArray]], [[API - gpu.readVramRect]], [[API - visual diff]], [[API - findings store]] |

## Goal
Find the world-space dirt renderer + its editable source, deform it locally, and match a collision edit so Flik lands coincident.

## Procedure (reproducible)
1. Load [[Fixture - g30 openground]]; settle a frame.
2. EXEC [[FUNC_800172DC]] (GP0 0x3C quad emitter, `lui at,0x3c00` at `0x800173cc`; rtps/rtpt `0x80017464/74bc/784c`); capture per-quad SXY + the source buffer `a1` ([[MEM - Terrain vertex buffer 8012C1D0]]).
3. `scatterWrite` a Y-shift to quads inside a screen box; `gpu.readVramRect` before/after + `diffFrames` to confirm motion (Y-shift deforms, X-shift shears).
4. For the bulk foreground floor, edit the DAT-object Y at `vert+0xa` via the `0x80019xxx` sub-emitter ([[FUNC_80019934]]).
5. Match: lower both the visual buffer and collision sector186 ([[MEM - Collision sector table 800A7E48]], read all 223 via `readArray`).

## Result
Terrain-buffer Y-rise / X-shear was read as **VISIBLE — now SUPERSEDED** (the later neutralize shows chunk-35 is occluded; the effect was a `0x80010000`↔`0x800172dc` address swap). The **bulk foreground DAT floor** edit changed **38090 px** (diff-confirmed, via [[FUNC_80010000]]/`0x80019xxx`) — that lever stands; a *matched* visual+collision lower lands Flik coincident on the lowered floor (consistency proven via the DAT floor). The "staged ground" of an interim read was a bottom-clip artifact (corrected).

> [!note] A dramatic *localized* pit is **rendering-limited**, not tooling-limited: near ground clips off the screen bottom (512×224), the camera follows Flik's Y, and gouraud/uniform texture hides a uniform lower. A photogenic pit needs the GTE-trace/frame-diff calibration (the buffer is strip-ordered, not spatial).

## Conclusion
[[FUNC_800172DC]] renders a chunk-35 mesh layer (buffer [[MEM - Terrain vertex buffer 8012C1D0]], on-disk LEVEL.RAW chunk 35) that is **occluded** (SUPERSEDED as "the visible surface"); the **visible** walkable floor is DAT-backed via [[FUNC_80010000]]/`0x80019xxx` (f13). Both buffers are editable; visual (DAT) and collision are matchable but separate.

## Linked findings / functions / structures
- [[Finding - Visible terrain renderer]] · [[Finding - Visible ground from DAT verts]] · [[Finding - Localized terrain edit]] · [[Finding - Terrain on-disk source is chunk 35]] · [[Finding - Visual is not collision]]
- [[FUNC_800172DC]] · [[FUNC_80010000]] · [[FUNC_80019934]] · [[FUNC_8001DFE4]] · [[MEM - Terrain vertex buffer 8012C1D0]] · [[MEM - Collision sector table 800A7E48]]
## Source
`src_re_geometry/geometry_g30_terrain_render_source_plan.md`
