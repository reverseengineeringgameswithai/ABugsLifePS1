/* ============================================================================
 * yellow_seed_plants.c — the yellow seed lane: berry shooters + the MINE plant
 *                        (and the SECOND permanent-kill lane, confirmed)
 * ----------------------------------------------------------------------------
 * Decoded 2026-07-03 from the operator's `yellow_seed_levels.movie.json`
 * (windows: Y1 262500-263213 blue shooter / Y2 263462-263927 purple shooter /
 *  Y3 264100-265000 mine). Yellow count-4 duplicates count-3 (type 11) — three
 *  windows cover the lane. Completes the seed system: ALL FIVE LANES SOLVED.
 * NOTE: the operator flagged a desync in Y3; in this replay all three windows
 * in fact played (shooters spawned + fired; both mines grew; the mine KILL
 * landed) — the evidence below is from the replayed movie itself.
 *
 * CRACK: identical X-butt-slam chain. Spawns: Y1 slot3 type 14 @262520 ·
 * Y2 slot4 type 13 @263495 · Y3 slot5 type 11 @264134 + slot6 type 11 @264410.
 *
 * ---------------------------------------------------------------------------
 * SHOOTERS (types 14 / 13 — handlers 0x8005CA7C / 0x8005CA24)
 * ---------------------------------------------------------------------------
 *   Both fire class-2 berry contact objects (the same projectile class as
 *   Flik's thrown berries):
 *     type 14 (count-1, "blue berry shooter"):   projectile model +0x24 = 110
 *       (the basic/blue berry model)
 *     type 13 (count-2, "purple homing shooter"): projectile model +0x24 = 124
 *       (the MEGA/purple homing model)
 *   Their projectiles carry +0x27 = 0 -> shooter kills are NOT permanent.
 *   Firing is intermittent (observed sporadic fires; trigger law = residual).
 *   Lifetimes: type 14 ~666f, type 13 ~432f (standard wilt chain).
 *
 * ---------------------------------------------------------------------------
 * THE MINE (type 11 — handler 0x8005C918): enemy-proximity bomb, PERMANENT
 * ---------------------------------------------------------------------------
 *   - mine #1: planted @264134; when an enemy came near it EXPLODED at ~+90f
 *     — the mine slot is CONSUMED by its own explosion (slot freed at the
 *     detonation frame).
 *   - mine #2: planted @264410 with only Flik nearby; never exploded; wilted
 *     normally at ~480f  =>  the fuse is ENEMY-proximity; Flik-safe.
 *   - THE KILL IS PERMANENT: G_ENEMIES_REMAINING 15 -> 14 at the detonation.
 *   - THE MECHANISM (breakpoint on the RCG-022 permanence gate, caught live):
 *       explosion hit-record: class=2000, +0x24=0, **+0x27 = 6**
 *       -> gate 0x800591f0 falls to the +0x27==6 compare -> s7 |= 2 (PERM)
 *       -> 999-hit -> destroy block -> quota decrement.
 *     ==> the second permanent-kill lane hypothesized in
 *     enemy_death_permanence.c ("+0x27==6 LIKELY the Mine Plant") is now
 *     CONFIRMED. ABL has exactly TWO permanent-kill sources:
 *       GOLD berry  (hit-record +0x24 == 11)
 *       MINE plant  (hit-record +0x27 == 6)
 * ============================================================================ */

#include "re_types.h"

#define SHOOTER_BLUE_HANDLER   0x8005CA7Cu /* type 14: fires model-110 berries  */
#define SHOOTER_PURPLE_HANDLER 0x8005CA24u /* type 13: fires model-124 (mega)   */
#define MINE_HANDLER           0x8005C918u /* type 11: enemy-proximity bomb     */
#define MINE_PERM_LANE_BYTE    6           /* explosion record +0x27 == 6 ->    */
                                           /* s7|=2 permanent (RCG-022 lane 2)  */
#define MINE_FUSE_OBSERVED_F   90          /* plant->detonation with enemy near */

void yellow_seed_plants_refs(void)
{
    volatile unsigned t = SHOOTER_BLUE_HANDLER ^ SHOOTER_PURPLE_HANDLER ^ MINE_HANDLER;
    volatile int v = MINE_PERM_LANE_BYTE + MINE_FUSE_OBSERVED_F;
    (void)t; (void)v;
}
