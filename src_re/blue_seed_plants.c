/* ============================================================================
 * CORRECTED 2026-08-01 -- the tier->flag-bit model below is WRONG on two of three.
 *
 * 0x800A6590 POWER-FLAGS WORD -- corrected bit map (2026-08-01), derived by decoding the
 * ori/andi immediate at every one of its 26 writers (tools/census_address.py):
 * 
 *   bit 0x01  ground/locomotion state   set 0x8001D5F8, 0x800485D0, 0x80048634; clr 0x80048560
 *   bit 0x02  TRANSIENT per-action flag set 0x8004A7B0 (damage), 0x8004B02C, 0x8005D088;
 *                                       clr 0x80048588 / 0x80048600 (~2 frames). NOT a power.
 *   bit 0x04  transient contact/AI flag set 0x8004A8E0, 0x8004A9E8, 0x8004EB6C, 0x8004FA1C
 *   bit 0x08  CHECKPOINT marker         set 0x80054E90 (ori 8 @0x80054E68); clr 0x80054CB4
 *   bit 0x20  SUPER JUMP (B09)          set 0x800588F8 in contact_pickup_walker, with sfx 75
 *   bit 0x80  GRAIN HARVESTER (C13)     set 0x80051EB0
 * 
 *   respawn_transition_state_handler 0x8005B340 does `andi 0x0020`, i.e. it KEEPS ONLY the
 *   super-jump bit and clears every other flag -- so B09 survives a respawn while the power
 *   slot 0x800A657E is zeroed outright at 0x8005B268.
 * 
 * INVINCIBILITY (B06) AND THE BUBBLE SHIELD (B08) DO NOT USE A FLAG BIT AT ALL. They use the
 * sign-multiplexed slot 0x800A657E: 0x800588D0 writes +400, 0x800589A8 writes -3. No writer of
 * 0x800A6590 exists anywhere in 0x8005C000-0x8005D000, so the blue-plant type handlers do not
 * touch the flags word.
 *
 * The claim that the type-7 handler 0x8005C744 "applies direct effects as bits in
 * 0x800A6590" is FALSE: an alias-aware census of all 26 writers of that word finds none
 * in 0x8005C000-0x8005D000. What the blue tier-1/tier-3 handlers actually do is spawn a
 * CONTACT OBJECT; collecting it is what grants the power, via contact_pickup_walker.
 *
 * Only "0x20 = super jump" from the original triple survives.
 * See ObsidianVault/Canon/Systems/SYS_player_power_slot.md.
 * ========================================================================== */
