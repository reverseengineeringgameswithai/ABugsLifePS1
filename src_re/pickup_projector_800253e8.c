/* RCA a4 (2026-07-09): SUPERSEDED for build purposes — 0x800253e8 is byte-matched in the
   shipping build as asm/hand_written/800253e8_pickup_projector.s (config/segments.yml `attempted`;
   validate_build.py SHA-1 PASS). This src_re file is documentation-grade pseudocode,
   retained for its analysis/comments; it is NOT the build unit. */
/* ============================================================================
 * pickup_projector_800253e8.c  — type-0x3f object visibility + screen projection  [DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.800253e8  (prologue `addiu sp,sp,-184` @0x800253e8; prev fn ends
 *                    `jr ra` @0x800253e0). The per-frame pass that PROJECTS every live
 *                    type-0x3f record to screen and marks which are on-screen.
 * CONFIDENCE       : CONFIRMED — record iteration (G_TYPE3F_PTR), the consumed-sentinel skip,
 *                    the camera-relative 3x3 matrix transform reading entry.{X,Y,Z}, and the
 *                    on-screen flag write to entry+0x0d. The perspective-divide + actual draw
 *                    in the tail (0x8002566c..0x80025f20) are SUMMARISED (LIKELY), not fully
 *                    expanded here.
 * WHY IT MATTERS   : This is the render side proven this session — the gem (and every pickup)
 *                    is drawn DIRECTLY from its type-0x3f record. Editing the record's X/Z in
 *                    RAM (e.g. gem entry 67 X @0x80160c30) moves the on-screen object live and
 *                    the edit persists; Y is overwritten every frame by the bob in
 *                    source3f_dispatch (see that file). See INV note + COORDINATE_MODDING.md.
 * KNOWN GLOBALS    : G_TYPE3F_PTR (0x80096e9c) record ptr (same array source3f_dispatch walks).
 *                    Y_SENTINEL_CONSUMED (0x80000000) = consumed entry (skip).
 * VIEW STRUCT (s1) : a camera/view block — +0x10/+0x14/+0x18 = camera X/Y/Z (world);
 *                    +0x20/+0x22/+0x24 = row 0 and +0x26/+0x28/+0x2a = row 1 of a packed 3x3
 *                    rotation matrix (s16, 4.12 fixed point). (s1 set up in the prologue; its
 *                    origin — scratchpad 0x1f800374 vs caller arg — left unnamed, UNVERIFIED.)
 * COUPLING         : writes the per-entry on-screen flag at entry+0x0d (=1 visible, 0 cleared).
 *                    source3f_dispatch_80053814.c gates pickup eligibility on this very byte
 *                    (`status (+0x0d) must == 1`) — so the projector's visibility decision
 *                    feeds the pickup/contact pass.
 * MOD HOOK         : `tools/training_word_pickups.py` patches the descriptor load at 0x800258a4.
 *                    In Training (scene 0x11; user-facing LEVEL00, retail files LEVEL07), only
 *                    type-0x3f entries 50-53 and appended entries 62-65 use a visual gate at
 *                    0x80081430 and a helper at 0x800813ac with descriptor/row data at
 *                    0x80081580. The helper reuses a native-like 24x24 pickup descriptor and
 *                    swaps UV bytes to draw T/R/A/I/N/I/N/G from baked 8-frame spin strips.
 *                    The strips must be staged into the live pickup-page chunks:
 *                    LEVEL07/LEVEL.RAW chunk 11 and LEVEL07/LEVEL1.RAW chunk 12. Chunks
 *                    12/13 are adjacent art and do not feed the VRAM page at x=640,y=0.
 *                    It deliberately avoids LEVEL07/LEVEL1.BIN scratch/state such as timer
 *                    0x800b4a50. An earlier resident gate at 0x8007fbc8 was overwritten during
 *                    Training scene load and caused a jump into data. A later helper at
 *                    0x8007f130 clobbered live retail state at 0x8007f16c; additionally, after
 *                    compacting the helper, descriptor/table offsets must be +0x24/+0x30, not
 *                    the stale +0x2c/+0x38, or the letters render as banded garbage. A later
 *                    static custom-UV version sampled flower/background texels because native
 *                    F/L/I/K slots are fed by repeated 6x24 VRAM uploads. Other scenes and
 *                    other entries replay the original descriptor-table load.
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))

#define Y_SENTINEL_CONSUMED  0x80000000

/* The view/camera struct (s1). Only the fields the transform touches are named. */
typedef struct {
    uint8_t  _pad10[0x10];
    int32_t  camX, camY, camZ;     /* +0x10/+0x14/+0x18 world camera position */
    uint8_t  _pad1c[0x04];
    int16_t  m[12];                /* +0x20.. packed 3x3 rotation rows (s16, 4.12) */
} ViewStruct;

