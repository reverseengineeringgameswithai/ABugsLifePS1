/* ============================================================================
 * level_exit_trigger.c — LEVEL01 end-of-level / level-exit trigger [SOLVED]
 * ----------------------------------------------------------------------------
 * Punchlist §10 "End-of-level point / level exit" — the long-standing
 * "biggest real gap". CLOSED 2026-06-24 (runtime, isolated DuckStation, pristine
 * Disney-Pixar A Bug's Life v1.0) using the operator save `level01_end_of_stage.sav`
 * (Flik standing just short of the exit; "walk forward to trigger it").
 *
 * HEADLINE
 *   The level exit is a per-sector REGION CODE in the COLLISION sector table.
 *   When Flik walks into a sector whose region code == 2, the type-1 transition
 *   fires (sets the transition lever [0x800823a0]=1) → the level tears down.
 *   In LEVEL01 exactly ONE sector carries code 2: collision sector 177.
 *
 * THE CHAIN (all live-confirmed)
 *   per-tick  FUNC_80048138 (scene/exit handler; holds Flik base in s1=0x800a6500)
 *     -> v1 = FUNC_80038f38(0, &Flik[+0x82])        // query current sector's code
 *     -> if (v1==0) no trigger
 *        if (lever[0x800823a0]!=0) already transitioning -> skip
 *        switch (v1):                               // region-code -> transition kind
 *           1 -> FUNC_8004A700(...,a3=1)            // type-2 initiator (other levels)
 *           2 -> lever[0x800823a0]=1; fade[0x80082470]=23; FUNC_80050994(58,0)  // <-- LEVEL01 EXIT
 *           3 -> ... ; 4 -> ...                     // other region kinds (other levels)
 *
 * FUNC_80038f38 (the trigger query) — returns the current sector's region code:
 *     short FUNC_80038f38(int player_idx, char *flik_p82) {
 *         if (*flik_p82 != 1) return 0;             // gate byte [Flik+0x82] must be 1
 *         int sector = G_CUR_SECTOR[player_idx];    // [0x80090560 + player_idx*20]
 *         return SECTOR_TABLE[sector].region_code;  // halfword @ sector_base + 0x2e
 *     }
 *   SECTOR_TABLE = 0x800a7e48, stride 0x30 (built from LEVEL.RAW chunk 32 by the
 *   collision converter); region_code at +0x2e. G_CUR_SECTOR (0x80090560) is the
 *   player's current collision sector, maintained per-tick by FUNC_80038090 (the
 *   point-in-polygon "which region am I in" updater).
 *
 * DISC SOURCE (offline-located, byte-confirmed)
 *   The region code is STATIC, baked in LEVEL.RAW chunk 32. Sector source records:
 *     chunk-32 decompressed local 0x36570 (global 0xCD248 in the full RAW decode),
 *     stride 0x4c; origin XYZ @ +0x08/+0x0c/+0x10 (stored value = runtime >> 5);
 *     REGION CODE @ +0x2c (word) -> built into runtime SECTOR_TABLE +0x2e.
 *   LEVEL01 sector 177 record @ chunk-32-local 0x36570 + 177*0x4c (global 0xD06D4):
 *     origin (-5094,-5309,-3901) == runtime (-163008,-169888,-124832) >> 5,
 *     +0x2c word = 2.  It is the ONLY one of the 189 real records with code 2.
 *   => to MOVE the exit: set +0x2c=2 on the desired sector record (clear the old),
 *      recompress chunk 32, rebuild via tools/build_autolayout_disc.py.
 *   RELOCATION PROVEN IN-GAME (2026-06-24): tools/edit_sector_region_code.py moved
 *      the LEVEL01 exit 177->108; on the rebuilt disc the runtime table read
 *      [108]+0x2e=2 / [177]+0x2e=0 and the same forward-walk that is inert on
 *      pristine (99->108) ended the level at sector 108 (lever->1, level teardown).
 *
 * EVIDENCE
 *   - Held "forward" from the at-exit save: lever[0x800823a0] 0->1, writer PC
 *     0x800496dc (the type-1 store inside FUNC_80048138), at Flik in sector 177.
 *   - Breakpoint in the type-1 block: reached with s1=0x800a6500, via the
 *     `beq v1,2,0x800496c4` dispatch where v1 = FUNC_80038f38 return.
 *   - Sector scan: runtime SECTOR_TABLE[i]+0x2e == 2 only for i==177; chunk-32
 *     source +0x2c == 2 only for record 177; origins match runtime>>5 exactly.
 *   - OUTCOME (legitimate walk-in, NOT teleport): level torn down
 *     (active[0x800822f8] 1->0, scene[0x80082504] 1->0), Flik did NOT respawn at
 *     spawn -> a real transition (distinguishes it from the death-from-falling
 *     respawn that the earlier teleport test produced; see
 *     proximity_updater_8004abf4.c, which was RULED OUT as the exit).
 *   - The post-teardown stall at scene=0 is the documented GAP-0035B limit (the
 *     next-level *load* needs shell-phase destination/resource sequencing that a
 *     raw gameplay state does not drive); it does not affect the trigger finding.
 *
 * GLOBALS
 *   G_PLAYER_X/Y/Z 0x800a6500/04/08 · G_FLIK_GATE 0x800a6582 ([Flik+0x82])
 *   G_CUR_SECTOR   0x80090560 (player_idx*20) · SECTOR_TABLE 0x800a7e48 (stride 0x30)
 *   G_TRANSITION_LEVER 0x800823a0 · G_FADE_COLOR 0x80082470 · G_LEVEL_ACTIVE 0x800822f8
 * RELATED: Gameplay - Warp and Level Transition.md (Pass-5), FUNC_8004A700,
 *          proximity_updater_8004abf4.c (the ruled-out type-6 lead),
 *          tools/edit_collision_sector.py, ground-sculpt-collision-disc-edit memory.
 * ============================================================================ */

