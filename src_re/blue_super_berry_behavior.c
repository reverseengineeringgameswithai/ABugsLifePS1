/*
 * Documentation-grade reconstruction for Phase 4 row C07.
 * This is reviewed semantic source, not matching source and not build-linked.
 * Exact provenance: analysis/phase4_c07_blue_berry.json.
 */

#include <stdint.h>

enum {
    BLUE_EQUIP_INDEX = 1,
    BLUE_CONSTRUCTOR_TYPE = 5,
    BLUE_RECORD_CLASS = 2,
    BLUE_INITIAL_TIMER = 100,
    BLUE_CONNECTION_CLASS = 2,
    BLUE_DAMAGE_BYTE = 0,
    ENEMY_BERRY_TOUGH = 0x40
};

enum blue_hit_result {
    BLUE_COUNTER_STILL_POSITIVE,
    BLUE_TEMPORARY_DEFEAT
};

struct blue_contact_fields {
    int16_t record_class_20;     /* 2 */
    int16_t timer_22;            /* 100 */
    int16_t model_or_marker_24;  /* 110 */
    int16_t marker_copy_26;
    int16_t feedback_a_28;       /* 50 */
    int16_t feedback_b_2a;       /* 50 */
    int16_t connection_class_2c; /* 2: not red's reaction-only class 1 */
    uint8_t orientation_2e;
    uint8_t secondary_kind_2f;   /* 1: not permanent marker 6 */
    uint8_t scale_30;
    uint8_t scale_31;
    uint8_t reserved_32;
    uint8_t flags_33;            /* 0xe5 */
    uint8_t damage_byte_34;      /* 0: exact -2 switch arm */
    uint8_t presentation_35;     /* 0x20; semantic owner not assigned */
    uint8_t presentation_36;     /* 0x80; semantic owner not assigned */
};

/* Selector 1 maps to constructor table index 5 at 0x800471a8..0x800471b0. */
static void construct_blue_fields(struct blue_contact_fields *contact)
{
    contact->record_class_20 = BLUE_RECORD_CLASS;
    contact->timer_22 = BLUE_INITIAL_TIMER;
    contact->model_or_marker_24 = 110;
    contact->marker_copy_26 = 110;
    contact->feedback_a_28 = 50;
    contact->feedback_b_2a = 50;
    contact->connection_class_2c = BLUE_CONNECTION_CLASS;
    contact->orientation_2e = 0;
    contact->secondary_kind_2f = 1;
    contact->scale_30 = 1;
    contact->scale_31 = 0;
    contact->flags_33 = 0xe5;
    contact->damage_byte_34 = BLUE_DAMAGE_BYTE;
    contact->presentation_35 = 0x20;
    contact->presentation_36 = 0x80;
}

/*
 * Unlike red, blue does not take the enemy+0x5c bit-0x40 reaction-only exit:
 * connection class 2 != 1 and damage byte 0 != 1. Both ordinary and tough
 * actors therefore enter the shared damage switch and lose exactly two units.
 */
static enum blue_hit_result apply_blue_to_enemy(uint16_t enemy_state,
                                                 int16_t *enemy_counter)
{
    (void)enemy_state;
    if (*enemy_counter < 100)
        *enemy_counter = (int16_t)(*enemy_counter - 2);
    if (*enemy_counter > 0)
        return BLUE_COUNTER_STILL_POSITIVE;

    /* Class 2 is not gold class 11 and secondary kind 1 is not permanent kind
     * 6. The common tail therefore installs a temporary defeat only. */
    return BLUE_TEMPORARY_DEFEAT;
}

void blue_super_berry_behavior_refs(void)
{
    (void)construct_blue_fields;
    (void)apply_blue_to_enemy;
    (void)BLUE_EQUIP_INDEX;
    (void)BLUE_CONSTRUCTOR_TYPE;
    (void)ENEMY_BERRY_TOUGH;
}
