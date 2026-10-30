/* ============================================================================
 * enemy_ai_programs.c — per-enemy AI movement: mover-VM programs + the chase law
 * ----------------------------------------------------------------------------
 * Enemy AI movement decode (2026-07-03). Static VM-program disassembly (ISA from
 * FUNC_8004C13C, GAP-0033) + live behavioral sweep over 18 saves + a falsification
 * test. Complements enemy_actor_spawn.c (spawn) and enemy_death_permanence.c (death).
 * OPERATOR ground truth confirmed: "some of them have aggro, some do not."
 *
 * HEADLINE: every regular enemy is driven by the mover-VM (FUNC_8004C13C). Its AI is
 * a small RESIDENT bytecode program (0x8007745c..0x80077af6; per-enemy IP at
 * actor+0x70). "Aggro" exists at THREE distinct levels:
 *   (1) CHASE  — a GLOBAL feature of the VM's motion phase (0x8004c8ac+): if the
 *       actor's flags (+0x5c) have BIT 0x2 set and Flik is within a per-object
 *       radius, the motion goal is swapped from the wander/path target to FLIK's
 *       live position (Y offset −2048). LIVE-FALSIFIED: suppressing bit 0x2 on the
 *       chasing spider flipped pursuit +0.93 -> −0.89 (it wandered away).
 *   (2) PROXIMITY TRIGGER — op17 in a program: s3 = dist(Flik) < R; a following
 *       op9 branch reacts (advance path / jump to a strike section).
 *   (3) CONTACT RING — in the motion phase, an actor PARKED on op17/op18 whose
 *       dist²(Flik) < 0x9c3f (~200 units, ~6400 runtime) gets IP += 6 = an
 *       unconditional jump into its strike/attack section.
 *
 * ---------------------------------------------------------------------------
 * THE PHASE-2 MOTION-APPLY (0x8004c8ac..0x8004caa4) — where movement happens
 * ---------------------------------------------------------------------------
 *   Programs PARK on a motion opcode (stream 5..20 -> phase-2 mode = stream−5);
 *   each frame the motion-apply advances position toward the target (+0x34/38/3c)
 *   at fixed speed s4 (program[+0x14]<<4), heading-rotated via the sine table.
 *   - mode 2 arrive-test: dist² < s4² -> IP += 2 (program continues); else wait 10.
 *   - CHASE GATE @0x8004c930: if (flags+0x5c & 0x2) && mode < 3:
 *         if dist²XZ(actor_accum +0x28/+0x30, Flik) < chaseR²   // chaseR from
 *             goal = (Flik.X, Flik.Y−2048, Flik.Z)              // op16 scratch:
 *                                                               // 0x3e8=1000/0x190=400
 *   - CONTACT @0x8004c9b0: if parked op is 17/18 and dist²(actor, Flik) < 0x9c3f
 *         -> IP += 6 (jump into the strike section), wait cleared.
 *
 * ---------------------------------------------------------------------------
 * PER-ENEMY PROGRAMS (disassembled; resident, per-actor IP seeded at spawn)
 * ---------------------------------------------------------------------------
 * A) WANDER+CHASE class — loop: [op3 wait rnd(0..63)+32][op4 random-direction
 *    step][op6/18 PARK seek-target] -> LOOP. Chase via the global bit-0x2 gate.
 *      spider       prog 0x80077470 (wander loop 0x77492; init CALL sub7, wait 20)
 *      dragonfly    prog 0x8007755c (pure wander loop 0x77568)
 *      bee          prog 0x80077578 (wander parked on op18 -> contact ring = strike)
 *      earthworm    prog 0x800775c8 (wander)
 *      huge_spider  prog 0x80077674 (wander; lives on a platform — Flik must jump
 *                                    up (X+UP) to engage it)
 *      Redbug       prog 0x80077690 (wander)
 *      Horsefly     prog 0x800776d0 (wander -> falls into the two-speed section)
 *      shell_bug /  prog 0x800776ec: TWO-MODE wander — op16 chaseR=0x3e8 fast
 *      canyon_bug   wander, noise coin-flip (op15 &0x1) -> op16 chaseR=0x190 slow
 *                   wander, coin-flip back (canyon_bug also has path/step sections
 *                   at 0x77850+ with op20 branches + CALL sub5).
 * B) PATH-PATROL + PROXIMITY class — loop: [op5 next waypoint][op10 PARK]
 *    [op17 dist<1200][op9 if s3 goto op5] -> LOOP: the actor only advances along
 *    its LEVEL.DAT waypoint path while Flik is within 1200; else it parks.
 *      mosquito     prog 0x800775e4 (radius 1200)
 *      (bee/earthworm's program block also contains this section at 0x775fa —
 *       shared code; which section runs depends on the seeded IP/state.)
 * C) AMBUSH/POPUP class (stationary; "no aggro movement" — the no-chase enemies):
 *    loop: [anim][op13 flags][op2 wait][op8 PARK arrive+stop][op17 dist<R]
 *    [op9 if s3 goto STRIKE] -> LOOP; STRIKE: flags|=0x40 (berry-tough bit!),
 *    op12 CALL sub8 (native strike action), strike anim, waits, loop back.
 *      worm         section 0x800779f6: op17 radius 700;  flags mask |0x08c0
 *      wall_worm    section 0x80077a58: op17 radius 1200; flags mask |0x08c0
 *      pill_bug     section 0x8007799c: gated by op25 (GLOBAL FLAG, not proximity)
 *                   -> curl/uncurl cycle (helper(27) calls, anim 1,18 / 1,24)
 *    NOTE: their op13 masks (&0xf73f|0x08c0) leave bit 0x2 CLEAR -> the global
 *    chase never engages = stationary. The 0x40 they set on strike is the
 *    berry-tough bit (see enemy_death_permanence.c) — VM-managed!
 * D) grasshopper  prog 0x8007760c: tiny [op23][op12 CALL sub3][anim][op7 PARK
 *    arrive-test][op22 DONE] — target/behavior set natively via CALL sub 3; its
 *    observed chase comes from the global bit-0x2 gate while parked on arrive-test.
 *
 * ---------------------------------------------------------------------------
 * BEHAVIORAL SWEEP (18 saves; pursuit = mean cos(step, dir-to-Flik))
 * ---------------------------------------------------------------------------
 *   Chase episodes observed live: spider +0.93 (idle phase!), grasshopper +0.78,
 *   huge_spider +0.83, canyon_bug +0.64, dragonfly_2 +0.72, Horsefly/Redbug closed
 *   ~16-20k in phase tests. STATIONARY (0 movement both phases): worm, pill_bug,
 *   wall_worm. bee/mosquito/earthworm/shell_bug: patrol/wander episodes dominate
 *   (state-dependent; chase engages by proximity + state).
 *   FALSIFICATION: suppressing flags bit 0x2 per frame on the chasing spider:
 *   pursuit +0.93 -> −0.89, closing −2931 -> opening +10331. Chase gate proven.
 *
 * ---------------------------------------------------------------------------
 * MODDING LEVERS (no mod built — RE only; these are EXE data edits)
 * ---------------------------------------------------------------------------
 *   - op17 AGGRO RADIUS operands (e.g. worm 700 @0x80077a0a, wall_worm 1200
 *     @0x80077a72, mosquito-path 1200 @0x80077600) — u16, byte-editable.
 *   - op16 CHASE RADIUS scratch (0x3e8/0x190 in the 0x776ec program).
 *   - op2/op3 wait operands = patrol cadence; op23 params = anim/speed bytes.
 *   - actor flags bit 0x2 = chase on/off (runtime or program op13 masks).
 *   - program table 0x80077af8 (40 ptrs) / record byte 13 selects the program.
 * ============================================================================ */
