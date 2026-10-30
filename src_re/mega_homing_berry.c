/*
 * Phase 4 C09 reconstruction of the native purple/mega homing berry.
 * Explanatory C only; values are tied to pristine SCUS_942.88.
 */

#include "re_types.h"

enum {
    MEGA_PRIMARY_TYPE = 45,
    MEGA_PRIMARY_TIMER = 8,
    MEGA_PRIMARY_SUBTYPE = 9,
    MEGA_CHILD_TYPE = 48,
    MEGA_CHILD_TIMER = 100,
    MEGA_CHILD_SUBTYPE = 8,
    MEGA_DAMAGE_SELECTOR = 128,
    MEGA_DAMAGE_DELTA = -3
};

struct mega_contact_metadata {
    int16_t record_class_20;       /* 2 */
    int16_t timer_22;              /* primary 8, child 100 */
    int16_t model_24;              /* 124 */
    int16_t scale_26;              /* 256 */
    int16_t radius_28;             /* 50 */
    int16_t field_2a;              /* 50 */
    int16_t connection_class_2c;   /* primary 9, child 8 */
    int8_t orientation_2e;         /* 0 */
    uint8_t secondary_kind_2f;     /* 13 */
    uint8_t flags_33;              /* primary 0xe5, child 0xed */
    uint8_t damage_selector_34;    /* 128 -> exact -3 */
    uint8_t presentation_35;       /* 0x20 */
    uint8_t presentation_36;       /* 0x80 */
};

/*
 * Equip index 4 constructs type 45. Terminal subtype 9 calls
 * FUNC_8005743C(primary, 0), which uses the same target scan as green but
 * creates type 48. With no target, it stores timer 80/subtype 8.
 */
static int16_t mega_damage(int16_t enemy_counter)
{
    if (enemy_counter < 100)
        enemy_counter = (int16_t)(enemy_counter + MEGA_DAMAGE_DELTA);
    return enemy_counter;
}

/*
 * Mega is not a faster homing tier. The type-48 spawn block is instruction-
 * identical to type 16 except for the constructor literal, both child rows
 * carry homing flag 0x08, and both enter the same fixed sine/8, quarter-error
 * updater. The mechanical upgrade is -3 damage versus green's -2.
 */
void mega_homing_berry_phase4_refs(void)
{
    volatile unsigned constants = MEGA_PRIMARY_TYPE ^ MEGA_PRIMARY_TIMER ^
        MEGA_PRIMARY_SUBTYPE ^ MEGA_CHILD_TYPE ^ MEGA_CHILD_TIMER ^
        MEGA_CHILD_SUBTYPE ^ MEGA_DAMAGE_SELECTOR;
    (void)constants;
    (void)mega_damage;
}
