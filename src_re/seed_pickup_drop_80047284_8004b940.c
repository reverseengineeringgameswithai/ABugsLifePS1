/*
 * Phase 4 A09 semantic reconstruction: movable-seed pickup, carry, and drop.
 *
 * Documentation-grade semantic C, not byte-matching build source.
 * Pristine ASM owners:
 *   player_contact_response 0x80047284..0x80047EB8
 *   actor update             0x8004B940..0x8004C15C
 *   generic detach helper    0x80046CAC..0x80046D20
 */
#include <stdbool.h>
#include <stdint.h>

enum {
    PLAYER_BASE = 0x800A6500u,
    ACTOR_OFFSET_BASE = 0x8009FD80u,
    CARRY_OFFSET_ADDR = 0x800A655Cu,
    CARRY_MODE_ADDR = 0x800A65A3u,
    ACTOR_FLAG_PICKUP = 0x0020u,
    ACTOR_FLAG_CARRIED = 0x0040u,
    CARRY_Y_OFFSET = 19200,
    PICKUP_RADIUS_SQ_QUANTIZED = 0x270ff,
    PICKUP_FACING_WINDOW = 1024
};

typedef struct SeedActorA09 {
    uint32_t id;             /* +0x00; movable seed id is 11 */
    int32_t x, y, z;         /* +0x04..+0x0C */
    uint8_t unknown_10[0x0c];
    int32_t velocity_x;      /* +0x1C */
    int32_t velocity_y;      /* +0x20 */
    int32_t velocity_z;      /* +0x24 */
    uint8_t unknown_28[0x18];
    int32_t behavior_state;  /* +0x40 */
    uint8_t unknown_44[0x18];
    uint16_t flags;          /* +0x5C */
    int16_t enabled_5e;      /* +0x5E */
} SeedActorA09;

typedef struct PlayerSeedA09 {
    int32_t x, y, z;         /* +0x00..+0x08 */
    uint8_t unknown_0c[0x14];
    int32_t heading;         /* +0x20 */
    uint8_t unknown_24[0x08];
    int32_t motion_x;        /* +0x2C */
    int32_t motion_y;        /* +0x30 */
    int32_t motion_z;        /* +0x34 */
    uint8_t unknown_38[0x24];
    int32_t carried_offset;  /* +0x5C; actor - 0x8009FD80 */
    uint8_t unknown_60[0x1a];
    int16_t action_lock_7a;  /* +0x7A */
    uint8_t unknown_7c[0x06];
    int16_t gate_82;         /* +0x82 */
    int16_t gate_84;         /* +0x84 */
    uint8_t unknown_86[2];
    int16_t action_state_88; /* +0x88 */
    uint8_t unknown_8a[0x16];
    uint8_t carry_mode_a3;   /* +0xA3 */
} PlayerSeedA09;

/* 0x80047788..0x80047840. angle_delta is already reduced modulo 0x1000. */
static bool movable_seed_pickup_candidate(const PlayerSeedA09 *p,
                                          const SeedActorA09 *seed,
                                          uint32_t angle_delta)
{
    int32_t dx = (seed->x - p->x) >> 5;
    int32_t dy = (seed->y - p->y) >> 5;
    int32_t dz = (seed->z - p->z) >> 5;
    int32_t distance_sq = dx * dx + dy * dy + dz * dz;

    return (seed->flags & ACTOR_FLAG_PICKUP) != 0 &&
           seed->enabled_5e != 0 && seed->behavior_state != 4 &&
           distance_sq <= PICKUP_RADIUS_SQ_QUANTIZED &&
           angle_delta < PICKUP_FACING_WINDOW;
}

/* 0x80047858..0x80047890 after a fresh Square edge and the player-state gates. */
static void movable_seed_pickup_commit(PlayerSeedA09 *p, SeedActorA09 *seed)
{
    p->carried_offset = (int32_t)((uintptr_t)seed - ACTOR_OFFSET_BASE);
    p->carry_mode_a3 = (seed->behavior_state < 3) ? 8 : 14;
    seed->flags |= ACTOR_FLAG_CARRIED;
    p->motion_x = 0;
    p->motion_z = 0;
}

/* 0x8004BA38..0x8004BB00. Mode 11 raises and centers the carried actor. */
static void movable_seed_lift_mode_11(PlayerSeedA09 *p, SeedActorA09 *seed)
{
    int32_t dy = p->y - (seed->y + CARRY_Y_OFFSET);
    if (dy > 2048) dy = 2048;
    if (dy < -2048) dy = -2048;
    seed->velocity_y = dy;

    if (dy > -2048 && dy < 2048) {
        seed->velocity_x = (p->x - seed->x) >> 2;
        seed->velocity_z = (p->z - seed->z) >> 2;
        if (seed->velocity_x > -128 && seed->velocity_x < 128 &&
            dy > -128 && dy < 128 &&
            seed->velocity_z > -128 && seed->velocity_z < 128)
            p->carry_mode_a3 = 12;
    }
}

/* 0x8004BB68..0x8004BC10. A separated mode-12 seed cancels attachment. */
static bool movable_seed_mode_12_is_valid(const PlayerSeedA09 *p,
                                           const SeedActorA09 *seed)
{
    int32_t dx = (p->x - seed->x) >> 5;
    int32_t dy = (p->y - (seed->y + CARRY_Y_OFFSET)) >> 5;
    int32_t dz = (p->z - seed->z) >> 5;
    return dx * dx + dy * dy + dz * dz < 10001;
}

/*
 * 0x80047C1C..0x80047D00, positive carried_offset branch.
 * There is no environment-obstruction denial in this release gate. World collision
 * affects the seed only after it has been detached and given outward motion.
 */
static void movable_seed_manual_drop(PlayerSeedA09 *p, SeedActorA09 *seed,
                                     int32_t throw_x, int32_t throw_z)
{
    seed->flags &= (uint16_t)~ACTOR_FLAG_CARRIED;
    if (seed->behavior_state < 3) {
        seed->velocity_x = throw_x;
        seed->velocity_y = 0;
        seed->velocity_z = throw_z;
        p->action_state_88 = 14;
    } else {
        p->action_state_88 = 17;
    }
    p->carried_offset = 0;
    p->motion_x = 0;
    p->motion_z = 0;
    p->carry_mode_a3 = 13; /* transient release mode; later state update returns 0 */
}

/*
 * Other clearers are lifecycle consumers, not alternate pickup owners:
 * 0x80046D04 generic forced detach; 0x80048394 action cancellation;
 * 0x8004BB38 mode-11 timeout; 0x8004BBF8 mode-12 separation;
 * 0x8005B258 respawn transition; 0x8005C204 cannon consumption.
 */
