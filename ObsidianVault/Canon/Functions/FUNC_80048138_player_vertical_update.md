---
kind: function
id: FUNC_80048138
aliases: [FUNC_80048138, 0x80048138]
address: 0x80048138
name: player_vertical_update
status: static_seen
confidence: medium
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - src_re/player_update_80048138.c
src_paths:
  - src_re/player_update_80048138.c
patch_policy: unknown
---

# FUNC_80048138 - player vertical update

## Purpose

Generated from C source coverage. The original-game behavior should be refined manually with call/read/write links.

## Known behavior

See the exact source excerpt below. Preserve `UNKNOWN`, `LIKELY`, and `TODO` labels from the source comments.

## Address / identity

- Address: `0x80048138`
- Name: `player_vertical_update`
- Source path: `src_re/player_update_80048138.c`

## C source excerpt

Source: `src_re/player_update_80048138.c`

```c
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

/* --------------------------------------------------------------------------------------------------
 * KEY FINDING (this session) -- why the Tier-3 custom floor froze Flik's animation:
 *
 * The grounded flag [+0x82] is the master gate of the locomotion/landing animation. Inside THIS
 * function every store to [+0x82] is `sh zero` (CLEAR-only): the jump-takeoff clears it (0x80048be8),
 * the hurt/respawn paths clear it (0x800486c0, 0x800488cc), etc. -- nowhere does FUNC_80048138 SET it.
 * The SET to grounded (0x0101) is produced EXTERNALLY by the collision-resolution path under the
 * movement integrator FUNC_8003633C (see src_re/movement_integrator_8003633c.c), ONLY when native
 * collision reports ground contact. (A halting/access write-watch on 0x800A6582 during a pristine
 * jump+land flags the grounded SET inside the FUNC_8003633C region around 0x80036cbc/0x80036cd0/
 * 0x80036b90 -- exact store instruction not pinned: this debugger fork's data-access PC is imprecise,
 * and the write lands in a collision subroutine the integrator calls.)
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
```

## Evidence

- Source: `src_re/player_update_80048138.c`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Phase 4 A03 jump law (2026-08-03)

Shipping ASM, the retained B09 capsule, and same-anchor pristine controls now
establish the normal jump recurrence.

- Cross admission sets state 1, grounded 0, animation 3, and impulse -3072.
- Player power flag +0x90 bit 0x20 selects impulse -3776.
- The common airborne tail adds 256 per gameplay update and caps descent at 4096.
- State-1 release applies the -800/384 threshold, arithmetic half, and common
  tail described in `src_re/jump_state_80048138.c`.
- The normal measured apex gains are 6336 at one held tick, 11520 at four,
  17024 when released at tick 11, and 16896 when held through tick 12.
- The tick-11 result is a real 128-unit micro-optimum, not measurement noise.
- The movement integrator and swept-plane passes own ceiling/floor response and
  are the sole producer of grounded 0x0101.

The exact evidence and bounded geometry residual are in
[[EXP_2026-08-03_phase4_a03_jump]].

## Phase 4 A03 natural ceiling confirmation (2026-08-03)

A pristine Interpreter replay joined the jump update to an accepted native ceiling collision. The uninterrupted control reproduced the 16,896 full-hold recurrence after removing its 3,200 entry displacement. A second held jump rose only 10,880.

At frame 162720, the resolver retained plane 0x800f1d04 in sector 166, normal [-777, 16363, -288], after the segment crossed from d_start=219 to d_end=-1827 and the polygon test returned true. The actor then descended and landed. Thus natural ceiling geometry truncates the integrated upward path; it does not redefine the local jump recurrence. Evidence: analysis/phase4_a03_ceiling_movie_v2.json.

## The collision region-code dispatch (F01, 2026-08-05)

Beyond the vertical/jump/land machine documented above, this function hosts the
**collision region-code dispatch** at `0x80049640..0x800497A0` — the mechanism by
which authored collision sectors complete a scene or damage the player. Five arms
(codes 0–4), gated on the GROUNDED flag `player+0x82` via `FUNC_80038F38` and
guarded single-shot by the transition request word
[[MEM_800823A0_scene_transition_request]]. Codes 1/4 call the player damage
handler; codes 2/3 request scene completion. The `sp+0x50` commit flag
(zero-initialised at `0x800481BC`, set only by arms 1 and 2) re-commits position
from the previous-position mirror and clears `player+0x82` at the join.

83 pinned instruction words: `tools/phase4_f01_objective_lifecycle.c` ·
[[EXP_2026-08-05_phase4_f01_objective_lifecycle]].