/* ============================================================================
 * D20 HOPPER (boss) confirmed to use this SAME chase gate — 2026-08-03
 * ----------------------------------------------------------------------------
 * Live-traced from movies/Phase4/Interpreter/Hopper_white_berry_death.movie.json
 * (Phase 4, analysis/phase4_d20_hopper.json's AGGRO_CHASE_MECHANISM_CONFIRMED
 * section). Hopper is chunk-31 actor id=22 (NOT the archived Enemy_AI_state_
 * machine.md's claimed 0x80095358 — that address is the camera). His own
 * position writes (X @0x8004cd64, Z @0x8004cdcc) land inside FUNC_8004C13C, the
 * same mover-VM this file documents. His flags(+0x5c) bit 0x2 read SET at every
 * one of 7 sampled frames during active pursuit (distance oscillating 8261-
 * 46299 units as he closes to throwing range and backs off) and CLEAR right
 * before his scripted bird-nest defeat cinematic. No new mechanism — this file's
 * existing chase-gate documentation already covers him; his own program pointer
 * (actor+0x70 = 0x800778cc at the sampled instant) falls in the long unlabeled
 * block after `redbug @ 0x80077690` in analysis/vm_programs.md, not yet walked
 * start-to-end or given a species name.
 * ============================================================================ */

#include "re_types.h"

#define VM_MOTION_APPLY      0x8004c8acu /* phase-2 motion + chase + contact ring   */
#define VM_CHASE_GATE_BIT    0x0002      /* actor flags +0x5c: chase-enable         */
#define VM_CONTACT_RING_SQ   0x9c3f      /* dist² for op17/18-parked strike jump    */
#define VM_PROGRAM_REGION    0x8007745cu /* ..0x80077af6 resident AI programs       */
#define VM_PROGRAM_TABLE     0x80077af8u /* 40 pointers; end-exclusive 0x80077b98   */
#define AGGRO_RADIUS_WORM      700
#define AGGRO_RADIUS_WALLWORM  1200
#define AGGRO_RADIUS_MOSQUITO  1200

void enemy_ai_programs_refs(void)
{
    volatile unsigned t = VM_MOTION_APPLY ^ VM_PROGRAM_REGION ^ VM_PROGRAM_TABLE ^
        (VM_CHASE_GATE_BIT + VM_CONTACT_RING_SQ +
         AGGRO_RADIUS_WORM + AGGRO_RADIUS_WALLWORM + AGGRO_RADIUS_MOSQUITO);
    (void)t;
}
