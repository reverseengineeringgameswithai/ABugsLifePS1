/*
 * Documentation-grade reconstruction for Phase 4 row C06.
 * This is reviewed semantic source, not matching source and not build-linked.
 * Exact provenance: analysis/phase4_c06_red_berry.json.
 */

#include <stdint.h>

enum {
    RED_EQUIP_INDEX = 0,
    RED_THROW_TYPE = 2,
    RED_INITIAL_TIMER = 100,
    RED_CONNECTION_CLASS = 1,
    RED_DAMAGE_BYTE = 0x70,
    ENEMY_BERRY_TOUGH = 0x40,
    HIT_TEMPORARY = 1,
    HIT_PERMANENT = 2
};

enum red_hit_result {
    RED_REACTION_ONLY,
    RED_COUNTER_STILL_POSITIVE,
    RED_TEMPORARY_DEFEAT
};

/* The collision loop keeps s1 biased eight bytes past the allocation base. */
struct red_contact_fields {
    int16_t type_20;             /* 2 */
    int16_t timer_22;            /* 100 */
    int16_t model_or_marker_24;  /* 110 */
    int16_t marker_copy_26;
    int16_t feedback_a_28;       /* 50 */
    int16_t feedback_b_2a;       /* 50 */
    int16_t connection_class_2c; /* 1: red/tough reaction class */
    uint8_t orientation_2e;
    uint8_t mode_2f;
    uint8_t scale_30;
    uint8_t scale_31;
    uint8_t reserved_32;
    uint8_t flags_33;            /* 0xe5 */
    uint8_t damage_byte_34;      /* 0x70: default -1 arm */
    uint8_t visual_35;           /* 0x12 */
    uint8_t visual_36;
};

/*
 * Constructor 0x8005a0e0 indexes table 0x8007941c with type * 0x14.
 * Equip index 0 is mapped to type 2 at 0x8004719c..0x800471a4.
 */
static void construct_red_fields(struct red_contact_fields *contact)
{
    contact->type_20 = RED_THROW_TYPE;
    contact->timer_22 = RED_INITIAL_TIMER;
    contact->model_or_marker_24 = 110;
    contact->marker_copy_26 = 110;
    contact->feedback_a_28 = 50;
    contact->feedback_b_2a = 50;
    contact->connection_class_2c = RED_CONNECTION_CLASS;
    contact->orientation_2e = 0;
    contact->mode_2f = 1;
    contact->scale_30 = 1;
    contact->scale_31 = 0;
    contact->flags_33 = 0xe5;
    contact->damage_byte_34 = RED_DAMAGE_BYTE;
    contact->visual_35 = 0x12;
    contact->visual_36 = 0;
}

/*
 * Contact handler 0x80058af8, ordinary/tough split at 0x80058ee4.
 * `enemy_counter` is enemy+0x6e. High sentinels (>=100) bypass this lane.
 */
static enum red_hit_result apply_red_to_enemy(uint16_t enemy_state,
                                               int16_t *enemy_counter)
{
    if ((enemy_state & ENEMY_BERRY_TOUGH) != 0)
        return RED_REACTION_ONLY;

    if (*enemy_counter < 100)
        *enemy_counter = (int16_t)(*enemy_counter - 1);
    if (*enemy_counter > 0)
        return RED_COUNTER_STILL_POSITIVE;

    /* Red sets the temporary-hit accumulator bit. It never sets bit 2, so the
     * permanent-quota block at 0x800592cc..0x80059300 is skipped. */
    return RED_TEMPORARY_DEFEAT;
}

void red_berry_behavior_refs(void)
{
    (void)construct_red_fields;
    (void)apply_red_to_enemy;
    (void)RED_EQUIP_INDEX;
    (void)HIT_TEMPORARY;
    (void)HIT_PERMANENT;
}
