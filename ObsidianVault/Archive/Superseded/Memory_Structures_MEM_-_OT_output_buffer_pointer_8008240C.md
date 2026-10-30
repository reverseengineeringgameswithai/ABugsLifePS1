---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - OT output buffer pointer 8008240C.md
aliases:
  - "MEM - OT output buffer pointer 8008240C"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - OT output buffer pointer 8008240C.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_OT_output_buffer_pointer_8008240C.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

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
