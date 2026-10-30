/* ============================================================================
 * dot_guide_npc.c — Dot, the LEVEL01 guide NPC: path, guide law, wait behavior
 * ----------------------------------------------------------------------------
 * RCG-032 (created + solved 2026-07-03). Live decode on level01.sav.
 *
 * WHO SHE IS (in engine terms):
 *   - A regular chunk-31 actor: LEVEL01 record type 0x070e (unique, 1 per
 *     level), actor id 14 @ 0x800a0a64 in level01.sav; registered in the
 *     damageable table with the TARGETABLE BIT CLEAR (+0x5c bit 0x1 = 0)
 *     -> berries can't hit her, homing ignores her (friendly NPC).
 *   - CORRECTION: the AI-movement sweep's "mosquito = path-patrol" row was
 *     actually DOT (find_actor picked the id-14 actor in mosquito.sav = her).
 *     The real mosquito enemy is the id-10 chaser (the one Thumper throws).
 *
 * ---------------------------------------------------------------------------
 * HER PATH — LEVEL.DAT record @ file +0x468 (type 1, 104 waypoints)
 * ---------------------------------------------------------------------------
 *   Header {u16 count=0x68(104), u16 type=1}; waypoints at +0x46c, stride 0xc,
 *   s32 XYZ in FILE coords (runtime = <<5). The path runs from Flik's spawn
 *   area (159296,-40192,528512) across the level to (-195552,-183200,-97440)
 *   — terminating at the LEVEL01 EXIT region (sector 177). Live-verified:
 *   her current move-target (+0x34) == waypoint[wp_idx] <<5 exactly.
 *   (This is the rec1 path the old mover-relocation experiment moved.)
 *
 * ---------------------------------------------------------------------------
 * THE GUIDE LAW — the proximity-gated path program (mover-VM)
 * ---------------------------------------------------------------------------
 *   Her VM program is the shared path-follower at 0x800775e4/0x800775fa:
 *     0x800775fa  op5   next path waypoint -> target
 *     0x800775fc  op10  PARK (motion wait-mode)
 *     0x800775fe  op17  s3 = dist(FLIK) < 1200         ; ~38,400 runtime units
 *     0x80077602  op9   if (s3>0) goto 0x800775fa      ; advance while near
 *     0x80077606  op0   LOOP -> 0x800775fc
 *   => SHE ONLY ADVANCES ALONG THE PATH WHILE FLIK IS WITHIN THE RADIUS.
 *   Live: Flik 53k away -> she finishes the current leg and PARKS (wp frozen
 *   240f+); Flik beside her -> wp advances (1->6 over ~400f), she walks legs
 *   of the path with Flik in tow (~147 units/frame).
 *
 * ---------------------------------------------------------------------------
 * "WHAT IF FLIK TAKES TOO LONG?"
 * ---------------------------------------------------------------------------
 *   Nothing punitive: the op17 wait-loop has NO timeout — she waits at the
 *   current waypoint INDEFINITELY. While parked she emits a periodic idle cue:
 *   effect/sound helper 0x8005044c(id=7, &her_pos) fired from the per-actor
 *   update handler (ra 0x80049eb4, ~every 50 frames) — the visible/audible
 *   "waiting/beckoning" cue. She never path-regresses toward Flik.
 *
 * ---------------------------------------------------------------------------
 * VOICE LINES (operator ask) — trigger path partially bounded
 * ---------------------------------------------------------------------------
 *   Her callouts do NOT go through sfx_dispatch (0x80050994: zero calls in
 *   guiding + waiting windows). The only per-actor audio/FX trigger caught is
 *   the 0x8005044c(id 7) periodic cue above (0x8005044c ids feed the effect+
 *   sound spawner). Full voice attribution needs the SPU key-on trace — the
 *   long-standing GAP-0031 residual (named, not yet traced).
 *
 * RESIDUALS: end-of-path/arrival behavior (a waypoint-poke test perturbed her
 * leg state; needs a natural full walk); the exact op17 distance scale; the
 * SPU voice key-on; whether other levels' guide NPCs (id-14 class records)
 * reuse the same program.
 * ============================================================================ */

#include "re_types.h"

#define DOT_RECORD_TYPE     0x070e      /* chunk-31 type word (unique in LEVEL01) */
#define DOT_ACTOR_ID        14
#define DOT_PATH_FILE_OFF   0x468       /* LEVEL.DAT: {cnt 104, type 1} + wps @+0x46c */
#define DOT_PATH_WAYPOINTS  104
#define DOT_GUIDE_PROGRAM   0x800775fau /* op5/op10/op17(1200)/op9/op0 loop        */
#define DOT_FOLLOW_RADIUS   1200        /* op17 operand (~38,400 runtime)          */
#define DOT_WAIT_CUE_ID     7           /* 0x8005044c(7,&pos) every ~50f while parked */

void dot_guide_npc_refs(void)
{
    volatile unsigned t = DOT_GUIDE_PROGRAM ^ (DOT_RECORD_TYPE + DOT_ACTOR_ID +
        DOT_PATH_FILE_OFF + DOT_PATH_WAYPOINTS + DOT_FOLLOW_RADIUS + DOT_WAIT_CUE_ID);
    (void)t;
}