#include "re_types.h"

#define G_FLIK_BASE         0x800a6500
#define G_FLIK_GATE         (*(volatile u8  *)0x800a6582)   /* [Flik+0x82] */
#define G_CUR_SECTOR_BASE   0x80090560                       /* + player_idx*20 */
#define SECTOR_TABLE_BASE   0x800a7e48
#define SECTOR_STRIDE       0x30
#define SECTOR_REGION_CODE  0x2e                             /* halfword */
#define G_TRANSITION_LEVER  (*(volatile s16 *)0x800823a0)
#define G_FADE_COLOR        (*(volatile s16 *)0x80082470)

#define REGION_NONE         0
#define REGION_TYPE2_EXIT   1   /* -> FUNC_8004A700 type-2 initiator (other levels) */
#define REGION_TYPE1_EXIT   2   /* -> sets the lever = 1 : the LEVEL01 level exit   */

extern void FUNC_8004A700(s32 a0, s32 a1, void *a2, s32 a3);
extern s32  FUNC_80050994(s32 sfx, s32 a1);   /* level-complete jingle/SFX (a0=58) */

/* FUNC_80038f38 — return the region code of the sector the player is standing in.
 * a0 = player index (0 = Flik); a1 = &Flik[+0x82] (a gate byte that must be 1). */
s16 sector_region_code_80038f38(s32 player_idx, const u8 *flik_gate)
{
    if (*flik_gate != 1)                       /* gate not armed -> no trigger */
        return REGION_NONE;

    s32 sector = *(volatile s32 *)(G_CUR_SECTOR_BASE + player_idx * 20);
    s16 *rec   = (s16 *)(SECTOR_TABLE_BASE + sector * SECTOR_STRIDE + SECTOR_REGION_CODE);
    return *rec;                               /* LEVEL01 exit sector (177) -> 2 */
}

/* The relevant slice of FUNC_80048138 (the scene/exit handler) — the dispatch
 * that turns a region code into a transition. (Surrounding bookkeeping omitted.) */
void scene_exit_dispatch_80048138_slice(void)
{
    s16 code = sector_region_code_80038f38(0, (const u8 *)&G_FLIK_GATE);
    if (code == REGION_NONE)
        return;                                /* not standing in a trigger sector */
    if (G_TRANSITION_LEVER != 0)
        return;                                /* a transition is already in flight */

    switch (code) {
    case REGION_TYPE2_EXIT:                     /* code 1 (used by other levels) */
        FUNC_8004A700(0, 0, /*&sp[44]*/ (void *)0, /*a3=*/1);
        break;
    case REGION_TYPE1_EXIT:                     /* code 2 = LEVEL01 EXIT */
        G_TRANSITION_LEVER = 1;                 /* sh v0(=1), 0x23a0  -> level tears down */
        G_FADE_COLOR       = 23;
        FUNC_80050994(58, 0);                   /* level-complete jingle/SFX */
        break;
    /* case 3, 4: other region kinds in other levels */
    }
}

/* ============================================================================
 * 2026-06-27 — REPLICATED in the Tier-3 custom engine (Track A "goal/exit")
 * ----------------------------------------------------------------------------
 * The Tier-3 levels SUPPRESS the native collision sectors, so the native
 * per-tick FUNC_80048138 never sees an exit-region sector (G_CUR_SECTOR isn't
 * maintained) — walking the custom geometry can't fire the native exit. So the
 * custom engine detects an EXIT VOLUME (blob data) itself and REPLICATES the
 * region-code-2 body from a cave (mod/caves/tier3_walls.c, Track A):
 *
 *     G_TRANSITION_LEVER (0x800823A0) = 1;
 *     G_FADE_COLOR       (0x80082470) = 23;
 *     FUNC_80050994(58, 0);
 *
 * LIVE-CONFIRMED on the cold-boot disc: reaching the exit volume runs the
 * native FADE-OUT (the screen fades to black over ~23 frames = G_FADE_COLOR
 * counting 23->0) — the level-exit transition. KEY FINDING: setting the
 * LEVER ALONE (0x800823A0=1) does NOTHING (its consumer is gated behind the
 * suppressed native scene state); the FADE + the FUNC_80050994(58,0) CALL are
 * what actually drive the transition. (An earlier attempt poking only the
 * lever sat at 1 with no effect.) The post-fade NEXT-SCENE LOAD does not
 * advance in a standalone custom level (no next level wired + suppressed scene
 * manager) — that is multi-level-progression work, separate from the exit
 * trigger itself, which fires correctly.
 *
 * 2026-07-06 — REUSED in the Track-B G3-native P11 Spawn/Goal hook
 * ----------------------------------------------------------------------------
 * The GTE-native Blender path keeps native collision/rendering alive, but its
 * `level_meta.goal` is an authored runtime volume rather than a native sector
 * region-code edit. tools/build_g3_native.py therefore uses the same decoded
 * type-1 body from this file in a small resident hook at 0x800495D0:
 *
 *     G_TRANSITION_LEVER (0x800823A0) = 1;
 *     G_FADE_COLOR       (0x80082470) = 23;
 *     FUNC_80050994(58, 0);
 *
 * P11 validation records a separate goal flag at 0x8007F300 so the DuckStation
 * replay can assert the authored goal was reached before any fade/teardown
 * side effects obscure the state. This is a runtime validation trigger, not a
 * claim that clean multi-level handoff is solved.
 * ========================================================================== */
