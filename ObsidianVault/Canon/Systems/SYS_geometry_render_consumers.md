---
kind: system
id: SYS_geometry_render_consumers
created: 2026-07-08
updated: 2026-07-08
status: static_seen
confidence: medium
source_state: original_game_reference_or_mod_reference
src_paths:
  - src_re_geometry/geometry_render_consumers.c
address: 0x000010b1
patch_policy: safe_to_read
---

# SYS_geometry_render_consumers - geometry render consumers

## Purpose

This page closes the migration source-coverage gap for `src_re_geometry/geometry_render_consumers.c`. It records the symbol `geometry_render_consumers` and links the C reference into the structured vault.

- Address if known: `0x000010b1`
- Coverage comments: original address header: fcn.800224ec (scene/render driver, size 900) and the GTE transform helpers


## C source excerpt

Source: `src_re_geometry/geometry_render_consumers.c`

```c
/* ============================================================================
 * geometry_render_consumers.c  —  Render-facing consumers        [PHASE G4 — ANALYZED 2026-06-13]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.800224ec (scene/render driver, size 900) and the GTE transform helpers
 *                    fcn.800140a0 / fcn.80014360 / fcn.800146e0 it dispatches the geometry to.
 * CONFIDENCE       : fcn.800224ec as a render/scene driver that READS the parser geometry pointers
 *                    is CONFIRMED (static refs + render context). G5.5 execute fallback CONFIRMED
 *                    fcn.800140a0 / fcn.80014360 / fcn.800146e0 execute at runtime with parser
 *                    table pointers. G5.5 Part C CONFIRMED reads of DAT-backed pass-1 trail
 *                    flag/sentinel fields (`DAT+0x1512`, runtime `0x80161d0a`; `DAT+0x1526`,
 *                    runtime `0x80161d1e`) in fcn.800140a0. G6 CONFIRMED that changing
 *                    `DAT+0x1526` from `0x0041` to `0xffff` causes major terrain/ground render
 *                    disappearance/cutoff without crash. Exact trail-field semantics and downstream
 *                    GPU primitive emission stage remain UNKNOWN. G7 reinspection CONFIRMED the
 *                    body-field reads are gated by a runtime bitmask table at `0x800901c8+`;
 *                    entry24 +0x00 (`DAT+0x16e4`, runtime `0x80161edc`) is CONFIRMED read by
 *                    `0x8001419c: lw s3,-0x14(a0)` near a specific edge-of-level area. Path A
 *                    CONFIRMED the full entry24 body row is read. G8 Candidates A/A2/C were valid
 *                    builds and CPU-read-confirmed, but all produced no obvious visual change in
 *                    the tested edge-of-level area. G9 first static trace shows entry24
 *                    +0x00/+0x04/+0x08 feed a view-relative vector into SQR/MVMVA culling/range
 *                    tests, with +0x0c as path/extent term; output writes store row pointers to
 *                    lists, not direct coordinates. G9 runtime stepping CONFIRMED entry24 passes
 *                    the first reject at 0x80014280 but rejects at 0x800142b0 before late list-write
 *                    output in the tested state. Candidate late-write row 0x80161f40 maps to
 *                    pass-1 entry29, not entry24.
 *                    C body = ANNOTATION ONLY.
 * SOURCE NOTES     : r2 disasm of SCUS_942.88 (G4, read-only); gp-relative ref scan of parser
 *                    globals; geometry_runtime_buffers.c (G3); dat_geometry_records.c (G2);
 *                    docs/EXECUTABLE_AND_OVERLAYS.md (fcn.8003f938 render loop, camera 0x1f800374).
 * KNOWN CALLERS    : fcn.800224ec is called from 0x8004f428 / 0x8004f448 / 0x8004f718 (scene/gameplay
 *                    state path near fcn.8004ecd4) -> per-scene/per-frame driver.
 * KNOWN CALLEES    : (of fcn.800224ec, geometry-relevant) fcn.80017b98 (GTE matrix setup) x2;
 *                    fcn.800140a0, fcn.80014360, fcn.800146e0 (GTE transform helpers);
 *                    fcn.8003f938 (CONFIRMED object render/projection loop, exec doc);
 *                    plus 0x80014xxx / 0x8003dxxx draw/flush helpers (not classified here).
 * KNOWN GLOBALS    : G_TRAIL_BLOCK_PTR(0x800824ac) read @0x800225f4; G_PASS3_BASE_PTR(0x80082508)
 *                    read @0x80022858; view matrix scratchpad 0x1f8003b4; view vector 0x1f800384;
 *                    camera/view base 0x1f800374; geometry loop count [0x80082440] (gp+0x6a8).
 * UNRESOLVED       : G10 (2026-06-14) ANSWERED the emission question: survivor lists are consumed by
 *                    fcn.8001ea6c / fcn.800206e8 (per-survivor primitive builders that bridge row+0x10
 *                    -> output record -> +0x18 -> source record, transform source vec[3] by the camera
 *                    matrix, dispatch by row-kind, and pack primitives into GPU/OT buffer [0x8008240c]);
 *                    see geometry_g10_payload_render_chain.md. G10 §7 (2026-06-14) further CONFIRMED
 *                    (runtime READ 0x80167b80 + EXEC 0x8001eb34) that kind-dispatch routes entry29-region
 *                    survivors to builder case 0x8001ec44, and statically decoded that case: it reads
 *                    source vec[3]/angle[3]/scale[3]/attr/payload-ptr and tail-calls fcn.80010000
 *                    (payload-vertex projector/emitter, payload = {u32 count; vertex[]}).
 *                    STILL OPEN: fcn.80010000 + 0x80060284 primitive type / payload vertex stride /
 *                    GPU-OT write target; whether READ vs dispatch snapshots are the same iteration
 *                    (s2 differs); LIST_B's consumer; pass-2 readers fcn.80029030/fcn.800292dc.
 *
 * ============================================================================
 * SEARCH METHOD (G4)
 * ------------------
 * Scanned all gp-relative loads/stores in the text segment for the five parser-stored globals
 * (G_DAT_BASE_PTR, G_TRAIL_BLOCK_PTR, G_PASS2_BASE_PTR, G_PASS3_BASE_PTR, G_DAT_ENTRY_COUNTER).
 * 23 refs total; 17 inside the parser fcn.8001cdc0; the 6 EXTERNAL refs are the consumers:
 *   - G_TRAIL_BLOCK_PTR read @0x800225f4  -> fcn.800224ec
 *   - G_PASS3_BASE_PTR  read @0x80022858  -> fcn.800224ec   (same function)
 *   - G_PASS2_BASE_PTR  read x4 @0x80029034/94, 0x800292e0/0x80029508 -> fcn.80029030 / fcn.800292dc
 * (G_DAT_BASE_PTR is read only inside the parser; geometry consumers use the trail/pass3 pointers,
 *  which already hold DATbase+offset, not DATbase directly.)
 *
 * ============================================================================
 * CONSUMER 1 — fcn.800224ec  (CONFIRMED: scene/render driver reading parser geometry)
 * ----------------------------------------------------------------------------------
 * Per-scene driver. Geometry-relevant flow (CONFIRMED from disasm):
 *
 *   ... jal fcn.8003f938                 ; CONFIRMED object render/projection loop (sprite pool)
 *   0x800225f4  lw s2, 0x714(gp)         ; s2 = G_TRAIL_BLOCK_PTR  (= DATbase + 0x1504)
 *   0x80022614  jal fcn.80017b98         ; build GTE rotation matrix into 0x1f8003b4 (scratchpad)
 *   0x8002262c  jal fcn.800140a0         ; a0=s2(trail), a1=0x1f8003b4(matrix), a2=0x1f800384(vec)
 *   0x80022634  move s0, v0 ; sra s4,s0,0x10 ; andi s0,0xffff   ; split return into two halfwords
 *   ...
 *   0x80022858  lw s2, 0x770(gp)         ; s2 = G_PASS3_BASE_PTR  (= DATbase + 0x3aec)
 *   0x80022870  jal fcn.80017b98         ; matrix setup
 *   0x80022880  jal fcn.80014360         ; a0=s2(pass3), a1=s0, a2=s1+0x10
 *
 * RENDER EVIDENCE (CONFIRMED): calls the confirmed render loop fcn.8003f938; uses GTE matrix setup
 * fcn.80017b98 (the same one the parser used to fill the output-record matrices); stages a view
 * matrix/vector in PS1 scratchpad 0x1f8003b4/0x1f800384 (camera base 0x1f800374, exec doc); dispatches
 * the geometry to GTE-heavy helpers; runs once per scene from the gameplay/scene state path.
 *
 * LINKAGE TO THE PASS-1 OUTPUT RECORDS (LIKELY): the parser repoints each pass-1 trailing-table entry
 * `[s3+2] = out` (output record). So walking the trailing table via G_TRAIL_BLOCK_PTR reaches the
 * 0x20-byte ParserOutputRecord20 matrices. fcn.800140a0 takes the trail pointer (a0) and a view
 * matrix/vector, so it is the path by which the output matrices are consumed.
 *
 * CONSUMER 2 — fcn.800140a0 / fcn.80014360 / fcn.800146e0  (runtime execution + selected
 *                                                           trail flag read/effect CONFIRMED)
 * ----------------------------------------------------------------------------------------------
 * Each is GTE-heavy (cop2): fcn.800140a0 = {MVMVA x2, SQR x3}, fcn.80014360 = {MVMVA x2, SQR x3},
 * fcn.800146e0 = {MVMVA x5}. fcn.800140a0 head: loads a 3x3 matrix from a1 and a vector from a2 into
 * the GTE (mtc2/ctc2), reads a loop count from [0x80082440], and iterates a table referenced by a0
 * (= the parser trail/pass3 pointer). MVMVA = matrix x vector transform; SQR = squared length/distance.
 * EVIDENCE: matrix/vector GTE transforms of the parser geometry under a camera matrix, invoked by the
 * render driver. G5.5 fallback execution breaks hit:
 *   - 0x800140a0 standing and after movement/stopped with a0=0x80161cfc (= G_TRAIL_BLOCK_PTR)
 *   - 0x80014360 after movement/stopped with a0=0x801642e4 (= G_PASS3_BASE_PTR)
 *   - 0x800146e0 after movement/stopped with s2=0x801642e4 (= G_PASS3_BASE_PTR)
 * This CONFIRMS runtime execution of the helper path. G5.5 Part C then CONFIRMED read watches on
 * `0x80161d0a` (LEVEL01 DAT+0x1512 pass-1 trail entry0 flag/sentinel) and `0x80161d1e`
 * (LEVEL01 DAT+0x1526 pass-1 trail entry1 flag/sentinel) with DuckStation PC `0x80014174`,
 * consistent with the `lh t3,0x0e(a0)` read site at `0x80014170`. UNKNOWN: read watches on one
 * chosen output record (`0x801b3cb0`, `0x801b3cc8`), source scale (`0x8016560a`), and tested
 * entry0 body fields (`0x80161d08`, `0x80161d00`, `0x80161d04`) had no hits, and the trail-field
 * semantics are not yet named. G6 then patched `DAT+0x1526` (`41 00` -> `ff ff`) and produced major
 * terrain/ground render disappearance/cutoff while sky/backdrop, actors, objects, enemy/props still
 * loaded and the game did not crash. This CONFIRMS the fcn.800140a0 trail flag path controls
 * render-stage terrain visibility/scanning. No RTPS/RTPT/NCLIP perspective-projection or
 * GPU-primitive/ordering-table write was observed in the sampled ranges, so this helper may still be
 * a transform/visibility pre-stage feeding a later projection. Do not call it a mesh/triangle
 * rasterizer.
 *
 * G7 BODY-FIELD GATING MODEL (CONFIRMED from disassembly + entry24 runtime read):
 *  - `entry+0x0e` is read for every scanned row before gating (`0x80014170: lh t3,0x0e(a0)`).
 *  - body reads happen only if `t9 = s1 & s4` is nonzero at `0x80014194`.
 *  - `s1` is loaded from a runtime bitmask table starting at `0x800901c8`; `s4` starts at `0x80`
 *    and shifts down for each row, reloading the next byte every 8 entries.
 *  - body-read sites after the `t9` gate:
 *      `0x8001419c` entry+0x00 word
 *      `0x800141a0` entry+0x08 word
 *      `0x800141a4` entry+0x0c halfword
 *      `0x800141b4` / `0x80014258` entry+0x04 word
 *  - This explains why entry0/entry1 flag watches hit while entry0 body watches did not: flags are
 *    scanned unconditionally, but body reads are skipped when the current bit is clear.
 *  - Runtime watch round on the pristine image:
 *      0x80161e78 = entry19 +0x00 (DAT+0x1680), expected PC 0x8001419c: no hit
 *      0x80161e84 = entry19 +0x0c (DAT+0x168c), expected PC 0x800141a4: no hit
 *      0x80161edc = entry24 +0x00 (DAT+0x16e4), expected PC 0x8001419c: no hit during general
 *        standing/walking/jumping/camera movement away from the area; later hit once when
 *        Flik/camera was near a specific edge-of-level area. DuckStation
 *        showed PC 0x800141a0, consistent with post-read stop after 0x8001419c; a0=0x80161ef0,
 *        read address a0-0x14=0x80161edc, loaded s3 reported as 0xfffd126d.
 *    Entry24 +0x00 is eligible for a future render-body diagnostic proposal. Entry19 remains
 *    zero-hit / not eligible yet. Collision/pathing impact remains UNKNOWN.
 *  - PATH A (RUN 2026-06-14, COMPLETE): the whole entry24 body row is CONFIRMED read by
 *    fcn.800140a0, all at the predicted PCs with a0=0x80161ef0, in the same edge-of-level state
 *    (+0x00 control re-fired, hit count 2). Not F-collection gated.
 *      0x80161edc = entry24 +0x00 (DAT+0x16e4) word, PC shown 0x800141a0, read site 0x8001419c  CONFIRMED
 *      0x80161ee4 = entry24 +0x08 (DAT+0x16ec) word, PC shown 0x800141a4, read site 0x800141a0  CONFIRMED
 *      0x80161ee8 = entry24 +0x0c (DAT+0x16f0) half, PC shown 0x800141a8, read site 0x800141a4  CONFIRMED
 *      0x80161ee0 = entry24 +0x04 (DAT+0x16e8) word, PC shown 0x8001425c, read site 0x80014258  CONFIRMED
 *    +0x04 hit at 0x80014258 confirms the non-negative-+0x0c branch (pristine +0x0c=734>=0).
 *    entry24 is a CONFIRMED non-sentinel DAT-backed render body row; LIKELY location/view gated;
 *    field semantics UNKNOWN; collision impact UNKNOWN. NOTE: at the +0x00 hit DuckStation reported
 *    s3=0xfffd126d while the static DAT word is 0xffffd800 (-10240) -> UNKNOWN whether the row is
 *    runtime-rewritten; this gates any static edit (G8). G8 proposal (entry24 +0x08 small numeric
 *    perturbation, with a live-value verification gate) is recorded in geometry_g55_dynamic_watch.md
 *    §11. Do not patch yet.
 *
 * RULED OUT / NOT THIS PATH:
 *  - G_DAT_BASE_PTR has no external geometry reader (only the parser); geometry consumers use trail/pass3.
 *  - G_DAT_ENTRY_COUNTER has no external reader at all -> the parser return count is consumed only by
 *    the caller's cursor math (fcn.8003cf2c), not by a render loop; fcn.800140a0 uses its own count
 *    [0x80082440], NOT G_DAT_ENTRY_COUNTER.
 *  - fcn.80029030 / fcn.800292dc read G_PASS2_BASE_PTR, but pass 2 is EMPTY in LEVEL01 ([p2]=-1) ->
 *    not active LEVEL01 geometry consumers; role UNKNOWN, deferred (not render-classified).
 * ============================================================================ */

#include "../src_re/re_types.h"

/* CANDIDATE consumer descriptors (local to G4; NOT promoted to re_types.h). */

/* fcn.800224ec — scene/render driver. Reads G_TRAIL_BLOCK_PTR and G_PASS3_BASE_PTR, dispatches the
 * geometry to the GTE helpers below. CONFIRMED render driver; exact per-record field reads UNKNOWN. */

/* fcn.800140a0(table=a0, view_matrix=a1, view_vec=a2) -> packed (hi:count? , lo) :
 *   loads matrix+vec into GTE, loops `[0x80082440]` entries over `table`, MVMVA/SQR transform.
 *   LIKELY render-stage transform of the pass-1 output records reached via the trailing table. */
/* fcn.80014360(table=a0, arg=a1, out=a2) : same shape; consumes the pass-3 table. LIKELY transform. */
/* fcn.800146e0(...) : {MVMVA x5}; called later in the driver; LIKELY transform. */

/*
 * G4 OPEN ITEMS / handoff:
 *  [x] G7/G8 read coverage: entry24 body row CONFIRMED read (Path A, §10). G8 render-only diagnostic
 *      PROPOSAL + PREP recorded in geometry_g55_dynamic_watch.md §11 (candidate entry24 +0x08, small
 *      numeric perturbation DAT 0x16ec 9f fa ff ff -> 9f fb ff ff; +0x00 avoided as edit target due to
 *      static-vs-runtime value mismatch; live-value verification is a BLOCKING gate). Gated patch-prep
 *      script tools/patch_g8_entry24_plus08_test.py. G8 BUILT 2026-06-14: live-value gate PASSED for
 *      +0x08 (live 0x80161ee4 == static 0xfffffa9f at PC 0x800141a4), Candidate A patched
 *      (DAT 0x16ec 9f fa ff ff -> 9f fb ff ff, patched sha1 67dbb832...) and test image
 *      ABL_G8_ENTRY24_PLUS08_TEST.cue built with embedded-byte verification (LBA 2906, 0x16ec reads
 *      9f fb ff ff); staged workspace restored to pristine. Emulator result (2026-06-14): EXECUTED /
 *      VALID BUILD / NO OBVIOUS VISUAL CHANGE (boots, LEVEL01 loads, no crash; edge-of-level area
 *      looks the same by eye) -> +256 likely too small/masked/not directly positional; +0x08 may
 *      still be render-body data, semantics UNKNOWN. Optional CPU confirmation: CONFIRMED data read in
 *      G8 image (READ 0x80161ee4 fired at PC 0x800141a4, read site 0x800141a0, a0=0x80161ef0, hit
 *      count 1); raw s5=0xfffffb9f not separately captured, so patched-bytes proof is the embedded DAT
 *      verification (0x16ec=9f fb ff ff). Candidate A2 BUILT 2026-06-14 (larger same-field nudge
 *      DAT 0x16ec 9f fa ff ff -> 9f fe ff ff, -353, +1024; patched sha1 8714b578...; image
 *      ABL_G8_ENTRY24_PLUS08_A2_TEST.cue, embedded 0x16ec verified 9f fe ff ff at LBA 2906; workspace
 *      restored to pristine). A2 emulator result 2026-06-14: EXECUTED / VALID BUILD / CPU READ
 *      CONFIRMED / NO OBVIOUS VISUAL CHANGE. READ 0x80161ee4 hit (count 1, PC 0x800141a4, a0=0x80161ef0);
 *      CPU memory view CONFIRMS live RAM 0x80161ee4=FFFFFE9F (9f fe ff ff) matching the A2 patch
 *      (cross-checked +0x00=FFFFD800, +0x04=FFFFF5B3). +1024 is CPU-read- and RAM-confirmed yet
 *      visually imperceptible -> +0x08 may be too subtle/masked/not directly positional; render-body
 *      relevance not disproven; semantics UNKNOWN. Save state captured (not committed). Candidate C
 *      +0x04 (DAT 0x16e8 b3 f5 ff ff -> b3 f9 ff ff, +1024) result: EXECUTED / VALID BUILD / CPU
 *      READ CONFIRMED / NO OBVIOUS VISUAL CHANGE. READ 0x80161ee0 hit once at PC 0x8001425c (actual
 *      read site 0x80014258). A/A2/C together show small same-sign entry24 body perturbations are
 *      valid and read but visually imperceptible; continued blind/small entry24 perturbations are
 *      low-yield. DAT/BIN/CUE/save-state artifacts gitignored/not committed. Detail in
 *      geometry_g55_dynamic_watch.md §12-15.
 *  [x] G9 first static trace: entry24 +0x00/+0x04/+0x08 are paired as a view-relative vector
 *      (+0x00-t5, +0x04-t6, +0x08-t7). +0x0c selects the non-negative path and acts as an
 *      extent/range term. The vector feeds SQR at 0x8001425c (opcode 0x4aa00428) and MVMVA at
 *      0x80014298 (opcode 0x4a49e012), then several reject branches before possible row-pointer
 *      writes at 0x8001430c (list A, base 0x80096ea8) or 0x80014320 (list B, base 0x8009e338).
 *      This is LIKELY culling/bounds/range data rather than a direct mesh-position row. Runtime
 *      stepping result: READ 0x80161ee0 (+0x04) hit with PC shown 0x8001425c, actual read site
 *      0x80014258, a0=0x80161ef0. At 0x80014280, s3=0xffff262b, so the first bgez reject was not
 *      taken. At 0x800142b0, t0=0x000010b1 and the operator-observed bgtz branch back to 0x80014170
 *      was taken. Therefore
 *      entry24 participates in GTE/math reject testing but does not reach late list-write output in
 *      this tested state. This explains G8 A/A2/C no-obvious-visual-change results without
 *      disproving entry24 relevance in every state. A noisy late-write observation with
 *      t0=0x80161f40 was another row, not entry24; it maps cleanly to pass-1 entry29, DAT row
 *      0x1748 (+0x04=0x174c, +0x08=0x1750, +0x0c=0x1754). G9b should find/map a row that reaches
```

Note: source excerpt truncated; 83 additional lines remain in `src_re_geometry/geometry_render_consumers.c`.
