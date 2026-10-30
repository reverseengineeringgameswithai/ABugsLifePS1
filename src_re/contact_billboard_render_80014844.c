/* ============================================================================
 * contact_billboard_render_80014844.c  — contact-object sprite renderer [PHASE 4 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.80014844  (656 bytes, 0x80014844..0x80014AD0, jr ra at 0x80014ACC)
 * CENSUS NAME       : contact_record_billboard_render
 * CONFIDENCE        : CONFIRMED. Every step below is a MEASURED disassembly read
 *                    (analysis/phase4_contact_object_render.json task3_renderer), not
 *                    inferred. This file has NOT been hand-asm'd or byte-matched; it is
 *                    documentation-grade C, like contact_alloc_80059e44.c and
 *                    contact_walker_800586b0.c, and is NOT a build unit.
 * SOLE CALLER       : 0x800225B0, inside the per-frame render sequence. a0/a1/a2 = camera
 *                    world X/Y/Z (a0 = *(s1); a1/a2 come from scratchpad 0x1F800378/037C).
 * KNOWN GLOBALS     : G_CONTACT_ARRAY (0x800B0D18, 64 * 0x38, shared with contact_alloc_
 *                    80059e44.c and contact_walker_800586b0.c), G_DESCRIPTOR_TABLE
 *                    (0x80096B98, u32[50], RAM/BSS — the SAME table type-0x3f pickups use,
 *                    just indexed differently, see the correction below), G_PRIM_CURSOR
 *                    (0x8008249C, the current linked-list OT primitive write pointer),
 *                    G_DEPTH_FAR_SCALE (0x80082394), G_OT_BASE (0x80082230),
 *                    G_OT_DEPTH_TABLE (0x800A3390).
 * UNRESOLVED        : the exact meaning of 0x800A3390's per-depth OT-bucket table; whether
 *                    culled records still get their +0x32 draw-flag bit cleared correctly
 *                    on every path (traced for the emit and near/far-cull paths only).
 *
 * CORRECTION TO AN EARLIER BRIEF (verified live 24/24, see the artifact): contact objects
 * were assumed to be OUTSIDE the 0x80096B98 kind->descriptor Canon that governs type-0x3f
 * pickups. REFUTED — this renderer uses the exact same table and the same descriptor
 * struct shape. The only difference is the INDEX: type-0x3f pickups index it by a
 * placement record's kind byte; contact objects index it by contact-record +0x20, which
 * is metadata-table-B's action id (see contact_alloc_80059e44.c). rec+0x20 is therefore
 * DOUBLE-DUTY: it selects both the behaviour handler (0x8001B570[action-2], see
 * contact_walker_800586b0.c) and the sprite descriptor (0x80096B98[action]). Changing one
 * changes the other. Descriptor indices 0x15, 0x19, 0x20 and 0x2E ARE consumed by contact
 * objects (0x2E is the B08 bubble shield's own sprite) and are NOT free to repurpose, even
 * though the type-0x3f "safe to repurpose" list (pickup-render-kind-descriptor-table
 * memory note) does not mention them — that list is type-0x3f-only.
 *
 * SPRITES, NOT MESHES: each drawn record emits exactly one 40-byte POLY_FT4 (textured
 * 4-point polygon), screen-aligned. The GTE rotation matrix is loaded ONCE before the loop
 * to a fixed diag(1.6, 1.0, 1.0) and never reloaded per object — only the TRANSLATION
 * (TRX/TRY/TRZ) varies per object, so quad corners are never camera-rotated, only the quad
 * *center* moves and the quad itself stays screen-aligned. This is why every contact
 * pickup in the game renders as a flat, camera-facing billboard.
 * ============================================================================ */

#include "re_types.h"

#define LW(p)    (*(int32_t  *)(p))
#define LH(p)    (*(int16_t  *)(p))
#define LHU(p)   (*(uint16_t *)(p))
#define LBU(p)   (*(uint8_t  *)(p))
#define SW(p,v)  (*(int32_t  *)(p) = (int32_t)(v))
#define SH(p,v)  (*(uint16_t *)(p) = (uint16_t)(v))
#define SB(p,v)  (*(uint8_t  *)(p) = (uint8_t)(v))

/* G_CONTACT_ARRAY is already defined in re_types.h (0x800b0d18u) */
#define CONTACT_COUNT        64
#define CONTACT_STRIDE       0x38
#define G_DESCRIPTOR_TABLE   0x80096B98u   /* u32[50], RAM/BSS, built at load               */
#define G_PRIM_CURSOR        0x8008249Cu   /* current OT primitive write pointer            */
#define G_DEPTH_FAR_SCALE    0x80082394u
#define G_OT_BASE            0x80082230u
#define G_OT_DEPTH_TABLE     0x800A3390u   /* u16[], indexed by (depth & ~1)                */
#define PRIM_SIZE            40             /* sizeof(POLY_FT4)                              */

