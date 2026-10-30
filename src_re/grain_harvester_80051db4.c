/*
 * grain_harvester_80051db4.c
 *
 * Documentation-grade reconstruction of the original grain-harvester system.
 * This file is not a build unit; the retail bytes remain authoritative.
 *
 * Evidence:
 *   analysis/phase4_c13_harvester.json
 *   analysis/phase4_c13_harvester_live.json
 *   movies/Phase4/c13_GRAIN_HARVESTER.annotations.yaml
 *
 * Confirmed resident paths:
 *   0x80051DB4..0x80052090  equip and equipped-state update
 *   FUNC_80053814           type-0x3f grain source -> contact construction
 *   FUNC_8004ABF4           actor/player contact resolution and HP=998 handoff
 *
 * Bounded residuals:
 *   - the exact Cross-disengage clearing store is not yet attributed;
 *   - the exact per-frame ctor-0x51 steering writer is not yet attributed;
 *   - enemy-family breadth and all-level availability are not established.
 */

#include "re_types.h"

#define G_PAD_HELD          (*(volatile uint16_t *)0x80082488)
#define G_PAD_PREVIOUS      (*(volatile uint16_t *)0x80082380)
#define G_HARVESTER_STATE_L (*(volatile int16_t *)G_HARVESTER_STATE)
#define G_POWERUP_FLAGS_L   (*(volatile uint16_t *)G_POWERUP_FLAGS)
#define G_PLAYER_GROUNDED   (*(volatile int16_t *)0x800a6582)
#define G_PLAYER_BUSY       (*(volatile int16_t *)0x800a657c)
#define G_PLAYER_MODE_6588  (*(volatile int16_t *)0x800a6588)
#define G_HARVESTER_ACTOR   ((volatile HarvesterActor *)0x800a1dfc)

#define PAD_SQUARE          0x8000u
#define HARVESTER_ACTOR_ID  0x23u
#define HARVESTER_GRAIN_KIND 0x14u
#define HARVESTER_CONTACT_CTOR 0x51u
#define HARVESTER_METRIC_MAX 0x15f8f
#define HARVESTER_ENEMY_HP_SENTINEL 998

typedef struct {
    uint32_t id;            /* +0x00: must be 0x23 for the LEVEL01 equip path */
    int32_t x;              /* +0x04 */
    int32_t y;              /* +0x08 */
    int32_t z;              /* +0x0c */
} HarvesterActor;

typedef struct {
    int32_t x;              /* +0x00, file units */
    int32_t y;              /* +0x04; set to 0x80000000 when consumed */
    int32_t z;              /* +0x08 */
    uint8_t kind;           /* +0x0c: 0x14 = grain source */
    uint8_t _unknown_0d[3];
} Type3fSource;

/*
 * Static reconstruction of the confirmed entry gates at 0x80051DCC..0x80051E70.
 * The native helper at 0x80052508 supplies the grounded proximity test.
 */
static int harvester_entry_gates_pass(int native_proximity_passes)
{
    const int square_fresh =
        (G_PAD_HELD & PAD_SQUARE) != 0 &&
        (G_PAD_PREVIOUS & PAD_SQUARE) == 0;

    return square_fresh &&
           G_HARVESTER_ACTOR->id == HARVESTER_ACTOR_ID &&
           G_PLAYER_GROUNDED != 0 &&
           (G_POWERUP_FLAGS_L & POWERUP_HARVESTER) == 0 &&
           native_proximity_passes &&
           G_PLAYER_MODE_6588 != 13 &&
           G_PLAYER_BUSY == 0;
}

/*
 * Confirmed stores:
 *   0x80051EA0: state := 1
 *   0x80051EB0: flags |= 0x80
 *   0x80051F60: active path maintains state := 1
 *
 * The surrounding native routine also starts sound/animation and mirrors player
 * position into the harvester actor. Those render/animation fields remain partial.
 */
static void harvester_commit_equipped_state(void)
{
    G_HARVESTER_STATE_L = 1;
    G_POWERUP_FLAGS_L |= POWERUP_HARVESTER;
}

