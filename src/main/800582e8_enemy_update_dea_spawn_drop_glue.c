/* enemy_update_dea_spawn_drop_glue @ 0x800582e8 - 16 drops (type 0xc|(i&1)) at
 * base+4/8/12, proximity SFX gate, sound 13. */
extern void spawn_drop(int x, int y, int z, int type, int arg5);
extern void sfx_proximity_priority_gate(int x, int y, int z, int a, int arg5);
extern void play_sound(int id, void *p);

void enemy_update_dea_spawn_drop_glue(int *base)
{
    int i;

    for (i = 0; i < 16; i++)
        spawn_drop(base[1], base[2], base[3], (i & 1) | 0xc, 5);
    sfx_proximity_priority_gate(base[1], base[2], base[3], 0x80c0, 30);
    play_sound(13, base + 1);
}
