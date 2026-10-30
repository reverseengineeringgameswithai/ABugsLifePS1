/* ============================================================================
 * dandelion_glide_static_8005c818.c
 *
 * Documentation-grade semantic C reconstructed by tools/phase4_b03_asm_static.c
 * from the retained hand-written MIPS ASM. This is not a build unit and is not
 * byte-matched. It covers the reachable dandelion path, the carried-state reset
 * callee, the quantized proximity helpers, and the propeller bridge.
 * Brown tier 3 selects plant type 8 through resident table 0x8007A448; resident
 * behavior table entry type-2 == 6 points to this handler at 0x8005C818.
 *
 * Evidence:
 *   analysis/phase4_b03_dandelion_static.json
 *   asm/hand_written/8005bfbc_plant_behavior_walker.s
 *   asm/hand_written/8005c818_seed_plant_dandelion_handler.s
 *   asm/hand_written/8005c258_seed_plant_propeller_handler.s
 * ========================================================================== */

#include "re_types.h"

#define S16(a) (*(volatile int16_t *)(uintptr_t)(a))
#define U16(a) (*(volatile uint16_t *)(uintptr_t)(a))
#define S32(a) (*(volatile int32_t *)(uintptr_t)(a))
#define U8(a)  (*(volatile uint8_t *)(uintptr_t)(a))

#define PLAYER_BASE              0x800A6500u
#define PLAYER_VELOCITY_Y        0x800A6530u
#define CARRIED_ACTOR_OFFSET     0x800A655Cu
#define PLAYER_TIMER_657A        0x800A657Au
#define PLAYER_MODE              0x800A6580u
#define PLAYER_CONTACT           0x800A6582u
#define PLAYER_FIELD_6584        0x800A6584u
#define INDEXED_STATE_658C       0x800A658Cu
#define PLAYER_ACTION            0x800A6588u
#define PLAYER_POWER_FLAGS       0x800A6590u
#define PLANT_INTERACTION_LATCH  0x800A659Eu
#define PLAYER_FIELD_65A3        0x800A65A3u

#define CARRIED_ACTOR_ARENA      0x8009FD80u
#define HARVESTER_FLAG           0x0080u
#define DANDELION_LATCH          11
#define CONTACT_LATCH            12

typedef struct {
    int32_t x;
    int32_t y;
    int32_t z;
} Vec3i;

typedef struct {
    int16_t type;             /* +0x00 */
    int16_t data_w2;          /* +0x02 */
    int32_t anim_hi;          /* +0x04 */
    Vec3i position;           /* +0x08 */
    int32_t zero_14;          /* +0x14 */
    uint32_t anim_seq;        /* +0x18 */
    uint32_t data_cursor;     /* +0x1C */
    uint32_t seed_actor;      /* +0x20 */
    int16_t zero_24;          /* +0x24 */
    int16_t data_w0;          /* +0x26 */
    int16_t zero_28;          /* +0x28 */
    int16_t zero_2a;          /* +0x2A */
    int16_t zero_2c;          /* +0x2C */
    uint16_t extra_state;     /* +0x2E */
} PlantSlot;

_Static_assert(sizeof(PlantSlot) == 0x30, "PlantSlot layout");

extern void play_sound(int sound_id, const Vec3i *position);

/*
 * FUNC_80052508: three-axis quantized sphere test.
 * MIPS uses the low 32-bit products and a signed final slt.
 */
static int within_xyz_q8(const Vec3i *a, const Vec3i *b, int32_t radius)
{
    int32_t dx = (a->x - b->x) >> 8;
    int32_t dy = (a->y - b->y) >> 8;
    int32_t dz = (a->z - b->z) >> 8;
    int32_t distance2 = dx * dx + dy * dy + dz * dz;
    return distance2 < radius * radius;
}

/* FUNC_800524B8: propeller X/Z cylinder test; Y is handled separately. */
static int within_xz_q8(const Vec3i *a, const Vec3i *b, int32_t radius)
{
    int32_t dx = (a->x - b->x) >> 8;
    int32_t dz = (a->z - b->z) >> 8;
    int32_t distance2 = dx * dx + dz * dz;
    return distance2 < radius * radius;
}

