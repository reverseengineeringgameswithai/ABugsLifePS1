/*
 * abdomen_bounce_80048138_8004abf4.c
 *
 * Documentation-grade semantic slices from pristine SCUS-94288.
 * These are not standalone original functions and are not linked into the MOD.
 * They preserve the A05 decisions inside FUNC_80048138 and FUNC_8004ABF4.
 */

#include "re_types.h"

typedef struct PlayerA05 {
    int32_t x;                       /* +0x00 */
    int32_t y;                       /* +0x04 */
    int32_t z;                       /* +0x08 */
    uint8_t pad0c[0x20];
    int32_t vx;                      /* +0x2c */
    int32_t vy;                      /* +0x30 */
    int32_t vz;                      /* +0x34 */
    uint8_t pad38[0x10];
    int32_t floor_y;                 /* +0x48 */
    uint8_t pad4c[0x2e];
    int16_t action_timer;            /* +0x7a */
    uint8_t pad7c[4];
    int16_t air_state;               /* +0x80 */
    int16_t grounded;                /* +0x82 */
    int16_t dive_phase;              /* +0x84 */
    int16_t reserved86;              /* +0x86 */
    int16_t animation_selector;      /* +0x88 */
} PlayerA05;

typedef struct ActorA05 {
    uint32_t id;                     /* +0x00 */
    int32_t x;                       /* +0x04 */
    int32_t y;                       /* +0x08 */
    int32_t z;                       /* +0x0c */
    uint8_t pad10[0x44];
    int16_t reaction_x;              /* +0x54 */
    int16_t reaction_z;              /* +0x56 */
    int16_t reaction_y;              /* +0x58 */
    uint8_t pad5a[2];
    uint16_t flags;                  /* +0x5c */
    uint8_t pad5e[6];
    int16_t collision_dx;            /* +0x64 */
    int16_t collision_dy;            /* +0x66 */
    int16_t collision_dz;            /* +0x68 */
    int16_t collision_radius;        /* +0x6a */
    int16_t reaction_timer;          /* +0x6c */
    int16_t hp;                      /* +0x6e */
    uint32_t mover_vm;               /* +0x70 */
    const void *model_collision;     /* +0x74 */
} ActorA05;

enum {
    BTN_CROSS = 0x4000,
    STATE_GROUNDED = 0,
    STATE_JUMP_TAKEOFF = 1,
    STATE_AIRBORNE = 2,
    STATE_LOW_SLAM = 3,
    STATE_HIGH_DIVE = 4,
    STATE_CONTACT_REBOUND = 5,
    GROUNDED_NATIVE = 0x0101,
    DIVE_FLOOR_GAP = 8193,
    DIVE_PHASE_START = 10,
    DIVE_SPEED = 4096,
    CONTACT_REBOUND_SPEED = -1536,
    IMPACT_RECOVERY_START = -6144,
    IMPACT_RECOVERY_STEP = 512,
    BONUS1_TARGET = 5,
    BONUS1_LOW_FLAG = 0x02,
    BONUS1_EARNED_FLAG = 0x20,
    BONUS_SCENE = 0x10,
};

extern void event_or_sound(int32_t id, const void *position);
extern void spawn_drop_burst_8_entry(ActorA05 *actor); /* 0x80057f44 */
extern int inside_actor_model_ellipsoid(const ActorA05 *actor,
                                        const PlayerA05 *player);

/* 0x80048B60..0x80048D68. The Phase-2 <=20-frame recognizer is not
 * represented here because it is an offline movie classifier, not retail state. */
