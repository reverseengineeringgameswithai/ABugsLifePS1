---
kind: function
id: FUNC_8004ABF4
aliases: [FUNC_8004ABF4, 0x8004abf4, actor_player_contact_resolver, proximity_updater]
address: 0x8004ABF4
name: actor_player_contact_resolver
status: live_confirmed
confidence: confirmed
source_state: original_game
system:
  - SYS_grain_harvester
calls: []
reads:
  - 0x80090748
  - 0x800A6590
writes:
  - actor_record+0x6E
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - EXP_2026-07-30_phase4_c13_grain_harvester
  - analysis/phase4_c13_harvester_live.json
src_paths:
  - src_re/proximity_updater_8004abf4.c
patch_policy: do_not_touch
---

# FUNC_8004ABF4 - actor/player contact resolver

## Purpose

This per-tick routine iterates the NULL-terminated live actor table at
`0x80090748`, performs actor/player proximity and contact dispatch, and includes
the grain-harvester enemy-contact branch. `0x8004B158/160` reads
`0x800A6590 & 0x80`; `0x8004B204/208` writes the delayed-destroy HP sentinel
`998`. A paired pristine LEVEL01 control reproduces bee HP `4 → 998 →
retirement` while equipped and HP `4`/live after immediate Cross disengagement.

The former “proximity updater of the first actor” framing is superseded. It was
also correctly ruled out as the LEVEL01 exit; the real exit is the collision
sector region-code path. The full contact-family dispatch remains partial.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8004ABF4.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8004ABF4`
- Name: `proximity_updater_8004abf4`
- Original note: `ObsidianVault/Functions/FUNC_8004ABF4.md`
- Source path: `src_re/proximity_updater_8004abf4.c`

## C source excerpt

Source: `src_re/proximity_updater_8004abf4.c`

```c
/* ============================================================================
 * proximity_updater_8004abf4.c — type-6 per-tick proximity updater [PARTIAL DECODE]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : FUNC_8004ABF4 (0x8004abf4)
 * CONFIDENCE       : The proximity MATH is CONFIRMED (disasm + a live test that
 *                    matched the decoded threshold). The function's *role* is NOT
 *                    confirmed — see "WHAT THIS IS NOT" below.
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
 * Net: the proximity math below is real; whether this updater drives anything
 * gameplay-visible (a hazard/catch NPC? a guide?) is UNRESOLVED. Do not cite this
 * as the exit.
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
 * FUNC_8004ABF4 — runs every tick on the actor pointed to by [0x80090748].
 * CONFIRMED through the radius test; the post-test body is not decoded and the
 * function's gameplay role is UNRESOLVED (see header — NOT the level exit).
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
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8004ABF4.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8004ABF4.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8004ABF4.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
