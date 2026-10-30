/* D05 source-level reconstruction from pristine SCUS_942.88 ASM. */
#include <stdint.h>

typedef struct EnemyActor {
    int32_t id;
    int32_t x, y, z;
    uint8_t unknown_10[0x3a];
    int16_t death_timer;       /* +0x4a: live-list death/retirement timer */
    uint8_t unknown_4c[0x10];
    uint16_t flags;            /* +0x5c */
    uint8_t unknown_5e[4];
    int16_t respawn_delay;     /* +0x62: KO-pool respawn delay */
    uint8_t unknown_64[2];
    int16_t vertical_extent;   /* +0x66 */
    uint8_t unknown_68[2];
    int16_t visibility_extent; /* +0x6a */
    int16_t reaction;
    int16_t hp;                /* +0x6e */
    const void *program;
    uint8_t unknown_74[0x0c];
    const uint8_t *spawn;      /* +0x80 */
} EnemyActor;

extern int enemy_spawn_is_visible(const int32_t *camera_anchor,
                                  const EnemyActor *actor); /* 0x80025084 */
extern void enemy_reinstantiate_from_spawn(EnemyActor *actor); /* 0x80049c30 */
extern void enemy_death_animation_update(EnemyActor *actor, int mode);

/* Reconstruction of the decision split in 0x8004d224..0x8004d694. */
void enemy_scheduler_decision(EnemyActor *actor,
                              const int32_t *camera_anchor)
{
    if (actor->hp > 0) {
        /* Live actors follow a separate near-anchor admission path. */
        return;
    }

    /* KO actors never execute the live near-anchor admission test. */
    if (actor->respawn_delay != 0) {
        if (actor->respawn_delay < 5000)
            --actor->respawn_delay;
        return;
    }

    if ((actor->flags & 0x0010) != 0 ||
        !enemy_spawn_is_visible(camera_anchor, actor))
        enemy_reinstantiate_from_spawn(actor);
}

/* Separate second-pass lifecycle; +0x4a is not the +0x62 respawn delay. */
void enemy_live_list_retirement(EnemyActor *actor)
{
    if (actor->death_timer > 0) {
        if (--actor->death_timer == 0)
            enemy_death_animation_update(actor, 1);
    } else if (actor->death_timer < 0) {
        if (++actor->death_timer == 0)
            enemy_death_animation_update(actor, 2);
    }
}