static void abdomen_cross_admission(PlayerA05 *player, uint16_t buttons,
                                    int coyote_guard)
{
    if ((buttons & BTN_CROSS) == 0)
        return;

    if (player->air_state == STATE_JUMP_TAKEOFF || player->air_state >= 4)
        return;

    if (player->grounded != 0 ||
        (player->floor_y - player->y < 1024 && coyote_guard == 0)) {
        player->air_state = STATE_JUMP_TAKEOFF;
        player->grounded = 0;
        player->animation_selector = 3;
        return;
    }

    if (player->air_state != STATE_AIRBORNE)
        return;

    if (player->floor_y - player->y < DIVE_FLOOR_GAP) {
        player->air_state = STATE_LOW_SLAM;       /* 0x80048D64 */
        return;
    }

    event_or_sound(27, 0);
    player->dive_phase = DIVE_PHASE_START;        /* 0x80048CA8 */
    player->air_state = STATE_HIGH_DIVE;          /* 0x80048CBC */
    player->animation_selector = player->vy < 257 ? 2 : 7;
}

/* 0x80048D90..0x80048DD4. */
static void abdomen_advance_phase(PlayerA05 *player)
{
    if (player->dive_phase > 1) {
        player->dive_phase--;
        player->vy = 0;
    } else if (player->dive_phase == 1) {
        player->vy = DIVE_SPEED;
    } else if (player->dive_phase < 0) {
        player->dive_phase += IMPACT_RECOVERY_STEP;
    }
}

/* 0x80048B3C..0x80048B58 and 0x80048DD8..0x80048E98. */
static void abdomen_finish_high_dive(PlayerA05 *player, int was_grounded)
{
    if (player->air_state != STATE_HIGH_DIVE || !was_grounded)
        return;

    player->dive_phase = IMPACT_RECOVERY_START;
    player->action_timer = 12;
    player->vy = 0;
    player->air_state = STATE_JUMP_TAKEOFF;

    /* Retail also emits the radial particles, contact object 91 at Y-4096,
     * and sound 16. The timer==12 presentation path selects animation 28. */
}

static int inside_outer_contact_sphere(const ActorA05 *actor,
                                       const PlayerA05 *player)
{
    int32_t dx = ((actor->x + actor->collision_dx) - player->x) >> 5;
    int32_t dy = ((actor->y + actor->collision_dy) - (player->y - 7360)) >> 5;
    int32_t dz = ((actor->z + actor->collision_dz) - player->z) >> 5;
    int32_t radius = actor->collision_radius + 250;
    return dx * dx + dy * dy + dz * dz < radius * radius;
}

/* Decisive A05 tail in FUNC_8004ABF4 after the generic contact geometry.
 * `dive_phase` is loaded as unsigned at 0x8004B2AC. */
static void abdomen_actor_contact(PlayerA05 *player, ActorA05 *actor,
                                  uint32_t *streak, uint8_t *bonus_flags,
                                  int16_t *transition_latch,
                                  int16_t *fade_timer, uint32_t scene)
{
    if (!inside_outer_contact_sphere(actor, player) ||
        !inside_actor_model_ellipsoid(actor, player))
        return;

    if ((actor->flags & (0x20 | 0x40 | 0x80 | 0x800)) != 0)
        return;

    if ((uint16_t)player->dive_phase >= 2)
        return;

    event_or_sound(-4, 0);
    actor->reaction_timer = -20;
    actor->reaction_x = 4096;
    actor->reaction_y = 4096;
    spawn_drop_burst_8_entry(actor);

    /* This slice deliberately does not assign actor->hp. */
    if (player->dive_phase == 0) {
        player->vy = CONTACT_REBOUND_SPEED;
        player->air_state = STATE_CONTACT_REBOUND;
        player->grounded = 0;
        player->animation_selector = 3;
        return;
    }

    if ((*bonus_flags & BONUS1_EARNED_FLAG) != 0 || scene == BONUS_SCENE)
        return;

    uint32_t new_count = *streak + 1;
    *streak = new_count;
    if (new_count != BONUS1_TARGET)
        return;

    *bonus_flags |= BONUS1_LOW_FLAG;
    *transition_latch = 6;
    *fade_timer = 30;
    *streak = 0;
}

void abdomen_bounce_semantic_refs(void)
{
    (void)abdomen_cross_admission;
    (void)abdomen_advance_phase;
    (void)abdomen_finish_high_dive;
    (void)abdomen_actor_contact;
}
