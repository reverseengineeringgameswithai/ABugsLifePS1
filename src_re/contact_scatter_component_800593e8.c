/* ============================================================================
 * contact_scatter_component_80059e3e8.c  — contact-record spawn-scatter decoder [PHASE 4]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.800593E8  (extent 0x800593E8..0x8005953B, jr ra at 0x80059534,
 *                    delay slot 0x80059538 `addu v0, a1, zero`)
 * CENSUS NAME       : contact_scatter_component_decode
 * CONFIDENCE        : SOLVED — measured statically, then VERIFIED LIVE 24/24 exact matches
 *                    (analysis/phase4_contact_object_render.json task2_fcn_800593E8).
 *                    Cases 2,3,4,5,6 were NOT exercised live (static-only for those five);
 *                    cases 1 and the pass-through were live-verified.
 * CALLER            : contact_alloc (0x80059E44, see contact_alloc_80059e44.c) — called
 *                    four times per allocation, once per table-A field, to produce record
 *                    +0x0C/+0x10/+0x14/+0x18.
 * KNOWN GLOBAL       : G_SCATTER_CURSOR (0x800822F4) — a BYTE-STREAM cursor into a table
 *                    of pre-generated "random" bytes. The table is NOT a dedicated data
 *                    blob: the game reuses ITS OWN CODE IMAGE as the noise source (a live
 *                    read observed the cursor pointing into 0x80017F53, inside .text).
 *                    Every case advances this cursor by exactly one byte, including the
 *                    pass-through case, which reads a byte and then still discards it —
 *                    no, CORRECTION: selector 0 / >=7 (pass-through) consumes NOTHING,
 *                    only cases 1-6 read+advance the cursor. See dispatch below.
 * ============================================================================ */

#include "re_types.h"
#include <stdint.h>

#define G_SCATTER_CURSOR  0x800822F4u

/*
 * fcn.800593E8 — u32 f(selector_nibble, value). Six cases (1..6) apply a distinct
 * transform to `value` using one freshly-consumed "random" byte; selector 0 and any
 * value >= 7 return `value` UNCHANGED with NO cursor advance (contact_alloc's row-3
 * all-zero-selector profile relies on exactly this: zero random bytes consumed, see
 * contact_alloc_80059e44.c's "why_row_3_is_all_zeros").
 *
 * Dispatch: a0 -= 1; if ((unsigned)a0 >= 6) return value unchanged (pass-through). Else
 * jr [0x8001B778 + a0*4] — jump table for cases 1..6 in order.
 */
uint32_t contact_scatter_component_decode(uint32_t selector_nibble, uint32_t value)
{
    uint32_t case_idx = selector_nibble - 1;
    if (case_idx >= 6)
        return value;   /* selector 0, or any selector >= 7: pass-through, NO cursor read */

    /* every taken case does the identical 4-instruction random-byte fetch first: */
    uint8_t *cursor = (uint8_t *)(uintptr_t)(*(int32_t *)(uintptr_t)G_SCATTER_CURSOR);
    *(int32_t *)(uintptr_t)G_SCATTER_CURSOR = (int32_t)(uintptr_t)(cursor + 1);
    uint32_t r = *cursor;   /* 'r' below matches the artifact's own case-formula notation */

    switch (selector_nibble) {
    case 1: return (uint32_t)(((int32_t)(r & value) - ((int32_t)value >> 1)) << 3);
    case 2: return (r & value) << 3;
    case 3: return (uint32_t)(-(int32_t)(r & value)) << 3;
    case 4: return ((r & value) + (((int32_t)value & 0xFFFFFF00) >> 4)) << 3;
    case 5: return (uint32_t)(((int32_t)(r & value) - (((int32_t)value & 0xFFFFFF00) >> 4)) << 3);
    case 6: return (uint32_t)(((int32_t)(r & value) - ((int32_t)value >> 1)) << 4);
    default: return value;   /* unreachable given the case_idx >= 6 guard above */
    }
}
