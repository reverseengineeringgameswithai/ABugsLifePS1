/*
 * Documentation-grade semantic C for Phase 4 A07.
 *
 * Shipping bytes remain in asm/hand_written/80048138_player_vertical_update.s
 * and asm/hand_written/800563d4_actor_skinned_update.s. This file is not a
 * matching translation and is not a build unit.
 */
#include <stdbool.h>
#include <stdint.h>

enum {
    A07_UP = 0x10,
    A07_RIGHT = 0x20,
    A07_DOWN = 0x40,
    A07_LEFT = 0x80,
    A07_DIRECTION_MASK = 0xf0,
    A07_BUSY_FLAG = 0x80,
    A07_CARRIED_FLAG = 0x40,
    A07_SPIN_ANIMATION = 13,
    A07_INITIAL_SFX_TICKS = 120,
    A07_SFX_ID = 64,
};

typedef struct A07PlayerSlice {
    uint8_t pad00[0x38];
    int32_t motion_38;
    int32_t motion_3c;
    uint8_t pad40[0x1c];
    int32_t carried_actor_offset; /* +0x5c, relative to 0x8009fd80 */
    uint8_t pad60[0x1a];
    int16_t action_lock_7a;
    uint8_t pad7c[0x0c];
    int16_t requested_animation_88;
    int16_t current_animation_8a;
    int16_t indexed_attachment_8c;
    uint8_t pad8e[2];
    uint16_t flags_90;
    uint8_t pad92[0x0c];
    int16_t queued_action_9e;
    uint8_t pad_a0[3];
    uint8_t seed_action_a3;
} A07PlayerSlice;

typedef struct A07ActorSlice {
    uint8_t pad00[0x1c];
    int32_t velocity_x;
    int32_t velocity_y;
    int32_t velocity_z;
    uint8_t pad28[0x34];
    uint16_t flags_5c;
} A07ActorSlice;

typedef struct A07Recognizer {
    uint16_t history_800894d0[8];
    int16_t next_index_800823b0;
    uint16_t inactivity_8008229a;
} A07Recognizer;

static const uint16_t a07_clockwise_twice_80077304[8] = {
    A07_UP, A07_RIGHT, A07_DOWN, A07_LEFT,
    A07_UP, A07_RIGHT, A07_DOWN, A07_LEFT,
};

static bool a07_is_exact_cardinal(uint16_t pad)
{
    /* Full-word equality means diagonals and any simultaneous action button do
     * not enter the history, even though the 0xf0 pre-gate accepts them. */
    return pad == A07_UP || pad == A07_RIGHT ||
           pad == A07_DOWN || pad == A07_LEFT;
}

static void a07_append(A07Recognizer *r, uint16_t value)
{
    r->history_800894d0[(uint16_t)r->next_index_800823b0] = value;
    r->next_index_800823b0++;
    if (r->next_index_800823b0 >= 8)
        r->next_index_800823b0 = 0;
}

static bool a07_history_matches(const A07Recognizer *r)
{
    int i;
    for (i = 0; i < 8; i++) {
        int slot = (r->next_index_800823b0 + i) & 7;
        if (r->history_800894d0[slot] != a07_clockwise_twice_80077304[i])
            return false;
    }
    return true;
}

/* 0x800481C4..0x800483AC inside FUNC_80048138. */
bool a07_direction_tick(A07Recognizer *r, A07PlayerSlice *player,
                        uint16_t current_pad_80082488,
                        uint16_t previous_pad_80082380,
                        A07ActorSlice *carried_actor,
                        int32_t *spin_sfx_timer_80082294,
                        void (*indexed_attachment_reset_80041a74)(void))
{
    bool changed = current_pad_80082488 != previous_pad_80082380;

    if (changed && (current_pad_80082488 & A07_DIRECTION_MASK) != 0 &&
        a07_is_exact_cardinal(current_pad_80082488)) {
        a07_append(r, current_pad_80082488);
        r->inactivity_8008229a = 0;
    } else {
        r->inactivity_8008229a++;
        if ((int16_t)r->inactivity_8008229a == 20) {
            r->inactivity_8008229a = 0;
            a07_append(r, 0); /* invalidates a stale complete sequence */
        }
    }

    if (!a07_history_matches(r) || (player->flags_90 & A07_BUSY_FLAG) != 0)
        return false;

    if (player->requested_animation_88 != A07_SPIN_ANIMATION)
        *spin_sfx_timer_80082294 = A07_INITIAL_SFX_TICKS;

    if (player->carried_actor_offset > 0 && carried_actor != 0) {
        carried_actor->velocity_x = 0;
        carried_actor->velocity_y = 0;
        carried_actor->velocity_z = 0;
        carried_actor->flags_5c &= (uint16_t)~A07_CARRIED_FLAG;
    }
    indexed_attachment_reset_80041a74();
    player->action_lock_7a = 0;
    player->carried_actor_offset = 0;
    player->seed_action_a3 = 0;
    player->requested_animation_88 = A07_SPIN_ANIMATION;
    player->queued_action_9e = 0;
    return true;
}

/* 0x8005677C..0x800567C4: clip 13 outlives the matching history while
 * locomotion still has material velocity. The first comparison is signed;
 * only the second component is made absolute by the shipping code. */
void a07_retain_animation_13(A07PlayerSlice *player)
{
    int32_t second = player->motion_3c;
    if (second < 0)
        second = -second;
    if (player->current_animation_8a == A07_SPIN_ANIMATION &&
        (player->motion_38 >= 64 || second >= 64))
        player->requested_animation_88 = A07_SPIN_ANIMATION;
}

/* 0x80056EE0..0x80056F44. Animation 13 is shared with the propeller path,
 * so this periodic sound behavior is not unique evidence for the recognizer. */
void a07_animation_13_sfx(A07PlayerSlice *player, int32_t *timer,
                          uint8_t random_byte,
                          void (*contact_pickup_sfx_80050c40)(int, int))
{
    if (*timer > 0)
        --*timer;
    if (player->requested_animation_88 == A07_SPIN_ANIMATION && *timer == 0) {
        *timer = (int32_t)random_byte + 60;
        contact_pickup_sfx_80050c40(A07_SFX_ID, 0);
    }
}

/* Player spawn at 0x80046B34 clears all 16 history bytes and resets both
 * counters at 0x80046B5C/60. Scene initialization clears the shared SFX timer
 * at 0x8005BA90. */
void a07_spawn_reset(A07Recognizer *r)
{
    for (int i = 0; i < 8; i++)
        r->history_800894d0[i] = 0;
    r->next_index_800823b0 = 0;
    r->inactivity_8008229a = 0;
}
