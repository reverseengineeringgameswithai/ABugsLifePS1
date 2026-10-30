/* RCA a4 (2026-07-09): SUPERSEDED for build purposes — 0x800586b0 is byte-matched in the
   shipping build as asm/hand_written/800586b0_contact_walker.s (config/segments.yml `attempted`;
   validate_build.py SHA-1 PASS). This src_re file is documentation-grade pseudocode,
   retained for its analysis/comments; it is NOT the build unit. */
/* ============================================================================
 * contact_walker_800586b0.c  — player-proximity / pickup walker [PHASE 4 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.800586b0  (size 1096 bytes, 0x800586b0..0x80058af8)
 *                    [size corrected 2026-08-01: the 580-byte figure was stale
 *                     against analysis/functions.json]
 * CONFIDENCE       : CONFIRMED walker loop, live gates, distance math, radius test,
 *                    action_id dispatch table. Action case bodies are summarized only;
 *                    detailed handler decompilation is Phase 5.
 * SOURCE NOTES     : docs/EXPERIMENT_LOG.md (exact math), docs/COORDINATE_MODDING.md
 *                    (auto-collect/weak-Y), docs/EXECUTABLE_AND_OVERLAYS.md,
 *                    Phase 3 contact_alloc_80059e44.c, r2 disasm.
 * KNOWN CALLERS    : fcn.8004ecd4 @0x8004f074.
 * KNOWN CALLEES    : per-action cases via table G_WALKER_DISPATCH(0x8001b570);
 *                    fcn.800503fc, fcn.8005044c, fcn.80050994, fcn.80054eac,
 *                    fcn.8004a700.
 * KNOWN GLOBALS    : G_CONTACT_ARRAY(0x800b0d18, 64*0x38), G_PLAYER_X/Y/Z,
 *                    G_BERRY_MARKER, G_GRAIN_COUNT, G_WALKER_DISPATCH,
 *                    0x80082504 (scene id), 0x800a6590/0x800a6594/0x800a657e,
 *                    0x800822f4 (script cursor), 0x80089938 actor/berry table.
 * UNRESOLVED       : action-case bodies and gameplay semantics (Phase 5); meaning of
 *                    player-Y bias -0x1cc0; exact meanings of rec+0x2c writes and
 *                    post-hit 0x8004a700 call.
 *
 * CONFIRMED WALKER FACTS:
 *   - Array base 0x800b0d18, loop count 64, stride 0x38.
 *   - Live gate: lh rec+0x22 > 0, then (lbu rec+0x33 & 2) != 0.
 *   - Player snapshot is taken once before the loop:
 *       X = [0x800a6500], Y = [0x800a6504] - 0x1cc0, Z = [0x800a6508].
 *   - Distance scaling uses signed multiply and arithmetic shift:
 *       dx = ((playerX - rec.x) * 0x300) >> 13
 *       dy = ((playerY - rec.y) * 0x100) >> 13
 *       dz = ((playerZ - rec.z) * 0x300) >> 13
 *   - Radius = 0x12c + (lh rec+0x28). Contact if dist2 < radius*radius.
 *   - Dispatch index = (int16_t)((lhu rec+0x20) - 2); if (uint32_t)idx < 0x75,
 *     jump through word table 0x8001b570[idx], else use default case 0x800589d4.
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LBU(p)  (*(uint8_t  *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))
#define SH(p,v) (*(uint16_t *)(p) = (uint16_t)(v))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))

#define CONTACT_SLOT_COUNT      0x40
#define CONTACT_ACTION_LIMIT    0x75
#define PLAYER_Y_CONTACT_BIAS   0x1cc0
#define ACTOR_BERRY_COLUMN_TABLE 0x80089938u /* 64 actor rows x 5 native berry columns */
#define G_SCENE_ID              0x80082504u /* CONFIRMED read by action_id 2 case */
#define G_SCRIPT_CURSOR         0x800822f4u /* CONFIRMED read by action_id 0x20 case */
#define G_UNK_800A6590          0x800a6590u /* UNKNOWN flags halfword; action_id 0x0f ORs 0x20 */
#define G_UNK_800A6594          0x800a6594u /* UNKNOWN halfword counter; action_id 9 increments */
#define G_POWER_SLOT            0x800a657eu /* player power slot; action_id 0x2E stores -3.
                                               Sign-multiplexed: >0 = B06 invincibility
                                               countdown (time-consumed), <0 = B08 bubble
                                               hit quota (hit-consumed). See
                                               ObsidianVault/Canon/Systems/SYS_player_power_slot.md */

