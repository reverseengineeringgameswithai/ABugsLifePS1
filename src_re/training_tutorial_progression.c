/* ============================================================================
 * training_tutorial_progression.c -- Training NPC objective progression
 * ----------------------------------------------------------------------------
 * Retail/ALLMODS live RE, 2026-07-07, SCUS-94288 scene 0x11 (Training).
 *
 * Goal: explain how the instructor ant progresses between tutorial objectives
 * after the solved step-0 sign/audio patch, and how later objective items appear.
 *
 * Evidence:
 *   - Isolated DuckStation external-debugger run on build/ABL_ALLMODS.cue.
 *   - Movie: TRAINING_NPC_STAGES.movie.json, v3 from-boot, 8039 frames,
 *     SHA-256 2b05a9758975a3dd983503a216e347b49a1b344ea9435954d2f325a29fe28f0d.
 *   - DuckStation fork fe0cca16... dirty, duckstation-qt binary SHA-256
 *     5538e0e0ca198b54f184ba5650e9a708ef4faf79b47180e49430e912fcc35448.
 *
 * High-level model:
 *   - LEVEL07/LEVEL1.BIN loads at 0x800B39A0.
 *   - 0x800B3F58 is the 14-step tutorial state machine.
 *   - G_TRAIN_STEP (0x800B4A3C) selects jump_table[step].
 *   - G_TRAIN_STEP_STATE[step] (0x800B4A58 + step*4) persists per-step progress.
 *   - G_TRAIN_WAIT (0x800B4A50) is a shared 30 Hz-ish inter-step wait timer.
 *   - Each step plays voice id G_TRAIN_AUDIO_IDS[step], then waits for a gameplay
 *     condition. A handler sets s1=1 to advance. The common tail then calls
 *     0x80045A60, sets G_TRAIN_WAIT=30, clears 0x800A65E0, writes a timestamp-like
 *     value to 0x800A65F0, and increments G_TRAIN_STEP.
 *
 * Item reveal model:
 *   - Training init scans the current type-0x3f pickup record through
 *     [0x80096E9C].
 *   - It caches two kind 0x2B entry pointers in G_KIND2B_PTR[0..1] and up to four
 *     kind 0x2C entry pointers in G_KIND2C_PTR[0..3].
 *   - During init it HIDES those entries by adding +8000 to entry.y and entry+0x0E
 *     rest-height. In the ALLMODS run at movie frame 3900, the cached entries were:
 *
 *       G_KIND2B_PTR[0] = 0x8011F3F0, kind 0x2B, y 7672, rest 8472
 *       G_KIND2B_PTR[1] = 0x8011F400, kind 0x2B, y 7461, rest 8261
 *       G_KIND2C_PTR[0] = 0x8011F410, kind 0x2C, y 6242, rest 7042
 *       G_KIND2C_PTR[1] = 0x8011F420, kind 0x2C, y 7519, rest 8319
 *       G_KIND2C_PTR[2] = 0x8011F430, kind 0x2C, y 6098, rest 6898, status 0
 *       G_KIND2C_PTR[3] = 0x8011F440, kind 0x2C, y 7414, rest 8214
 *
 *     Subtracting 8000 returns them to normal world/rest height. This is not a
 *     separate allocator path: once revealed, the existing type-0x3f pickup pass
 *     (FUNC_80053814) constructs/collects the item normally when the player enters
 *     range. Completion is usually detected by entry.y becoming the consumed
 *     sentinel 0x80000000.
 *
 * Source-coordinate edit note (2026-07-07):
 *   - The first green tutorial token is not dynamically allocated; it is the
 *     first kind-0x2B type-0x3f source entry, retail/ALLMODS entry index 56.
 *   - In the fixed green-token-right image it was moved by an in-place disc
 *     edit only: file x -1197 -> -597, y -50, z 148 unchanged.
 *   - Do not rerun the full Training word-pickup/manifest asset path for a
 *     coordinate-only move. A previous attempt did that and produced a black
 *     screen when Training loaded because the build changed multiple Training
 *     files/layouts instead of only the type-0x3f coordinate.
 *
 * ALLMODS step-2 blackberry gate crash fix (2026-07-07):
 *   - The optional custom gate for step 2 appends a hidden kind-0x25 pickup
 *     (entry 66 in the current ALLMODS build), reveals it when step 2 starts,
 *     and advances only when BOTH the step-2 voice flag has cleared and
 *     0x800A6597 == 5 (Blackberry/Fastberry collected/equipped).
 *   - Do not use LEVEL1.BIN apparent tail 0x800B4A30 as code. Live crash
 *     evidence from the user's DuckStation instance: PC=0x000000A0,
 *     COP0_EPC=0x800B4A34, and live memory at 0x800B4A30 was runtime data, not
 *     cave code. In this model 0x800B4A30 is G_PREV_A6580, and adjacent words
 *     hold cached kind pointers / tutorial state.
 *   - Fixed cave allocation: main gate 0x8007F0D8..0x8007F118; reveal shim
 *     0x8007F930..0x8007F954. The forbidden runtime ranges remain
 *     0x8007F130..0x8007F16F, 0x8007FBC8, 0x8007FD58.., 0x80081858,
 *     0x80081CF0, and 0x800821FC.
 *
 * Jump table:
 *   step  0 -> 0x800B3FD4  (ALLMODS rewrites only advance half for audio-gated sign)
 *   step  1 -> 0x800B402C
 *   step  2 -> 0x800B40C4
 *   step  3 -> 0x800B4128
 *   step  4 -> 0x800B4200
 *   step  5 -> 0x800B4368
 *   step  6 -> 0x800B4264  (reveals first cached kind 0x2B item)
 *   step  7 -> 0x800B42C4
 *   step  8 -> 0x800B4318
 *   step  9 -> 0x800B43FC  (reveals second cached kind 0x2B item)
 *   step 10 -> 0x800B4470
 *   step 11 -> 0x800B4570
 *   step 12 -> 0x800B45E0
 *   step 13 -> 0x800B4670  (reveals cached kind 0x2C items)
 *
 * This is RE pseudocode. It is not compiled into the mod.
 * ==========================================================================*/

