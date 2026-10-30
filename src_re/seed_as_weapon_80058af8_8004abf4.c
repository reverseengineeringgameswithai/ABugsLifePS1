#include <stdbool.h>
#include <stdint.h>

/*
 * Documentation-grade reconstruction of the two resident seed/contact KO arms.
 * This is semantic source, not compiler-matching replacement source.
 *
 * Pristine sites:
 *   0x80058DE4..0x80058E38  contact-kind-4 arm used by A11's thrown seed
 *   0x8004B2AC..0x8004B2E0  alternate dropped-object subtype arm
 *
 * The A11 capsule executes the first arm. Both arms write reaction state, not HP.
 */

typedef struct ActorA11 {
    uint32_t id;                 /* +0x00 */
    int32_t x, y, z;             /* +0x04..+0x0C */
    uint8_t pad10[0x44];
    int16_t reaction_x;          /* +0x54 */
    int16_t reaction_z;          /* +0x56 */
    int16_t reaction_y;          /* +0x58 */
    int16_t reaction_state;      /* +0x5A */
    uint16_t flags;              /* +0x5C */
    uint8_t pad5e[0x0E];
    int16_t knockback;           /* +0x6C */
    int16_t hp;                  /* +0x6E, deliberately untouched here */
} ActorA11;

enum {
    ACTOR_CONTACT_REJECT_MASK = 0x00A0,
    ACTOR_KIND4_REJECT_FLAG = 0x0040,
    CONTACT_KIND_SEED = 4,
    SEED_KO_COUNTDOWN = -20,
    REACTION_COMPONENT = 4096,
    IMPACT_CUE = 17
};

extern void sfx_dispatch(int id);                    /* 0x80050994 */
extern void spawn_impact_burst_8(ActorA11 *actor);  /* entry 0x80057F44 */
extern void play_sound(int id, const void *xyz);    /* 0x8005044C */

static bool actor_contact_prefilter(const ActorA11 *actor)
{
    return (actor->flags & ACTOR_CONTACT_REJECT_MASK) == 0 &&
           actor->knockback >= 0;
}

static void apply_seed_ko_reaction(ActorA11 *actor)
{
    sfx_dispatch(-4);
    actor->knockback = SEED_KO_COUNTDOWN;
    actor->reaction_x = REACTION_COMPONENT;
    actor->reaction_y = REACTION_COMPONENT;
    spawn_impact_burst_8(actor);
    play_sound(IMPACT_CUE, &actor->x);

    /* No actor->hp assignment exists in either native arm. */
}

bool carried_contact_kind4_seed_hit(ActorA11 *actor, uint8_t contact_kind)
{
    if (!actor_contact_prefilter(actor))
        return false;
    if (contact_kind != CONTACT_KIND_SEED)
        return false;
    if ((actor->flags & ACTOR_KIND4_REJECT_FLAG) != 0)
        return false;
    apply_seed_ko_reaction(actor);
    return true;
}

bool alternate_dropped_object_seed_hit(ActorA11 *actor,
                                       uint16_t collision_subtype)
{
    if (!actor_contact_prefilter(actor))
        return false;
    if (collision_subtype >= 2)
        return false;
    apply_seed_ko_reaction(actor);
    return true;
}