/*
 * fcn.800253e8 — for each live type-0x3f record, transform its world {X,Y,Z} into the camera
 * frame, distance-cull, and (if visible) set its on-screen flag + project/draw it. Runs once
 * per frame, before source3f_dispatch's contact pass.
 */
void pickup_projector(ViewStruct *s1 /* a-reg set in prologue */)
{
    int32_t s7 = /* max render distance², computed in prologue from a setting */ 0;

    uint8_t *rec = (uint8_t *)(uintptr_t)LW(G_TYPE3F_PTR);   /* 0x80096e9c */
    if (rec == 0) return;                                    /* @0x80025510 */
    int32_t count = LHU(rec);                                /* @0x80025524 */
    if (count <= 0) return;                                  /* @0x8002552c */

    uint8_t *s3 = rec + 4;    /* &entry[0].X  (entry base +0)  @0x80025514 */
    uint8_t *s2 = rec + 12;   /* &entry[0].Z  (entry base +8)  @0x80025540  -> Y is [s2-4] */
    int32_t  s5 = 0;          /* loop index */

    do {
        SB(s2 + 5, 0);        /* clear on-screen flag entry+0x0d  @0x80025544 */

        /* ---- coarse XZ distance reject vs s7 (squared, axes >>4 then >>2) @0x80025548.. ----
         * dxz² ≈ ((X-camX)>>4)² + ((Z-camZ)>>2)²  - 100 ; if >= s7 -> skip (0x80025efc). */
        int32_t dX = LW(s3)     - s1->camX;            /* @0x80025548/4c (X - camX) */
        int32_t dZ = LW(s2)     - s1->camZ;            /* @0x8002556c    (Z - camZ) */
        int32_t aX = dX >= 0 ? dX : dX;                /* (rounding bias +15 before >>4) */
        int32_t coarse = ((aX + 15) >> 4) * ((aX + 15) >> 4)
                       + ((dZ + 15) >> 4) * ((dZ + 15) >> 4) - 100;   /* @0x80025560..0x8002559c */
        if (!(coarse < s7)) goto skip;                 /* @0x800255a4 too far */

        if ((uint32_t)LW(s2 - 4) == Y_SENTINEL_CONSUMED) goto skip;   /* entry.Y consumed @0x800255b4 */

        SB(s2 + 5, 1);        /* mark on-screen  @0x800255bc (drives source3f_dispatch eligibility) */

        /* ---- camera-relative projection: screen.x/y = (Δworld · matrixRow) >> 12 ----
         * Δ = entry.{X,Y,Z} - camera.{X,Y,Z};  rows are s16 4.12 fixed point. */
        int32_t sx = ((LW(s3)   - s1->camX) * s1->m[0]      /* +0x20 @0x800255c0.. */
                    + (LW(s2-4) - s1->camY) * s1->m[1]      /* +0x22 */
                    + (LW(s2)   - s1->camZ) * s1->m[2]) >> 12;  /* +0x24  -> [sp+0x28] @0x80025620 */
        int32_t sy = ((LW(s3)   - s1->camX) * s1->m[3]      /* +0x26 @0x80025624.. */
                    + (LW(s2-4) - s1->camY) * s1->m[4]      /* +0x28 */
                    + (LW(s2)   - s1->camZ) * s1->m[5]) >> 12;  /* +0x2a */

        /* ---- tail 0x8002566c..0x80025f20 (SUMMARY / LIKELY): depth (row 2) + perspective
         * divide, screen-bounds test against s4/s6 (0x00ffffff / 0xff000000 clip masks set
         * @0x80025534/3c), then emit the sprite/quad. Not fully expanded in this pass. ---- */
        (void)sx; (void)sy;

    skip:
        s2 += 0x10; s3 += 0x10; s5++;
    } while (s5 < count);
}

/* ----------------------------------------------------------------------------
 * FINDINGS (this session):
 *  - CONFIRMED: pickups (incl. the green gem, kind 0x30) are rendered DIRECTLY from the
 *    type-0x3f record array — no separate constructed render entity. Hence a live RAM edit of
 *    the record's X/Z (which have no per-frame writer) moves the object and persists across
 *    save/reload; Y is reasserted each frame by the bob (source3f_dispatch_80053814.c).
 *  - CONFIRMED: the on-screen flag the projector writes (entry+0x0d) is exactly the eligibility
 *    byte source3f_dispatch tests — projector → dispatch coupling.
 *  - LIKELY/TODO: pin the ViewStruct origin (s1), and expand the perspective-divide + draw tail.
 *  - MODDED TRAINING WORD: the visual side is entry-index gated, not kind-gated, so duplicated
 *    native kinds 0x10..0x13 elsewhere keep their original F/L/I/K descriptors.
 * ---------------------------------------------------------------------------- */
