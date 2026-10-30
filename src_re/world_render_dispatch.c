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
 *     Flik is just another generic mesh-object with the same struct shape as terrain chunks.
 * CAVEAT for any retry: pickObject at a fixed "Flik" pixel is unreliable -- "3c quad" there may be
 * terrain BEHIND Flik. Use all_contributors / project Flik's world pos (0x800a6500) to his exact
 * screen pixel and check his specific prim ram address.
 * CONCLUSION: ABL's renderer UNIFIES terrain and the player as generic, dynamically-listed mesh
 * objects with no usable static "is-terrain" discriminator on the render side. A clean terrain-only
 * blank preserving native Flik is not achievable via render-side gating with any discriminator found
 * (primitive, builder, a0 range, or object struct field). RECOMMENDED: path (b) -- early-return
 * fcn.80010000 to blank the whole near scene, then render the custom level AND a custom Flik marker;
 * OR keep native terrain as a backdrop under the custom platform. (A non-render-side route would be
 * to suppress the terrain at its DATA source -- e.g. zero the terrain mesh list the dispatch reads --
 * but that is the native-format work Tier-3 set out to bypass.)
 *
 * ============================================================================================
 * P21 RENDER/CULL POINTER FAULT PROVENANCE (2026-07-06) -- Track-B collision expansion blocker.
 * The P18/P20 minimal failing collision replacement interaction (P17 seed sectors 93/99/100/107/108
 * plus sectors 0/73/92) does NOT fail by reaching the swept floor resolver. It faults earlier in this
 * render/cull object traversal and then the scheduler/player update stops because the guest is in the
 * exception path.
 *
 * The fault site is the dispatch case for key 65:
 *   0x8001EAF4  lw s0,0x10(a1)       ; load object/render node payload holder
 *   0x8001EAFC  lw s2,0x18(s0)       ; load native payload/node pointer
 *   0x8001EB3C  lw v0,0x0(s2)        ; data bus error when s2 is invalid
 *
 * Failing seed+0/73/92 trace:
 *   a1=0x80173130, [a1+0x10 @ 0x80173140] = 0x801c3614
 *   s0=0x801c3614, [s0+0x18 @ 0x801c362c] = 0xfffabfa0  (outside PS1 RAM)
 *   dispatch key = 65, jump table 0x8001aa74 -> 0x8001eb3c
 *
 * Passing controls at the same dispatch target load valid main-RAM payload pointers from the same
 * field shape: seed+0/73 loads [0x801c1678]=0x801741e0; sector-92-alone loads 0x80171e4c;
 * P17 seed loads 0x80170598; P18 prefix07 loads 0x801791d4. Each readable pointer has the expected
 * native node/payload shape (including the 0xc0080000 marker in the first words).
 *
 * A post-arm write watch on the failing source slot 0x801c362c recorded zero writes before the fault,
 * so the bad value is already present when this traversal consumes it. An early long watch saw source
 * slot write leads at reported PCs 0x8001d1b8, 0x800319a4, and 0x80031a68; because accessLog write
 * PCs can be instruction+4 and value_hex is the pre-write value, the instruction-level candidates are
 * 0x8001d1b4 `sw s0,0(s1)`, 0x800319a0 `sw s7,0(t9)`, and 0x80031a64 `sw v0,0(a2)`. Treat those as
 * builder leads, not final writer proof.
 *
 * Collision correlation: replacing sector 92 in the interaction expands chunk-32 by 6324 bytes
 * versus the seed+0/73 control and shifts later block data, but P21 proves the immediate crash is a
 * bad render object/list field consumed here, not a normal collision-candidate rejection. Evidence:
 * docs/G3_NATIVE_P21_RENDER_CULL_POINTER_PROVENANCE.md and
 * build/g3_native_p21_pointer_provenance_report.json.
 *
 * P22 BUILDER PROVENANCE (2026-07-06): the bad field is not a literal on-disc value and is not
 * written by this dispatch body. tools/trace_g3_native_render_node_builder.py proves:
 *   - media/static search finds no 0xfffabfa0 byte pattern or failing node prefix in the built bin,
 *     staged RAW/DAT/EXE snapshots, decompressed chunk 32, runtime patch JSON, or P21 flight dumps;
 *   - temporal scan: [0x801c362c] is valid pointer 0x80175b84 at movie frame 4282 and becomes
 *     0xfffabfa0 at frame 4283; passing controls keep valid analogous payload pointers;
 *   - focused exec/access trace captures 0x80031a64 `sw v0,0(a2)` with a2=0x801c362c and
 *     v0=0xfffabfa0. ra=0x80031890 places the writer in the collision grid/list builder
 *     0x800313a8..0x8003229c, not in render/cull.
 *
 * Therefore dispatch key 65 is the consumer/victim: it expects s0+0x18 to be a native payload/node
 * pointer, but in the failing seed+[0,73,92] build that RAM range has already been populated with
 * collision grid/bounds data. P23 target: inspect the collision grid/list builder destination ranges
 * and limits around 0x800319a0 `sw s7,0(t9)` and 0x80031a64 `sw v0,0(a2)`, because replacement of
 * sector 92 expands decompressed chunk 32 by 6324 bytes and exposes an in-RAM ownership/layout
 * collision between that builder output and this render/cull source slot. Evidence:
 * docs/G3_NATIVE_P22_RENDER_NODE_BUILDER_PROVENANCE.md and
 * build/g3_native_p22_builder_provenance_report.json.
 *
 * ============================================================================================
 * TIER-3 TRACK B v1 (2026-06-27) -- pragmatic OT cleanup, not identity-level RE.
 * After Track A replaced native pickups/exit with blob-owned gameplay, the remaining visible residue on
 * the Tier-3 render disc was cosmetic native props/effects (leaf/right props/mosquito body/sparkles).
 * Two data-level candidates were live-tested and rejected:
 *   - zero actor/render list 0x80090748 (48 * 0x84) for 2 frames -> residual props still rendered;
 *   - zero contact/object array 0x800b0d18 (64 * 0x38) -> black frame / unsafe, not a visual-only suppressor.
 * Shipped mod-side v1 therefore stays in the existing OT pass:
 *   - lower the native OT offset gate in mod/caves/tier3_otrender.c from 0x3000 to 0x1800;
 *   - collapse residual native effect command classes GP0(2e)/GP0(3e).
 * Live validation on the rebuilt cold-boot disc: large leaf/right props/mosquito body are gone and Flik/HUD/
 * Tier-3 mesh remain intact. A stricter 0x1000 gate removes the last tiny fragments but clips Flik's body/arms,
 * so it was rejected. This is a bounded cosmetic cleanup, not a solved native object identity discriminator.
 *
 * ============================================================================================
 * MULTI-PASS OT STRUCTURE + BACKGROUND/SCENE DISCRIMINATOR (2026-06-30) -- depth-layer RE.
 * Pinned down WHY a Tier-3 ground prepended into the OT could still cover the native HUD/seed-power
 * overlay. The DrawOTag DMA kick 0x80064618 fires for SEVERAL distinct OT chains per DISPLAYED frame
 * (double-buffered: a different buffer-pair each present). Live evidence (execTrace addWatch on the
 * hook entry, capture a0 = OT head; runUntilAddress 0x80064638 = the MADR store, read a0):
 *   - BACKGROUND chain, drawn FIRST: head is a POPULATED env+sky node -- tag length != 0 (heads seen
 *     0x801E1368 / 0x801CC3AC, exactly 1 node, 9 GP0 words = E3/E4/E5/E1/E2/E6 + the GP0(02) blue
 *     sky-fill). This is the backdrop.
 *   - SCENE chain, drawn SECOND: head is an EMPTY ClearOTagR bucket -- tag length == 0 (heads seen
 *     0x801CD870 / 0x801E282C, ~1200-1600 nodes) holding native terrain + Flik + objects + the
 *     HUD/seed-power overlay, depth-sorted (near=high buffer offset, far=low; see the 2026-06-25
 *     CORRECTION above).
 * => CLEAN, ROBUST DISCRIMINATOR for "is this the backdrop pass": read [ot_head]>>24; nonzero = the
 *    background/sky pass, zero = a scene/overlay pass. (Earlier work keyed on the head ADDRESS, which
 *    is fragile across the double buffer / level; the head TAG LENGTH is stable.)
 * The pause/START menu is drawn by a path that does NOT call this kick (the hook's per-call sentinel
 * did not advance while paused), so menu frames are not reachable from here.
 * DEPTH CONSEQUENCE: a prim's visibility is the painter order ACROSS passes, not just within one. A
 * Tier-3 ground PREPENDED into the SCENE chain draws behind Flik (verified: MADR a0 = our NODEBUF, so
 * the DMA starts from our nodes -> Flik on top) yet still lands IN FRONT of the seed-power overlay,
 * because that overlay composites in a layer the scene-pass ground precedes. The only way to be a true
 * backdrop behind EVERYTHING native is to inject into the BACKGROUND pass (append after the sky node).
 * suppress_terrain is NOT a factor for the overlay: a clean LEVEL01 scene maxes out at OT offset
 * 0x17A4 (< the 0x1801 gate) with no GP0(2e/3e) prims, so the gate collapses nothing there.
 * The mod-side consumer of this finding is mod/caves/tier3_otrender.c (renders the Tier-3 ground only
 * in the background pass, appended after the sky fill; scene pass = suppress_terrain only).
 *
 * ============================================================================================
 * TIER-3 LEVEL-REPLACEMENT PHASE 1 -- EVIDENCE PASS (2026-07-01, fixed tools: gpu.pickObject +
 * matched-frame loadState A/B). Goal: classify what native content LEAKS through suppress_terrain at a
 * grazing angle on the current render disc, and map each to a SOURCE removal (not a render-side gate,
 * which is proven impossible above). Method: reach LEVEL01 (movie + turbo), pan to grazing, pickObject
 * grid-census over the 512x224 CRTC; classify by GP0 command + texpage + clut + source.ramAddress.
 * FINDINGS (per-prim signatures, verified live):
 *   - OUR custom floor   = GP0(24) textured-tri, texpage 0x660, clut 0x3ffc, ram in NODEBUF 0x801F9400+.
 *   - Authored collectibles (KEEP) = native type-0x3f objects riding the native OT: GP0(2c) clut 0x3677
 *     (grain), GP0(2e) clut 0x3672 (FLIK letter), GP0(2d) clut 0x3770. (ram in the native scene OT, NOT
 *     our NODEBUF -- so ramAddress cleanly separates OUR prims from native ones.)
 *   - NATIVE TERRAIN LEAK = GP0(3c)/GP0(34) GOURAUD-textured, texpage 0x604, clut 0x3a70..0x3a78, ram in
 *     the native scene OT (0x1cd/0x1ce/0x1e2/0x1e3xxx). This is the flicker the operator sees.
 *   - NATIVE DECOR / floating objects = GP0(60) sprites (no texpage) + GP0(3e) + surplus type-0x3f
 *     collectibles floating in the sky at ORIGINAL LEVEL01 coords.
 * DECISIVE matched-frame A/B (loadState + 3-frame advance; chunk-35 submitter FUNC_800172DC live-stubbed
 * to `jr ra; nop`, code-cache auto-invalidated): NAT_TERRAIN census 19 -> 10 hits; OUR_FLOOR (407->410)
 * and authored collectibles (29->30) UNCHANGED. => FUNC_800172DC (chunk-35) is ~HALF the terrain leak,
 * and stubbing it is SAFE (does not touch our floor or collectibles). The OTHER half is a DIFFERENT
 * builder: fcn.80010000 is already COPIED-gated-stubbed in LEVEL01 (verified @0x80010000 = 0x0801fcc1,
 * COPIED=1) so it is NOT the residual source -- ruling it out. Residual terrain builder UNIDENTIFIED
 * (candidates: the background builder 0x80017480, the shared mesh assembler 0x800186F0, or a DAT
 * terrain-mesh payload fed to the generic per-object dispatch). NEXT (Phase 4): pickObject a residual
 * terrain prim -> accessLog write-watch its OT node -> builder PC (the same pickObject->writer technique
 * used above), then stub/null it at the source. Full roadmap: ObsidianVault "Tier 3 - Level Replacement
 * Phases". Mod consumers: chunk-35 stub -> mod/tier3_loader.asm (Phase 3); object deletes ->
 * tools/build_tier3_render_disc.py (Phase 2).
 *
 * PHASE 3 UPDATE (2026-07-01): FUNC_800172DC pinned down + suppressed at source. transferLog.resolve says
 * it is RESIDENT EXE (SCUS_942.88 fileOffset 31452, exact) -- NOT a per-level overlay -- so it is shared by
 * every level and the suppression must be LEVEL01-gated. Its prologue is 0x800172DC `lui v0,0x1f80` +
 * 0x800172E0 `ori v0,v0,0` (ori is a no-op), then it GTE-loads a matrix and emits the chunk-35 gouraud
 * quads buffered at 0x8012c1d0 (first word 0x3c747474 = a GP0(3c) template). Baked a COPIED-gated neuter
 * (tier3_neuter_172dc @0x8007F340, hook at 0x800172DC) in mod/tier3_loader.asm, mirroring the fcn.80010000
 * neuter. Proof (execTrace on the body 0x800172E4): COPIED=1 (LEVEL01) -> 0 hits (suppressed); COPIED=0
 * (LEVEL00/2/boot/load) -> 16 hits (runs) -> native terrain preserved there. IMPORTANT: both FUNC_800172DC
 * (chunk-35) AND a still-unidentified 2nd builder emit gouraud texpage-0x604 terrain, so suppressing chunk-35
 * only removes its (pose-dependent) share; the 2nd builder is the Phase-4 target.
 *
 * PHASE 4 INVESTIGATION (2026-07-01) -- residual terrain builders PINNED; render-side removal CONFIRMED
 * INTRACTABLE (re-confirms this file's multi-session conclusion). With fcn.80010000 + FUNC_800172DC both
 * stubbed (execTrace: 0 body hits in LEVEL01, Flik STILL renders -> so fcn.80010000 does NOT draw Flik in
 * this build, contra the old note), the leftover grazing terrain was traced by pickObject -> accessLog
 * write-watch on the OT node:
 *   - dirt, gouraud GP0(3c)/GP0(34) texpage 0x604, clut 0x3a7x: writer PC 0x80014ce8, inside FUNC_80014b04
 *     (entry byte-identical to FUNC_800172DC: `lui v0,0x1f80; ori v0,v0,0; lw a1,0x20(a0); lw a2,[0x80082424]
 *     ; sw s0..s6,(v0)` -- a sibling GTE terrain submitter). Called from the world-render dispatch
 *     0x8001d3cc..0x8001dfe0 (functionBounds EXACT) at 0x8001dcbc.
 *   - grass/mound, gouraud GP0(3c) texpage 0x663, clut 0x3e7x: writer PC 0x80013700, inside the fn
 *     0x80013108..0x8001409c (EXACT).
 *   - the "sand cliffs" a grazing view shows are actually OUR floor (GP0(24) texpage 0x660, NODEBUF) -- not a leak.
 * MESH SOURCE is TERRAIN-ONLY: over 40 breakpoint hits at 0x80014ce8, a1 (mesh ptr) was ALWAYS in the
 * decompressed-LEVEL.RAW terrain region 0x8012c64c..0x8012e5cc -- NEVER Flik's CHARS model region. So the
 * terrain data IS separable from Flik at the DATA level (unlike the a0-range render-side gate, which fails).
 * BUT render-side neutering FAILS: naive `jr ra` early-return at FUNC_80014b04 / the grass fn / the dispatch
 * either DESTABILIZED the guest (pc -> 0x00000df8 / 0x1a44, invalid) or left the terrain census UNCHANGED
 * (TERR663 85->95, TERR604 11->9) -- multiple tangled builders/paths, and the dispatch 0x8001d3cc reads
 * Flik.X (0x800a6500) at entry so it is world/Flik-coupled, not terrain-only. Whack-a-mole per-builder EXE
 * stubs are both unsafe and incomplete.
 * CONCLUSION / DEFERRED PATH: the residual terrain must be removed at its DATA SOURCE -- null the LEVEL.RAW
 * terrain-mesh list the submitters iterate (root ptr [0x80082424]=0x801cc554 -> [0x8008240c]=0x801cc390;
 * mesh vertex data 0x8012xxxx) so the submitters find ZERO terrain meshes while Flik (CHARS) is untouched.
 * That is a bounded but non-trivial RE task (decode the mesh-list header/count, null it from the cave
 * SPAWN one-shot or at the LEVEL.RAW disc source, verify collision + loader + Flik survive) -- deferred as
 * its own session. The alternative complete fix stays the GTE depth-sorted render path. Phases 0-3 (LEVEL00
 * gate, object deletes, chunk-35 stub) shipped; Phase 4 is documented + deferred, not forced. Full roadmap:
 * ObsidianVault "Tier 3 - Level Replacement Phases".
 *
 * PHASE 4 DATA-SOURCE RE + PoC (2026-07-01) -- terrain render is a DATA-DRIVEN MULTI-DISPATCH, and an
 * empty-terrain-list PoC is SAFE (Flik/collision/loader/objects intact). CORRECTION to the "root ptr" note
 * above: [0x80082424]=0x801cc554 is the OT the terrain links INTO (a ClearOTagR reversed list; each word =
 * its-own-addr-4), and [0x8008240c]=0x801cc390 is the GPU draw-env (GP0 0xe1/e3/e4/e5) -- NOT the mesh list.
 * The terrain is drawn from PER-OBJECT RENDER LISTS, one per pass, each with its own count:
 *   DIRT (tp 0x604, FUNC_80014b04) -- dispatch FUNC 0x8001d3cc..0x8001dfe0 (EXACT) walks an 84-byte-stride
 *     object array, per-object type-dispatches to FUNC_80014b04. Loop bound (0x8001df90):
 *     `P=[0x800a6300]; count=(u16)[P+6]; loop while ++i<count`. Live P=0x800ff984, count=24; each object's
 *     [obj+0x20] = a LEVEL.RAW terrain mesh ptr (0x8012xxxx) -- ALL 24 terrain, NONE Flik.
 *     ** LEVER (proven): write 0 to the u16 at [ [0x800a6300]+6 ]. Built ONCE at load (persists, not
 *     per-frame). With it 0, FUNC_80014b04's store 0x80014ce8 drops 24 -> 0 hits, the tp604 dirt disappears,
 *     census TERRAIN 154 -> 107. **
 *   GRASS/MOUND (tp 0x663, builder 0x80013700 in fn 0x80013108..0x8001409c EXACT) -- a SEPARATE dispatch
 *     FUNC 0x800206e8..0x800212f8 (EXACT), called from 0x800228c0 with a0=array 0x80096ea8, a1=count(=s0,
 *     live 18), a2=OT 0x801cc554. Its loop bound is the REGISTER s7=a1 (`blez s7` skips) -- a caller ARG,
 *     so its lever is the caller's count source (s0 in 0x800228xx, not yet pinned to a memory word).
 *   (both dispatches link into the SAME OT 0x801cc554; Flik is drawn by NEITHER -- separate, as required.)
 * PoC RESULT: zeroing the DIRT count each frame at a grazing pose removed the tp604 dirt with FULL integrity
 * -- Flik WALKED (Up 30f -> position moved, grounded=0x0101) and JUMPED (vy=1088 airborne), collision held
 * on the custom floor, loader stable (COPIED=1, DAT=0x801607f8, no crash), type-3f table = 15 throughout.
 * Renderers were NOT modified (pure data poke). This VALIDATES the data-source approach as safe + non-destructive
 * (unlike the render-side jr-ra above, which crashed). REMAINING for FULL terrain removal: empty EACH terrain
 * dispatch's list -- DIRT lever done; GRASS needs its count source (s0 in 0x800228xx) pinned to a memory word
 * (or force a1=0 at 0x800206e8 entry); then survey for further passes. Eventual mod = zero these counts from
 * the collision cave's LEVEL01 SPAWN one-shot (DIRT count persists so a one-shot suffices; GRASS may need
 * per-frame if rebuilt). Harness: scratchpad p4b_*.py.
 *
 * PHASE 3 REVERTED -- FUNC_800172DC IS FLIK-SHARED (2026-07-01). CRITICAL correction to the Phase 3 note
 * above (chunk-35 neuter): FUNC_800172DC is NOT terrain-only. It is one of ABL's generic GTE mesh submitters,
 * shared by terrain AND the player -- stubbing it (COPIED-gated) to hide chunk-35 also removed FLIK'S BODY
 * mesh, so Flik rendered as a headless/torsoless thin-limb figure. Decisive A/B (live, LEVEL01): restoring
 * FUNC_800172DC's prologue at 0x800172DC (0x0801fcd0 -> 0x3c021f80) brought Flik's torso back WHOLE; re-applying
 * the neuter removed it. Phase-1's "19->10 while KEEPING Flik" was a FALSE pass -- it checked the terrain census
 * + Flik's STATE (pos/grounded), never his MODEL, so the missing torso went unnoticed (the thin figure in the
 * Phase-3 captures was misread as an animation pose). REVERTED the FUNC_800172DC hook + tier3_neuter_172dc in
 * mod/tier3_loader.asm. LESSON (reinforces this file's thesis): render-side stubbing of a shared submitter is
 * the intractable path -- ALWAYS verify Flik's MODEL (capture, not just state) after a render change. This is
 * exactly why the Phase-4 DATA-SOURCE lever is correct: emptying a terrain render-LIST count makes the shared
 * submitter iterate zero TERRAIN objects while still drawing Flik (verified: the DIRT-list poke keeps Flik whole).
 * Grass count = computed by FUNC_80014360 (0x80014360..0x80014500, EXACT), a GTE cull/build that transforms the
 * grass source, writes the visible list to 0x80096ea8, and returns the count (v0 -> s0&0xffff at 0x80022888);
 * its lever is the source count (inside FUNC_80014360, not yet pinned) or forcing a1=0 at 0x800206e8.
 *
 * PHASE 4 DONE -- both gouraud terrain passes source-removed + baked (2026-07-01). Grass lever pinned:
 * FUNC_80014360 iterates a SENTINEL-TERMINATED source list at 0x80163F74 (per-object stride 20; the loop
 * exits on `lh t3,0xe(a0); bltz t3` at 0x800143f0/f8), GTE-culls, and returns the visible count. So the grass
 * "count" is computed from the source, not stored -- the DATA lever is the source terminator: write a negative
 * halfword to [0x80163F74+0xe] (obj0 becomes the terminator) -> FUNC_80014360 returns 0 -> dispatch 0x800206e8
 * draws nothing. Proven: grass tp663 census 100 -> 0, dirt + Flik untouched. Source 0x80163F74 lives in the
 * LEVEL01 DAT region (0x801607F8 + 0x377C), deterministic. BOTH terrain levers (DIRT count [[0x800A6300]+6]=0 +
 * GRASS source truncate) PERSIST (built once at load) and are baked into the collision cave's SPAWN_DONE
 * one-shot (mod/caves/tier3_collision.c; already DAT_BASE-gated to LEVEL01). Cold-boot (disc 04d7a25f...):
 * gouraud terrain (604/663) = 0 at spawn/grazing/roam+jump, Flik's MODEL whole (walks/jumps, no crash) --
 * because emptying the render LISTS leaves the shared GTE submitters intact (the Phase-3 failure mode, stubbing
 * a shared submitter, is avoided by construction).
 *   ** CORRECTION (2026-07-01): the DIRT lever is NOT Flik-safe. **  Cold-boot on the both-levers bake dropped
 *   FLIK entirely (0 gouraud prims at his spawn pixel). Diagnosed live: restoring the GRASS source left Flik
 *   gone, restoring the DIRT count ([[0x800A6300]+6]->24) brought him back (0->45 prims). So dispatch 0x8001d3cc
 *   DRAWS FLIK too -- count=0 early-exits the pass and skips his draw (the "all 24 objects terrain, none Flik"
 *   sample missed that Flik is drawn by the dispatch outside/after the counted loop). The earlier "Flik-safe"
 *   check verified STATE, not MODEL -- same mistake as Phase 3. FIX: the baked one-shot (tier3_collision.c)
 *   applies ONLY the GRASS source-truncation (Flik-safe); the DIRT count lever is removed -> dirt tp604 stays.
 *   DIRT removal is OPEN: needs a Flik-separable lever (e.g. null the terrain objects' [obj+0x20] mesh ptrs in
 *   the list while keeping count>0 so Flik's draw survives -- unverified) or the GTE render path.
 *   ** DIRT-PASS RE DONE (2026-07-01) -- the mesh-null lever CORRUPTS the OT; dirt is inseparable from Flik. **
 *   Enumerated the [0x800A6300] list: 24 STATIC terrain objects (base 0x8008a054, stride 84; [obj+0x20] mesh
 *   ptr = 0x8012c5f8..0x80131194, all LEVEL.RAW; dynamic-checksum after Flik jumps: NONE animate). FUNC_80014b04
 *   parses each object's mesh as a GP0 prim STREAM (48-byte prims; lwc2 v0/v1/v2 + rtpt GTE-transform per prim);
 *   loop head 0x80014b8c `lw t0,0(a1)`; it EXITS when a prim command word has (t0 & 0x3c000000)==0 (0x80014bec
 *   `and t1,t0,0x3c000000; bne t1,0x3c` -> 0x80014d78 `beq t1,zero,exit`) -- so mesh[0]=0 is a 0-prim terminator.
 *   Flik's body is gouraud TEXPAGE 0x604 -- the SAME as the dirt -- built in the SAME 0x8012xxxx work region, so
 *   it is indistinguishable from dirt by texpage OR mesh region. PoC (null the 24 terrain objects' mesh[0]=0,
 *   keep count): FAILS, and NON-LINEARLY -- nulling either 12-object HALF leaves Flik's body box UNCHANGED (94
 *   picks), but nulling ALL 24 drops it to 12 (Flik broken). A clean per-object 0-prim would be linear; the
 *   all-or-nothing threshold = the zeroed objects leave dangling/short OT nodes that CORRUPT the shared scene-OT
 *   chain, so Flik (drawn later in the same chain) is dropped. Results were also fragile/pose-dependent. CONCLUSION:
 *   the DIRT pass is inseparable from Flik via the render-list/mesh lever (shared dispatch + texpage + work region
 *   + OT chain) -- confirms this file's overall thesis. GRASS was cleanly removable (SEPARATE dispatch 0x800206e8
 *   + its own source list); DIRT is not. Only clean route left = the GTE depth-sorted render path (draw our own
 *   everything -> native suppression moot). Kept the safe GRASS-only bake (disc cbfff41c, Flik whole, dirt stays).
 *   ** FORMAT-PRESERVING PRIM-STREAM PATCH (2026-07-01) -- CONCEPT VALIDATED (Flik's model SURVIVES), cold-boot
 *   BAKE unresolved. ** Decoded FUNC_80014b04's per-object mesh = a GP0 prim STREAM: prims are read at
 *   [a1+0]=cmd; the loop TERMINATES when a command word has (cmd & 0x3c000000)==0; each prim's OT node inserts
 *   per-prim into the scene OT depth buckets. Vertex/colour data is in the prim's [a1+4..a1+0x2f]. **The
 *   format-preserving no-op: keep every command word (so stream length + prim count + terminator + per-prim OT
 *   structure are all preserved) but ZERO each prim's 44 vertex/colour bytes -> the terrain prim becomes a
 *   degenerate/culled no-op.** LIVE PoC (settled state): parse objects 0..count-2, zero their prim verts, SPARE
 *   the last object -> dirt tp604 census 28->3 and FLIK'S MODEL IS INTACT (full ant, flik-box 93). So Flik's
 *   model DOES survive a correct format-preserving patch -- the key question answered YES. Flik = the LAST object
 *   (index count-1); found by a clean bisection (this patch is LINEAR, unlike the OT-corrupting mesh[0]=0).
 *   COLD-BOOT BAKE FAILED though: baking it (per-frame, then one-shot, both LEVEL01-gated) consistently broke
 *   Flik + crashed (pc->0x1a44) at cold-boot despite the settled-state PoC working. Two real defects were found +
 *   mitigated but not fully cured: (a) the prims are NOT all 48 B -- the fixed-48 stride DESYNCS (obj22's parse
 *   over-ran into Flik's mesh 0x80131194; mitigated with a hard "a1+0x30 <= flik-mesh" bound); (b) the parse is
 *   NON-IDEMPOTENT (zeroed bytes become false terminators), so per-frame re-patching drifts (mitigated with a
 *   one-shot DIRT_DONE flag). Even with a+b mitigations + a valid-list guard, the cold-boot patch still broke
 *   Flik identically -- a cold-boot-vs-settled difference (Flik-index timing or the desync manifesting on the
 *   real cold-boot stream) that this pass didn't crack. REVERTED to the grass-only bake (cbfff41c). REMAINING for
 *   a robust dirt removal: a CORRECT VARIABLE-PRIM-SIZE DECODER (decode each command's real byte length instead
 *   of assuming 48, so the stream parses without desync) + reliable cold-boot Flik-object identification; or the
 *   GTE render path. Harness: scratchpad p7_*.py.
 *   ** G3-native P2 UPDATE (2026-07-06) -- the GRASS source is RAW-backed in the current build path. **
 *   Older notes said the live source at 0x80163F74 was DAT_base+0x377C; that is wrong for the current
 *   build_g3_native/P1 layout. A DAT+0x378A baked sentinel patch changed the staged DAT but runtime
 *   0x80163F82 stayed 0. accessLog write-watch from cold boot showed FUNC_8001A1DC (LEVEL.RAW decompressor)
 *   writes the live table around frame 3325; the effective source row is in LEVEL.RAW decompressed chunk 66,
 *   local 0x134 (current emitted RAW full-decomp offset 0x1395B6; pristine full-decomp offset 0x1330C6).
 *   tools/build_g3_native.py --suppress-grass now searches that exact row pattern after emit_floor_planes,
 *   sets row+0x0E to -1, recompresses only chunk 66, and verifies decoder round-trip before disc staging.
 *   Baked proof on build/ABL_g3native.cue: runtime read 0x80163F82 = 0xFFFF; gpu.pickObject at the former
 *   top-right 0x663 pixel (450,30) returns background.
 *   ** G3-native P2 UPDATE 2 (2026-07-06) -- the 0x68D sprite backdrop is EXE-backed but A/B-only. **
 *   Wider pick census showed many final contributors were GP0(65) sprites, texpage 0x68D/clut 0x3470, written by
 *   FUNC_8003E928 (the chunk-29 panorama/haze tile builder; see backdrop_tile_builder_8003e928.c). A live
 *   `jr ra; nop` at 0x8003E928 removed those sprites without touching Flik or FUNC_80010000, so
 *   build_g3_native.py --suppress-horizon can stage a size-preserving resident-EXE patch at SCUS_942.88+0x2F128.
 *   Baked A/B proof: runtime 0x8003E928 bytes = 08 00 E0 03 00 00 00 00; pickObject at the former 0x68D points
 *   (310,82) and (300,105) returns background. Later manual boot proved this function is menu-shared and also
 *   changes the level-select backdrop, so normal Blender builds leave it unpatched.
 *   ** P2 closure boundary. ** Remaining 0x660/0x663 quads in that view are written by FUNC_80010000, the target
 *   native GTE floor emitter, so they are P3 visual-authoring/sheet cleanup, not a suppressible P2 background pass.
 *   The small 0x604 dirt residue remains the known FUNC_80014B04 hard path: a fresh deterministic live A/B of entry
 *   `jr ra; nop` on this build only changed the pick-grid 0x204/0x604 samples 2 -> 1, so it is still not a clean
 *   bake candidate. Leave the prior DIRT cautions in force.
 *   ** G3-native P3 UPDATE (2026-07-06) -- remaining native-floor quads are authored, not suppressed. **
 *   P3 is intentionally NOT another render blanking patch. tools/build_g3_native.py --planes now builds the
 *   FUNC_80010000 floor visual with native_terrain_export.flatten_floor(), setting each DAT node-array floor
 *   vertex to the authored file-frame surface. The legacy displace-to-mean path remains available only as
 *   --displace-visual. Geometry proof for build/ABL_g3native_terrain.DAT: 30 native floor payloads / 2775 vertices,
 *   every payload Y[-497,-497], max_abs_error_to_target_after=0. Movie validation stays clean:
 *   RENDER_C=0, FUNC_80010000=7303, no plunge. So the 0x660/0x663 native quads are P3-authored floor, not P2
 *   residue to suppress.
 *   ** G3-native P6 AUDIT (2026-07-06) -- hard residuals are bounded, not newly baked. **
 *   After P5 heightfield validation, tools/report_g3_native_residuals.py verified the safe RAW chunk 66 local
 *   0x134+0x0e sentinel=-1 grass/mound source suppressor plus the then-experimental FUNC_8003E928 horizon A/B stub.
 *   Manual boot later proved the horizon stub is menu-shared, so only the RAW grass source suppressor remains
 *   baseline-safe. Report artifact: build/g3_native_p6_residual_report.json. The remaining hard residuals are
 *   intentionally NOT baked:
 *   chunk-34/35 structural terrain still has prior load-wedging evidence, and texpage-0x604 FUNC_80014B04 dirt
 *   still lacks a Flik-separable cold-boot-safe lever (live jr-ra/nop only changed pick-grid samples 2->1).
 *   Do not turn P6 into a blanket chunk-35 edit or a 0x604 render-list/count patch without new source-level proof.
 *   ** G3-native P20 UPDATE (2026-07-06) -- replacement interaction faults in render/cull, not scheduler. **
 *   P20 traced why the minimal collision replacement interaction P17 seed + [0,73,92] appeared to stop
 *   FUNC_80048138 after the P11 spawn. Static JAL scan corrected the player-update call site to 0x8004EFD8
 *   (0x8004F7D8 is not the caller). Passing controls re-enter the top/gameplay loop and call FUNC_80048138
 *   normally; the failing build enters the BIOS exception path before the next scheduler tick. COP0 reports
 *   CAUSE=0x41c, ExcCode=7, EPC=0x8001EB3C, BadVAddr=0. The EPC instruction is `lw v0,0(s2)` in the
 *   render/cull object traversal path, with the sampled exception-context s2 value outside normal RAM
 *   (0xfffabfa0; GPRs may be BIOS-clobbered, EPC is decisive). The last normal gameplay-loop render region is
 *   around 0x8004F448, where the loop calls FUNC_800224EC with a0=0x8009EC50 after the player-update region.
 *   Therefore the P20 blocker is render/cull list/pointer provenance caused or exposed by the 0,73,92
 *   replacement interaction. It is not a player scheduler gate and not a FUNC_80035280 selector rejection.
 *   Evidence doc: docs/G3_NATIVE_P20_PLAYER_UPDATE_SCHEDULER.md.
 * Survey: only these 2 gouraud passes exist. Residuals (not
 * gouraud terrain, separate work): a faint background horizon band (native env/sprites), revealed native decor
 * behind the terrain (Track B), and Flik's-feet-clip-into-our-floor (pre-existing depth-sort, no Z-buffer;
 * render-OFF = clean native feet; tune DS_MUL to fix, trade-off vs occlusion).
 */

/*
 * P23 collision grid-builder destination diagnosis (2026-07-06). Render/cull key 65 is the
 * stale consumer of 0x801c3614..0x801c3688 after the collision grid/list builder legitimately
 * writes that range. The bad [s0+0x18] word is builder max-Z data, not a render node pointer.
 */

/*
 * P24_RENDER_STALE_NODE_LIFETIME_2026_07_06
 * P24 render stale-node lifetime fix (2026-07-06). The seed+[0,73,92] crash is a stale render/cull key-65 payload-holder slot (`0x801c362c`) after collision-builder workspace reuse. An opt-in `--p24-stale-render-guard` hook skips only invalid non-main-RAM payload pointers at `0x8001eb3c` and counts skips at `0x8007f30c`. Default P11/P17/P18 behavior is unchanged.
 *
 * P47_REPLACEMENT_ENVELOPE_2026_07_07
 * P47 does not change this dispatch path. It preserves P46 and proves the unguarded prefix07 replacement envelope
 * [0,73,87,88,89,90,91,93,99,100,107,108] on the platform-ramp cold boot with marker/goal, RENDER_C=0,
 * FUNC_80010000=500, no plunge, replaced_authored_block=12, and no retained route blocks. Sector 92 remains outside
 * that unguarded envelope because the 0,73,92 interaction is this stale key-65 workspace-lifetime fault. Any sector-92
 * re-entry must be guarded and must report the P24 skip counter explicitly; P47 does not promote the P24 guard,
 * replacement sectors, retile, sink-outside, or broad replacement to defaults.
 *
 * P48 result: the guarded P47 control passes with skip counter 0, but P47+92 stalls at spawn before this key-65 guard
 * runs: FUNC_80010000=0, no goal, P24 skip counter 0, and no player-floor liveness. Sector 92 therefore remains
 * unsupported even in the guarded P48 envelope; the next investigation is upstream of this dispatch hook.
 *
 * P49 result (2026-07-07): the P48 full probe matches the P27 full frontier and fails before this dispatch loop for
 * the same reason: the render driver calls 0x8003efc8, but the helper does not return to 0x80022608. It never reaches
 * 0x8002262c, 0x8001ea6c, or FUNC_80010000. The divergent active record is v1=0x801c561c/span=0xfff94040 in the
 * failing set versus v1=0x801c411c/span=0x0000000f in the nearest pass. P49 does not prove the writer of that record.
 *
 * P50 result (2026-07-07): sector 92 becomes cold-boot traversable only in the guarded swap envelope that omits
 * sector 91: [0,73,87,88,89,90,92,93,99,100,107,108]. The full 91+92 set still stops before FUNC_80010000, while the
 * swap reaches marker/goal with RENDER_C=0, FUNC_80010000=413, no plunge, retained route blocks [], and exactly one
 * P24 skip. Treat this as a guard-dependent envelope result, not sector-92/default or active-record-writer proof.
 */

/*
 * P54 (2026-07-07) — VISIBLE-GROUND CENSUS on authored (Track-B) worlds + the two-renderer
 * doctrine correction. gpu.pickObject census + live A/B function stubs on the bigland disc:
 *
 *   panorama band (cliff/grass/painted berries) = GP0(65) sprites texpage 0x68D CLUT 0x3470
 *     <- FUNC_8003E928 from the chunk-29 image (plus a GP0(60) flat fog sprite from the same
 *     builder region). Suppressed at SOURCE by build_g3_native.py --blank-backdrop (chunk-29
 *     pixels := sky index; palette untouched; menu-safe RAW edit).
 *   original ground mass = FUNC_800172DC drawing the chunk-35 shared mesh buffer
 *     0x8012C1D0..0x8012E784. The old f13 "fully occluded" finding holds ONLY for pristine
 *     geometry: pristine payload floor covers this mass exactly; authored worlds move the
 *     payload floor and EXPOSE it. Suppressed by --suppress-bulk-mesh: the P11 cave
 *     (DAT-marker-gated) one-shot zeroes the buffer at level init — level-local RAM, no
 *     structural chunk-35 edit (sidesteps the 0x8002ADD0-class load wedge), live-proven
 *     stable 240+ frames with Flik/enemies/HUD intact (they use other buffers in gameplay).
 *   authored floor = GP0(3C) quads texpage 0x660 CLUT 0x3FF3 (native FUNC_80010000) — but it
 *     only tiles the ORIGINAL floor footprints; with the bulk mass suppressed, off-footprint
 *     ground reads as void over solid collision. Visual-coverage expansion of the payload
 *     regeneration lane is the remaining fix for full authored-world visuals.
 *   baked fixtures (twig/tree/branches/grass/mushroom/leaf) = GP0(2C/2D) quads, model atlas
 *     0x60A, CLUTs 0x3672/0x3674/0x3676, per-frame packet pool ~0x801E28xx. Survive panorama,
 *     bulk-mesh, and dirt stubs; NOT in the chunk-35 tail (0x8012E784..0x80131000 zero = no
 *     change). Their chunk-34 arena/instance directory is the open lead.
 *   FUNC_80014B04 (0x604 dirt): stub removes pieces of FLIK — re-confirmed Flik-shared,
 *     never usable as a scenery lever.
 */

/*
 * P54b census CORRECTION (2026-07-07): the "tree/ridge" masses attributed above were
 * TWO different systems, neither of them chunk-34/35 mesh clients:
 *   ridge/pebble sweeps  = FUNC_8003E928 tiles of a SECOND panorama image (128x128 at
 *     RAW full+0x39550) — the VRAM strip (832,0) is re-uploaded per zone. Lever:
 *     --blank-far-terrain (pixels := its sky index; grass horizon 128x96 kept).
 *   tree trunk/branches/grass cluster = pass-3 baked fixtures with ROTATION-ONLY cull
 *     (parked anchors ineffective). Lever: clear the pass-3 enable bitmap
 *     0x800902B6..0x800902C7 (P11-cave one-shot; see pass3_backdrop_cull_80014360.c).
 *   wall/cliff bands = the 12 non-floor node-array payloads (0x45F0 run) ->
 *     --park-nonfloor-nodes.
 * Negative results: stubs of all five FUNC_8001DFE4 emitters and the dispatcher itself
 * do not remove these; zeroing the chunk-34 arena (0x80108CDC..0x80135522) breaks FLIK
 * (his model data lives there — never blanket-zero chunk 34).
 * Plus the P54b visual-coverage fix: native_terrain_export.regenerate_floor_tiled
 * (--regen-visual N) tiles the whole play box with the 30 floor payloads (in-place-fit
 * injection; keep DAT growth small — +60KB append wedged the load at the arena limit).
 */

/* ============================================================================
 * P58 ADDENDUM (2026-07-07) — TWO RENDER STATES + THE NEAR-FIELD LAW
 * ----------------------------------------------------------------------------
 * 1) The movie-stall "settle" state (after movie.stopPlayback, and after any
 *    warp-guard teleport, +0x82=0x0101) renders floor payloads far more
 *    generously than normal WALKED gameplay. Two taps of walking switch to the
 *    gameplay following-camera state and near floor rows vanish. NOT corruption:
 *    FUNC_80010000 still runs per payload (drawn set tracks position), SXYs
 *    project onscreen, DAT image byte-stable. The vanishing rows are the PS1
 *    GPU primitive-size reject (>1023px wide) on quads near the camera; the
 *    stall state's vantage just never exposes it. EVERY visual claim must be
 *    verified WHILE WALKING (blue-fraction of the lower screen), never from
 *    the stall state. This confound cost sessions P54b-P57.
 * 2) The near band in pristine gameplay is covered by (a) the static tan
 *    GP0(60) fill bands (their real purpose) and (b) chunk-35 fine instanced
 *    meshes (the pebbled texture, ~50-file-unit chunklets pass the size
 *    reject everywhere). Payload floors alone CANNOT cover the near band at
 *    any density that fits the DAT arena ceiling.
 * 3) DAT+0x380..0x680 (in-RAM DAT header band) holds per-entry words whose
 *    bit 0x100 toggles as Flik crosses zones (e.g. +0x394 0x00280014 ->
 *    0x00280114, +0x574 loses the bit). Restoring or force-setting the band
 *    does NOT revive floors -> derived state, not the render gate.
 * 4) Adaptive native density (P58_ADAPTIVE_N): per payload, the largest grid n
 *    whose styled regen fits the payload's ORIGINAL byte slot reproduces
 *    native quad pitch (~470-650 file) with ~zero DAT growth; with it the
 *    authored floor renders underfoot exactly as well as pristine in the same
 *    camera state (operator's blue-floor spot: 5/6 picks, == pristine).
 * ============================================================================ */
