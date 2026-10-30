/*
 * grain_contact_convergence_8005a308.c
 *
 * Documentation-grade extraction of the common homing branch inside the
 * resident 64-record contact updater. The historical name
 * "berry_projectile_update" describes important branches but is too narrow:
 * ctor 0x51 grain records use this common branch as well.
 *
 * This is not a matching-C build unit. The exact 0x8005A308 function slice,
 * ctor-0x51 metadata row, and key instructions are checked by the Phase-4
 * collectibles frontier generator.
 */

#include "re_types.h"

typedef struct GrainContactMotion {
    int32_t x;             /* +0x00 */
    int32_t y;             /* +0x04 */
    int32_t z;             /* +0x08 */
    int32_t velocity_x;    /* +0x0C */
    int32_t target;        /* +0x10: -1 selects player */
    int32_t velocity_z;    /* +0x14 */
    int32_t heading;       /* +0x18, 12-bit turn */
    int32_t scratch;       /* +0x1C */
    uint16_t action_id;    /* +0x20: ctor 0x51 => 20 */
    int16_t active_gate;   /* +0x22: ctor 0x51 => 200 */
    int16_t phase;         /* +0x24: ctor 0x51 => 210 */
    int16_t phase_reload;  /* +0x26 */
    int16_t radius_add;    /* +0x28: ctor 0x51 => 100 */
    int16_t field_2a;      /* +0x2A: ctor 0x51 => 100 */
    int16_t state;         /* +0x2C: ctor 0x51 => 22 */
    int8_t ctor_sign;      /* +0x2E */
    uint8_t selector;      /* +0x2F: ctor 0x51 => 0 */
    uint8_t phase_mod;     /* +0x30 */
    uint8_t phase_step;    /* +0x31 */
    uint8_t field_32;      /* +0x32 */
    uint8_t flags;         /* +0x33: ctor 0x51 => 0xEA */
} GrainContactMotion;

#define PLAYER_X (*(int32_t *)0x800A6500u)
#define PLAYER_Y (*(int32_t *)0x800A6504u)
#define PLAYER_Z (*(int32_t *)0x800A6508u)

extern int32_t atan2_turn_80060ae4(int32_t x, int32_t z);
extern int16_t sine_table_80074970[4096];

static int32_t clamp_vertical_step(int32_t value)
{
    if (value > 0x400) {
        return 0x400;
    }
    if (value < -0x400) {
        return -0x400;
    }
    return value;
}

void grain_contact_common_convergence(GrainContactMotion *record)
{
    /*
     * ctor 0x51 sets flags=0xEA, so flags bit 0x08 enables this branch and the
     * signed active gate is decremented before motion. source3f explicitly
     * overwrites target to -1, selecting player coordinates rather than an
     * actor target.
     */
    if (!(record->flags & 0x08)) {
        record->x += record->velocity_x;
        record->z += record->velocity_z;
        return;
    }

    record->active_gate--;
    if (record->active_gate > 0 && record->target == -1) {
        uint32_t desired = (uint32_t)atan2_turn_80060ae4(
            PLAYER_X - record->x, PLAYER_Z - record->z);
        uint32_t delta = (desired - (uint32_t)record->heading) & 0xFFF;

        /*
         * Preserve the native piecewise turn law exactly. The negative arm
         * uses 0x800-delta, not the conventional 0x1000-delta shortest-arc
         * expression.
         */
        if (delta < 0x800) {
            record->heading += (int32_t)delta >> 2;
        } else {
            record->heading += (int32_t)(0x800 - delta) >> 2;
        }
        record->heading &= 0xFFF;

        /*
         * Move one eighth of the vertical error toward playerY-0x2000, with a
         * per-update clamp of +/-0x400 native coordinate units.
         */
        record->y -= clamp_vertical_step(
            (record->y + 0x2000 - PLAYER_Y) >> 3);

        record->velocity_x =
            (int16_t)sine_table_80074970[record->heading] >> 3;
        record->velocity_z =
            (int16_t)sine_table_80074970[(record->heading + 0x400) & 0xFFF] >> 3;
    }

    record->x += record->velocity_x;
    record->z += record->velocity_z;
}

/*
 * Distinct radii must not be conflated:
 * - source3f kind 0x14 constructs ctor 0x51 only at squared distance <=0x15F8F;
 * - ctor 0x51 retains radius_add=100;
 * - the native pickup walker uses 300+radius_add, hence radius 400.
 */
