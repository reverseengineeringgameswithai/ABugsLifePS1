---
kind: memory
id: MEM_8008240C
aliases: [MEM_8008240C, 0x8008240c, "MEM - OT output buffer pointer 8008240C", "MEM - OT output buffer pointer", MEM_-_OT_output_buffer_pointer_8008240C]
address: 0x8008240C
name: OT_output_buffer_pointer_8008240C
status: static_seen
confidence: confirmed
source_state: original_game
system: []
read_by: []
written_by: []
related_structs: []
evidence: []
src_paths: []
patch_policy: unknown
---

# MEM_8008240C - OT output buffer pointer 8008240C

## Purpose

`[0x8008240C]` = the active GPU primitive / ordering-table output buffer the renderer packs into this frame. It holds one of the two DRAWENV work-area bases and **toggles each render** between the two framebuffers.

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - OT output buffer pointer 8008240C
type: memory
confidence: CONFIRMED
address: "0x8008240C"
tags: [memory, rendering, ot, double-buffer, gp]
---

# MEM — OT / output-buffer pointer `0x8008240C` (gp+0x674)

`[0x8008240C]` = the active GPU primitive / ordering-table output buffer the renderer packs into this frame. It holds one of the two DRAWENV work-area bases and **toggles each render** between the two framebuffers.

## The two values it alternates between
| Value | DRAWENV | Buffer | draw offset |
|-------|---------|--------|-------------|
| `0x801e134c` | env @0x801e134c | **x0** | (0, 256) |
| `0x801cc390` | env @0x801cc390 | **x512** | (512, 256) |

Distinguish them with **bit `0x20000`**: set ⇒ `0x801e134c` (x0); clear ⇒ `0x801cc390` (x512). (clip/ofs read live: `drawenv@0x801cc390` clip=(512,256,512,240) ofs=(512,256); `drawenv@0x801e134c` clip=(0,256,512,240) ofs=(0,256).)

## Why it matters (back-buffer targeting)
Sampled at the render hook **`0x80062d04`**, `[0x8008240C] == draw_off == the DISPLAYED buffer`, and the freshly-rendered scene (incl. the horizon haze) is always in the **opposite** (back) buffer. So to draw into the buffer that flips to display next (the back buffer) WITHOUT flicker, target the **opposite** of `[0x8008240C]`. This is the flicker fix in [[Finding - Persistent night render hook]].

- gp = `0x80081d98`; `0x8008240C` = gp+0x674. A second staging pointer `[0x8008249c]` (gp+0x6fc?) feeds the GTE transform leaf bank. (See `geometry_g10_payload_render_chain.md`, `geometry_g30...md:401,441`.)

## Related
[[FUNC_800639CC]] · [[Finding - Persistent night render hook]] · [[Finding - Visible terrain renderer]]

## Source
`src_re_geometry/geometry_g10_payload_render_chain.md:42-52`; `geometry_g30_terrain_render_source_plan.md:401,441-442`; live trace this session (drawenv builder s0 alternation + `[0x8008240c]` correlation at hook 0x80062d04).


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - OT output buffer pointer 8008240C.md`
- Migration status: copy-first Canon seed.
