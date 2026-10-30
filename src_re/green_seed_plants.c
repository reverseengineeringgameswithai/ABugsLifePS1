/* ============================================================================
 * green_seed_plants.c — the green seed lane: leaf platforms + climbing plants
 * ----------------------------------------------------------------------------
 * Decoded 2026-07-03 from the operator's `green_seed_levels.movie.json`
 * (initial 121368, 2713 frames; windows: G1 121531-121896 small leaf /
 *  G2 122143-122547 taller leaf / G3 122809-123381 three-leaf climber /
 *  G4 123427-124032 rose climber). Companion to brown/blue_seed_plants.c.
 *
 * CRACK: identical X-butt-slam chain (X pressed 38-60f before every spawn).
 * Spawns matched the (green,count) rows of 0x8007A448 exactly:
 *   G1 slot3 type 4 @121568 · G2 slot4 type 10 @122171 ·
 *   G3 slot5 type 9 @122837 · G4 slot6 type 1 @123455
 *   (type 1 = PLANT01 rose DID load on this level — the "unreachable from
 *    LEVEL01's model set" caveat is per-level, not global.)
 *
 * ---------------------------------------------------------------------------
 * MECHANISM — green plants are PASSIVE COLLISION, not dispatcher verbs
 * ---------------------------------------------------------------------------
 * All four types route to the "passive" handler FUNC_8005CCE8 (the dispatch
 * table's platform/climb entry). Live read-watch on the active plant slot
 * during a hang shows the handler reading the slot EVERY FRAME
 * (PCs 0x8005cd8c / 0x8005cda0 / 0x8005cda4 / 0x8005cdd0 / 0x8005ce90 /
 *  0x8005cf34 / 0x8005d0d0 / 0x8005d220 — slot fields +0x0/+0x2/+0x4/+0x6/
 *  +0x14/+0x26/+0x2e), testing Flik against the plant's geometry and feeding
 * the result into the STANDARD player collision path:
 *   - standing on a leaf top and HANGING on a stem both show the ordinary
 *     grounded Y-commit writers (0x80036384 / 0x80036cf0 / 0x80036d58 — the
 *     movement-integrator family) and the ordinary landing writers
 *     (0x80035e40 / 0x80035fe0) at attach;
 *   - no special vy writer exists for green (unlike propeller/cannon).
 * => a plant is a dynamic floor/grab surface injected into normal collision.
 *
 * ---------------------------------------------------------------------------
 * CLIMBING LAW (three-leaf type 9 / rose type 1) — jump-and-grab, not a mode
 * ---------------------------------------------------------------------------
 *   The "climb" is a LADDER OF JUMPS: Flik jumps (normal impulse ~ -0xB00,
 *   gravity-decayed by 0x80048d90 as usual), and on CONTACT with the stem he
 *   GRABS: treated as grounded (vy held 0, Y frozen — gravity suspended) by
 *   the standard integrator; then jumps again from the hang point. Observed
 *   hang holds of ~27+ frames with Y locked (e.g. -25475), then the next
 *   burst. Climbers reached: three-leaf ~24.9k, rose ~38.6k above ground.
 *
 * ---------------------------------------------------------------------------
 * PLATFORM HEIGHTS + LIFETIMES (movie-measured)
 * ---------------------------------------------------------------------------
 *   small leaf (4): top ~2.8k above ground (brief 9f stand captured)
 *   taller leaf (10): ~4.3k reached at jump apex; the operator noted it is
 *     NOT reachable without a mushroom boost — top-standing was not exercised
 *     (mechanism proven identical via G1 + the climbers; no redo needed).
 *   lifetimes (spawn -> slot freed; the standard wilt chain, see
 *   blue_seed_plants.c): type4 ~348f · type10 ~381f · type9 ~543f ·
 *   type1 ~555f — climbers persist noticeably longer than platforms.
 * ============================================================================ */

#include "re_types.h"

#define PASSIVE_PLANT_HANDLER 0x8005CCE8u /* types 4/9/10/12 (+1): platform/climb  */
#define PASSIVE_READER_FIRST  0x8005cd8cu /* per-frame slot readers inside it       */
#define PASSIVE_READER_LAST   0x8005d220u
#define GREEN_T1_SMALL_LEAF   4
#define GREEN_T2_TALL_LEAF    10
#define GREEN_T3_THREE_LEAF   9
#define GREEN_T4_ROSE         1
#define CLIMB_HANG_VY         0          /* grabbed = grounded; gravity suspended  */

void green_seed_plants_refs(void)
{
    volatile unsigned t = PASSIVE_PLANT_HANDLER ^ PASSIVE_READER_FIRST ^ PASSIVE_READER_LAST;
    volatile int v = GREEN_T1_SMALL_LEAF + GREEN_T2_TALL_LEAF + GREEN_T3_THREE_LEAF +
                     GREEN_T4_ROSE + CLIMB_HANG_VY;
    (void)t; (void)v;
}

/*
 * PHASE 4 B05 CORRECTION (2026-08-03)
 *
 * Earlier prose in this reconstruction describes the green routes as wholly
 * passive and implies that no green-specific vertical-velocity writer exists.
 * That is too broad. 0x8005CCE8 is only the plant-walker continuation into the
 * common loop at 0x8005CD2C. During state-0 growth, the gate at
 * 0x8005CF30..0x8005D0CC writes player VY=-3584 for type 4 and sends green
 * types 1/9/10 through the generic radial reaction that writes VY=-2048.
 * Mature leaf support is still ordinary asset collision. See
 * SYS_green_seed_platforms.md and EXP_2026-08-03_phase4_b05_green_leaf_platforms.md.
 */
