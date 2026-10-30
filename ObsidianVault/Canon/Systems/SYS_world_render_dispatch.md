---
kind: system
id: SYS_world_render_dispatch
created: 2026-07-08
updated: 2026-07-08
status: static_seen
confidence: medium
source_state: original_game_reference_or_mod_reference
src_paths:
  - src_re/world_render_dispatch.c
address: 0x0000000f
patch_policy: safe_to_read
---

# SYS_world_render_dispatch - world render dispatch

## Purpose

This page closes the migration source-coverage gap for `src_re/world_render_dispatch.c`. It records the symbol `world_render_dispatch` and links the C reference into the structured vault.

- Address if known: `0x0000000f`
- Coverage comments: none


## C source excerpt

Source: `src_re/world_render_dispatch.c`

```c
/* src_re/world_render_dispatch.c -- OG reverse-engineering: A Bug's Life (PS1, SCUS-94288)
 * The per-frame WORLD RENDER dispatch in the frame driver, and what it takes to suppress the native
 * level geometry (Tier-3 Phase 3c "render-suppression": blank the native terrain so a custom level
 * looks fully custom). Findings 2026-06-25 via live NOP/early-return experiments + gp0Trace.
 *
 * NOT a clean decompile -- this records the dispatch structure + the suppression-relevant facts.
 */

/* ---- the frame-driver render tail (around 0x80062c00 .. 0x80062d04) ----------------------------
 * The driver dispatches render work through function pointers (jalr ra,v0). The decisive call:
 *
 *   0x80062cfc  jalr ra, v0   ; v0 = 0x800646b8  -> draws the ENTIRE world ordering table (OT)
 *
 * NOP'ing 0x80062cfc blanks the whole frame to the sky-blue background fill -- terrain AND walls AND
 * objects AND Flik all vanish. So 0x800646b8 is the DrawOTag-style routine that DMAs the one OT
 * holding the complete 3D scene; the native terrain and the dynamic objects share that single OT.
 * (A sibling call 0x80062c54 -> 0x800646b8 has no visible effect -- the other double-buffered OT or
 * an empty layer.)  0x80062cc4 jal 0x80063778 = a different driver step (not the world draw).
 *
 *   0x80062d04  addiu a3,s2,14  -- the per-frame post-render hook the Tier-3 render cave installs
 *                                 (mod/caves/tier3_render.c); it composites the custom platform on
 *                                 top, AFTER the world OT has been drawn at 0x80062cfc.
 *
 * The game renders via GPU DMA (linked-list OT), NOT direct GP0-port writes -- gp0Trace captures
 * ZERO commands for a gameplay frame, confirming everything goes through the DMA'd OT.
 *
 * ---- ruled out (the old vault "blank it" leads were WRONG) -------------------------------------
 *  - early-return fcn.80010000  (jr ra @ entry): terrain unchanged.
 *  - early-return fcn.800172dc  (jr ra @ entry): terrain unchanged.
 *  - zero the runtime mesh buffer 0x8012c000..0x80130000: terrain unchanged.
 * So none of those is the per-frame terrain emitter; the terrain primitives are already in the OT by
 * the time the driver reaches the draw.
 *
 * ---- implication for Phase 3c -----------------------------------------------------------------
 * The whole-world DrawOTag (0x80062cfc) is too coarse -- killing it removes Flik/objects too. Clean
 * terrain-ONLY suppression needs one of:
 *   (a) EDIT THE OT: walk the linked-list the draw consumes and zero/skip the terrain primitives
 *       (must first distinguish terrain prims from object prims -- e.g. by texpage or OT depth);
 *   (b) find the TERRAIN-OT-BUILD function (inserts the level mesh into the OT) and suppress it,
 *       leaving the per-frame object inserts intact;
 *   (c) hook BETWEEN the terrain layer and the object layer (if the build is layered) and mask.
 * Next concrete step: capture the OT head argument at 0x80062cfc and walk the list to classify its
 * primitives (terrain vs object) -- that decides (a) vs (b).
 *
 * ---- the OT located (2026-06-25) --------------------------------------------------------------
 * 0x800646b8(a0,a1,a2,a3): at 0x80062cfc the args are
 *   a0 = 0x80064618  GPU/render context struct
 *   a1 = 0x801E1368  ORDERING TABLE head  (same 0x801E1xxx region as the drawenv 0x801E134C and the
 *                    back-buffer-select bit 0x20000 that abl_night_hook/tier3_render.c use)
 *   a2 = 0x00000040  = 64  OT bucket count
 *   a3 = 0x801E138C  second OT / primitive buffer
 * The routine prologue stashes them (s3=a0, s0=a1, s1=a2, s2=a3) and loops 0x80064f28 / 0x80064f5c
 * (per-bucket DrawOTag internals). So the world is a 64-bucket depth-sorted OT; terrain prims are
 * INTERLEAVED with object prims by Z, not a separable layer. Clean Phase-3c suppression = walk the
 * 64 buckets, classify each primitive (texpage = dirt vs sprite), and unlink the terrain ones --
 * tractable but involved + fragile; (b) finding the terrain OT-insert (static, likely built at level
 * load) is the cleaner target. Deferred: needs a focused OT-walk + texpage classification pass.
 *
 * ---- OT structure + builder MAPPED (2026-06-25, follow-up pass) --------------------------------
 * The DMA kick is 0x80064618 (called by 0x800646b8): it does sw a0,0(D2_MADR) then CHCR=0x01000401,
 * so a0 AT 0x80064618 ENTRY = the OT head being drawn. It is called SEVERAL times per frame:
 *   - drawenv OT @ 0x801E1368 (1 node, 9 words: E3/E4/E5/E1/E2/E6 + sky-fill 02) -- the background.
 *   - SCENE OT, DOUBLE-BUFFERED @ 0x801E282C / 0x801CD870 (alternates): ~2050 nodes (2048 depth
 *     buckets via ClearOTagR) holding ~810 textured polygons.
 * KEY: ~all 810 scene polys use ONE texpage 0x8D (terrain AND Flik AND props) + 1-2 on pages 9/10
 * -> TEXPAGE DOES NOT separate terrain from objects. So the discriminator must be the BUILDER.
 *
 * A terrain/mesh prim builder = the loop at 0x80013388..0x800135A8 (writers 0x8001350C / 0x80013590
 * / 0x80013594...): per iteration it assembles a 52-byte (13-word) textured-quad node into *s3 and
 * links it (sw t4,0(t9), the OT-bucket update at 0x8001358C; prim->next written via t5=[t9]). It is
 * inside a very large function (functionBounds merged 0x80008E98..0x800185B4 -- unreliable here).
 * NEGATIVE suppression tests (none blanked the VISIBLE dirt ground): early-return 0x80008E98;
 * NOP the OT-link 0x8001358C; early-return fcn.80010000 / fcn.800172DC; zero buf 0x8012C000.
 * => the on-screen dirt ground is built by a DIFFERENT/additional path than this one loop (this loop
 * likely builds a sub-mesh / off-screen or another layer). NEXT: at the 0x80013388 builder (and any
 * sibling builders), correlate the emitted prim's SCREEN XY to the visible ground to find WHICH
 * builder makes the dirt; or breakpoint per-prim and bisect by zeroing prim screen coords. Then NOP
 * that builder's call/loop. Tools live: paused OT-walk + per-prim write-watch (this session).
 *
 * ---- evidence ---------------------------------------------------------------------------------
 * NOP 0x80062cfc -> build/3c_nop_cfc.png (solid sky-blue). NOP 0x80062c54 -> no change
 * (build/3c_nop_c54.png). early-return 0x80010000/0x800172dc -> build/3c_kill_*.png (terrain intact).
 * Disc build/ABL_tier3_collision.cue, LEVEL01, settled. All edits were reverted after capture.
 *
 * ---- BUILDER ISOLATION (2026-06-25) -- dirt builder found, distinct from Flik's ----------------
 * Per-frame OT editor mod/caves/tier3_otfilter.c (hook 0x80064618). Recoloring all 0x3C prims paints
 * the WHOLE scene red (terrain + props + Flik are ALL gouraud-tex 0x3C quads on texpage 0x8D; size
 * can't split them) -> the discriminator must be the BUILDER. Write-watching prims sampled from the
 * BOTTOM-LEFT of the screen (pure dirt, far from centre-Flik) pins the DIRT builder to
 * **0x80010574..0x800108B4** -- an `s3 += 52` textured-quad prim loop in fcn.80010000 (lui t4,0x0c00
 * tag; stores to 0x8/0x14/0x2c/0x30(s3)). It is DISTINCT from the centre/Flik builder **0x80019AA0**
 * (GTE-RTPS mesh assembler in 0x800186F0). So dirt and Flik ARE separable by builder.
 * OPEN: early-returning/NOP-ing the dirt loop's stores did NOT blank the dirt, and OT-filter COLLAPSE
 * (zero a 0x3C prim's XY) did NOT either, though RECOLOR of the same prims works -> the visible dirt
 * is likely OVERDRAWN / a second pass. NEXT: tag the dirt loop's prims at build time + collapse only
 * tagged prims (Flik spared); and/or find the 2nd dirt pass. The 0x80010000 region is inside a giant
 * analyzer-merged function (no clean jr-ra/prologue), so suppress at the loop/store level.
 *
 * ============================================================================================
 * CORRECTION (2026-06-25, with FIXED tooling -- code-cache invalidation + gpu.pickObject):
 * The earlier "3c SOLVED via offset-gate" result (commit 159bc86) was an INSTRUCTION-CACHE ARTIFACT.
 * Every live suppression patch that "had no effect" was actually never executing (the recompiler ran
 * the stale cached block); the one offset-gate frame that looked like "foreground gone, Flik intact"
 * was the cave running partially/stale, NOT a real discriminator. After the fork added code-cache
 * invalidation, gpu.pickObject ground truth shows:
 *   - Flik prims (~0x..9594/0x..9628) and foreground-dirt prims (~0x..9f54/0x..9fe8) INTERLEAVE in
 *     the HIGH end of the scene-OT buffer; background grass/wall (~0x..2960/0x..3180) are LOW. So
 *     buffer offset tracks DEPTH (near=high, far=low), NOT terrain-vs-object -> an offset gate
 *     collapses Flik together with the near dirt. The offset gate is NOT a valid discriminator.
 *   - early-return fcn.80010000 removes the WHOLE near scene (foreground dirt AND Flik) -> it is the
 *     shared generic, type-dispatched (jump table @0x800103c0), DOUBLE-BUFFERED mesh renderer for
 *     both terrain and Flik. Background is a separate builder/OT.
 *   - NOPing the dirt loop's OT-link (0x8001089c, `sw t4,0(t9)`) did NOT blank the dirt -> the
 *     visible dirt comes through a DIFFERENT dispatch path than that one loop (multiple sub-builders).
 *   - pickObject all_contributors at a dirt pixel = 2 (a full-screen sprite behind + ONE 0x3C quad);
 *     at Flik = 3 (sprite + 2 quads). So not heavy overdraw -- the blocker is identifying WHICH of
 *     the jump-table sub-builders emits the visible dirt, per mesh.
 * STATUS: clean terrain-only blank PRESERVING native Flik is NOT solved. texpage / GP0 command /
 * prim size / buffer offset all fail; terrain + Flik share the renderer. Viable paths: (a) keep
 * native terrain as a backdrop under the custom platform (current honest state); (b) blank the whole
 * near scene (early-return fcn.80010000, works cleanly now) + render the custom level AND a custom
 * Flik; (c) write-watch a pickObject-confirmed dirt prim (reliable now) to pin its exact sub-builder
 * and suppress that path -- a focused but non-trivial follow-up.
 *
 * ============================================================================================
 * PATH (c) PUSHED with fixed tools (2026-06-25) -- mechanism nailed; it is OBJECT-level, not a NOP.
 * Map screen region -> builder PC (pickObject prim addr -> accessLog write-watch):
 *   fg-dirt-C/L -> 0x800199e8 / 0x80019934 (loop in fcn 0x800186F0);  fg-dirt-R -> 0x800107b0
 *   (loop in fcn.80010000);  Flik -> 0x80019164 (SAME 0x800186F0 loop) AND 0x80010834 (SAME
 *   0x80010000 loop);  grass/wall -> 0x80017480 (separate background builder).
 * => the per-prim "sub-builders" are GENERIC mesh assemblers SHARED by terrain AND Flik; NOPing one
 *    kills Flik too. Only discriminator = **a0 = mesh-data pointer** at the builder (execTrace @
 *    0x800199e8: a0 = 0x8017c1ec / 0x8016e130 ...; terrain meshes ~0x8018xxxx, Flik/objects
 *    ~0x8016-0x8017xxxx). s7 is just scratchpad (0x1f800000), not the object.
 * Each builder loop has MULTIPLE depth-conditional LINK paths. 0x800186F0 loop: 0x80019998 `bne`
 *   on `sltiu t,80` (near-clip) splits into two link sections; near-clip link = 0x800199cc
 *   (`sw t4,0(s6)`, s6=OT bucket, tag via `lui t6,0x0c00`), normal/far prims link in 0x800199d4+.
 *   NOPing 0x800199cc (near) OR 0x8001089c (0x80010 loop link) did NOT blank the VISIBLE dirt -> the
 *   visible prims take the OTHER depth path.
 * CONCLUSION: a clean terrain-only blank needs a0-gating EVERY link path in EVERY builder loop, OR
 * (cleaner) gating at the PER-OBJECT DISPATCH (the caller that sets a0=mesh + invokes the builder per
 * scene object): skip terrain meshes (a0 >= ~0x80180000) wholesale, one check per mesh. Find that
 * dispatch next (xrefsTo the builders; jump table @0x800103c0 is the type dispatch). Real scoped
 * effort, not a single NOP. Pragmatic alt = (b): early-return fcn.80010000 (blanks the whole near
 * scene cleanly) + render the custom level and a custom Flik.
 *
 * ============================================================================================
 * PER-OBJECT GATE TESTED (2026-06-25) -- a0 RANGE also fails; needs the object TYPE field.
 * fcn.80010000 is the PER-OBJECT near-scene renderer: 24 calls/frame, a0 = that object's mesh ptr.
 * Built + proved an a0-gated ENTRY hook (skip the object when a0 in a range, else replay prologue):
 *   - gate a0 in [0x80180000,0x80190000): changed the GRASS, kept Flik AND the foreground dirt
 *     -> 0x8018xxxx meshes are grass/background, NOT the foreground dirt.
 *   - gate a0 in [0x80170000,0x80180000): removed Flik AND foreground dirt-L together (both ->
 *     the sprite behind), while dirt-C/R (other ranges) stayed.
 * => FLIK and TERRAIN meshes SHARE the same a0 range (0x8017xxxx), and the foreground dirt is spread
 *    across multiple ranges. So a0 mesh-pointer RANGE cannot separate them either. The per-object
 *    gate MECHANISM works (it cleanly skips objects by a0 and spares others), but there is no
 *    pointer-range that isolates terrain from Flik.
 * FINAL: NO heuristic discriminator works (texpage / GP0 cmd / prim size / OT offset / builder PC /
 * a0 range). The only remaining separator is the object's TYPE/identity -- a field in the per-object
 * struct at a0 (e.g. [a0+0], read by the entry's `lw t7,0(a0)`). The clean (c) solve = read that
 * type field at the fcn.80010000 entry gate and skip terrain-typed objects. Finding which struct
 * field flags "terrain" (label each of the ~13 a0 per frame by gating it one-at-a-time + pickObject,
 * then diff terrain vs Flik structs) is the next dedicated step. Until then, pragmatic path (b)
 * stands: early-return fcn.80010000 (whole near scene) + custom render incl. a custom Flik.
 *
 * ============================================================================================
 * OBJECT-TYPE-FIELD HUNT -- DONE, NEGATIVE (2026-06-25). The per-object dispatch is a loop in the
 * function at 0x8001eacc..0x800206b0 whose ONLY call to fcn.80010000 is at 0x80020698 (24 calls/
 * frame). The per-object cursor is **s2** (callee-saved, so still valid at fcn.80010000 entry); the
 * struct: [s2+0x14]=mesh ptr (a0), [s2+0x18]=byte->a2, [s2+0x19] byte (game tests &0xc0 @0x80020650),
 * [s2+0x10] / [s2+0x24] = 0xc0080000 or 0xc0040000 (a layer/type-ish word), [s2+0x1c]/[s2+0x20] =
 * clip bounds. Findings:
 *   - Gating fcn.80010000 entry on `[s2+0x19] & 0xc0`: the bits-set group is NOT Flik (skipping the
 *     bits-CLEAR group removed terrain AND Flik). Flik is bits-clear, same as terrain.
 *   - The object structs are DYNAMICALLY REBUILT each frame at DIFFERENT addresses (0x80164xxx one
 *     frame, 0x80166xxx the next; 7 objects one frame, 16 another) -> no stable s2 to key on.
 *   - Skipping any single object struct had ~zero visible effect (only grass flickered for 2) -> the
 *     scene is heavily redundant/overdrawn; no single object IS the dirt.
 *   - No struct field (incl. [s2+0x10] c008/c004, [s2+0x19]) cleanly separates Flik from terrain;
```

Note: source excerpt truncated; 443 additional lines remain in `src_re/world_render_dispatch.c`.

## E03 census: present structure and packet accounting (2026-08-03)

The E03 OT/packet census answered this page's structural questions with a
double-implemented measurement (C RAM-walker ≡ gp0Trace, exact on 3 scene
classes): the present is a SEQUENCE of linked-list DMA kicks through the
helper call site 0x80064F28 — env preamble list, then the 1228-bucket body
chain (this page's "one OT holds the whole world" = that body list), then
scene-dependent auxiliary lists. Frames rebuild every packet (the dynamic
per-frame object structs this page observed match the census's fresh-address
law); the only static chain element is the 4-command node at 0x8007FC84. The
per-frame emitter roster (cursor write-watch) names every packet owner. The
sibling call 0x80062C54's role remains open — plausibly one of the auxiliary
kicks. Full detail: [[SYS_render_ot_and_present]] ·
[[EXP_2026-08-03_phase4_e03_ot_packet_census]].