extern void fcn_800503fc(void *arg);           /* Phase 5 / later: semantics UNKNOWN */
extern void fcn_8005044c(int result, void *rec);/* post-pickup bookkeeping (CONFIRMED call shape) */
extern void fcn_80050994(int sound_or_event_id);/* sound/event helper; exact meaning Phase 5 */
extern void fcn_80054eac(void);                /* grain pickup handler; body Phase 5 */
extern void fcn_8004a700(int dx, int dz, void *out, int zero); /* post-hit helper; UNKNOWN */

/* Handler table entries observed in 0x8001b570. Index is action_id - 2.
 * Default entry 0x800589d4 sets rec+0x2c = 0x0c and rec.active_type = 1.
 * Non-default action bodies are intentionally NOT decompiled here (Phase 5). */
typedef enum WalkerActionCase {
    WALKER_CASE_SCENE_DEPENDENT_A = 0x02, /* idx 0  -> 0x80058834 */
    WALKER_CASE_SCENE_DEPENDENT_B = 0x08, /* idx 6  -> 0x80058854 */
    WALKER_CASE_UNK_EVENT_09      = 0x09, /* idx 7  -> 0x80058864 */
    WALKER_CASE_UNK_TIMER_0C      = 0x0c, /* idx 10 -> 0x800588b0 */
    WALKER_CASE_FLAG_0F           = 0x0f, /* idx 13 -> 0x800588d4 */
    WALKER_CASE_GRAIN             = 0x14, /* idx 18 -> 0x800589b8 -> fcn.80054eac */
    WALKER_CASE_MARKER_CLEAR      = 0x20, /* idx 30 -> 0x800588fc */
    WALKER_CASE_MARKER_2          = 0x21, /* idx 31 -> 0x80058940 */
    WALKER_CASE_MARKER_3          = 0x22, /* idx 32 -> 0x80058954 */
    WALKER_CASE_MARKER_1          = 0x23, /* idx 33 -> 0x80058968 */
    WALKER_CASE_MARKER_4          = 0x24, /* idx 34 -> 0x80058978 */
    /* Action ids CORRECTED 2026-08-01 by decoding G_WALKER_DISPATCH(0x8001b570)
       directly (index = action_id - 2). The three previous ids -- 0x32, 0x37 and
       0x52 -- ALL resolve to the default case 0x800589d4, so every one of them was
       wrong and none of these bodies was reachable by the id it claimed. */
    WALKER_CASE_BUBBLE_GRANT      = 0x2E, /* idx 44 -> 0x80058998  B08 grant := -3 */
    WALKER_CASE_DISABLE_RECORD    = 0x33, /* idx 49 -> 0x8005889c */
    WALKER_CASE_UNK_52            = 0x3A  /* idx 56 -> 0x800589c8 (0x76 aliases here) */
} WalkerActionCase;

static int32_t walker_scaled_delta(int32_t player, int32_t record, int32_t scale)
{
    /* MIPS: subu; mult signed; mflo; sra 13. Overflow/HI ignored. */
    return ((player - record) * scale) >> 13;
}

/*
 * fcn.800586b0 — scan active ContactRecord slots and fire the record action
 * when the player is within the record's radius.
 */
