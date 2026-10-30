/*
 * Documentation-grade semantic C for resident handler 0x8005C258.
 * This is not matching C and is not compiled into the game.
 * Byte authority remains asm/hand_written/8005c258_seed_plant_propeller_handler.s.
 */
#include <stdint.h>

typedef struct {
    int16_t unknown_00;
    int16_t state_02;
    int32_t unknown_04;
    int32_t x_08, y_0c, z_10;
    uint8_t unknown_14[0x1a];
    uint16_t flags_2e;
} PlantSlot;

typedef struct {
    uint8_t id;
    uint8_t pad_01[3];
    int32_t x, y, z;
    uint8_t pad_10[0x0c];
    int32_t vx, vy, vz;
    uint8_t pad_28[0x18];
    int32_t field_40;
    uint8_t pad_44[0x18];
    uint16_t flags_5c;
    uint16_t field_5e;
} LiveActor;

extern int xz_radius_800524b8(const void *a, const void *b, int radius);
extern void detach_carried_state_80046cac(void);
extern uint8_t next_random_byte(void);

static volatile int32_t *const player = (volatile int32_t *)(uintptr_t)0x800A6500u;
static LiveActor *volatile *const live_actor_table = (LiveActor *volatile *)(uintptr_t)0x80090748u;

void propeller_plant_semantic_8005c258(PlantSlot *plant)
{
    int32_t player_delta_y = plant->y_0c - player[1];

    if (xz_radius_800524b8(&plant->x_08, (const void *)(uintptr_t)0x800A6500u, 40) &&
        (*(volatile uint16_t *)(uintptr_t)0x800A6590u & 0x0080u) == 0 &&
        *(volatile int16_t *)(uintptr_t)0x800A6582u == 0 &&
        player_delta_y <= 40959 &&
        (player_delta_y >= 12289 ||
         (*(volatile int16_t *)(uintptr_t)0x800A659Eu == 11 && player_delta_y >= 4097))) {
        detach_carried_state_80046cac();
        if (*(volatile int16_t *)(uintptr_t)0x800A659Eu == 12)
            *(volatile int16_t *)(uintptr_t)0x800A659Eu = 0;
        *(volatile int16_t *)(uintptr_t)0x800A6580u = 5;
        *(volatile int16_t *)(uintptr_t)0x800A6584u = 0;
        player[12] -= 512;
        if (*(volatile int16_t *)(uintptr_t)0x800A6588u != 13)
            *(volatile int32_t *)(uintptr_t)0x80082294u = 120;
        *(volatile int16_t *)(uintptr_t)0x800A6588u = 13;
        if (player[12] < -3072)
            player[12] = -3072;
    }

    for (unsigned i = 0; live_actor_table[i] != 0; i++) {
        LiveActor *actor = live_actor_table[i];
        int32_t actor_delta_y = plant->y_0c - actor->y;
        if ((actor->flags_5c & 0x0020u) == 0 || actor->field_40 != 0 ||
            !xz_radius_800524b8(&plant->x_08, &actor->x, 40) ||
            actor_delta_y < 12289 || actor_delta_y > 40959)
            continue;

        actor->vy -= 512;
        if (actor->vx == 0 && actor->vz == 0) {
            actor->vx = next_random_byte();
            actor->vz = next_random_byte();
        }
        actor->field_5e = 0;
    }
}

/*
 * Important non-behaviors:
 * - Carrying alone is not a detach condition. Detach occurs only after the
 *   player lift predicate succeeds.
 * - The actor loop has no seed-ID check and no carried-flag exclusion.
 * - This handler does not clear player mode 5 or own landing.
 * - It does not write player X/Z velocity; steering remains shared physics.
 */