#include "re_types.h"

#define G_TYPE3F_REC_PTR       (*(volatile uint32_t *)0x80096E9C)
#define G_TRAIN_STEP           (*(volatile int32_t  *)0x800B4A3C)
#define G_TRAIN_WAIT           (*(volatile int32_t  *)0x800B4A50)
#define G_TRAIN_ALT_AUDIO      (*(volatile int32_t  *)0x800B4A54)
#define G_TRAIN_STEP_STATE     ((volatile int32_t  *)0x800B4A58)
#define G_TRAIN_AUDIO_IDS      ((volatile int16_t  *)0x800B4A14)
#define G_KIND2B_PTR           ((Type3FEntry **)0x800B4A34)
#define G_KIND2C_PTR           ((Type3FEntry **)0x800B4A40)

/* Runtime-owned Training overlay state. Static zeros here are not free space. */
#define G_PREV_A6580           (*(volatile int32_t *)0x800B4A30)
#define G_A6580                (*(volatile int16_t *)0x800A6580)
#define G_A6584                (*(volatile int16_t *)0x800A6584)
#define G_EQUIPPED_BERRY       (*(volatile uint8_t *)0x800A6597)

#define TYPE3F_KIND_2B         0x2Bu
#define TYPE3F_KIND_2C         0x2Cu
#define HIDE_DELTA             8000
#define CONSUMED_Y             ((int32_t)0x80000000u)

#define TRAINING_FIRST_GREEN_TOKEN_INDEX       56
#define TRAINING_FIRST_GREEN_TOKEN_KIND        TYPE3F_KIND_2B
#define TRAINING_FIRST_GREEN_TOKEN_ORIG_X      (-1197)
#define TRAINING_FIRST_GREEN_TOKEN_FIXED_X     (-597)
#define TRAINING_FIRST_GREEN_TOKEN_Y           (-50)
#define TRAINING_FIRST_GREEN_TOKEN_Z           148

#define ALLMODS_STEP2_BLACKBERRY_ENTRY         66
#define ALLMODS_STEP2_BLACKBERRY_KIND          0x25u
#define ALLMODS_STEP2_BLACKBERRY_EQUIP_INDEX   5
#define ALLMODS_STEP2_GATE_MAIN_CAVE           0x8007F0D8u
#define ALLMODS_STEP2_GATE_REVEAL_CAVE         0x8007F930u

extern void play_training_voice_once(int16_t packed_id);    /* 0x80046AC0 */
extern int  voice_is_playing(void);                         /* 0x80046B14 */
extern void transition_finalize_80045a60(void);             /* 0x80045A60 */
extern void training_raise_sign(int sign_index, int count); /* 0x800B3B54 */
extern int  func_80038e48(void);

static void play_step_voice_once(int *state)
{
    if (*state == 0) {
        play_training_voice_once(G_TRAIN_AUDIO_IDS[G_TRAIN_STEP]);
        *state = 1;
    }
}

static void hide_entry(Type3FEntry *e)
{
    e->y += HIDE_DELTA;
    *(int16_t *)&e->bob_base_lo += HIDE_DELTA;
}

static void reveal_entry(Type3FEntry *e)
{
    e->y -= HIDE_DELTA;
    *(int16_t *)&e->bob_base_lo -= HIDE_DELTA;
}

