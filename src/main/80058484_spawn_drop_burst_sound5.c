/* spawn_drop_burst_sound5 - 5 drops (type 0x2e|(i&1)) at coords, then sound 5. */
extern void *spawn_drop(int x, int y, int z, int ctorType, int stackArg);
extern void play_sound(int id, void *obj);

void spawn_drop_burst_sound5(int *coords)
{
    int i;

    for (i = 0; i < 5; i++)
        spawn_drop(coords[0], coords[1], coords[2], (i & 1) | 0x2e, 2);
    play_sound(5, coords);
}
