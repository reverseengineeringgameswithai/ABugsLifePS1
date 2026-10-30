/* LEVEL10_LEVEL overlay @ 0x800b3bf0. Initializes four overlay-local state
 * words; only 0x800b41b8 is nonzero.
 */
extern int g_800b41b4;
extern int g_800b41b8;
extern int g_800b41bc;
extern int g_800b41b0;

void level10_init_overlay_state(void)
{
    g_800b41b4 = 0;
    g_800b41b8 = 20;
    g_800b41bc = 0;
    g_800b41b0 = 0;
}
