/*
 * grain_harvester_equipment_80051db4.c
 *
 * Documentation-grade semantic reconstruction of the resident grain-harvester
 * equip/follow owner. This is not a matching-C build unit. Exact opcodes and
 * function slices are guarded by analysis/phase4_collectibles_frontier.json.
 *
 * The function is called once per gameplay update from 0x8004EFF8, before the
 * actor updater (0x8004D224), contact updater (0x8005A308), source-3f dispatcher
 * (0x8005CD2C), and contact walker (0x8005BFBC).
 */

#include "re_types.h"

#define LH(addr)   (*(int16_t *)(addr))
#define LHU(addr)  (*(uint16_t *)(addr))
#define LW(addr)   (*(int32_t *)(addr))
#define SH(addr,v) (*(uint16_t *)(addr) = (uint16_t)(v))
#define SW(addr,v) (*(int32_t *)(addr) = (int32_t)(v))

#define GLOBAL_ENABLE_FLAGS 0x80082488u
#define GLOBAL_DENIAL_FLAGS 0x80082380u
#define PLAYER_BASE         0x800A6500u
#define PLAYER_EQUIP_GATE   0x800A6582u
#define PLAYER_STATE_6588   0x800A6588u
#define PLAYER_STATE_657C   0x800A657Cu
#define PLAYER_POWER_FLAGS  0x800A6590u
#define PLAYER_FOLLOW_FLAG  0x800A657Eu
#define PLAYER_EFFECT_659E  0x800A659Eu
#define HARVESTER_ACTOR     0x800A1DFCu /* fixed actor slot 63 */
#define HARVESTER_ACTOR_ID  35
#define HARVESTER_BIT       0x0080u

extern int  proximity_test_80052508(void *player, void *actor_xyz, int radius);
extern void event_80050994(int event_id);
extern void post_pickup_8005044c(int result, void *player);
extern void actor_effect_8005f5b8(void *actor);
extern void player_effect_80046cac(void);
extern void spawn_effect_80058378(int x, int y, int z);
extern void actor_transform_8004c10c(void *actor, int a1, int a2);

void grain_harvester_equipment_80051db4(void)
{
    if (!(LHU(GLOBAL_ENABLE_FLAGS) & 0x8000)) {
        return;
    }
    if (LHU(GLOBAL_DENIAL_FLAGS) & 0x8000) {
        return;
    }
    if (LW(HARVESTER_ACTOR) != HARVESTER_ACTOR_ID) {
        return;
    }

    if (LH(PLAYER_EQUIP_GATE) != 0 &&
        !(LHU(PLAYER_POWER_FLAGS) & HARVESTER_BIT) &&
        proximity_test_80052508(
            (void *)PLAYER_BASE, (void *)(HARVESTER_ACTOR + 4), 40) &&
        LH(PLAYER_STATE_6588) != 13 &&
        LH(PLAYER_STATE_657C) == 0) {
        event_80050994(0x32);
        post_pickup_8005044c(-12, (void *)PLAYER_BASE);
        actor_effect_8005f5b8((void *)HARVESTER_ACTOR);
        SH(PLAYER_FOLLOW_FLAG, 1);
        SH(PLAYER_EFFECT_659E, 0);
        SH(PLAYER_POWER_FLAGS, LHU(PLAYER_POWER_FLAGS) | HARVESTER_BIT);
        player_effect_80046cac();
        spawn_effect_80058378(
            LW(HARVESTER_ACTOR + 4),
            LW(HARVESTER_ACTOR + 8) - 0x2000,
            LW(HARVESTER_ACTOR + 12));
    }

    if (!(LHU(PLAYER_POWER_FLAGS) & HARVESTER_BIT)) {
        return;
    }

    /*
     * Equipped ownership is direct: slot 63 follows the player every update.
     * The retained C13 index observes the resulting actor-player delta
     * (0, 192, 0) from the first 0x80-bit frame onward. That offset is an
     * observed post-update result; it is not authored as a literal here.
     */
    SW(HARVESTER_ACTOR + 0x04, LW(PLAYER_BASE + 0x00));
    SW(HARVESTER_ACTOR + 0x08, LW(PLAYER_BASE + 0x04));
    SW(HARVESTER_ACTOR + 0x0C, LW(PLAYER_BASE + 0x08));
    SW(HARVESTER_ACTOR + 0x24, LW(PLAYER_BASE + 0x00));
    SW(HARVESTER_ACTOR + 0x28, LW(PLAYER_BASE + 0x04));
    SW(HARVESTER_ACTOR + 0x2C, LW(PLAYER_BASE + 0x08));
    SW(HARVESTER_ACTOR + 0x30, LW(PLAYER_BASE + 0x00));
    SW(HARVESTER_ACTOR + 0x34, LW(PLAYER_BASE + 0x04));
    SW(HARVESTER_ACTOR + 0x38, LW(PLAYER_BASE + 0x08));
    SW(HARVESTER_ACTOR + 0x14, LW(PLAYER_BASE + 0x20));

    /*
     * 0x80051FE0..0x80052070 also selects actor_transform_8004c10c modes
     * from player+0x38 and derives the actor +0x48 byte. Those presentation
     * details are retained in the opcode frontier but intentionally remain
     * outside the equipment/attraction ownership claim.
     */
}
