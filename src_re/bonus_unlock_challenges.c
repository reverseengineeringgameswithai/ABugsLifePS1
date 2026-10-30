/* ============================================================================
 * bonus_unlock_challenges.c — three native bonus-movie unlock challenges
 * ----------------------------------------------------------------------------
 * DOCUMENTATION-GRADE SLICES ONLY. These helpers reconstruct blocks inside the
 * retail functions named below; they are not standalone functions in SCUS_942.88
 * and are not linked into the MOD.
 *
 * ORIGINAL BUILD : SCUS-94288, Disney-Pixar A Bug's Life (v1.0)
 * CONFIDENCE     : CONFIRMED by static disassembly plus deterministic playback
 *                  of movies/Bonus_Level_01..03 on the pristine image. Runtime
 *                  PC coverage was accepted only after full-RAM hashes matched
 *                  untouched CachedInterpreter playback at the same movie frame.
 *
 * SHARED RESULT  : a successful challenge sets transition latch 6, starts a
 *                  fade, sets its low bonus bit, and enters scene 0x10. Scene
 *                  0x10 is the "Bonus Level" loader/playback wrapper.
 *
 * CONTAINERS     : Bonus 1  FUNC_8004ABF4, block 0x8004B35C..0x8004B3D0
 *                  Bonus 2  plant walker, block 0x8005C548..0x8005C6E4
 *                  Bonus 3  contact_vs_actor_handler:
 *                           0x80058B34, 0x8005916C..0x800591EC,
 *                           case-13 reset 0x80059994..0x80059A0C
 * SOURCE NOTE    : ObsidianVault/Canon/Systems/SYS_bonus_unlock_challenges.md
 * EXPERIMENT     : ObsidianVault/Experiments/Runtime Tests/
 *                  EXP_2026-07-11_bonus_unlock_challenges.md
 * ============================================================================ */

#include "re_types.h"

#define G_BONUS1_STOMP_STREAK        (*(volatile uint32_t *)0x8008223c)
#define G_BONUS3_BLUE_KILL_STREAK    (*(volatile uint32_t *)0x80082240)
#define G_BONUS2_MUSHROOM_SEQUENCE   ((volatile int8_t *)0x80082248) /* five IDs; -1 empty */
#define G_BONUS_TRANSITION_LATCH     (*(volatile int16_t *)0x800823a0)
#define G_BONUS_PROGRESS_COMMAND     (*(volatile uint32_t *)0x80082444)
#define G_BONUS_FADE_TIMER           (*(volatile int16_t *)0x80082470)
#define G_CURRENT_SCENE              (*(volatile uint32_t *)0x80082504)
#define G_BONUS_FLAGS                (*(volatile uint8_t *)0x8009b889)
#define G_PLAYER_VERTICAL_SPEED      (*(volatile int32_t *)0x800a6530)
#define G_NATIVE_BERRY_SELECTOR      (*(volatile uint8_t *)0x800a6597)

enum {
    BONUS_SCENE = 0x10,
    BONUS_TRANSITION = 6,
    BONUS_TARGET_COUNT = 5,
    BONUS_PROGRESS_BASE = 113,

    BONUS2_UNLOCK_BIT = 0x01,
    BONUS1_UNLOCK_BIT = 0x02,
    BONUS3_UNLOCK_BIT = 0x04,

    BONUS2_EARNED_GUARD = 0x10,
    BONUS1_EARNED_GUARD = 0x20,
    BONUS3_EARNED_GUARD = 0x40,

    NATIVE_BERRY_BLUE = 1,
    GRASSHOPPER_ACTOR_ID = 15,
    BLUE_BERRY_DAMAGE_CLASS = 0,
};

/* 0x8004B35C..0x8004B3D0, late in FUNC_8004ABF4.
 * Reached by one qualifying butt-slam target interaction in the Training spider
 * arena. The older interpretation of this store as a normal level exit was
 * incorrect: this branch is specifically the five-stomp Bonus 1 unlock. */
static void bonus1_register_butt_slam_target(void)
{
    uint8_t flags = G_BONUS_FLAGS;
    if ((flags & BONUS1_EARNED_GUARD) != 0 || G_CURRENT_SCENE == BONUS_SCENE)
        return;

    uint32_t old_count = G_BONUS1_STOMP_STREAK;
    uint32_t new_count = old_count + 1;
    G_BONUS_PROGRESS_COMMAND = old_count + 114; /* 114..118 for progress 1..5 */
    G_BONUS1_STOMP_STREAK = new_count;           /* store PC 0x8004B3A8 */
    if (new_count != BONUS_TARGET_COUNT)
        return;

    G_BONUS_FLAGS = flags | BONUS1_UNLOCK_BIT;   /* 0x8004B3B4 */
    G_BONUS_TRANSITION_LATCH = BONUS_TRANSITION; /* 0x8004B3C0 */
    G_BONUS_FADE_TIMER = 30;                     /* 0x8004B3CC */
    G_BONUS1_STOMP_STREAK = 0;                   /* 0x8004B3D0 */
}

