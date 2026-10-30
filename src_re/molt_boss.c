/*
 * Documentation-grade reconstruction of the original Molt boss contract.
 * This is not a MOD implementation and does not replace byte-exact ASM.
 * Static owner: LEVEL03/LEVEL1.BIN at 0x800B3B2C..0x800B448C.
 */
#include <stddef.h>
#include <stdint.h>

enum {
    MOLT_ID = 29,
    MOLT_HP_INITIAL = 50,
    MOLT_HP_DEFEAT_THRESHOLD = 20,
    MOLT_ACCEPTED_HIT_DAMAGE = 2,
    MOLT_CROWD_RED_PICKUP_TYPE = 71,
    MOLT_CROWD_RED_PICKUP_ACTION = 32,
    MOLT_PLAYER_THROWN_RED_TYPE = 2,
    MOLT_TRANSITION_TICKS = 150
};

typedef struct MoltActor {
    uint32_t id;                 /* +0x00 */
    int32_t x, y, z;             /* +0x04..+0x0C */
    uint8_t unknown_10[0x34];
    uint32_t acceptance_gate;    /* +0x44: value 1 rejects/rolls back hit */
    uint8_t unknown_48[0x14];
    uint16_t flags;              /* +0x5C: 0x5043 in retained fight */
    uint8_t unknown_5e[0x0e];
    int16_t field_6c;
    int16_t hp;                  /* +0x6E */
    uint32_t vm_ip;              /* +0x70: 0x80077688 park_seek at hits */
    uint8_t unknown_74[8];
    uint32_t callback;           /* +0x7C: 0x8004A0A0 sound callback */
    uint32_t metadata;           /* +0x80 */
} MoltActor;

_Static_assert(offsetof(MoltActor, acceptance_gate) == 0x44, "gate offset");
_Static_assert(offsetof(MoltActor, flags) == 0x5c, "flags offset");
_Static_assert(offsetof(MoltActor, hp) == 0x6e, "HP offset");
_Static_assert(offsetof(MoltActor, vm_ip) == 0x70, "VM offset");
_Static_assert(offsetof(MoltActor, callback) == 0x7c, "callback offset");
_Static_assert(sizeof(MoltActor) == 0x84, "actor stride");

/* Exact branch at 0x800B3C98..0x800B3CC4. The transition latch also blocks
 * late contacts after the accepted defeat hit. */
static int molt_hit_is_blocked(const MoltActor *molt, int16_t goal_latch)
{
    return molt->acceptance_gate == 1 || goal_latch != 0;
}

/* Semantic form of the overlay's accepted-HP snapshot protocol. The shared
 * resident dispatcher has already written post_hit_hp before this runs. */
static int16_t molt_observe_post_hit(MoltActor *molt,
                                     int16_t accepted_hp_snapshot,
                                     int16_t goal_latch)
{
    if (molt_hit_is_blocked(molt, goal_latch)) {
        molt->hp = accepted_hp_snapshot;       /* 0x800B3CC4 */
        return accepted_hp_snapshot;
    }

    /* Original code also submits two type-11 hit effects and actor state 12. */
    accepted_hp_snapshot = molt->hp;           /* 0x800B3F0C */
    if (molt->hp < MOLT_HP_DEFEAT_THRESHOLD + 1) {
        /* Original writes goal_latch=1 and transition_timer=150, then submits
         * the victory effect/event chain. */
    }
    return accepted_hp_snapshot;
}

/* Semantic input contract for the producer at 0x800B41CC..0x800B4468.
 * A four-entry arena table supplies an origin. The producer aims toward Flik,
 * rejects distant origins, and allocates type 71 at 0x800B43F8. Metadata row
 * 71 selects action 32; its handler at 0x800588FC writes equip index 0 (red) at
 * 0x80058934. A later player throw is a distinct type-2 contact. */
static int crowd_throw_is_eligible(uint8_t random_low_two_bits,
                                   int16_t goal_latch,
                                   uint32_t squared_xz_distance)
{
    return random_low_two_bits == 0 && goal_latch == 0 &&
           squared_xz_distance <= 0x7ffffu;
}

void molt_boss_reference_contract(void)
{
    MoltActor actor = {0};
    volatile int16_t snapshot;
    actor.id = MOLT_ID;
    actor.hp = MOLT_HP_INITIAL;
    actor.flags = 0x5043;
    actor.vm_ip = 0x80077688u;
    actor.callback = 0x8004A0A0u;
    snapshot = molt_observe_post_hit(&actor, MOLT_HP_INITIAL, 0);
    (void)snapshot;
    (void)crowd_throw_is_eligible(0, 0, 0x7ffffu);
}
