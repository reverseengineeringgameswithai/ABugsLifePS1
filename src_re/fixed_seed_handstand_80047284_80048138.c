/*
 * Documentation-grade semantic reconstruction for Phase 4 A10.
 * This is not matching build source and must not be compiled into the game.
 * Pristine owners: 0x80047284 player_contact_response and
 * 0x80048138 player_vertical_update.
 */
#include <stdint.h>

typedef struct {
    int32_t x, y, z;                    /* +0x04, +0x08, +0x0c */
    uint8_t pad10[0x30];
    int32_t behavior;                   /* +0x40 */
    uint8_t pad44[0x18];
    uint16_t flags;                     /* +0x5c; 0x40 = selected/carried */
} A10Actor;

typedef struct {
    int32_t x, y, z;                    /* +0x00 */
    uint8_t pad0c[0x50];
    uint32_t selected_actor_offset;     /* +0x5c, base 0x8009fd80 */
    uint8_t pad60[0x20];
    int16_t vertical_state;             /* +0x80 */
    int16_t grounded;                   /* +0x82 */
    int16_t vertical_accumulator;       /* +0x84 */
    int16_t action;                     /* +0x88 */
    uint8_t pad8a[0x19];
    uint8_t seed_action_mode;           /* +0xa3 */
} A10Player;

enum {
    A10_MODE_MOVABLE_PULL_IN = 8,
    A10_MODE_FIXED_HANDSTAND = 14,
    A10_MODE_RELEASE_TRANSIENT = 13,
    A10_ACTION_HANDSTAND_RELEASE = 17,
    A10_VERTICAL_LANDING = 5,
    A10_VERTICAL_HANDSTAND_DISMOUNT = 6
};

static void a10_mount_commit(A10Player *player, A10Actor *actor,
                             uint32_t actor_offset)
{
    player->selected_actor_offset = actor_offset;            /* 0x80047858 */
    player->seed_action_mode = actor->behavior < 3 ?
        A10_MODE_MOVABLE_PULL_IN : A10_MODE_FIXED_HANDSTAND;  /* 0x80047864..74 */
    actor->flags |= 0x40;                                    /* 0x80047888 */
}

static int a10_bypasses_ordinary_vertical_update(const A10Player *player)
{
    return player->seed_action_mode == A10_MODE_FIXED_HANDSTAND;
    /* 0x80048b2c..0x80048b34 branches directly to 0x80048d90. */
}

static void a10_fixed_seed_release(A10Player *player, A10Actor *actor)
{
    actor->flags &= (uint16_t)~0x40;                         /* 0x80047c60 */
    player->action = A10_ACTION_HANDSTAND_RELEASE;           /* 0x80047cd0..d8 */
    player->selected_actor_offset = 0;                       /* 0x80047ce8 */
    player->seed_action_mode = A10_MODE_RELEASE_TRANSIENT;   /* 0x80047d00 */
}

static void a10_post_release_vertical_update(A10Player *player)
{
    if (player->seed_action_mode == A10_MODE_RELEASE_TRANSIENT)
        player->seed_action_mode = 0;                        /* 0x800490ac */
    if (player->vertical_state == A10_VERTICAL_LANDING)
        player->vertical_state = A10_VERTICAL_HANDSTAND_DISMOUNT;
                                                               /* 0x80048d64 */
}
