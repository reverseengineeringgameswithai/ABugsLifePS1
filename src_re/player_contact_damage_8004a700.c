/*
 * Documentation-grade reconstruction of D03 ordinary enemy contact damage.
 * This is semantic source, not compiler-matching replacement source.
 *
 * Pristine resident paths:
 *   0x8004ABF4  actor/player broad-sphere and pose-ellipsoid admission
 *   0x8004B4A0  actor body-contact call to the shared handler
 *   0x8004A700  shared damage, suppression, and knockback handler
 *   0x8004853C  signed stagger-timer tick
 *
 * The retail handler also accepts nonzero special kinds. They bypass the
 * ordinary contact-health lane and are intentionally outside this model.
 */

#include <stdbool.h>
#include <stdint.h>

enum {
    CONTACT_KIND_ORDINARY = 0,
    CONTACT_HEALTH_DELTA = -1,
    CONTACT_VERTICAL_LAUNCH = -1024,
    CONTACT_STAGGER_TICKS = 45,
    CONTACT_INTERCEPT_TICKS = -30,
    CONTACT_PLAYER_RADIUS = 250,
    REGION_INTERCEPT_ONE = 1,
    REGION_INTERCEPT_FIVE = 5
};

typedef struct ContactActorFields {
    uint32_t id;                 /* +0x00 */
    int32_t x, y, z;             /* +0x04..+0x0C */
    uint8_t pad10[0x34];
    uint32_t pose_index;         /* +0x44 */
    uint8_t pad48[0x14];
    uint16_t flags;              /* +0x5C */
    uint8_t pad5e[0x06];
    int16_t broad_offset_x;      /* +0x64 */
    int16_t broad_offset_y;      /* +0x66 */
    int16_t broad_offset_z;      /* +0x68 */
    int16_t broad_radius;        /* +0x6A */
    int16_t reaction_lockout;    /* +0x6C */
    int16_t hp;                  /* +0x6E; not used by player damage */
    uint32_t mover_program;      /* +0x70 */
    uint32_t pose_hitboxes_address;   /* +0x74 */
} ContactActorFields;

typedef struct ContactPlayerState {
    int32_t x, y, z;
    int32_t velocity_x, velocity_y, velocity_z;
    int16_t power_slot;
    int16_t state;
    int16_t grounded;
    int16_t air_timer;
    int16_t substate;
    uint16_t flags;
    int16_t stagger_timer;
    int16_t health;
    int16_t interaction_latch;
} ContactPlayerState;

static int64_t square_i32(int32_t value)
{
    return (int64_t)value * value;
}

bool contact_broad_sphere_contains_player(const ContactActorFields *actor,
                                          const ContactPlayerState *player)
{
    int32_t dx = (actor->x + actor->broad_offset_x - player->x) >> 5;
    int32_t dy = (actor->y + actor->broad_offset_y -
                  (player->y - 7360)) >> 5;
    int32_t dz = (actor->z + actor->broad_offset_z - player->z) >> 5;
    int32_t radius = actor->broad_radius + CONTACT_PLAYER_RADIUS;
    return square_i32(dx) + square_i32(dy) + square_i32(dz) <
           square_i32(radius);
}

/*
 * Broad-sphere success is necessary but not sufficient. 0x8004AD14..0x8004AE8C
 * selects actor->pose_hitboxes[actor->pose_index], rotates the player delta by
 * the actor heading, scales it by three pose-local axes, and requires a second
 * ellipsoid test with its radius also expanded by 250. This is why enemy-family
 * and animation differences affect contact reach without changing damage.
 */

void contact_stagger_tick(ContactPlayerState *player)
{
    if (player->stagger_timer > 0)
        player->stagger_timer--;
    else if (player->stagger_timer < 0)
        player->stagger_timer++;
}

typedef enum ContactResult {
    CONTACT_SUPPRESSED_BY_STAGGER,
    CONTACT_INTERCEPTED,
    CONTACT_DAMAGED,
    CONTACT_FATAL
} ContactResult;

ContactResult ordinary_contact_apply(ContactPlayerState *player,
                                     int16_t region_code,
                                     int32_t normalized_x,
                                     int32_t normalized_z)
{
    /* 0x8004A744..0x8004A78C occurs before every suppression test. */
    player->velocity_x = normalized_x >> 2;
    player->velocity_z = normalized_z >> 2;

    /* A positive timer suppresses health and vertical launch without refresh. */
    if (player->stagger_timer > 0)
        return CONTACT_SUPPRESSED_BY_STAGGER;

    player->flags |= 0x0002;
    if (player->power_slot != 0 || region_code == REGION_INTERCEPT_ONE ||
        region_code == REGION_INTERCEPT_FIVE) {
        if (player->power_slot < 0 && player->stagger_timer == 0)
            player->power_slot++;
        if (!(player->power_slot < 0 && player->stagger_timer != 0))
            player->stagger_timer = CONTACT_INTERCEPT_TICKS;
        return CONTACT_INTERCEPTED;
    }

    player->state = 5;
    player->velocity_y = CONTACT_VERTICAL_LAUNCH;
    player->air_timer = 0;
    player->grounded = 0;
    player->substate = 0;
    player->interaction_latch = 0;
    player->health = (int16_t)(player->health + CONTACT_HEALTH_DELTA);
    player->stagger_timer = player->health < 0 ?
                            -CONTACT_STAGGER_TICKS : CONTACT_STAGGER_TICKS;
    return player->health < 0 ? CONTACT_FATAL : CONTACT_DAMAGED;
}
