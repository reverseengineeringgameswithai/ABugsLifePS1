/*
 * Documentation-grade reconstruction for Phase 4 row D06.
 * Provenance and confidence are recorded in:
 *   analysis/phase4_d06_grasshoppers.json
 *
 * This is not matching source and is not linked into a game build.
 */

#include <stdint.h>

typedef struct Actor Actor;
typedef struct SpawnTemplate SpawnTemplate;

struct Actor {
    uint8_t unknown_00[0x14];
    int32_t heading_14;
    uint8_t unknown_18[0x08];
    int32_t motion_20;
    uint8_t unknown_24[0x0c];
    int32_t z_30;
    uint8_t unknown_34[0x0c];
    uint8_t state_40;
    uint8_t unknown_41[3];
    const void *animation_44;
    uint8_t unknown_48[4];
    const void *state_data_4c;
    uint32_t flags_50;
    uint8_t unknown_54[0x0c];
    int32_t cooldown_60;
    uint8_t unknown_64[6];
    int16_t scale_or_height_6a;
    uint8_t unknown_6c[4];
    const uint16_t *program_70;
    uint8_t unknown_74[0x0c];
    const SpawnTemplate *spawn_80;
};

struct SpawnTemplate {
    uint8_t unknown_00[0x0f];
    uint8_t subtype_0f;
};

extern int32_t heading_toward_player(int32_t x, int32_t z); /* 0x80060ae4 */
extern void spawn_actor_object(int kind, Actor *owner);      /* 0x80059e44 */
extern void play_sfx(int id);                               /* 0x8005044c */

/* Overlay table at 0x800b4d20.  Exact subtype names remain unassigned. */
extern uint8_t g_grasshopper_subtype_initialized[];

/*
 * Native selector 3, 0x800b3d78..0x800b3e84, called by VM opcode 0x000b.
 * The retail function is 68 instructions.  It is shared by every observed
 * actor-15/program-8 spawn, so visual variants are state/subtype variations,
 * not separately implemented enemy classes.
 */
void grasshopper_native_initialize(Actor *actor, int32_t x)
{
    uint8_t subtype;
    int outer;
    int inner;

    actor->heading_14 = heading_toward_player(x, actor->z_30);
    actor->flags_50 |= 2;
    subtype = actor->spawn_80->subtype_0f;
    if (g_grasshopper_subtype_initialized[subtype] != 0)
        return;

    g_grasshopper_subtype_initialized[subtype] = 1;
    actor->scale_or_height_6a = (int16_t)(actor->scale_or_height_6a + 2400);
    for (outer = 0; outer < 3; ++outer)
        for (inner = 0; inner < 8; ++inner)
            spawn_actor_object(21, actor);
    actor->motion_20 = -2048;
    play_sfx(102);
}

/*
 * Shared movement completion at 0x8004d02c..0x8004d03c.  When the arrival
 * condition accepts a movement mode >= 3, it releases the movement fields
 * and advances program 8 from opcode 0x0006 to opcode 0x0015.
 */
void enemy_vm_accept_arrival(Actor *actor)
{
    actor->motion_20 = 0;
    actor->cooldown_60 = 0;
    actor->program_70 += 1;
}

/*
 * Program 8 at 0x8007760c includes the selector-3 native call, pursuit/
 * arrival opcode 0x0006, opcode 0x0015, animation/state opcodes, a random
 * 32..95 tick cooldown, a random-heading step, and a parked movement state.
 * Contact damage and berry damage/death are common enemy subsystems (D03,
 * D04, and D05); no actor-15-only immunity gate was found.
 */
