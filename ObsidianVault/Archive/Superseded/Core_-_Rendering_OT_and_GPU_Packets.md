---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Core - Rendering OT and GPU Packets.md
aliases:
  - "Core - Rendering OT and GPU Packets"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Core - Rendering OT and GPU Packets.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Core_-_Rendering_OT_and_GPU_Packets.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Core - Rendering OT and GPU Packets
type: core
updated: 2026-06-22
tags: [core, rendering, ot, gpu, gp0, milestone5, gap-0030]
---

# Core — Rendering: ordering table, GPU packets, frame flip (baseline)

> M5 consolidation for [[Gap Audit|GAP-0030]] — the OT/packet/flip pipeline in one place for visual debugging + editor correctness. **Provenance:** render chain + packet formats are STATIC/CONFIRMED; the OT layout + DMA-submit/flip call site are now CONFIRMED (static + live 2026-06-22, local-only — see *OT layout + flip chain*). See [[Rendering]] · [[Geometry pipeline]].

## Render chain (STATIC — CONFIRMED)
`[[FUNC_800224EC]]` (scene/render driver) → `[[FUNC_800140A0]]` (GTE trail-cull → survivor lists `0x80096EA8` / `0x8009E338`) → `[[FUNC_8001EA6C]]` / `[[FUNC_800206E8]]` (primitive builders) → **`[[FUNC_80010000]]`** (per-object mesh emitter: RTPS/RTPT/NCLIP, packs polys into the OT). Terrain/general-mesh surface = `[[FUNC_800172DC]]` (GP0 `0x3C` quads) via dispatcher `[[FUNC_8001DFE4]]` (5 emitters: `0x80014b04 / 0x80014ee0 / 0x800153d0 / 0x800163e0 / 0x800172dc`). `[[FUNC_80019934]]` = bulk-ground sub-emitter → `FUNC_80010000`.

## Ordering table / output buffer (STATIC — CONFIRMED)
- **`[0x8008240C]` = `G_GPU_OT_OUTPUT_BUFFER_PTR`** (gp+0x674): the active OT/output buffer; **toggles each render** between two framebuffers — `0x801e134c` (display x0) / `0x801cc390` (x512), distinguished by bit `0x20000`. The fresh scene is always in the **opposite (back) buffer** (basis of the flicker-free night hook). → [[MEM - OT output buffer pointer 8008240C]].
- Second staging pointer `[0x8008249c]` feeds the GTE transform leaf bank + is the geom base read by [[FUNC_8001DFE4]].

## GP0 packet formats (STATIC — CONFIRMED)
- **Terrain/mesh = GP0 `0x3C`** shaded-textured quads, stride `0x30`; verts low16=X/high16=Y at `+0x4/0xc/0x14/0x1c`, Z at `+0x8/0x10/0x18/0x20`, gray colours `+0x00/0x24/0x28/0x2c` → [[MEM - Terrain vertex buffer 8012C1D0]].
- **Sky = GP0 `0x02`** background FILL (`0x02BBGGRR`; observed `0x02db5931`), rebuilt each frame by `[[FUNC_800639CC]]` from DRAWENV RGB cache `0x800771BC/C0/C4` (`sky_clear_r/g/b`) → [[Finding - Sky is a GP0 background fill]].
- **`FUNC_80010000` payload** = `{u32 count; Vertex[stride 0xc]; cmd stream @ payload+4+count·0xc}`, type jump table `0x8001036c` (type-0 = triangle) → [[Finding - fcn.80010000 payload format]].
- Arbitrary GP0 primitives can be injected into a frame → [[Finding - GPU primitive injection]].

## Frame flip / libgpu primitives (STATIC string anchors)
ResetGraph `0x8001bf58`→`fcn.8006213c`; **DrawSync `0x8001bff4`→`fcn.800625fc`**; SetDispMask `0x8001bfe0`; **ClearOTag `0x8001c05c`**. Graphics init/teardown `fcn.80039970`/`fcn.80039a20` (call ResetGraph). The DMA submit + flip live in the per-frame driver around render hook `0x80062d04`; the night hook polls **D2_CHCR (`0xBF8010A8` bit 24)** for DrawSync and kicks the GPU DMA ([[Finding - Persistent night render hook]]).

## OT layout + flip chain — RESOLVED (2026-06-22, static + live; GAP-0030)
> Closes the two "Open questions" residuals below. Live anchor: isolated DuckStation (fork `fe0cca16b`, port 23460, binary sha256 `1ee88e2c…`), `SCUS-94288_1.sav` (LEVEL01). DYNAMIC/local-only (GAP-0001).