/* 0x8005C548..0x8005C6E4 in the type-5 mushroom handler.
 * `mushroom_id` is the current plant-walker slot identity. Five distinct IDs
 * must be appended. Touching an ID already present restarts the sequence with
 * that mushroom as item 1; it does not merely ignore the duplicate. */
static void bonus2_register_mushroom_bounce(int8_t mushroom_id)
{
    volatile int8_t *sequence = G_BONUS2_MUSHROOM_SEQUENCE;
    int insertion = -1;

    for (int i = 0; i < BONUS_TARGET_COUNT; i++) {
        if (sequence[i] == mushroom_id) {
            sequence[0] = mushroom_id;           /* 0x8005C54C */
            for (int j = 1; j < BONUS_TARGET_COUNT; j++)
                sequence[j] = -1;                /* 0x8005C554..0x8005C56C */
            insertion = 0;
            break;
        }
        if (sequence[i] == -1) {
            sequence[i] = mushroom_id;           /* 0x8005C580 */
            insertion = i;
            break;
        }
    }

    (void)insertion; /* Original code recounts all five slots after either path. */
    uint32_t command = BONUS_PROGRESS_BASE;
    for (int i = 0; i < BONUS_TARGET_COUNT; i++) {
        if (sequence[i] != -1)
            command++;
    }
    G_BONUS_PROGRESS_COMMAND = command;           /* 0x8005C660/0x8005C690 */
    if (command != BONUS_PROGRESS_BASE + BONUS_TARGET_COUNT)
        return;

    G_BONUS_TRANSITION_LATCH = BONUS_TRANSITION; /* 0x8005C6B8 */
    G_BONUS_FADE_TIMER = 60;                     /* 0x8005C6CC */
    G_PLAYER_VERTICAL_SPEED = -0x4000;           /* 0x8005C6DC */
    G_BONUS_FLAGS |= BONUS2_UNLOCK_BIT;          /* 0x8005C6E4 */
}

/* 0x8005C034..0x8005C08C initializes the five-slot sequence to -1 whenever
 * the type-5 challenge is not applicable, scene 0x10 is active, or the high
 * earned guard bit is already set. */
static void bonus2_clear_sequence(void)
{
    for (int i = 0; i < BONUS_TARGET_COUNT; i++)
        G_BONUS2_MUSHROOM_SEQUENCE[i] = -1;
}

/* 0x80058B00..0x80058B34, contact_vs_actor_handler entry. The streak is valid
 * only while native selector 1 (blue berry) is equipped. */
static void bonus3_validate_equipped_berry(void)
{
    if (G_NATIVE_BERRY_SELECTOR != NATIVE_BERRY_BLUE)
        G_BONUS3_BLUE_KILL_STREAK = 0;            /* store PC 0x80058B34 */
}

/* 0x8005916C..0x800591EC, reached only after the struck enemy's local HP is
 * <= 0. The challenge accepts blue contact class 0 against actor ID 15. */
static void bonus3_register_enemy_kill(const uint8_t *hit_record, const uint8_t *enemy)
{
    uint8_t damage_class = hit_record[0x2c];
    uint32_t actor_id = *(const uint32_t *)(enemy + 0x00);
    uint8_t flags = G_BONUS_FLAGS;

    if (damage_class != BLUE_BERRY_DAMAGE_CLASS ||
        actor_id != GRASSHOPPER_ACTOR_ID ||
        (flags & BONUS3_EARNED_GUARD) != 0)
        return;

    uint32_t old_count = G_BONUS3_BLUE_KILL_STREAK;
    uint32_t new_count = old_count + 1;
    G_BONUS_PROGRESS_COMMAND = old_count + 114;
    G_BONUS3_BLUE_KILL_STREAK = new_count;        /* 0x800591C0 */
    if (new_count != BONUS_TARGET_COUNT)
        return;

    G_BONUS_FLAGS = flags | BONUS3_UNLOCK_BIT;    /* 0x800591D0 */
    G_BONUS_TRANSITION_LATCH = BONUS_TRANSITION; /* 0x800591DC */
    G_BONUS_FADE_TIMER = 30;                     /* 0x800591E8 */
    G_BONUS3_BLUE_KILL_STREAK = 0;               /* 0x800591EC */
}

/* Contact-dispatch case 13, 0x80059994..0x80059A0C. Early edits near frame 900
 * were rejected because the extra throw changed Flik's later route enough to
 * cause a fall. A later two-frame edit at 2150..2151, while Flik was stationary
 * after kill 4, isolated the rule: case 13 executed once and streak 4 became 0;
 * the original fifth grasshopper then produced streak 1 with no transition. */
static void bonus3_reset_on_contact_case_13(void)
{
    G_BONUS3_BLUE_KILL_STREAK = 0;                /* store PC 0x80059A0C */
}

/* Keep the documentation helpers referenced without pretending they form an
 * original call graph. */
void bonus_unlock_challenge_refs(void)
{
    (void)bonus1_register_butt_slam_target;
    (void)bonus2_register_mushroom_bounce;
    (void)bonus2_clear_sequence;
    (void)bonus3_validate_equipped_berry;
    (void)bonus3_register_enemy_kill;
    (void)bonus3_reset_on_contact_case_13;
}