/* record field offsets (shared with contact_alloc_80059e44.c's CONFIRMED map) */
#define REC_X          0x00
#define REC_Y          0x04
#define REC_Z          0x08
#define REC_ACTION_ID  0x20   /* metaB+0x00; ALSO the descriptor index for THIS renderer   */
#define REC_LIFETIME   0x22   /* metaB+0x02; countdown TTL, only the LOW BYTE is checked   */
#define REC_RADIUS_X   0x28   /* metaB+0x08; quad half-width                                */
#define REC_RADIUS_Y   0x2A   /* metaB+0x0a; quad half-height                               */
#define REC_FRAME_IDX  0x31   /* animation frame index into the descriptor's u/v strip     */
#define REC_DRAW_FLAG  0x32   /* bit0 = "was drawn THIS frame" -- objective render proof   */
#define REC_TPAGE_BITS 0x33   /* flags; bits 0x60 OR into the emitted TPAGE                */
#define REC_TINT_RGB   0x34   /* 3 bytes: R,G,B                                             */
#define REC_GPU_CODE   0x37   /* GPU primitive code byte, observed 0x2C or 0x2E             */

/* the 0xC-byte descriptor struct at G_DESCRIPTOR_TABLE[action_id] (task3_renderer.descriptor_struct) */
#define DESC_ATLAS_TYPE  0x00  /* u8: 0x1C/0x1D/0x1E observed; NOT read by this renderer   */
#define DESC_WIDTH_M1    0x02  /* u8: texel width - 1                                       */
#define DESC_HEIGHT_M1   0x03  /* u8: texel height - 1                                      */
#define DESC_TPAGE       0x04  /* u16: zero in the EXE image, written at runtime            */
#define DESC_CLUT        0x06  /* u16: zero in the EXE image, written at runtime            */
#define DESC_UV_STRIP    0x08  /* u16 per frame (u | v<<8); frame index = rec+0x31          */

extern void  fcn_gte_mvmva_translate(int32_t dx, int32_t dy, int32_t dz); /* cop2 0x04BE012 */
extern void  fcn_gte_rtpt(void);                                          /* cop2 0x0280030 */

typedef struct ContactRecord ContactRecord; /* opaque here; full layout in contact_alloc_80059e44.c */

/*
 * fcn.80014844 — walk the 64-slot contact array and emit one screen-aligned POLY_FT4
 * sprite per live, visible, in-frustum record. Sole caller passes the camera position.
 */