void training_tutorial_init_800b3c94(void)
{
    Type3FEntry *entries = (Type3FEntry *)(uintptr_t)(G_TYPE3F_REC_PTR + 4);
    uint16_t count = *(volatile uint16_t *)(uintptr_t)G_TYPE3F_REC_PTR;
    int kind2b_count = 0;
    int kind2c_count = 0;

    G_TRAIN_WAIT = 0;
    G_TRAIN_ALT_AUDIO = 0;
    G_KIND2B_PTR[0] = 0;
    G_KIND2B_PTR[1] = 0;
    G_KIND2C_PTR[0] = 0;
    G_KIND2C_PTR[1] = 0;
    G_KIND2C_PTR[2] = 0;
    G_KIND2C_PTR[3] = 0;
    G_TRAIN_STEP = 0;
    for (int i = 0; i < 14; i++)
        G_TRAIN_STEP_STATE[i] = 0;

    for (uint16_t i = 0; i < count; i++) {
        Type3FEntry *e = &entries[i];
        if (e->kind == TYPE3F_KIND_2B) {
            if (kind2b_count < 2)
                G_KIND2B_PTR[kind2b_count++] = e;
            hide_entry(e);
        } else if (e->kind == TYPE3F_KIND_2C) {
            if (kind2c_count < 4)
                G_KIND2C_PTR[kind2c_count++] = e;
            hide_entry(e);
        }
    }
}

static int step1_berries(int *state)
{
    play_step_voice_once(state);

    if (G_A6580 == 1 && (G_PREV_A6580 == 0 || G_PREV_A6580 == 3)) {
        (*state)++;
        if (*state >= 7)
            return 1;
        training_raise_sign(1, 6 - *state);
    }
    G_PREV_A6580 = G_A6580;
    return 0;
}

static int step2_triple_signal(int *state)
{
    play_step_voice_once(state);
    if (G_A6584 == 9) {
        (*state)++;
        if (*state >= 4)
            return 1;
        training_raise_sign(2, 3 - *state);
    }
    return 0;
}

static int step6_reveal_first_2b(int *state)
{
    play_step_voice_once(state);
    if (*state == 1 && G_KIND2B_PTR[0] != 0)
        reveal_entry(G_KIND2B_PTR[0]);
    return (G_KIND2B_PTR[0] != 0 && G_KIND2B_PTR[0]->y == CONSUMED_Y);
}

static int step9_reveal_second_2b(int *state)
{
    play_step_voice_once(state);
    if (*state == 1 && G_KIND2B_PTR[1] != 0)
        reveal_entry(G_KIND2B_PTR[1]);
    return (G_KIND2B_PTR[1] != 0 && G_KIND2B_PTR[1]->y == CONSUMED_Y);
}

static int step13_reveal_2c_batch(int *state)
{
    if (*state == 0) {
        play_step_voice_once(state);
        for (int i = 0; i < 4; i++) {
            if (G_KIND2C_PTR[i] != 0)
                reveal_entry(G_KIND2C_PTR[i]);
        }
    }
    return 0; /* final/tutorial-loop step; common audio tail handles voice repeat */
}

void training_tutorial_tick_800b3f58(int caller_flags)
{
    int step = G_TRAIN_STEP;
    int state = G_TRAIN_STEP_STATE[step];
    int advance = 0;
    int audio_repeat_allowed = caller_flags & 0x1000;

    if (G_TRAIN_WAIT != 0) {
        G_TRAIN_WAIT--;
        return;
    }

    switch (step) {
    case 1:  advance = step1_berries(&state); break;
    case 2:  advance = step2_triple_signal(&state); break;
    case 6:  advance = step6_reveal_first_2b(&state); break;
    case 9:  advance = step9_reveal_second_2b(&state); break;
    case 13: advance = step13_reveal_2c_batch(&state); break;
    default:
        play_step_voice_once(&state);
        /* Other steps are decoded in comments/notes but left out here until
         * their exact gameplay signal names are proven. */
        break;
    }

    G_TRAIN_STEP_STATE[step] = state;

    if (advance) {
        transition_finalize_80045a60();
        G_TRAIN_WAIT = 30;
        G_TRAIN_STEP++;
    } else if (audio_repeat_allowed && !voice_is_playing()) {
        if (step == 13) {
            play_training_voice_once(G_TRAIN_ALT_AUDIO ? G_TRAIN_AUDIO_IDS[12]
                                                       : G_TRAIN_AUDIO_IDS[13]);
            G_TRAIN_ALT_AUDIO ^= 1;
        } else {
            play_training_voice_once(G_TRAIN_AUDIO_IDS[step]);
        }
    }
}
