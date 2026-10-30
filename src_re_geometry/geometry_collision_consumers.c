/* ============================================================================
 * geometry_collision_consumers.c  —  Collision/pathing consumers   [PHASE G5 — ANALYZED 2026-06-14]
 * ----------------------------------------------------------------------------
 * RESULT: NO static collision/pathing consumer of the parser geometry was found.
 *         Static evidence indicates the parser geometry (records 0x01/0x0b/0x0c/0x0d/-2..-7,
 *         the trailing tables, the pass-1 output records, and the payload band) is consumed
 *         ONLY by the render driver path identified in G4. Movement / player-position code
 *         shows no static read of the parser geometry. This is a documented negative result,
 *         not a confirmed "all geometry is render-only" claim (see UNRESOLVED). G6 added dynamic
 *         separation evidence for one render trail field: patching `DAT+0x1526` removed most visible
 *         terrain while tested ground collision remained usable.
 * ----------------------------------------------------------------------------
 * CONFIDENCE  : The negative result (no static parser-geometry collision consumer) is CONFIRMED
 *               for global-visible access paths. Whether collision reaches the geometry via a
 *               register/struct-passed pointer (invisible to a global scan) is UNKNOWN.
 * SOURCE NOTES: r2 disasm + lui-tracking global-ref scan of SCUS_942.88 (G5, read-only);
 *               geometry_render_consumers.c (G4); src_re/contact_walker_800586b0.c (pickup walker);
 *               docs/EXECUTABLE_AND_OVERLAYS.md (fcn.80025084, PAD\PATH*.BIN pathfinding files).
 * KNOWN GLOBALS: G_TRAIL_BLOCK_PTR(0x800824ac), G_PASS3_BASE_PTR(0x80082508),
 *               type table 0x80096da0 (geom slots 0x01/0x0b/0x0c/0x0d/-2..-7), player pos
 *               0x800a6500/04/08, matrix 0x80090fb0.
 * UNRESOLVED  : where world/level collision actually reads its geometry (PATH/PAD files vs a
 *               non-global pointer); whether any parser geometry also has collision use outside
 *               the tested `DAT+0x1526` render trail field.
 *
 * ============================================================================
 * SEARCH METHOD (G5)
 * ------------------
 * 1. lui-tracking scan of the whole text segment for references to:
 *    - the geometry record-type slots in the dynamic type table (0x80096da0 + t*4) for
 *      t = 0x01, 0x0b, 0x0c, 0x0d and the negatives -2..-7 (the parser geometry record types);
 *    - player position globals 0x800a6500 / 04 / 08;
 *    - the oriented-test matrix 0x80090fb0;
 *    - G_DAT_BASE_PTR (0x80082498).
 * 2. Combined with the G4 gp-relative scan of G_TRAIL_BLOCK_PTR / G_PASS3_BASE_PTR.
 * 3. Caller analysis of fcn.80025084 (containment test) and the player-position writer.
 * 4. PATH/PAD string + loader check.
 *
 * ============================================================================
 * KEY NEGATIVE FINDINGS (CONFIRMED)
 * ---------------------------------
 * A. The geometry record-type slots TT[0x01], TT[0x0b], TT[0x0c], TT[0x0d], TT[-2..-7] have
 *    ZERO readers anywhere in the resident text. Only TT[0x3f] (the pickup record) is consumed
 *    via the type table. => no resident function reaches the parser geometry records by type.
 * B. G_TRAIL_BLOCK_PTR / G_PASS3_BASE_PTR are read by exactly one external function, the render
 *    driver fcn.800224ec (G4). No collision/movement function reads them.
 * C. G_DAT_BASE_PTR is read only inside the parser and the loader fcn.8003cf2c. No collision use.
 * D. ~40 functions read player pos 0x800a6500/04/08 (camera/movement/gameplay), but NONE of them
 *    also reads any parser-geometry handle (type table geom slots, trail/pass3, or DATbase).
 *    => statically, no function joins player position to the parser geometry.
 * E. The sole WRITER of player pos is fcn.8005b134; it is a state dispatcher into the Region-A
 *    LEVEL overlay verbs (0x800b3adc/3ae8/3aec/3c54/3c5c) and reads no parser geometry.
 * F. Pathfinding data is external: PAD\PATH*.BIN files exist (strings @ ~0x8007ee94; exec doc).
 *    Pathing LIKELY uses those, not the LEVEL.DAT parser geometry.
 * G. G6 dynamic test: `DAT+0x1526` (`41 00` -> `ff ff`) made terrain/ground render mostly disappear,
 *    but Flik could still stand/move on the invisible/missing terrain in the tested area. This
 *    supports render/collision separation for that trail flag/sentinel field. It does NOT identify
 *    the collision/pathing data source and does NOT prove all parser geometry is collision-free.
 *
 * ============================================================================
 * fcn.80025084 — oriented range/containment test (NOT a parser-geometry consumer)  [CONFIRMED]
 * --------------------------------------------------------------------------------------------
 * Disasm (head) shows it reads, for actor a1 and world point a0/a2:
 *   v0 = a1[0]; obj = ((void**)0x800a6300)[v0]; if (*(int16*)obj == 0) return 0;   // object-table gate
 *   p   = a1[+0x80];   coord = (*(int32*)p) << 5;   delta = coord - a0;            // actor coord <<5 - point
 *   m   = *(int16*)0x80090fbc;   t2 = delta * m;                                    // rotate by matrix 0x80090fb0
 *   extent = (int16)a1[+0x66];                                                      // range test vs extent
 * Inputs: actor struct a1 (0x800a0a64), a world point, object-pointer table 0x800a6300, matrix
 * 0x80090fb0. It reads NONE of the parser geometry (no DATbase, no trail/pass3, no geom type slots).
 * Caller: exactly one, fcn.8004d224 @0x8004d3bc (which also touches no geometry handle).
 * ROLE: oriented containment/range test on ACTOR/OBJECT data; render-vs-collision still UNKNOWN, but
 * it is NOT a consumer of the G1-G3 parser geometry. Keep out of the geometry-collision question.
 *
 * ============================================================================
 * RULED OUT as parser-geometry collision consumers
 * ------------------------------------------------
 *  - fcn.800224ec + fcn.800140a0/80014360/800146e0 : RENDER path (G4); read no player pos.
 *  - fcn.80025084 / fcn.8004d224                    : actor/object containment; no parser geometry.
 *  - fcn.8005b134                                   : player-pos writer; dispatches to overlay verbs.
 *  - fcn.800586b0 (contact walker)                  : PICKUP proximity over array 0x800b0d18 (solved
 *                                                     context); not world geometry.
 *  - all ~40 player-pos readers                     : none read a parser-geometry handle.
 * ============================================================================ */

