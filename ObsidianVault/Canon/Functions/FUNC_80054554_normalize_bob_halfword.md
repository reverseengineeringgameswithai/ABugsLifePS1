---
kind: function
id: FUNC_80054554
aliases: [FUNC_80054554, 0x80054554]
address: 0x80054554
name: normalize_bob_halfword
status: static_seen
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - src_re/pickup_handlers_80054288_80054554.c
src_paths:
  - src_re/pickup_handlers_80054288_80054554.c
patch_policy: unknown
---

# FUNC_80054554 - normalize bob halfword

## Purpose

Generated from C source coverage. The original-game behavior should be refined manually with call/read/write links.

## Known behavior

See the exact source excerpt below. Preserve `UNKNOWN`, `LIKELY`, and `TODO` labels from the source comments.

## Address / identity

- Address: `0x80054554`
- Name: `normalize_bob_halfword`
- Source path: `src_re/pickup_handlers_80054288_80054554.c`

## C source excerpt

Source: `src_re/pickup_handlers_80054288_80054554.c`

```c
/* ============================================================================
 * pickup_handlers_80054288_80054554.c  — pickup/action handlers [PHASE 5 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESSES : source-side action labels inside fcn.80053814:
 *                      0x80053d04/0x80053e64/0x80053fc0/0x8005411c (FLIK bits,
 *                      summarized), 0x80054288..0x80054554 (berry/token/telescope),
 *                      plus fcn.80054eac (grain handler, 0x80054eac..0x80055188).
 * CONFIDENCE         : CONFIRMED marker/counter writes, token counter encoding, seed
 *                      power-up calls, telescope activation writes, grain count/reward branch.
 *                      Some side-effect globals remain UNKNOWN and are labelled.
 * SOURCE NOTES       : docs/LEVEL01_TYPE3F_MAP.md, docs/COORDINATE_MODDING.md,
 *                      docs/EXECUTABLE_AND_OVERLAYS.md, docs/EXPERIMENT_LOG.md,
 *                      Phase 2 source3f_dispatch_80053814.c, Phase 4 walker,
 *                      r2 disasm (MIPS LE, gp=0x80081d98).
 * KNOWN CALLERS      : fcn.80053814 source-side jump table 0x8001b42c; fcn.800586b0
 *                      record-side jump table 0x8001b570 mirrors several marker/grain cases.
 * KNOWN CALLEES      : fcn.80050994 (sound/event by id), fcn.8003e760 (token sprite
 *                      re-skin ONLY — plant selection happens at plant time, see
 *                      plant_spawn_8005bdbc.c / HRE-004),
 *                      fcn.8005044c (post-pickup bookkeeping), fcn.80045678,
 *                      fcn.80044d28, fcn.800571e0, fcn.8005721c.
 * KNOWN GLOBALS      : G_BERRY_MARKER, G_GRAIN_COUNT, G_SEED_CTR_ORANGE/BLUE/GREEN,
 *                      0x800a659b/9c (extra seed counters for kinds 0x2c/0x2d),
 *                      seed obj-id table 0x80078e90={0x17,0x19,0x18,0x2f},
 *                      0x800b0196 seed-nibble mask, 0x800824dc telescope-view active flag.
 * UNRESOLVED         : downstream gameplay EFFECT of each berry marker value; exact
 *                      meaning of seed-nibble mask 0x800b0196, grain pre-effect
 *                      fcn.80044d28, and several global timers/counters.
 *
 * IMPORTANT CONTEXT:
 *   The labels at 0x80054288..0x80054554 are not standalone ABI functions. They are
 *   jump-table cases inside fcn.80053814 and use that function's live registers:
 *     s4 = Type3FEntry* entry, s2 = entry+4, s3 = collected-bitmask/global byte,
 *     s1 = post-loop result code, fp = count/index for kind 0x30 cases.
 *   The C below models each case as a helper with explicit parameters.
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LBU(p)  (*(uint8_t  *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))
#define SH(p,v) (*(uint16_t *)(p) = (uint16_t)(v))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))

#define G_SCRIPT_CURSOR         0x800822f4u
#define G_SCENE_ID              0x80082504u
#define G_MASTER_GAME_STATE     0x800823a0u /* UNKNOWN name outside notes; compared to 2 */
#define G_GRAIN_PRE_EFFECT_GATE 0x8008244cu /* UNKNOWN gp+0x6b4 */
#define G_PROGRESS_BYTE         0x800a65a0u /* CONFIRMED FLIK/grain reward progress byte (<9) */
#define G_PLAYER_EXTRA_6548     0x800a6548u /* UNKNOWN companion player/global word */
#define G_UNK_FLAGS_6590        0x800a6590u /* UNKNOWN flags halfword; bit2 gates grain pre-effect */
#define G_UNK_COUNTER_6594      0x800a6594u /* UNKNOWN halfword touched by token/grain/walker */
#define G_EXTRA_SEED_CTR_2C     0x800a659bu /* CONFIRMED extra token counter for action 0x2c */
#define G_EXTRA_SEED_CTR_2D     0x800a659cu /* CONFIRMED extra token counter for action 0x2d */
#define G_TELESCOPE_ACTIVE      0x800824dcu
#define G_TELESCOPE_INDEX       0x800823ccu
#define G_PLAYER_VEL_X          0x800a652cu
#define G_PLAYER_VEL_Y          0x800a6530u
#define G_PLAYER_VEL_Z          0x800a6534u
#define G_PLAYER_GROUNDED       0x800a6582u
#define G_SEED_NIBBLE_MASK      0x800b0196u
#define G_BOB_188              0x800b0188u
#define G_BOB_18C              0x800b018cu
#define G_BOB_190              0x800b0190u
#define G_BOB_194              0x800b0194u
#define G_REWARD_SNAPSHOT      0x80090b80u
#define G_FLK_SNAPSHOT         0x800b3988u
static void normalize_bob_halfword(uint32_t addr)
{
    /* Repeated idiom: if value >= 0xc00, mirror from 0x1000; else clamp down
     * to 0x400 when value > 0x400; if zero, force 0x40. */
    int16_t v = LH(addr);
    if (v >= 0x0c00) {
        SH(addr, 0x1000 - v);
    } else if (v >= 0x0401) {
        SH(addr, 0x0400);
    }
    if (LH(addr) == 0) {
        SH(addr, 0x0040);
    }
}
/* Full source is in the listed source path. */
```

## Evidence

- Source: `src_re/pickup_handlers_80054288_80054554.c`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`