/* FUNC_80041A74, called by the shared detach/reset helper. */
static void reset_indexed_state_80041a74(void)
{
    int32_t index = S16(INDEXED_STATE_658C);
    if (index != 0) {
        uintptr_t record = 0x8009C874u + (uintptr_t)(index - 1) * 0x344u;
        S16(record) = -30;
        S16(INDEXED_STATE_658C) = 0;
    }
}

/*
 * FUNC_80046CAC. The dandelion and propeller callers pass position-like
 * arguments, but this callee and its nested helper do not consume them.
 * Its concrete behavior is carried-object detachment and player-state reset.
 */
static void detach_carried_state_80046cac(void)
{
    int32_t offset = S32(CARRIED_ACTOR_OFFSET);
    if (offset > 0) {
        uintptr_t actor = CARRIED_ACTOR_ARENA + (uint32_t)offset;
        S32(actor + 0x1C) = 0;
        S32(actor + 0x20) = 0;
        S32(actor + 0x24) = 0;
        U16(actor + 0x5C) &= (uint16_t)~0x0040u;
    }

    reset_indexed_state_80041a74();
    S16(PLAYER_TIMER_657A) = 0;
    S32(CARRIED_ACTOR_OFFSET) = 0;
    U8(PLAYER_FIELD_65A3) = 0;
}

/*
 * Reachable semantic body of seed_plant_dandelion_handler 0x8005C818.
 *
 * plant_behavior_walker supplies:
 *   selected_slot = player_sector_lookup() - 1
 *   current_slot  = the current 0x30-byte slot index
 *   player        = (Vec3i *)0x800A6500
 *
 * The walker already requires slot->extra_state bit 0x04 before dispatch.
 * Native negative controls are explicit: a different selected slot, missing
 * slot bit 0x02, failed radius-40 sphere, or harvester flag 0x80 prevents the
 * relevant launch/latch action.
 */
void seed_plant_dandelion_static(
    PlantSlot *slot,
    int32_t selected_slot,
    int32_t current_slot)
{
    Vec3i *player = (Vec3i *)(uintptr_t)PLAYER_BASE;

    if (selected_slot == current_slot && (slot->extra_state & 0x0002u) != 0) {
        detach_carried_state_80046cac();
        S32(PLAYER_VELOCITY_Y) = -4096;
        S16(PLAYER_MODE) = 5;
        S16(PLAYER_CONTACT) = 0;
        S16(PLAYER_FIELD_6584) = 0;
        S16(PLAYER_ACTION) = 3;
        play_sound(15, &slot->position);
    }

    /*
     * The original mutates slot Y in place for the call and restores it before
     * jumping to the shared passive plant tail at 0x8005CCE8.
     */
    slot->position.y -= 0x7400;
    if (within_xyz_q8(&slot->position, player, 40) &&
        (U16(PLAYER_POWER_FLAGS) & HARVESTER_FLAG) == 0) {
        S16(PLANT_INTERACTION_LATCH) = DANDELION_LATCH;
    }
    slot->position.y += 0x7400;
}

/*
 * Statically reconstructed dandelion-relevant portion of the propeller handler.
 * This shows exactly how latch 11 extends the inner vertical activation band.
 */
int seed_plant_propeller_bridge_static(PlantSlot *slot)
{
    Vec3i *player = (Vec3i *)(uintptr_t)PLAYER_BASE;
    int32_t dy;
    int32_t velocity;

    if (!within_xz_q8(&slot->position, player, 40))
        return 0;
    if ((U16(PLAYER_POWER_FLAGS) & HARVESTER_FLAG) != 0)
        return 0;

    dy = slot->position.y - player->y;
    if (dy > 0x9FFF || S16(PLAYER_CONTACT) != 0)
        return 0;

    if (dy < 0x3001) {
        if (S16(PLANT_INTERACTION_LATCH) != DANDELION_LATCH)
            return 0;
        if (dy < 0x1001)
            return 0;
    }

    detach_carried_state_80046cac();
    if (S16(PLANT_INTERACTION_LATCH) == CONTACT_LATCH)
        S16(PLANT_INTERACTION_LATCH) = 0;

    velocity = S32(PLAYER_VELOCITY_Y) - 512;
    S16(PLAYER_MODE) = 5;
    S16(PLAYER_FIELD_6584) = 0;
    S32(PLAYER_VELOCITY_Y) = velocity;
    S16(PLAYER_ACTION) = 13;
    if (velocity < -3072)
        S32(PLAYER_VELOCITY_Y) = -3072;
    return 1;
}
