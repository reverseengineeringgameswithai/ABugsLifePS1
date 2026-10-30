---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_800172DC.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_800172DC.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_800172DC_shared_.ALL-mesh_renderer_(terrain_is_one_occluded_client).md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_800172DC — shared .ALL/mesh renderer (terrain is one occluded client)
type: function
address: 0x800172DC
confidence: CONFIRMED
tags: [function, rendering, terrain, gte, g30]
---
# FUNC_800172DC — shared `.ALL`/mesh renderer (terrain + actors; occluded in terrain states)

> Draws GP0 0x3C shaded-textured quads from a **shared mesh vertex buffer** (terrain **and** actors — e.g. `FLICK.ALL`). It is a **general mesh renderer**, **not** the confirmed visible-floor renderer: in the G30 terrain states its output is fully occluded (see callout). The **visible walkable floor = LEVEL.DAT via [[FUNC_80010000]]** (f13).

> [!important] **Scope correction (2026-07-07, P54): "occluded" holds for PRISTINE geometry only.** On Track-B
> authored discs the LEVEL.DAT payload floor is MOVED to authored heights, and this renderer's chunk-35 ground mass
> becomes **visible** (it was always drawn — the pristine payload floor merely covered it exactly). Live A/B on the
> bigland disc: stubbing `FUNC_800172DC` (or zeroing buffer `0x8012C1D0..0x8012E784`) removes the visible original
> ground mass while Flik/enemies/HUD keep rendering. Custom levels suppress it via the level-gated P11-cave RAM zero
> (`build_g3_native.py --suppress-bulk-mesh`), NOT a global stub (this renderer draws character `.ALL` models in
> other scenes). See [[Tier 3 - Native Terrain Path]] P54 + `docs/G3_NATIVE_P54_VISUAL_WORLD_CLEANUP.md`.

> [!warning] Visible-floor attribution SUPERSEDED (2026-06-20; reconciled by M7 2026-06-21 · GAP-0009/0010/0011/0038)
> The 7-scene neutralize ([[Experiment - Visible floor renderer neutralize]]) found `fcn.800172dc`/chunk-35 contributes **~0 visible px (occluded)** in all tested scenes, and that the **visible walkable floor = LEVEL.DAT via [[FUNC_80010000]]** (findings-store **f13**, authoritative per [[Confirmed Knowledge]]). The earlier "X-shear visibly shears the ground" was attributed to a **function-address swap** (`0x80010000`↔`0x800172dc`). The renderer/GP0 mechanics, buffer layout, and chunk-35 mapping below remain valid; only the **"this is the visible floor" interpretation is superseded**. **Now reconciled (M7 2026-06-21):** [[Gap Audit|GAP-0011]] **Verified** (visible spawn floor = DAT/`fcn.80010000`, chunk-34/35 = occluded/collision-adjacent) + [[Gap Audit|GAP-0038]] **Verified** (visual≠collision, both arms). **Residual (local-only, GAP-0001):** the X-shear/strip vs occlusion *physics* is the one open reconciliation.

| Field | Value |
|-------|-------|
| Address | 0x800172DC |
| Source file | disasm only (G30 live trace) |
| Confidence | Renderer/buffer/GP0 mechanics CONFIRMED; the "visible terrain floor" attribution is **SUPERSEDED** (occluded — see callout; visible floor = LEVEL.DAT/[[FUNC_80010000]], f13) |

## Purpose
Builds GP0 0x3C shaded-textured quads (`lui at,0x3c00` at `0x800173cc`) from source vertices in buffer `a1`. RTPS/RTPT projection at `0x80017464 / 0x800174bc / 0x8001784c`. Reads from the persistent buffer [[MEM - Terrain vertex buffer 8012C1D0]] (`0x8012c1d0–0x8012e784`, words `0x8012c/0x8012d`).

## Arguments / Returns
`a1` = source vertex buffer base (`0x8012c1d0`). Per-quad stride `0x30`: verts xy at `+0x4/0xc/0x14/0x1c` (low16 X, high16 Y), z at `+0x8/0x10/0x18/0x20`, gray colors at `+0x00/0x24/0x28/0x2c`.

> [!important] **Cross-finding (2026-06-18, B7) — this is a *general* mesh renderer, not terrain-exclusive.** In `operator_backup` the `0x8012c…` buffer holds **`FLICK.ALL` (Flik's model)** — header byte-exact at `0x8012c1cc`, and this same `fcn.800172dc` (`0x8001745c`+) reads its primitive section to draw Flik. So the `0x30`-stride colour+s16-vert quad grammar above is the **shared `.ALL`/terrain primitive format**, and `0x8012c…` is the **active mesh vertex buffer** (terrain in the G30 states, the character model here) — not a terrain-only buffer. The operator-verified terrain result (X-shear/Y-deform) **stands for terrain states**; what this refines is the *naming/scope* (general mesh renderer + shared buffer). See [[Finding - Character ALL model format]] · [[Asset - Character and plant models]].

## Calls (callees)
- libgte transform leaf bank [[FUNC_80060724]] (`0x80060650–0x80060814`).

## Called by (callers)
- [[FUNC_8001DFE4]] — scene-geometry draw dispatcher (one of 5 emitters: `0x80014b04 / 0x80014ee0 / 0x800153d0 / 0x800163e0 / 0x800172dc`).

## Globals & structures touched
- [[MEM - Terrain vertex buffer 8012C1D0]] (shared mesh source; terrain in the G30 states, a character model in others) · OT base `[0x8008240c]`.

## Evidence & confidence notes
G30 R1 mapped the render call tree and narrowed the terrain hunt to 6 emitters; R5 read `fcn.800172dc` as "the terrain surface" (X-shift sheared the ground, Y-shift deformed) — that **visible-floor reading is SUPERSEDED** by the 2026-06-18 7-scene neutralize (the layer is occluded; the visible floor is LEVEL.DAT/[[FUNC_80010000]], f13) and was attributed to a function-address swap. The renderer/GP0/buffer mechanics stand. The earlier "staged ground" idea (§13) was a bottom-clip artifact and was corrected. Localized edits to this buffer work but are occluded (and a photogenic pit is rendering-limited) — see [[Finding - Localized terrain edit]]. Findings store ids f4, ~~f5~~ (f5 retracted), f9.

## Related
- Findings: [[Finding - Visible terrain renderer]] · [[Finding - Terrain on-disk source is chunk 35]] · [[Finding - Localized terrain edit]] · [[Finding - Visual is not collision]]
- Functions: [[FUNC_8001DFE4]] · [[FUNC_80060724]] · [[FUNC_8001A1DC]] (produces the buffer)
- Experiments: [[Experiment - G30 localized terrain edit]] · Memory: [[MEM - Terrain vertex buffer 8012C1D0]] · Fixture: [[Fixture - g30 openground]]
- Source docs: `src_re_geometry/geometry_g30_terrain_render_source_plan.md`
