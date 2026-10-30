/* spawn_drop_burst_type76 - 5 type-76 drops at obj xyz, then play sound 5. */
extern void *spawn_drop(int x, int y, int z, int type, int arg5);
extern void play_sound(int id, void *obj);

void spawn_drop_burst_type76(int *obj)
{
    int i;

    for (i = 0; i < 5; i++)
        spawn_drop(obj[0], obj[1], obj[2], 76, 2);

    play_sound(5, obj);
}
