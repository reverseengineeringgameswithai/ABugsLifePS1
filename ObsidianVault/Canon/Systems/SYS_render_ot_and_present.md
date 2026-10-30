---
kind: system
id: SYS_render_ot_and_present
created: 2026-08-03
updated: 2026-08-03
status: runtime_confirmed
confidence: confirmed
source_state: original_game
address: 0x80064F28
src_paths:
  - tools/phase4_e03_ot_packet_census.py
  - tools/phase4_e03_ot_walk.c
  - tools/phase4_e03_crosscheck.py
  - tools/phase4_e03_emitter_watch.py
patch_policy: safe_to_read
---

# SYS_render_ot_and_present — the OT, the present sequence, and packet ownership

All claims double-implemented: a C linked-list walker over mid-frame RAM dumps
agrees EXACTLY with gp0Trace's dispatch-time stream on all three 3D scene
classes (492/492, 712/712, 749/749) — [[EXP_2026-08-03_phase4_e03_ot_packet_census]].

## Structure

- **Two output buffers**, `0x801E134C` (drawenv x0) and `0x801CC390` (x512),
  alternating per rendered frame (30 fps = 2 vsyncs/frame). `[0x8008240C]`
  (gp+0x674) = the displayed buffer; it toggles in lockstep with the displayed
  VRAM rect x0↔x512. Per-buffer layout is identical: **7-command env preamble
  node at `+0x1C`** (E3,E4,E5,E1,E2,E6,fill), **depth-bucket chain head at
  `+0x14E0`**.
- **Depth-bucket table: 1228 entries**, invariant across scene classes,
  walked far→near with LIFO insertion (classic addPrim: tag = *bucket |
  size<<24, *bucket = prim&0xFFFFFF). `frame_present` (0x80039A70) is the
  SOLE writer of both the primitive cursor `[0x8008249C]` and the bucket base
  `[0x80082230]` — per-frame OT re-init has one owner.
- **The present is a SEQUENCE of linked-list DMA kicks** through one helper
  call site **0x80064F28** (list head in a1 at the call): kick 0 = the env
  preamble list (own terminator; NOT linked into the body), kick 1 = the
  bucket body chain, kicks 2+ = scene-dependent auxiliary lists (scratchpad
  0x1F8010F0-built, stack-built) with zero GP0 draw commands observed.
  Training fires ≥6 kicks per frame.
- **Packet lifetime: everything is rebuilt every frame.** The only cross-frame
  recurring DMA source is a 4-command static node at `0x8007FC84` (data
  segment), linked mid-chain. Same-buffer frames also share a deterministic
  allocation prefix (same reset cursor), which is not retention.
- **After present, each buffer's OT is reset** (env node + terminator) — a
  post-vsync RAM dump never contains the full chain; only a mid-frame dump
  does (breakpoint the kick site).

## Packet families and emitters (OT ownership)

Emitters enumerated by write-watching the primitive cursor (batch-wise).
Core set in every scene: `frame_present`, `per_object_mesh_draw_payload_emitter`
(0x80010000), `dirt_mesh_builder` (0x80014B04), `contact_record_billboard_render`
(0x80014844), `hud_draw_glyph`, `ot_depth_fade_postprocess` (0x80027004).
Gameplay/boss add `shared_all_mesh_renderer` (0x800172DC) + `object_mesh_draw`
(0x8002D674); boss adds `grass_mound_mesh_builder` + `pickup_projector`;
training routes skinned meshes through `bone_matrix_array_mesh_transform`
instead and adds `backdrop_tile_builder` + `backdrop_horizon_gradient_draw`.

Family profiles per scene class (quantified, frame-exact):
`analysis/phase4_e03_ot_packet_census.json`. Gameplay ≈ 342 gouraud-textured
quads + ~100 semitrans prims + 10 CPU→VRAM texture-streaming blits per frame;
boss adds sprite_var ×10; training sprite_var ×45 + 45 backdrop 0x65 rects.

## Transparency

Every semi-transparent prim in the three 3D scenes is a **textured polygon**;
STP blend modes: additive `B+F` dominant, subtractive `B-F` secondary,
average `B/2+F/2` only in E1 defaults (+20 boss prims). Mode sums equal the
per-scene semitrans totals exactly: `analysis/phase4_e03_transparency_modes.json`.

## FMV regime

No polygons, no OT: per frame exactly **20 CPU→VRAM blits of 128×24 strips**
(MDEC output) + 20 clear_caches via MMIO + a DMA env sextet. Display is
**24-bit color** with a vertical y248↔y8 buffer flip; `[0x8008240C]` never
toggles during FMV.

## Corrections and retractions (2026-08-03)

- RETRACTED (same investigation): "the env node is linked into the body chain
  at present time" — falsified at the kick-1 halt; env is its own list.
- Earlier bucket-table figures 1025/1214 were head-derivation artifacts; the
  table is 1228 entries in all scenes measured.

## Open residuals

Sibling present call 0x80062C54's role; auxiliary lists' content (no GP0 draws
observed); descriptor-table tpage/CLUT writer (needs a level-transition
fixture; belongs to the descriptor row).

## Evidence

`analysis/phase4_e03_ot_packet_census.json` ·
`analysis/phase4_e03_ot_walk_crosscheck.json` ·
`analysis/phase4_e03_emitter_roster.json` ·
`analysis/phase4_e03_transparency_modes.json` · `tests/test_phase4_e03.py`
(8 gates) · [[EXP_2026-08-03_phase4_e03_ot_packet_census]]

## Related

[[SYS_world_render_dispatch]] · [[SYS_actor_model_loading]] ·
[[FUNC_80010000_per-object_mesh_draw_-_payload_emitter]] ·
[[FUNC_800172DC_shared_.ALL-mesh_renderer_(terrain_is_one_occluded_client)]]
