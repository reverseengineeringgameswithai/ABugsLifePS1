/* spawn_drop_burst @ 0x800581c8 - 5 type-75 drops (y-4096), one type-77 drop, sound 5. */
extern void spawn_drop(int x, int y, int z, int type, int arg5);
extern void play_sound(int id, void *p);

void spawn_drop_burst(int *p)
{
    int i;

    for (i = 0; i < 5; i++)
        spawn_drop(p[0], p[1] - 4096, p[2], 75, 18);
    spawn_drop(p[0], p[1], p[2], 77, 3);
    play_sound(5, p);
}
