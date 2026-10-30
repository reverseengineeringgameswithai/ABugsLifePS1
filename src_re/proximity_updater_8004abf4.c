/* RCA a4 (2026-07-09): SUPERSEDED for build purposes — 0x8004abf4 is byte-matched in the
   shipping build as asm/hand_written/8004abf4_proximity_updater.s (config/segments.yml `attempted`;
   validate_build.py SHA-1 PASS). This src_re file is documentation-grade pseudocode,
   retained for its analysis/comments; it is NOT the build unit. */
/* ============================================================================
 * proximity_updater_8004abf4.c — actor/player contact resolver [PARTIAL DECODE]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : FUNC_8004ABF4 (0x8004abf4)
 * CONFIDENCE       : The proximity MATH and live-actor-table iteration are
 *                    CONFIRMED. The full family/damage dispatch remains partial.
 * CONTEXT          : LEVEL01 §10 "end-of-level / level exit" investigation
 *                    (ObsidianVault/Systems/LEVEL01 Level-Edit Punchlist.md §10).
 *                    Reached via flik_to_level01_stall.mv.movie.json on the pristine
 *                    Disney-Pixar A Bug's Life (v1.0) disc, isolated DuckStation.
 *
 * ---------------------------------------------------------------------------
 * WHAT THIS IS NOT  (read before reusing — retraction of an earlier claim)
 * ---------------------------------------------------------------------------
 * This was investigated as a candidate for the LEVEL01 *level-exit* trigger and
 * RULED OUT. The actor it watches, [0x80090748] (= 0x8009fd80 in LEVEL01), is a
 * MOVING NPC (its base X drifts 85788 -> 89015 -> 91644 while Flik stands still),
 * not a fixed exit point.
 *
 * A teleport test where Flik was warped onto that moving actor DID flip the
 * transition lever [0x800823a0] from 0 to 2 — but advancing further showed the
 * real outcome: Flik's Y climbed (he was FALLING) and he RESPAWNED at the spawn
 * point (197091,2734,492897) with the scene unchanged. So that [0x800823a0]=2 was
 * a DEATH-FROM-FALLING respawn (the teleport spot was non-floor geometry), NOT a
 * level exit, and is NOT attributable to this function. Method trap recorded:
 * "teleport Flik to a guessed XZ" is confounded by death-from-falling, so
 * "Flik reaches position X => transition lever set" is not evidence of an exit.
 *
 * 2026-07-30 SUPERSESSION: the routine iterates the NULL-terminated live actor
 * table at 0x80090748, not only its first slot. Its 0x8004B158/160 branch reads
 * player power flags 0x800A6590 bit 0x80; the special contact path writes actor
 * HP 998 at 0x8004B208. A pristine LEVEL01 paired control reproduced bee id 13
 * HP 4 -> 998 -> retirement while equipped, versus HP 4/live after immediate
 * Cross disengagement. See SYS_grain_harvester and
 * analysis/phase4_c13_harvester_live.json. The abbreviated C below still models
 * only the entry proximity slice; it is not the full 2792-byte loop.
 *
 * THE REAL LEVEL01 EXIT WAS FOUND (2026-06-24) — see level_exit_trigger.c: it is a
 * collision-sector REGION CODE (sector_table+0x2e == 2, source LEVEL.RAW chunk-32
 * record +0x2c), read by FUNC_80038f38 and dispatched by FUNC_80048138 — a totally
 * different path from this function. §10 is now CLOSED.
 *
 * ---------------------------------------------------------------------------
 * CONFIRMED MATH (disasm of the entry block)
 * ---------------------------------------------------------------------------
 *   s1 = *(u32*)0x80090748;            // watched actor; NULL mid-level => early-out
 *   // actor world position = base (+4/+8/+0xc, s32) + per-tick sub-offset
 *   //                        (+0x64/+0x66/+0x68, s16):
 *   ax = *(s32*)(s1+0x04) + *(s16*)(s1+0x64);
 *   ay = *(s32*)(s1+0x08) + *(s16*)(s1+0x66);
 *   az = *(s32*)(s1+0x0c) + *(s16*)(s1+0x68);
 *   // Flik world position; note the Y is compared with a -7360 bias:
 *   dx = *(s32*)0x800a6500 - ax;
 *   dy = (*(s32*)0x800a6504 - 7360) - ay;
 *   dz = *(s32*)0x800a6508 - az;
 *   r  = *(s16*)(s1+0x6a) + 250;        // trigger radius
 *   if ((dx*dx + dz*dz + dy*dy) < r*r) {   // inside radius...
 *       if (*(s16*)(s1+0x6c) >= 0) {       // ...and enable flag non-negative
 *           /* proceeds — body not fully decoded; role unresolved */
 *       }
 *   }
 *
 * GLOBALS : G_PLAYER_X 0x800a6500, G_PLAYER_Y 0x800a6504, G_PLAYER_Z 0x800a6508,
 *           G_TYPE6_ACTOR_PTR 0x80090748, G_TRANSITION_LEVER 0x800823a0.
 * RELATED : FUNC_8004A700 (type-2 transition initiator),
 *           Gameplay - Warp and Level Transition.md (transition lever model).
 * ============================================================================ */

#include "re_types.h"

#define G_PLAYER_X         (*(volatile s32 *)0x800a6500)
#define G_PLAYER_Y         (*(volatile s32 *)0x800a6504)
#define G_PLAYER_Z         (*(volatile s32 *)0x800a6508)
#define G_TYPE6_ACTOR_PTR  (*(volatile u32 *)0x80090748)
#define PLAYER_Y_BIAS      7360
#define RADIUS_PAD         250

/* The watched actor's per-tick layout (only the fields this updater touches). */
typedef struct {
    u8  _pad04[4];      /* +0x00 */
    s32 base_x;         /* +0x04 */
    s32 base_y;         /* +0x08 */
    s32 base_z;         /* +0x0c */
    u8  _pad10[0x54];   /* +0x10 */
    s16 sub_x;          /* +0x64  per-tick animation offset, added to base_x */
    s16 sub_y;          /* +0x66 */
    s16 sub_z;          /* +0x68 */
    s16 radius;         /* +0x6a  trigger radius (RADIUS_PAD is added) */
    s16 enable;         /* +0x6c  gate: must be >= 0 to proceed */
} Type6Actor;

/*
 * FUNC_8004ABF4 — entry-slice model only. The native routine advances through
 * the live actor table after each candidate and contains the confirmed harvester
 * HP-998 branch described above.
 */
void proximity_updater_8004abf4(void)
{
    Type6Actor *a = (Type6Actor *)G_TYPE6_ACTOR_PTR;
    if (a == 0) return;                 /* NULL mid-level => early-out */

    s32 ax = a->base_x + a->sub_x;
    s32 ay = a->base_y + a->sub_y;
    s32 az = a->base_z + a->sub_z;

    s32 dx = G_PLAYER_X - ax;
    s32 dy = (G_PLAYER_Y - PLAYER_Y_BIAS) - ay;
    s32 dz = G_PLAYER_Z - az;

    s32 r = a->radius + RADIUS_PAD;

    if ((dx * dx + dz * dz + dy * dy) < (r * r)) {   /* inside trigger radius */
        if (a->enable >= 0) {
            /* body not fully decoded; role unresolved (see header) */
        }
    }
}
