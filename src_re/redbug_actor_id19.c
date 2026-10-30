/* Conservative D09 reconstruction from pristine SCUS_942.88. */
#include <stddef.h>
#include <stdint.h>

typedef struct RedbugActor {
    int32_t id;
    int32_t x, y, z;
    uint8_t unknown_10[0x4c];
    uint16_t flags;
    uint8_t unknown_5e[4];
    int16_t respawn_delay;
    uint8_t unknown_64[8];
    int16_t reaction;
    int16_t hp;
    const uint16_t *program;
    uint8_t unknown_74[0x0c];
    const uint8_t *spawn;
} RedbugActor;

_Static_assert(offsetof(RedbugActor, flags) == 0x5c, "flags offset");
_Static_assert(offsetof(RedbugActor, respawn_delay) == 0x62, "delay offset");
_Static_assert(offsetof(RedbugActor, hp) == 0x6e, "hp offset");
_Static_assert(offsetof(RedbugActor, program) == 0x70, "program offset");
_Static_assert(offsetof(RedbugActor, spawn) == 0x80, "spawn offset");

enum {
    REDBUG_ID = 19,
    ACTOR_FLAG_CHASE = 0x0002,
    ACTOR_KO_FLAGS = 0x0880,
    ACTOR_KO_SENTINEL = 999
};

static int16_t projectile_hp_delta(uint8_t marker)
{
    switch (marker) {
    case 0:
    case 12:  return -2;
    case 1:   return -99;
    case 127: return -4;
    case 128: return -3;
    default:  return -1;
    }
}

static void redbug_landed_hit(RedbugActor *actor, uint8_t marker)
{
    actor->hp = (int16_t)(actor->hp + projectile_hp_delta(marker));
    actor->flags |= ACTOR_FLAG_CHASE;
}

static int redbug_substitutes_player_goal(const RedbugActor *actor,
                                          unsigned parked_mode,
                                          int32_t distance_squared,
                                          int32_t chase_radius_squared)
{
    return (actor->flags & ACTOR_FLAG_CHASE) != 0 && parked_mode < 3 &&
           distance_squared < chase_radius_squared;
}

static void redbug_begin_temporary_ko(RedbugActor *actor,
                                     const uint16_t *stop_program)
{
    actor->hp = ACTOR_KO_SENTINEL;
    actor->flags = (uint16_t)((actor->flags | ACTOR_KO_FLAGS) &
                              ~ACTOR_FLAG_CHASE);
    actor->program = stop_program;
}

void redbug_actor_id19_reconstruction_refs(RedbugActor *actor,
                                           uint8_t marker,
                                           const uint16_t *stop_program)
{
    if (actor && actor->id == REDBUG_ID) {
        redbug_landed_hit(actor, marker);
        (void)redbug_substitutes_player_goal(actor, 0, 0, 1);
        if (actor->hp <= 0)
            redbug_begin_temporary_ko(actor, stop_program);
    }
}
