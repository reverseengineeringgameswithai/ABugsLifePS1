/* Documentation-grade reconstruction of the ordinary grounded movement core
 * inside FUNC_80048138. This is not a build unit and deliberately leaves the
 * camera-vector resolver and trig table as named boundaries.
 */
#include <stdint.h>

enum {
    A01_ANGLE_MASK = 0x0fff,
    A01_DIRECTION_MASK = 0x00f0,
    A01_SLOW_MASK = 0x0300,
    A01_RUN_CAP = 0x0700,
    A01_SLOW_CAP = 0x0300,
    A01_FORWARD_HARD_CAP = 0x0800,
    A01_LATERAL_DECAY = 0x0100,
    A01_FORWARD_DECAY = 0x0040,
    A01_INPUT_ACCEL_EXTRA = 0x0050,
    A01_TURN_CAP = 0x0400,
};

struct a01_horizontal_state {
    uint16_t actual_heading;       /* player +0x20 */
    uint16_t target_heading;       /* player +0x28 */
    int32_t velocity_x;            /* player +0x2c */
    int32_t velocity_z;            /* player +0x34 */
    int32_t forward_component;     /* player +0x38 */
    int32_t lateral_component;     /* player +0x3c */
};

static int32_t a01_toward_zero(int32_t value, int32_t step)
{
    if (value < 0)
        return value + step > 0 ? 0 : value + step;
    if (value > 0)
        return value - step < 0 ? 0 : value - step;
    return 0;
}

static int32_t a01_clamp(int32_t value, int32_t limit)
{
    if (value > limit)
        return limit;
    if (value < -limit)
        return -limit;
    return value;
}

/* 0x80049240..0x800492a8: shortest modular turn, capped before
 * the state-selected arithmetic shift. The ordinary grounded shift is 2.
 */
static uint16_t a01_converge_heading(uint16_t actual, uint16_t target,
                                     unsigned shift)
{
    int32_t delta = ((int32_t)target - actual) & A01_ANGLE_MASK;
    int32_t magnitude;

    if (delta > 0x800)
        delta -= 0x1000;
    magnitude = delta < 0 ? -delta : delta;
    if (magnitude > A01_TURN_CAP)
        magnitude = A01_TURN_CAP;
    magnitude >>= shift;
    actual = (uint16_t)(actual + (delta < 0 ? -magnitude : magnitude));
    return actual & A01_ANGLE_MASK;
}

/* One 30 Hz gameplay tick after FUNC_80047EBC has supplied the camera-relative
 * target heading and a Q14 magnitude. Physical analog full-up reaches this same
 * path as working-button Up (0x0010) on the verified AnalogController setup.
 * Trig rotation at 0x800494b4..0x80049540 is intentionally kept as a boundary.
 */
void a01_ground_move_tick(struct a01_horizontal_state *s, uint16_t buttons,
                          uint16_t resolved_target, uint16_t q14_magnitude,
                          int direction_sign)
{
    int32_t input_cap = (buttons & A01_SLOW_MASK) ? A01_SLOW_CAP : A01_RUN_CAP;

    input_cap = (input_cap * q14_magnitude) >> 14; /* 0x80049150..0x80049158 */
    s->target_heading = resolved_target & A01_ANGLE_MASK;

    if (s->velocity_x == 0 && s->velocity_z == 0 &&
        (buttons & A01_DIRECTION_MASK))
        s->actual_heading = s->target_heading;
    else
        s->actual_heading = a01_converge_heading(s->actual_heading,
                                                 s->target_heading, 2);

    s->lateral_component = a01_toward_zero(s->lateral_component,
                                            A01_LATERAL_DECAY);
    s->forward_component = a01_toward_zero(s->forward_component,
                                            A01_FORWARD_DECAY);
    if (direction_sign > 0 && s->forward_component < input_cap)
        s->forward_component += A01_FORWARD_DECAY + A01_INPUT_ACCEL_EXTRA;
    else if (direction_sign < 0 && s->forward_component > -input_cap)
        s->forward_component -= A01_FORWARD_DECAY + A01_INPUT_ACCEL_EXTRA;

    s->lateral_component = a01_clamp(s->lateral_component, input_cap);
    s->forward_component = a01_clamp(s->forward_component,
                                     A01_FORWARD_HARD_CAP);
}

/* Grounded/default animation branch only. Other action, air, damage, and actor
 * state gates remain in FUNC_80048138/FUNC_800563D4.
 */
uint16_t a01_ground_animation(uint16_t buttons)
{
    if (buttons & A01_SLOW_MASK)
        return 29;
    if (buttons & A01_DIRECTION_MASK)
        return 0;
    return 22;
}
