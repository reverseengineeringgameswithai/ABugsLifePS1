/* RCA a4 (2026-07-09): SUPERSEDED for build purposes — 0x80048138 is byte-matched in the
   shipping build as asm/hand_written/80048138_player_vertical_update.s (config/segments.yml `attempted`;
   validate_build.py SHA-1 PASS). This src_re file is documentation-grade pseudocode,
   retained for its analysis/comments; it is NOT the build unit. */
/* =============================================================================
 * FUNC_80048138  --  player update + movement/animation STATE MACHINE
 * =============================================================================
 * REVERSE-ENGINEERED original code (decompiled from SCUS-94288). Documents the
 * vertical / jump / land / butt-slam state machine and the GROUNDED-flag gate that
 * drives Flik's displayed animation. This is the function the Tier-3 custom-collision
 * hook attaches to (the hook site 0x800495d0 is INSIDE this function, just after the
 * integrator FUNC_8003633C returns for the player). Track-A uses that slot for
 * mod/caves/tier3_collision.c. Track-B/P11 G3-native builds also use that slot for a
 * smaller resident EXE hook emitted by tools/build_g3_native.py from Blender `level_meta`.
 *
 * Function bounds (debugger.functionBounds, confidence "exact"): 0x80048138 .. 0x800498a8,
 * prologue `addiu sp,sp,-256`. Per-frame it runs the input -> movement/animation logic, then
 * calls the integrator FUNC_8003633C (player call site ~0x800495c8), then more housekeeping.
 *
 * P20 scheduler correction (2026-07-06): the direct gameplay-loop caller is the static JAL at
 * 0x8004EFD8 (return address 0x8004EFE0 when hit). The older watched PC 0x8004F7D8 is not the
 * player-update call site. In the minimal Track-B replacement failure P17 seed + [0,73,92],
 * FUNC_80048138 has zero post-spawn hits because the guest leaves the normal scheduler through a
 * render/cull data-bus exception first: COP0_CAUSE=0x41c, ExcCode=7, COP0_EPC=0x8001EB3C
 * (`lw v0,0(s2)`). This is not evidence that FUNC_80048138 itself changed state, that the P11
 * spawn hook disabled the player actor, or that FUNC_80035280 rejected sector-92 planes.
 *
 * -----------------------------------------------------------------------------
 * Player struct (base s1 = 0x800A6500). Offsets VERIFIED LIVE this session:
 *   [+0x04] int32   Y           (X@+0, Z@+8; -Y is up)
 *   [+0x30] int32   vy          vertical velocity (<0 rising, >=0 falling/grounded)
 *   [+0x48] int32   floor_Y     floor-height the controller's coyote/landing checks read.
 *                               Tier-3 substitutes this with OUR floor at the 0x800495dc hook.
 *   [+0x80] s16     air_state   0 = grounded, 1 = jump-takeoff, 2 = airborne/falling,
 *                               3 = butt-slam, (4/5/6 = transient fall/land sub-states)
 *   [+0x82] s16     GROUNDED    grounded = 0x0101, airborne = 0  (see KEY FINDING below)
 *   [+0x88] s16     anim_index  idle 22 (0x16), walk 0, jump-rise 3, jump-fall/slam 4, landing 5
 *   [+0x90] u16     input/flag bits (X edge tested at 0x80048be0 via &0x0080)
 *   [+0x9e] s16     a queued one-shot anim/event id (11 special-cased at 0x800486dc)
 *   [+0x7c]/[+0x7e] s16 countdown timers (decremented at the top of the per-frame update)
 * Globals:
 *   0x80082488  u16  current button state (Cross/X = bit 0x4000) -- read at 0x80048b60
 *   [gp+0x69c]       a coyote-gate guard read at 0x80048bb8 (gp = 0x80081d98)
 *
 * P11 G3-native runtime Spawn/Goal hook (2026-07-06):
 *   tools/build_g3_native.py --level-meta-json replaces the instruction at 0x800495D0
 *   (`jal 0x80037A38`) with `j 0x800810C0`, leaving delay slot 0x800495D4
 *   (`addu a0,s1,zero`) intact. The cave replays `jal 0x80037A38`, then:
 *     - gates to LEVEL01 by stable loaded-DAT marker words, not exact DAT_BASE
 *       (autolayout moved P11 DAT_BASE to 0x80166CE8; older notes used 0x801607F8);
 *     - one-shot writes Flik X/Z from Blender file-space `level_meta.spawn` as runtime <<5;
 *     - writes Flik Y as collision_floor + 3200, matching FUNC_8003633C's final body offset;
 *     - publishes grounded/floor/zero-velocity fields so the first gameplay frame is coherent;
 *     - checks `level_meta.goal` as a simple runtime XZ AABB and runs the LEVEL01 type-1
 *       exit body on hit (see src_re/level_exit_trigger.c).
 *   P12 extends the same cave with one optional non-visible `level_meta.marker` X/Z AABB:
 *     - file-space X/Z/radius are converted to runtime <<5, exactly like the goal;
 *     - entering the marker only sets marker_flag 0x8007F308;
 *     - it does not draw, does not call the exit body, and does not touch native pickup counters.
 *   P13's visible marker indicator does NOT change this hook. The visual side is a size-preserving
 *   LEVEL.DAT floor-tint pass (`native_floor_tint`) over existing FUNC_80010000 primitives near the same
 *   marker; this hook remains the authoritative in-game trigger/flag path.
 *   Validation artifact: build/ABL_g3native_runtime_patch.json. Cold-boot P11 replay:
 *   spawn exact at (197088,5344,492896), goal detected at frame ~5610. Cold-boot P12 marker replay:
 *   marker at file-space (1340,14233), runtime AABB (42880,455456) radius 40960, flag
 *   0x8007F308 set at frame ~4570 with RENDER_C=0 / FUNC_80010000 active.
 *   P13 marker-visual replay additionally records 4 native floor payloads / 42 primitives / 72 vertices
 *   tinted and captures build/g3nm_p13_marker_visual_marker_f4570.png at the same trigger frame.
 *
 * P68 signed-coyote correction (2026-07-11): 0x80048BAC executes signed
 * `slti v0,v0,1024` after computing `[player+0x48] - player_Y`. P67's raised
 * outside floor therefore produced a large negative delta and made repeated Cross presses
 * eligible forever while falling (7 decision hits / 5 jump-state writes at 0x80048BDC).
 * A deep outside floor instead produces a large positive delta. P71 clears only stale
 * grounded collision state at the authored boundary, leaving air_state/Y/VY to the
 * original state machine and +256 gravity (capped at 4096). P70's repeated state-2
 * write re-armed the airborne-Cross sound-27/timer-10 path, whose 0x80048DBC store
 * held VY at zero. The original 0x80049808 fall guard then requests
 * FUNC_8004A700 mode 2 and respawns through the native safe-anchor path.
 *
 * P65 slow-walk regression (2026-07-10, solved ASM + runtime differential):
 *   - L2/R2 are working-word bits 0x0100/0x0200. The exact 0x80048488 sequence tests
 *     BUTTONS & 0x0300 and sets the movement throttle register s5=768.
 *   - actor_skinned_update (0x800563d4) independently tests BUTTONS & 0x0300 at
 *     0x800566cc and selects anim_index 29. OG and ALLMODS both reached index 29 and
 *     advanced player[+0x44], proving the state machine was not frozen.
 *   - Bigland's former P54 one-shot zero of 0x8012C1D0..0x8012E784 destroyed a live
 *     shared post-load workspace. OG had 8,100 nonzero bytes and 30 pointers into the
 *     range; the bad ALLMODS had zero nonzero bytes. Removing only that clear changed
 *     only Flik's pixels in matched frames and restored the visible stride. Exact mixed
 *     ownership of the workspace remains incompletely decoded; see the P65 experiment.
 *
 * ===========================================================================*/

