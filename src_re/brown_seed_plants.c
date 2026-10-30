/* ============================================================================
 * brown_seed_plants.c — confirmed brown-seed planting and per-tier effects:
 *                       crack-open -> plant -> observed effect on Flik -> discard
 * ----------------------------------------------------------------------------
 * Decoded 2026-07-03 from the operator's `brown_seed_levels.movie.json`
 * (initial 47454, 2381 frames; one window per token tier:
 *  T1 47500-47923 mushroom / T2 48143-48615 propeller /
 *  T3 48880-49400 dandelion / T4 49415-49798 cannon).
 * Extends seed-plant binding (HRE-004): the (color,count)->type table was known;
 * THIS file adds the crack trigger, the per-tier handler physics on Flik, and
 * the carry/discard lifecycle. Vault: [[Brown seed plant behaviors]].
 *
 * ---------------------------------------------------------------------------
 * 1. HOW THE SEED IS CRACKED OPEN (identical at all four tiers)
 * ---------------------------------------------------------------------------
 *   Input signature (movie): X (jump) pressed ~50 frames before each crack —
 *   Flik JUMPS and BUTT-SLAMS onto the seed. The chain:
 *     a. slam contact: PC 0x8004af80 writes 0x00010000 to seed_actor+0x6c
 *        (ONE-SHOT; observed at movie frames 47577/48151/48903/49415 — the
 *        crack trigger; +0x6c high halfword = crack state).
 *     b. the actor manager (writer 0x8004d494, ~10 stepped writes to +0x6c over
 *        ~20 frames) runs the CRACK-OPEN animation; seed flags +0x5c drop the
 *        pickup bit (0x4031 -> 0x31).
 *     c. ~20 frames after the slam the plant spawner (FUNC_8005BDBC) allocates
 *        a plant slot (20 x 0x30 @ 0x80090BF0; slot+0x20 backlinks the seed
 *        actor) with type from the (color,count) table 0x8007A448.
 *   Observed spawns (brown lane counts 1..4): slot10 type 5 @47598,
 *   slot11 type 3 @48174, slot12 type 8 @48924, slot13 type 2 @49437.
 *   The seed ACTOR is reusable: the same actor 0x800a0854 was carried, cracked,
 *   and regenerated across all four windows (flags cycle back to 0x4031).
 *
 * ---------------------------------------------------------------------------
 * 2. WHAT EACH TIER DOES FOR FLIK (handler physics, live-measured)
 * ---------------------------------------------------------------------------
 *   Flik vy = 0x800A6530 (-Y is up; gravity integrator writer = 0x80048d90,
 *   +0x100 per 2-frame physics tick).
 *
 *   T1 count-1 MUSHROOM TRAMPOLINE (type 5, handler 0x8005C58C):
 *     On Flik landing on the cap (landing writers 0x80035e40/0x80035fe0 then
 *     the handler @0x8005c600), the bounce sets vy ~= -3328 (-0xD00) ->
 *     Flik rises ~28,000 units; retriggers on every landing (infinite bounce).
 *
 *   T2 count-2 PROPELLER PLANT (type 3, handler 0x8005C258):
 *     While Flik rides it, the handler writes vy DIRECTLY every physics tick
 *     (@0x8005c428 / 0x8005c458) with an ACCELERATING ramp: -0x1C0, -0x2C0,
 *     -0x3C0 ... (-0x100 steeper per tick) -> sustained powered lift; observed
 *     rise ~44,000 units.
 *
 *   T3 count-3 DANDELION (type 8, handler 0x8005C818):
 *     The retained B03 capsule corrects the older "attach @0x8005c84c" claim:
 *     0x8005c84c is only addiu v0,5. The trigger path stores vy=-4096 at
 *     0x8005c848 and mode=5 at 0x8005c854. On the next physics update the
 *     shared player path advances to mode 6 and applies an exact ballistic law:
 *     vy += 256 and delta-Y == new vy every two movie frames. In the captured
 *     event, Flik rises 30,720 units before the apex. This proves a one-shot
 *     lift/updraft impulse in that fixture, not sustained attachment, steering,
 *     sink rate, or the complete dandelion-glide lifecycle.
 *     Static ASM analysis adds two important corrections. The trigger calls
 *     0x80046cac, which DETACHES the globally carried actor (clears its 0x40
 *     bit and 0x800A655C), then plays positional sound 15. Independently, the
 *     handler tests a quantized radius-40 sphere centered 0x7400 above the
 *     plant and writes interaction latch 11 at 0x800A659E. The propeller
 *     handler reads that latch to extend its usable vertical band, applies
 *     vy -= 512 per accepted update, and clamps at -3072. Thus the retained
 *     ASM contains a dandelion-to-propeller bridge, but no attach writer.
 *
 *   T4 count-4 CANNON PLANT (type 2, handler 0x8005C110):
 *     Two phases: SEATED/aim - the +0x7C lockout counts 17 physics ticks and
 *     0x80048688..0x8004869C pins vx/vy/vz and two auxiliary velocities to 0.
 *     FIRE - timer expiry at 0x800486B8 seeds vy = -8192 (-0x2000); ordinary
 *     gravity adds +256 in the same physics update, so the first retained
 *     frame boundary is -7936 (and the following boundary is -7680). The
 *     launch is fixed-literal, not table-driven. B04 measured a 126,976-unit
 *     rise before the apex, then a dandelion latch-11 slow-fall at vy=+350.
 *
 * ---------------------------------------------------------------------------
 * 3. CARRY + DISCARD (the seed lifecycle around planting)
 * ---------------------------------------------------------------------------
 *   PICK UP: walking onto the seed sets flags 0x4031 -> 0x4039 (transient) ->
 *   0x4071: bit 0x40 = CARRIED. While carried the seed actor is position-locked
 *   to Flik at a fixed offset (~(-1092, +4096, -46) from the player origin).
 *   DISCARD: on release the carry bit clears (0x4071 -> 0x4031) and the seed is
 *   PLACED AT REST at the drop point INSTANTLY - its position is constant from
 *   the release frame on (no toss arc, no bounce; anim field +0x44 stays 0).
 *   The visible "toss" is Flik's own put-down animation; the seed itself has no
 *   discard physics and is immediately crackable again where it was dropped.
 *   (Verified at three releases: 48072, 48705, 48825 - seed pos frozen while
 *   Flik's distance grows.)
 * ============================================================================ */