void contact_walker(void)
{
    ContactRecord *rec = (ContactRecord *)(uintptr_t)G_CONTACT_ARRAY;
    uint8_t old_marker = LBU(G_BERRY_MARKER);     /* saved before loop */
    int32_t player_x = LW(G_PLAYER_X);
    int32_t player_y = LW(G_PLAYER_Y) - PLAYER_Y_CONTACT_BIAS;
    int32_t player_z = LW(G_PLAYER_Z);

    int hit_for_post_angle = 0;                   /* s6; set by selected cases */
    ContactRecord *post_angle_rec = 0;            /* s5; valid when hit_for_post_angle == 1 */

    for (int slot = 0; slot < CONTACT_SLOT_COUNT; slot++, rec++) {
        if (rec->active_type <= 0) continue;      /* lh, signed; blez skips */
        if ((rec->flags & 0x02) == 0) continue;   /* lbu & 2; beqz skips */

        int32_t dx = walker_scaled_delta(player_x, rec->x, 0x300);
        int32_t dy = walker_scaled_delta(player_y, rec->y, 0x100);
        int32_t dz = walker_scaled_delta(player_z, rec->z, 0x300);
        int32_t dist2 = dx*dx + dy*dy + dz*dz;

        int32_t radius = CONTACT_RADIUS_BASE + rec->radius_add; /* radius_add is lh */
        int32_t radius2 = radius * radius;
        if (dist2 >= radius2) continue;           /* slt(dist2,radius2); beqz skips */

        int16_t action = (int16_t)(rec->action_id - 2); /* lhu, addiu -2, sll/sra 16 */
        int result_for_bookkeeping = 0;           /* s1 */
        int state_to_store = 0x0c;                /* s0 default case 0x800589d4 */

        if ((uint32_t)action < CONTACT_ACTION_LIMIT) {
            /* CONFIRMED dispatch table: target = ((uint32_t*)0x8001b570)[action].
             * This switch is a structured representation of observed non-default
             * table targets. Bodies are Phase 5 and intentionally summarized. */
            switch (rec->action_id) {
            case WALKER_CASE_SCENE_DEPENDENT_A:
                hit_for_post_angle = 1;
                state_to_store = (LW(G_SCENE_ID) == 0x0f) ? 0x15 : 0x14;
                post_angle_rec = rec;
                break;

            case WALKER_CASE_SCENE_DEPENDENT_B:
                hit_for_post_angle = 1;
                state_to_store = 0x13;
                post_angle_rec = rec;
                break;

            case WALKER_CASE_UNK_EVENT_09:
                state_to_store = 7;
                fcn_800503fc((void *)0x800b0190);
                SH(G_UNK_800A6594, LHU(G_UNK_800A6594) + 1);
                fcn_80050994(0x3e);
                result_for_bookkeeping = -4;
                break;

            case WALKER_CASE_DISABLE_RECORD:
                hit_for_post_angle = 1;
                state_to_store = 0;
                rec->flags = 0x60;                /* sb 0x60, rec+0x33 */
                post_angle_rec = rec;
                break;

            case WALKER_CASE_UNK_TIMER_0C:
                if (LH(G_BERRY_MARKER - 0x19) <= 0) {
                    fcn_80050994(0x41);
                }
                SH(G_BERRY_MARKER - 0x19, 0x0190); /* fp = 0x800a657e */
                state_to_store = 7;
                result_for_bookkeeping = -0x0c;
                break;

            case WALKER_CASE_FLAG_0F:
                fcn_80050994(0x4b);
                state_to_store = 7;
                SH(G_UNK_800A6590, LHU(G_UNK_800A6590) | 0x20);
                result_for_bookkeeping = -7;
                break;

            case WALKER_CASE_MARKER_CLEAR: {
                uint8_t *cur = (uint8_t *)(uintptr_t)LW(G_SCRIPT_CURSOR);
                SW(G_SCRIPT_CURSOR, (int32_t)(uintptr_t)(cur + 1));
                fcn_80050994(((LBU(cur) & 1) * 15) + 0x4e);
                SB(G_BERRY_MARKER, 0);
                state_to_store = 7;
                result_for_bookkeeping = -5;
                break;
            }

            case WALKER_CASE_MARKER_2:
                SB(G_BERRY_MARKER, 2);
                fcn_80050994(0x36);
                state_to_store = 7;
                result_for_bookkeeping = -5;
                break;

            case WALKER_CASE_MARKER_3:
                SB(G_BERRY_MARKER, 3);
                fcn_80050994(0x38);
                state_to_store = 7;
                result_for_bookkeeping = -5;
                break;

            case WALKER_CASE_MARKER_1:
                SB(G_BERRY_MARKER, 1);
                fcn_80050994(0x35);
                state_to_store = 7;
                result_for_bookkeeping = -5;
                break;

            case WALKER_CASE_MARKER_4:
                SB(G_BERRY_MARKER, 4);
                fcn_80050994(0x37);
                state_to_store = 7;
                result_for_bookkeeping = -5;
                break;

            case WALKER_CASE_BUBBLE_GRANT:
                fcn_80050994(-3);
                SH(G_POWER_SLOT, -3);
                state_to_store = 7;
                result_for_bookkeeping = -0x0c;
                break;

            case WALKER_CASE_GRAIN:
                fcn_80054eac();
                state_to_store = 0x10;
                result_for_bookkeeping = -1;
                break;

            case WALKER_CASE_UNK_52:
                hit_for_post_angle = 1;
                state_to_store = 0;
                post_angle_rec = rec;
                break;

            default:
                state_to_store = 0x0c;
                result_for_bookkeeping = 0;
                break;
            }
        }

        /* Common action tail at 0x800589d8. The field names are NOT promoted:
         * Phase 4 only confirms these writes, not their stable semantic names. */
        if (state_to_store > 0) {
            rec->unk2c = (int16_t)state_to_store;
            rec->active_type = 1;
        } else if (state_to_store < 0) {
            rec->active_type = 1;
        }

        if (result_for_bookkeeping != 0) {
            fcn_8005044c(result_for_bookkeeping, rec);
        }
    }

    /* Post-loop helper used by action cases that saved a hit record in s5.
     * CONFIRMED arguments: a0 = rec.x - playerX, a1 = rec.z - playerZ,
     * a2 = sp+0x10, a3 = 0, [sp+0x14] = 0. Semantics UNKNOWN. */
    if (hit_for_post_angle == 1) {
        int32_t tmp[2];
        fcn_8004a700(post_angle_rec->x - LW(G_PLAYER_X),
                     post_angle_rec->z - LW(G_PLAYER_Z),
                     tmp,
                     0);
    }

    /* First-use berry-column inheritance. New-game state initializes column 0
     * to 100 and columns 1..4 to 0xff. The first switch to an uninitialized
     * berry copies all 64 actor rows from the old column into the new one. */
    if (old_marker != LBU(G_BERRY_MARKER)
        && LBU(ACTOR_BERRY_COLUMN_TABLE + LBU(G_BERRY_MARKER)) == 0xff) {
        uint8_t *table = (uint8_t *)ACTOR_BERRY_COLUMN_TABLE;
        for (int i = 0, off = 0; i < 0x40; i++, off += 5) {
            table[off + LBU(G_BERRY_MARKER)] = table[off + old_marker];
        }
    }
}

/* ----------------------------------------------------------------------------
 * PHASE 4 FINDINGS:
 *  - CONFIRMED loop count/stride: 64 records, rec += 0x38.
 *  - CONFIRMED active/type gate: signed lh rec+0x22 must be > 0.
 *  - CONFIRMED flags gate: lbu rec+0x33 & 0x02 must be nonzero.
 *  - CONFIRMED radius: 0x12c + signed lh rec+0x28.
 *  - CONFIRMED distance scaling: X/Z use *0x300 >> 13; Y uses *0x100 >> 13
 *    after playerY is biased by -0x1cc0. This underweights Y to 1/3 of X/Z.
 *  - CONFIRMED dispatch: action_id is lhu rec+0x20; index = (int16)(action_id - 2);
 *    if unsigned index < 0x75, jr through 0x8001b570[index], else default case.
 *  - NO ContactRecord field promotions: rec+0x2c and rec+0x22 writes are confirmed,
 *    but their precise gameplay semantics remain UNKNOWN/TODO.
 *  - Phase 5 is ready to decompile the action-case bodies and shared handlers.
 * ---------------------------------------------------------------------------- */