/* ============================================================================
 * blue_seed_plants.c — the blue seed lane solved + plant expiry (disappearance)
 * ----------------------------------------------------------------------------
 * Decoded 2026-07-03 from the operator's `blue_seed_levels.movie.json`
 * (initial 110486, 3795 frames; windows: B1 110581-111234 invincibility /
 *  B2 111470-112184 health / B3 112491-113272 bubble shield /
 *  B4 113414-114254 super jump). Companion to brown_seed_plants.c.
 *
 * ---------------------------------------------------------------------------
 * CRACK-OPEN — identical to the brown lane (movie-verified)
 * ---------------------------------------------------------------------------
 *   X (jump) pressed 40-60 frames before every plant spawn = Flik butt-slams
 *   the seed; plant slots spawned ~20f later: B1 slot0 type 7 (extra 0x2000),
 *   B2 slot1 type 7 (0x3000), B3 slot2 type 6 (0x0000 bubble shield),
 *   B4 slot3 type 7 (0x4000) — exactly the (blue,count) rows of 0x8007A448.
 *
 * ---------------------------------------------------------------------------
 * WHAT EACH TIER DOES FOR FLIK — the power-up status word 0x800A6590
 * ---------------------------------------------------------------------------
 *   The type-7 handler (0x8005C744) applies DIRECT EFFECTS by setting bits in
 *   the player power-up status word @ 0x800A6590 (u32; several per-frame
 *   maintainer writers: 0x80048564 / 0x80054cb8 / 0x80047aa4 / 0x80049640 /
 *   0x80054e94). Live-observed per window:
 *
 *   B1 count-1 INVINCIBILITY (7/0x2000):  bit 0x02 set. A countdown packed in
 *      the word's upper bytes (+2/+3; observed 0xFF pulse decaying) times it
 *      out — active ~105 frames in the movie.
 *   B2 count-2 HEALTH (7/0x3000):        restores health (retail: full leaf
 *      refill). CAVEAT: the TRUE health store was NOT isolated — both
 *      0x800a7e28 and 0x800a7e2a proved to be HUD leaf-pulse ANIMATION fields
 *      (sole writers 0x8005266c / 0x80052680 / 0x800526dc cycle 0..15 & 0..7).
 *      The real health variable remains a named residual (ties to RCG-021).
 *   B3 count-3 BUBBLE SHIELD (6/0x0000): handler 0x8005C6F0 spawns the shield
 *      contact object (ctor 0x1F, known); bit 0x08 set while shielded. The
 *      upper-byte 0xFF pulses seen during B3 (3 pulses) are LIKELY the
 *      absorbed-hit i-frames (manual: shield takes 3 hits).
 *   B4 count-4 SUPER JUMP (7/0x4000):    bit 0x20 set. Jump impulse becomes
 *      vy = -3520 vs the normal -2816 (+25%); observed on three jumps.
 *
 * ---------------------------------------------------------------------------
 * PLANT EXPIRY — how a plant "disappears" (applies to ALL lanes)
 * ---------------------------------------------------------------------------
 *   Slot lifecycle in slot+0x2e (low byte; high byte 0x20 = render family kept
 *   by the renderer maintainers 0x800216fc / 0x800217bc / 0x80021c00):
 *     spawn: 0x05 (growing)  -> 0x07 (MATURE; bit 0x2 + the dispatcher-active
 *     bit 0x4 that gates the interaction handlers) -> |= 0x40 (WILT — set by
 *     the ONE-SHOT writer 0x8005cecc) -> ~100 frames of wilt animation ->
 *     slot freed (type u16 cleared). Slot init writer: 0x8005bf40 (the
 *     dispatcher/spawn walker).
 *   The slot carries AGE accumulators (+0x1a family, ~+52/frame u16) that the
 *   expiry decision reads. Measured lifetimes (spawn -> slot freed):
 *     brown T1 mushroom ~327f · T2 propeller ~444f · T3 dandelion ~477f ·
 *     blue B1 invincibility ~633f — per-type/lane lifetime constants are a
 *     residual (the mechanism, wilt bit, and setter PC are pinned).
 * ============================================================================ */

#include "re_types.h"

#define G_POWERUP_STATUS   0x800A6590u /* u16 flags. CORRECTED: 0x02 is a transient
                                          per-action flag, 0x08 is the CHECKPOINT marker,
                                          only 0x20 = super jump is a power. Invincibility
                                          and the bubble live in the SLOT 0x800A657E. */
#define POWER_INVINCIBLE   0x02 /* MISNOMER -- retained so the code below still reads;
                                   this bit is NOT invincibility. See the banner. */
#define POWER_SHIELD       0x08
#define POWER_SUPERJUMP    0x20
#define SUPERJUMP_VY       (-3520)   /* vs normal jump -2816 (+25%)                */
#define NORMAL_JUMP_VY     (-2816)
#define PLANT_WILT_SETTER  0x8005ceccu /* one-shot: slot+0x2e |= 0x40 (expiry)     */
#define PLANT_SLOT_INIT    0x8005bf40u /* dispatcher/spawn walker writes +0x2e=0   */
#define PLANT_FLAG_MATURE  0x02
#define PLANT_FLAG_ACTIVE  0x04       /* gates the interaction handler dispatch    */
#define PLANT_FLAG_WILT    0x40

void blue_seed_plants_refs(void)
{
    volatile unsigned t = G_POWERUP_STATUS ^ PLANT_WILT_SETTER ^ PLANT_SLOT_INIT;
    volatile int v = POWER_INVINCIBLE + POWER_SHIELD + POWER_SUPERJUMP +
                     SUPERJUMP_VY + NORMAL_JUMP_VY +
                     PLANT_FLAG_MATURE + PLANT_FLAG_ACTIVE + PLANT_FLAG_WILT;
    (void)t; (void)v;
}