#include "re_types.h"

#define G_PLANT_SLOTS        0x80090BF0u /* 20 x 0x30; +0x20 = seed-actor backlink */
#define SEED_CRACK_TRIGGER   0x8004af80u /* slam contact: seed+0x6c = 0x00010000   */
#define SEED_CRACK_STATE_OFF 0x6c        /* crack counter (manager 0x8004d494)     */
#define SEED_CARRIED_BIT     0x0040      /* seed flags +0x5c while Flik carries it */

#define TRAMPOLINE_HANDLER   0x8005C58Cu /* type 5: bounce vy ~ -3328 (@0x8005c600) */
#define PROPELLER_HANDLER    0x8005C258u /* type 3: vy ramp -0x100/tick (@0x8005c428)*/
#define DANDELION_HANDLER    0x8005C818u /* type 8: vy=-4096 @0x8005c848, mode 5 */
#define CANNON_HANDLER       0x8005C110u /* type 2: vy pinned 0 (@0x80048690), then  */
#define CANNON_LAUNCH_VY     (-8192)     /* +0x7C expiry seed; gravity -> -7936       */
#define TRAMPOLINE_BOUNCE_VY (-3328)

void brown_seed_plants_refs(void)
{
    volatile unsigned t = G_PLANT_SLOTS ^ SEED_CRACK_TRIGGER ^ TRAMPOLINE_HANDLER ^
                          PROPELLER_HANDLER ^ DANDELION_HANDLER ^ CANNON_HANDLER;
    volatile int v = CANNON_LAUNCH_VY + TRAMPOLINE_BOUNCE_VY +
                     SEED_CRACK_STATE_OFF + SEED_CARRIED_BIT;
    (void)t; (void)v;
}
