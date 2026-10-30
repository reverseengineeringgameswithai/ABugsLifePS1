/* Phase 4 A19: SELECT status-display path reconstructed from pristine SCUS-94288. */
#include <stdint.h>

#define PAD_SELECT              0x0001u
#define HUD_PULSE_LIVES         (*(volatile int16_t *)0x800b0188u)
#define HUD_LATCH_LIVES         (*(volatile int16_t *)0x800b018au)
#define HUD_PULSE_GRAIN         (*(volatile int16_t *)0x800b018cu)
#define HUD_DIGITS_GRAIN        (*(volatile uint16_t *)0x800b018eu)
#define HUD_PULSE_HEALTH        (*(volatile int16_t *)0x800b0190u)
#define HUD_LATCH_HEALTH        (*(volatile int16_t *)0x800b0192u)
#define HUD_PULSE_FLIK          (*(volatile int16_t *)0x800b0194u)
#define PLAYER_LIVES            (*(volatile uint8_t *)0x800a65a0u)
#define GRAIN_COUNT             (*(volatile uint8_t *)0x800a65a1u)
#define FLIK_PROGRESS_BITS      (*(volatile uint8_t *)0x800a65a2u)
#define PLAYER_TRUE_HEALTH      (*(volatile int16_t *)0x800a6594u)

/* 0x800503FC. This is a generic pickup/HUD pulse normalizer. While SELECT is
 * held, player_vertical_update calls it for the four status pulses. */
static void normalize_status_pulse(volatile int16_t *pulse)
{
    int16_t value = *pulse;
    if (value >= 0x0c00)
        value = (int16_t)(0x1000 - value);
    else if (value >= 0x0401)
        value = 0x0400;
    *pulse = value;
    if (*pulse == 0)
        *pulse = 0x0040;
}

/* Interior of player_vertical_update at 0x800484B0..0x800484F0. */
void status_display_select_update(uint16_t controller_bits)
{
    if ((controller_bits & PAD_SELECT) == 0)
        return;
    normalize_status_pulse(&HUD_PULSE_LIVES);
    normalize_status_pulse(&HUD_PULSE_GRAIN);
    normalize_status_pulse(&HUD_PULSE_HEALTH);
    normalize_status_pulse(&HUD_PULSE_FLIK);
}

static uint16_t pack_decimal(uint8_t value)
{
    uint8_t tens = value / 10;
    uint8_t ones = value - tens * 10;
    return (uint16_t)(tens | ((uint16_t)ones << 8));
}

/* Contract extracted from the relevant branches of 0x800526F4. Rendering calls
 * are omitted. Gameplay passes step=0x40 at 0x8004F3E8. */
void status_display_latch_update(int16_t step)
{
    if (HUD_PULSE_LIVES == 0x0400)
        HUD_LATCH_LIVES = PLAYER_LIVES;
    if (HUD_PULSE_GRAIN == 0x0400)
        HUD_DIGITS_GRAIN = pack_decimal(GRAIN_COUNT);
    if (PLAYER_TRUE_HEALTH >= 5)
        PLAYER_TRUE_HEALTH = 4;
    if (HUD_PULSE_HEALTH == 0x0400)
        HUD_LATCH_HEALTH = PLAYER_TRUE_HEALTH;

    /* The renderer also reads FLIK_PROGRESS_BITS while HUD_PULSE_FLIK is active.
     * Scene-specific branches reuse that pulse for their own progress icons. */
    (void)FLIK_PROGRESS_BITS;
    (void)step;
}