/*
 * FUNC_80053814 grain subpath, confirmed by nine independent source events.
 * Player coordinates are converted to file units; Y uses a -0xe6 bias. The
 * inclusive squared metric gate is 0x15f8f. Passing kind-0x14 sources construct
 * ctor-0x51 contact records and set source.y to INT32_MIN.
 *
 * Contact allocation/initialization is omitted here because the exact native
 * allocator remains represented by the byte-matched resident assembly.
 */
static int harvester_source_is_eligible(
    const Type3fSource *source,
    int32_t player_x_file,
    int32_t player_y_file,
    int32_t player_z_file)
{
    int32_t dx;
    int32_t dy;
    int32_t dz;
    int32_t metric;

    if ((G_POWERUP_FLAGS_L & POWERUP_HARVESTER) == 0 ||
        source->kind != HARVESTER_GRAIN_KIND) {
        return 0;
    }

    dx = (player_x_file - source->x) >> 3;
    dy = ((player_y_file - 0xe6) - source->y) >> 3;
    dz = (player_z_file - source->z) >> 3;
    metric = dx * dx + dy * dy + dz * dz;
    return metric <= HARVESTER_METRIC_MAX;
}

/*
 * FUNC_8004ABF4 actor-contact subpath:
 *   0x8004B158/160 reads and tests POWERUP_HARVESTER.
 *   0x8004B204/208 writes s16 HP 998 to the contacted actor.
 *
 * Existing enemy retirement logic treats 998 as the delayed permanent-destroy
 * handoff. In the retained LEVEL01 control, the id-13 bee changes 4 -> 998 and is
 * removed 86 frames later. Immediate Cross disengagement keeps the same bee at 4.
 */
static int16_t harvester_enemy_contact_hp(int16_t current_hp)
{
    if ((G_POWERUP_FLAGS_L & POWERUP_HARVESTER) != 0) {
        return HARVESTER_ENEMY_HP_SENTINEL;
    }
    return current_hp;
}

/*
 * PHASE 4 C13 STRICT-CLOSURE ADDENDUM (2026-08-02)
 *
 * This supersedes the older residual that called the Cross clearer and grain
 * steering unresolved. Pristine ASM establishes:
 *
 *   0x8004A94C: positive-slot Cross path applies flags &= 0xFF7E.
 *   0x80048654: ordinary player-slot tick changes state 1 -> 0 because
 *               0x80051F60 no longer maintains the slot.
 *   0x80053C58: a new grain starts with target = -1.
 *   0x8005A358: flagsEA bit 8 selects player-homing steering.
 *   0x8005A39C: player bearing helper call.
 *   0x8005A4C8/0x8005A548/0x8005A56C: Y/X/Z steering writes.
 *   0x800589B8: active-grain collection walker.
 *   0x80054F80/0x80054F9C: collection SFX manager call / grain count.
 *   0x8005B268/0x8005B340: scene-reset clearing sites.
 *
 * C RAW analysis identifies one identical non-position harvester placement
 * (type_word 0x00002223, record 63) in scene resources 1, 3, 5, 7, 10,
 * and 12, corresponding to operator levels 1, 2, 8, 10, 5, and 11.
 * The ordering is normalized in the scorecard.
 *
 * Status remains PARTIAL. C13-specific high-yield semantics are exhausted,
 * but the shared player-block pointer frontier and behavioral breadth are not
 * Phase-4-closed. See analysis/phase4_c13_dod_scorecard.json.
 */

typedef struct GrainHarvesterStrictClosure {
  uint32_t cross_clear_pc;
  uint16_t cross_keep_mask;
  uint32_t ordinary_release_tick_pc;
  uint32_t grain_target_init_pc;
  int32_t grain_target_initial_value;
  uint32_t steering_flag_test_pc;
  uint16_t steering_flag_mask;
  uint32_t bearing_call_pc;
  uint32_t scene_reset_pc[2];
} GrainHarvesterStrictClosure;

static const GrainHarvesterStrictClosure k_grain_harvester_strict_closure = {
  0x8004A94Cu, 0xFF7Eu, 0x80048654u,
  0x80053C58u, -1, 0x8005A358u, 0x0100u, 0x8005A39Cu,
  { 0x8005B268u, 0x8005B340u }
};