#include "../src_re/re_types.h"

/* No candidate parser-geometry collision/pathing consumer to declare. The geometry's only
 * identified consumer is the render driver (see geometry_render_consumers.c). */

/*
 * NEXT-STEP STRATEGY (recommendation only; no emulator run performed):
 *  [ ] Dynamic watch on the source-record / output-record bytes during gameplay while walking the
 *      player into level geometry: set a read-watch on a payload-band address (DATbase+payload) or on
 *      an output-record matrix; if it fires only during the render-driver call (fcn.800224ec) and NOT
 *      during movement, that CONFIRMS render-only. If it also fires from a movement/physics function,
 *      that function is the missing collision consumer -> capture its address.
 *  [ ] Watch writes to player pos 0x800a6500/04/08 and step back to the writer's inputs; check whether
 *      any input pointer derives from DATbase (would reveal a non-global geometry read).
 *  [ ] Trace PAD\PATH*.BIN loading/use to confirm pathing is a separate data source from LEVEL.DAT.
 *  [ ] Re-examine fcn.8004d224 (the lone fcn.80025084 caller) for a world-collision role on actor data.
 *
 * G6 RESULT: the `DAT+0x1526` trail flag/sentinel edit produced a CONFIRMED render-stage terrain
 * disappearance/cutoff, while tested ground collision remained usable. Collision/pathing impact
 * remains UNKNOWN beyond that tested area, and no collision-aware parser-geometry consumer is known.
 */

