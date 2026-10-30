/* spawn_drop_burst_5_type79 @ 0x800584f8 - spawn 5 type-79 drops at coords,
 * fire the proximity SFX gate (color 0xffffff), then play sound 5. */
extern void *spawn_drop(int x, int y, int z, int type, int arg5);
extern void sfx_proximity_priority_gate(int x, int y, int z, int a, int arg5);
extern void play_sound(int id, void *src);

void spawn_drop_burst_5_type79(int *coords)
{
    int i;

    for (i = 0; i < 5; i++)
        spawn_drop(coords[0], coords[1], coords[2], 79, 5);

    sfx_proximity_priority_gate(coords[0], coords[1], coords[2], 0xffffff, 30);
    play_sound(5, coords);
}
