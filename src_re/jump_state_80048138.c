/* Documentation-grade C for the shipping A03 jump state machine.
 * Shipping source: asm/hand_written/80048138_player_vertical_update.s
 * This is not a build unit and does not replace the byte-matched ASM.
 */

#include <stdint.h>

enum {
    PLAYER_GROUNDED = 0,
    PLAYER_JUMP_HELD = 1,
    PLAYER_AIRBORNE_RELEASED = 2,
    PLAYER_SLAM_ARMED = 3,
    PLAYER_SLAM = 4,
    PLAYER_LANDING = 5,
    PLAYER_LANDING_FOLLOWUP = 6
};

typedef struct JumpState {
    int32_t y;              /* player +0x04 */
    int32_t velocity_y;     /* player +0x30 */
    int32_t floor_y;        /* player +0x48 */
    uint8_t state;          /* player +0x80 */
    uint16_t grounded;      /* player +0x82 */
    uint16_t animation;     /* player +0x88 */
    uint16_t power_flags;   /* player +0x90 */
} JumpState;

static int32_t mips_sra1(int32_t value)
{
    return value >= 0 ? value / 2 : -(((-value) + 1) / 2);
}

/* Cross admission at 0x80048B5C..0x80048C6C. The caller-side a0 gate is
 * represented by action_blocked. The gp+0x69c value is coyote_guard. */
static int jump_is_admitted(const JumpState *p, int cross,
                            int action_blocked, int coyote_guard)
{
    if (!cross || action_blocked || p->state == PLAYER_JUMP_HELD ||
        p->state >= PLAYER_SLAM)
        return 0;
    if (p->animation == 8)
        return 0;
    if (p->grounded != 0)
        return 1;
    return (p->floor_y - p->y) < 1024 && coyote_guard == 0;
}

/* One player vertical update. Collision response is intentionally outside this
 * function: FUNC_8003633C and its swept-plane passes commit Y and are the sole
 * producer of grounded=0x0101. */
void jump_vertical_tick(JumpState *p, int cross, int action_blocked,
                        int coyote_guard)
{
    if (jump_is_admitted(p, cross, action_blocked, coyote_guard)) {
        p->velocity_y = (p->power_flags & 0x20) ? -3776 : -3072;
        p->state = PLAYER_JUMP_HELD;
        p->grounded = 0;
        p->animation = 3;
    } else if (!cross && p->state == PLAYER_JUMP_HELD) {
        if (p->velocity_y < 0) {
            if (p->velocity_y < -800)
                p->velocity_y += 384;
            p->velocity_y = mips_sra1(p->velocity_y);
            p->velocity_y -= 256;
        }
        p->state = PLAYER_AIRBORNE_RELEASED;
    } else if (!cross && p->grounded != 0) {
        p->state = PLAYER_GROUNDED;
    }

    if (p->grounded == 0) {
        p->velocity_y += 256;
        if (p->velocity_y > 4096)
            p->velocity_y = 4096;
    }
}

/* Scope boundary for Phase 4 A03:
 * - A13 owns the separate Cross-edge carried-seed output selector.
 * - A15 owns jump + butt-slam contact at 0x8004AF80 and the subsequent seed
 *   sink/spawn lifecycle ending at FUNC_8005BDBC.
 * Neither mechanism changes the recurrence above.
 */
