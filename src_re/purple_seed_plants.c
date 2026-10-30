/* ============================================================================
 * purple_seed_plants.c — the purple seed lane: berry-grant plants (map CLOSED)
 * ----------------------------------------------------------------------------
 * Decoded 2026-07-03 from the operator's `purple_seed_levels.movie.json`
 * (windows: P1 133250-133571 / P2 133796-134109 / P3 134350-134769 /
 *  P4 135000-135406). Companion to brown/blue/green_seed_plants.c.
 * CLOSES the long-open HRE-004/RCG-004 residual "purple ctor -> berry-kind map".
 *
 * CRACK: identical X-butt-slam chain (X 34-60f before every spawn).
 * All four tiers grow plant TYPE 6 (the berry-carrier) with a per-tier extra;
 * the type-6 handler 0x8005C6F0 spawns ONE berry-grant contact object
 * (ctor = (extra>>12) + 0x1F, one-shot via slot bit3), which Flik collects
 * to ARM a berry (equip byte 0x800a6597 via the walker berry-arm actions).
 *
 * ---------------------------------------------------------------------------
 * THE MAP (live-observed, plant -> grant object -> equip transition)
 * ---------------------------------------------------------------------------
 *  tier | extra  | ctor/type | walker action | equips           | retail name
 *  -----+--------+-----------+---------------+------------------+-------------
 *   1   | 0x4000 |  0x23/35  | 35 (0x80058968) | 1  BLUE/super  | Blue/Super Berry
 *   2   | 0x2000 |  0x21/33  | 33 (0x80058940) | 2  HOMING      | Green/Homing Berry
 *   3   | 0x1000 |  0x20/32  | 36 (0x80058978) | 4  MEGA        | "stronger homing"
 *   4   | 0x3000 |  0x22/34  | 34 (0x80058954) | 3  GOLD        | Gold Berry
 *  (observed equip walk: 0 -> 1 @133396 -> 2 @133921 -> 4 @134488 -> 3 @135205)
 *
 * UNIFICATION: these are the SAME contact-object grant types 32..35 cataloged
 * in enemy_drops.c — a purple-4 plant produces the literal type-34 gold-berry
 * pickup that arms/equips gold, and blue count-3's bubble shield is the extra-0
 * case (ctor 0x1F) of the same handler. The Gold-berry drop mod is intentionally
 * different: it uses the same contact allocator, but spawns a type-120 spinning
 * gold-kill glyph and credits the tagged enemy on walk-over without equipping gold.
 *
 * Lifetimes (standard wilt chain, blue_seed_plants.c): ~300-378 frames.
 * ============================================================================ */

#include "re_types.h"

#define PURPLE_PLANT_TYPE      6
#define BERRY_CARRIER_HANDLER  0x8005C6F0u /* spawns ctor=(extra>>12)+0x1F, once */
#define GRANT_BLUE_TYPE        35  /* extra 0x4000 -> equip 1 */
#define GRANT_HOMING_TYPE      33  /* extra 0x2000 -> equip 2 */
#define GRANT_MEGA_TYPE        32  /* extra 0x1000 -> equip 4 */
#define GRANT_GOLD_TYPE        34  /* extra 0x3000 -> equip 3 */

void purple_seed_plants_refs(void)
{
    volatile unsigned t = BERRY_CARRIER_HANDLER ^ (PURPLE_PLANT_TYPE +
        GRANT_BLUE_TYPE + GRANT_HOMING_TYPE + GRANT_MEGA_TYPE + GRANT_GOLD_TYPE);
    (void)t;
}
