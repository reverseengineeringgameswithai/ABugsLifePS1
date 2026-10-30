/* spawn_drop_burst_type12 @ 0x80058258 - 16 drops (type 0xc|(i&1)), proximity SFX gate, sound 13. */
extern void spawn_drop(int x, int y, int z, int type, int arg5);
extern void sfx_proximity_priority_gate(int x, int y, int z, int a, int arg5);
extern void play_sound(int id, void *p);

void spawn_drop_burst_type12(int *p)
{
    int i;

    for (i = 0; i < 16; i++)
        spawn_drop(p[0], p[1], p[2], (i & 1) | 0xc, 5);
    sfx_proximity_priority_gate(p[0], p[1], p[2], 0x80c0, 30);
    play_sound(13, p);
}
