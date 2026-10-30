/*
 * Phase 4 C08 reconstruction of the native green/homing berry path.
 * This is explanatory C tied to pristine SCUS_942.88 instructions, not a
 * replacement implementation.
 */

#include "re_types.h"

enum {
    GREEN_PRIMARY_TYPE = 8,
    GREEN_PRIMARY_SUBTYPE = 5,
    GREEN_CHILD_TYPE = 16,
    GREEN_CHILD_SUBTYPE = 3,
    GREEN_CHILD_TIMER = 100,
    GREEN_NO_TARGET_TIMER = 80,
    TARGETABLE_BIT = 0x0001,
    ACQUIRE_EXCLUDED_BITS = 0x00a0,
    CHILD_INVALID_BITS = 0x0880
};

/*
 * At primary timer cleanup, subtype 5 calls FUNC_8005743C(primary, 1).
 * The actual routine scans u32 pointers beginning at 0x80090748 and stops on
 * the first NULL. There is no range or Y-distance test in this scanner.
 */
static void *green_select_target(const int32_t primary_x,
                                 const int32_t primary_z,
                                 void *const *damageable_table)
{
    void *best = 0;
    int32_t best_distance = INT32_MAX;

    for (; *damageable_table != 0; ++damageable_table) {
        uint8_t *enemy = *damageable_table;
        uint16_t state = *(uint16_t *)(enemy + 0x5c);
        int32_t dx;
        int32_t dz;
        int32_t distance;

        if ((state & TARGETABLE_BIT) == 0 ||
            (state & ACQUIRE_EXCLUDED_BITS) != 0)
            continue;
        dx = (primary_x - *(int32_t *)(enemy + 0x04)) >> 5;
        dz = (primary_z - *(int32_t *)(enemy + 0x0c)) >> 5;
        distance = dx * dx + dz * dz;
        if (best_distance < distance)
            continue;
        /* Equality intentionally replaces the earlier table entry. */
        best = enemy;
        best_distance = distance;
    }
    return best;
}

/*
 * A selected target is stored once at child record +0x10. If no target was
 * selected, the primary is retained with timer 80 and terminal subtype 3.
 */
static int green_child_target_is_invalid(const uint8_t *target)
{
    return *(const int16_t *)(target + 0x6e) == 0 ||
           (*(const uint16_t *)(target + 0x5c) & CHILD_INVALID_BITS) != 0;
}

/*
 * The type-16 updater does not call FUNC_8005743C. Invalidity stages timer=1;
 * the common update/cleanup path then changes 1 -> 0 -> -1 -> 0 and dispatches
 * subtype 3, which decrements the owned-throw counter at 0x800A6596.
 */
void green_homing_berry_phase4_refs(void)
{
    volatile unsigned constants = GREEN_PRIMARY_TYPE ^ GREEN_PRIMARY_SUBTYPE ^
        GREEN_CHILD_TYPE ^ GREEN_CHILD_SUBTYPE ^ GREEN_CHILD_TIMER ^
        GREEN_NO_TARGET_TIMER;
    (void)constants;
    (void)green_select_target;
    (void)green_child_target_is_invalid;
}
