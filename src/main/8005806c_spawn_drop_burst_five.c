/* spawn_drop_burst_five - 5 drops (flavor (i&1)+3) at pos, then sound 5. */
extern int spawn_drop(int x, int y, int z, int flavor, int kind);
extern void play_sound(int id, void *arg);

void spawn_drop_burst_five(int *pos)
{
    int i;
    for (i = 0; i < 5; i++)
        spawn_drop(pos[0], pos[1], pos[2], (i & 1) + 3, 2);
    play_sound(5, pos);
}
