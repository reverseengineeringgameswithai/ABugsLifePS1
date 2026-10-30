---
type: experiment
status: complete
date: 2026-08-03
system: render ordering and packets
phase: 4
artifacts:
  - analysis/phase4_e03_ot_packet_census.json
  - analysis/phase4_e03_ot_walk_crosscheck.json
  - analysis/phase4_e03_emitter_roster.json
  - analysis/phase4_e03_transparency_modes.json
  - tools/phase4_e03_ot_packet_census.py
  - tools/phase4_e03_midframe_walk.py
  - tools/phase4_e03_ot_walk.c
  - tools/phase4_e03_crosscheck.py
  - tools/phase4_e03_emitter_watch.py
  - tools/phase4_e03_transparency_modes.py
  - tests/test_phase4_e03.py
---

# Phase 4 E03: OT/packet census per scene class, double-implemented

## Question

E03's `next`: capture one frame's OT chain per scene class (normal/boss/FMV);
classify packet families and their emitters. Missing list: primitive/object
families, lifetime, double buffering, transparency, OT ownership.

## Method

1. **gp0Trace census** (`tools/phase4_e03_ot_packet_census.py`, isolated
   instance port 23701, config `/tmp/dsrepro-e03-20260803`, pristine disc):
   per scene class, arm `gp0Trace` (start→clear→advance-while-drawing→get) over
   8 vsyncs, classify every GP0 command into a family, cluster DMA source
   addresses, sample `[0x8008240C]` + `gpu.getStatus` per vsync. Scene classes:
   normal gameplay (level02.sav), boss (level_15.sav), training
   (phase3_pristine_training_gameplay_i5.sav), FMV
   (movies/Phase4/E15_fmv_skip.movie.sav, drawing starts ~244 frames in).
2. **C cross-implementation** (the `region_provenance.c` double-implementation
   pattern, operator-requested): `tools/phase4_e03_midframe_walk.py` halts at
   the present DMA-kick call site 0x80064F28 (kick 0 and kick 1), records the
   list heads from a1, dumps 2 MiB RAM mid-frame; `tools/phase4_e03_ot_walk.c`
   walks the linked list from the RAM side exactly as DMA sync-mode-2 would;
   `tools/phase4_e03_crosscheck.py` diffs walker vs dispatch-time trace.
3. **Emitter roster** (`tools/phase4_e03_emitter_watch.py`): a 4-byte write
   watch on the primitive cursor `[0x8008249C]` + depth-bucket base
   `[0x80082230]` enumerates every packet allocator (batch-wise) per scene.
4. **Transparency** (`tools/phase4_e03_transparency_modes.py`): decode STP
   blend modes from E1 bits 5-6 and each textured semi-transparent prim's
   texpage attribute (2nd uv word's high half).

## Results

**Cross-check: EXACT agreement on all three 3D scene classes** — RAM-side walk
vs GPU dispatch stream, opcode-for-opcode: 492/492 (gameplay), 712/712 (boss),
749/749 (training). Two independent implementations of "what is in this
frame's OT" agree completely.

**The present is a SEQUENCE of linked-list kicks** through one helper call
site (0x80064F28), list head in a1: kick 0 = a 7-command env preamble node
(E3,E4,E5,E1,E2,E6,fill at `buffer+0x1C`; its terminator is real — env is its
own list, never linked into the body; an earlier "env linked at present"
hypothesis is RETRACTED, falsified by the kick-1 halt), kick 1 = the
depth-bucket body chain (head at `buffer+0x14E0`, both buffers structurally
identical), kicks 2+ = scene-dependent auxiliary lists (a scratchpad-built
list at 0x1F8010F0, stack-built lists ~0x801FFFxx) contributing zero GP0 draw
commands in the traced frames. Training fires ≥6 kicks per frame.

**Depth-bucket table: 1228 entries, invariant across scene classes** (walker
empty-link-node count; earlier per-scene 1025/1214 figures were artifacts of
trace-derived heads skipping leading empty buckets). Chain runs far→near with
LIFO insertion; `frame_present` (0x80039A70) is the SOLE writer of both the
primitive cursor and the bucket base (per-frame OT re-init has one owner).

**Packet lifetime: fully rebuilt every frame.** Across every adjacent-frame
pair in all 3D scenes, the ONLY recurring DMA source is the 4-command static
node at 0x8007FC84 (data segment), linked mid-chain. Same-buffer frame pairs
additionally share a deterministic allocation prefix (54–443 addresses — same
reset cursor + similar content, not retained packets).

**Double buffering, lockstep:** `[0x8008240C]` toggles 0x801E134C↔0x801CC390
per rendered frame (30 fps — 2 vsyncs/frame, re-confirmed independently) in
lockstep with the displayed VRAM rect x0↔x512. FMV never flips the OT pointer
and displays 24-bit color with a VERTICAL y248↔y8 buffer flip.

**Families quantified per scene class** (frame 0 examples): gameplay 519 cmds
= 342 gouraud-tex quads + 84 semitrans gouraud quads + 33 tris + 12 flat-tex
semitrans quads + 10 clear_cache + 10 cpu_to_vram blits + env; boss 739 (adds
sprite_var ×10, 54 flat-tex semitrans); training 776 (sprite_var ×45, heaviest
transparency, 45 backdrop 0x65 rects). **FMV regime**: exactly 20 CPU→VRAM
blits of 128×24 strips + 20 clear_caches per frame via MMIO + a DMA env sextet
— no polygons, no OT.

**Emitter roster (OT ownership):** core set in every scene = frame_present,
per_object_mesh_draw_payload_emitter (0x80010000), dirt_mesh_builder
(0x80014B04), contact_record_billboard_render (0x80014844), hud_draw_glyph,
ot_depth_fade_postprocess (0x80027004). Gameplay/boss add
shared_all_mesh_renderer (0x800172DC) + object_mesh_draw (0x8002D674); boss
adds grass_mound_mesh_builder + pickup_projector; training instead routes
skinned meshes via bone_matrix_array_mesh_transform and adds the backdrop
pair (backdrop_tile_builder, backdrop_horizon_gradient_draw). Counts are
batches (one cursor store per emitter batch).

**Transparency:** every semi-transparent prim in all three 3D scenes is a
textured polygon; blend modes decode to additive B+F dominant (88/100
gameplay; 144/214 training), subtractive B-F secondary (shadow-like), average
B/2+F/2 only in E1 defaults + 20 boss prims. Mode sums equal the semitrans
totals exactly (internal check).

## Open residuals (explicit)

- The sibling present call 0x80062C54 (committed SYS_world_render_dispatch
  question "other double-buffered OT or an empty layer") — not probed here;
  the kick-sequence structure suggests it is one of the auxiliary kicks.
- Auxiliary lists' content (scratchpad 0x1F8010F0, stack lists) — zero GP0
  draw commands observed; role unattributed (likely DrawSync/env-only kicks).
- The descriptor-table tpage/CLUT writer (phase-3 `writer_attribution:
  unresolved`) needs a level-TRANSITION fixture (save states land mid-level,
  after the writes) — unchanged, belongs to the descriptor row.

## Gates

`tests/test_phase4_e03.py` — 8 tests: census coverage/consistency, lockstep
double-buffering, static-node-only recurrence law, FMV regime, walker≡trace
on all scenes with the 1228-bucket invariant, walker compiles, emitter core
set + single reset owner, transparency accounting. All pass.

## Related

[[SYS_render_ot_and_present]] · [[SYS_world_render_dispatch]] ·
[[EXP_2026-08-03_phase4_e05_actor_model_binding]] (skinned-mesh draw chain)
