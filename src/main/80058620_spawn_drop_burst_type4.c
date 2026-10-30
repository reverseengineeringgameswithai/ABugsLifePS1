/* spawn_drop_burst_type4 @ 0x80058620 - 5 drops (type 6|(i&1)), proximity SFX gate, sound 6. */
extern void spawn_drop(int x, int y, int z, int type, int arg5);
extern void sfx_proximity_priority_gate(int x, int y, int z, int a, int arg5);
extern void play_sound(int id, void *p);

void spawn_drop_burst_type4(int *p)
{
    int i;

    for (i = 0; i < 5; i++)
        spawn_drop(p[0], p[1], p[2], (i & 1) | 6, 4);
    sfx_proximity_priority_gate(p[0], p[1], p[2], 0xf00000, 16);
    play_sound(6, p);
}
