/* spawn_drop_burst_type2 - 5 drops (kind (i&1)+9) at *p, then sound 5. */
extern void spawn_drop(int x, int y, int z, int kind, int type);
extern void play_sound(int id, void *p);

void spawn_drop_burst_type2(int *p)
{
    int i;

    for (i = 0; i < 5; i++)
        spawn_drop(p[0], p[1], p[2], (i & 1) + 9, 2);
    play_sound(5, p);
}
