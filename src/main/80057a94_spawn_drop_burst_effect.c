/* spawn_drop_burst_effect @ 0x80057a94 - 8 cycling type-21/22/23 drops (y-7360) +
 * sound 24; set p[8], then flag+92: bit 0x2 when the (kind,berry) table entry is
 * small, and always clear bit 0x80. */
extern void spawn_drop(int x, int y, int z, int type, int arg5);
extern void play_sound(int id, void *p);
extern unsigned char g_800a6597;        /* equipped berry index */
extern unsigned char g_80089938[];      /* [kind*5 + berry] threshold table */

#define FLAG(p) (*(unsigned short *)((char *)(p) + 92))

void spawn_drop_burst_effect(int *p)
{
    int t = 0, i;

    for (i = 0; i < 8; i++) {
        spawn_drop(p[1], p[2] - 7360, p[3], t + 21, 6);
        t++;
        if (t >= 3)
            t = 0;
    }
    p[8] = -3072;
    play_sound(24, p + 1);
    if (g_80089938[p[0] * 5 + g_800a6597] < 100)
        FLAG(p) |= 0x2;
    FLAG(p) &= 0xff7f;
}
