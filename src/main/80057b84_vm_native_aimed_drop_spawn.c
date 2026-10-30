/* vm_native_aimed_drop_spawn @ 0x80057b84 - 8 cycling type-21/22/23 drops + sound
 * 24, then set the object's facing (p[5]): aim at the player when kind==40, else
 * derive it from the descriptor byte. */
extern void spawn_drop(int x, int y, int z, int type, int arg5);
extern void play_sound(int id, void *p);
extern int sub_80060ae4(int dx, int dz);      /* atan2-style heading */
extern int g_800a6500;                        /* player X */
extern int g_800a6508;                        /* player Z */

void vm_native_aimed_drop_spawn(int *p)
{
    int t = 0, i;

    for (i = 0; i < 8; i++) {
        spawn_drop(p[1], p[2], p[3], t + 21, 6);
        t++;
        if (t >= 3)
            t = 0;
    }
    play_sound(24, p + 1);
    if (p[0] == 40) {
        int ang = sub_80060ae4((p[1] - g_800a6500) >> 5, (p[3] - g_800a6508) >> 5);
        p[5] = (ang + 2048) & 0xfff;
    } else {
        p[5] = ((unsigned char *)p[32])[15] << 4;
    }
}
