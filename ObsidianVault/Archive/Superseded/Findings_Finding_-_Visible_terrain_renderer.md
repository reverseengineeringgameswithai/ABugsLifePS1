---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Visible terrain renderer.md
aliases:
  - "Finding - Visible terrain renderer"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Visible terrain renderer.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Visible_terrain_renderer.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Visible terrain renderer
type: finding
confidence: CONFIRMED
gstep: G30
tags: [finding, rendering, terrain, levelraw]
---

# Finding — `fcn.800172dc` is a shared mesh renderer (occluded terrain layer, NOT the visible floor)

> ⚠️ **Title is legacy.** [[FUNC_800172DC]] builds GP0 `0x3C` quads from a persistent buffer (LEVEL.RAW **chunk 35**), but the 2026-06-18 live test proves **this layer is fully occluded (0 visible px in 7 scenes)** — it is **NOT** the surface you see. The **visible walkable floor is LEVEL.DAT via [[FUNC_80010000]]** → [[Finding - Visible ground from DAT verts]]. This note documents `fcn.800172dc` + its buffer; see the CORRECTED callout below.

> [!check] **CORRECTED 2026-06-18 (authoritative, live API) → f13.** A patch-verified, frame-matched, **7-scene** neutralize test shows **`fcn.800172dc` contributes 0 visible pixels** (it *fires* — internal rtpt 172→0 hits when patched — but is fully occluded). Neutralizing **`fcn.80010000` (LEVEL.DAT)** is what flattens the pebble floor to a plain plane (44.5%, lower-screen) — *that* is the visible walkable floor. The prior "172dc flattens the ground" reading was a **function-address swap** (`0x80010000` ↔ `0x800172dc`). **Visible walkable floor = LEVEL.DAT / `fcn.80010000` (f13)**; `fcn.800172dc` / chunk-35 = a separate, occluded terrain layer. Evidence: [[Experiment - Visible floor renderer neutralize]]. *(Supersedes the prior f5/f10 note; `f5` → DISPROVEN, `f13` → CONFIRMED.)*

**Confidence:** `fcn.800172dc` draws chunk-35 GP0 0x3C quads = CONFIRMED; *that those quads are the visible floor* = **DISPROVEN (2026-06-18)** — see callout · **Findings-store id:** f4, ~~f5~~ (f5 retracted)

## Summary
- [[FUNC_800172DC]] builds GP0 `0x3C` shaded-textured quads (`lui at,0x3c00` at `0x800173cc`); projection rtps/rtpt at `0x80017464 / 0x800174bc / 0x8001784c`.
- It reads source verts from the persistent buffer [[MEM - Terrain vertex buffer 8012C1D0]] (`0x8012c1d0`–`0x8012e784`, the `0x8012c/0x8012d` pages).
- **Edit levers (⚠️ contradicted 2026-06-18):** earlier sessions reported Y-shift→rise/sink and X-shift→shear of this buffer as *visible*, but the buffer's output is **fully occluded** (0 visible px, 7 scenes) → those visible effects could not be reproduced and were likely misattributed. See [[Experiment - Visible floor renderer neutralize]].

## What `fcn.800172dc` actually renders (2026-06-18 live deep-dive)
- **It IS a real, active renderer** — not dead code: it reads chunk-35 vertices from `0x8012c1d0` (`a1` steps 0x30/quad), RTPT-projects **~43 GP0 `0x3C` textured-quad verts/frame** to a **near-floor screen patch around Flik** (SXY **X 227–409, Y 103–221**), they **pass** its depth-band cull (SZ1 810–1029, window `[0, s0+750)` = `[0, 5358)`), it builds packets at `~0x801e28xx`, and **links them into the active display OT** (53 OT links confirmed; the display double-buffers `0x801cc390` / `0x801e134c`).
- **Yet it contributes 0 visible pixels** (7 scenes; still 0% even after neutralizing 8 other floor builders): its quads sit at the **bottom of a multi-layer floor stack** and are **completely overdrawn** by the upper floor layers (a flat-plane layer + the LEVEL.DAT pebble floor on the same footprint).
- **Net on-screen: nothing.** `fcn.800172dc` is a real but **fully-occluded under-layer** of the floor — it does all the work (read → project → cull → build → link) but every quad is painted over. It would only show if nothing drew over its lower-center footprint, which never happens in normal play. *(Candidate gate worth testing: the `DAT+0x1526` "trail flag gates terrain render" finding.)* → [[Experiment - Visible floor renderer neutralize]].

## Evidence
- G30 R1 mapped the render call tree from driver [[FUNC_800224EC]] → scene dispatcher [[FUNC_8001DFE4]] (5 emitters: `0x80014b04/0x80014ee0/0x800153d0/0x800163e0/0x800172dc`), narrowing terrain to `fcn.800172dc`.
- ~~Live X-shift of the buffer visibly sheared the ground texture~~ — **NOT REPRODUCED (2026-06-18):** neutralizing the whole `fcn.800172dc` renderer changes 0 visible px across 7 scenes, so this buffer does **not** feed the visible surface (it is occluded).
- The earlier "staged ground" idea (a per-frame staging buffer) was a bottom-clip artifact and was corrected — the source is the **persistent** `0x8012c/d` buffer.

## Related functions
[[FUNC_800172DC]] · [[FUNC_800224EC]] · [[FUNC_8001DFE4]] · [[FUNC_8001A1DC]] (decompresses the buffer) · [[FUNC_8003A318]]

## Related memory structures
[[MEM - Terrain vertex buffer 8012C1D0]] · [[MEM - LEVEL.RAW chunk model]]

## Related experiments
[[Experiment - G30 localized terrain edit]]

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - execTrace]] · [[API - accessLog]] · [[API - scatterWrite]] · [[API - gpu.readVramRect]] · [[API - gp0Trace]]

## Next steps
The visible walkable floor (incl. the spawn area, M7 GAP-0011 Verified) is drawn by [[FUNC_80010000]]/[[FUNC_80019934]] from DAT objects — see [[Finding - Visible ground from DAT verts]]; `fcn.800172dc` draws the broad terrain mesh layer but it is **occluded** (not the visible surface). Pin per-emitter source for the multi-emitter foreground.

## Source
`src_re_geometry/geometry_g30_terrain_render_source_plan.md` §13-14, §17
