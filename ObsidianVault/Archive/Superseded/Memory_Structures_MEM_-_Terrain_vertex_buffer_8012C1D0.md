---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - Terrain vertex buffer 8012C1D0.md
aliases:
  - "MEM - Terrain vertex buffer 8012C1D0"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - Terrain vertex buffer 8012C1D0.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_Terrain_vertex_buffer_8012C1D0.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: MEM - Shared mesh vertex buffer 8012C1D0 (terrain + actors)
type: memory-structure
address: 0x8012C1D0
address_end: 0x8012E784
confidence: CONFIRMED
tags: [memory, terrain, rendering, levelraw, g30]
---

# MEM — Shared mesh vertex buffer `0x8012C1D0` (terrain + actors; occluded in terrain states)

> The persistent vertex buffer for [[FUNC_800172DC]]'s **shared mesh renderer** (terrain **and** actors — e.g. `FLICK.ALL`). Decompressed from LEVEL.RAW chunk 35. *(The filename keeps the legacy "Terrain vertex buffer" token for wikilink stability; this is a general mesh buffer, and in terrain states its render is **occluded** — the visible floor is LEVEL.DAT via [[FUNC_80010000]], f13.)*

> [!warning] "Visible floor" SUPERSEDED (2026-06-20; reconciled by M7 2026-06-21 · GAP-0009/0010/0011/0038)
> Earlier framed as "the editable visual-floor source buffer," but the 7-scene neutralize ([[Experiment - Visible floor renderer neutralize]]) found `fcn.800172dc`/chunk-35 = **~0 visible px (occluded)**; the **visible walkable floor = LEVEL.DAT via [[FUNC_80010000]]** (findings-store **f13**). Buffer layout + chunk-35 mapping + model↔world scale below remain valid; only the **visible-floor role is superseded**. **Now reconciled (M7):** [[Gap Audit|GAP-0011]] Verified + [[Gap Audit|GAP-0038]] Verified. **Residual (local-only, GAP-0001):** the X-shear/strip vs occlusion *physics* is unreconciled.

> [!check] **B7 confirmed + visible-terrain transform solved (live, 2026-06-22 · [[Gap Audit|GAP-0023]])**
> Live capture settled it: at render time this buffer holds **Flik's `FLICK.ALL`**, not terrain — [[FUNC_800172DC]] (RTPT `0x80017464`) logged **1032 hits = only Flik** (XZ extent ~164) in LEVEL01 **and** LEVEL02; chunk-34/35 is never drawn. ⇒ the model↔world **scale recorded below (G33: Y 1.0 / X 1.569 / Z 1.046) was Flik's model→view, not terrain.** The **visible terrain's** model→world is instead solved on [[FUNC_80010000]] (RTPT `0x800106f8`): **`world = (R⁻¹·(TR + RT·v/4096) + Cdiv)×32`** via scratchpad camera struct `0x1f800374` (C@+0x00, Cdiv@+0x10, RT@+0x20, TR@+0x54) — forward-projection EXACT (computed SXY == live `SXY0`) + a floor tile under Flik reconstructs to footing (dY 672). The editor's `1450`/Y-flip is refuted.

| Field | Value |
|-------|-------|
| **Range** | `0x8012C1D0` … `0x8012E784` |
| **Producer** | [[FUNC_8001A1DC]] (LZSS decompressor) — write PCs `0x8001a5e8 / 0x8001a5f0 / 0x8001a678` |
| **Consumer** | [[FUNC_800172DC]] (shared `.ALL`/mesh renderer; terrain output occluded) reads source verts from buffer `a1` |
| **On-disk source** | LEVEL01/LEVEL.RAW **chunk 35** (file off `0x9908a`, comp `0x1b24` → dec `0x34f4`) — see [[Finding - Terrain on-disk source is chunk 35]] |

## Layout (CONFIRMED — GP0 0x3C shaded-textured quads, stride 0x30)
Each quad packet = 4 vertices, stride `0x30`:
| Offset | Meaning |
|--------|---------|
| +0x04 / +0x0c / +0x14 / +0x1c | vertex XY — **low16 = X, high16 = Y** |
| +0x08 / +0x10 / +0x18 / +0x20 | vertex Z |
| +0x00 / +0x24 / +0x28 / +0x2c | gray colors |

## Model↔world scale (G33, CONFIRMED)
Captured the renderer's model→view matrix via `execTrace` at rtpt `0x80017464`. Camera rotation is
orthonormal → column norms = model→world scale (camera-invariant): **height axis = model-Y, world-scale
= 1.000** (X 1.569, Z 1.046). So a terrain model-Y change of δ = δ world units. **Matched-bump calibration
vs collision:** terrain model-Y `Δ = ΔW`, collision src origin-Y `Δ = ΔW≫5` (= 32× smaller). See
[[Plan - Terrain+collision matched bump (Option B)]].

## Spatial localization (G33b)
`execTrace` at rtpt `0x80017464` with `capture:["a1","gte.SXY0..2"]`: **`a1` walks the buffer**, so
`a1 − 0x8012C1D0` = the quad's **buffer/chunk-35 local offset**; SXY = its screen position (1 RTPT lag;
RTPT does 3 verts/call). Floor renders as a narrow center strip (screenX ~221–275). **Floor in front of
Flik = highest-screenY quads** (spawn: offsets `0x01c4,0x031c,0x028c,0x02ec,0x034c,…`). Sign: subtract
model-Y to raise (see [[Plan - Terrain+collision matched bump (Option B)]]).

## Edit levers (buffer mechanics CONFIRMED; visible-terrain effect SUPERSEDED — occluded)
> The buffer is editable and these levers move its mesh, but in terrain states the output is **occluded (~0 visible px)** — so a terrain edit here is **not** visible (the earlier "visible" shear was a function-address swap, [[FUNC_80010000]]↔`fcn.800172dc`). For a *visible* floor edit use the f13 DAT vert-Y lever ([[Finding - Candidate A is DAT-backed visual terrain]]).
- **Y-shift** a vertex → mesh deforms (occluded in terrain states).
- **X-shift** → shears the mesh (occluded in terrain states).
- Localized edit: EXEC at [[FUNC_800172DC]] rtpt `0x80017464`, capture per-quad SXY + `a1`, edit quads inside a screen box (diff-confirmed). See [[Finding - Localized terrain edit]].

> [!warning] Collision is a *separate* layer — see [[MEM - Collision sector table 800A7E48]] and [[Finding - Visual is not collision]]. (Per the callout at top: this buffer is the **occluded** general-mesh buffer, **not** the visible floor — that is LEVEL.DAT / [[FUNC_80010000]].) A uniform lower is invisible (camera follows Y + uniform texture); near-ground quads clip off the bottom at 512×224.

## Related
- Findings: [[Finding - Visible terrain renderer]] · [[Finding - Terrain on-disk source is chunk 35]] · [[Finding - Visual is not collision]] · [[Finding - Localized terrain edit]]
- Functions: [[FUNC_800172DC]] · [[FUNC_8001A1DC]] · [[FUNC_8003A318]]
- Fixture: [[Fixture - g30 openground]] · APIs: [[API - accessLog]] · [[API - execTrace]] · [[API - gpu.readVramRect]]
- Asset model: [[MEM - LEVEL.RAW chunk model]] · Findings store ids: f5, f10
