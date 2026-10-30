/* LEVEL06_LEVEL overlay @ 0x800b3b94. Clears four overlay-local state words. */
extern int g_800b3fdc;
extern int g_800b3fe4;
extern int g_800b3fe0;
extern int g_800b3fd8;

void level06_clear_overlay_state(void)
{
    g_800b3fdc = 0;
    g_800b3fe4 = 0;
    g_800b3fe0 = 0;
    g_800b3fd8 = 0;
}
