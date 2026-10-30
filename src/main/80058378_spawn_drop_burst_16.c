/* spawn_drop_burst_16 - spawn 16 type-119 drops at one location. */
extern void *spawn_drop(int x, int y, int z, int type, int arg5);

void spawn_drop_burst_16(int x, int y, int z)
{
    int i;

    for (i = 0; i < 16; i++)
        spawn_drop(x, y, z, 119, 5);
}