#include <stdint.h>

#define PLAYER_Y      (*(volatile int32_t *)0x800A6504)
#define PLAYER_VY     (*(volatile int32_t *)0x800A6530)
#define PLAYER_FLOOR  (*(volatile int32_t *)0x800A6548)   /* [+0x48] */
#define AIR_STATE     (*(volatile int16_t *)0x800A6580)   /* [+0x80] */
#define GROUNDED      (*(volatile int16_t *)0x800A6582)   /* [+0x82] */
#define ANIM_INDEX    (*(volatile int16_t *)0x800A6588)   /* [+0x88] */
#define BUTTONS       (*(volatile uint16_t *)0x80082488)
#define COYOTE_GUARD  (*(volatile int32_t *)0x80081d98 + 0x69c)  /* [gp+0x69c]; gp=0x80081d98 */
#define BTN_CROSS     0x4000
#define BTN_SLOW_WALK 0x0300  /* L2 0x0100 | R2 0x0200; exact solved-ASM mask */

/* --------------------------------------------------------------------------------------------------
 * KEY FINDING (this session) -- why the Tier-3 custom floor froze Flik's animation:
 *
 * The grounded flag [+0x82] is the master gate of the locomotion/landing animation. Inside THIS
 * function every store to [+0x82] is `sh zero` (CLEAR-only): the jump-takeoff clears it (0x80048be8),
 * the hurt/respawn paths clear it (0x800486c0, 0x800488cc), etc. -- nowhere does FUNC_80048138 SET it.
 * One exact SET producer is now statically pinned. The player call passes a2=player+0x82 at
 * 0x800495B8; FUNC_8003633C writes byte 1 at 0x80036CB8 and again in the 0x80036CC0 delay slot,
 * producing little-endian 0x0101. The raw set condition is a3!=2 && (s0==1 || a3==1); a pristine
 * jump+land observation independently associates that transition with landing. A general census
 * retains unresolved pointer-derived accesses and indirect calls, so this is a proven producer,
 * not a global sole-producer result.
 *
 * CORRECTION HISTORY (2026-08-04 audit): the former approximate PCs 0x80036B90/0x80036CBC/
 * 0x80036CD0 are a load/jump/branch, not stores, and the writes are in the integrator rather than
 * a called collision subroutine. The former ONLY-producer attribution is retracted.
 *
 * Consequence for Tier-3: the custom engine SUPPRESSES native collision, so the integrator never
 * reports contact -> grounded stays 0 forever -> air_state never resets, the landing transition never
 * runs, and Flik is stranded in jump-fall anim 4 (walking slides in that frozen pose). The MOD fix
 * re-publishes [+0x82]=0x0101 from the Tier-3 hook when Flik rests on the custom floor
 * (mod/caves/tier3_collision.c). Live pristine landing trace (level01_lookingdown_flatground.sav):
 *   falling: air_state 2, grounded 0, anim 4
 *   LAND:    Y reaches floor, integrator clamps vy + sets grounded 0x0101 (air_state still 2), anim 5
 *   next:    air_state -> 0 (via 0x80048d00), anim 5 -> 0 -> 22 (idle)
 * -------------------------------------------------------------------------------------------------- */