/* ============================================================================
 * G29 ADDENDUM (2026-06-15) — collision/pathing SOURCE discovery plan for a CONFIRMED visual floor
 * --------------------------------------------------------------------------------------------------
 * CONTEXT (G28): Candidate A (DAT 0x188cc, payload 0x801790c4, vertex 0x801790c8, count 83) is now a
 * CONFIRMED DAT-backed VISUAL floor/top-surface render payload — the DAT+0x18992 edit (v16.y +1024)
 * VISIBLY caved the floor, but collision/pathing did NOT follow the deform. So for that tested edit:
 *     visual terrain payload != collision/pathing source.
 * The collision/floor source is therefore UNKNOWN and is NOT assumed to be in Candidate A, LEVEL.DAT,
 * or LEVEL.RAW. This G29 pass is ANALYSIS + a runtime-watch RUNBOOK only — NO patch/build/run.
 *
 * WHY RUNTIME-FIRST: the G5 negative above stands — no static parser-geometry collision consumer exists
 * (geom type slots have zero readers; ~40 player-pos readers touch no geometry handle). So the floor
 * query reaches its data by a NON-GLOBAL pointer or from a NON-PARSER source, invisible to a global
 * text scan. We find it from the player-Y side at runtime.
 *
 * CANDIDATE COLLISION / FLOOR-CONTACT TARGETS (existing evidence; no new fn names invented):
 *   [CONFIRMED addr] G_PLAYER_Y 0x800a6504 (+X 0x800a6500 / +Z 0x800a6508) — the value that MUST change
 *                    on floor contact; writer-of-Y is the floor/movement integrator (writer PC UNKNOWN).
 *   [LIKELY] fcn.8005b134 — G5-named player-pos writer / Region-A overlay dispatcher (verbs
 *            0x800b3adc/3ae8/3aec/3c54/3c5c); LIKELY the movement/floor-snap integrator. CONTRADICTION
 *            to resolve at runtime: EXECUTABLE_AND_OVERLAYS.md L409 lists progress/pos writers
 *            fcn.80047284/80048138/8004a700/800563d4/80056f68/8005b12c (write 0x800a6580 block via base
 *            0x800a6500). Which PC actually writes 0x800a6504 (Y) is UNKNOWN -> the WRITE watch decides.
 *   [CONFIRMED shape / role UNKNOWN] fcn.80025084 oriented containment/range test (actor 0x800a0a64
 *            +0x80 coords<<5 / +0x66 extent, object table 0x800a6300, matrix 0x80090fb0; caller
 *            fcn.8004d224 @0x8004d3bc) — plausible WALL/LEDGE/object collision primitive (NOT parser
 *            geometry, NOT pickups).
 *   [LIKELY external / floor-role UNKNOWN] PAD\PATH*.BIN (<=1.3KB; strings ~0x8007ee94) via universal
 *            loader fcn.80046330(a0=filename,a1=dest). CAUTION: likely AI/enemy pathing, not Flik floor
 *            height — do not assume floor.
 *   [DECOY — EXCLUDE] contact array 0x800b0d18 + walker fcn.800586b0 (player-Y bias -0x1cc0) = PICKUP
 *            proximity, NOT world floor collision. Ignore the -0x1cc0 bias for the floor question.
 *
 * RUNTIME RUNBOOK (<=6 BPs/pass; full detail: geometry_g29_collision_source_plan.md):
 *   Pass 1  WRITE watch 0x800a6504 (+0x6500/+0x6508 context): stand + walk on the floor -> record the
 *           Y-writer PC/RA = the floor/movement integrator (expect fcn.8005b134 or an L409 writer).
 *   Pass 2  EXEC the Pass-1 writer PC: find the memory operand `S` it reads as the target floor height;
 *           arm a READ watch on S; CLASSIFY S = DAT (S-0x801607f8 in [0,0x51418), NOT the A vertex band
 *           ~0x80179188) / LEVEL.RAW-decompressed (S<0x8015fcbc or high heap) / sidecar buffer / generated.
 *   Pass 3  (DECISIVE) READ watch S over the floor on the PRISTINE image vs the G28-deformed patch:
 *           if S and Flik Y are IDENTICAL over deformed vs pristine -> collision source is INDEPENDENT
 *           of Candidate A => S CONFIRMED as the floor/collision source; A holds no collision data.
 *   Pass 4  EXEC 0x80046330 entry: log a0(filename)/a1(dest)/ra/size; find PAD\PATH*.BIN or any load whose
 *           [a1,a1+size) brackets S.
 *   Pass 5  (low priority) EXEC 0x80025084: walk into wall / off ledge -> is it the wall/ledge primitive?
 *
 * FALSE-POSITIVE GUARDRAILS: render path fcn.80010000/0x800108b4/0x80010718 is NOT collision; visual
 * deformation is NOT tangibility; 0x801bdc58 is compressed LEVEL.RAW source (not a payload, != Cand E
 * 0x8018dc58); do NOT assume LEVEL.RAW (retracted heap-floor theory) or LEVEL.DAT collision just because
 * the visual floor is DAT-backed. No collision-source claim without runtime evidence. Collision/pathing
 * UNKNOWN until Pass 1-4 hits. Visual != collision.
 *
 * ============================================================================
 * G29 PASS 1 RESULT (2026-06-15) — player-Y writer = FUNC_3633C @0x8003633c (NOT fcn.8005b134)
 * --------------------------------------------------------------------------------------------------
 * Operator ran Pass 1 on the PRISTINE image: WRITE watch 0x800a6504 (player Y), Candidate-B floor, Flik moving.
 * Writer PCs observed: 0x80036384 / 0x80036cf0 / 0x80036d58. State at 0x80036384: a0=s1=s7=0x800a6500,
 * a1=s5=0x800a652c, a2=0x800a6582; the other two carry ra=0x80036c70, s5=0x800a652c, s6=0x800a6582, s7=0x800a6500.
 *
 * STATIC DISASM (SCUS_942.88, t_addr 0x80010000 + 0x800 header; r2 read-only) resolves all three to ONE function:
 *   FUNC_3633C head 0x8003633c: s7=a0=player struct base (rt 0x800a6500); s5=a1=velocity/delta vec
 *   (rt 0x800a652c = base+0x2c); a2=contact-flag bytes (rt 0x800a6582 = base+0x82). Per-frame MOVEMENT +
 *   COLLISION-RESPONSE integrator on the player struct. Callers (jal scan): 0x800495c8 (RA 0x800495d0,
 *   observed), 0x8004c024, 0x8004e628. DuckStation reports PC = store_addr + 4 (all 3 PCs are store+4).
 *
 *   Four stores to [s7+4]=0x800a6504:
 *     0x80036380 sw v0,4(s7); v0=[s7+4]-0xc80      (obs 0x80036384) = Y PROBE-BIAS DOWN 0xc80; NOT a floor value.
 *     0x80036cec sw v1,4(s7); v1=[sp+0x1c]         (obs 0x80036cf0) = COMMIT of the COLLISION-RESOLVED position
 *                  (X=[sp+0x18],Y=[sp+0x1c],Z=[sp+0x20]) = the floor/contact-corrected Y. THE DECISIVE WRITE.
 *     0x80036d30 sw v0,4(s7); v0=[s7+4]+[s5+4]      (PC 0x80036d34, NOT observed) = free velocity integration.
 *     0x80036d54 sw a0,4(s7); a0=[s7+4]+0xc80       (obs 0x80036d58) = Y PROBE-BIAS UP (restore); NOT a floor value.
 *
 *   ra=0x80036c70 on the resolved/restore hits = return of jal 0x800345cc (0x80036c68+8) -> the ACTIVE collision
 *   helper in the observed walk is 0x800345cc. FUNC_3633C calls: 0x80035f24 (sweep -> v0), 0x800345cc (-> result
 *   code a3), 0x80035280 (alt path). 0x800345cc / 0x80035280 read [gp+0x57c]=collision-candidate COUNT
 *   (gp=0x80081d98 rt -> 0x80082314), iterate a per-frame candidate list, write the resolved position into the
 *   sp+0x10/sp+0x18 scratch buffer. The floor-height SOURCE S is an element of that candidate list -- a per-frame
 *   gp-relative scratch structure reached by a NON-GLOBAL pointer => exactly why finding D above (G5) found no
 *   static collision consumer. The G5 negative is VINDICATED, not contradicted.
 *
 *   fcn.8005b134 CONTRADICTION -- SUPERSEDED/PENDING (do NOT erase finding E above): the store to 0x800a6504 is
 *   in 0x8003633c, NOT 0x8005b134; fcn.8005b134 has ZERO jal callers (overlay/jump-table dispatched), 0x8003633c
 *   has 3 (0x800495c8/0x8004c024/0x8004e628), none = 0x8005b134. "Sole player-pos writer = fcn.8005b134" is now
 *   SUPERSEDED/PENDING: fcn.8005b134 may write pos in another (scripted/spawn/overlay) context; the per-frame
 *   movement+collision Y writer is 0x8003633c. Relationship UNKNOWN until a runtime EXEC pass. (The -0xc80 probe
 *   bias is distinct from the pickup-walker -0x1cc0; fcn.800586b0 stays excluded.)
 *
 * NEXT = G29 Pass 2 (no patch/build/G28-compare yet): EXEC 0x80036cec (read resolved [sp+0x18..0x20] floor pos);
 *   EXEC 0x800345cc (find candidate-list base + floor-height operand S, [gp+0x57c]=0x80082314 count); READ-watch S
 *   and classify its band. Full plan: geometry_g29_collision_source_plan.md. Collision/pathing UNKNOWN; visual != collision.
 *
 * ============================================================================
 * G29 PASS 2 RESULT (2026-06-15) — resolved-Y is a per-axis ACCUMULATE; source = collision-candidate list (UNLOCATED)
 * --------------------------------------------------------------------------------------------------------
 * Operator confirmed at EXEC 0x80036cec: sp=0x801FFE00, v1=0xFFFE2196, working buffer [sp+0x18..0x24] =
 * {0x00005B7B, 0xFFFE2196, 0xFFFFB44B, 0xFFFF0000} ([sp+0x1c]==v1==resolved Y). Then WRITE watch 0x801FFE1C
 * (= sp+0x1c) caught TWO writers (r2-verified; DuckStation PC=store+4):
 *
 *   Hit A  store 0x80035ed8 `sw v0,4(s5)` (reported PC 0x80035edc) INSIDE helper 0x800345cc -- the resolved-Y
 *          COMPUTE. It is a 3-component vector ACCUMULATE: pos[i] (word @s5) += signed_halfword delta[i] (@s3)
 *          for X(s5+0<-s3+0)/Y(s5+4<-s3+2)/Z(s5+8<-s3+4). s5=0x801FFE18 = FUNC_3633C sp+0x18 working buffer
 *          (FUNC_3633C passes s4=sp+0x18 as a1 -> helper s5); s3=0x801FFE10 = FUNC_3633C sp+0x10 delta buffer
 *          (a0 -> helper s3). At the hit [s3+2]=0 -> Y delta 0 -> accumulate added nothing -> 0xFFFE2196 pre-existed
 *          (this is the WRITE SITE, not the value's origin). Owner = 0x800345cc (prologue addiu sp,-0x110).
 *   Hit B  store 0x80036bdc `sw v1,0x1c(sp)` (reported PC 0x80036be0) INSIDE FUNC_3633C -- a COPY/seed: 4-word
 *          [sp+0x18..0x24] <- [s7..s7+0xc], gated by bgtz [gp+0x57c]/blez [gp+0x5cc]. Propagation, NOT the origin.
 *
 *   STRUCTURAL CORRECTION: at Hit B s7=0x801FFEA8 (a STACK position vector), NOT the player global 0x800a6500.
 *   FUNC_3633C sets s7=a0 once at entry, so THIS invocation integrates a stack XYZ vector; its 0x80036cec commit
 *   writes [0x801FFEAC], not player Y. FUNC_3633C is a REUSABLE position+collision integrator over whatever a0
 *   points at (Pass 1 caught the player-base invocation s7=0x800a6500). Do NOT claim 0x801FFEA8 = player; the link
 *   stack-vector -> player global 0x800a6504 is a separate step (UNKNOWN/TODO).
 *
 * SOURCE CHAIN (best model): per-frame collision-candidate list (counts [gp+0x57c]=0x80082314,[gp+0x5cc]=0x80082364)
 *   -> sweep helper 0x80035f24 (called 0x80036c50; a0=sp+0x10 delta-out, a1=sp+0x18, a2=s5) writes per-axis DELTAS
 *   to sp+0x10 -> accumulate helper 0x800345cc (0x80035ed8) adds them into sp+0x18 working buffer -> commit
 *   0x80036cec. The floor-height value the deltas derive from lives in the candidate list; its BACKING REGION
 *   (DAT / LEVEL.RAW-decompressed / generated) is UNKNOWN. Source data structure = PARTIAL.
 *
 * NEXT (Pass 2-next, one BP, no patch/build/G28-compare): EXEC 0x80035f24 -- dump a0(sp+0x10 delta-out)/a1(sp+0x18)/
 *   a2(s5)/a3 + the candidate-list base it iterates (+[gp+0x57c]/[gp+0x5cc]); step its head to the lw/lh that reads
 *   a floor-height candidate S; classify S's band. (0x80035ed8 only consumes pre-computed deltas -> dumping there
 *   won't reveal the source.) Collision/pathing source UNKNOWN; visual != collision.
 *
 * ============================================================================
 * G29 -- candidate-record read/compare evidence (2026-06-15)
 * --------------------------------------------------------------------------------------------------------
 * Operator captured a candidate-record read/compare path inside FUNC_3633C. At pc=0x80036B70 (ra=0x800363CC,
 * s5=0x801FFEB8, s7=0x801FFEA8 -- same stack-vector invocation as the Pass 2 result above), register v1 already
 * equals the 32-bit little-endian word at [t1-0x08]. CONFIRMED in three captures:
 *     t1=0x800F7BB8 v1=0x000011FC [0x800F7BB0]=FC 11 00 00
 *     t1=0x800F7B74 v1=0x0000121A [0x800F7B6C]=1A 12 00 00
 *     t1=0x800F7B30 v1=0x00001300 [0x800F7B28]=00 13 00 00
 * The three t1 are 0x44 apart, but that is the spacing BETWEEN samples, NOT a proven record stride. Candidate
 * records live at 0x800F7xxx = a runtime/heap/BSS region (above exe end ~0x80082800, below DAT 0x801607f8 /
 * RAW 0x80115aac); backing source UNKNOWN (NOT DAT/RAW/decompressed).
 *
 * Capture-point roles: 0x80036B78 = post-read PC previously observed; 0x80036B74 = useful read/compare site;
 * 0x80036B70 = stronger post-load/pre-compare capture point. Exact load PC = TODO, likely near 0x80036B6C unless
 * statically confirmed.
 * Pointer caveat: earlier 0x80036B74 captures had t2=t1-0x30, t6=t1+0x90; newer 0x80036B70 captures had t2=t1-0x30,
 * t6=t2. So t2=t1-0x30 appears STABLE in observed captures; the t6 relationship is state/site-dependent -- do NOT
 * treat as universal.
 *
 * STATIC (r2) grounding (for next-phase confirmation, not a runtime claim): the loop 0x800369a0..0x80036b7c (in
 * FUNC_3633C) walks a chained list of candidate BLOCKS (t2; next-ptr lw t2,-4(t2) @0x80036b74; count lhu [t2]).
 * Per entry t1 = t2 + a3*0xc (sub-record stride 0xc; so t2=t1-0x30 => index a3=4 -> why it "looks stable"); t6=t2
 * @0x800369bc then t6+=0xc0 per outer step (state-dependent). The candidate +4 word loads at 0x80036a38 `lw v1,4(t1)`
 * and feeds a bounding/range-overlap compare (slt v1,t5 @0x80036a40; slt s3,.. @0x80036a54); after addiu t1,t1,0xc
 * @0x80036b40 that v1 equals [t1-0x08] at the 0x80036b70 capture. Matched candidates are copied to an output list at
 * 0x80090868 (stride 0xc, count [gp+0x5cc]=0x80082364). So [t1-0x08] (a candidate +4 field) is LIKELY a candidate
 * scalar in the compare/selection path -- possibly a coordinate bound / range / ranking / contact metric -- semantic
 * UNKNOWN; NOT confirmed floor height. Exact load PC to confirm at runtime (TODO).
 *
 * BOUNDARY: G28 Candidate A stays CONFIRMED visual/render only; collision/pathing did not follow its deform;
 * collision/pathing source remains UNKNOWN. No claim about Candidate A here. Recommended next step: static/decompile
 * inspection around 0x80036B6C..0x80036B78 to confirm the exact load feeding v1/[t1-0x08]. No patch/build run.
 *
 * ============================================================================
 * G29 LIVE RESULT (2026-06-15, DuckStation external debugger + controller input; Flik MOVING) -- COLLISION SOURCE FOUND
 * --------------------------------------------------------------------------------------------------------
 * JSON-RPC debugger (127.0.0.1:2346) + new setControllerState/advanceFrames on SCUS-94288_1.sav. Holding Flik walking
 * makes the PLAYER integrator FUNC_3633C run (a0=0x800a6500) and resolve Y through a collision structure. CONFIRMED
 * end-to-end data path (live-verified):
 *   player XZ 0x800a6500 (MOVING) -> SECTOR TABLE @0x800a7e48 (count [gp+0x508]=223, start [gp+0x6cc]=191; 0x30-byte
 *     records: AABB min @+0x14/+0x1c, extent @+0x24/+0x28, flag @+0x2c, block ptr @+0x10; code 0x80036700/0x80036804)
 *   -> [sector+0x10] collision block (e.g. 0x800C1690) -> 32-byte collision records @~0x800D0xxx, AABB-tested vs the
 *     quantized player query (loop 0x80036820..0x8003690c) -> matches stored as POINTERS into the gp+0x57c list
 *     @0x8009c230 (store 0x800368E8; parallel halfword list @0x80091718) -> resolution helpers (0x800345cc /
 *     accumulate 0x80035ED8) -> resolved [sp+0x18..] -> COMMIT 0x80036CEC writes player Y 0x800a6504.
 * DECISIVE capture (moving player): at 0x80036CEC s7=0x800a6500, [gp+0x57c]=7, list@0x8009c230 =
 *   {0x800D0FA8,0x800D1028,0x800D1048,0x800D10C8,0x800D10E8,0x800D1108,0x800D1128} (all 0x800D0xxx), posY -109521 ->
 *   resolvedY -109693 (dY=-172, dZ=+189). Contact list non-empty EXACTLY during Y resolution.
 *
 * => CONFIRMED floor/collision SOURCE = sector table 0x800a7e48 + per-sector record blocks (0x800C/0x800D heap) via the
 *    gp+0x57c list; reached by a NON-GLOBAL chain ([sector+0x10] heap ptr) -- exactly the pointer the G5 global scan
 *    (finding D above) could not see, now resolved at runtime (G5 negative VINDICATED). SEPARATE from the DAT visual
 *    floor (Candidate A) -> directly EXPLAINS G28 (DAT visual deform did not move collision). The gp+0x5cc / 0x800F7xxx
 *    grid (global 0x8009f9ec) had 0 winners same-frame -> LIKELY a secondary (wall/object) broadphase, not the floor.
 * STILL OPEN (TODO): on-disk backing of 0x800a7e48 / 0x800C-0x800D blocks (LEVEL.RAW-decompressed vs collision sidecar
 *    vs generated) -> WRITE-watch during LEVEL LOAD; exact record-field -> resolved-Y arithmetic in the helpers.
 * Movement injection REQUIRED (idle state: no player call, empty contact list). NO patch/build/mem-write; save state
 * not overwritten. Detail: geometry_g29_collision_source_plan.md sec 2.8.
 *
 * ============================================================================
 * G29 LIVE -- ON-DISK SOURCE CONFIRMED = LEVEL.RAW (decompressed) (2026-06-15)
 * --------------------------------------------------------------------------------------------------------
 * From the PRE-LOAD save state SCUS-94288_2.sav (post-cutscene black; [0x800a7e48]=0, [gp+0x508]=0 at load -> before
 * the build), WRITE-watches pinned the on-disk source. CONFIRMED full disk->player-Y chain:
 *   LEVEL.RAW (compressed) -> loaded to 0x80115aac by fcn.8003a318 (G22) -> DECOMPRESSED per-chunk by fcn.8001a1dc
 *   into 0x800F7xxx [WRITE hit pc=0x8001A60C in the decompressor, ra=0x8003A4EC in fcn.8003a318; compressed src
 *   a0=0x8018B598/s5=0x8015ED7B in the LEVEL.RAW buffer [0x80115aac,0x801cc690)] -> built+scaled(<<5) into the SECTOR
 *   TABLE 0x800a7e48 by 0x80030F60 (copies from src rec t1=0x800F7BF8; caller 0x800314CC) -> runtime: player XZ ->
 *   sector AABB -> [sector+0x10] -> 0x800D0xxx records -> gp+0x57c list 0x8009c230 -> helpers 0x800345cc/0x80035ED8
 *   -> commit 0x80036CEC writes player Y 0x800a6504.
 * => collision/floor SOURCE FILE = LEVEL.RAW (decompressed). This is the PAYOFF of the G22-G25 LEVEL.RAW pipeline:
 *    LEVEL.RAW carries COLLISION/floor; LEVEL.DAT carries the VISUAL floor (Candidate A) -- two different files ->
 *    DEFINITIVELY EXPLAINS G28 (DAT visual deform could not move collision). EDIT NOTE (TODO): LEVEL.RAW is compressed
 *    (codec fcn.8001a1dc) -> a controlled collision edit needs decompress->edit->recompress / chunk-locate. STILL OPEN:
 *    exact decompressed record format (floor-height vs AABB vs normal) + record->resolved-Y math. No edit attempted.
 *    Detail: geometry_g29_collision_source_plan.md sec 2.9.
 * ============================================================================ */
