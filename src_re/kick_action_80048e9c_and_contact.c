/*
 * Documentation-grade reconstruction of the retail kick action and its
 * actor-contact branch. This is evidence-oriented C, not a linkable game unit.
 *
 * Input/timer/animation sites:
 *   0x80048EA4..0x80048ED4  signed action timer approaches zero
 *   0x80048F4C..0x80048FB4  kick admission and timer := -16
 *   0x800563D4              timer-to-animation selection
 *   0x80055654              kick effect emission
 *
 * Actor contact/reaction sites:
 *   0x8004ABF4              actor/player proximity updater
 *   0x8004B450              kick-facing success branch
 *   0x8004B4A0              normal player-damage call (skipped by kick)
 *   0x8004B5D8              ordinary reaction knockback := 30
 *   0x8004B638              optional chase flag |= 2
 *   0x8004B644              player impact animation := 30
 *   0x8004B650              flag-0x80 reduced knockback := 15
 *
 * Kick-effect damage sites (a separate, later path):
 *   0x80058B54              reject actor flags 0x20 or 0x80
 *   0x80058ED8              accepted contact knockback := 20
 *   0x80058EE4              actor flag 0x40 special-reaction selector
 *   0x80059094              action class 1 selects HP - 99
 *   0x800590E4              stores the action-class HP result
 *   0x800592A8              death tail writes HP := 999
 */

#include <stdbool.h>
#include <stdint.h>

enum {
    PAD_L2_R2 = 0x0300,
    PAD_SQUARE = 0x8000,
    KICK_INITIAL_TIMER = -16,
    ANIM_KICK = 1,
    ANIM_KICK_IMPACT = 30,
    ACTOR_FLAG_OPTIONAL_CHASE = 0x0002,
    ACTOR_FLAG_KICK_SPECIAL = 0x0040,
    ACTOR_FLAG_REDUCED_KICK = 0x0080,
    ACTOR_FLAG_KICK_CONTACT = 0x1000,
    ACTOR_FLAG_CONTACT_DAMAGE_SKIP = 0x00a0,
    CONTACT_ACTION_KICK = 1
};

typedef struct KickActorFields {
    int32_t x;
    int32_t y;
    int32_t z;
    int16_t collision_x;
    int16_t collision_y;
    int16_t collision_z;
    int16_t collision_radius;
    uint16_t flags;       /* retail actor +0x5C */
    int16_t knockback;    /* retail actor +0x6C */
    int16_t hp;           /* retail actor +0x6E; not changed here */
} KickActorFields;

static int32_t abs_i32(int32_t value)
{
    return value < 0 ? -value : value;
}

int16_t kick_action_timer_tick(int16_t timer)
{
    if (timer < 0)
        return (int16_t)(timer + 1);
    if (timer > 0)
        return (int16_t)(timer - 1);
    return 0;
}

bool kick_try_arm(uint16_t pad_now, uint16_t pad_previous,
                  int32_t player_y, int32_t floor_y,
                  uint16_t player_state_5c, int16_t *action_timer)
{
    if ((pad_now & PAD_L2_R2) == 0)
        return false;
    if ((pad_now & PAD_SQUARE) == 0 ||
        (pad_previous & PAD_SQUARE) != 0)
        return false;
    if (*action_timer < 0 || player_state_5c != 0)
        return false;
    if (abs_i32(player_y - floor_y) >= 1024)
        return false;

    *action_timer = KICK_INITIAL_TIMER;
    return true;
}

int kick_animation_for_timer(int16_t timer)
{
    if (timer < 0)
        return ANIM_KICK;
    if (timer == 12)
        return 28;
    if (timer > 0)
        return 6;
    return 0;
}

void kick_emit_effects(int animation, int16_t timer,
                       void (*spawn_ctor108)(void),
                       void (*spawn_ctor109)(void))
{
    if (animation != ANIM_KICK || timer < -7 || timer > -2)
        return;

    if (timer == -7)
        spawn_ctor108();
    spawn_ctor109();
}

bool kick_effect_actor_prefilter(uint16_t actor_flags, int16_t knockback)
{
    /* 0x80058B54 and 0x80058B68 in the generic contact-object hit tail. */
    return (actor_flags & ACTOR_FLAG_CONTACT_DAMAGE_SKIP) == 0 &&
           knockback >= 0;
}

bool kick_effect_uses_flag40_special(uint16_t actor_flags,
                                     int16_t contact_mode_24,
                                     uint8_t action_id)
{
    /*
     * 0x80058EE4..0x80058F10. For ctor109, action_id is 1, so an
     * actor carrying flag 0x40 consumes the kick as a special reaction and
     * bypasses the HP-class dispatcher.
     */
    return (actor_flags & ACTOR_FLAG_KICK_SPECIAL) != 0 &&
           (contact_mode_24 == 1 || action_id == CONTACT_ACTION_KICK);
}

int16_t contact_action_hp_after_hit(int16_t hp, uint8_t action_id)
{
    switch (action_id) {
    case CONTACT_ACTION_KICK:
        return (int16_t)(hp - 99);
    case 0:
    case 12:
        return (int16_t)(hp - 2);
    case 0x7f:
        return (int16_t)(hp - 4);
    case 0x80:
        return (int16_t)(hp - 3);
    default:
        return hp;
    }
}

bool kick_broad_sphere_contains_player(const KickActorFields *actor,
                                       int32_t player_x,
                                       int32_t player_y,
                                       int32_t player_z)
{
    int32_t actor_x = actor->x + actor->collision_x;
    int32_t actor_y = actor->y + actor->collision_y;
    int32_t actor_z = actor->z + actor->collision_z;
    int32_t dx = (actor_x - player_x) >> 5;
    int32_t dy = (actor_y - (player_y - 7360)) >> 5;
    int32_t dz = (actor_z - player_z) >> 5;
    int32_t radius = actor->collision_radius + 250;

    return dx * dx + dy * dy + dz * dz <= radius * radius;
}

bool kick_contact_gate(int16_t action_timer, int player_animation,
                       uint16_t player_to_actor_angle_delta,
                       bool actor_state_ellipsoid_contains_player)
{
    uint16_t angle = player_to_actor_angle_delta & 0x0fff;
    bool in_forward_half_plane = angle <= 1024 || angle >= 3072;

    if (action_timer >= 0 || !in_forward_half_plane)
        return false;
    if (player_animation == 11 || player_animation == 12 ||
        player_animation == ANIM_KICK_IMPACT)
        return false;
    return actor_state_ellipsoid_contains_player;
}

void kick_apply_actor_reaction(KickActorFields *actor,
                               bool chase_exception_allows_flag,
                               int16_t *player_animation)
{
    uint16_t flags_before_contact = actor->flags;

    actor->flags |= ACTOR_FLAG_KICK_CONTACT;
    if ((flags_before_contact & ACTOR_FLAG_REDUCED_KICK) != 0) {
        actor->knockback = 15;
        return;
    }

    actor->knockback = 30;
    if (chase_exception_allows_flag)
        actor->flags |= ACTOR_FLAG_OPTIONAL_CHASE;
    *player_animation = ANIM_KICK_IMPACT;

    /* This body-contact branch does not write HP. The later ctor109 effect does. */
}
