/* mine_detonation_effect - 24 debris drops (type 0xc|(i&1)), proximity SFX gate, sound 13. */
extern void *spawn_drop(int x, int y, int z, int type, int arg5);
extern void sfx_proximity_priority_gate(int x, int y, int z, int a, int arg5);
extern void play_sound(int id, void *src);

void mine_detonation_effect(int *coords)
{
    int i;

    for (i = 0; i < 24; i++)
        spawn_drop(coords[0], coords[1], coords[2], (i & 1) | 0xc, 11);

    sfx_proximity_priority_gate(coords[0], coords[1], coords[2], 0x80c0, 30);
    play_sound(13, coords);
}
