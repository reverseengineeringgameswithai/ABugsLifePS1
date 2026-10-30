/*
 * Phase 4 A13 documentation-grade reconstruction of plant-output cycling.
 * Retail ASM remains authoritative; this is not a build unit.
 */
#include <stdint.h>

enum PlantOutputLane {
    PLANT_OUTPUT_BROWN = 0,
    PLANT_OUTPUT_BLUE = 1,
    PLANT_OUTPUT_GREEN = 2,
    PLANT_OUTPUT_PURPLE = 3,
    PLANT_OUTPUT_YELLOW = 4,
    PLANT_OUTPUT_LANE_COUNT = 5
};

enum {
    PLANT_OUTPUT_SELECTOR_BASE = 0x800a6598u,
    PLANT_OUTPUT_TABLE = 0x8007a448u,
    PLANT_OUTPUT_CYCLE_TIMER = 0x800824a4u,
    PLANT_OUTPUT_CYCLE_TICKS = 120,
    PLANT_OUTPUT_EVENT = -16,
    PLANT_OUTPUT_X_MASK = 0x4000,
    PLANT_OUTPUT_TRAINING_SCENE = 0x11
};

typedef struct PlantOutputSelectors {
    uint8_t lane[PLANT_OUTPUT_LANE_COUNT];
} PlantOutputSelectors;

_Static_assert(sizeof(PlantOutputSelectors) == 5, "five packed selector bytes");

static unsigned selected_output(uint8_t selector)
{
    return selector >> 4;
}

static unsigned maximum_available_output(uint8_t selector)
{
    return selector & 0x0f;
}

/* The X handler uses only three low bits, unlike timeout normalization. */
static unsigned cycle_available_output(uint8_t selector)
{
    return selector & 7u;
}

static int plant_output_table_index(unsigned color, uint8_t selector)
{
    return (int)(color * 4u + selected_output(selector)) - 1;
}

/* 0x80047B34..0x80047B6C, after the carried-seed and X-edge gates. */
static int cycle_plant_output(uint8_t *selector)
{
    unsigned next = *selector;
    const unsigned available = cycle_available_output(*selector);

    if (available < 2u) {
        return 0; /* no write, descriptor update, event, or timer arm */
    }
    next += 0x10u;
    if ((next & 7u) < (next >> 4)) {
        next = (next & 7u) + 0x10u;
    }
    *selector = (uint8_t)next;
    return 1;
}

/* 0x8004757C..0x800476A8 after the 120-tick timer expires. */
static int normalize_selection_to_maximum(uint8_t *selector)
{
    const unsigned available = maximum_available_output(*selector);
    const uint8_t normalized = (uint8_t)((available << 4) + available);

    if (normalized == *selector) {
        return 0;
    }
    *selector = normalized;
    return 1;
}

/* Active type-0x3f token handlers at 0x800542F4..0x800544F8. */
static uint8_t upgrade_available_output(uint8_t selector)
{
    const unsigned next = (selector + 1u) & 7u;
    return (uint8_t)((next << 4) + next);
}

/* Natural authored states are 0x11..0x44. The consumer itself has no guard. */
static int selector_is_naturally_safe(uint8_t selector)
{
    const unsigned selected = selected_output(selector);
    const unsigned available = maximum_available_output(selector);
    return available >= 1u && available <= 4u &&
           selected >= 1u && selected <= available;
}

void plant_output_selection_reference(void)
{
    PlantOutputSelectors selectors = {{0x14, 0, 0, 0, 0}};
    volatile int index;

    (void)cycle_plant_output(&selectors.lane[PLANT_OUTPUT_BROWN]);
    (void)normalize_selection_to_maximum(&selectors.lane[PLANT_OUTPUT_BROWN]);
    selectors.lane[PLANT_OUTPUT_BLUE] =
        upgrade_available_output(selectors.lane[PLANT_OUTPUT_BLUE]);
    index = plant_output_table_index(PLANT_OUTPUT_BROWN,
                                     selectors.lane[PLANT_OUTPUT_BROWN]);
    index += selector_is_naturally_safe(selectors.lane[PLANT_OUTPUT_BROWN]);
    (void)index;
}
