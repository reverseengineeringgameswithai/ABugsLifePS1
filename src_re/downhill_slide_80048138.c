/*
 * Evidence-oriented C reconstruction of Phase 4 A06.
 * This is documentation, not a matching decompilation or build input.
 *
 * The ordinary held-Cross slide and the player+0x8c contact-projector fast
 * path are deliberately modeled as separate routes.
 */
#include <stdint.h>

typedef struct PlayerSlideSlice {
    int32_t position_x;
    int32_t position_y;
    int32_t position_z;
    uint8_t pad0c[0x14];
    int32_t heading;
    uint8_t pad24[0x04];
    int32_t target_heading;
    int32_t velocity_x;
    int32_t velocity_y;
    int32_t velocity_z;
    int32_t projected_lateral;
    int32_t projected_forward;
    uint8_t pad40[0x04];
    int32_t animation_progress;
    int32_t floor_y;
    uint8_t pad4c[0x2e];
    int16_t action_timer;
    uint8_t pad7c[0x04];
    int16_t action_state;
    int16_t grounded;
    int16_t dive_phase;
    uint8_t pad86[0x02];
    int16_t animation_selector;
    int16_t latched_animation_selector;
    int16_t terrain_contact_slot_plus_one;
} PlayerSlideSlice;

static int32_t absolute_i32(int32_t value)
{
    return value < 0 ? -value : value;
}

static int32_t wrapped_heading_step(int32_t current, int32_t target,
                                    int32_t cap, unsigned shift)
{
    int32_t delta = (current - target) & 0x0fff;
    int32_t magnitude;

    if (delta > 0x0800) {
        magnitude = 0x1000 - delta;
        if (magnitude > cap)
            magnitude = cap;
        current += magnitude >> shift;
    } else {
        magnitude = delta;
        if (magnitude > cap)
            magnitude = cap;
        current -= magnitude >> shift;
    }
    return current & 0x0fff;
}

void phase4_a06_apply_ordinary_steering(PlayerSlideSlice *player,
                                        int turn_negative, int turn_positive)
{
    /* 0x800490D0 and 0x80049100 on the default ordinary input route. */
    if (turn_negative)
        player->target_heading -= 0x20;
    if (turn_positive)
        player->target_heading += 0x20;
    player->target_heading &= 0x0fff;

    /* Default fcn.80048138 parameters: cap 0x400, shift 2. */
    player->heading = wrapped_heading_step(player->heading,
                                           player->target_heading,
                                           0x400, 2);
}

void phase4_a06_ordinary_latch(PlayerSlideSlice *player, int cross_down)
{
    if (!cross_down) {
        /* 0x80048D00..0x80048D10: release clears only when grounded. */
        if (player->grounded)
            player->action_state = 0;
        return;
    }

    /* 0x80048CD8..0x80048D64: held + grounded state 4 or later -> 5. */
    if (player->action_state >= 4 && player->grounded)
        player->action_state = 5;
}

void phase4_a06_slide_maintenance(PlayerSlideSlice *player, int cross_down)
{
    int16_t desired = 0;

    /* 0x80048EC8..0x80048ED4 decrements a positive timer. */
    if (player->action_timer > 0)
        player->action_timer--;

    /*
     * 0x80048EE8..0x80048F3C: only the 12 -> 11 update can rearm.
     * The first projected component is compared signed; the second uses abs.
     */
    if (player->action_timer == 11 && cross_down &&
        (player->projected_lateral >= 0x300 ||
         absolute_i32(player->projected_forward) >= 0x300)) {
        player->action_timer = 12;
    }

    /* Slide 0x1c -> recovery 0x06 -> ordinary fallback as the timer expires. */
    if (player->action_timer > 0)
        desired = 0x06;
    if (player->action_timer == 12)
        desired = 0x1c;
    player->animation_selector = desired;

    /* 0x80056988..0x800569AC resets animation progress on selector changes. */
    if (player->latched_animation_selector != desired) {
        player->animation_progress = 0;
        player->latched_animation_selector = desired;
    }
}

void phase4_a06_dive_admission(PlayerSlideSlice *player, int cross_down)
{
    /* No slope-angle predicate: state 2 uses vertical floor separation. */
    if (cross_down && player->action_state == 2 &&
        player->floor_y - player->position_y > 0x2000) {
        player->dive_phase = 10;
        player->action_state = 4;
    }
}

/*
 * The distinct 0x800488D8..0x80048A70 route is entered only when
 * terrain_contact_slot_plus_one is nonzero. It has its own 0x80 heading cap,
 * surface projection, and new-Cross jump. The A06 Interpreter movies execute
 * the ordinary route above with no +0x8c writes.
 */
