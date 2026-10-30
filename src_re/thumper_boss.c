/* ============================================================================
 * thumper_boss.c — the Thumper boss fight: actor, HP, damage law, defeat trigger
 * ----------------------------------------------------------------------------
 * Decoded 2026-07-03 from the operator's COMPLETE `thumper_boss_2.movie.json`
 * (3092 frames, digital; initial_frame 57593) + live poke-falsification.
 * Corrects TWO prior claims: (1) "Thumper fights as the chaser AI @0x80095358"
 * — that address is the CAMERA; (2) "HP/throw/berry bookkeeping live in the
 * boss COMBAT OVERLAY 0x800b4xxx" — REFUTED: the whole damage path is RESIDENT.
 *
 * ---------------------------------------------------------------------------
 * THE ACTOR — Thumper is a REGULAR chunk-31 enemy
 * ---------------------------------------------------------------------------
 *   Scene 2 (LEVEL03 dir). Damageable table during the fight:
 *     slot0 0x8009fe04 id=16  <== THUMPER (record backlink 0x80094a54 = the
 *           chunk-31 spawn record; flags +0x5c = 0x4053: targetable 0x1,
 *           chase-enabled 0x2, BERRY-TOUGH 0x40)
 *     slot1 0x8009fe88 id=10  <== the THROWN MOSQUITO (its own persistent
 *           chunk-31 actor; species callback +0x7c = 0x8004a180)
 *
 *   THE MOSQUITO THROW (traced in the act, movie frame 58953 — operator's
 *   58950..58973 window): the mosquito idles PARKED at a perch (pos == target,
 *   flags = 0x0002). The launch is NATIVE code inside the per-actor update
 *   handler FUNC_800498AC (0x800498ac..0x80049e84 — the same function whose
 *   death-anim branch is documented in enemy_death_permanence.c; the launcher
 *   branch is at ~0x80049c98..0x80049db8):
 *     [0x80049c98]  mosquito+0x70 (VM IP) = 0x80077654   // the FLIGHT program
 *     [0x80049db0+] mosquito+0x34/38/3c   = aim target   // toward Flik's area
 *     flags 0x0002 -> 0x4007                              // live + targetable
 *   The FLIGHT program 0x80077654 (a program-table entry) is a standard VM
 *   seek loop: [op23 params][op13 flags|0x4][op14 anim][op3 wait rnd][op4
 *   random-dir jitter][op6 PARK seek-target] LOOP — the mover-VM then flies it
 *   to the aim point with jitter. So the "throw" = re-seed IP + aim + arm; the
 *   flight itself is ordinary VM motion (pos writers 0x8004cd68... during
 *   flight are the VM integrator).
 *   Thumper's mover-VM program is PARK-IN-PLACE (IP 0x800776ae: [op8 PARK
 *   arrive+stop][op0 LOOP]) — his flight/attack cycle is driven by the species
 *   callback +0x7c = 0x8004a0f4 (0x8004a0f4..0x8004a118, thin dispatcher).
 *   Fight phase/attack counters tick at 0x80090bf2 / 0x80090bf6.
 *
 * ---------------------------------------------------------------------------
 * HP + THE BERRY-TOUGH DAMAGE LAW (resident, inside contact_vs_actor_handler)
 * ---------------------------------------------------------------------------
 *   HP = actor+0x6e (s16). Thumper starts at 50; every berry hit in the movie
 *   decremented it by 2 (50 -> 46 44 42 ... 20), single writer PC 0x800590e8.
 *   The law @0x8005905c (the berry-tough branch of contact_vs_actor_handler):
 *
 *     hp = enemy[+0x6e];
 *     if (hp >= 100) skip;                 // regular enemies park 999 here ->
 *                                          // they never take this path (they
 *                                          // use the hit-marker/quota path)
 *     cls = berry_record[+0x2c];           // per-berry DAMAGE CLASS byte
 *     switch (cls) {
 *       case 0:   hp -= 2; break;
 *       case 1:   hp -= 99; break;         // near-instakill class
 *       case 12:  hp -= 2; break;
 *       case 127: hp -= 4; break;
 *       case 128: hp -= 3; break;
 *       default:  hp -= 1; break;
 *     }
 *     enemy[+0x6e] = hp;                   // sh @0x800590e4/0x800590e8
 *
 *   This is ALSO the long-open "per-berry damage vs berry-tough enemies" table
 *   (the worm/wall_worm take the same path). NO overlay involvement.
 *
 * ---------------------------------------------------------------------------
 * DEFEAT TRIGGER — HP <= 20 (causally proven)
 * ---------------------------------------------------------------------------
 *   Live poke test at the fight: hp=21 -> nothing; hp=20 -> within a few frames
 *   the defeat-FSM flag 0x80090bee flips to 2, written by the setpiece-actor
 *   INIT block @0x8004db44 (the 0x8004dbxx sibling of setpiece_spawn_init that
 *   populates 0x80090bc0..0x80090bee) => the previously-decoded defeat chain
 *   runs: 0x80090bee -> finale FUNC_8004DA94 -> the scripted end-of-fight
 *   approach/bird setpiece (FUNC_8004DD98 on actor 0x80090bc0).
 *   FIGHT MATH: 50 -> 20 at -2/hit = **15 berry hits to defeat Thumper**.
 *   (Movie confirmed: ~15 damage events between first hit and the FSM flip.)
 *
 * ---------------------------------------------------------------------------
 * METHOD NOTES
 * ---------------------------------------------------------------------------
 *   - The movie gave deterministic hit anchors (first damage ~abs frame 59025);
 *     snapshots + accessLog write-watch on +0x6e pinned HP and the writer.
 *   - GOTCHA: a v1/v2 movie replay CAN DRIFT when the run is paused heavily by
 *     debugger breakpoints/watches mid-playback (run 2 fell ~2 hits behind and
 *     the recorded kill never landed) — poke-falsification closed the defeat
 *     threshold instead (and is stronger evidence anyway).
 * ============================================================================ */

#include "re_types.h"

#define THUMPER_ID            16          /* chunk-31 type-word low byte          */
#define BOSS_HP_OFF           0x6e        /* actor+0x6e s16; regular enemies park
                                             999 here (the hit marker)            */
#define THUMPER_HP_START      50
#define THUMPER_HIT_DELTA     (-2)        /* class-0 berry vs berry-tough         */
#define THUMPER_DEFEAT_HP     20          /* hp <= 20 -> defeat FSM (poke-proven) */
#define THUMPER_HITS_TO_KILL  15
#define BERRY_TOUGH_DMG_DISPATCH 0x8005905cu /* class byte = berry_record[+0x2c]  */
#define G_DEFEAT_FSM          0x80090beeu    /* 2 = defeat chain engaged           */
#define THUMPER_DRIVER_CB     0x8004a0f4u    /* species callback (flight/attack)   */
#define MOSQUITO_DRIVER_CB    0x8004a180u    /* thrown-mosquito callback           */

void thumper_boss_refs(void)
{
    volatile int t = THUMPER_ID + BOSS_HP_OFF + THUMPER_HP_START + THUMPER_HIT_DELTA +
                     THUMPER_DEFEAT_HP + THUMPER_HITS_TO_KILL;
    volatile unsigned u = BERRY_TOUGH_DMG_DISPATCH ^ G_DEFEAT_FSM ^
                          THUMPER_DRIVER_CB ^ MOSQUITO_DRIVER_CB;
    (void)t; (void)u;
}
