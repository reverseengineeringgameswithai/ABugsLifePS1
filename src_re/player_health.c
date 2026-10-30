/* ============================================================================
 * player_health.c — Flik health economy: damage, death, lives, health leaves
 * ----------------------------------------------------------------------------
 * RCG-021 ("Health leaves and damage counters"). Live investigation 2026-07-03
 * (isolated DuckStation, SCUS-94288, mosquito.sav) + the health-leaf drop
 * machinery decoded while building the gold-drop mod (see enemy_drops.c).
 *
 * OPERATOR GROUND TRUTH (incorporated): enemy contact damage is a FLAT -1, uniform
 * across all enemies (not per-enemy variable). The only other health-loss path is
 * falling into a bottomless pit, which is a SEPARATE instant death (costs a life
 * directly) — it is not enemy contact damage.
 *
 * ---------------------------------------------------------------------------
 * HEALTH READOUT — 0x800a7e2a (s16), full = 7
 * ---------------------------------------------------------------------------
 *   - The SELECT status panel reads it (`lh` @0x80052c10) to draw the leaf count
 *     (draws 272 - <sin-scaled> per leaf). Full = 7 leaves; 0 = last HP (next hit
 *     = death). Live: one mosquito strike 5->4; two strikes 7->5 (= flat -1 each).
 *   - CAVEAT: in gameplay the in-game HUD (fcn.800526f4 region, PCs 0x80052640+)
 *     REUSES/animates this 0x800a7e2x cluster for the leaf-spin/flash, so raw live
 *     reads cycle 0..7 while Flik moves or just after a hit. The AT-REST / SELECT
 *     value is the true health. (Corrects the old "byte mirror 0x800910a8" claim —
 *     0x800910a8/a9/aa are HUD leaf-spin animation counters, NOT a health mirror.)
 *   - The exact -1 damage-write instruction was NOT isolated: the field is HUD-
 *     animated and the accessLog PC attribution was unreliable here (residual).
 *     Positional knockback on contact is the movement-integrator response near
 *     0x80036cec (separate from the HP decrement).
 *
 * ---------------------------------------------------------------------------
 * LIVES — 0x800a65a0 (u8)
 * ---------------------------------------------------------------------------
 *   Decrements on death (contact-death OR pit-death); 0 = last life -> game-over.
 *   (Menu/HUD note: poking it kept Flik alive through a fatal hit.) The pit fall is
 *   an instant death that spends a life directly, bypassing the -1 contact path.
 *
 * ---------------------------------------------------------------------------
 * HEALTH-LEAF MERCY-DROP SYSTEM (health UP)  — see enemy_drops.c for spawn_drop
 * ---------------------------------------------------------------------------
 *   - DROP: health leaf = spawn_drop type 38, emitted by the once-per-death drop
 *     roll at 0x8004999c, gated on the mercy counter [0x800a6594] < 4 and rarer as
 *     it rises (chance = 1/(2 << [0x800a6594])), skipping berry-tough enemies.
 *   - COLLECT: walker action_id 9 -> handler 0x80058864 — spawns pickup FX
 *     (0x800503fc), plays SFX 62, and INCREMENTS the mercy counter [0x800a6594].
 *   - 0x800a6594 = the health-leaf drop-rate governor: collecting leaves raises it,
 *     which throttles/stops further leaf drops (a supply-limiting mercy mechanic).
 *     Distinct from the displayed health (0x800a7e2a) AND the enemies-remaining
 *     quota (0x800a658e, RCG-022).
 *   - Heal AMOUNT = residual: a clean at-rest measurement was blocked by the display
 *     animation + ongoing enemy attacks; the collect handler bumps the mercy counter
 *     + SFX, and the health restore flows through the animated 0x800a7e2a path.
 * ============================================================================ */

#include "re_types.h"

#define G_HEALTH_DISPLAY  0x800a7e2au  /* s16, full=7; SELECT reads it; HUD-animated in play */
#define G_LIVES           0x800a65a0u  /* u8; 0 = last life -> game-over                       */
#define G_LEAF_MERCY_CTR  0x800a6594u  /* health-leaf drop governor; ++ on leaf collect        */
#define LEAF_DROP_TYPE    38           /* spawn_drop type: health leaf (collect action_id 9)    */
#define LEAF_COLLECT_SFX  62

/* Contact damage is a fixed constant, uniform across enemies (operator-confirmed,
 * live-verified as -1). Pit/fall = separate instant death (spends a life). */
#define CONTACT_DAMAGE    1            /* health -= 1 per enemy hit (flat)                      */

void player_health_refs(void)
{
    volatile int t = G_HEALTH_DISPLAY + LEAF_DROP_TYPE + CONTACT_DAMAGE + LEAF_COLLECT_SFX;
    (void)t;
}
