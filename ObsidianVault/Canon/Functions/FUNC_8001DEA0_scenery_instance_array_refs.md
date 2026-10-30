---
kind: function
id: FUNC_8001DEA0
aliases: [FUNC_8001DEA0, 0x8001dea0]
address: 0x8001DEA0
name: scenery_instance_array_refs
status: static_seen
confidence: medium
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - src_re/scenery_instance_array_8001dea0.c
src_paths:
  - src_re/scenery_instance_array_8001dea0.c
patch_policy: unknown
---

# FUNC_8001DEA0 - scenery instance array refs

## Purpose

Generated from C source coverage. The original-game behavior should be refined manually with call/read/write links.

## Known behavior

See the exact source excerpt below. Preserve `UNKNOWN`, `LIKELY`, and `TODO` labels from the source comments.

## Address / identity

- Address: `0x8001DEA0`
- Name: `scenery_instance_array_refs`
- Source path: `src_re/scenery_instance_array_8001dea0.c`

## C source excerpt

Source: `src_re/scenery_instance_array_8001dea0.c`

```c
/* ============================================================================
 * scenery_instance_array_8001dea0.c — chunk-35 arena instance draw loop [PARTIAL]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESSES : draw loop body ~0x8001D900..0x8001DF8C (caller of
 *                      FUNC_800172DC at 0x8001DF2C, ra 0x8001DF34).
 *                      Instance array: stride 0x54, base 0x80089F58 (LEVEL01;
 *                      ~25 live entries with arena mesh ptrs).
 * CONFIDENCE         : PARTIAL — array + draw path live-proven (execTrace);
 *                      static world-placement encoding NOT yet identified.
 * ============================================================================
 *
 * WHAT IS PROVEN (2026-07-07, pristine LEVEL01 stall + walk):
 *  - FUNC_800172DC (generic GTE mesh submitter, ALSO used for Flik's body) is
 *    called ~4×/frame with a0 = entries of a stride-0x54 array at 0x80089F58.
 *    a1 = 0x1F8003C8 (scratchpad packet staged by this caller), NOT the mesh.
 *  - Entry fields:
 *      +0x20  mesh pointer into the chunk-35 arena (0x8012C1D0..) — STATIC.
 *      +0x0c  second arena pointer on some entries (LOD pair?).
 *      +0x00..+0x08, +0x28..+0x38  rewritten EVERY frame by 0x8005EE14 /
 *             0x8005EFD0 / 0x80060548 (matrix/dynamics helpers; +0x34 lo16
 *             clusters ≈ view-space Z). +0x60..+0x70 region (via shifted base
 *             regs; parallel 0x54-stride walkers s1/s2/s4..s7 in the loop) =
 *             s16 3x3 instance rotation matrix consumed with the camera
 *             rotation globals 0x800A6566/6A/6C.
 *  - Load-time one-shot writer of +0x00: 0x8002FD98 (struct init, writes 0).
 *  - Savestate-controlled pokes of every dumped field (incl. the mesh ptr)
 *    produced ZERO pixel diffs 2 frames later -> the on-screen packets are
 *    NOT rebuilt from this struct per frame (zone-baked packet path, like the
 *    GP0(60) fill bands; rebuilt on camera-zone change only), OR the drawn 4
 *    entries that frame were other slots. Distinguish next time by poking ALL
 *    25 entries at once and forcing a zone change.
 *
 * WHY IT MATTERS: the chunk-35 instances are the PEBBLED NEAR-FIELD of
 * pristine gameplay (the payload floors cannot draw the nearest band — PS1
 * size-reject; see docs/G3_NATIVE_P58_NATIVE_DENSITY_AND_RENDER_MODES.md).
 * Re-heighting these instances to an authored surface would give custom
 * levels the native pebbled underfoot look. Blocked on finding the static
 * placement encoding (world XZ is NOT an obvious field of the 0x54 struct;
 * candidate: the packets are baked per camera zone from a different source
 * list — find the zone-bake routine by write-watching a packet in the
 * 0x801Dxxxx arena across a zone change while WALKING).
 * ============================================================================ */

#include "re_types.h"

#define G_INSTANCE_ARRAY   0x80089F58u /* stride 0x54, ~25 entries (LEVEL01)  */
#define G_INSTANCE_STRIDE  0x54u
#define G_SUBMITTER        0x800172DCu /* generic GTE mesh submitter (shared) */
#define G_DRAW_CALLER      0x8001DF34u /* ra of the instance draw jal          */
#define G_SCRATCH_PACKET   0x1F8003C8u /* a1 staging packet in scratchpad      */
#define G_ARENA_BASE       0x8012C1D0u /* chunk-35 shared model arena          */

void scenery_instance_array_refs(void)
{
    volatile unsigned t = G_INSTANCE_ARRAY ^ G_INSTANCE_STRIDE ^ G_SUBMITTER ^
                          G_DRAW_CALLER ^ G_SCRATCH_PACKET ^ G_ARENA_BASE;
    (void)t;
}
```

## Evidence

- Source: `src_re/scenery_instance_array_8001dea0.c`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`