- **Double-buffer flip — LIVE-CONFIRMED.** Reading `[0x8008240C]` across displayed frames toggles the active OT/output buffer **`0x801E124C` ↔ `0x801CC390`** (the x512 buffer `0x801CC390` matches the documented base exactly; the x0 head reads ~`0x100` below the documented `0x801e134c` — the OT-list head vs framebuffer base). The scene is built into the back buffer and swapped on present.
- **OT structure — LIVE-CONFIRMED (`gp0Trace` one frame).** The OT is a **DMA linked-list resident in the active framebuffer** (`source:"dma"`, `source_addr 0x001CC3B0` = physical of `0x801CC390`) — i.e. the ordering table is built in the very double-buffer it flips. Nodes are standard libgpu env + primitive packets: **E1** texpage (`0xE100020A`), **E3** draw-area TL (`0xE3040200`), **E4** draw-area BR (`0xE407BFFF`), **E5** draw-offset (`0xE5080200`), interleaved with the `0x3C` poly primitives. ⇒ each OT node = a GP0 packet chained by its DMA tag in framebuffer RAM (libgpu `addPrim`/`DrawOTag` list).
- **Submit/flip call site — ENUMERATED (corrects the "inferred `0x80062d04`").** The per-frame driver `0x80062C70` calls the present routine via `jalr v0` at **`0x80062CFC`** — resolved live to **`v0 = 0x800646B8`** (`ra = 0x80062CCC`; fires 2×/4 advanced frames ⇒ 30 fps present); `0x80062E18` is the symmetric 2nd pass. **`0x800646B8` = libgpu DrawSync + DrawOTag-DMA present:** polls the VSync frame counter (`[0x8007FCCC]` vs `[0x8007FCD0]`, `andi 0x3F`) in wait-loop `0x80064F5C`, submits the OT via `0x80064F28` (DrawOTagEnv → DMA2), then advances `[0x8007FCD4]`. The night hook's `0x80062D04` is exactly the instruction *after* this present `jalr` (consistent). **Replay:** `execTrace.addWatch {pc:0x80062cfc, capture:[pc,ra,v0]}` → `execTrace.run {frames:4}`; `gp0Trace.start`→`advanceFrames {frames:3}`→`gp0Trace.get`.
- **Residual:** exact OT node *count* / Z-sort depth per frame (the list length varies with scene); the GPU-DMA register kick is the standard DMA2 linked-list (`0xBF8010A0` CHCR, busy bit `0x01000000`) per the night hook.

## gpu.pickObject ↔ rendered primitives (DYNAMIC — LOCAL-ONLY, dirty fork)
Resolves a native CRTC pixel → final GP0 drawable with exact DMA-packet + vertex-word addresses; **`orderingTableEntry = packet − 4`** (probable); `gteVertices` only when draw-time SXY0..2 match the packet → [[API - gpu.pickObject]]. Uses the same completed-command snapshot as [[API - gp0Trace]] (65536-record ring). **`gpu_object_picker` is a dirty-worktree-only module** ([[DuckStation Fork Reproducibility]]).

## Open questions
- ~~No formal OT-layout note + no per-frame submit→flip sequence; DMA submit call site inferred (`0x80062d04`).~~ **RESOLVED (2026-06-22)** — see *OT layout + flip chain* above: OT = DMA linked-list in the active framebuffer (`gp0Trace`), flip = `0x80062CFC`→`0x800646B8` (VSync + DrawOTag-DMA), buffer toggle `0x801E124C`↔`0x801CC390` live-confirmed. Residual = per-frame OT node count/sort depth.
- **Visible-floor contradiction — RESOLVED (M7/M8 2026-06-21; GAP-0008/0009/0010/0038):** `FUNC_800172DC`/chunk-35 was named "terrain renderer" but the 7-scene neutralize found it **~0 visible px (occluded)**; the visible floor = LEVEL.DAT via `FUNC_80010000` (f13). The findings store now holds **f13 as the sole CONFIRMED** floor answer (GAP-0008 Resolved; f5/f10 Superseded), and `FUNC_800172DC`/its buffer are reframed as the **shared mesh renderer** (GAP-0009/0010 Resolved). Treat `FUNC_800172DC` as a *general mesh renderer*, not "the visible floor."

## Next experiments
1. ✅ Done (2026-06-22) — `gp0Trace` one frame reconstructed the OT (DMA linked-list in framebuffer) + `execTrace` enumerated the flip call site `0x80062CFC`→`0x800646B8`. See *OT layout + flip chain*.
2. Optional: count OT nodes per frame across scenes to bound list depth (Z-sort resolution).

## Related
[[Rendering]] · [[Geometry pipeline]] · [[MEM - OT output buffer pointer 8008240C]] · [[Core - Camera and Projection]] · [[FUNC_800224EC]] · [[FUNC_80010000]] · [[FUNC_800639CC]] · [[API - gpu.pickObject]] · [[API - gp0Trace]] · [[Finding - GPU primitive injection]] · [[DuckStation Fork Reproducibility]]
