---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - gp0Trace.md
aliases:
  - "API - gp0Trace"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - gp0Trace.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - gp0Trace
type: api
category: Tracing
tags: [api, duckstation, gpu, gp0, displaylist]
updated: 2026-07-06
---
# API — gp0Trace (GP0 display-list trace)

> One entry per complete GP0 command at the FIFO dispatch point, with source provenance. Identifies *which* GPU primitives draw a thing.

## Methods & syntax
- **`gp0Trace.start {max_entries?=4096 (≤65536), max_params?=16}`** / **`stop`** / **`clear`**.
- **`gp0Trace.get {offset?, limit?=256, clear?}`** → `{entries:[{frame, command_id, command_id_hex, source:"dma"|"mmio", source_addr?, word_count, words:[hex]}], total, dma_count, mmio_count, warning?, note?, …}`. `command_id = words[0]>>24` (GP0 opcode). **`dma_count`/`mmio_count`** = the DMA-vs-MMIO source breakdown across all buffered entries (not just the page) — confirm DMA attribution at a glance.
- **DMA capture is verified end-to-end:** both block-mode and linked-list/ordering-table (DMA sync mode 2) GPU DMA route through `GPU::DMAWrite`, which stamps the source RAM addr into the GPU FIFO, so the hook tags them `source:"dma"`. The hook is **not** bypassed.

## Best use in ABL RE
Confirm a surface's primitive type and find the RAM source of its display list — e.g. distinguishing GP0 0x3C shaded-textured quads (terrain) from a GP0 0x02 background FILL (sky).

For a known screen pixel or small UI box, start with [[API - gpu.pickObject]] / `gpu.traceRegion`: they use this same completed-command capture automatically and return the final contributor(s), structured texture/CLUT/draw-mode, geometry, and DMA pointer chain. Arm `gp0Trace` when the surrounding state commands or pageable history are also needed. For live texture/CLUT source questions, use `gpu.vramWriteLog.get` for the upload timeline or `gpu.resolveVramProvenance` / `gpu.resolveClutProvenance` for a focused rect first.

## Common mistakes / gotchas
- CPU→VRAM image loads (`0xA0`–`0xBF`) and polylines record **only the header** — pixel data is streamed later and not captured.
- **`total:0` ≠ broken.** It means nothing was drawn in the window (a **static screen** / load — verify with [[API - frame hashing]] / [[API - framebuffer capture]] that the display hash changes), or the trace was armed mid-frame. `get` adds a **`warning`** in that case with the exact sequence: `start → clear → advanceFrames(N)` *(while actively drawing)* `→ get`.
- **`dma_count:0` is often correct.** Many games/scenes — and **all 2D menus** (ABL's title/menus, the BIOS shell) — issue GP0 by **MMIO** register writes, not the GPU DMA channel, so there is legitimately no `source:"dma"` to capture. `get` adds a **`note`** when everything is MMIO; cross-check [[API - dma state]] / [[API - transferLog]] (GPU channel) to confirm whether DMA is actually occurring. Capture during a **3D scene** to see `source:"dma"`.
> [!warning] The ring is cleared on the debugger's own [[API - loadState]] (kept armed), but **GUI/hotkey/rewind loads do NOT clear it** — call `gp0Trace.clear` after a GUI load.

## ABL examples
- Identified terrain as **GP0 0x3C** quads from [[MEM - Terrain vertex buffer 8012C1D0]] → [[Finding - Visible terrain renderer]].
- Identified the sky as a **GP0 0x02** background fill (`0x02db5931`), not an image → [[Finding - Sky is a GP0 background fill]].

## Related
[[API - gpu.pickObject]] · [[API - provenance.timeline]] · [[API - trace.armWhen]] · [[API - transferLog]] · [[API - gpu.readVramRect]] · [[API - execTrace]] · [[Finding - Sky is a GP0 background fill]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
