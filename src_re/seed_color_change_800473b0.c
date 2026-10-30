/*
 * Documentation-grade semantic reconstruction of the pristine SCUS-94288
 * seed-color action at 0x800473B0..0x80047480.
 *
 * This file describes the recovered behavior. It is not a compiler-matching
 * replacement for the retail routine.
 */

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum {
    PAD_TRIANGLE = 0x1000,
    SEED_COLOR_COUNT = 5,
    SEED_COLOR_TIMER_START = 16,
    SEED_COLOR_SOUND_BASE = 30,
    SEED_COLOR_EFFECT_BASE = 124,
};

typedef struct SeedSourceRecord {
    uint8_t unknown_00_0d[0x0e];
    uint8_t current_color;        /* +0x0e */
    uint8_t default_color;        /* +0x0f; nonzero also forces Triangle */
    uint8_t unknown_10_17[8];
    uint8_t transition_timer;     /* +0x18 */
} SeedSourceRecord;

typedef struct SeedColorAction {
    bool accepted;
    bool changed;
    uint8_t old_color;
    uint8_t new_color;
    uint8_t sound_id;
    uint8_t effect_object_id;
} SeedColorAction;

typedef struct SeedColorPresentation {
    uint8_t red;
    uint8_t green;
    uint8_t blue;
} SeedColorPresentation;

static const SeedColorPresentation k_seed_color_rgb[SEED_COLOR_COUNT] = {
    {128, 64, 0},
    {0, 64, 128},
    {32, 128, 32},
    {128, 32, 112},
    {200, 127, 0},
};

/*
 * 0x800B0196 holds four low-to-high nibbles in first-collection order.
 * A zero nibble is both the brown baseline and the end/wrap sentinel.
 */
uint16_t seed_color_append_unlock(uint16_t order, uint8_t color)
{
    unsigned shift;

    color &= 0x0f;
    if (color == 0)
        return order;

    for (shift = 0; shift < 16; shift += 4) {
        if (((order >> shift) & 0x0f) == 0)
            return (uint16_t)(order | ((uint16_t)color << shift));
    }
    return order;
}

/*
 * Mirrors the search/wrap law at 0x80047414..0x80047460.
 * An authored nonzero default bypasses the unlock order.
 */
uint8_t seed_color_next(uint16_t order, uint8_t current, uint8_t default_color)
{
    uint16_t cursor = order;
    const uint8_t first = (uint8_t)(order & 0x0f);
    unsigned slot;

    if (default_color != 0)
        return (uint8_t)(default_color & 0x0f);

    current &= 0x0f;
    if (current == 0)
        return first;

    for (slot = 0; slot < 4; ++slot) {
        if (current == (cursor & 0x0f))
            return (uint8_t)((cursor >> 4) & 0x0f);
        cursor >>= 4;
    }

    return first;
}

/*
 * selected_offset is the signed value at 0x800A655C. The retail code obtains
 * source from selected_actor+0x80 after these gates.
 */
SeedColorAction seed_color_triangle(
    int16_t selected_offset,
    uint16_t current_pad,
    uint16_t previous_pad,
    uint16_t unlock_order,
    SeedSourceRecord *source)
{
    SeedColorAction out = {0};

    if (selected_offset <= 0 || source == NULL)
        return out;
    if ((current_pad & PAD_TRIANGLE) == 0)
        return out;
    if ((previous_pad & PAD_TRIANGLE) != 0)
        return out;

    out.accepted = true;
    out.old_color = source->current_color;
    source->transition_timer = SEED_COLOR_TIMER_START;
    source->current_color = seed_color_next(
        unlock_order, source->current_color, source->default_color);
    out.new_color = source->current_color;
    out.changed = out.old_color != out.new_color;
    out.sound_id = (uint8_t)(SEED_COLOR_SOUND_BASE + out.new_color);
    out.effect_object_id =
        (uint8_t)(SEED_COLOR_EFFECT_BASE + out.new_color);
    return out;
}

const SeedColorPresentation *seed_color_presentation(uint8_t color)
{
    if (color >= SEED_COLOR_COUNT)
        return NULL;
    return &k_seed_color_rgb[color];
}

/*
 * Actor reinitialization at 0x80049DE4..0x80049DF4:
 *
 *     source->transition_timer = 0;
 *     source->current_color = source->default_color & 0x0f;
 */
void seed_color_reinitialize(SeedSourceRecord *source)
{
    if (source == NULL)
        return;
    source->transition_timer = 0;
    source->current_color = (uint8_t)(source->default_color & 0x0f);
}
