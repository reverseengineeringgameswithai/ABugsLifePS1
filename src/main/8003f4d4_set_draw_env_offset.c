/* set_draw_env_offset @ 0x8003f4d4 - stash draw-env x/y offsets */
extern int g_800822cc;
extern int g_800822d0;
extern short g_801cc508[8];
extern short g_801e14c4[8];
extern short g_801cc50a[8];
extern short g_801e14c6[8];

void set_draw_env_offset(int x, int y) {
    g_800822cc = x;
    g_800822d0 = y;
    g_801cc508[0] = x;
    g_801e14c4[0] = x;
    g_801cc50a[0] = y;
    g_801e14c6[0] = y;
}