extern int  FUNC_8003633C(void);   /* movement integrator (Y/collision) */
extern void play_sound(int id, int a1);  /* 0x8005044c */

/* The vertical / jump / land / butt-slam decision, in C. Mirrors 0x80048b40..0x80048d8c. */
void player_vertical_update(void)
{
    int was_grounded = (GROUNDED != 0);              /* 0x80048b4c..b58 (saved to sp+0x48) */

    if (BUTTONS & BTN_CROSS) {                        /* 0x80048b60..b6c: X (Cross) held */
        if (AIR_STATE == 1 || AIR_STATE >= 4) {
            /* 0x80048b7c/b84: mid-jump or transient -> butt-slam progression block (0x80048cd8) */
        } else if (GROUNDED != 0) {
            /* 0x80048b8c..b94: GROUNDED jump path -> takeoff (0x80048bc8 region):
             *   air_state = 1; GROUNDED = 0; anim_index = 3 (jump-rise). */
            AIR_STATE = 1; GROUNDED = 0; ANIM_INDEX = 3;     /* 0x80048bdc/be8/bf4 */
        } else {
            /* 0x80048b9c..bc0: airborne X. Coyote jump only if close to floor AND guard clear: */
            if ((PLAYER_FLOOR - PLAYER_Y) < 1024 && COYOTE_GUARD == 0) {
                AIR_STATE = 1; GROUNDED = 0; ANIM_INDEX = 3;  /* same takeoff path */
            } else {
                /* 0x80048c6c: BUTT-SLAM / airborne handling. If air_state==2 and within 8193 of the
                 * floor -> air_state = 3 (butt-slam). Else (still high) play fall sound 27, set a fall
                 * timer [+0x84]=10, air_state = 4. */
                if (AIR_STATE == 2 && (PLAYER_FLOOR - PLAYER_Y) < 8193)
                    AIR_STATE = 3;                            /* 0x80048c90 -> 0x80048d64 (v0=3) */
            }
        }
    } else {
        /* 0x80048d00: X not held. If grounded, snap air_state back to ground; otherwise advance the
         * jump arc (state 1 -> compute jump velocity -> state 2). This is the path that, once the
         * EXTERNAL grounded flag is set on landing, completes the transition back to idle/walk. */
        if (GROUNDED != 0)
            AIR_STATE = 0;                                    /* 0x80048d10 */
        if (AIR_STATE == 1) {
            /* 0x80048d24..d50: integrate the jump impulse into vy, then air_state = 2 (airborne). */
            AIR_STATE = 2;
        }
        /* 0x80048d58: air_state 5 -> 6 land sub-state progression. */
    }
    /* 0x80048d68..d8c: gravity/anim continuation; commit vy to [+0x30]. */
    (void)was_grounded;
}