void contact_record_billboard_render(int32_t cam_x, int32_t cam_y, int32_t cam_z)
{
    uint8_t *rec = (uint8_t *)(uintptr_t)G_CONTACT_ARRAY;
    uint8_t *prim_cursor = (uint8_t *)(uintptr_t)LW(G_PRIM_CURSOR);

    /* GTE rotation matrix set ONCE, outside the loop -- diag(1.6, 1.0, 1.0). Only the
     * per-object TRANSLATION varies below, so sprites never rotate with the camera. */
    /* ctc2 6553 -> $0 (r0c0=1.6, r0c1=0); ctc2 4096 -> $2 (r1c1=1.0); ctc2 4096 -> $4 (r2c2=1.0) */
    /* VZ0/VZ1/VZ2 are also zeroed once before the loop (the quad has no depth extent). */

    for (int i = 0; i < CONTACT_COUNT; i++, rec += CONTACT_STRIDE) {
        /* ---- 1. liveness: BYTE load of the low byte of the 16-bit TTL ---- */
        if (LBU(rec + REC_LIFETIME) == 0)
            continue;

        uint8_t draw_flag = LBU(rec + REC_DRAW_FLAG) & 0xFE;  /* clear bit0 by default */

        /* ---- 3. position: (rec.xyz - camera.xyz) >> 5, then MVMVA (view rotation only) ---- */
        int32_t dx = (LW(rec + REC_X) - cam_x) >> 5;
        int32_t dy = (LW(rec + REC_Y) - cam_y) >> 5;
        int32_t dz = (LW(rec + REC_Z) - cam_z) >> 5;
        fcn_gte_mvmva_translate(dx, dy, dz);   /* -> MAC1/2/3 -> ctc2 TRX/TRY/TRZ */

        /* ---- 4. quad corners (screen-aligned, size from the record's own radius) ---- */
        int16_t rx = LH(rec + REC_RADIUS_X);
        int16_t ry = LH(rec + REC_RADIUS_Y);
        /* VXY0 = (-rx, -ry); VXY1 = (+rx, +ry) */
        fcn_gte_rtpt();   /* transforms both corners through the fixed rotation + the
                            * per-object translation just set above -> SXY0, SXY1, SZ */
        int32_t sxy0 = 0, sxy1 = 0;   /* GTE SXY FIFO outputs, opaque here */
        int32_t sz = 0;                /* GTE SZ FIFO output (== MAC3), used below */

        /* ---- 6. depth cull ---- */
        if (sz < 40 || sz >= (int32_t)(LW(G_DEPTH_FAR_SCALE) << 2)) {
            SB(rec + REC_DRAW_FLAG, draw_flag);   /* NOT drawn this frame */
            continue;
        }

        /* ---- 7. screen cull: reject unless a corner is on-screen and above a Y floor ---- */
        if (!((uint32_t)sxy0 < 0x00F00000u || (uint32_t)sxy1 < 0x00F00000u) ||
            !((int16_t)sxy0 < 512 || (int16_t)sxy1 < 512)) {
            SB(rec + REC_DRAW_FLAG, draw_flag);
            continue;
        }

        /* ---- 5. descriptor: action id 0 is the renderer's explicit "do not draw" value ---- */
        uint16_t action_id = LHU(rec + REC_ACTION_ID);
        if (action_id == 0) {
            SB(rec + REC_DRAW_FLAG, draw_flag);
            continue;
        }
        uint8_t *desc = (uint8_t *)(uintptr_t)
            LW(G_DESCRIPTOR_TABLE + action_id * 4);

        /* ---- 9. texture: u/v come from the descriptor's per-frame strip ---- */
        uint16_t uv0   = LHU(desc + DESC_UV_STRIP + LBU(rec + REC_FRAME_IDX) * 2);
        uint8_t  u0    = uv0 & 0xFF, v0 = uv0 >> 8;
        uint8_t  u1    = u0 + LBU(desc + DESC_WIDTH_M1);
        uint8_t  v2    = v0 + LBU(desc + DESC_HEIGHT_M1);
        uint16_t clut  = LHU(desc + DESC_CLUT);
        uint16_t tpage = LHU(desc + DESC_TPAGE) + (LBU(rec + REC_TPAGE_BITS) & 0x60);

        /* ---- 8. OT insert: classic addPrim into the depth-bucketed linked list ---- */
        uint32_t depth_bucket = LW(G_OT_BASE) +
            LHU((uint8_t *)(uintptr_t)(G_OT_DEPTH_TABLE + (sz & ~1)));
        uint32_t *bucket = (uint32_t *)(uintptr_t)depth_bucket;

        /* ---- build the 40-byte POLY_FT4 at prim_cursor ---- */
        SW(prim_cursor + 0x00, (*bucket & 0x00FFFFFF) | 0x09000000u); /* tag: 9 words follow */
        /* ---- 10. colour: straight copy of the record's tint + GPU code byte ---- */
        SW(prim_cursor + 0x04, LW(rec + REC_TINT_RGB));  /* {R,G,B,code} packed             */
        /* XY0 = SXY0, XY3 = SXY1, XY1 = (SXY1.x,SXY0.y), XY2 = (SXY0.x,SXY1.y) -- axis-aligned */
        SW(prim_cursor + 0x08, sxy0);
        SW(prim_cursor + 0x0C, (uv0 & 0xFF) | (v0 << 8) | (clut << 16));   /* UV0 + CLUT   */
        SW(prim_cursor + 0x10, /* (sxy1.x, sxy0.y) */ 0);
        SW(prim_cursor + 0x14, u1 | (v0 << 8) | (tpage << 16));            /* UV1 + TPAGE  */
        SW(prim_cursor + 0x18, /* (sxy0.x, sxy1.y) */ 0);
        SW(prim_cursor + 0x1C, u0 | (v2 << 8));                            /* UV2          */
        SW(prim_cursor + 0x20, sxy1);
        SW(prim_cursor + 0x24, u1 | (v2 << 8));                            /* UV3          */

        *bucket = (uint32_t)(uintptr_t)prim_cursor & 0x00FFFFFFu;
        prim_cursor += PRIM_SIZE;

        SB(rec + REC_DRAW_FLAG, draw_flag | 1);   /* drawn this frame */
    }

    SW(G_PRIM_CURSOR, (int32_t)(uintptr_t)prim_cursor);
}
