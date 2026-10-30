/*
 * Documentation-grade reconstruction of the dandelion glide state path.
 *
 * This is not a build unit and is not claimed byte-matched. It records the
 * statically proven control flow joining 0x8005C818, 0x80048138, 0x8005C258,
 * and the gameplay scheduler. Negative Y velocity rises; positive Y falls.
 */

#include <stdint.h>

#define PLAYER_VY       (*(volatile int32_t *)0x800A6530)
#define PLAYER_Y        (*(volatile int32_t *)0x800A6504)
#define PLAYER_X        (*(volatile int32_t *)0x800A6500)
#define PLAYER_Z        (*(volatile int32_t *)0x800A6508)
#define PLAYER_LOCKOUT  (*(volatile int16_t *)0x800A657C)
#define PLAYER_STATE    (*(volatile int16_t *)0x800A6580)
#define PLAYER_GROUNDED (*(volatile int16_t *)0x800A6582)
#define PLAYER_ANIM     (*(volatile int16_t *)0x800A6588)
#define PLANT_LATCH     (*(volatile int16_t *)0x800A659E)

enum {
    PLAYER_STATE_DANDELION_ENTRY = 5,
    PLAYER_STATE_NORMAL_FALL = 6,
    PLANT_LATCH_DANDELION = 11,
    PLANT_LATCH_CONTACT = 12,
    NORMAL_FALL_CAP = 4096,
    DANDELION_FALL_CAP = 350
};

/* 0x8005C840..0x8005C860, after 0x80046CAC clears carrier binding. */
static void dandelion_launch(void)
{
    PLAYER_VY = -4096;
    PLAYER_STATE = PLAYER_STATE_DANDELION_ENTRY;
    PLAYER_GROUNDED = 0;
}

/*
 * 0x8005C8B8..0x8005C8BC. The real write also requires the elevated,
 * quantized XYZ radius-40 test and a clear player flag 0x80.
 */
static void dandelion_enable_glide(void)
{
    PLANT_LATCH = PLANT_LATCH_DANDELION;
}

/*
 * 0x800486DC..0x80048728. Return 1 for the latch-11 jump to 0x80048D90.
 * This skips ordinary state-5-to-6 and gravity processing, but rejoins before
 * horizontal input. Starting at -4096, rise is 30,720 coordinate units. The
 * comparison-before-addition tail is 256, 512, 350, 350...
 */
static int dandelion_vertical_override(void)
{
    if (PLANT_LATCH != PLANT_LATCH_DANDELION)
        return 0;

    if (PLAYER_GROUNDED != 0) {
        PLANT_LATCH = 0; /* 0x80048700: automatic grounded release. */
        return 0;
    }

    if (PLAYER_VY < DANDELION_FALL_CAP)
        PLAYER_VY += 256;
    else
        PLAYER_VY = DANDELION_FALL_CAP;
    return 1;
}

/* 0x8004872C..0x80048750: separate latch-12 positive-VY cap. */
static void contact_latch_vertical_cap(void)
{
    if (PLANT_LATCH == PLANT_LATCH_CONTACT && PLAYER_VY >= 513)
        PLAYER_VY = 512;
}

/* 0x80048D54..0x80048D8C when latch 11 did not take the override. */
static void ordinary_vertical_tail(void)
{
    if (PLAYER_STATE == PLAYER_STATE_DANDELION_ENTRY)
        PLAYER_STATE = PLAYER_STATE_NORMAL_FALL;

    if (PLAYER_GROUNDED == 0) {
        PLAYER_VY += 256;
        if (PLAYER_VY > NORMAL_FALL_CAP)
            PLAYER_VY = NORMAL_FALL_CAP;
    }
}

extern void player_timer_updates_from_80048d90(void);
extern void player_horizontal_input_and_velocity_to_80049540(void);
extern void player_collision_integrator_8003633c(void);
extern void effect_mesh_transform_80022fe0(
    int32_t x, int32_t y, int32_t z, int32_t arg3,
    int32_t arg4, int32_t arg5, int32_t arg6, int32_t arg7);

/*
 * 0x80051B84, called from the gameplay state machine. The exact semantic names
 * of the final five effect arguments remain unknown, so they stay positional.
 * This is the direct owner of the latch-gated overhead mesh submission.
 */
static void dandelion_effect_submit(void)
{
    if (PLANT_LATCH == PLANT_LATCH_DANDELION && PLAYER_LOCKOUT == 0)
        effect_mesh_transform_80022fe0(
            PLAYER_X, PLAYER_Y - 22528, PLAYER_Z, 200, 320, 13, 32, 0);
}

/* 0x800568BC..0x800568D4 in actor_skinned_update. */
static void dandelion_animation_select(void)
{
    if (PLANT_LATCH == PLANT_LATCH_DANDELION)
        PLAYER_ANIM = 18;
}

/*
 * Direct retained-ASM retirement sites beyond grounded release:
 *   level transition 0x8004A87C, harvester activation 0x80051EA4,
 *   respawn 0x8005B314. Every direct latch writer stores literal 0, 11, or 12;
 *   there is no direct timer/decrement law. Indirect aliases remain unproved.
 */

/*
 * Both vertical paths converge at 0x80048D90. Steering then stores VX at
 * 0x80049524 and VZ at 0x80049540 before the collision integrator.
 */
static void player_update_glide_slice(void)
{
    if (!dandelion_vertical_override()) {
        contact_latch_vertical_cap();
        ordinary_vertical_tail();
    }

    player_timer_updates_from_80048d90();
    player_horizontal_input_and_velocity_to_80049540();
    player_collision_integrator_8003633c();
}

extern void other_gameplay_updates_between_player_and_plants(void);
extern void plant_behavior_walker_8005bfbc(void);

/*
 * Scheduler order is player update at 0x8004EFD8, then plant walker at
 * 0x8004F010. A new latch is first consumed next tick. Grounding is produced
 * in the later player integrator, so a newly detected landing clears latch 11
 * on the following tick.
 */
static void gameplay_tick_order(void)
{
    player_update_glide_slice();
    other_gameplay_updates_between_player_and_plants();
    plant_behavior_walker_8005bfbc();
}

void dandelion_glide_static_reference(void)
{
    if (0) {
        dandelion_launch();
        dandelion_enable_glide();
        gameplay_tick_order();
        dandelion_effect_submit();
        dandelion_animation_select();
    }
}
